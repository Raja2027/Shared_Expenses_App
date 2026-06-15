from datetime import datetime, timezone
from uuid import uuid4

import bcrypt
from jose import JWTError, jwt

from expense_App.config import settings
from expense_App.exception import AuthenticationException


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("Password cannot exceed 72 UTF-8 bytes.")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (TypeError, ValueError):
        return False


def create_access_token(user_id: int, email: str) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    expires_at = now + settings.access_token_expiry
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "iat": now,
        "exp": expires_at,
        "jti": str(uuid4()),
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token, settings.access_token_expire_minutes * 60


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as error:
        raise AuthenticationException(
            message="The access token is invalid or expired.",
            error_code="invalid_access_token",
        ) from error

    if payload.get("type") != "access" or not payload.get("sub"):
        raise AuthenticationException(
            message="The access token is invalid.",
            error_code="invalid_access_token",
        )
    return payload
