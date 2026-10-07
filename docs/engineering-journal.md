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

## Portfolio documentation: one workflow and bounded evidence

### Hurdle and decision

The existing documentation explains technologies but does not provide one short study path tying purpose, implementation, failure investigation, and verified evidence together. Prepared `docs/interview-guide.md` with introductions, an architecture map, component contracts and failure cases, an ordered reading path, three factual engineering stories, demonstration steps, questions, and a one-page summary.

Use the guide for quick preparation and the journal for detailed evidence. Personal investigation claims remain separate; no personal motivation or learning was invented. The README now links both documents and replaces an unsupported blanket retry-safety claim with the distinction between result checkpointing and demonstrated recovery behavior.

### Tradeoffs and verification

A short guide cannot carry every hypothesis and command, so it links the journal and verification notes. Historical functional results, fresh rework results, blocked runtime checks, and unresolved dependency advisories remain distinct. Combined README/guide/plan checks passed for unique headings, balanced code fences, existing local-link targets, and scoped whitespace. The README and plan diffs were reviewed. No Markdown-specific formatter or linter is configured in the repository; these were structural and manual documentation checks, not application test reruns. No new application behavior is included in this documentation increment.

### References and provenance

- Safe test-storage fix: `902813e`.
- Dependency remediation: `801d4d2`.
- `README.md`, `docs/interview-guide.md`, `docs/rework-plan.md`, and `docs/verification.md`.

This is a documentation and explanation hurdle, not a production incident. Learning exercises remain deferred until the working baseline is accepted.

## Investigation: incompatible runs could produce a misleading release decision

### Problem and acceptance criteria

A regression gate is meaningful only when baseline and candidate use the same workload and scoring definitions. Static inspection found that the comparison endpoint checks project membership and completed status but does not compare dataset version IDs or evaluator snapshots.

Expected: reject incompatible comparisons with HTTP 422 and persist no decision. Preserve comparisons across different prompt versions when dataset and evaluator definitions match.

### Reproduction

`tests/integration/test_comparisons.py` creates real immutable versions and runs through the API, executes the deterministic engine directly, then requests comparisons. Cases cover different dataset versions, different evaluator types, different regex options, and a compatible control. The differing workloads or scoring rules are chosen so each candidate scores 1.0 despite a lowercase prompt change; the compatible control scores 0.0.

```shell
.venv\Scripts\python.exe -m pytest tests/integration/test_comparisons.py -q
```

All three incompatible cases failed their rejection assertion: the API returned HTTP 201 and persisted comparison decisions instead of HTTP 422. Pass-rate checks passed at 1.0 for these incompatible workloads or scoring rules. Some final decisions were false because measured mock latency exceeded the default threshold; no claim is made that every reproduced comparison falsely approved a release. The defect is creating a decision for incomparable runs in the first place.

This is an in-process API/engine reproduction, not a live-broker experiment or production incident. Shared HTTP setup was moved to `tests/helpers.py` so the existing workflow and new regressions do not duplicate helpers.

### Root cause and fix

The endpoint treated project membership and completion as sufficient comparability. Aggregate rates do not encode which cases or scoring definitions produced them. Added dataset-version and evaluator-snapshot equality checks before aggregate comparison and persistence. Different prompt versions remain valid candidates.

### Tradeoffs and alternatives

Exact equality is small, explicit, and preserves immutable provenance. It intentionally rejects equivalent dataset copies and reordered scoring definitions. Digest-based or semantic equivalence could permit more comparisons, but requires rules for case identity, order, tags, options, and scoring semantics; that complexity is not justified for this increment. No schema or provider behavior changes are needed.

### Verification, lesson, and interview explanation

