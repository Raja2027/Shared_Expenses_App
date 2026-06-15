from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from expense_App.entity.models import User
from expense_App.exception import AuthenticationException, ConflictException, DatabaseException
from expense_App.logger import get_logger
from security import create_access_token, hash_password, verify_password


logger = get_logger(__name__)


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email.lower())
        return self.db.execute(statement).scalar_one_or_none()

    def get_user_by_id(self, user_id: int) -> User | None:
        statement = select(User).where(User.id == user_id)
        return self.db.execute(statement).scalar_one_or_none()

    def register_user(self, name: str, email: str, password: str) -> User:
        normalized_email = email.lower()
        if self.get_user_by_email(normalized_email):
            raise ConflictException(
                message="A user with this email already exists.",
                error_code="email_already_registered",
                details={"email": normalized_email},
            )

        user = User(
            name=name,
            email=normalized_email,
            hashed_password=hash_password(password),
            is_active=True,
        )
        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        except SQLAlchemyError as error:
            self.db.rollback()
            logger.exception("Failed to register user email=%s", normalized_email)
            raise DatabaseException(
                message="Failed to register user.",
                details={"email": normalized_email},
            ) from error
        return user

    def authenticate_user(self, email: str, password: str) -> User:
        normalized_email = email.lower()
        user = self.get_user_by_email(normalized_email)
        if not user or not verify_password(password, user.hashed_password):
            raise AuthenticationException(
                message="Invalid email or password.",
                error_code="invalid_credentials",
            )
        if not user.is_active:
            raise AuthenticationException(
                message="This user account is inactive.",
                error_code="inactive_user",
            )
        return user

    def issue_access_token(self, user: User) -> tuple[str, int]:
        return create_access_token(user_id=user.id, email=user.email)
