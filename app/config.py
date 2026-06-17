import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Garage Management System"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    DB_HOST: str = os.environ.get("DB_HOST") or "postgresql"
    DB_PORT: int = int(os.environ.get("DB_PORT") or "5432")
    DB_USER: str = os.environ.get("DB_USER") or os.environ.get("POSTGRES_USER") or "postgres"
    DB_PASSWORD: str = os.environ.get("DB_PASSWORD") or os.environ.get("POSTGRES_PASSWORD") or os.environ.get("PASSWORD") or "postgres"
    DB_NAME: str = os.environ.get("DB_NAME") or "postgres"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    SECRET_KEY: str = "change-this-in-production-super-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    CORS_ORIGINS: list[str] = ["*"]
    VOLC_ARK_API_KEY: str = "ark-1b134190-ce8b-4aba-a0f7-b349445b8c2c-c8e9a"
    VOLC_ARK_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    VOLC_ARK_MODEL: str = "doubao-pro-32k-250528"
    AI_ENABLED: bool = True
    AI_CACHE_TTL_HOURS: int = 24
    AI_TEMPERATURE: float = 0.3
    AI_MAX_TOKENS: int = 4096
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
