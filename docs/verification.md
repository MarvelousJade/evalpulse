# Verification

Run the checks from the repository root:

```shell
ruff check .
mypy python/evalpulse
pytest --cov=evalpulse
npm run lint
npm run typecheck
npm test
npm run build
docker compose config --quiet
kubectl kustomize infra/k8s/overlays/kind
```

Pytest ignores an inherited application `DATABASE_URL` by default and creates a temporary SQLite database. Destructive fixture setup operates only on the selected test database, and the temporary database is cleaned up after the session.

For PostgreSQL integration checks, explicitly set `TEST_DATABASE_URL` to a **disposable** PostgreSQL database whose name ends in `_test`. The fixtures drop and recreate mapped tables there. The name check reduces accidental selection but does not establish that a database is safe to destroy. Never use an application database. CI opts into its dedicated `evalpulse_test` service database; `DATABASE_URL` still selects the migration target separately.

```shell
# Only with a disposable local database provisioned for tests:
export TEST_DATABASE_URL=postgresql+psycopg://localhost/evalpulse_test
python -m pytest tests/integration
```

In PowerShell, use `$env:TEST_DATABASE_URL = "postgresql+psycopg://localhost/evalpulse_test"`. Unset this variable to return to temporary SQLite tests. SQLite results do not establish PostgreSQL locking or broker-delivery behavior.

Measured counts and performance claims belong here only after the commands have run in a clean environment. The local Kubernetes overlay is a demonstration path and is not described as production infrastructure.

## Rework baseline (Windows)

Fresh local checks used Python 3.12.10, Node 24.19.0, and npm 11.17.0:

- Ruff lint and format checks passed; strict mypy passed across 15 application source files.
- `python -m pytest --cov=evalpulse --cov-report=term-missing`: 21 tests passed, with 80% statement coverage across 1,386 statements. One Starlette/httpx deprecation warning was reported.
- Workspace lint, TypeScript checks, all 5 API-client tests, and the optimized Next.js 16.3.1 build passed after `npm ci` restored local command shims.
- Compose configuration rendered with `docker compose --env-file .env.example -p evalpulse-rework config --quiet`.
- Production dependency audit failed for `next`, `sharp`, and `source-map-js`; the full audit reported 13 vulnerable package records. Remediation is outstanding.
- Docker Desktop's selected Linux daemon was unavailable. PostgreSQL/Redis execution, container builds, HTTP smoke, and Playwright workflow checks were not verified in this refresh.

The workflow tests execute the engine directly and stub broker dispatch. Their SQLite results do not prove live worker delivery or PostgreSQL concurrency behavior. See the [engineering journal](engineering-journal.md) for commands, failed attempts, evidence, and limitations.

## Latest local test refresh

Verified locally on July 29, 2026 with Python 3.12.10 and Node 24.11.0:

- 16 Python unit/integration tests passed with 80% statement coverage across 1,380 statements.
- 5 typed API-client contract tests passed.

The browser test requires a running web/API stack and was not included in this local refresh.

## Full-stack baseline

Verified locally on July 21, 2026 with Docker 29.6.1 and kubectl/Kustomize 1.36.1:

- 1 Playwright browser workflow passed against the Compose stack.
- Ruff, strict mypy, ESLint, TypeScript, and the optimized Next.js build passed.
- `npm audit --audit-level=moderate` reported zero known vulnerabilities.
- All four application images built and ran as non-root with read-only root filesystems.
- The HTTP smoke script completed two Celery runs and confirmed the expected failed regression decision against PostgreSQL and Redis.
- The `kind` and production Kustomize overlays rendered successfully. A local cluster run was not recorded because `kind` was not installed; CI owns that deployment proof.