Fresh checks passed on Windows/Python 3.12.10: Ruff lint, Ruff format check (34 files), strict mypy across 18 application and changed-test source files, and the full pytest coverage run (25 tests, 81% coverage across 1,390 statements, 121.90 seconds). All three incompatible cases now reject with HTTP 422 and persist no comparison; the compatible control and existing workflow pass. One Starlette/httpx deprecation warning remains. The lesson is that a metric comparison needs an experimental contract: hold workload and scoring fixed before interpreting differences. First reproduce acceptance of incompatible inputs, then reject them at the decision boundary and prove that rejection leaves no persisted decision.

### References and provenance

- `python/evalpulse/api.py`: `create_comparison`.
- `tests/integration/test_comparisons.py` and `tests/integration/test_workflow.py`.
- `tests/helpers.py` and `docs/architecture.md`.

This defect existed before the continuation and was reproduced during ordinary rework. It was not intentionally introduced for a learning exercise. No production impact or personal investigation experience is inferred.

### Minor implementation mistake

An exact-text edit initially matched both `prompt` and `candidate_prompt` assignments and was rejected without changing the file. Used indentation-specific matches and reapplied successfully. No behavioral bug resulted; no meaningful tradeoff exists.

### Continuation runtime check

A fresh `docker info --format "{{.ServerVersion}}"` attempt timed out after 45 seconds with no server version. Unlike the earlier missing-pipe error, this provides no specific daemon error; readiness is unproven. A read-only process check showed Docker Desktop and `com.docker.backend` processes present and responding. That does not establish engine/API readiness or a specific root cause. The combined output did not establish a service status. No restart, container mutation, or volume deletion was performed. Do not rerun readiness commands merely to wait or treat the timeout as a passing check.

### Branch boundary

The user renamed local `master` to `me`. Work continues on `shaoyu/rework`; remote branches are unchanged, and integration into `me` still requires authorization. Historical kickoff references to `master` describe the branch name at that time.

## Investigation: caught temporary provider errors strand running runs

### Expected behavior and reproduction

An ordinary temporary provider error should permit the configured retry to continue, without re-evaluating committed cases. Static inspection found that execution commits `running`, then only rolls back the current transaction on a temporary error. Celery retries subsequently attempt a queued-only claim, so rollback alone cannot release the previously committed claim.

Created deterministic tests with a provider that fails once before the first result or after one checkpoint. The first attempt is expected to raise the temporary error and release the run to queued; the next attempt should complete while retaining existing result/score IDs and the original start time. The pre-fix reproduction completed: both cases failed because the run remained `running` instead of `queued`. This confirms that rollback did not undo the previously committed claim:

```shell
.venv\Scripts\python.exe -m pytest tests/integration/test_retries.py -k temporary_errors_release -q
```

Additional acceptance tests cover the bound Celery task's three-retry budget using eager request contexts (no broker), a second-session delivery during an active provider call, cancellation between attempts, terminal redelivery, and a stranded running-row boundary. These are synthetic in-process checks, not a live-worker or PostgreSQL concurrency proof.

### Root cause, correction, and tradeoffs

Rollback only affects the current uncommitted transaction; the run's `running` claim was already committed. Retry scheduling and execution ownership were therefore inconsistent.

The temporary-error handler now releases only the run whose current execution caught the error and remains running, commits a retry event, then rethrows for existing Celery backoff. The bound task passes retry eligibility into execution. On exhaustion, execution persists terminal failure before releasing ownership; releasing first would allow another claimant before failure is recorded. Queued-only claims, committed case checkpoints, and cancellation intent are preserved. The claim update uses `coalesce` so an existing start time is retained rather than reset at each attempt.

The ownership assumption is explicit: only the successful queued-only claimant executes the run, and no external code forcibly resets its running state. After the retry-release commit, the old invocation performs no further run/result/event writes.

This no-schema-change correction intentionally does not recover killed owners or close the database-release/broker-scheduling gap. General recovery would require explicit ownership/leases with fencing or an equivalent proven mechanism. A duplicate delivery after a legitimate release may claim queued work first; the atomic queued-only claim still selects one owner. The retry budget belongs to a Celery task chain, not a durable global per-run attempt counter across independent deliveries. Provider calls interrupted before checkpointing may repeat; no stronger cost or exactly-once guarantee is claimed.

