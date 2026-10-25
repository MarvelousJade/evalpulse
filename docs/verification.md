# Verification

## Next.js audit remediation

CI run `40240837113` failed the production dependency audit for Next.js 16.4.0; lint, typing,
client tests, and build did not run in that failed job. Locally reproduced the audit rejection,
updated both Next.js pins and `eslint-config-next` to 16.4.3, and refreshed the lockfile without
changing audit policy.

On Windows/Node 22.23.3/npm 12.2.0, the complete local `web-check` sequence passed: `npm ci`, six
audit-policy tests, production audit (zero vulnerabilities), workspace lint, workspace typing,
five client tests, and optimized production/client builds. A separate full audit still fails with
three development package records: two moderate (`@vitest/mocker`, `vitest`) and one high (`zod`).
This is not a clean full audit. ESLint's unsupported-version warning remains. Local npm blocked
`unrs-resolver` postinstall under its allowScripts policy; lint and build still passed.

This is local verification, not a successful hosted CI run or a verified deployment. No Python,
Docker, browser, or live model checks were rerun for this dependency-only fix. Earlier audit counts
below are historical observations; advisory data can change without a source change.

## Resume measurement refresh — 2026-10-25 UTC

The local measurement harness passed independently: five 50-case mock runs had median direct-engine
execution of 0.661 seconds (0.638–0.723 seconds), and a temporary-error retry preserved 25 result and
25 score identities before completing 50 cases in 51 provider calls. See the
[procedure](benchmarks/README.md), [raw JSON](benchmarks/local-mock-evidence.json), and
[resume claims](resume-evidence.md).

Python 3.12.15 on Windows 11: 43 tests passed, one opt-in benchmark skipped, one Starlette/httpx
deprecation warning; 82% statement coverage across 1,401 application statements. Full output is in
[python-checks.txt](benchmarks/python-checks.txt). Ruff lint and formatting passed, as did strict mypy
across the application and changed scripts/tests (19 source files). This refresh used disposable
SQLite, not PostgreSQL or a live broker. No frontend code changed; frontend/build/browser checks
were not rerun. Earlier full-stack evidence below is historical, not refreshed by this increment.

The repository's old `.venv` could not find its base Python. A separate ignored `.pi/measure-venv`
was provisioned for this verification. The existing environment and application databases were not
modified. See the journal for failed setup commands and resolution.

## Standard checks

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

## Local main-branch integration

The user authorized merging `shaoyu/rework` at `d629a38` into local main branch `me` with a two-parent merge commit. The earlier merge `50a70f9`, all faulty/fixed commits and tags, and code comments are preserved without squashing or rewriting history. A separate worktree protects uncommitted changes in the original checkout.

Fresh verification of the main-worktree result passed: 40 SQLite tests, 82% coverage across 1,401 statements, Ruff lint/formatting (38 files), strict mypy (19 source files), Markdown fence checks (13 staged documents), and scoped Git diff checks. The known Starlette/httpx warning remains. Only documentation differs from `d629a38`; application code, tests, and scripts are identical. Earlier PostgreSQL/container/browser/client/audit evidence below is preserved, not claimed as newly rerun for this integration. The five development dependency findings remain. No remote push was performed.

Documentation uses neutral engineering wording; actual branch/tag names and intentional-defect provenance remain accurate. Existing commit messages are preserved as part of the requested history.

## Final rework-state verification

Corrected investigations were merged into `shaoyu/rework` as `50a70f9` (parents `7d26f9b`, `2bf8967`). The full branch diff was reviewed before merge; application code across `python`, `services`, `apps`, and `packages` matches the verified baseline. The integration adds regression coverage and debugging documentation, with both faulty/fixed pairs preserved in history and tags.

Fresh checks after merge passed:

- SQLite: 40 tests, 82% statement coverage across 1,401 statements, 145.69 seconds (Windows/Python 3.12.10).
- Disposable PostgreSQL: 40 tests, same coverage, 59.70 seconds (Linux/Python 3.12.10).
- Ruff lint/formatting (39 files including the local verification helper), strict mypy across 19 application/test/helper files, and workspace lint/typing.
- Five client tests, six audit-policy tests, and production dependency audit with no vulnerabilities.
- Isolated Compose rebuild/startup, migration completion, API/PostgreSQL/Redis readiness, and running web/worker.
- Live HTTP smoke: asynchronous baseline/candidate completion and expected regression rejection (`status=ok`, `decision=failed`).
- Playwright: one passing reviewer workflow, 6.7 seconds (total 8.3 seconds).

The full `npm audit --json` still fails with five high-severity development records in the `braces` lint chain (GHSA-vfj7-8cjw-p6xm). No incompatible downgrade, unsupported override, or advisory exception was applied. The Starlette/httpx warning remains. Neither result is hidden by the passing production audit or functional checks.

Start investigations at [reproduction instructions](debugging/README.md), not solution files or the journal. Faulty/fixed references: `learning/01-faulty` (`79e46e9`) / `learning/01-fixed` (`3e366ce`), and `learning/02-faulty` (`f2bbc8e`) / `learning/02-fixed` (`2bf8967`). No faulty implementation was deployed or merged as the working final state.

