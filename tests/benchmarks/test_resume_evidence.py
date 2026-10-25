"""Opt-in measurements; run through scripts/measure_resume.py for provenance."""

import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any

import pytest
from evalpulse.database import SessionLocal
from evalpulse.engine import execute_run
from evalpulse.models import EvaluationResult, EvaluationRun
from evalpulse.providers import (
    MockProvider,
    ProviderRequest,
    ProviderResponse,
    TemporaryProviderError,
)
from fastapi.testclient import TestClient

from tests.helpers import create_mock_run

pytestmark = pytest.mark.skipif(
    not os.environ.get("EVALPULSE_EVIDENCE_OUTPUT"),
    reason="opt-in local measurement: python scripts/measure_resume.py --output <new.json>",
)


class OneTemporaryFailure(MockProvider):
    def __init__(self) -> None:
        self.calls: Counter[str] = Counter()

    def evaluate(self, request: ProviderRequest) -> ProviderResponse:
        value = str(request.input["mock_response"])
        self.calls[value] += 1
        if value == "CASE-025" and self.calls[value] == 1:
            raise TemporaryProviderError("Synthetic temporary failure")
        return super().evaluate(request)


def test_local_throughput_and_checkpoint_recovery(
    authenticated_client: tuple[TestClient, dict[str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, headers = authenticated_client
    cases: list[dict[str, Any]] = [
        {"input": {"mock_response": f"CASE-{index:03}"}, "expected": f"CASE-{index:03}"}
        for index in range(50)
    ]
    durations = []
    warmup_seconds = 0.0
    run_ids: set[str] = set()
    # A fresh immutable input/run per trial; setup and validation are outside the timed region.
    for trial in range(6):
        run = create_mock_run(client, headers, cases, idempotency_key=f"throughput-{trial}")
        run_id = str(run["id"])
        assert run_id not in run_ids
        run_ids.add(run_id)
        with SessionLocal() as db:
            start = perf_counter()
            status = execute_run(db, run_id)
            elapsed = perf_counter() - start
            assert status == "completed"
            saved_run = db.get(EvaluationRun, run_id)
            assert saved_run is not None
            assert saved_run.aggregate["pass_rate"] == 1.0
            assert db.query(EvaluationResult).filter_by(run_id=run_id).count() == len(cases)
        if trial == 0:
            warmup_seconds = elapsed
        else:
            durations.append(elapsed)

    provider = OneTemporaryFailure()
    monkeypatch.setattr("evalpulse.engine.get_provider", lambda name: provider)
    recovery = create_mock_run(client, headers, cases, idempotency_key="checkpoint-recovery")
    recovery_id = str(recovery["id"])
    with SessionLocal() as db:
        with pytest.raises(TemporaryProviderError):
            execute_run(db, recovery_id)
        saved_run = db.get(EvaluationRun, recovery_id)
        assert saved_run is not None and saved_run.status == "queued"
        checkpoints = db.query(EvaluationResult).filter_by(run_id=recovery_id).all()
        assert len(checkpoints) == 25
        result_ids = {result.id for result in checkpoints}
        score_ids = {score.id for result in checkpoints for score in result.scores}
        assert len(score_ids) == 25
    with SessionLocal() as db:
        assert execute_run(db, recovery_id) == "completed"
        results = db.query(EvaluationResult).filter_by(run_id=recovery_id).all()
        assert len(results) == 50
        assert result_ids <= {result.id for result in results}
        assert score_ids <= {score.id for result in results for score in result.scores}
        assert all(result.passed for result in results)
    assert len(provider.calls) == 50
    assert provider.calls["CASE-025"] == 2
    assert sum(provider.calls.values()) == 51
    assert all(provider.calls[f"CASE-{index:03}"] == 1 for index in range(25))

    report = {
        "workload": {
            "cases": 50,
            "dataset_sha256": hashlib.sha256(
                json.dumps(cases, sort_keys=True).encode()
            ).hexdigest(),
            "case_recipe": "CASE-000 through CASE-049; mock_response equals expected",
            "prompt": "Return response",
            "evaluators": [{"type": "exact_match", "options": {}}],
            "provider": "mock",
            "provider_config": {},
        },
        "throughput": {
            "timing_boundary": "execute_run only; excludes HTTP/setup and result assertions",
            "warmup_seconds": warmup_seconds,
            "trial_seconds": durations,
            "trial_cases_per_minute": [50 / seconds * 60 for seconds in durations],
            "median_seconds": median(durations),
            "min_seconds": min(durations),
            "max_seconds": max(durations),
            "median_cases_per_minute": median([50 / seconds * 60 for seconds in durations]),
            "measured_runs_completed": len(durations),
            "measured_runs_attempted": 5,
        },
        "recovery": {
            "failure": "one TemporaryProviderError on CASE-025; direct engine reinvocation",
            "results_before_retry": len(result_ids),
            "result_ids_preserved": len(result_ids),
            "score_ids_preserved": len(score_ids),
            "results_after_retry": len(results),
            "provider_calls": dict(sorted(provider.calls.items())),
            "total_provider_calls": sum(provider.calls.values()),
            "completed_checkpoint_provider_recalls": 0,
            "final_status": "completed",
        },
    }
    Path(os.environ["EVALPULSE_EVIDENCE_OUTPUT"]).write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
