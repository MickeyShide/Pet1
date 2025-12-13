from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str  # postgresql+asyncpg://user:pass@host:port/db
    SQL_ECHO: bool = False

    # Security / auth
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_SECURE: bool = True
    CORS_ALLOW_ORIGINS: list[str] = []
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

    # Domain settings
    BOOKING_EXPIRE_SECONDS: int = 20
    LOCATION_CACHE_TTL_SECONDS: int = 6
    TIMESLOT_CACHE_TTL_SECONDS: int = 30

    model_config = SettingsConfigDict(
        env_file=f"{Path(__file__).resolve().parent}/.env",  # откуда читать
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
