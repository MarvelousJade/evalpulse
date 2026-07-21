from typing import Any


def compare_aggregates(
    baseline: dict[str, Any], candidate: dict[str, Any], policy: dict[str, Any]
) -> tuple[bool, list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []

    allowed_drop = float(policy.get("max_pass_rate_drop", 0.02))
    baseline_pass = float(baseline.get("pass_rate", 0))
    candidate_pass = float(candidate.get("pass_rate", 0))
    minimum_pass = baseline_pass - allowed_drop
    checks.append(
        _check(
            "pass_rate",
            candidate_pass >= minimum_pass,
            candidate_pass,
            minimum_pass,
            "Candidate pass rate must remain within the allowed drop",
        )
    )

    critical_minimum = float(policy.get("critical_pass_rate", 1.0))
    critical_actual = float(candidate.get("critical_pass_rate", 1.0))
    checks.append(
        _check(
            "critical_pass_rate",
            critical_actual >= critical_minimum,
            critical_actual,
            critical_minimum,
            "Critical-tagged cases must meet the minimum pass rate",
        )
    )

    latency_increase = float(policy.get("max_p95_latency_increase", 0.20))
    baseline_p95 = float(baseline.get("p95_latency_ms", 0))
    candidate_p95 = float(candidate.get("p95_latency_ms", 0))
    maximum_p95 = baseline_p95 * (1 + latency_increase) if baseline_p95 else candidate_p95
    checks.append(
        _check(
            "p95_latency",
            candidate_p95 <= maximum_p95,
            candidate_p95,
            maximum_p95,
            "Candidate P95 latency must remain within the allowed increase",
        )
    )

    maximum_errors = float(policy.get("max_provider_error_rate", 0.01))
    error_rate = float(candidate.get("provider_error_rate", 0))
    checks.append(
        _check(
            "provider_error_rate",
            error_rate <= maximum_errors,
            error_rate,
            maximum_errors,
            "Provider error rate must stay below the configured maximum",
        )
    )
    return all(check["passed"] for check in checks), checks


def _check(name: str, passed: bool, actual: float, threshold: float, rule: str) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "actual": round(actual, 6),
        "threshold": round(threshold, 6),
        "explanation": f"{rule}: actual={actual:.4f}, threshold={threshold:.4f}",
    }
