from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from expense_App.exception.custom_exception import ExpenseAppException
from expense_App.logger import get_logger


logger = get_logger(__name__)


def error_response(
    request: Request,
    status_code: int,
    error_code: str,
    message: str,
    details: dict | list | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "error_code": error_code,
                "message": message,
                "details": details or {},
            },
            "request_id": getattr(request.state, "request_id", None),
        },
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ExpenseAppException)
    async def handle_expense_app_exception(
        request: Request,
        exception: ExpenseAppException,
    ) -> JSONResponse:
        logger.warning(
            "Controlled application error request_id=%s code=%s path=%s",
            getattr(request.state, "request_id", None),
            exception.error_code,
            request.url.path,
        )
        return error_response(
            request=request,
            status_code=exception.status_code,
            error_code=exception.error_code,
            message=exception.message,
            details=exception.details,
            headers=exception.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        exception: RequestValidationError,
    ) -> JSONResponse:
        return error_response(
            request=request,
            status_code=422,
            error_code="request_validation_error",
            message="Request validation failed.",
            details=exception.errors(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request,
        exception: StarletteHTTPException,
    ) -> JSONResponse:
        message = exception.detail if isinstance(exception.detail, str) else "HTTP request failed."
        return error_response(
            request=request,
            status_code=exception.status_code,
            error_code="http_error",
            message=message,
            details={} if isinstance(exception.detail, str) else exception.detail,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(
        request: Request,
        exception: Exception,
    ) -> JSONResponse:
        logger.exception(
            "Unhandled application error request_id=%s path=%s",
            getattr(request.state, "request_id", None),
            request.url.path,
            exc_info=(type(exception), exception, exception.__traceback__),
        )
        return error_response(
            request=request,
            status_code=500,
            error_code="internal_server_error",
            message="An unexpected server error occurred.",
        )
