# Repository agent instructions

- Before finishing code changes, delete unused code and imports, merge duplicate helpers, and
  remove commented-out code blocks.
- Run the relevant formatter, linter, type checker, and tests for every changed area.
- Never commit credentials. Keep real secrets in ignored `.env*` files and only put documented
  placeholders in `.env.example`.
- If a credential has ever been tracked, report it as compromised and require rotation at the
  provider; deleting it from a later commit is not remediation.
