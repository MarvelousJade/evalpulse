export type User = {
  id: string;
  email: string;
  display_name: string;
};

export type Project = {
  id: string;
  name: string;
  description: string;
  owner_id: string;
  created_at: string;
};

export type PromptVersion = {
  id: string;
  prompt_id: string;
  version: number;
  text: string;
  variables: string[];
  created_at: string;
};

export type Prompt = {
  id: string;
  project_id: string;
  name: string;
  versions: PromptVersion[];
};

export type Dataset = { id: string; project_id: string; name: string };

export type DatasetVersion = {
  id: string;
  dataset_id: string;
  version: number;
  source_format: string;
  row_count: number;
  content_sha256: string;
  created_at: string;
};

export type EvaluatorSpec = {
  type:
    | "exact_match"
    | "case_insensitive_exact_match"
    | "contains_all"
    | "regex"
    | "valid_json"
    | "json_schema"
    | "required_json_keys"
    | "max_latency";
  options?: Record<string, unknown>;
};

export type Run = {
  id: string;
  project_id: string;
  prompt_version_id: string;
  dataset_version_id: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  provider: string;
  evaluators: EvaluatorSpec[];
  aggregate: {
    total?: number;
    completed?: number;
    passed?: number;
    failed?: number;
    pass_rate?: number;
    critical_pass_rate?: number;
    p95_latency_ms?: number;
    provider_error_rate?: number;
  };
  cancel_requested: boolean;
  failure_reason: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type ComparisonCheck = {
  name: string;
  passed: boolean;
  actual: number;
  threshold: number;
  explanation: string;
};

export type Comparison = {
  id: string;
  project_id: string;
  baseline_run_id: string;
  candidate_run_id: string;
  policy_snapshot: Record<string, number>;
  passed: boolean;
  checks: ComparisonCheck[];
  created_at: string;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string,
  ) {
    super(message);
  }
}

function csrfToken(): string | undefined {
  if (typeof document === "undefined") return undefined;
  return document.cookie
    .split("; ")
    .find((value) => value.startsWith("evalpulse_csrf="))
    ?.split("=")[1];
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = init.method?.toUpperCase() ?? "GET";
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = csrfToken();
    if (csrf) headers.set("X-CSRF-Token", decodeURIComponent(csrf));
  }
  const response = await fetch(path, { ...init, headers, credentials: "include" });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as {
      detail?: string;
      code?: string;
    };
    throw new ApiError(payload.detail ?? "Request failed", response.status, payload.code);
  }
  return response.json() as Promise<T>;
}

export const api = {
  me: () => request<User>("/api/auth/me"),
  login: (email: string, password: string) =>
    request<User>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => request<{ message: string }>("/api/auth/logout", { method: "POST" }),
  projects: () => request<Project[]>("/api/projects"),
  createProject: (name: string, description: string) =>
    request<Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    }),
  createPrompt: (projectId: string, name: string, text: string) =>
    request<Prompt>(`/api/projects/${projectId}/prompts`, {
      method: "POST",
      body: JSON.stringify({ name, text, variables: [] }),
    }),
  createPromptVersion: (promptId: string, text: string) =>
    request<PromptVersion>(`/api/prompts/${promptId}/versions`, {
      method: "POST",
      body: JSON.stringify({ text, variables: [] }),
    }),
  createDataset: (projectId: string, name: string) =>
    request<Dataset>(`/api/projects/${projectId}/datasets`, {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  importDataset: (datasetId: string, content: string, format: "json" | "csv" = "json") =>
    request<DatasetVersion>(`/api/datasets/${datasetId}/versions`, {
      method: "POST",
      body: JSON.stringify({ format, content }),
    }),
  createRun: (
    projectId: string,
    promptVersionId: string,
    datasetVersionId: string,
    idempotencyKey: string,
    evaluators: EvaluatorSpec[],
  ) =>
    request<Run>(`/api/projects/${projectId}/runs`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({
        prompt_version_id: promptVersionId,
        dataset_version_id: datasetVersionId,
        provider: "mock",
        provider_config: {},
        evaluators,
      }),
    }),
  run: (runId: string) => request<Run>(`/api/runs/${runId}`),
  cancelRun: (runId: string) => request<Run>(`/api/runs/${runId}/cancel`, { method: "POST" }),
  compare: (projectId: string, baselineRunId: string, candidateRunId: string) =>
    request<Comparison>(`/api/projects/${projectId}/comparisons`, {
      method: "POST",
      body: JSON.stringify({ baseline_run_id: baselineRunId, candidate_run_id: candidateRunId }),
    }),
};

