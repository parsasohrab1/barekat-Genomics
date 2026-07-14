"""مدیریت کاربران و RBAC."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from barekat_genomics.core.rbac import is_valid_role
from barekat_genomics.core.security import hash_password
from barekat_genomics.models.organization import OrganizationMembership
from barekat_genomics.models.user import User


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_users(self, organization_id: uuid.UUID | None = None) -> list[User]:
        q = self.db.query(User)
        if organization_id is not None:
            q = q.filter(User.organization_id == organization_id)
        return q.order_by(User.created_at.desc()).all()

    def create_user(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        role: str,
        organization_id: uuid.UUID | None = None,
    ) -> User:
        if not is_valid_role(role):
            raise ValueError(f"نقش نامعتبر: {role}")
        if self.db.query(User).filter(User.email == email).first():
            raise ValueError("ایمیل تکراری است")
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=role,
            organization_id=organization_id,
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()
        if organization_id:
            self.db.add(
                OrganizationMembership(
                    organization_id=organization_id,
                    user_id=user.id,
                    org_role="admin" if role == "admin" else "member",
                )
            )
        self.db.commit()
        self.db.refresh(user)
        return user

    def set_active(self, user_id: uuid.UUID, is_active: bool) -> User | None:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        user.is_active = is_active
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_role(self, user_id: uuid.UUID, role: str) -> User | None:
        if not is_valid_role(role):
            raise ValueError(f"نقش نامعتبر: {role}")
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        user.role = role
        self.db.commit()
        self.db.refresh(user)
        return user
