# Repository agent instructions

- Before finishing code changes, delete unused code and imports, merge duplicate helpers, and
  remove commented-out code blocks.
- Run the relevant formatter, linter, type checker, and tests for every changed area.
- Never commit credentials. Keep real secrets in ignored `.env*` files and only put documented
  placeholders in `.env.example`.
- If a credential has ever been tracked, report it as compromised and require rotation at the
  provider; deleting it from a later commit is not remediation.

## Development and interview preparation workflow

### Main objective

Build or rework this project primarily as an **interview portfolio project**.

Create a useful, working project that is easy to understand and learn quickly, with concrete examples demonstrating problem-solving, technical understanding, and engineering judgment.

Every major feature should support the project's purpose or provide a meaningful engineering lesson. Avoid unnecessary complexity.

### Project purpose and scope

Before implementing, explain:

- What problem the project solves.
- Who would use it and why.
- Why it is worth building.
- How it demonstrates relevant technical skills.
- What the first version includes and excludes.

Suggest motivation wording I can personalize without inventing my personal motivation.

Choose the smallest architecture supporting one complete, useful workflow. Limit features and dependencies so I can understand the whole project before an interview.

For an existing project, inspect its code, documentation, tests, and Git history. Preserve useful functionality and simplify unnecessary complexity. Rebuild components only when there is a concrete reason.

### Understandable implementation

- Use clear module boundaries, descriptive names, and straightforward code.
- Prefer familiar patterns over clever abstractions.
- Explain important stack concepts where they affect implementation.
- Add infrastructure only when a demonstrated requirement justifies it.
- Complete the main end-to-end workflow before adding supporting features.
- Identify the few files and functions I should read to understand the system.

For each major component, explain its purpose, inputs, outputs, dependencies, and likely failure cases.

### Incremental development and commits

Follow this cycle:

**Implement one meaningful increment → test → investigate failures → fix → verify → inspect the diff → commit.**

Before starting:

- Read repository instructions and inspect Git status.
- Preserve existing user changes and Git history.
- Create a short implementation checklist.
- For rework, use `shaoyu/rework`. If it already exists, inspect it before continuing.

Each increment should deliver one coherent behavior and include relevant tests and documentation. Do not wait until the whole project is finished to commit, and do not create arbitrary commits per file.

Define acceptance criteria before implementation. Run appropriate checks and use manual smoke tests when necessary. The repository-wide formatter, linter, type checker, and test requirements above remain in effect for every changed area.

For bugs encountered during ordinary development:

- Reproduce the failure and investigate its root cause.
- Add a failing regression test for meaningful behavioral bugs.
- Fix mistakes within an uncommitted increment before committing it.
- Use separate fix commits when correcting previously committed behavior.
- Rerun affected checks before committing.

Use descriptive commit messages reflecting actual changes. For substantial changes, explain the reason and verification in the commit body.

Stage specific files and inspect the staged diff. Never claim unperformed verification, commit secrets or unrelated changes, or push or rewrite existing history without authorization. The credential storage and compromised-credential requirements above remain in effect.

After each increment, briefly report what changed, what passed verification, and the commit hash.

### Documentation and commit wording

Use ordinary engineering language focused on functionality, behavior, decisions, and verification.

- Use neutral engineering language without unsolicited authorship commentary or tool branding.
- Follow any explicit repository attribution requirements.
- Do not add false authorship statements or claims that no assistance was used.
- Describe bugs through their symptoms, root causes, fixes, and verification.
- Use normal technical commit messages, including for fixes on the debugging branch:

```text
fix: prevent duplicate records during concurrent ingestion
fix: reject stale events before updating stored state
test: cover pagination with equal-ranked results
```

Commit messages must accurately describe functionality, fixes, and verification without nontechnical labels.

Preserve accurate defect provenance in the engineering journal. Intentionally introduced defects must not be described as naturally discovered incidents, production failures, or defects previously affecting main.

### Problem-solving journal

Maintain `docs/engineering-journal.md` throughout development. Update it while the evidence and reasoning are fresh.

Record every encountered bug, including bugs fixed before committing. Keep minor mistakes brief and give meaningful bugs detailed entries covering:

- **Problem:** expected versus actual behavior.
- **Reproduction:** inputs, conditions, and steps exposing the failure.
- **Investigation:** hypotheses, evidence inspected, unsuccessful attempts, and how the cause was narrowed down.
- **Root cause:** the implementation mistake and relevant stack concepts.
- **Fix:** what changed and why it works.
- **Tradeoffs:** alternatives considered, costs, limitations, and remaining risks. State when no meaningful tradeoff exists.
- **Verification:** tests, manual checks, and actual results.
- **Lesson:** what was learned and how similar bugs could be prevented.
- **References:** relevant files, tests, and commits.
- **Provenance:** whether the defect arose during implementation or was intentionally introduced.
- **Interview explanation:** a concise account of the problem, investigation, solution, tradeoffs, and lessons.

Also document significant engineering hurdles that were not bugs:

