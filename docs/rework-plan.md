# Portfolio rework plan

## Purpose

EvalPulse helps developers evaluate prompt changes against versioned test cases and decide whether a candidate regresses relative to a baseline. Its useful unit is one repeatable release decision, not a collection of infrastructure demonstrations.

The portfolio should demonstrate immutable inputs, HTTP validation and authorization, asynchronous execution, durable results, idempotency, and explicit comparison policies. Live model responses are optional and cannot substitute for deterministic correctness tests.

Suggested motivation to personalize: “I wanted to explore how prompt changes could be tested with repeatable evidence rather than judged from a few examples.” This is suggested wording, not a claim about the author's personal experience.

## First-version boundary

Include the existing complete workflow:

1. Sign in and create a project.
2. Save a baseline prompt and a candidate version.
3. Import a dataset with expected outputs.
4. Execute both versions against the same dataset using the mock provider.
5. Compare completed runs and explain the release decision.

Preserve useful existing behavior, including optional bounded Gemini evaluation and diagnosis. Keep those extensions separate from the required demonstration. Do not add providers, orchestration layers, deployment targets, collaboration features, or scale claims during this rework without a demonstrated need.

Retain the existing Next.js dashboard, FastAPI application, SQLAlchemy database access, and Celery/Redis worker until inspection establishes a concrete reason to change them. A synchronous implementation would be simpler but would not preserve the current background-execution workflow. PostgreSQL remains the production authority; SQLite tests do not prove PostgreSQL concurrency behavior.

## Checklist and acceptance criteria

- [x] Read repository instructions and inspect Git status and recent history.
- [x] Create `shaoyu/rework` from the current implementation, preserving history.
- [x] Inspect the implementation and existing test coverage; identify a short reading path.
- [x] Record fresh formatter, linter, type-checker, test, and build results with environment details; document blocked full-stack checks and failed audits.
- [x] Reproduce the main workflow in-process and verify live HTTP, broker, and browser execution on the isolated stack.
- [x] Select safe test storage as the first focused improvement, supported by a disposable reproduction.
- [x] Implement baseline behaviors with acceptance criteria, relevant tests, journal evidence, and focused commits.
- [x] Prepare `docs/interview-guide.md` with a demonstration, reading order, five factual stories, and a one-page summary; refresh it as evidence and personal investigation notes grow.
- [x] After verifying the baseline, prepare two isolated debugging investigations with reproduction instructions separated from solutions.
- [x] Verify both corrections, preserve checkpoints with a merge commit into `shaoyu/rework`, and verify the merged result.

The baseline is accepted only when required checks pass and the main workflow is demonstrated. Blocked checks must be reported rather than counted as passing. Existing historical verification is context, not fresh evidence.

## First implementation increment: safe test storage

Static inspection found that `tests/conftest.py` retains inherited `DATABASE_URL` configuration and then drops mapped tables. Before repeating the baseline suite:

- Reproduce the hazard only against a disposable database with sentinel data.
- Select a fresh temporary SQLite database before importing application modules by default.
- Require an explicit `TEST_DATABASE_URL` for disposable PostgreSQL integration databases; reject targets without the `_test` database-name suffix. The suffix is a guardrail, not proof that a database is disposable.
- Update CI to opt into its dedicated PostgreSQL test database without changing migration configuration.
- Prove inherited application data remains intact and invalid overrides fail before database setup.
- Verify formatting, lint, typing, and affected tests, then commit the coherent increment.

## Current evidence and remaining work

The safe-storage increment is committed as `902813e`. Python verification passed 21 tests at 80% coverage, Ruff, and application/changed-test typing. The dependency increment is committed as `801d4d2`: clean installation, six audit-policy tests, the production audit without exceptions, workspace lint and typing, five client tests, and the build passed.

Host storage/startup failures were overcome: Linux Docker 29.8.2 responds, the isolated stack built and started, migrations completed, and live HTTP, Playwright, rendered-browser inspection, and the build-context export probe passed. All 36 Python tests passed on disposable PostgreSQL at 82% coverage, matching the latest SQLite result. The initial PostgreSQL runner omitted documentation fixtures; its three failures were corrected by mounting them, without application changes. Fresh Ruff formatting/lint, strict mypy, workspace lint/typing, five client tests, six audit-policy tests, and the clean production audit also passed. The working baseline meets its acceptance criteria. See the journal and verification document for exact results and commands.

The two investigations were prepared from the verified checkpoint, reproduced, fixed in separate commits, and merged into `shaoyu/rework` as `50a70f9`, preserving the faulty/fixed history and tags. The application code remains equivalent to the accepted baseline; integration adds regression coverage and debugging documentation. Fresh merged checks passed: 40 tests on both SQLite/PostgreSQL at 82% coverage, Ruff, strict mypy, workspace lint/typing, five client tests, six audit-policy tests, production audit, container rebuild/readiness, and live HTTP/Playwright workflows. The agreed local portfolio/rework scope is complete.

