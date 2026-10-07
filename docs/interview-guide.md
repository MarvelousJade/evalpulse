# EvalPulse interview guide

## Project introduction

**One sentence:** EvalPulse evaluates versioned prompts against a shared dataset and explains whether a candidate meets explicit regression gates.

**60-second introduction:** “Prompt changes can look good on a few examples while breaking important cases. EvalPulse stores immutable prompt and dataset versions, runs both a baseline and a candidate, and compares their measured outcomes against release thresholds. The dashboard uses Next.js and TypeScript; FastAPI validates and authorizes requests; SQLAlchemy stores durable state; Celery and Redis execute background work. The default mock provider makes the demonstration reproducible without model credentials. The latest verified in-process Python suite passed 34 tests at 82% statement coverage, and five typed client tests passed. Full-stack verification during rework is blocked by the local Docker daemon, so those tests are not evidence of live queue delivery.”

**Three-minute walkthrough:**

1. Explain the decision: would you release this candidate instead of the baseline?
2. Save two immutable prompt versions and one dataset with expected values and critical tags.
3. Queue both runs against the same cases and scoring rules.
4. Trace one case from persisted input through provider output, evaluation, result persistence, and aggregate calculation.
5. Show the comparison: pass rate, critical-case pass rate, provider errors, and P95 latency have explicit gates.
6. Explain why the synthetic lowercase candidate fails exact-match checks, and distinguish that demonstration from real model quality evidence.

## Purpose, users, and motivation

Developers changing prompts need repeatable comparisons, useful failure evidence, and stable inputs. The first useful scope is one end-to-end release decision, not a general-purpose AI platform.

Suggested motivation to personalize: “I wanted to explore how prompt changes could be tested with repeatable evidence rather than judged from a few examples.” Do not present suggested wording or implementation records as personal experience you have not completed.

Included: project isolation, immutable versions, dataset validation, mock evaluation, results, and comparison. Existing Gemini evaluation and cited diagnosis remain optional extensions. New infrastructure, providers, scale claims, and collaboration features are outside the current rework scope.

## Architecture and stack

```text
Browser → Next.js dashboard/proxy → FastAPI → PostgreSQL
                                     │          ↑
                                     └→ Redis → Celery worker
                                                  │
                                           provider → evaluators

Optional diagnosis: authorized run → read-only evidence + local runbooks → Gemini
```

### Trace one operation

The dashboard submits a run with prompt version, dataset version, provider, and evaluator definitions. The API checks authentication, CSRF, and project access, then stores the run and dispatch intent. A worker claims the run, evaluates dataset cases, persists results, and updates aggregate state. The browser reads durable state and listens for progress. Once both runs complete, the comparison endpoint evaluates release gates and persists an explainable decision.

Redis is delivery and progress infrastructure, not the authority for completed results. A result checkpoint alone does not prove that retry ownership or interrupted-run recovery is correct; those paths need dedicated investigation and tests.

### Component map

| Component | Inputs → outputs | Dependencies and likely failures |
| --- | --- | --- |
| Dashboard and typed client | User actions → authenticated HTTP requests and reports | API availability, expired sessions, partial request failure, stale UI state |
| API and schemas | Requests → validated versions, runs, comparisons | Authentication, CSRF, project authorization, invalid inputs, database/dispatch failure |
| Dataset importer | JSON/CSV → normalized cases and digest | Size/row limits, malformed shapes, inconsistent fields |
| Persistence | Versioned inputs and lifecycle changes → durable records | Constraints, transaction boundaries, concurrent updates, unavailable database |
| Dispatcher and worker | Stored run ID → case results and aggregate state | Broker delivery, provider errors, duplicate delivery, cancellation, interrupted work |
| Evaluators and comparisons | Output/expectation and aggregates/policy → scores and release gates | Invalid evaluator options, incompatible workloads, poorly justified thresholds |
| Optional diagnosis | Authorized failure evidence and retrieved runbooks → cited advisory | Model availability, cost caps, citation validation, retrieval quality |

### Why these technologies?

- **Next.js/React/TypeScript:** existing interactive workflow and typed HTTP contract. A simpler HTML interface would reduce frontend tooling but sacrifice the current dashboard.
- **FastAPI/Pydantic:** explicit HTTP validation and schemas. Understand validation versus authorization; a valid ID is not proof of access.
- **SQLAlchemy/PostgreSQL/Alembic:** durable relational data, constraints, and schema evolution. Understand flush versus commit, uniqueness, and isolation. SQLite is convenient for isolated tests but is not PostgreSQL concurrency evidence.
- **Celery/Redis:** preserve the existing asynchronous workflow and progress delivery. A synchronous API is simpler, but changes execution and failure behavior. Understand at-least-once delivery, idempotency, claim ownership, and recovery.
- **Deterministic provider:** reproducible, free tests. It exercises orchestration and gates, not the quality of a real model.
- **Optional Gemini and local retrieval:** bounded advisory functionality, kept outside the required demo. More retrieval infrastructure is unjustified for a small curated runbook set.