These are local mock/controlled-interleaving results, not evidence of production usage, load, exploitation, external model quality, comprehensive authorization auditing, or general worker-loss/concurrent-delivery recovery. Kubernetes/production deployment checks were not part of this local acceptance scope. At this rework checkpoint, nothing was pushed or merged into `me`; local verification artifacts and existing user changes were intentionally excluded from commits.

## Verified runtime baseline before investigations

After host storage recovery, Linux Docker 29.8.2 passed readiness/storage inspection. The isolated `evalpulse-rework` stack built and started, migrations completed, and API/PostgreSQL/Redis were healthy; web/worker were running. Runtime versions: Python 3.12.10, Node 22.17.0, PostgreSQL 17.5, Redis 8.0.6.

- Public HTTP smoke passed through the live broker/worker: baseline pass rate 1.0, candidate 0.0, expected failed release decision.
- The existing Playwright reviewer workflow passed: one test (11.6 seconds), total runner time 20.8 seconds.
- Rendered-browser inspection also completed the three-case workflow and confirmed two completed runs, 100%/0% pass rates, and `Regression detected`/`FAIL` with separate policy outcomes.
- All 36 Python tests passed on `evalpulse_rework_test` PostgreSQL at 82% coverage across 1,401 statements (55.86 seconds, Linux/Python 3.12.10). The initial runner omitted documentation fixtures: 33 passed/3 failed; adding the read-only fixture mount fixed the harness, without application changes.
- The BuildKit context exclusion probe passed assertions and completed image export/unpack. Private `.env*`, `.pi`, and `.neon` were absent; `.env.example` remained.
- A read-only application-database query found six completed runs from the three workflows. Destructive pytest setup targeted only the separately provisioned `_test` database.

These are local mock/controlled-interleaving results. They do not establish worker-loss recovery, all concurrent-delivery scenarios, production load or model quality. The known Starlette/httpx deprecation warning remains. Fresh Ruff lint/formatting (36 files), strict mypy (16 application/changed-test files), workspace lint/typing, five client tests, six audit-policy tests, and production audit all passed. Production audit reported no vulnerabilities. The last full npm audit still flagged five development dependency records; this is not a clean full audit.

### Isolated stack and HTTP/browser reproduction (Windows cmd)

Use only local disposable development storage. The session value below is a test placeholder, not a secret suitable for a shared deployment. Default Compose port publishing can expose services on host interfaces; do not expose this demo to untrusted networks.

```cmd
set "API_PORT=18000"
set "WEB_PORT=13000"
set "MIGRATION_DATABASE_URL=postgresql+psycopg://evalpulse:evalpulse@postgres:5432/evalpulse"
set "LLM_ENABLED=false"
set "GEMINI_API_KEY="
set "SESSION_SECRET=rework-local-placeholder-secret-at-least-32-characters"
docker compose --parallel 1 --env-file .env.example -p evalpulse-rework up --build --detach --wait --wait-timeout 180
.venv\Scripts\python.exe scripts\smoke.py http://localhost:18000
set "PLAYWRIGHT_BROWSERS_PATH=%cd%\.pi\playwright-browsers"
call node_modules\.bin\playwright.cmd install chromium
set "E2E_BASE_URL=http://localhost:13000"
call node_modules\.bin\playwright.cmd test --config tests\e2e\playwright.config.ts --output .pi\verification\playwright-results
```

### Disposable PostgreSQL reproduction

Provision `evalpulse_rework_test` once in this isolated stack and confirm it belongs exclusively to tests before running destructive fixtures. The API's normal `evalpulse` database must not be selected. The runner mounts only source, tests, documentation fixtures, and configuration read-only; no private environment files are mounted. An ephemeral `/tmp` virtual environment uses the image's application dependencies plus pytest/httpx/coverage. Select `COVERAGE_CORE=pytrace` to avoid attempting native tracer mapping on the protected temporary mount.

```cmd
docker compose --env-file .env.example -p evalpulse-rework exec -T postgres createdb -U evalpulse evalpulse_rework_test
docker compose --env-file .env.example -p evalpulse-rework run --rm --no-deps ^
  --entrypoint sh --workdir /workspace ^
  -e "TEST_DATABASE_URL=postgresql+psycopg://evalpulse:evalpulse@postgres:5432/evalpulse_rework_test" ^
  -e "PYTHONDONTWRITEBYTECODE=1" -e "COVERAGE_FILE=/tmp/.coverage" -e "COVERAGE_CORE=pytrace" ^
  -e "LLM_ENABLED=false" -e "GEMINI_API_KEY=" ^
  -v "%cd%\python:/workspace/python:ro" -v "%cd%\tests:/workspace/tests:ro" ^
  -v "%cd%\docs:/workspace/docs:ro" -v "%cd%\pyproject.toml:/workspace/pyproject.toml:ro" ^
  api -c "python -m venv --system-site-packages /tmp/test-venv && /tmp/test-venv/bin/python -m pip install --no-cache-dir 'pytest>=8.4,<9' 'pytest-cov>=6.2,<7' 'httpx>=0.28,<1' && /tmp/test-venv/bin/python -m pytest --cov=evalpulse --cov-report=term-missing"
```

The successful runner resolved pytest 8.4.2, pytest-cov 6.3.0, httpx 0.28.1, and coverage 7.16.2. The command above inlines the same temporary runner script used for verification; future dependency ranges may resolve differently. See the journal for the failed setup attempt, correction, and local artifact paths.

## Historical rework baseline (Windows)

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

## Historical local test refresh

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
