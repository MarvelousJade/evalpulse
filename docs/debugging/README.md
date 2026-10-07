# Debugging investigations

Two isolated investigations will have separate faulty checkpoints and fixes on `shaoyu/learning`. The starting implementation is the verified baseline `7d26f9b`. The faults are intentionally introduced for study; neither describes a production incident or a defect that affected `shaoyu/rework`.

## Study safely

1. Read [case 01](01-critical-policy.md) or [case 02](02-run-access.md), not the solution directory, fix diffs, or engineering journal. The journal records implementation diagnoses; read it after your own investigation.
2. Use a separate worktree at the faulty checkpoint listed in the case. Do not overwrite your existing work or switch a dirty checkout.
3. Install development dependencies in that worktree. Keep `TEST_DATABASE_URL` unset for safe temporary SQLite, or explicitly provision a disposable PostgreSQL database ending in `_test`.
4. Reproduce, write down expected/actual behavior, list competing hypotheses, and inspect evidence before editing.
5. Add or extend a regression and verify your correction plus controls and the full suite.
6. Record your own investigation and reflections in separate study notes before reading solutions.

Do not build or deploy faulty checkpoints, point them at application databases, expose them to other users, or treat them as release candidates. The existing Docker stack remains the correct baseline while these investigations run.

Checkpoint references will be filled in after their failures are verified. Solutions and progressive hints will be kept separate; ask for a hint if you want one without the full diagnosis.

Implementation fixes and integration proceed independently of your study progress. The final learning branch will be corrected and tested before a merge commit into `shaoyu/rework`; the faulty history remains available for study.
