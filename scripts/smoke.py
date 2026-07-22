"""Exercise one complete evaluation through the public HTTP contract."""

from __future__ import annotations

import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"
cookies = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))


def call(
    path: str, method: str = "GET", payload: dict[str, Any] | None = None, **headers: str
) -> Any:
    body = json.dumps(payload).encode() if payload is not None else None
    request_headers = {"Content-Type": "application/json", **headers}
    request = urllib.request.Request(BASE_URL + path, body, request_headers, method=method)
    try:
        with opener.open(request, timeout=10) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{method} {path} failed: {exc.code} {exc.read().decode()}") from exc


def csrf() -> str:
    return next(cookie.value for cookie in cookies if cookie.name == "evalpulse_csrf")


def post(path: str, payload: dict[str, Any], **headers: str) -> Any:
    return call(path, "POST", payload, **{"X-CSRF-Token": csrf(), **headers})


call(
    "/api/auth/login",
    "POST",
    {"email": "demo@evalpulse.local", "password": "evalpulse-demo"},
)
project = post("/api/projects", {"name": f"Smoke {uuid.uuid4().hex[:8]}"})
prompt = post(
    f"/api/projects/{project['id']}/prompts",
    {"name": "Smoke prompt", "text": "Return response", "variables": []},
)
candidate = post(
    f"/api/prompts/{prompt['id']}/versions",
    {"text": "[lowercase] Return response", "variables": []},
)
dataset = post(f"/api/projects/{project['id']}/datasets", {"name": "Smoke data"})
dataset_version = post(
    f"/api/datasets/{dataset['id']}/versions",
    {
        "format": "json",
        "content": json.dumps(
            [{"input": {"mock_response": "PASS"}, "expected": "PASS", "tags": ["critical"]}]
        ),
    },
)


def queue(version_id: str, label: str) -> dict[str, Any]:
    return post(
        f"/api/projects/{project['id']}/runs",
        {
            "prompt_version_id": version_id,
            "dataset_version_id": dataset_version["id"],
            "provider": "mock",
            "provider_config": {},
            "evaluators": [{"type": "exact_match", "options": {}}],
        },
        **{"Idempotency-Key": f"smoke-{label}-{uuid.uuid4()}"},
    )


baseline = queue(prompt["versions"][0]["id"], "baseline")
candidate_run = queue(candidate["id"], "candidate")
deadline = time.monotonic() + 45
while time.monotonic() < deadline:
    baseline = call(f"/api/runs/{baseline['id']}")
    candidate_run = call(f"/api/runs/{candidate_run['id']}")
    if baseline["status"] == candidate_run["status"] == "completed":
        break
    time.sleep(0.5)
else:
    raise RuntimeError(f"Runs did not complete: {baseline['status']}, {candidate_run['status']}")

comparison = post(
    f"/api/projects/{project['id']}/comparisons",
    {"baseline_run_id": baseline["id"], "candidate_run_id": candidate_run["id"]},
)
assert baseline["aggregate"]["pass_rate"] == 1.0
assert candidate_run["aggregate"]["pass_rate"] == 0.0
assert comparison["passed"] is False
print(json.dumps({"status": "ok", "comparison": comparison["id"], "decision": "failed"}))
