import json

from evalpulse.database import SessionLocal
from evalpulse.engine import execute_run
from evalpulse.models import EvaluationResult, RunEvent
from fastapi.testclient import TestClient


def post(
    client: TestClient, path: str, payload: dict[str, object], headers: dict[str, str]
) -> dict[str, object]:
    response = client.post(path, json=payload, headers=headers)
    assert response.status_code in {200, 201, 202}, response.text
    return response.json()


def test_complete_authorized_regression_workflow(
    authenticated_client: tuple[TestClient, dict[str, str]],
) -> None:
    client, csrf = authenticated_client
    project = post(
        client,
        "/api/projects",
        {"name": "Support quality", "description": "Regression suite"},
        csrf,
    )
    prompt = post(
        client,
        f"/api/projects/{project['id']}/prompts",
        {"name": "Responder", "text": "Return the supplied response", "variables": []},
        csrf,
    )
    baseline_version = prompt["versions"][0]
    candidate_version = post(
        client,
        f"/api/prompts/{prompt['id']}/versions",
        {"text": "[lowercase] Return the supplied response", "variables": []},
        csrf,
    )
    dataset = post(
        client,
        f"/api/projects/{project['id']}/datasets",
        {"name": "Critical greetings"},
        csrf,
    )
    content = json.dumps(
        [
            {"input": {"mock_response": "HELLO"}, "expected": "HELLO", "tags": ["critical"]},
            {"input": {"mock_response": "WORLD"}, "expected": "WORLD", "tags": []},
        ]
    )
    dataset_version = post(
        client,
        f"/api/datasets/{dataset['id']}/versions",
        {"format": "json", "content": content},
        csrf,
    )

    run_payload = {
        "dataset_version_id": dataset_version["id"],
        "provider": "mock",
        "provider_config": {},
        "evaluators": [{"type": "exact_match", "options": {}}],
    }
    baseline = post(
        client,
        f"/api/projects/{project['id']}/runs",
        {**run_payload, "prompt_version_id": baseline_version["id"]},
        {**csrf, "Idempotency-Key": "baseline-workflow"},
    )
    duplicate = post(
        client,
        f"/api/projects/{project['id']}/runs",
        {**run_payload, "prompt_version_id": baseline_version["id"]},
        {**csrf, "Idempotency-Key": "baseline-workflow"},
    )
    assert duplicate["id"] == baseline["id"]
    candidate = post(
        client,
        f"/api/projects/{project['id']}/runs",
        {**run_payload, "prompt_version_id": candidate_version["id"]},
        {**csrf, "Idempotency-Key": "candidate-workflow"},
    )

    with SessionLocal() as db:
        assert execute_run(db, str(baseline["id"])) == "completed"
        assert execute_run(db, str(baseline["id"])) == "completed"
        assert execute_run(db, str(candidate["id"])) == "completed"
        assert db.query(EvaluationResult).filter_by(run_id=baseline["id"]).count() == 2
        assert db.query(RunEvent).filter_by(run_id=baseline["id"]).count() >= 4

    baseline_response = client.get(f"/api/runs/{baseline['id']}")
    candidate_response = client.get(f"/api/runs/{candidate['id']}")
    assert baseline_response.json()["aggregate"]["pass_rate"] == 1.0
    assert candidate_response.json()["aggregate"]["pass_rate"] == 0.0

    comparison = post(
        client,
        f"/api/projects/{project['id']}/comparisons",
        {"baseline_run_id": baseline["id"], "candidate_run_id": candidate["id"]},
        csrf,
    )
    assert comparison["passed"] is False
    assert any(not check["passed"] for check in comparison["checks"])


def test_authentication_csrf_and_dataset_validation(client: TestClient) -> None:
    assert client.get("/api/projects").status_code == 401
    login = client.post(
        "/api/auth/login",
        json={"email": "demo@evalpulse.local", "password": "evalpulse-demo"},
    )
    assert login.status_code == 200
    assert client.post("/api/projects", json={"name": "Blocked"}).status_code == 403
    csrf = {"X-CSRF-Token": client.cookies["evalpulse_csrf"]}
    project = post(client, "/api/projects", {"name": "Validation"}, csrf)
    dataset = post(
        client,
        f"/api/projects/{project['id']}/datasets",
        {"name": "Broken"},
        csrf,
    )
    invalid = client.post(
        f"/api/datasets/{dataset['id']}/versions",
        json={"format": "json", "content": "{}"},
        headers=csrf,
    )
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "invalid_dataset"
