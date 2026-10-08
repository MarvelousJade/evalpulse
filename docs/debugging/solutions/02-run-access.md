# Case 02 solution — read after investigating

Reproduction instructions: [case 02](../02-run-access.md). Faulty checkpoint: `learning/02-faulty` / `f2bbc8e`. Correct scenario controls: `001c483`. Corrected checkpoint: `learning/02-fixed`.

## Progressive hints

1. Distinguish proof of an active identity from permission to read a particular project's resources.
2. Compare the access decisions used for project requests and direct run/result requests; trace both routes.
3. Inspect the shared run lookup and check what happens after a run is found but before its data is returned.

## Diagnosis and correction

The intentionally faulty refactor removed `authorize_project(db, run.project_id, user)` from `authorized_run`. `get_current_user` still validated the session and active user, and missing runs still returned 404, but a signed-in nonmember could retrieve an existing run or its results. The owner controls passed, so an owner-only happy path would miss the mistake.

Restore project membership authorization in the shared helper before returning the run. Keep the established nonmember 404 contract, rather than changing it to 403 or permitting only the creator. A legitimate viewer's membership must still allow reads.

This restores correct behavior already present in `shaoyu/rework`. It does not repair a defect that affected the implementation branch's working tree, and no faulty image was deployed.

## Verification and tradeoffs

At the faulty checkpoint, both nonmember route cases failed with 200 instead of 404; owner-access and login assertions succeeded beforehand. After correction, both focused routes passed all owner/nonmember/unknown-run/viewer assertions (5.15 seconds), and the full SQLite suite passed all 40 tests at 82% coverage across 1,401 statements (125.28 seconds). Ruff formatting/lint passed (39 files including the local verification helper), as did strict mypy across 18 application/test/helper files. The known Starlette/httpx warning remained. Merged state `50a70f9` subsequently passed fresh 40-test SQLite/PostgreSQL suites at 82% coverage, quality/client/audit-policy checks, production audit, container rebuild/readiness, and live HTTP/Playwright workflows. The full audit's five development findings remain; see the final verification record. The full controls verify owner access, rejected nonmember access, unknown-run handling, and explicitly granted viewer access for both routes.

The shared helper avoids duplicating guards across read paths. These regressions cover metadata/results, not an exhaustive authorization audit of every endpoint, role, or timing/existence side channel. Retain the existing API contract; no new schema, role system, dependency, or authentication mechanism is needed.

## Lesson and interview explanation

Authentication answers who is requesting; object-level authorization answers whether they may read this resource. Reproduce with two identities and different memberships, compare shared route behavior, restore the resource guard, and retain both rejection and legitimate-access controls. Label this an intentionally introduced local investigation, not a production incident or personal work you have not performed.
