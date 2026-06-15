from typing import Any


class ExpenseAppException(Exception):
    """Base exception for controlled application failures."""

    def __init__(
        self,
        message: str,
        error_code: str = "expense_app_error",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.headers = headers or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }

    def __str__(self) -> str:
        if not self.details:
            return f"{self.error_code}: {self.message}"
        return f"{self.error_code}: {self.message} | details={self.details}"


class ValidationException(ExpenseAppException):
    def __init__(
        self,
        message: str,
        error_code: str = "validation_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=422,
            details=details,
        )


class NotFoundException(ExpenseAppException):
    def __init__(
        self,
        message: str,
        error_code: str = "not_found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=404,
            details=details,
        )


class DatabaseException(ExpenseAppException):
    def __init__(
        self,
        message: str,
        error_code: str = "database_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=500,
            details=details,
        )


class ServiceUnavailableException(ExpenseAppException):
    def __init__(
        self,
        message: str,
        error_code: str = "service_unavailable",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=503,
            details=details,
        )


class AuthenticationException(ExpenseAppException):
    def __init__(
        self,
        message: str = "Authentication is required.",
        error_code: str = "authentication_required",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=401,
            details=details,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationException(ExpenseAppException):
    def __init__(
        self,
        message: str = "You are not allowed to perform this action.",
        error_code: str = "forbidden",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=403,
            details=details,
        )


class ConflictException(ExpenseAppException):
    def __init__(
        self,
        message: str,
        error_code: str = "conflict",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=409,
            details=details,
        )
