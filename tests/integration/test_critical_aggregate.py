import pytest
from evalpulse.comparisons import compare_aggregates
from evalpulse.database import SessionLocal
from evalpulse.engine import execute_run
from fastapi.testclient import TestClient

from tests.helpers import create_mock_run


@pytest.mark.parametrize("critical_passes", [True, False])
def test_critical_policy_uses_only_critical_cases(
    authenticated_client: tuple[TestClient, dict[str, str]], critical_passes: bool
) -> None:
    client, csrf = authenticated_client
    critical_response = "steady" if critical_passes else "STEADY"
    ordinary_responses = ["READY", "VERIFIED"] if critical_passes else ["ready", "verified"]
    run = create_mock_run(
        client,
        csrf,
        [
            {
                "input": {"mock_response": critical_response},
                "expected": critical_response,
                "tags": ["critical"],
            },
            *[
                {"input": {"mock_response": response}, "expected": response, "tags": []}
                for response in ordinary_responses
            ],
        ],
        prompt_text="[lowercase] Return response",
    )
    with SessionLocal() as db:
        assert execute_run(db, run["id"]) == "completed"
    response = client.get(f"/api/runs/{run['id']}")
    assert response.status_code == 200
    aggregate = response.json()["aggregate"]
    assert aggregate["total"] == 3
    assert aggregate["completed"] == 3
    assert aggregate["pass_rate"] == pytest.approx((1 if critical_passes else 2) / 3)
    assert aggregate["critical_pass_rate"] == float(critical_passes)

    # Synthetic policy control: hold latency/error evidence equal to isolate the critical gate.
    baseline = {**aggregate, "pass_rate": 1.0, "critical_pass_rate": 1.0}
    passed, checks = compare_aggregates(baseline, aggregate, {"max_pass_rate_drop": 1.0})
    critical_check = next(check for check in checks if check["name"] == "critical_pass_rate")
    assert critical_check["passed"] is critical_passes
    assert passed is critical_passes
