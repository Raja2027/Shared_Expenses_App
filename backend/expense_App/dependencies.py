from collections.abc import Generator

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from expense_App.config import settings
from expense_App.database import SessionLocal
from expense_App.entity.models import User
from expense_App.exception import AuthenticationException
from expense_App.components.auth_service import AuthService
from security import decode_access_token


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login",
    auto_error=False,
)


def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db_session),
) -> User:
    if not token:
        raise AuthenticationException(
            message="Authentication is required.",
            error_code="authentication_required",
        )

    payload = decode_access_token(token)
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as error:
        raise AuthenticationException(
            message="The access token is invalid.",
            error_code="invalid_access_token",
        ) from error

    user = AuthService(db).get_user_by_id(user_id)
    if not user:
        raise AuthenticationException(
            message="The access token user no longer exists.",
            error_code="token_user_not_found",
        )
    if not user.is_active:
        raise AuthenticationException(
            message="This user account is inactive.",
            error_code="inactive_user",
        )
    return user
