# Debugging investigations

Two isolated investigations have preserved faulty checkpoints and separate verified fixes on `shaoyu/learning`. The starting implementation is the verified baseline `7d26f9b`. The faults are intentionally introduced for isolated reproduction; neither describes a production incident or a defect that affected `shaoyu/rework`.

## Reproduce safely

1. Read [case 01](01-critical-policy.md) or [case 02](02-run-access.md), not the solution directory, fix diffs, or engineering journal. The journal records implementation diagnoses; read it after your own investigation.
2. Use a separate worktree at the faulty checkpoint listed in the case. Do not overwrite your existing work or switch a dirty checkout.
3. Install development dependencies in that worktree. Keep `TEST_DATABASE_URL` unset for safe temporary SQLite, or explicitly provision a disposable PostgreSQL database ending in `_test`.
4. Reproduce, write down expected/actual behavior, list competing hypotheses, and inspect evidence before editing.
5. Add or extend a regression and verify your correction plus controls and the full suite.
6. Record your own investigation and reflections in separate investigation notes before reading solutions.

Do not build or deploy faulty checkpoints, point them at application databases, expose them to other users, or treat them as release candidates. The existing Docker stack remains the correct baseline while these investigations run.

Preserved faulty references: case 01 `learning/01-faulty`; case 02 `learning/02-faulty`. Each checkpoint contains only its own unresolved intentional defect. Solutions and progressive hints are kept separate; ask for a hint if you want one without the full diagnosis.

The corrected state was merged into `shaoyu/rework` as `50a70f9`, preserving the faulty/fixed history with a merge commit. The merged state passed fresh SQLite/PostgreSQL suites (40 tests, 82% coverage), formatting/lint/typing, client/audit-policy tests, production audit, container rebuild/readiness, and live HTTP/Playwright workflows. The full audit still flags five development dependency records; see the verification document for boundaries. The fixes restore already-correct baseline behavior; the integration adds regression controls, shared test setup, and debugging documentation, not a repair to a defect that affected the implementation branch. Your investigation progress does not block implementation verification.

## Python-only setup for an isolated worktree

After creating the separate worktree listed in a case and changing into its directory, use Python 3.12 or 3.13. No Docker or Node setup is needed for these two focused investigations.

```cmd
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
set "TEST_DATABASE_URL="
.venv\Scripts\python.exe -m pytest tests/integration/test_critical_aggregate.py -v
```

Use `tests/integration/test_run_authorization.py` instead for case 02. On Linux/macOS, use `.venv/bin/python` and `unset TEST_DATABASE_URL`. Clearing the explicit test target selects disposable temporary SQLite; never target application storage. The faulty reference is expected to fail its designated regression, while the corrected reference should pass.