### Reading order

1. `tests/integration/test_workflow.py`: follow the whole behavior first.
2. `python/evalpulse/models.py`: understand persistent entities and constraints.
3. `python/evalpulse/datasets.py`: `parse_dataset` and input boundaries.
4. `python/evalpulse/api.py`: `create_run` and `create_comparison`.
5. `python/evalpulse/tasks.py`: dispatch and task configuration.
6. `python/evalpulse/engine.py`: `execute_run`, claims, checkpoints, and completion.
7. `python/evalpulse/comparisons.py`: `compare_aggregates` and threshold explanations.
8. `apps/web/app/page.tsx` and `packages/api-client/src/index.ts`: browser orchestration and the HTTP contract.

## Problem-solving stories

These are engineering records to study, not claims about your own investigation. Use your completed personal notes for first-person interview statements. Full evidence lives in [the journal](engineering-journal.md).

### 1. Prevent destructive tests from selecting application storage

**Problem →** test setup inherited an application database URL and dropped mapped tables.
**Hypothesis →** configuration precedence selected the wrong engine before fixtures ran.
**Evidence →** a disposable sentinel-table reproduction lost its marker column.
**Decision/fix →** temporary SQLite by default; explicit disposable PostgreSQL opt-in before engine initialization.
**Tradeoff →** more explicit integration setup; a `_test` suffix is only a guardrail, not proof of ownership.
**Verification →** sentinel preservation and invalid-target regressions passed in the 21-test suite; changed-test typing passed.
**Lesson →** destructive setup requires an explicit safety boundary. Commit: `902813e`.

### 2. Resume caught temporary failures without duplicating completed work

**Problem →** a temporary provider error left a run running, so a queued-only retry could not resume it.
**Hypothesis →** rollback affected the case transaction, not the earlier committed execution claim.
**Evidence →** failures before the first result and after one checkpoint both left the durable status running.
**Decision/fix →** release the caught-error owner's claim before retry; preserve checkpoints and start time; persist terminal failure on task-chain exhaustion before releasing ownership.
**Tradeoff →** the small correction does not provide leases, worker-loss recovery, exactly-once external calls, or a global per-run attempt cap.
**Verification →** nine focused tests and the 34-test suite passed, including checkpoint/score identity, duplicate active delivery, cancellation, exhaustion, and terminal states.
**Lesson →** delivery retries and durable execution ownership must agree; rollback is not a general undo operation. This was an existing defect reproduced during rework.

### 3. Preserve the asynchronous architecture without making unsupported reliability claims

**Problem →** portfolio simplicity competes with preserving the existing background workflow.
**Hypothesis →** a synchronous rewrite might reduce complexity but change useful behavior.
**Evidence →** the implementation already separates API, durable state, dispatch, worker, and progress; the workflow tests stub dispatch and call the engine directly.
**Decision →** retain the stack while focusing the demonstration on one release decision.
**Tradeoff →** queue ownership and recovery remain concepts to learn and verify.
**Verification →** in-process workflow tests passed; Docker-dependent runtime checks are blocked.
**Lesson →** explain both the architecture's purpose and what the available evidence does not prove.

### 4. Reject misleading comparisons between different experiments

**Problem →** completed runs with different datasets or scoring rules produced persisted release decisions.
**Hypothesis →** aggregate rates hid the experimental inputs used to compute them.
**Evidence →** three API regressions returned 201 instead of 422; their pass-rate gates passed even though workload or scoring changed.
**Decision/fix →** require the same immutable dataset version and exact evaluator definitions before calculating or storing a decision.
**Tradeoff →** equivalent dataset copies and reordered evaluator lists are conservatively rejected; semantic compatibility would need explicit rules.
**Verification →** all rejection cases and the compatible control passed in the 25-test suite; existing workflow, lint, formatting, and typing passed.
**Lesson →** hold workload and scoring fixed before interpreting metric differences. This was a reproduced implementation defect, not an intentional exercise or production incident.

## Demonstration script

### Verified in-process demonstration

From a development environment with project dependencies installed:

```shell
python -m pytest tests/integration/test_workflow.py::test_complete_authorized_regression_workflow -v
```

