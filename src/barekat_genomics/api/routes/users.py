"""مدیریت کاربران (Admin)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import CurrentUser, require_permission
from barekat_genomics.core.database import get_db
from barekat_genomics.core.rbac import Permission
from barekat_genomics.schemas import UserResponse
from barekat_genomics.services.user_service import UserService

router = APIRouter(prefix="/users")


class UserCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8)
    full_name: str
    role: str = Field(pattern="^(admin|analyst|physician|clinician|geneticist|lab_tech)$")


class UserRoleUpdate(BaseModel):
    role: str = Field(pattern="^(admin|analyst|physician|clinician|geneticist|lab_tech)$")


class UserActiveUpdate(BaseModel):
    is_active: bool


@router.get("/", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.USERS_MANAGE)),
) -> list[UserResponse]:
    rows = UserService(db).list_users(organization_id=user.organization_id)
    return [UserResponse.model_validate(u) for u in rows]


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(
    body: UserCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.USERS_MANAGE)),
) -> UserResponse:
    try:
        created = UserService(db).create_user(
            email=body.email,
            password=body.password,
            full_name=body.full_name,
            role=body.role,
            organization_id=user.organization_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return UserResponse.model_validate(created)


@router.patch("/{user_id}/role", response_model=UserResponse)
def update_role(
    user_id: uuid.UUID,
    body: UserRoleUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_permission(Permission.USERS_MANAGE)),
) -> UserResponse:
    try:
        updated = UserService(db).update_role(user_id, body.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    return UserResponse.model_validate(updated)


@router.patch("/{user_id}/active", response_model=UserResponse)
def set_active(
    user_id: uuid.UUID,
    body: UserActiveUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Permission.USERS_MANAGE)),
) -> UserResponse:
    updated = UserService(db).set_active(user_id, body.is_active)
    if not updated:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    return UserResponse.model_validate(updated)
