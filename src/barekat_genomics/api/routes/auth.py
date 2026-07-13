"""احراز هویت JWT."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from barekat_genomics.api.deps import CurrentUser, get_current_user
from barekat_genomics.core.database import get_db
from barekat_genomics.schemas import TokenResponse, UserResponse
from barekat_genomics.services.auth_service import AuthService

router = APIRouter(prefix="/auth")


@router.post("/login", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    service = AuthService(db)
    result = service.authenticate(form.username, form.password)
    if not result:
        raise HTTPException(status_code=401, detail="ایمیل یا رمز عبور نادرست است")
    user, token = result
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def me(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    from barekat_genomics.models.user import User

    db_user = db.query(User).filter(User.id == user.id).first()
    if db_user:
        return UserResponse.model_validate(db_user)
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=True,
    )
