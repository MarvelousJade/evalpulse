import json
from contextlib import suppress

from celery import Celery
from redis import Redis

from .config import get_settings
from .database import SessionLocal
from .engine import execute_run
from .models import EvaluationRun, RunDispatch
from .providers import TemporaryProviderError

settings = get_settings()
celery_app = Celery("evalpulse", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    worker_prefetch_multiplier=1,
    beat_schedule={
        "redispatch-pending-runs": {
            "task": "evalpulse.dispatch_pending",
            "schedule": 5.0,
        }
    },
)


def _redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def publish_progress(run_id: str, payload: dict[str, object]) -> None:
    with suppress(Exception):
        _redis().publish(f"evalpulse:run:{run_id}", json.dumps(payload))


def cancellation_requested(run_id: str) -> bool:
    try:
        return bool(_redis().get(f"evalpulse:cancel:{run_id}"))
    except Exception:
        return False


@celery_app.task(
    bind=True,
    autoretry_for=(TemporaryProviderError,),
    retry_backoff=True,
    retry_backoff_max=30,
    retry_jitter=True,
    max_retries=3,
)  # type: ignore[untyped-decorator]
def evaluate_run_task(self: object, run_id: str) -> str:
    with SessionLocal() as db:
        return execute_run(db, run_id, publish_progress, cancellation_requested)


def dispatch_pending(limit: int = 100) -> int:
    dispatched = 0
    with SessionLocal() as db:
        rows = (
            db.query(RunDispatch)
            .filter(RunDispatch.state == "pending")
            .order_by(RunDispatch.created_at)
            .limit(limit)
            .all()
        )
        for row in rows:
            run = db.get(EvaluationRun, row.run_id)
            if run is None or run.status != "queued":
                row.state = "discarded"
                continue
            try:
                evaluate_run_task.delay(row.run_id)
                row.state = "dispatched"
                row.attempts += 1
                row.last_error = None
                dispatched += 1
            except Exception as exc:
                row.attempts += 1
                row.last_error = str(exc)[:500]
        db.commit()
    return dispatched


@celery_app.task(name="evalpulse.dispatch_pending")  # type: ignore[untyped-decorator]
def dispatch_pending_task() -> int:
    return dispatch_pending()
