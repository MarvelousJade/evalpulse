import json

import pytest
from evalpulse.comparisons import compare_aggregates
from evalpulse.datasets import DatasetValidationError, parse_dataset
from evalpulse.evaluators import evaluate_output
from evalpulse.providers import MockProvider, ProviderRequest, TemporaryProviderError


def test_all_deterministic_evaluators() -> None:
    output = json.dumps({"answer": "Hello world", "count": 2})
    specs = [
        {"type": "contains_all", "options": {"phrases": ["Hello", "world"]}},
        {"type": "regex", "options": {"pattern": "Hello.*world"}},
        {"type": "valid_json", "options": {}},
        {"type": "required_json_keys", "options": {"keys": ["answer", "count"]}},
        {
            "type": "json_schema",
            "options": {
                "schema": {
                    "type": "object",
                    "required": ["answer"],
                    "properties": {"answer": {"type": "string"}},
                }
            },
        },
        {"type": "max_latency", "options": {"milliseconds": 20}},
    ]
    scores = evaluate_output(output, None, 19.999, specs)
    assert all(score.passed for score in scores)


def test_exact_match_boundaries() -> None:
    exact = evaluate_output("Hello", "hello", 0, [{"type": "exact_match", "options": {}}])
    folded = evaluate_output(
        "Hello", "hello", 0, [{"type": "case_insensitive_exact_match", "options": {}}]
    )
    assert exact[0].passed is False
    assert folded[0].passed is True


def test_dataset_parses_json_and_rejects_invalid_shape() -> None:
    parsed = parse_dataset(
        '[{"input":{"text":"yes"},"expected":"yes","tags":["critical"]}]',
        "json",
        10_000,
        10,
    )
    assert parsed.schema == {"input_fields": ["text"], "case_count": 1}
    assert len(parsed.digest) == 64
    with pytest.raises(DatasetValidationError, match="must be an array"):
        parse_dataset('{"input": {}}', "json", 10_000, 10)


def test_mock_provider_is_deterministic_and_classifies_failures() -> None:
    provider = MockProvider()
    request = ProviderRequest("[uppercase]", {"text": "hello"}, {})
    first = provider.evaluate(request)
    second = provider.evaluate(request)
    assert first.output == second.output == "HELLO"
    with pytest.raises(TemporaryProviderError):
        provider.evaluate(ProviderRequest("", {"mock_behavior": "temporary_error"}, {}))


def test_regression_checks_explain_each_threshold() -> None:
    baseline = {
        "pass_rate": 1.0,
        "critical_pass_rate": 1.0,
        "p95_latency_ms": 100,
        "provider_error_rate": 0,
    }
    candidate = {
        "pass_rate": 0.8,
        "critical_pass_rate": 0.5,
        "p95_latency_ms": 130,
        "provider_error_rate": 0.02,
    }
    passed, checks = compare_aggregates(baseline, candidate, {})
    assert passed is False
    assert {check["name"] for check in checks} == {
        "pass_rate",
        "critical_pass_rate",
        "p95_latency",
        "provider_error_rate",
    }
    assert all("actual=" in check["explanation"] for check in checks)
