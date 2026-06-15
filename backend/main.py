from contextlib import asynccontextmanager

from fastapi import FastAPI

from expense_App.api.router import api_router
from expense_App.config import settings
from expense_App.exception.handlers import register_exception_handlers
from expense_App.logger import get_logger
from expense_App.middleware import register_middleware


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s version=%s environment=%s",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )
    yield
    logger.info("Stopping %s", settings.app_name)


def create_app() -> FastAPI:
    docs_url = "/docs" if settings.docs_enabled else None
    redoc_url = "/redoc" if settings.docs_enabled else None
    openapi_url = "/openapi.json" if settings.docs_enabled else None

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )
    register_middleware(app)
    register_exception_handlers(app)
    app.include_router(api_router)

    @app.get("/", tags=["Root"], include_in_schema=False)
    def root() -> dict:
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "health": f"{settings.api_v1_prefix}/health/ready",
            "docs": docs_url,
        }

    return app


app = create_app()
