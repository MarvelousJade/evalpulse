import json
import time
from dataclasses import dataclass
from typing import Any, Protocol


class TemporaryProviderError(RuntimeError):
    pass


class PermanentProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderRequest:
    prompt: str
    input: dict[str, Any]
    config: dict[str, Any]


@dataclass(frozen=True)
class ProviderResponse:
    output: Any
    latency_ms: float
    input_tokens: int
    output_tokens: int
    metadata: dict[str, Any]


class Provider(Protocol):
    def evaluate(self, request: ProviderRequest) -> ProviderResponse: ...


class MockProvider:
    """A deterministic adapter with explicit fixtures for retries and regressions."""

    def evaluate(self, request: ProviderRequest) -> ProviderResponse:
        started = time.perf_counter()
        behavior = request.input.get("mock_behavior", request.config.get("behavior"))
        if behavior == "temporary_error":
            raise TemporaryProviderError("Configured temporary provider failure")
        if behavior == "permanent_error":
            raise PermanentProviderError("Configured permanent provider failure")
        delay_ms = min(float(request.input.get("mock_latency_ms", 0)), 2_000)
        if delay_ms:
            time.sleep(delay_ms / 1000)
        output = request.input.get("mock_response", request.input.get("text", request.input))
        if "[uppercase]" in request.prompt:
            output = _to_text(output).upper()
        if "[lowercase]" in request.prompt:
            output = _to_text(output).lower()
        if "[json]" in request.prompt and not isinstance(output, str):
            output = json.dumps(output, sort_keys=True)
        if "[invalid-json]" in request.prompt:
            output = "{invalid"
        latency_ms = (time.perf_counter() - started) * 1000
        prompt_tokens = len(request.prompt.split()) + len(_to_text(request.input).split())
        output_tokens = len(_to_text(output).split())
        return ProviderResponse(
            output=output,
            latency_ms=round(latency_ms, 3),
            input_tokens=prompt_tokens,
            output_tokens=output_tokens,
            metadata={"provider": "mock", "deterministic": True},
        )


def _to_text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True)


def get_provider(name: str) -> Provider:
    if name == "mock":
        return MockProvider()
    raise PermanentProviderError(f"Unsupported provider: {name}")
