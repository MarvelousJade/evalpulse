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
