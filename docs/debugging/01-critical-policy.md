# Case 01: a surprising critical-policy failure

## Simulated reviewer report

> One critical case still matches exactly, while two ordinary cases fail after a candidate lowercases their outputs. The overall score is one out of three, but the critical policy reports a failure even though the critical case passed.

This is an intentionally introduced local defect, not a production incident. Faulty checkpoint: `learning/01-faulty`. Starting correct baseline: `7d26f9b`; verified scenario controls: `001c483`.

Create a separate worktree from the repository root (use unused directory/branch names):

```shell
git worktree add -b debug/case-01 "../evalpulse-case-01" learning/01-faulty
```

## Reproduce

In a separate development worktree at the faulty checkpoint, run:

```shell
python -m pytest tests/integration/test_critical_aggregate.py -v
```

The test uses a mock lowercase candidate and three cases: one tagged `critical`, two ordinary. Its passing-critical scenario expects overall pass rate `1/3`, critical pass rate `1.0`, and a passing critical gate. The control changes the inputs so the critical case fails while both ordinary cases pass: overall `2/3`, critical `0.0`, failed critical gate.

The policy-control baseline is synthetic: latency and error evidence are held equal to focus on the critical gate; ordinary failures are permitted for this check. This is not a load benchmark or a claim that such a permissive policy suits production.

## Acceptance criteria

- Critical-policy outcomes match the critical cases, independently of ordinary-case outcomes.
- The overall score still includes all three cases.
- Both positive and negative controls and the full Python suite pass.
- Your notes identify the faulty calculation and explain the boundary cases and tradeoff.

## Investigation notes

Before seeking hints, record what you expect, the actual values, at least two hypotheses, the evidence that distinguishes them, your change, and verification. Do not inspect fix commits or solution files until you want the diagnosis.
