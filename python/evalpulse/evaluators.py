import json
import re
from dataclasses import dataclass
from typing import Any

from jsonschema import ValidationError, validate


@dataclass(frozen=True)
class Score:
    name: str
    passed: bool
    value: float | None
    explanation: str


def evaluate_output(
    output: Any, expected: Any, latency_ms: float, specs: list[dict[str, Any]]
) -> list[Score]:
    return [_evaluate(output, expected, latency_ms, spec) for spec in specs]


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _as_json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _evaluate(output: Any, expected: Any, latency_ms: float, spec: dict[str, Any]) -> Score:
    name = spec["type"]
    options = spec.get("options", {})
    if name == "exact_match":
        passed = output == expected
        return Score(
            name,
            passed,
            float(passed),
            "Output exactly matches expected value"
            if passed
            else "Output differs from expected value",
        )
    if name == "case_insensitive_exact_match":
        passed = _as_text(output).casefold() == _as_text(expected).casefold()
        return Score(
            name,
            passed,
            float(passed),
            "Case-insensitive values match" if passed else "Case-insensitive values differ",
        )
    if name == "contains_all":
        phrases = options.get("phrases", expected if isinstance(expected, list) else [expected])
        missing = [str(phrase) for phrase in phrases if str(phrase) not in _as_text(output)]
        return Score(
            name,
            not missing,
            float(not missing),
            "All required phrases found"
            if not missing
            else f"Missing phrases: {', '.join(missing)}",
        )
    if name == "regex":
        pattern = str(options.get("pattern", expected))
        try:
            passed = re.search(pattern, _as_text(output)) is not None
            explanation = f"Output {'matches' if passed else 'does not match'} /{pattern}/"
        except re.error as exc:
            passed, explanation = False, f"Invalid regular expression: {exc}"
        return Score(name, passed, float(passed), explanation)
    if name == "valid_json":
        try:
            _as_json(output)
            return Score(name, True, 1.0, "Output is valid JSON")
        except (json.JSONDecodeError, TypeError):
            return Score(name, False, 0.0, "Output is not valid JSON")
    if name == "json_schema":
        try:
            validate(_as_json(output), options.get("schema", {}))
            return Score(name, True, 1.0, "Output satisfies the JSON Schema")
        except (json.JSONDecodeError, TypeError, ValidationError) as exc:
            reason = exc.message if isinstance(exc, ValidationError) else str(exc)
            return Score(
                name,
                False,
                0.0,
                f"JSON Schema validation failed: {reason}",
            )
    if name == "required_json_keys":
        keys = options.get("keys", [])
        try:
            parsed = _as_json(output)
            missing = [key for key in keys if not isinstance(parsed, dict) or key not in parsed]
        except (json.JSONDecodeError, TypeError):
            missing = list(keys)
        return Score(
            name,
            not missing,
            float(not missing),
            "All required keys found" if not missing else f"Missing keys: {', '.join(missing)}",
        )
    if name == "max_latency":
        maximum = float(options.get("milliseconds", 1000))
        passed = latency_ms <= maximum
        return Score(
            name,
            passed,
            latency_ms,
            f"Latency {latency_ms:.2f}ms {'is within' if passed else 'exceeds'} {maximum:.2f}ms",
        )
    raise ValueError(f"Unsupported evaluator: {name}")
