"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Garage Management System"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # PostgreSQL — 支持 Zeabur Postgres 插件自动注入 (POSTGRES_*) 和手动配置 (DB_*)
    DB_HOST: str = ""
    DB_PORT: int = 5432
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_NAME: str = ""

    # Zeabur 自动注入的变量（优先级高于 DB_*）
    POSTGRES_HOST: str = ""
    POSTGRES_PORT: str = ""
    POSTGRES_USERNAME: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DATABASE: str = ""

    @property
    def DATABASE_URL(self) -> str:
        host = self.POSTGRES_HOST or self.DB_HOST or "localhost"
        port = int(self.POSTGRES_PORT or self.DB_PORT or 5432)
        user = self.POSTGRES_USERNAME or self.DB_USER or "postgres"
        password = self.POSTGRES_PASSWORD or self.DB_PASSWORD or "postgres"
        database = self.POSTGRES_DATABASE or self.DB_NAME or "garage_system"
        return (
            f"postgresql://{user}:{password}"
            f"@{host}:{port}/{database}"
            f"?connect_timeout=5"
        )

    # JWT (for future auth extension)
    SECRET_KEY: str = "change-this-in-production-super-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Volcengine Ark AI
    VOLC_ARK_API_KEY: str = ""
    VOLC_ARK_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    VOLC_ARK_MODEL: str = "doubao-pro-32k-250528"
    AI_ENABLED: bool = True
    AI_CACHE_TTL_HOURS: int = 24
    AI_TEMPERATURE: float = 0.3
    AI_MAX_TOKENS: int = 4096

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
