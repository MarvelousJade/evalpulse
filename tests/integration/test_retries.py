import json
from collections import Counter

import pytest
from celery.exceptions import Retry
from evalpulse.database import SessionLocal
from evalpulse.engine import execute_run
from evalpulse.models import EvaluationResult, EvaluationRun, RunEvent
from evalpulse.providers import (
    MockProvider,
    ProviderRequest,
    ProviderResponse,
    TemporaryProviderError,
)
from evalpulse.tasks import evaluate_run_task
from fastapi.testclient import TestClient

from tests.helpers import post


@pytest.fixture
def queued_run(authenticated_client: tuple[TestClient, dict[str, str]]) -> str:
    client, csrf = authenticated_client
    project = post(client, "/api/projects", {"name": "Retry recovery"}, csrf)
    prompt = post(
        client,
        f"/api/projects/{project['id']}/prompts",
        {"name": "Responder", "text": "Return response", "variables": []},
        csrf,
    )
    dataset = post(client, f"/api/projects/{project['id']}/datasets", {"name": "Two cases"}, csrf)
    version = post(
        client,
        f"/api/datasets/{dataset['id']}/versions",
        {
            "format": "json",
            "content": json.dumps(
                [
                    {"input": {"mock_response": value}, "expected": value}
                    for value in ["FIRST", "SECOND"]
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
        {**csrf, "Idempotency-Key": "retry-run"},
    )
    return str(run["id"])


class TransientProvider(MockProvider):
    def __init__(self, failed_case: str, *, persistent: bool = False) -> None:
        self.failed_case = failed_case
        self.persistent = persistent
        self.calls: Counter[str] = Counter()

    def evaluate(self, request: ProviderRequest) -> ProviderResponse:
        case = str(request.input["mock_response"])
        self.calls[case] += 1
        if case == self.failed_case and (self.persistent or self.calls[case] == 1):
            raise TemporaryProviderError("Simulated provider throttling")
        return super().evaluate(request)


@pytest.mark.parametrize("failed_case,checkpoints", [("FIRST", 0), ("SECOND", 1)])
def test_temporary_errors_release_the_claim_and_preserve_checkpoints(
    queued_run: str, monkeypatch: pytest.MonkeyPatch, failed_case: str, checkpoints: int
) -> None:
    provider = TransientProvider(failed_case)
    monkeypatch.setattr("evalpulse.engine.get_provider", lambda name: provider)
    with SessionLocal() as db:
        with pytest.raises(TemporaryProviderError):
            execute_run(db, queued_run)
        run = db.get(EvaluationRun, queued_run)
        assert run is not None
        assert run.status == "queued"
        started_at = run.started_at
        assert started_at is not None
        saved = db.query(EvaluationResult).filter_by(run_id=queued_run).all()
        assert len(saved) == checkpoints
        saved_ids = {result.id for result in saved}
        saved_scores = {score.id for result in saved for score in result.scores}

    with SessionLocal() as db:
        assert execute_run(db, queued_run) == "completed"
        run = db.get(EvaluationRun, queued_run)
        assert run is not None
        assert run.started_at == started_at
        assert run.aggregate["pass_rate"] == 1.0
        results = db.query(EvaluationResult).filter_by(run_id=queued_run).all()
        assert len(results) == 2
        assert saved_ids <= {result.id for result in results}
        assert saved_scores <= {score.id for result in results for score in result.scores}
    assert provider.calls[failed_case] == 2
    assert provider.calls["SECOND" if failed_case == "FIRST" else "FIRST"] == 1


def test_celery_retry_budget_ends_in_a_durable_failed_run(
    queued_run: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = TransientProvider("FIRST", persistent=True)
    monkeypatch.setattr("evalpulse.engine.get_provider", lambda name: provider)
    monkeypatch.setattr("evalpulse.tasks.publish_progress", lambda run_id, payload: None)
    monkeypatch.setattr("evalpulse.tasks.cancellation_requested", lambda run_id: False)
    for attempt in range(evaluate_run_task.max_retries + 1):
        evaluate_run_task.push_request(retries=attempt, called_directly=False, is_eager=True)
        try:
            if attempt < evaluate_run_task.max_retries:
                with pytest.raises(Retry):
                    evaluate_run_task.run(queued_run)
                expected = "queued"
            else:
                assert evaluate_run_task.run(queued_run) == "failed"
                expected = "failed"
        finally:
            evaluate_run_task.pop_request()
        with SessionLocal() as db:
            run = db.get(EvaluationRun, queued_run)
            assert run is not None
            assert run.status == expected
    assert provider.calls["FIRST"] == 4
    with SessionLocal() as db:
        run = db.get(EvaluationRun, queued_run)
        assert run is not None and run.finished_at is not None
        assert run.failure_reason == "Provider retry budget exhausted"
        assert db.query(RunEvent).filter_by(run_id=queued_run, event_type="run.failed").count() == 1
        assert execute_run(db, queued_run) == "failed"
    assert provider.calls["FIRST"] == 4


def test_active_delivery_does_not_reclaim_the_running_owner(
    queued_run: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = MockProvider()
    original_evaluate = provider.evaluate
    calls: list[str] = []

    def evaluate(request: ProviderRequest) -> ProviderResponse:
        calls.append(str(request.input["mock_response"]))
        with SessionLocal() as duplicate_db:
            assert execute_run(duplicate_db, queued_run) == "running"
        return original_evaluate(request)

    monkeypatch.setattr(provider, "evaluate", evaluate)
    monkeypatch.setattr("evalpulse.engine.get_provider", lambda name: provider)
    with SessionLocal() as db:
        assert execute_run(db, queued_run) == "completed"
        assert db.query(EvaluationResult).filter_by(run_id=queued_run).count() == 2
    assert calls == ["FIRST", "SECOND"]


def test_cancellation_survives_retry_release(
    queued_run: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = TransientProvider("FIRST")
    monkeypatch.setattr("evalpulse.engine.get_provider", lambda name: provider)
    with SessionLocal() as db:
        with pytest.raises(TemporaryProviderError):
            execute_run(db, queued_run)
        run = db.get(EvaluationRun, queued_run)
        assert run is not None
        run.cancel_requested = True
        db.commit()
        assert execute_run(db, queued_run) == "cancelled"
        assert db.query(EvaluationResult).filter_by(run_id=queued_run).count() == 0
        assert run.finished_at is not None
    assert provider.calls == Counter({"FIRST": 1})


@pytest.mark.parametrize("status", ["running", "completed", "failed", "cancelled"])
def test_delivery_preserves_unreleased_or_terminal_runs(
    queued_run: str, monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    calls: list[str] = []
    monkeypatch.setattr("evalpulse.engine.get_provider", lambda name: calls.append(name))
    with SessionLocal() as db:
        run = db.get(EvaluationRun, queued_run)
        assert run is not None
        run.status = status
        db.commit()
        assert execute_run(db, queued_run) == status
        assert db.query(RunEvent).filter_by(run_id=queued_run).count() == 1
    assert calls == []
