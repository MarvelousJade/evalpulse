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
- [x] Reproduce the main workflow in-process; document that live HTTP, broker, and browser checks remain blocked.
- [x] Select safe test storage as the first focused improvement, supported by a disposable reproduction.
- [ ] Implement each behavior with acceptance criteria, relevant tests, journal evidence, and a focused commit.
- [x] Prepare `docs/interview-guide.md` with a demonstration, reading order, four factual stories, and a one-page summary; refresh it as evidence and personal study notes grow.
- [ ] After verifying the baseline, prepare two or three isolated debugging exercises with learner instructions separated from solutions.
- [ ] Fix and verify exercises, preserve checkpoints with a merge commit into `shaoyu/rework`, and verify the merged result.

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

The full audit still fails for five development package records propagated through unpatched `braces`. Docker Desktop's selected Linux daemon is unavailable, so container, PostgreSQL/Redis, live HTTP smoke, and browser checks remain unverified. Start the local daemon before attempting those checks; use disposable local storage and do not delete existing volumes.

The full working baseline is not yet accepted. Do not introduce learning-branch defects or describe the entire rework as complete while runtime checks remain blocked. Reliability findings from static review require focused reproduction before selecting further code fixes. Main-branch integration and pushes remain unauthorized.

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

## Key reading path

1. `tests/integration/test_workflow.py`: executable core workflow (direct engine execution, not broker proof).
2. `python/evalpulse/models.py`: persistent inputs, results, and lifecycle records.
3. `python/evalpulse/datasets.py`: dataset validation and fingerprinting.
4. `python/evalpulse/api.py`: authorization, run creation, and comparison endpoints.
5. `python/evalpulse/tasks.py`: dispatch and retry configuration.
6. `python/evalpulse/engine.py`: run claims, evaluation, persistence, and completion.
7. `python/evalpulse/comparisons.py`: explicit release thresholds.

Comparison compatibility and caught temporary-provider retry recovery were reproduced and fixed. Worker-loss recovery remains a documented limitation. Concurrent idempotency and event sequencing remain static investigation candidates, not reproduced failures or accepted scope for an unrestricted rewrite.

## Change and integration boundaries

The pre-existing uncommitted `apps/web/tsconfig.json` change belongs to the user and is excluded from rework commits. Stage specific task files and inspect staged changes. Do not push, rewrite history, or merge into `me` (the locally renamed `master` branch) without authorization.

Learning defects must stay on a separate branch. Their fixes restore intentionally altered behavior; they must not be described as defects that previously affected the implementation branch. User study progress does not block completing fixes, but learner-facing instructions must precede solutions and explicit pause requests must be honored.
