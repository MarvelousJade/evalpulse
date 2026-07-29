from functools import lru_cache

from pydantic import SecretStr, field_validator
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
    llm_enabled: bool = False
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.5-flash-lite"
    llm_request_timeout_seconds: float = 20.0
    llm_max_input_chars: int = 12_000
    llm_max_output_tokens: int = 256
    llm_diagnosis_max_output_tokens: int = 600
    llm_max_cases_per_run: int = 20
    llm_daily_request_limit: int = 100
    llm_daily_diagnosis_limit: int = 20
    llm_diagnosis_max_failures: int = 10
    rag_top_k: int = 3
    rag_knowledge_dir: str = "docs/knowledge"

    @field_validator("database_url")
    @classmethod
    def select_psycopg_driver(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value

    @field_validator("gemini_model")
    @classmethod
    def restrict_gemini_model(cls, value: str) -> str:
        # The model is deliberately allow-listed so a browser request cannot select
        # a much more expensive model. Update this list intentionally with pricing.
        allowed = {"gemini-3.5-flash-lite"}
        if value not in allowed:
            raise ValueError(f"gemini_model must be one of: {', '.join(sorted(allowed))}")
        return value

    @property
    def llm_configured(self) -> bool:
        return self.llm_enabled and bool(self.gemini_api_key.get_secret_value())

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
