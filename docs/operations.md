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
- A worker crash leaves a run retryable; duplicate task delivery is safe.
- Cancellation is cooperative and is observed between provider calls.
- `/health/live` reports process health. `/health/ready` also checks required dependencies.