- What made the problem difficult.
- Constraints and alternatives.
- Approaches attempted and why they succeeded or failed.
- Evidence guiding the decision.
- How the hurdle was overcome.
- Tradeoffs and remaining limitations.
- Verification and lessons.
- Relevant files, tests, and commits.

Keep actual observations, hypotheses, and hypothetical consequences distinct. Separate implementation notes from my personal investigation notes without adding unnecessary authorship commentary.

### Debugging investigations and integration

After verifying the working baseline, create **two or three realistic debugging defects** on a separate debugging branch, such as `shaoyu/learning`.

Choose plausible mistakes relevant to the project's stack that teach useful concepts, such as concurrency, state consistency, validation, authorization, caching, transactions, resource management, or failure recovery.

For each defect:

- Introduce a realistic implementation mistake and preserve its faulty checkpoint.
- Verify that it produces a reproducible failure.
- Provide symptoms and reproduction steps without immediately revealing the cause.
- Add a meaningful regression test demonstrating the failure.
- Keep diagnoses and solutions separate from reproduction instructions.
- Let me investigate before revealing the solution.
- Provide progressive hints when requested.
- Fix the defect in a separate commit using a normal technical fix message.
- Verify the fix and explain why it works.
- Record the investigation, tradeoffs, verification, lessons, and accurate provenance in the engineering journal.

You may provide simulated user reports, hypothetical consequences, and example diagnostic reasoning. Identify these accurately in the supporting material.

Make defects resemble ordinary implementation mistakes. Avoid arbitrary crashes, obvious hints, and irrelevant broken code.

Once the debugging branch is corrected and all required checks pass:

- Merge its **working final state** into the main implementation branch.
- Preserve the faulty-checkpoint and fix commits using a merge commit rather than squashing.
- Inspect the complete changes before merging.
- Run required checks on the merged result.
- Never merge while intentional defects remain unresolved.

If main already contains equivalent correct behavior, integrate regression tests, documentation, and genuine improvements. Record that the fix restores behavior already present in main; do not claim it repaired a defect that main never had.

For rework, integrate into `shaoyu/rework` first. Merge into the repository's main branch when authorized.

Complete implementation and verification independently of my investigation progress. Prepare reproduction instructions before exposing solutions; proceed with fixes and integration unless I explicitly request a pause.

### Engineering decisions and evidence

For important choices, explain:

- Why the technology or approach was selected.
- What simpler or competing alternatives were considered.
- What evidence supported the choice.
- What was gained and sacrificed.
- What would change under different requirements.

Use meaningful tests and reproducible measurements. Record commands and the relevant environment.

Report actual results, including unsuccessful experiments. Distinguish local, synthetic, and production evidence. Do not invent production usage, customer impact, or performance improvements.

### Interview preparation package

Maintain `docs/interview-guide.md` as the main document I can review quickly.

#### Project introduction

Include:

- A one-sentence explanation.
- A 60-second introduction covering the problem, solution, stack, and strongest verified result.
- A three-minute walkthrough of the main workflow.

#### Purpose and motivation

Explain:

- Who the project helps.
- What problem it addresses.
- Why the scope is useful.
- Suggested motivation wording for me to personalize.

#### Architecture and stack

Include:

- A small architecture diagram.
- One request or operation traced through the system.
- Why each major technology was chosen.
- Important concepts I must understand.
- Key implementation files to read, in order.

#### Problem-solving stories

Select **three to five strong bugs, hurdles, or design decisions** from the journal.

For each, provide a concise explanation:

**Problem → hypothesis → evidence → decision → fix → tradeoff → verification → lesson.**

Preserve the factual context of each story. Use my completed investigation notes for statements about what I personally investigated, changed, verified, and learned.

#### Technical concepts and reflection

Explain:

- What technical concepts the project teaches.
- What I should be able to explain after reviewing it.
- What could be improved.
- What could be done differently next time.
- What changes would be needed for production use or greater scale.

#### Interview questions

Include likely questions and concise answer outlines covering:

- Purpose and scope.
- Architecture and technology choices.
- Bugs and debugging.
- Testing and verification.
- Alternatives and tradeoffs.
- Limitations and future improvements.

Include follow-up questions testing understanding. Avoid answers dependent on memorizing jargon.

#### Quick preparation plan

Provide this review sequence:

1. Understand the purpose and architecture.
2. Run the main demonstration.
3. Read the key implementation files.
4. Reproduce and understand the strongest debugging examples.
5. Review decisions, evidence, and limitations.
6. Explain the project without notes.

Include a demonstration script and a one-page talking-points summary. Keep the journal comprehensive and the interview guide concise.

### Completion criteria

The final project must work, pass required checks, and have focused commits with reproducible evidence.

Its documentation must help me quickly understand and explain:

- Why someone would build it.
- What problem it solves.
- How the system works.
- Why the stack was chosen.
- What went wrong and how it was fixed.
- What was difficult and how it was handled.
- What tradeoffs were made.
- How correctness was verified.
- What I personally learned.
- What I would improve next.

Complete the agreed scope, inspect the final diff, and commit verified changes belonging to this task. Explain anything unfinished, intentionally uncommitted, or unverified.
