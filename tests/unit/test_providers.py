from typing import Any

import pytest
from evalpulse.config import Settings
from evalpulse.providers import (
    GeminiClient,
    GeminiGeneration,
    GeminiProvider,
    PermanentProviderError,
    ProviderRequest,
)


def test_gemini_client_normalizes_text_function_calls_and_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = GeminiClient("secret", "gemini-3.5-flash-lite", 2)
    captured: dict[str, Any] = {}

    def fake_send(payload: dict[str, Any]) -> dict[str, Any]:
        captured.update(payload)
        return {
            "candidates": [
                {
                    "content": {
                        "role": "model",
                        "parts": [
                            {"text": "hello"},
                            {"functionCall": {"name": "inspect", "args": {}}},
                        ],
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {"promptTokenCount": 4, "candidatesTokenCount": 2},
            "modelVersion": "test-version",
        }

    monkeypatch.setattr(client, "_send", fake_send)
    response = client.generate(
        contents=[{"role": "user", "parts": [{"text": "hi"}]}],
        system_instruction="Be concise",
        max_output_tokens=12,
    )

    assert response.text == "hello"
    assert response.function_calls == [{"name": "inspect", "args": {}}]
    assert (response.input_tokens, response.output_tokens) == (4, 2)
    assert captured["generationConfig"]["maxOutputTokens"] == 12


class FakeGeminiClient:
    def generate(self, **_: Any) -> GeminiGeneration:
        return GeminiGeneration(
            text="APPROVED",
            content={"role": "model", "parts": [{"text": "APPROVED"}]},
            function_calls=[],
            input_tokens=8,
            output_tokens=1,
            metadata={"provider": "gemini", "model": "gemini-3.5-flash-lite"},
        )


def test_gemini_provider_uses_server_token_cap_and_reports_usage() -> None:
    settings = Settings(llm_max_output_tokens=17)
    provider = GeminiProvider(FakeGeminiClient(), settings)  # type: ignore[arg-type]

    response = provider.evaluate(
        ProviderRequest(prompt="Return the answer", input={"answer": "APPROVED"}, config={})
    )

    assert response.output == "APPROVED"
    assert response.input_tokens == 8
    assert response.output_tokens == 1
    assert response.metadata["model"] == "gemini-3.5-flash-lite"


def test_gemini_provider_rejects_oversized_input_before_network_call() -> None:
    settings = Settings(llm_max_input_chars=10)
    provider = GeminiProvider(FakeGeminiClient(), settings)  # type: ignore[arg-type]

    with pytest.raises(PermanentProviderError, match="exceeds"):
        provider.evaluate(ProviderRequest(prompt="long prompt", input={"x": "long"}, config={}))
