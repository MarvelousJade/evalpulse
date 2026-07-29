"""Exercise one complete evaluation through the public HTTP contract."""

from __future__ import annotations

import json
import sys
import time
import uuid
from typing import Any

from http_client import EvalPulseHttpClient

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"
client = EvalPulseHttpClient(BASE_URL, timeout_seconds=10)


client.request(
    "/api/auth/login",
    "POST",
    {"email": "demo@evalpulse.local", "password": "evalpulse-demo"},
)
project = client.post("/api/projects", {"name": f"Smoke {uuid.uuid4().hex[:8]}"})
prompt = client.post(
    f"/api/projects/{project['id']}/prompts",
    {"name": "Smoke prompt", "text": "Return response", "variables": []},
)
candidate = client.post(
    f"/api/prompts/{prompt['id']}/versions",
    {"text": "[lowercase] Return response", "variables": []},
)
dataset = client.post(f"/api/projects/{project['id']}/datasets", {"name": "Smoke data"})
dataset_version = client.post(
    f"/api/datasets/{dataset['id']}/versions",
    {
        "format": "json",
        "content": json.dumps(
            [{"input": {"mock_response": "PASS"}, "expected": "PASS", "tags": ["critical"]}]
        ),
    },
)


def queue(version_id: str, label: str) -> dict[str, Any]:
    return client.post(
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
    baseline = client.request(f"/api/runs/{baseline['id']}")
    candidate_run = client.request(f"/api/runs/{candidate_run['id']}")
    if baseline["status"] == candidate_run["status"] == "completed":
        break
    time.sleep(0.5)
else:
    raise RuntimeError(f"Runs did not complete: {baseline['status']}, {candidate_run['status']}")

comparison = client.post(
    f"/api/projects/{project['id']}/comparisons",
    {"baseline_run_id": baseline["id"], "candidate_run_id": candidate_run["id"]},
)
assert baseline["aggregate"]["pass_rate"] == 1.0
assert candidate_run["aggregate"]["pass_rate"] == 0.0
assert comparison["passed"] is False
print(json.dumps({"status": "ok", "comparison": comparison["id"], "decision": "failed"}))
