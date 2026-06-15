from typing import Any

from expense_App.exception.custom_exception import ExpenseAppException, ValidationException


class ImportPipelineError(ExpenseAppException):
    """Base exception for controlled import pipeline failures."""

    def __init__(
        self,
        message: str,
        error_code: str = "import_pipeline_error",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
        )


class CSVSchemaError(ValidationException):
    """Raised when an uploaded CSV does not match the expected assignment schema."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="csv_schema_error",
            details=details,
        )
