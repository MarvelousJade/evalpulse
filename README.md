# EvalPulse

EvalPulse is a deterministic prompt-evaluation and regression-testing platform. It combines a Next.js dashboard, a FastAPI API, Celery workers, PostgreSQL, Redis, and a reproducible mock model so the complete workflow runs without paid AI services.

## Quick start

1. Copy `.env.example` to `.env` and replace `SESSION_SECRET`.
2. Run `docker compose up --build`.
3. Open <http://localhost:3000> and sign in with `demo@evalpulse.local` / `evalpulse-demo`.

The API documentation is available at <http://localhost:8000/docs>. See [operations](docs/operations.md) for local commands and [verification](docs/verification.md) for the evidence behind project claims.

For a hosted deployment, see the [Render Blueprint guide](docs/render.md).

## Repository map

- `apps/web`: Next.js dashboard
- `services/api`: FastAPI process entry point
- `services/worker`: Celery process entry point
- `python/evalpulse`: shared domain, persistence, provider, and evaluator code
- `tests`: Python integration and Playwright end-to-end tests
- `infra/k8s`: Kustomize base and local/production overlays

## Design principles

- PostgreSQL is authoritative; Redis contains only replaceable queue, cache, and progress data.
- Run inputs and evaluator configuration are immutable.
- Workers are retry-safe and results are unique per run and test case.
- The mock provider is deterministic and is the default in tests and demos.
- Every comparison explains each regression threshold independently.
