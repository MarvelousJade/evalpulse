# Evaluator failure runbook

## Exact match failures

Exact matching is intentionally strict: whitespace, punctuation, letter case, JSON serialization, and
extra prose all matter. Compare the stored output and expected value first. Use a case-insensitive or
schema evaluator only when that reflects the product contract; do not weaken an evaluator just to
make a regression disappear.

## Structured output failures

For `valid_json`, `json_schema`, or `required_json_keys` failures, ask the model for JSON only and
state the required keys and types in the prompt. Inspect the raw stored output for Markdown fences,
leading prose, truncated output, wrong types, and missing keys. If output is truncated, simplify the
schema or deliberately raise the server-controlled output cap after reviewing cost impact.

## Content and regex failures

For missing phrases, verify that the required phrases belong in the expected value or evaluator
options. For regex failures, test the expression independently and check escaping, anchors, and
case sensitivity. Invalid regular expressions are evaluator configuration problems rather than model
quality regressions.

## Latency failures

A `max_latency` failure with otherwise correct output is a performance regression. Compare p95 rather
than one case, separate provider throttling from prompt complexity, and avoid retrying successful but
slow responses because that adds cost without changing the evaluation.
