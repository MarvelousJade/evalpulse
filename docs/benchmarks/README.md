# Local resume measurements

## Purpose and scope

Measure EvalPulse's existing mock evaluation and caught-temporary-error recovery without inventing
customer impact. The user is a developer comparing prompt versions before a release. This harness
provides repeatable evidence of durable execution and test design, not an optimization or a new
runtime architecture. No additional application dependencies are needed.

Included: direct-engine throughput, checkpoint/result identity, score identity, provider call counts,
and a machine-readable evidence report. Excluded: HTTP latency, live queue throughput, PostgreSQL
contention, worker termination, live-model quality/cost, customer savings, and production capacity.

## Acceptance criteria

The benchmark encodes these correctness criteria as assertions:

- One warm-up and five measured runs have distinct IDs and each persists 50 passing case results.
- Timing covers only `execute_run`, including its database work; input creation and validation
  assertions are outside the timing boundary. No speed threshold is imposed: this establishes an
  absolute baseline, not a performance improvement.
- One injected temporary provider error at case 26 leaves 25 checkpoints and a queued run.
- Reinvoking the engine completes 50 results, preserves all 25 original result IDs and score IDs,
  and makes 51 total provider calls. Completed checkpoint cases are never called again.
- A failed assertion prevents publication of a successful JSON report. Existing output files cannot
  be overwritten. The runner clears `TEST_DATABASE_URL` and disables live model configuration.

## Reproduce

From the repository root with Python 3.12 or 3.13 and development dependencies installed:

```shell
python -m pip install -e ".[dev]"
python scripts/measure_resume.py --output docs/benchmarks/local-mock-new.json
```

Choose a new filename for each run. The script invokes only the benchmark through pytest, so the
existing fixtures select a temporary file-backed SQLite database and stub broker dispatch. It does
not connect to application storage, Redis, or a model provider. The ordinary `pytest` command skips
this benchmark; performance should not become a timing-sensitive CI assertion.

The report includes UTC time, base Git revision, working-tree status, SHA-256 hashes of measured
source/configuration, Python/OS/CPU metadata, key dependency versions, raw timings, per-case provider
calls, and pytest output. A dirty working tree is disclosed rather than silently attributed to the
base commit. Match the recorded source hashes when tracing the implementation. Raw logs contain
local filesystem paths; inspect reports before sharing. RAM, background load, and transitive package
versions are not captured, so this is not a fully controlled hardware comparison.

## Recorded result

[`local-mock-evidence.json`](local-mock-evidence.json) was measured on 2026-10-25 UTC with
Python 3.12.15 on Windows 11, a 12-logical-CPU AMD host, one process, and disposable SQLite.

| Metric | Observed result |
| --- | --- |
| Warm-up, excluded from summary | 0.629 seconds |
| Measured trials | 5/5 completed, 50 cases each |
| Median engine execution duration | 0.661 seconds |
| Minimum–maximum engine execution duration | 0.638–0.723 seconds |
| Median derived throughput | 4,536 mock cases/minute |
| Results and scores preserved after injected temporary failure | 25 result IDs and 25 score IDs |
| Final recovery result count | 50 passing results |
| Provider calls for recovery experiment | 51; only the failed call was repeated |
| Provider recalls for completed checkpoint cases | 0 |

Cases/minute is calculated as `50 / trial_seconds * 60`, then the median is taken across trials.
It is a rate derived from short runs, **not an observed sustained one-minute load test**. Five runs
are descriptive local evidence, not a statistical capacity study. No before/after speedup or dollar
savings were measured. The injected exception is a test stimulus, not an intentionally broken
application implementation or a newly discovered runtime defect.

`python-checks.txt` records the separate full Python suite and statement coverage. This refresh is
SQLite-only; older PostgreSQL and full-stack results remain historical evidence in
[verification](../verification.md).

## Read the implementation

1. `scripts/measure_resume.py`: isolates benchmark settings, invokes pytest, and records provenance.
2. `tests/benchmarks/test_resume_evidence.py`: workload, timing boundaries, acceptance assertions,
   fault injection, and output metrics.
3. `tests/helpers.py`: builds immutable inputs through authenticated HTTP requests; its optional
   idempotency key permits distinct trials rather than reusing an already-completed run.
4. `python/evalpulse/engine.py`: measured execution, durable checkpoints, claim release, and retry.
5. `tests/unit/test_resume_measurement.py`: report overwrite, environment, and failure safeguards.

Failures include assertion errors, unavailable dependencies, invalid output locations, or a failed
pytest subprocess. Failed measurements return a nonzero exit code and do not publish success reports.
The script deliberately has no automatic retry that could hide a failed trial.
