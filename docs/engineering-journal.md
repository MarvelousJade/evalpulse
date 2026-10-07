# Engineering journal

## Evidence conventions

Record observations separately from hypotheses and hypothetical consequences. Local tests, synthetic demonstrations, and production observations are different kinds of evidence. Historical documentation is not a fresh verification result.

Implementation records below do not establish what the project owner personally investigated or learned. Personal investigation notes have a separate section for the owner to complete. Intentionally introduced exercise defects must be explicitly identified and must not be attributed to the implementation branch.

## Rework kickoff

### Problem and constraints

The project already implements prompt versioning, evaluation, comparison, and optional diagnosis. The rework objective is to make its core workflow easier to understand and defend in an interview without replacing useful behavior merely for novelty.

A pre-existing uncommitted change in `apps/web/tsconfig.json` must be preserved and excluded from task commits. No `shaoyu/rework` branch existed at kickoff; it was created from `bda615b`. The repository's main branch is `master`; integration there requires authorization.

### Investigation and evidence

Inspected repository instructions, Git status and recent history, README, architecture and verification documents, architecture decisions, package scripts, CI configuration, the HTTP smoke script, browser workflow test, and the dashboard's orchestration code. Core backend and test review identified configuration isolation, retry-state, concurrent idempotency, and comparison-compatibility concerns; only test isolation has been reproduced and fixed in this increment.

Observed that the primary demonstration already uses deterministic mock responses and exact-match evaluation. Live Gemini integration is optional. CI separates Python checks, web checks, PostgreSQL integration, Compose browser tests, and optional Kubernetes smoke coverage.

Historical verification documents describe earlier runs. Their counts and results will not be presented as current results without rerunning the corresponding checks.

### Decision and alternatives

Begin with baseline verification and a bounded plan, not an architecture rewrite. Preserve the existing background-worker design until evidence justifies changes. A synchronous API would reduce process count but would change the existing execution and progress model; that cost is not currently justified.

### Verification

The initial Python baseline used Python 3.12.10 under Windows `cmd.exe`. Ruff lint passed, Ruff reported 30 files already formatted, and strict mypy passed across 15 source files. The process was stopped after static review found unsafe database selection in the test harness. No completed pytest result is available; this attempt does not establish a passing test baseline. Full-stack smoke and browser verification also remain outstanding.

The first web baseline ran under Windows `cmd.exe` with Node 24.19.0 and npm 11.17.0:

```shell
npm run lint
npm run typecheck
npm test --workspace @evalpulse/api-client
npm run build
```

Lint failed because Windows could not resolve the local `eslint` and `tsc` executables. The chained type checks, tests, and build did not run. This is an observed environment blocker, not evidence of an application defect. The initial hypothesis was that the existing dependency installation lacked usable Windows command shims; reinstalling from the lockfile subsequently restored the executables.

Recovery: `npm ci` using the existing lockfile restored usable local executables. The rerun passed workspace lint and type checks, all 5 API-client tests, and the optimized Next.js 16.3.1 production build. The API-client build/type check also passed. No browser test ran in this command.

The installation reported 13 vulnerabilities (1 moderate, 9 high, 3 critical) and a deprecated ESLint version. These are actual package-audit findings, not demonstrated application exploitation. Both audit checks completed and failed. `node scripts/audit-production.mjs` rejected `next`, `sharp`, and `source-map-js`. The full `npm audit --json` confirmed 13 vulnerable package records. Production findings include Next.js ranges below 16.3.6, Sharp below 0.35.5, and source-map-js below 1.2.2. Development findings include Vitest/mocker and Tinypool plus lint-tool transitive dependencies. Audit suggestions include Next.js 16.4.0 and a major Vitest upgrade; suggestions still require compatibility review and verification. No exploitation, exposure of a specific deployment, or compromise is established by these reports. Remediation belongs in a separate focused dependency increment; do not widen the audit allowlist or use `npm audit fix --force` as an unexplained remediation.

### Local stack verification blocker

Docker 29.6.1 and Docker Compose v5.3.0 are installed. `docker info --format "{{.ServerVersion}}"` failed because the `dockerDesktopLinuxEngine` named pipe was absent. This establishes that the selected Docker daemon is unavailable, not that application containers are broken. No containers were started. The subsequent chained Compose validation did not run. Standalone `docker compose --env-file .env.example -p evalpulse-rework config --quiet` then passed. This validates configuration rendering only, not image builds or running services.

Plan: use a separate `evalpulse-rework` Compose project with documented placeholder configuration for a synthetic demonstration once the local daemon is available. Do not reuse application database credentials or delete existing volumes. Full-stack PostgreSQL/Redis, HTTP smoke, and browser results remain unverified.

### Tradeoffs and remaining risks

Keeping the existing stack preserves functionality but requires learning queue delivery, durable state, and browser progress handling. In-process SQLite tests cannot establish PostgreSQL locking behavior or Redis/Celery delivery reliability. Optional external model calls cannot be used as deterministic correctness evidence.

