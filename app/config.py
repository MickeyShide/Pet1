from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DEBUG: bool = False
    APP_ENV: str = "local"

    # Database
    DATABASE_URL: str  # postgresql+asyncpg://user:pass@host:port/db
    SQL_ECHO: bool = False

    # Security / auth
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_SECURE: bool = True
    CORS_ALLOW_ORIGINS: list[str] = ['https://itouch-pet-project.ru.tuna.am']
    CORS_ALLOW_ORIGIN_REGEX: str | None = r"http://localhost:\d+$"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_CACHE_PREFIX: str = "myapp:cache:"

    # RabbitMQ / Celery
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # S3 / MinIO
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_PUBLIC_BASE_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "uploads"
    S3_PUBLIC_BUCKET: str | None = None
    S3_REGION: str = "us-east-1"
    S3_PRESIGN_EXPIRES_SECONDS: int = 900
    S3_MAX_UPLOAD_BYTES_PROXY: int = 50 * 1024 * 1024
    S3_MAX_UPLOAD_BYTES_PRESIGNED: int = 2 * 1024 * 1024 * 1024
    FILES_ALLOWED_CONTENT_TYPES: str = "image/jpeg,image/png,application/pdf"

    # Domain settings
    BOOKING_EXPIRE_SECONDS: int = 20
    LOCATION_CACHE_TTL_SECONDS: int = 6
    TIMESLOT_CACHE_TTL_SECONDS: int = 30
    API_GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS: int = 25
    API_SHUTDOWN_RETRY_AFTER_SECONDS: int = 15

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug_flag(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"debug", "dev", "development"}:
                return True
        return value

    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).resolve().parent.parent / ".env",  # project root
            Path(__file__).resolve().parent / ".env",  # legacy location
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def files_allowed_content_types(self) -> set[str]:
        raw = self.FILES_ALLOWED_CONTENT_TYPES
        if not raw:
            return set()
        return {item.strip() for item in raw.split(",") if item.strip()}

    @property
    def s3_public_bucket(self) -> str:
        return self.S3_PUBLIC_BUCKET or self.S3_BUCKET


settings = Settings()
