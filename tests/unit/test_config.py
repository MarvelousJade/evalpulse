import pytest
from evalpulse.config import Settings
from evalpulse.schemas import RunCreate
from pydantic import ValidationError


def test_render_postgres_url_selects_psycopg_driver() -> None:
    settings = Settings(database_url="postgresql://user:password@database/evalpulse")
    assert settings.database_url == "postgresql+psycopg://user:password@database/evalpulse"


def test_live_model_is_server_allow_listed() -> None:
    with pytest.raises(ValidationError, match="gemini_model"):
        Settings(gemini_model="gemini-expensive-model")


def test_client_cannot_override_live_model_or_token_cap() -> None:
    with pytest.raises(ValidationError, match="server-controlled"):
        RunCreate(
            prompt_version_id="prompt",
            dataset_version_id="dataset",
            provider="gemini",
            provider_config={"model": "expensive", "max_output_tokens": 100_000},
            evaluators=[{"type": "exact_match", "options": {}}],
        )
