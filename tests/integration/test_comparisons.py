import json
from typing import Any

import pytest
from evalpulse.database import SessionLocal
from evalpulse.engine import execute_run
from evalpulse.models import Comparison
from fastapi.testclient import TestClient

from tests.helpers import post


@pytest.mark.parametrize("difference", ["dataset", "evaluator_type", "evaluator_options", None])
def test_comparison_requires_the_same_workload_and_scoring(
    authenticated_client: tuple[TestClient, dict[str, str]], difference: str | None
) -> None:
    client, csrf = authenticated_client
    project = post(client, "/api/projects", {"name": "Comparable runs"}, csrf)
    prompt = post(
        client,
        f"/api/projects/{project['id']}/prompts",
        {"name": "Responder", "text": "Return the supplied response", "variables": []},
        csrf,
    )
    candidate_prompt = post(
        client,
        f"/api/prompts/{prompt['id']}/versions",
        {"text": "[lowercase] Return the supplied response", "variables": []},
        csrf,
    )
    dataset = post(client, f"/api/projects/{project['id']}/datasets", {"name": "Greetings"}, csrf)

    def import_version(response: str) -> str:
        version = post(
            client,
            f"/api/datasets/{dataset['id']}/versions",
            {
                "format": "json",
                "content": json.dumps(
                    [{"input": {"mock_response": response}, "expected": response}]
                ),
            },
            csrf,
        )
        return str(version["id"])

    baseline_dataset = import_version("HELLO")
    candidate_dataset = import_version("hello") if difference == "dataset" else baseline_dataset
    baseline_evaluators: list[dict[str, Any]] = [{"type": "exact_match", "options": {}}]
    candidate_evaluators = baseline_evaluators
    if difference == "evaluator_type":
        candidate_evaluators = [{"type": "case_insensitive_exact_match", "options": {}}]
    elif difference == "evaluator_options":
        baseline_evaluators = [{"type": "regex", "options": {"pattern": "^HELLO$"}}]
        candidate_evaluators = [{"type": "regex", "options": {"pattern": "^hello$"}}]

    def queue_run(prompt_id: str, dataset_id: str, evaluators: list[dict[str, Any]]) -> str:
        run = post(
            client,
            f"/api/projects/{project['id']}/runs",
            {
                "prompt_version_id": prompt_id,
                "dataset_version_id": dataset_id,
                "provider": "mock",
                "provider_config": {},
                "evaluators": evaluators,
            },
            {**csrf, "Idempotency-Key": prompt_id},
        )
        return str(run["id"])

    baseline_id = queue_run(prompt["versions"][0]["id"], baseline_dataset, baseline_evaluators)
    candidate_id = queue_run(candidate_prompt["id"], candidate_dataset, candidate_evaluators)
    with SessionLocal() as db:
        assert execute_run(db, baseline_id) == "completed"
        assert execute_run(db, candidate_id) == "completed"

    baseline = client.get(f"/api/runs/{baseline_id}").json()
    candidate = client.get(f"/api/runs/{candidate_id}").json()
    assert baseline["aggregate"]["pass_rate"] == 1.0
    assert candidate["aggregate"]["pass_rate"] == (0.0 if difference is None else 1.0)

    response = client.post(
        f"/api/projects/{project['id']}/comparisons",
        json={"baseline_run_id": baseline_id, "candidate_run_id": candidate_id},
        headers=csrf,
    )
    if difference is None:
        assert response.status_code == 201, response.text
        assert response.json()["passed"] is False
    else:
        assert response.status_code == 422, response.text
        expected = (
            "Runs must use the same dataset version"
            if difference == "dataset"
            else "Runs must use the same evaluator definitions"
        )
        assert response.json()["detail"] == expected
    with SessionLocal() as db:
        assert db.query(Comparison).count() == (1 if difference is None else 0)