### Lesson and interview explanation

The first engineering decision is to establish what already works and what evidence supports it before simplifying. The goal is one understandable release-decision workflow, not more technologies.

### References and provenance

- `docs/rework-plan.md`
- `docs/architecture.md`
- `docs/adr/0001-postgres-authority.md`
- `docs/adr/0002-deterministic-provider.md`
- `.github/workflows/ci.yml`
- `scripts/smoke.py`
- `tests/e2e/workflow.spec.ts`

This entry records a planning hurdle, not a discovered software defect or an intentional exercise defect.

## Defect: test setup selected inherited application storage

### Problem

Expected: verification must not modify application data. Actual: the test harness retained an inherited `DATABASE_URL`, then dropped and recreated all mapped tables.

### Reproduction

The regression test creates a disposable SQLite database containing a `projects` table with a sentinel column and row. A subprocess inherits its URL, imports the test harness, and invokes its destructive setup. Before the fix, querying the sentinel failed with `sqlite3.OperationalError: no such column: marker`: setup had replaced the table with the application schema. No real application database was used for this reproduction.

Command (Windows, repository virtual environment):

```shell
.venv\Scripts\python.exe -c "import runpy,tempfile; from pathlib import Path; suite=runpy.run_path('tests/unit/test_database_isolation.py'); directory=tempfile.TemporaryDirectory(); suite['test_inherited_application_database_is_not_modified'](Path(directory.name))"
```

### Investigation and root cause

Static review identified `os.environ.setdefault("DATABASE_URL", ...)` before application imports and `Base.metadata.drop_all(engine)` in the autouse fixture. `setdefault` preserves inherited configuration. Application imports construct the SQLAlchemy engine once, so changing configuration afterward would be too late. The disposable reproduction confirmed the path rather than relying on the static hypothesis alone.

### Fix

Select a fresh temporary SQLite database before application imports. Ignore the application's inherited database URL. An explicit `TEST_DATABASE_URL` permits PostgreSQL integration against a disposable database with a name ending in `_test`; invalid target types and names are rejected before application imports. Dispose pooled connections before cleaning temporary storage at session end.

CI explicitly opts into its existing dedicated PostgreSQL database. Migration configuration stays separate, preserving the PostgreSQL integration path rather than silently converting it to SQLite.

### Tradeoffs

A separate opt-in variable adds setup work but makes destructive intent explicit. The `_test` suffix is only a guardrail, not proof of safe ownership. The operator must provision disposable storage. Temporary SQLite keeps ordinary verification free of database services but cannot prove PostgreSQL concurrency behavior.

### Verification

The pre-fix disposable reproduction failed as expected and demonstrated replacement of the sentinel table. The first post-fix run passed formatting but stopped at Ruff E402: module-level application imports followed configuration statements. Moved application imports into fixtures to preserve safe initialization order without suppressing lint. Also corrected the yielding client fixture's return annotation. These were fixed within the uncommitted increment; later checks in that attempt did not run. Fresh checks passed under Windows with Python 3.12.10: Ruff lint, Ruff format check (31 files), strict mypy across 15 application source files, and `pytest --cov=evalpulse --cov-report=term-missing` (21 tests, 80% statement coverage across 1,386 statements, 155.38 seconds). The sentinel-preservation regression and three invalid-target cases passed. One Starlette/httpx deprecation warning was reported; it did not fail tests. Strict mypy also passed for the two changed test files, and the staged diff passed whitespace checks. No PostgreSQL integration result is claimed yet.

### Lesson and interview explanation

Configuration precedence is a safety boundary when tests perform destructive setup. Reproduce the dangerous path with disposable sentinel data, override configuration before engine construction, and preserve explicit integration coverage rather than hiding the hazard with a change in test backend.

### References and provenance

- `tests/conftest.py`
- `tests/unit/test_database_isolation.py`
- `.github/workflows/ci.yml`
- `docs/verification.md`

This was an existing implementation defect found during rework, not an intentionally introduced exercise. The reproduction confirms risk on disposable SQLite storage; it does not establish that real application data was lost.

## Minor mistake: SQLite regression-test handles stayed open

The first disposable reproduction also reported Windows `PermissionError` during temporary-directory cleanup. Investigation showed that Python's SQLite connection context manager handles commit/rollback but does not close the connection. The regression test now wraps connections with `contextlib.closing` so handles close explicitly. This is a mistake in the uncommitted test increment, not an application incident. Explicit closure has no meaningful design tradeoff. The corrected regression passed in the full 21-test run without the earlier temporary-directory cleanup error.

## Personal investigation notes

Not yet provided. Record your own reproduction steps, hypotheses, findings, changes, verification, and reflections here or link separate study notes. Interview statements about personal work must be based on these notes rather than inferred from implementation records.
