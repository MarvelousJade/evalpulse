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

## Dependency remediation: audited runtime and development packages

### Problem and reproduction

The restored lockfile installation passed functional checks but failed the repository's production dependency audit. Reproduce with `node scripts/audit-production.mjs` and `npm audit --json`. The production report rejected Next.js, Sharp, and source-map-js; the complete report contained 13 vulnerable package records. This is dependency-advisory evidence, not proof of exploitation or a deployed incident.

### Investigation and evidence

Inspected the exact advisory ranges, npm's suggested fixes, and package registry metadata:

```shell
npm view next@16.4.0 engines dependencies --json
npm view sharp@0.35.5 engines --json
npm view vitest@4.1.11 engines dependencies --json
npm view eslint-config-next@16.4.0 dependencies --json
npm view source-map-js@1.2.2 version --json
```

Next.js and Sharp require Node >=20.9.0; Vitest 4.1.11 supports Node 22 and 24, matching the project range. Vitest 4.1.11 depends on the patched mocker version and no longer lists Tinypool. This metadata supports trying the upgrade but does not prove application compatibility. The current production audit also contained an obsolete Next/PostCSS exception tied to an older Next release. Lockfile review showed Vitest selected Vite 8.3.3, whose Node requirement is >=22.12.0 within the supported project major versions. Tightened the root Node minimum from 22 to 22.12 to avoid advertising unsupported earlier Node 22 releases. Verification ran on Node 24.19.0; Node 22 compatibility is based on engine metadata and remains CI's execution path.

### Decision and fix in progress

Align Next.js and eslint-config-next at 16.4.0, update the explicit Sharp pin to 0.35.5, and upgrade both Vitest consumers to ^4.1.11. Refresh the lockfile without automatic force-fixes. Remove the obsolete advisory exception rather than widening it; fail the audit when npm reports an audit error or cannot complete normally.

Acceptance criteria: production audit passes with no exceptions; web lint, type checks, client tests, and production build pass; installation and lockfile agree; remaining full-audit findings are identified rather than hidden. Review the Vitest major upgrade for actual test compatibility.

### Tradeoffs and alternatives

A smaller patch-only update is preferred when it eliminates the reported vulnerabilities. Registry evidence supports Next 16.4.0 and Vitest 4.1.11; the latter changes a major version, so test verification is essential. Keeping vulnerable versions merely to avoid tooling changes leaves the audit failure unresolved. A forced automated update could introduce unrelated major upgrades and is not justified. Overrides must not substitute incompatible transitive versions without evidence.

### Verification

`npm install --ignore-scripts` refreshed the lockfile: 9 packages added, 16 removed, and 25 changed. The production audit passed with no vulnerabilities and no advisory exceptions. Workspace lint and typing, all 5 client tests under Vitest 4.1.11, script syntax validation, and the Next.js 16.4.0 production build passed. The web unit-test command exited successfully with no test files; it is not evidence of UI test coverage.

Six audit-policy tests passed: clean report, vulnerable dependency, registry error, failed command, terminated command, and invalid JSON. CI now runs those tests before the real audit.

Installation still reported 7 high-severity development dependency findings. The full report identified @next/eslint-plugin-next, eslint-config-next, fast-glob, micromatch, braces, brace-expansion, and js-yaml. Registry inspection showed `braces` latest is 3.0.3, still in the affected range. npm suggested downgrading eslint-config-next to 14.2.35 for that chain; this would misalign it with Next 16 and is not accepted. A range-respecting `npm update brace-expansion js-yaml --ignore-scripts` changed three transitive packages and eliminated those two package findings. Clean `npm ci --ignore-scripts` then passed, followed by all 6 audit-policy tests, the production audit, workspace lint and typing, all 5 client tests, and the Next.js 16.4.0 build. The final `npm audit --json` exited 1 with 5 high-severity package records in the unpatched braces chain: braces, micromatch, fast-glob, @next/eslint-plugin-next, and eslint-config-next. These are five package records propagated from the same underlying advisory, not five independent demonstrated exploits. The complete audit is not passing. No audit exceptions or unsupported major overrides were added. Docker runtime verification remains blocked by the unavailable daemon.

### Lesson, references, and provenance

Functional correctness and dependency security are separate checks. A successful build does not establish a clean audit, and an audit finding does not establish exploitation. Evidence must include exact package versions, affected ranges, compatibility constraints, and actual post-update results.

- Previous test-isolation increment: `902813e`.
- `package.json`, `apps/web/package.json`, `packages/api-client/package.json`, and `package-lock.json`.
- `scripts/audit-production.mjs`.

These findings arose from existing dependencies during baseline verification, not from intentionally introduced exercises. Personal learning claims remain reserved for completed study notes.

## Minor mistake: documentation validation command syntax

The first interview-guide structure check did not execute because its Python command used `%%` instead of a valid parity expression. The traceback showed a `SyntaxError` before any checks ran. Replaced the expression with a bitwise parity check and reran it; unique headings, balanced code fences, and existing local link targets passed. The guide-only whitespace check also passed. This is an uncommitted verification-command mistake, not a project defect. There is no meaningful design tradeoff; keep shell quoting separate from embedded-language syntax and never report a failed command as verification.

## Personal investigation notes

Not yet provided. Record your own reproduction steps, hypotheses, findings, changes, verification, and reflections here or link separate study notes. Interview statements about personal work must be based on these notes rather than inferred from implementation records.
