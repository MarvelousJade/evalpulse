# EvalPulse resume evidence

Use measured engineering outcomes, not invented business impact. EvalPulse helps developers evaluate
prompt changes against immutable datasets and explicit regression policies. Suggested motivation to
personalize: “I wanted to test prompt changes with repeatable evidence rather than a few examples.”
Only make first-person claims about work you can accurately describe and explain.

## Verified measurements

Evidence was collected on 2026-10-25 UTC. These are local synthetic results. The
[procedure and acceptance criteria](benchmarks/README.md) and
[raw report](benchmarks/local-mock-evidence.json) preserve the context needed to defend each claim.
The report records base revision `af69de0`, uncommitted measurement changes, and source hashes;
it does not claim that the new harness existed in that base commit.

| ID | Supported claim | Evidence and boundary |
| --- | --- | --- |
| E01 | 50 mock cases evaluated in a median 0.661 seconds across five measured trials | Direct engine, file-backed SQLite, one process; excludes HTTP setup and live queue/model time. Range: 0.638–0.723 seconds. No measured improvement over an earlier implementation. |
| E02 | Recovery preserved 25 result IDs and 25 score IDs, completed 50 results, and did not re-call completed cases | One injected temporary provider error; 51 total provider calls. Direct engine reinvocation, not worker-kill recovery or exactly-once external execution. |
| E03 | 43 tests passed at 82% statement coverage across 1,401 application statements | See [raw suite output](benchmarks/python-checks.txt): 43 passed, one opt-in benchmark skipped, one deprecation warning. The benchmark passed separately. This refresh uses SQLite, not PostgreSQL. |

## Resume bullet options

Use two or three bullets total for the project. Prioritize purpose and engineering behavior over a
large-looking rate. The following wording is supported by E01 and E02:

- Built a versioned prompt-evaluation workflow with persisted results and release gates; benchmarked
  50 mock cases at a median **0.661 seconds** across five local SQLite trials.
- Verified checkpoint-aware retry recovery by injecting a temporary provider failure, preserving
  **25 completed results and scores**, and completing all **50 cases** without re-calling completed
  cases.

Additional testing bullet supported by E03:

- Validated the evaluation workflow with **43 automated Python tests** at **82% statement coverage**,
  including retry, authorization, and comparison checks on disposable SQLite storage.

Optional performance wording, only when the context fits:

- Measured **4,536 mock cases/minute** derived from five 50-case direct-engine trials, with a
  **0.661-second median** run time on local SQLite.

Prefer the first duration-based bullet: the rate is extrapolated from short runs, not a sustained
load test. This increment measured existing behavior; it did not implement the underlying retry fix.
Choose verbs that accurately reflect your actual contribution.

Do not claim production traffic, customer time savings, model accuracy improvement, infrastructure
cost reduction, exactly-once processing, or a percentage performance gain from these measurements.

## Interview explanation

**Problem:** a working demo alone does not show how efficiently execution works or what retry safety
actually means.

**Approach:** fix the workload, use one excluded warm-up and five distinct measured runs, then inject
one temporary error after 25 persisted results. Count provider calls and compare stored identities,
not just the final “completed” label.

**Result:** median 0.661-second execution for 50 mock cases; the recovery experiment completed all
50 cases and retained 25 original result and score records with no completed-case recalls.

**Tradeoff:** deterministic SQLite measurements are inexpensive and reproducible, but do not exercise
Celery delivery, PostgreSQL contention, external model latency, or worker termination. Those need
separate experiments.

**Lesson:** define the claim and its evidence boundary before selecting a resume number. Test counts
and coverage support correctness stories but do not establish production reliability.

## Adding another claim

Copy this record for each new measurement:

```text
ID / status: Planned | Verified | Historical
Question and user value:
Metric and acceptance criterion:
Workload, provider, evaluator, and dataset digest:
Environment and dependency versions:
Exact reproduction command:
Trials, failures, and timing boundaries:
Baseline (if claiming an improvement):
Observed result and raw artifact:
Revision, dirty status, and source hashes:
Interpretation, tradeoffs, and what is not proven:
Supported resume wording:
Interview explanation:
```

Next useful experiments, not yet performed here: a fixed-workload live Celery/PostgreSQL benchmark;
labeled synthetic regression scenarios with unchanged controls; and diagnosis cache provider-call
counts. Measure real-model cost only with actual token usage and dated provider pricing. Measure
team time savings only with observed workflows and participants, not an imagined manual baseline.
