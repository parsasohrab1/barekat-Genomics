"""وابستگی‌های FastAPI: احراز هویت، RBAC و multi-tenant."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from barekat_genomics.core.config import get_settings
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import (
    Permission,
    has_permission,
    is_physician_role,
    is_privileged_role,
)
from barekat_genomics.core.security import TokenDecodeError, verify_access_token
from barekat_genomics.core.tenant import set_current_org_id
from barekat_genomics.models.patient import Patient
from barekat_genomics.models.user import User
from barekat_genomics.services.organization_service import OrganizationService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


@dataclass
class CurrentUser:
    id: uuid.UUID
    email: str
    role: str
    full_name: str
    organization_id: uuid.UUID | None = None


_DEV_USER = CurrentUser(
    id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
    email="dev@barekat.local",
    role="admin",
    full_name="Dev Admin",
    organization_id=None,
)


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
    x_organization_id: Annotated[str | None, Header(alias="X-Organization-Id")] = None,
) -> CurrentUser:
    settings = get_settings()
    if not settings.auth_enabled:
        org = OrganizationService(db).ensure_default()
        set_current_org_id(org.id)
        return CurrentUser(
            id=_DEV_USER.id,
            email=_DEV_USER.email,
            role=_DEV_USER.role,
            full_name=_DEV_USER.full_name,
            organization_id=org.id,
        )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="احراز هویت لازم است",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (TokenDecodeError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="توکن نامعتبر",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="کاربر یافت نشد")

    org_id = user.organization_id
    token_org = payload.get("org")
    if token_org:
        try:
            org_id = uuid.UUID(token_org)
        except ValueError:
            pass

    if x_organization_id:
        try:
            requested = uuid.UUID(x_organization_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="X-Organization-Id نامعتبر")
        if user.role == "admin" or OrganizationService(db).user_belongs(user.id, requested):
            org_id = requested
        else:
            raise HTTPException(status_code=403, detail="عضویت در این سازمان مجاز نیست")

    set_current_org_id(org_id)
    return CurrentUser(
        id=user.id,
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        organization_id=org_id,
    )


def require_permission(permission: Permission):
    async def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"دسترسی مجاز نیست: {permission.value}",
            )
        return user

    return checker


def can_access_patient(user: CurrentUser, patient: Patient) -> bool:
    if user.organization_id and patient.organization_id and patient.organization_id != user.organization_id:
        if user.role != "admin":
            return False
    if is_privileged_role(user.role):
        return True
    if is_physician_role(user.role):
        return patient.assigned_clinician_id == user.id
    return False


def assert_patient_access(user: CurrentUser, patient: Patient) -> None:
    if not can_access_patient(user, patient):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی به این بیمار مجاز نیست")
