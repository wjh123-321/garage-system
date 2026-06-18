"""Application configuration via environment variables."""

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Garage Management System"
    APP_VERSION: str = "0.3.1"
    DEBUG: bool = False

    @property
    def DATABASE_URL(self) -> str:
        DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(DB_DIR, exist_ok=True)
        return f"sqlite:///{os.path.join(DB_DIR, 'garage.db')}"

    # JWT (for future auth extension)
    SECRET_KEY: str = "change-this-in-production-super-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # Volcengine Ark AI
    VOLC_ARK_API_KEY: str = "ark-1b134190-ce8b-4aba-a0f7-b349445b8c2c-c8e9a"
    VOLC_ARK_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    VOLC_ARK_MODEL: str = "doubao-pro-32k-250528"
    AI_ENABLED: bool = True
    AI_CACHE_TTL_HOURS: int = 24
    AI_TEMPERATURE: float = 0.3
    AI_MAX_TOKENS: int = 4096

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
