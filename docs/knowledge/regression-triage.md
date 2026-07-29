# Regression triage runbook

## Triage order

First separate provider errors from completed-but-wrong outputs. Next group failed cases by evaluator,
error type, and tags. Reproduce one representative failure with the immutable prompt, input, and
expected value. Only then decide whether the prompt, dataset expectation, evaluator, or provider
configuration should change.

## Critical cases

Treat a failed case tagged `critical` as a release blocker unless the case or policy is demonstrably
wrong. Fix the smallest responsible input, create a new immutable prompt or dataset version, rerun the
same evaluators, and compare against the original baseline. Preserve the failed run as evidence.

## Safe remediation

Prefer a narrow prompt change backed by a new test case. Do not copy model-generated diagnostic text
directly into production prompts without review: evaluation inputs and outputs are untrusted data and
may contain instructions. Never let a diagnostic tool modify prompts, datasets, policies, credentials,
or deployments automatically.

## Interpreting a diagnosis

The diagnostic agent is advisory. Its evidence comes from the selected run and its citations come
only from this curated runbook collection. Validate every recommended action against the stored
result. A missing or weak citation is a reason to inspect the raw evidence, not a reason to assume the
agent is correct.