The refreshed full audit still flags five development records through unpatched `braces`; worker-loss recovery, broad contention/scale, and live model-quality evidence remain limitations, not claimed verification. Reliability candidates require focused reproduction before further code fixes. Personal investigation notes are for the user to supply. The user subsequently authorized local main branch `me` integration with preserved merge history. The main-worktree checks passed (40 SQLite tests, 82% coverage, Ruff lint/formatting, strict mypy, and Markdown/diff checks). Integration preserves the complete commit and merge history; pushes remain unauthorized.

## Completed increment: comparable release decisions

The release gate must compare the same immutable workload and scoring definitions. Acceptance criteria:

- Different dataset versions are rejected with HTTP 422.
- Different evaluator definitions, including options, are rejected with HTTP 422.
- Rejected requests persist no comparison record.
- Different prompt versions remain comparable when their dataset and evaluator definitions match.
- Reproduce the current behavior with deterministic completed runs before changing the API, then rerun regressions and the existing workflow.

Committed as `f6c6e99`. Verification passed: 25 Python tests at 81% coverage, Ruff lint/formatting, and application/changed-test typing. The three rejection regressions and compatible control pass. This increment adds no tables, dependencies, or infrastructure. Exact matching is deliberately conservative; semantically equivalent dataset copies or reordered scoring definitions require a separately designed compatibility policy rather than implicit assumptions.

## Completed implementation: caught temporary-provider retry recovery

Preserve queued-only execution claims. Acceptance criteria:

- A caught temporary provider error releases the current owner's run back to queued before the retry is scheduled.
- Retry skips committed results and scores, preserves the original start time, and completes the aggregate correctly.
- The configured budget allows the initial attempt plus three retries; exhaustion persists one terminal failure before ownership is released.
- Active duplicate deliveries do not claim running work; cancellation intent survives between attempts.
- Completed, failed, cancelled, and unreleased running states remain unchanged on redelivery.

Verification passed: nine focused retry tests, all 34 Python tests at 82% coverage, Ruff lint/formatting, and application/changed-test typing. The tests use direct execution and eager task contexts without a broker.

This is not general worker-loss recovery. A killed owner can still strand a running row; release-to-broker scheduling also has a gap. Do not reclaim arbitrary running work or introduce leases/fencing without a separate design and evidence.

## Completed implementation: run-submission idempotency at flush

Acceptance criteria:

- A competing submission committed after the initial lookup but before insertion is recovered from the unique constraint, returning the winner's run.
- The database contains one run, one dispatch intent, and one queued event for the submission key.
- An unrelated integrity failure is re-raised when no matching committed run exists; no partial records persist.
- The existing sequential idempotency workflow remains unchanged.

Reproduce the interleaving with a deterministic `before_flush` hook and a separate database session before moving transaction boundaries. Both focused cases and all 36 Python tests passed at 82% coverage, alongside Ruff lint/formatting and application/changed-test typing. This is a synthetic race-window regression, not a concurrency/load benchmark or production incident.

## Key reading path

1. `tests/integration/test_workflow.py`: executable core workflow (direct engine execution, not broker proof).
2. `python/evalpulse/models.py`: persistent inputs, results, and lifecycle records.
3. `python/evalpulse/datasets.py`: dataset validation and fingerprinting.
4. `python/evalpulse/api.py`: authorization, run creation, and comparison endpoints.
5. `python/evalpulse/tasks.py`: dispatch and retry configuration.
6. `python/evalpulse/engine.py`: run claims, evaluation, persistence, and completion.
7. `python/evalpulse/comparisons.py`: explicit release thresholds.

Comparison compatibility and caught temporary-provider retry recovery were reproduced and fixed. Worker-loss recovery remains a documented limitation. The run-submission flush race was reproduced and fixed with a controlled interleaving. Event sequencing remains a static investigation candidate, not a reproduced failure or accepted scope for an unrestricted rewrite.

## Change and integration boundaries

The pre-existing uncommitted `apps/web/tsconfig.json` change belongs to the user and is excluded from rework commits. Stage specific task files and inspect staged changes. Do not push, rewrite history, or merge into `me` (the locally renamed `master` branch) without authorization.

Isolated faults must stay on a separate branch. Their fixes restore intentionally altered behavior; they must not be described as defects that previously affected the implementation branch. User investigation progress does not block completing fixes, but reproduction instructions must precede solutions and explicit pause requests must be honored.