### Lesson and interview explanation

Retries combine delivery scheduling with durable execution ownership. Rolling back the current case does not undo an earlier committed claim. Reproduce a transient failure before and after a checkpoint, release only the caught-error owner's claim, preserve completed work, and terminate exhausted attempts before allowing another owner. Explain the explicit limits: no generic reclamation, no exactly-once external calls, and no durable global attempt cap.

### Runtime blocker investigation

`docker context show` selected `desktop-linux`. `wsl --list --verbose` showed the `docker-desktop` distribution stopped, while the normal development distribution was running. This explains why Docker Desktop GUI processes being present did not prove a usable Linux backend. `docker desktop start` exited successfully but only reported “Docker Desktop is already running.” It did not establish a recovered engine, so no new readiness pass is claimed and the command is not repeated merely to wait. Starting the engine in the Desktop UI or an explicitly authorized restart is needed next. No restart/reset, container deletion, or volume removal was performed. Engine readiness still requires a real API response.

### References and provenance

- `python/evalpulse/engine.py`, `python/evalpulse/tasks.py`.
- `tests/integration/test_retries.py`.
- Previous comparison fix: `f6c6e99`.

The two pre-fix reproductions failed at the expected state assertion. Post-fix verification passed on Windows/Python 3.12.10: Ruff lint, Ruff format check (35 files), strict mypy across 16 application/changed-test source files, all 9 focused retry tests, and the full suite (34 tests, 82% statement coverage across 1,401 statements, 191.06 seconds). Checkpoints and score IDs, original start time, cancellation intent, the task-chain retry budget, duplicate active delivery, and terminal/unreleased states passed their assertions. One Starlette/httpx deprecation warning remains. No live-broker, worker-kill, or PostgreSQL concurrency check ran. This is existing behavior reproduced during ordinary development, not an intentionally introduced defect or a production incident.

## Authorized Docker restart and full-stack verification

### Runtime recovery

The user explicitly authorized a Docker Desktop restart. `docker desktop restart` completed, then `docker info --format "Server={{.ServerVersion}} OSType={{.OSType}}"` returned `Server=29.6.1 OSType=linux`. This resolves the engine-readiness blocker; it does not itself verify application containers.

No containers or volumes were deleted. Full-stack verification uses a separate `evalpulse-rework` Compose project, web/API ports 13000/18000, the documented placeholder environment, an explicit local migration URL, and disabled live inference. Real `.env` contents are not used for this stack.

### Build-context hurdle

Before building, inspection found that `.dockerignore` excluded source-control and dependency directories but not environment files or local task/cloud metadata. Targeted Dockerfile COPY instructions reduce image exposure, but do not justify sending private files to the builder.

Added recursive `.env*` exclusions while retaining documented `.env.example` files, plus `.pi` and `.neon` exclusions. This is preventive hardening; no credential exposure, tracking, or compromise is established by the finding.

### Verification and tradeoffs

The isolated application build/start failed. Python package installation reported `OSError: [Errno 5] Input/output error`, and both Python and web build steps failed writing `/var/lib/docker/buildkit/containerd-overlayfs/metadata_v2.db` with `read-only file system`. The engine's successful version response did not establish writable build storage. Full-stack application startup and browser checks were not verified; further builds are paused rather than forcing writes or resetting storage. The BuildKit bind-mounted context probe executed all exclusion assertions successfully: real environment files and local metadata were absent while the example environment was present. The probe did not copy the context into an image layer. Image export then failed with `commit failed: input/output error`, so the overall probe build failed and no completed image artifact is claimed. Read-only capacity inspection reported C: free space = 0 bytes and G: free space = 101,397,356,544 bytes. `docker system df` also failed while reading snapshot storage with an input/output error. Disk exhaustion is a likely contributor, not proof that Docker's filesystem is otherwise healthy. Free host space before another build; any reset, destructive cleanup, or data relocation needs separate authorization and backups. No pruning, volume deletion, or Docker reset is authorized or performed. Recursive exclusion is deliberately conservative; runtime configuration belongs in environment injection rather than baked-in files. No meaningful functionality tradeoff is intended.

