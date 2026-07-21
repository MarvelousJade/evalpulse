from __future__ import annotations

import math
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session, selectinload

from .evaluators import evaluate_output
from .models import (
    DatasetVersion,
    EvaluationResult,
    EvaluationRun,
    EvaluationScore,
    PromptVersion,
    RunEvent,
)
from .providers import PermanentProviderError, ProviderRequest, TemporaryProviderError, get_provider

ProgressPublisher = Callable[[str, dict[str, Any]], None]
CancellationCheck = Callable[[str], bool]


def add_event(db: Session, run_id: str, event_type: str, payload: dict[str, Any]) -> RunEvent:
    latest = db.scalar(select(func.max(RunEvent.sequence)).where(RunEvent.run_id == run_id)) or 0
    event = RunEvent(run_id=run_id, sequence=latest + 1, event_type=event_type, payload=payload)
    db.add(event)
    return event


def execute_run(
    db: Session,
    run_id: str,
    publish: ProgressPublisher | None = None,
    is_cancelled: CancellationCheck | None = None,
) -> str:
    claimed = cast(
        CursorResult[Any],
        db.execute(
            update(EvaluationRun)
            .where(EvaluationRun.id == run_id, EvaluationRun.status == "queued")
            .values(status="running", started_at=datetime.now(UTC))
        ),
    )
    if claimed.rowcount != 1:
        db.rollback()
        existing_run = db.get(EvaluationRun, run_id)
        return existing_run.status if existing_run else "missing"
    add_event(db, run_id, "run.started", {"status": "running"})
    db.commit()

    run = db.get(EvaluationRun, run_id)
    if run is None:
        return "missing"
    prompt_version = db.get(PromptVersion, run.prompt_version_id)
    dataset_version = db.scalar(
        select(DatasetVersion)
        .options(selectinload(DatasetVersion.cases))
        .where(DatasetVersion.id == run.dataset_version_id)
    )
    if prompt_version is None or dataset_version is None:
        _fail_run(db, run, "Run references missing immutable input")
        return "failed"

    provider = get_provider(run.provider)
    total = len(dataset_version.cases)
    try:
        for completed, case in enumerate(dataset_version.cases):
            db.refresh(run)
            if run.cancel_requested or (is_cancelled and is_cancelled(run.id)):
                run.status = "cancelled"
                run.finished_at = datetime.now(UTC)
                add_event(db, run.id, "run.cancelled", {"completed": completed, "total": total})
                db.commit()
                _publish(
                    publish,
                    run.id,
                    {"type": "run.cancelled", "completed": completed, "total": total},
                )
                return "cancelled"
            existing_result = db.scalar(
                select(EvaluationResult).where(
                    EvaluationResult.run_id == run.id,
                    EvaluationResult.test_case_id == case.id,
                )
            )
            if existing_result is None:
                result = EvaluationResult(run_id=run.id, test_case_id=case.id)
                try:
                    response = provider.evaluate(
                        ProviderRequest(
                            prompt=prompt_version.text,
                            input=case.input,
                            config=run.provider_config,
                        )
                    )
                    scores = evaluate_output(
                        response.output, case.expected, response.latency_ms, run.evaluators
                    )
                    result.output = response.output
                    result.latency_ms = response.latency_ms
                    result.input_tokens = response.input_tokens
                    result.output_tokens = response.output_tokens
                    result.provider_metadata = response.metadata
                    result.passed = all(score.passed for score in scores)
                    result.scores = [
                        EvaluationScore(
                            name=score.name,
                            passed=score.passed,
                            value=score.value,
                            explanation=score.explanation,
                        )
                        for score in scores
                    ]
                except PermanentProviderError as exc:
                    result.error_type = "permanent_provider_error"
                    result.error_message = str(exc)[:500]
                    result.passed = False
                db.add(result)
                db.flush()
            progress = {"completed": completed + 1, "total": total}
            add_event(db, run.id, "run.progress", progress)
            db.commit()
            _publish(publish, run.id, {"type": "run.progress", **progress})
    except TemporaryProviderError:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        run = db.get(EvaluationRun, run_id)
        if run is not None:
            _fail_run(db, run, f"Evaluation failed: {type(exc).__name__}")
        return "failed"

    run = db.get(EvaluationRun, run_id)
    if run is None:
        return "missing"
    run.aggregate = calculate_aggregate(db, run.id, dataset_version)
    run.status = "completed"
    run.finished_at = datetime.now(UTC)
    add_event(db, run.id, "run.completed", {"aggregate": run.aggregate})
    db.commit()
    _publish(publish, run.id, {"type": "run.completed", "aggregate": run.aggregate})
    return "completed"


def calculate_aggregate(
    db: Session, run_id: str, dataset_version: DatasetVersion
) -> dict[str, Any]:
    results = list(
        db.scalars(
            select(EvaluationResult)
            .where(EvaluationResult.run_id == run_id)
            .order_by(EvaluationResult.created_at)
        )
    )
    total = len(dataset_version.cases)
    passed = sum(result.passed for result in results)
    errors = sum(result.error_type is not None for result in results)
    latencies = sorted(result.latency_ms for result in results if result.error_type is None)
    p95_index = max(0, math.ceil(len(latencies) * 0.95) - 1)
    critical_ids = {case.id for case in dataset_version.cases if "critical" in case.tags}
    critical_results = [result for result in results if result.test_case_id in critical_ids]
    critical_passed = sum(result.passed for result in critical_results)
    return {
        "total": total,
        "completed": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": passed / total if total else 0,
        "critical_pass_rate": (
            critical_passed / len(critical_results) if critical_results else 1.0
        ),
        "p95_latency_ms": latencies[p95_index] if latencies else 0,
        "provider_error_rate": errors / total if total else 0,
        "input_tokens": sum(result.input_tokens for result in results),
        "output_tokens": sum(result.output_tokens for result in results),
    }


def _fail_run(db: Session, run: EvaluationRun, reason: str) -> None:
    run.status = "failed"
    run.failure_reason = reason[:500]
    run.finished_at = datetime.now(UTC)
    add_event(db, run.id, "run.failed", {"reason": run.failure_reason})
    db.commit()


def _publish(publish: ProgressPublisher | None, run_id: str, payload: dict[str, Any]) -> None:
    if publish:
        publish(run_id, payload)
