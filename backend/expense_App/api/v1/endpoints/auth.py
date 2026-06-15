from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from expense_App.components.auth_service import AuthService
from expense_App.dependencies import get_current_user, get_db_session
from expense_App.entity.models import User
from expense_App.schemas.auth import AccessTokenResponse, UserRegisterRequest, UserResponse


router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register_user(
    payload: UserRegisterRequest,
    db: Session = Depends(get_db_session),
) -> User:
    return AuthService(db).register_user(
        name=payload.name,
        email=str(payload.email),
        password=payload.password.get_secret_value(),
    )


@router.post(
    "/login",
    response_model=AccessTokenResponse,
    summary="Log in and receive a bearer token",
)
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db_session),
) -> AccessTokenResponse:
    service = AuthService(db)
    user = service.authenticate_user(
        email=form_data.username,
        password=form_data.password,
    )
    token, expires_in = service.issue_access_token(user)
    return AccessTokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Return the authenticated user",
)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
