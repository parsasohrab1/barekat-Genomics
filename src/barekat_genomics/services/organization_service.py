"""سرویس سازمان‌ها و عضویت."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from barekat_genomics.core.tenant import DEFAULT_ORG_NAME, DEFAULT_ORG_SLUG
from barekat_genomics.models.organization import Organization, OrganizationMembership
from barekat_genomics.models.user import User


class OrganizationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ensure_default(self) -> Organization:
        org = self.db.query(Organization).filter(Organization.slug == DEFAULT_ORG_SLUG).first()
        if org:
            return org
        org = Organization(
            slug=DEFAULT_ORG_SLUG,
            name=DEFAULT_ORG_NAME,
            name_fa="سازمان پیش‌فرض",
            deployment_mode="saas",
            is_active=True,
        )
        self.db.add(org)
        self.db.commit()
        self.db.refresh(org)
        return org

    def get(self, org_id: uuid.UUID) -> Organization | None:
        return self.db.query(Organization).filter(Organization.id == org_id).first()

    def get_by_slug(self, slug: str) -> Organization | None:
        return self.db.query(Organization).filter(Organization.slug == slug).first()

    def list_all(self) -> list[Organization]:
        return self.db.query(Organization).order_by(Organization.created_at.desc()).all()

    def create(
        self,
        *,
        slug: str,
        name: str,
        name_fa: str | None = None,
        deployment_mode: str = "saas",
    ) -> Organization:
        org = Organization(
            slug=slug,
            name=name,
            name_fa=name_fa,
            deployment_mode=deployment_mode,
            is_active=True,
        )
        self.db.add(org)
        self.db.commit()
        self.db.refresh(org)
        return org

    def add_member(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        org_role: str = "member",
    ) -> OrganizationMembership:
        existing = (
            self.db.query(OrganizationMembership)
            .filter(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == user_id,
            )
            .first()
        )
        if existing:
            existing.org_role = org_role
            self.db.commit()
            return existing
        m = OrganizationMembership(
            organization_id=organization_id,
            user_id=user_id,
            org_role=org_role,
        )
        self.db.add(m)
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and user.organization_id is None:
            user.organization_id = organization_id
        self.db.commit()
        self.db.refresh(m)
        return m

    def user_belongs(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> bool:
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and user.organization_id == organization_id:
            return True
        return (
            self.db.query(OrganizationMembership)
            .filter(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == organization_id,
            )
            .first()
            is not None
        )
