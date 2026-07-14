"""سرویس پلن و اشتراک."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from barekat_genomics.models.billing import Invoice, Plan, Subscription
from barekat_genomics.models.organization import OrganizationMembership
from barekat_genomics.models.sample import SequencingSample
from barekat_genomics.models.patient import Patient


DEFAULT_PLANS = [
    {
        "code": "starter",
        "name": "Starter",
        "name_fa": "پایه",
        "deployment_mode": "saas",
        "price_monthly_usd": 499.0,
        "max_users": 5,
        "max_samples_month": 50,
        "max_storage_gb": 100,
        "features": ["pgx_panel", "fhir_export"],
    },
    {
        "code": "professional",
        "name": "Professional",
        "name_fa": "حرفه‌ای",
        "deployment_mode": "saas",
        "price_monthly_usd": 1499.0,
        "max_users": 25,
        "max_samples_month": 500,
        "max_storage_gb": 1000,
        "features": ["pgx_panel", "fhir_export", "hl7", "ai_assist", "multi_tenant"],
    },
    {
        "code": "enterprise_onprem",
        "name": "Enterprise On-Prem",
        "name_fa": "سازمانی درون‌سازمانی",
        "deployment_mode": "on_prem",
        "price_monthly_usd": 0.0,
        "max_users": 500,
        "max_samples_month": 100000,
        "max_storage_gb": 50000,
        "features": ["pgx_panel", "fhir_export", "hl7", "ai_assist", "multi_tenant", "offline"],
    },
]


class BillingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def seed_plans(self) -> list[Plan]:
        created = []
        for spec in DEFAULT_PLANS:
            existing = self.db.query(Plan).filter(Plan.code == spec["code"]).first()
            if existing:
                created.append(existing)
                continue
            plan = Plan(
                code=spec["code"],
                name=spec["name"],
                name_fa=spec["name_fa"],
                deployment_mode=spec["deployment_mode"],
                price_monthly_usd=spec["price_monthly_usd"],
                max_users=spec["max_users"],
                max_samples_month=spec["max_samples_month"],
                max_storage_gb=spec["max_storage_gb"],
                features_json=json.dumps(spec["features"]),
                is_active=True,
            )
            self.db.add(plan)
            created.append(plan)
        self.db.commit()
        return created

    def list_plans(self, deployment_mode: str | None = None) -> list[Plan]:
        self.seed_plans()
        q = self.db.query(Plan).filter(Plan.is_active.is_(True))
        if deployment_mode:
            q = q.filter(Plan.deployment_mode.in_([deployment_mode, "both"]))
        return q.order_by(Plan.price_monthly_usd.asc()).all()

    def get_subscription(self, organization_id: uuid.UUID) -> Subscription | None:
        return (
            self.db.query(Subscription)
            .filter(Subscription.organization_id == organization_id)
            .first()
        )

    def subscribe(
        self,
        organization_id: uuid.UUID,
        plan_code: str,
        *,
        trial_days: int = 14,
    ) -> Subscription:
        self.seed_plans()
        plan = self.db.query(Plan).filter(Plan.code == plan_code, Plan.is_active.is_(True)).first()
        if not plan:
            raise ValueError(f"پلن ناشناخته: {plan_code}")

        existing = self.get_subscription(organization_id)
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30 if plan.deployment_mode == "saas" else 365)
        status = "trial" if trial_days > 0 and plan.price_monthly_usd > 0 else "active"

        seats = (
            self.db.query(OrganizationMembership)
            .filter(OrganizationMembership.organization_id == organization_id)
            .count()
        ) or 1

        if existing:
            existing.plan_id = plan.id
            existing.status = status
            existing.current_period_end = period_end
            existing.seats_used = seats
            self.db.commit()
            self.db.refresh(existing)
            return existing

        sub = Subscription(
            organization_id=organization_id,
            plan_id=plan.id,
            status=status,
            billing_cycle="monthly",
            started_at=now,
            current_period_end=period_end,
            samples_used_period=0,
            seats_used=seats,
        )
        self.db.add(sub)
        self.db.flush()

        if plan.price_monthly_usd > 0:
            inv = Invoice(
                subscription_id=sub.id,
                amount_usd=plan.price_monthly_usd,
                status="pending" if status == "trial" else "paid",
                paid_at=None if status == "trial" else now,
                notes=f"Initial invoice for {plan.code}",
            )
            self.db.add(inv)

        self.db.commit()
        self.db.refresh(sub)
        return sub

    def usage(self, organization_id: uuid.UUID) -> dict:
        sub = self.get_subscription(organization_id)
        plan = sub.plan if sub else None
        sample_count = (
            self.db.query(SequencingSample)
            .join(Patient, SequencingSample.patient_id == Patient.id)
            .filter(Patient.organization_id == organization_id)
            .count()
        )
        user_count = (
            self.db.query(OrganizationMembership)
            .filter(OrganizationMembership.organization_id == organization_id)
            .count()
        )
        return {
            "organization_id": str(organization_id),
            "subscription_status": sub.status if sub else "none",
            "plan_code": plan.code if plan else None,
            "samples_used": sample_count,
            "samples_limit": plan.max_samples_month if plan else None,
            "seats_used": user_count,
            "seats_limit": plan.max_users if plan else None,
            "within_sample_limit": (
                True if not plan else sample_count <= plan.max_samples_month
            ),
            "within_seat_limit": True if not plan else user_count <= plan.max_users,
        }

    def assert_can_add_sample(self, organization_id: uuid.UUID | None) -> None:
        if organization_id is None:
            return
        info = self.usage(organization_id)
        if info["samples_limit"] is not None and not info["within_sample_limit"]:
            raise PermissionError("سقف نمونه ماهانه پلن به پایان رسیده است")
