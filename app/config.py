"""Application configuration via environment variables."""

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Garage Management System"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # PostgreSQL
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "garage_system"

    def __init__(self, **kwargs):
        # Zeabur-compatible env var fallback chains.
        # Zeabur injects POSTGRES_PASSWORD (and similar) automatically,
        # but the field name may not match. We resolve the first available
        # env var for each credential and pass it as a keyword argument
        # (highest priority in pydantic-settings resolution order).
        if "DB_PASSWORD" not in kwargs:
            kwargs["DB_PASSWORD"] = (
                os.environ.get("DB_PASSWORD")
                or os.environ.get("POSTGRES_PASSWORD")
                or os.environ.get("PASSWORD")
                or "postgres"
            )
        if "DB_HOST" not in kwargs:
            kwargs["DB_HOST"] = (
                os.environ.get("DB_HOST")
                or os.environ.get("POSTGRES_HOST")
                or os.environ.get("POSTGRESQL_HOST")
                or "localhost"
            )
        if "DB_PORT" not in kwargs:
            kwargs["DB_PORT"] = int(
                os.environ.get("DB_PORT")
                or os.environ.get("POSTGRES_PORT")
                or "5432"
            )
        if "DB_USER" not in kwargs:
            kwargs["DB_USER"] = (
                os.environ.get("DB_USER")
                or os.environ.get("POSTGRES_USER")
                or os.environ.get("POSTGRES_USERNAME")
                or "postgres"
            )
        if "DB_NAME" not in kwargs:
            kwargs["DB_NAME"] = (
                os.environ.get("DB_NAME")
                or os.environ.get("POSTGRES_NAME")
                or os.environ.get("POSTGRESQL_NAME")
                or "postgres"
            )
        super().__init__(**kwargs)

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # JWT (for future auth extension)
    SECRET_KEY: str = "change-this-in-production-super-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Volcengine Ark AI
    VOLC_ARK_API_KEY: str = "ark-1b134190-ce8b-4aba-a0f7-b349445b8c2c-c8e9a"
    VOLC_ARK_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    VOLC_ARK_MODEL: str = "doubao-pro-32k-250528"
    AI_ENABLED: bool = True
    AI_CACHE_TTL_HOURS: int = 24
    AI_TEMPERATURE: float = 0.3
    AI_MAX_TOKENS: int = 4096

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