### References and provenance

- `.dockerignore`, `compose.yaml`, and the three application Dockerfiles.
- Probe artifact: `.pi/verification/Dockerfile.context-probe` (uncommitted local verification support).

The Docker startup hurdle was an observed local environment issue, not an application or production incident. Full-stack and learning-exercise results will be recorded only after they run.

## Continuation: partial space recovery and run-submission race

### Docker storage readiness

A fresh host-capacity check reported C: free space = 2,516,295,680 bytes and G: free space = 104,680,407,040 bytes. The chained Docker engine query timed out after 60 seconds, so Docker storage usage did not run. Some host space was freed, but usable Docker storage is not established. A single Desktop restart/readiness sequence under the existing restart authorization timed out after 240 seconds without a new engine version or storage report. The sequence is not repeated blindly, and no recovered runtime is claimed. C: remains tight for builds; free more host space or use Docker Desktop's supported disk-image relocation workflow with backups and explicit authorization. No pruning, reset, volume deletion, or relocation was performed.

### Run-submission problem and hypothesis

Static inspection found that `create_run` flushes the new uniquely keyed run before entering its `IntegrityError` handler. A competing request can commit after the initial lookup returns no existing run; the losing insert would then fail at flush outside recovery rather than returning the committed winner.

### Reproduction and acceptance criteria

`tests/integration/test_idempotency.py` injects a separate-session committed run, dispatch intent, and queued event immediately before the original flush. It then expects the API to return the winner and leave exactly one of each record. A second synthetic case raises an unrelated integrity failure and expects it to propagate without partial persistence.

```cmd
.venv\Scripts\python.exe -m pytest tests/integration/test_idempotency.py -q
```

The competing-commit case failed with an unhandled `IntegrityError` at `api.py`'s explicit `db.flush()`: SQLite's unique constraint on `(created_by_id, idempotency_key)` rejected the losing insertion before the recovery handler was entered. The unrelated-failure control passed. The injection controls a realistic interleaving but is not a live concurrent HTTP/load experiment. The unrelated error is a labelled synthetic test condition, not an observed incident.

### Tradeoffs and provenance

Moved insertion, explicit flush, dispatch/event creation, and commit inside the same recovery boundary while retaining database uniqueness and rollback. The failure handler can now look up the committed winner after a flush collision; it still re-raises if no matching run exists. No locks, schema changes, or new dependencies were added. Fresh checks passed on Windows/Python 3.12.10: Ruff lint, Ruff format check (36 files), strict mypy across 16 application/changed-test source files, both focused idempotency cases, and all 36 Python tests (82% coverage across 1,401 statements, 183.71 seconds). Recovery returned the committed winner and left one run/dispatch/event; the unrelated-error control propagated without partial records. The existing sequential workflow passed. One Starlette/httpx warning remains. Live PostgreSQL contention and broker behavior were not tested. A pre-insert lookup alone cannot guarantee uniqueness under contention; the database constraint is the authority. This is an existing implementation defect reproduced during rework, not an intentionally introduced learning defect or production incident.

### Lesson, interview explanation, and references

A SQLAlchemy flush can execute constraint-checked SQL before commit. Recovery must cover the point where the error can actually occur, not merely the final commit. Reproduce the interleaving deterministically, move all related writes inside the rollback/recovery boundary, and verify both successful deduplication and propagation of unrelated failures.

- `python/evalpulse/api.py`: `create_run`.
- `tests/integration/test_idempotency.py`.
- Existing sequential coverage: `tests/integration/test_workflow.py`.

## Personal investigation notes

Not yet provided. Record your own reproduction steps, hypotheses, findings, changes, verification, and reflections here or link separate study notes. Interview statements about personal work must be based on these notes rather than inferred from implementation records.
