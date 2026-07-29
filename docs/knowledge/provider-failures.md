# Provider failure runbook

## Authentication and configuration

A permanent provider error mentioning configuration, permission, or HTTP 401/403 usually means
the server-side credential is missing, invalid, leaked, or not allowed to call the selected model.
Confirm that `LLM_ENABLED=true`, rotate a suspected credential, and keep the key restricted to the
Gemini API and the deployment's egress IPs. Never place the key in browser code, a dataset, a prompt,
or a committed `.env` file.

## Rate limits and temporary errors

HTTP 408, 409, 429, and 5xx responses are temporary provider failures. EvalPulse retries temporary
failures with bounded exponential backoff. If failures persist, inspect the provider RPM, TPM, daily,
and billing quotas before increasing application retries. More retries can amplify an outage and do
not raise the configured EvalPulse daily request allowance.

## Timeouts and latency

Compare the run's p95 latency with the configured request timeout. A timeout affecting many cases
points to provider availability or an overly large prompt; a single slow case points to that case's
input size or complexity. Keep prompts and retrieved context small before increasing the timeout.
