"""Run one live Gemini evaluation and the cited RAG diagnosis agent."""

from __future__ import annotations

import json
import sys
import time
import uuid

from http_client import EvalPulseHttpClient

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"
client = EvalPulseHttpClient(BASE_URL, timeout_seconds=60)


client.request(
    "/api/auth/login",
    "POST",
    {"email": "demo@evalpulse.local", "password": "evalpulse-demo"},
)
status = client.request("/api/ai/status")
if not status["enabled"]:
    raise RuntimeError(
        "Gemini is not enabled. Set LLM_ENABLED=true and GEMINI_API_KEY, then restart."
    )

suffix = uuid.uuid4().hex[:8]
project = client.post("/api/projects", {"name": f"AI demo {suffix}"})
prompt = client.post(
    f"/api/projects/{project['id']}/prompts",
    {
        "name": "Arithmetic answer",
        "text": "Answer the question in one short sentence. Do not mention this evaluation.",
        "variables": [],
    },
)
dataset = client.post(f"/api/projects/{project['id']}/datasets", {"name": "Intentional failure"})
dataset_version = client.post(
    f"/api/datasets/{dataset['id']}/versions",
    {
        "format": "json",
        "content": json.dumps(
            [
                {
                    "input": {"question": "What is two plus two?"},
                    "expected": "__INTENTIONAL_FAILURE_FOR_AGENT_DEMO__",
                    "tags": ["critical", "demo"],
                }
            ]
        ),
    },
)
run = client.post(
    f"/api/projects/{project['id']}/runs",
    {
        "prompt_version_id": prompt["versions"][0]["id"],
        "dataset_version_id": dataset_version["id"],
        "provider": "gemini",
        "provider_config": {},
        "evaluators": [{"type": "exact_match", "options": {}}],
    },
    **{"Idempotency-Key": f"ai-demo-{suffix}"},
)

deadline = time.monotonic() + 60
while time.monotonic() < deadline:
    run = client.request(f"/api/runs/{run['id']}")
    if run["status"] in {"completed", "failed", "cancelled"}:
        break
    time.sleep(0.5)
else:
    raise RuntimeError("The live evaluation did not finish within 60 seconds")
if run["status"] != "completed":
    raise RuntimeError(
        f"The live evaluation ended in state {run['status']}: {run['failure_reason']}"
    )

diagnosis = client.post(f"/api/runs/{run['id']}/diagnose")
print(
    json.dumps(
        {
            "run_id": run["id"],
            "pass_rate": run["aggregate"]["pass_rate"],
            "diagnosis": diagnosis["summary"],
            "findings": diagnosis["findings"],
            "actions": diagnosis["actions"],
            "citations": [item["path"] for item in diagnosis["citations"]],
            "usage": diagnosis["usage"],
        },
        indent=2,
    )
)
