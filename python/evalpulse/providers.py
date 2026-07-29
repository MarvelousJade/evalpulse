import json
import time
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .config import Settings, get_settings


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


@dataclass(frozen=True)
class GeminiGeneration:
    text: str
    content: dict[str, Any]
    function_calls: list[dict[str, Any]]
    input_tokens: int
    output_tokens: int
    metadata: dict[str, Any]


class GeminiClient:
    """Minimal Gemini REST client with a fixed origin and bounded request timeout."""

    api_origin = "https://generativelanguage.googleapis.com"

    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        if not api_key:
            raise PermanentProviderError("Gemini is not configured")
        self._api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        *,
        contents: list[dict[str, Any]],
        system_instruction: str,
        max_output_tokens: int,
        tools: list[dict[str, Any]] | None = None,
        tool_config: dict[str, Any] | None = None,
        json_schema: dict[str, Any] | None = None,
    ) -> GeminiGeneration:
        payload: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_output_tokens},
        }
        if tools:
            payload["tools"] = tools
        if tool_config:
            payload["toolConfig"] = tool_config
        if json_schema:
            payload["generationConfig"].update(
                {"responseMimeType": "application/json", "responseSchema": json_schema}
            )
        raw = self._send(payload)
        candidates = raw.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            blocked = raw.get("promptFeedback", {}).get("blockReason", "unknown reason")
            raise PermanentProviderError(f"Gemini returned no candidate ({blocked})")
        candidate = candidates[0]
        content = candidate.get("content", {})
        parts = content.get("parts", []) if isinstance(content, dict) else []
        text_parts: list[str] = []
        function_calls: list[dict[str, Any]] = []
        for part in parts:
            if not isinstance(part, dict):
                continue
            if isinstance(part.get("text"), str):
                text_parts.append(part["text"])
            if isinstance(part.get("functionCall"), dict):
                function_calls.append(part["functionCall"])
        usage = raw.get("usageMetadata", {})
        return GeminiGeneration(
            text="".join(text_parts).strip(),
            content=content if isinstance(content, dict) else {"role": "model", "parts": []},
            function_calls=function_calls,
            input_tokens=int(usage.get("promptTokenCount", 0)),
            output_tokens=int(usage.get("candidatesTokenCount", 0)),
            metadata={
                "provider": "gemini",
                "model": self.model,
                "model_version": raw.get("modelVersion"),
                "response_id": raw.get("responseId"),
                "finish_reason": candidate.get("finishReason"),
            },
        )

    def _send(self, payload: dict[str, Any]) -> dict[str, Any]:
        model = quote(self.model, safe="-._")
        url = f"{self.api_origin}/v1beta/models/{model}:generateContent"
        request = Request(
            url,
            data=json.dumps(payload, separators=(",", ":")).encode(),
            headers={"Content-Type": "application/json", "x-goog-api-key": self._api_key},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                decoded = json.load(response)
        except HTTPError as exc:
            message = _provider_http_error(exc)
            if exc.code in {408, 409, 429} or exc.code >= 500:
                raise TemporaryProviderError(message) from exc
            raise PermanentProviderError(message) from exc
        except (TimeoutError, URLError) as exc:
            raise TemporaryProviderError(f"Gemini request failed: {type(exc).__name__}") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TemporaryProviderError("Gemini returned an invalid JSON response") from exc
        if not isinstance(decoded, dict):
            raise TemporaryProviderError("Gemini returned an unexpected response")
        return decoded


class GeminiProvider:
    def __init__(self, client: GeminiClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings

    def evaluate(self, request: ProviderRequest) -> ProviderResponse:
        input_text = _to_text(request.input)
        request_chars = len(request.prompt) + len(input_text)
        if request_chars > self.settings.llm_max_input_chars:
            raise PermanentProviderError(
                f"Gemini input exceeds {self.settings.llm_max_input_chars} characters"
            )
        started = time.perf_counter()
        generation = self.client.generate(
            contents=[{"role": "user", "parts": [{"text": input_text}]}],
            system_instruction=request.prompt,
            max_output_tokens=self.settings.llm_max_output_tokens,
        )
        return ProviderResponse(
            output=generation.text,
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
            input_tokens=generation.input_tokens,
            output_tokens=generation.output_tokens,
            metadata=generation.metadata,
        )


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
    if name == "gemini":
        settings = get_settings()
        if not settings.llm_configured:
            raise PermanentProviderError(
                "Gemini is disabled; set LLM_ENABLED=true and GEMINI_API_KEY on the server"
            )
        client = GeminiClient(
            settings.gemini_api_key.get_secret_value(),
            settings.gemini_model,
            settings.llm_request_timeout_seconds,
        )
        return GeminiProvider(client, settings)
    raise PermanentProviderError(f"Unsupported provider: {name}")


def _provider_http_error(exc: HTTPError) -> str:
    try:
        payload = json.loads(exc.read(4_096).decode(errors="replace"))
        detail = payload.get("error", {}).get("message")
        if isinstance(detail, str):
            return f"Gemini request failed ({exc.code}): {detail[:300]}"
    except (AttributeError, json.JSONDecodeError):
        pass
    return f"Gemini request failed with HTTP {exc.code}"
