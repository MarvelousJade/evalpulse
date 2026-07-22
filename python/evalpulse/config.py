from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "EvalPulse"
    environment: str = "development"
    database_url: str = "sqlite:///./evalpulse.db"
    redis_url: str = "redis://localhost:6379/0"
    session_secret: str = "development-only-change-me-please"
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:3000"
    session_max_age_seconds: int = 60 * 60 * 12
    summary_cache_ttl_seconds: int = 30
    max_dataset_bytes: int = 1_000_000
    max_dataset_rows: int = 2_000

    @field_validator("database_url")
    @classmethod
    def select_psycopg_driver(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