Explain the uppercase expectations, lowercase candidate transformation, baseline pass rate of 1.0, candidate pass rate of 0.0, and failed comparison. This test exercises HTTP handlers and direct engine execution, not a live Celery worker.

### Full-stack demonstration (not freshly verified during rework)

Follow [local setup](../README.md#run-locally) using disposable local development storage, keep live model calls disabled, and start Docker Desktop first. Do not reuse production database URLs or delete existing volumes.

1. Open the local dashboard and sign in with the documented local demo account.
2. Create a uniquely named project.
3. Leave baseline/candidate text at the deterministic defaults and save immutable versions.
4. Import the default three-case dataset.
5. Choose Mock and run evaluations; inspect both completed runs.
6. Compare runs and explain the failed gates, not just the red label.
7. Optional CLI smoke: `python scripts/smoke.py http://localhost:8000`.
8. Optional browser test: `npm test --workspace @evalpulse/e2e` against a running stack.

Stop if readiness fails. A rendered Compose configuration does not prove that containers work. The smoke script creates synthetic projects and runs; it must not target a production endpoint.

## Learning, limitations, and future changes

Be able to explain immutable inputs, validation, authorization, transactions, idempotency, asynchronous delivery, deterministic tests, and explicit release policies without jargon.

Current rework limitations: production dependency remediation and clean-install checks passed, but the full audit still flags 5 high-severity development package records in the unpatched `braces` lint-tool chain; PostgreSQL/Redis, container, HTTP smoke, and browser checks are blocked by the local Docker daemon. Comparison compatibility and caught temporary-provider retry recovery were reproduced and fixed. Worker-loss recovery and release-to-broker scheduling remain explicit limitations. Concurrent idempotency and event sequencing are still static investigation candidates, not reproduced incidents.

For production or scale, verify recovery ownership and concurrent writes on PostgreSQL, bound metrics cardinality, justify thresholds with representative data, review authorization boundaries, and add operational recovery procedures. Do not claim production readiness from a local synthetic demo.

Next time, establish safe test configuration and evidence boundaries before running the suite. Prefer a smaller synchronous design only if background work is no longer a requirement; otherwise simplify explanation and interfaces before replacing architecture.

## Interview questions and follow-ups

| Question | Answer outline | Understanding check |
| --- | --- | --- |
| Why build this? | Repeatable prompt-change decisions against stable cases | What can a mock provider not tell you? |
| Why immutable versions? | Preserve the inputs that produced a result | What changes if a dataset is edited in place? |
| Why Redis and PostgreSQL? | Delivery/progress versus durable authority | What happens if Redis disappears mid-run? |
| Does idempotency make retries safe? | It helps deduplicate effects; ownership and recovery also matter | Can a checkpointed running task be stranded? |
| What bug did you investigate? | Explain the disposable test-storage reproduction and fix | Why must configuration change before imports? |
| How was correctness checked? | Regression, workflow, typing, lint, build; name blocked checks | Why are SQLite tests insufficient for concurrent claims? |
| Why these release gates? | Explicit policy, measurable outcomes, explainable thresholds | Is latency meaningful with different workloads? |
| What is not proven? | Live delivery, scale, production use, or exploitation | What experiment would establish the missing evidence? |
| What would you simplify? | Keep one workflow, optional extensions, no new infrastructure without need | When would synchronous execution be preferable? |

## Quick preparation plan

1. Understand the purpose and architecture.
2. Run the main demonstration.
3. Read the key implementation files.
4. Reproduce and understand the strongest debugging examples.
5. Review decisions, evidence, and limitations.
6. Practice explaining the project without notes.

Isolated learning-branch exercises will be prepared after the working baseline is accepted. Their intentionally introduced defects must not be retold as defects that affected the implementation branch.

## One-page talking points

- **Problem:** prompt changes need stable test cases and an explainable comparison.
- **User:** a developer deciding whether a candidate prompt regresses.
- **Workflow:** version → import → evaluate baseline/candidate → compare.
- **Stack:** Next.js/TypeScript, FastAPI/Pydantic, SQLAlchemy/PostgreSQL, Celery/Redis.
- **Design:** durable authority in the database; optional model integration; reproducible mock-first tests.
- **Strongest bug story:** destructive test setup inherited application storage; prove it with disposable sentinel data; isolate before engine initialization.
- **Verified evidence:** 34 Python tests, 82% coverage, five client tests, lint, typing, build, and Compose rendering.
- **Boundary:** direct-engine tests are not live-worker proof; historical results are not fresh verification.
- **Outstanding work:** remaining development advisories, Docker-dependent baseline, targeted reliability investigations, and learning exercises.
- **Personal reflection:** supply your completed investigation notes; do not memorize invented first-person experience.
