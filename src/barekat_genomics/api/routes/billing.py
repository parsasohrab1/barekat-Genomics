"""صورتحساب و پلن اشتراک."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import CurrentUser, get_current_user, require_permission
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import Permission
from barekat_genomics.services.billing_service import BillingService
from barekat_genomics.services.organization_service import OrganizationService

router = APIRouter(prefix="/billing")


class PlanResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    name_fa: str | None = None
    deployment_mode: str
    price_monthly_usd: float
    max_users: int
    max_samples_month: int
    max_storage_gb: int

    model_config = {"from_attributes": True}


class SubscribeRequest(BaseModel):
    plan_code: str = Field(min_length=2)
    trial_days: int = Field(default=14, ge=0, le=90)


class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    plan_id: uuid.UUID
    status: str
    billing_cycle: str
    samples_used_period: int
    seats_used: int

    model_config = {"from_attributes": True}


@router.get("/plans", response_model=list[PlanResponse])
def list_plans(
    deployment_mode: str | None = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.BILLING_READ)),
) -> list[PlanResponse]:
    plans = BillingService(db).list_plans(deployment_mode=deployment_mode)
    return [PlanResponse.model_validate(p) for p in plans]


@router.get("/usage")
def usage(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.BILLING_READ)),
) -> dict:
    org_id = user.organization_id or OrganizationService(db).ensure_default().id
    return BillingService(db).usage(org_id)


@router.get("/subscription", response_model=SubscriptionResponse | None)
def get_subscription(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.BILLING_READ)),
):
    org_id = user.organization_id or OrganizationService(db).ensure_default().id
    sub = BillingService(db).get_subscription(org_id)
    return SubscriptionResponse.model_validate(sub) if sub else None


@router.post("/subscribe", response_model=SubscriptionResponse)
def subscribe(
    body: SubscribeRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.BILLING_MANAGE)),
) -> SubscriptionResponse:
    org_id = user.organization_id or OrganizationService(db).ensure_default().id
    try:
        sub = BillingService(db).subscribe(org_id, body.plan_code, trial_days=body.trial_days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SubscriptionResponse.model_validate(sub)
