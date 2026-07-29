# Live LLM, RAG, and diagnostic agent

## Why Gemini 3.5 Flash-Lite

EvalPulse uses `gemini-3.5-flash-lite` as its only allow-listed live model. As checked on 2026-07-22,
Google describes it as the fastest, lowest-cost model in the 3.5 family and lists a free tier; standard
paid text rates are $0.30 per million input tokens and $2.50 per million output tokens. Pricing and limits
can change, so verify the [official Gemini pricing page](https://ai.google.dev/gemini-api/docs/pricing)
before enabling billing. Google states that free-tier content may be used to improve its products,
while paid-tier content is not; choose the tier appropriate for the data being evaluated.

The integration calls the first-party REST `generateContent` endpoint directly. No SDK or proxy is
needed, and the origin is fixed in code to avoid server-side request forgery through a configurable
base URL.

## Request flow

```mermaid
sequenceDiagram
  participant U as Authenticated user
  participant A as EvalPulse API
  participant D as PostgreSQL
  participant G as Gemini
  participant R as Local retriever

  U->>A: POST /api/runs/{id}/diagnose + CSRF
  A->>D: Authorize run; return cached diagnosis if present
  A->>G: Require inspect_failed_evaluations tool call
  G-->>A: Function call
  A->>D: Read bounded failed cases for authorized run ID
  A->>R: Retrieve top runbook chunks from failure terms
  R-->>A: Source IDs, paths, excerpts, scores
  A->>G: Tool evidence + retrieved sources + JSON schema
  G-->>A: Structured diagnosis and requested source IDs
  A->>A: Drop any source ID that was not retrieved
  A->>D: Persist one diagnosis per run
  A-->>U: Findings, actions, citations, and token usage
```

Retrieval is intentionally small and inspectable: Markdown is split by heading, tokenized locally,
and ranked with a BM25-style score. There is no embedding API call, vector database, or retrieval fee.
The evidence query is derived by the server from error types, tags, and evaluator explanations rather
than from model-proposed text.

## Cost and abuse controls

- The mock provider remains the default; live inference requires both `LLM_ENABLED=true` and a key.
- The key exists only in API/worker environment variables and is sent in an HTTP header, never a URL,
  response, browser bundle, prompt, stored run configuration, or log message.
- The API origin, model, generation settings, and token caps are fixed server-side. Live requests must
  send an empty `provider_config`.
- Each live call has bounded input characters, output tokens, and a timeout. Live runs have a smaller
  case cap and a database-derived daily request allowance.
- Diagnosis is authenticated, CSRF-protected, read-only, daily-limited, and persisted once per run.
- The agent has exactly one tool. Its model-supplied run ID is ignored and the authorized route ID is
  used, preventing cross-project reads.
- Retrieved evidence is labeled untrusted, output is constrained by a JSON schema, and citations are
  filtered against the actual retrieval result.

Application caps reduce accidental or abusive usage but do not provide a transactional billing
guarantee under all concurrent deployments. Create a dedicated key, follow Google's
[API-key restriction guidance](https://ai.google.dev/gemini-api/docs/api-key), apply egress/IP
restrictions where available, and set account-level quotas, prepaid credit, budgets, and alerts.

## Configuration

| Variable | Default | Purpose |
| --- | ---: | --- |
| `LLM_ENABLED` | `false` | Explicit paid-path opt-in |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Server allow-listed model |
| `LLM_MAX_CASES_PER_RUN` | `20` | Maximum live calls reserved by one run |
| `LLM_DAILY_REQUEST_LIMIT` | `100` | Database-derived daily live-run allowance |
| `LLM_DAILY_DIAGNOSIS_LIMIT` | `20` | Maximum persisted diagnoses per day |
| `LLM_MAX_OUTPUT_TOKENS` | `256` | Per-evaluation output cap |
| `LLM_DIAGNOSIS_MAX_OUTPUT_TOKENS` | `600` | Final diagnosis output cap |
| `LLM_MAX_INPUT_CHARS` | `12000` | Prompt plus case-input character cap |
| `LLM_REQUEST_TIMEOUT_SECONDS` | `20` | External request deadline |

Do not commit `GEMINI_API_KEY`. The supplied `.gitignore` excludes `.env`.
