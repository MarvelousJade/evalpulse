import json
from typing import Any

import pytest
from evalpulse.config import Settings
from evalpulse.database import SessionLocal
from evalpulse.diagnostics import diagnose_failed_run, inspect_failed_evaluations
from evalpulse.engine import execute_run
from evalpulse.providers import GeminiGeneration
from fastapi.testclient import TestClient


def post(client: TestClient, path: str, body: dict[str, Any], csrf: dict[str, str]) -> Any:
    response = client.post(path, json=body, headers=csrf)
    assert response.status_code < 400, response.text
    return response.json()


def failed_run(client: TestClient, csrf: dict[str, str]) -> str:
    project = post(client, "/api/projects", {"name": "Diagnosis"}, csrf)
    prompt = post(
        client,
        f"/api/projects/{project['id']}/prompts",
        {"name": "Responder", "text": "Return answer", "variables": []},
        csrf,
    )
    dataset = post(
        client,
        f"/api/projects/{project['id']}/datasets",
        {"name": "Failures"},
        csrf,
    )
    version = post(
        client,
        f"/api/datasets/{dataset['id']}/versions",
        {
            "format": "json",
            "content": json.dumps(
                [
                    {
                        "input": {"mock_response": "actual"},
                        "expected": "expected",
                        "tags": ["critical"],
                    }
                ]
            ),
        },
        csrf,
    )
    run = post(
        client,
        f"/api/projects/{project['id']}/runs",
        {
            "prompt_version_id": prompt["versions"][0]["id"],
            "dataset_version_id": version["id"],
            "provider": "mock",
            "provider_config": {},
            "evaluators": [{"type": "exact_match", "options": {}}],
        },
        {**csrf, "Idempotency-Key": "diagnosis-run"},
    )
    with SessionLocal() as db:
        assert execute_run(db, run["id"]) == "completed"
    return str(run["id"])


class FakeDiagnosticClient:
    calls = 0

    def __init__(self, *_: Any) -> None:
        pass

    def generate(self, **_: Any) -> GeminiGeneration:
        type(self).calls += 1
        if type(self).calls == 1:
            content = {
                "role": "model",
                "parts": [
                    {
                        "functionCall": {
                            "name": "inspect_failed_evaluations",
                            "args": {"run_id": "untrusted-other-run"},
                        }
                    }
                ],
            }
            return GeminiGeneration(
                text="",
                content=content,
                function_calls=[content["parts"][0]["functionCall"]],
                input_tokens=10,
                output_tokens=2,
                metadata={},
            )
        return GeminiGeneration(
            text=json.dumps(
                {
                    "summary": "The exact-match contract differs.",
                    "findings": ["Stored output is actual, not expected."],
                    "actions": ["Review the prompt and expected value."],
                    "citation_ids": [
                        "evaluator-failures#exact-match-failures",
                        "invented#citation",
                    ],
                }
            ),
            content={"role": "model", "parts": []},
            function_calls=[],
            input_tokens=30,
            output_tokens=12,
            metadata={},
        )


def test_inspection_tool_and_agent_are_bounded_to_requested_run(
    authenticated_client: tuple[TestClient, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, csrf = authenticated_client
    run_id = failed_run(client, csrf)
    FakeDiagnosticClient.calls = 0
    monkeypatch.setattr("evalpulse.diagnostics.GeminiClient", FakeDiagnosticClient)
    settings = Settings(
        llm_enabled=True,
        gemini_api_key="server-secret",
        rag_knowledge_dir="docs/knowledge",
    )

    with SessionLocal() as db:
        evidence = inspect_failed_evaluations(db, run_id)
        draft = diagnose_failed_run(db, run_id, settings)

    assert evidence["run_id"] == run_id
    assert evidence["failures"][0]["scores"][0]["name"] == "exact_match"
    assert draft.evidence["run_id"] == run_id
    assert draft.usage == {"calls": 2, "input_tokens": 40, "output_tokens": 14}
    assert [item["id"] for item in draft.citations] == ["evaluator-failures#exact-match-failures"]

    monkeypatch.setattr("evalpulse.api.settings", settings)
    FakeDiagnosticClient.calls = 0
    response = client.post(f"/api/runs/{run_id}/diagnose", headers=csrf)
    assert response.status_code == 200, response.text
    cached = client.post(f"/api/runs/{run_id}/diagnose", headers=csrf)
    assert cached.status_code == 200
    assert cached.json()["id"] == response.json()["id"]
    assert FakeDiagnosticClient.calls == 2
