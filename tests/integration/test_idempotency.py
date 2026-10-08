import json
from typing import Any

import pytest
from evalpulse.database import SessionLocal
from evalpulse.models import EvaluationRun, RunDispatch, RunEvent
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.helpers import post


@pytest.mark.parametrize("competing_commit", [True, False])
def test_run_flush_handles_idempotency_races_without_hiding_other_errors(
    authenticated_client: tuple[TestClient, dict[str, str]], competing_commit: bool
) -> None:
    client, csrf = authenticated_client
    project = post(client, "/api/projects", {"name": "Idempotent submission"}, csrf)
    prompt = post(
        client,
        f"/api/projects/{project['id']}/prompts",
        {"name": "Responder", "text": "Return response", "variables": []},
        csrf,
    )
    dataset = post(client, f"/api/projects/{project['id']}/datasets", {"name": "One case"}, csrf)
    version = post(
        client,
        f"/api/datasets/{dataset['id']}/versions",
        {
            "format": "json",
            "content": json.dumps([{"input": {"mock_response": "PASS"}, "expected": "PASS"}]),
        },
        csrf,
    )
    payload: dict[str, Any] = {
        "prompt_version_id": prompt["versions"][0]["id"],
        "dataset_version_id": version["id"],
        "provider": "mock",
        "provider_config": {},
        "evaluators": [{"type": "exact_match", "options": {}}],
    }
    injected = False
    winner_id: str | None = None

    def inject_before_flush(session: Session, context: object, instances: object) -> None:
        nonlocal injected, winner_id
        pending = next((row for row in session.new if isinstance(row, EvaluationRun)), None)
        if injected or pending is None:
            return
        injected = True
        if not competing_commit:
            raise IntegrityError("synthetic flush", {}, RuntimeError("Unrelated integrity failure"))
        with SessionLocal() as competing_db:
            winner = EvaluationRun(
                project_id=pending.project_id,
                prompt_version_id=pending.prompt_version_id,
                dataset_version_id=pending.dataset_version_id,
                created_by_id=pending.created_by_id,
                idempotency_key=pending.idempotency_key,
                provider=pending.provider,
                provider_config=pending.provider_config,
                evaluators=pending.evaluators,
            )
            competing_db.add(winner)
            competing_db.flush()
            competing_db.add(RunDispatch(run_id=winner.id))
            competing_db.add(
                RunEvent(
                    run_id=winner.id,
                    sequence=1,
                    event_type="run.queued",
                    payload={"status": "queued"},
                )
            )
            competing_db.commit()
            winner_id = winner.id

    event.listen(Session, "before_flush", inject_before_flush)
    try:
        if competing_commit:
            response = client.post(
                f"/api/projects/{project['id']}/runs",
                json=payload,
                headers={**csrf, "Idempotency-Key": "concurrent-submission"},
            )
            assert response.status_code == 202, response.text
            assert winner_id is not None
            assert response.json()["id"] == winner_id
        else:
            with pytest.raises(IntegrityError, match="Unrelated integrity failure"):
                client.post(
                    f"/api/projects/{project['id']}/runs",
                    json=payload,
                    headers={**csrf, "Idempotency-Key": "concurrent-submission"},
                )
    finally:
        event.remove(Session, "before_flush", inject_before_flush)
    assert injected
    with SessionLocal() as db:
        assert db.query(EvaluationRun).count() == int(competing_commit)
        assert db.query(RunDispatch).count() == int(competing_commit)
        assert db.query(RunEvent).count() == int(competing_commit)
