# Case 02: run data crosses a project boundary

## Simulated reviewer report

> A reviewer who is not a member of a private project can fetch its completed run metadata and case results if they know the run ID. The project owner can access the same data normally.

This is an intentionally introduced local defect, not a production incident. The faulty checkpoint is pending verification; the starting correct baseline is `7d26f9b`. Use only the isolated synthetic users created by the regression; do not investigate real users or deployments.

## Reproduce

In a separate development worktree at the faulty checkpoint, run:

```shell
python -m pytest tests/integration/test_run_authorization.py -v
```

The regression creates an owner's mock run and a separate active reviewer with no project membership. It checks both `/api/runs/{id}` and `/api/runs/{id}/results`.

Expected behavior: owner `200`, authenticated nonmember `404`, unknown run `404`, then reviewer `200` after explicitly granting viewer membership. The faulty checkpoint returns successful responses where access should be denied.

## Acceptance criteria

- Being signed in is not sufficient to read another project's run or results.
- Owner and legitimate viewer access still work; unknown runs remain `404`.
- Both route regressions and the full Python suite pass.
- Your notes distinguish authentication from object-level authorization and explain how the correction covers shared access paths.

## Investigation notes

Record the identities, memberships, route, expected/actual status, competing hypotheses, evidence, correction, controls, and remaining risks. Do not inspect fix commits or solution files until you want the diagnosis. Do not deploy the faulty checkpoint.
