import os
from dataclasses import dataclass
from datetime import timedelta

from expense_App.database import load_env_file


load_env_file()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Shared Expenses API")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    environment: str = os.getenv("APP_ENV", "development")
    api_v1_prefix: str = "/api/v1"
    docs_enabled: bool = os.getenv("DOCS_ENABLED", "true").lower() == "true"
    jwt_secret_key: str = os.getenv(
        "JWT_SECRET_KEY",
        "development-only-change-this-secret-before-deployment",
    )
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173",
        ).split(",")
        if origin.strip()
    )

    @property
    def access_token_expiry(self) -> timedelta:
        return timedelta(minutes=self.access_token_expire_minutes)


settings = Settings()
