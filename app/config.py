from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str  # postgresql+asyncpg://user:pass@host:port/db

    # Security / auth
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_SECURE: bool = True

    model_config = SettingsConfigDict(
        env_file=f"{Path(__file__).resolve().parent}/.env",  # откуда читать
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
