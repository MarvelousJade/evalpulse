import json
from typing import Any

from fastapi.testclient import TestClient


def post(
    client: TestClient, path: str, payload: dict[str, Any], headers: dict[str, str]
) -> dict[str, Any]:
    response = client.post(path, json=payload, headers=headers)
    assert response.status_code in {200, 201, 202}, response.text
    body = response.json()
    assert isinstance(body, dict)
    return body


def create_mock_run(
    client: TestClient,
    headers: dict[str, str],
    cases: list[dict[str, Any]],
    *,
    prompt_text: str = "Return response",
) -> dict[str, Any]:
    project = post(client, "/api/projects", {"name": "Regression verification"}, headers)
    prompt = post(
        client,
        f"/api/projects/{project['id']}/prompts",
        {"name": "Responder", "text": prompt_text, "variables": []},
        headers,
    )
    dataset = post(client, f"/api/projects/{project['id']}/datasets", {"name": "Cases"}, headers)
    version = post(
        client,
        f"/api/datasets/{dataset['id']}/versions",
        {"format": "json", "content": json.dumps(cases)},
        headers,
    )
    return post(
        client,
        f"/api/projects/{project['id']}/runs",
        {
            "prompt_version_id": prompt["versions"][0]["id"],
            "dataset_version_id": version["id"],
            "provider": "mock",
            "provider_config": {},
            "evaluators": [{"type": "exact_match", "options": {}}],
        },
        {**headers, "Idempotency-Key": "additional-regression-run"},
    )
