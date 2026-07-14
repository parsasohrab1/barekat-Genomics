"""سرویس احراز هویت."""

from sqlalchemy.orm import Session

from barekat_genomics.core.security import create_access_token, verify_password
from barekat_genomics.models.user import User


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def authenticate(self, email: str, password: str) -> tuple[User, str] | None:
        user = self.db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
        if not user or not verify_password(password, user.hashed_password):
            return None
        org_id = str(user.organization_id) if user.organization_id else None
        token = create_access_token(str(user.id), user.role, user.email, organization_id=org_id)
        return user, token

    def get_user_by_id(self, user_id: str) -> User | None:
        import uuid
        return self.db.query(User).filter(User.id == uuid.UUID(user_id)).first()
