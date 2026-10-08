# Operations

## Local development

Copy `.env.example` to `.env`, set a long random `SESSION_SECRET`, then run:

```shell
docker compose up --build
```

The web app is on port 3000 and the API is on port 8000. PostgreSQL and Redis stay private to the Compose network. Set `WEB_PORT` or `API_PORT` if either public port is already occupied.

## Process-level development

```shell
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
npm install
alembic upgrade head
uvicorn services.api.main:app --reload
celery -A services.worker.main.celery_app worker --loglevel=INFO
npm run dev --workspace @evalpulse/web
```

## Optional live AI

Set `LLM_ENABLED=true` and `GEMINI_API_KEY` in `.env` before starting the API and worker. Confirm the
connection without exposing the key with `GET /api/ai/status`, or run the end-to-end demo:

```shell
python scripts/demo_ai.py http://localhost:8000
```

Keep the key restricted to the Gemini API and deployment egress IP. Configure a provider-side billing
budget and alert as the final cost boundary; the in-app daily allowance is defense in depth, not a
replacement for an account-level cap.

## Failure recovery

- If Redis restarts, completed data remains in PostgreSQL. Re-submit undispatched rows with the dispatcher command.
- A caught temporary provider error releases the current execution claim to `queued` before Celery's backoff retry. Previously committed case results are retained. Each Celery task retry chain permits an initial attempt plus three retries; exhaustion persists a terminal failed run. This is not a durable global per-run attempt cap across independent duplicate deliveries.
- Duplicate deliveries do not claim active `running` or terminal runs. A delivery after an explicit retry release may claim queued work before the scheduled retry; the queued-only update still selects one owner.
- A worker crash after claiming can strand a `running` run. Broker redelivery alone does not repair database ownership. There is also a gap between committing a retry release and scheduling it in the broker. Neither limitation is solved by result uniqueness; general recovery needs an ownership/fencing or equivalent design. Do not reset active runs without establishing that their owner is no longer executing.
- Cancellation is cooperative and is observed between provider calls; cancellation intent persists across caught-error retries.
- `/health/live` reports process health. `/health/ready` checks database access, not broker or worker readiness.
