# Case 01 solution — read after investigating

Learner instructions: [case 01](../01-critical-policy.md). Faulty checkpoint: `learning/01-faulty` / `79e46e9`. Correct scenario controls: `001c483`. Corrected checkpoint: `learning/01-fixed`.

## Progressive hints

1. Trace a case outcome through persistence, aggregate calculation, and policy evaluation; identify where the values first become unexpected.
2. Compare which cases participate in overall and critical scoring. Check both passing and failing populations.
3. Inspect `calculate_aggregate` and verify that a ratio's numerator and denominator describe the same population.

## Diagnosis and correction

The intentionally faulty refactor counted passing critical results in the numerator but all results in the denominator. One passing critical case among three total results therefore became `1/3` rather than `1/1`. The zero-passing-critical control still returned zero, so that case alone would not catch the mistake. Formatting and typing cannot establish metric semantics.

Restore the divisor to `len(critical_results)`, retaining the existing `1.0` convention when there are no critical results. Overall pass rate still uses the entire dataset. The change restores correct behavior already present in `shaoyu/rework`; it does not repair a defect that ever affected its working implementation.

The regression includes both mixed-tag scenarios and checks aggregate values plus the critical policy result. Its policy-control baseline is explicitly synthetic, holding latency/error evidence equal and permitting ordinary failures to focus on this gate.

## Verification and tradeoffs

The faulty checkpoint produced one failing positive scenario and one passing negative control. After correction, both focused cases passed (7.51 seconds), and all 40 SQLite tests passed at 82% coverage across 1,401 statements (146.39 seconds). Ruff lint/formatting (38 files) and strict mypy (18 application/test/helper files) passed. The sole warning was the known Starlette/httpx deprecation. The corrected merged state will receive a fresh PostgreSQL and full-stack refresh before completion.

No schema, dependency, or policy change is required. Preserve the established no-critical-case convention rather than changing product semantics during a bug fix. These tests do not establish production gate thresholds, external model quality, or performance.

## Lesson and interview explanation

A metric can be correctly typed but semantically wrong when populations differ. Identify the first bad persisted value, check population definitions, reproduce with mixed groups and opposite outcomes, restore the calculation, and retain regressions. Describe this as an intentionally introduced local investigation, not a naturally discovered production incident or personal work you have not performed.
