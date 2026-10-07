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

## Dependency refresh during rework

After updating Next.js/eslint-config-next to 16.4.0, Sharp to 0.35.5, and Vitest to 4.1.11:

- Production audit passed with no vulnerabilities and no advisory exceptions.
- All 6 production-audit policy tests passed.
- Workspace lint and typing, all 5 client tests, and the production build passed.
- The web unit-test command found no tests; its zero exit status is not UI coverage.
- Range-respecting transitive updates and a clean `npm ci --ignore-scripts` passed, followed by the audit-policy tests, production audit, lint, typing, client tests, and build again.
- The full audit still fails with 5 high-severity development package records propagated through the unpatched `braces` lint-tool chain. This is not a clean full audit; no exceptions were added.
- Docker-dependent verification remains blocked.

## Comparison compatibility increment

On Windows/Python 3.12.10, the comparison guards passed Ruff lint, Ruff formatting (34 files), strict mypy across 18 application/changed-test files, and the full pytest coverage run: 25 tests, 81% coverage across 1,390 statements. Three pre-fix regressions had returned HTTP 201 for incompatible inputs; after the fix they return 422 and persist no decision. The compatible control and existing workflow pass. The Starlette/httpx deprecation warning remains. Docker-dependent checks are still unverified.

## Temporary-provider retry increment

On Windows/Python 3.12.10, Ruff lint/formatting (35 files), strict mypy across 16 application/changed-test files, and all 9 focused retry tests passed. The full coverage run passed 34 tests at 82% across 1,401 statements in 191.06 seconds. The two pre-fix regressions left runs running after temporary errors; the corrected path releases them for retry and preserves checkpoints. Task-chain exhaustion, duplicate active delivery, cancellation, start time, and terminal/unreleased states passed. Tests use direct engine execution and eager Celery request contexts without a broker; live delivery, worker-loss recovery, and PostgreSQL concurrency remain unverified. The Starlette/httpx warning remains.

## Authorized Docker restart and build attempt

`docker desktop restart` completed and the subsequent engine query returned `Server=29.6.1 OSType=linux`. The separate `evalpulse-rework` build used placeholder configuration, local migration storage, mock inference, and ports 13000/18000. It failed during package installation and BuildKit metadata writes with input/output and read-only-filesystem errors; no successful application startup or browser verification is claimed.

A BuildKit bind-mounted context probe executed the environment/metadata exclusion assertions successfully, but its image export failed with an I/O error. Context checks executed; the overall probe build did not pass and no completed probe image is claimed. Host storage inspection reported zero free bytes on C:, and `docker system df` failed reading snapshot storage. Free host space before retrying; no pruning, volume deletion, data relocation, or reset was performed.

## Run-submission flush recovery increment

On Windows/Python 3.12.10, Ruff lint/formatting (36 files), strict mypy across 16 application/changed-test files, both focused idempotency regressions, and all 36 Python tests passed. Coverage was 82% across 1,401 statements; the full run took 183.71 seconds. A separate-session committed winner injected before flush is returned with one run/dispatch/event; an unrelated synthetic integrity failure still propagates without partial records. This is controlled interleaving evidence, not live PostgreSQL contention or a load benchmark. The Starlette/httpx warning remains.

A later storage check found about 2.5 GB free on C:, but Docker readiness timed out after 60 seconds and the subsequent restart/readiness sequence after 240 seconds. No recovered runtime or successful full-stack result is claimed.

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
