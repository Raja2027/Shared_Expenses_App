from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from expense_App.config import settings
from expense_App.database import engine
from expense_App.exception import ServiceUnavailableException
from expense_App.logger import get_logger
from expense_App.schemas.health import LivenessResponse, ReadinessResponse


router = APIRouter()
logger = get_logger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Check whether the API process is running",
)
def liveness_check() -> LivenessResponse:
    return LivenessResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=utc_now(),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Check whether the API and database are ready",
)
def readiness_check() -> ReadinessResponse:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        logger.exception("PostgreSQL readiness check failed")
        raise ServiceUnavailableException(
            message="PostgreSQL is unavailable.",
            error_code="database_unavailable",
        ) from error

    return ReadinessResponse(
        status="ready",
        service=settings.app_name,
        database="connected",
        timestamp=utc_now(),
    )
