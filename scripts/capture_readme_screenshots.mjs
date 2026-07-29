import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const baseURL = process.env.SCREENSHOT_BASE_URL ?? "http://localhost:3000";
const outputDir = new URL("../docs/images/", import.meta.url);
await mkdir(outputDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
let signedIn = false;
let runNumber = 0;
const runs = new Map();
const now = new Date().toISOString();

const user = { id: "user-demo", email: "demo@evalpulse.local", display_name: "Demo Reviewer" };
const project = {
  id: "project-demo",
  name: "Release confidence",
  description: "A deterministic release-gate workspace",
  owner_id: user.id,
  created_at: now,
};
const baselineVersion = {
  id: "prompt-v1",
  prompt_id: "prompt-demo",
  version: 1,
  text: "Return the supplied response exactly.",
  variables: [],
  created_at: now,
};
const candidateVersion = {
  ...baselineVersion,
  id: "prompt-v2",
  version: 2,
  text: "[lowercase] Return the supplied response exactly.",
};

function json(route, payload, status = 200) {
  return route.fulfill({ status, contentType: "application/json", body: JSON.stringify(payload) });
}

await page.route("**/api/**", async (route) => {
  const request = route.request();
  const { pathname } = new URL(request.url());
  const method = request.method();

  if (pathname === "/api/auth/me") return json(route, signedIn ? user : {}, signedIn ? 200 : 401);
  if (pathname === "/api/auth/login" && method === "POST") {
    signedIn = true;
    return json(route, user);
  }
  if (pathname === "/api/ai/status") {
    return json(route, {
      enabled: true,
      provider: "gemini",
      model: "gemini-3.5-flash-lite",
      max_cases_per_run: 20,
      max_output_tokens: 256,
      daily_request_limit: 100,
    });
  }
  if (pathname === "/api/projects" && method === "POST") return json(route, project, 201);
  if (pathname === `/api/projects/${project.id}/prompts`) {
    return json(route, {
      id: "prompt-demo",
      project_id: project.id,
      name: "Support response",
      versions: [baselineVersion],
    }, 201);
  }
  if (pathname === "/api/prompts/prompt-demo/versions") return json(route, candidateVersion, 201);
  if (pathname === `/api/projects/${project.id}/datasets`) {
    return json(route, { id: "dataset-demo", project_id: project.id, name: "Release checks" }, 201);
  }
  if (pathname === "/api/datasets/dataset-demo/versions") {
    return json(route, {
      id: "dataset-v1",
      dataset_id: "dataset-demo",
      version: 1,
      source_format: "json",
      row_count: 3,
      content_sha256: "demo",
      created_at: now,
    }, 201);
  }
  if (pathname === `/api/projects/${project.id}/runs`) {
    runNumber += 1;
    const baseline = runNumber === 1;
    const run = {
      id: baseline ? "run-baseline" : "run-candidate",
      project_id: project.id,
      prompt_version_id: baseline ? baselineVersion.id : candidateVersion.id,
      dataset_version_id: "dataset-v1",
      status: "completed",
      provider: "mock",
      evaluators: [{ type: "exact_match", options: {} }],
      aggregate: {
        total: 3,
        completed: 3,
        passed: baseline ? 3 : 0,
        failed: baseline ? 0 : 3,
        pass_rate: baseline ? 1 : 0,
        critical_pass_rate: baseline ? 1 : 0,
        p95_latency_ms: baseline ? 1.4 : 1.7,
        provider_error_rate: 0,
      },
      cancel_requested: false,
      failure_reason: null,
      created_at: now,
      started_at: now,
      finished_at: now,
    };
    runs.set(run.id, run);
    return json(route, run, 202);
  }
  if (method === "GET" && runs.has(pathname.split("/").at(-1))) {
    return json(route, runs.get(pathname.split("/").at(-1)));
  }
  if (pathname === `/api/projects/${project.id}/comparisons`) {
    return json(route, {
      id: "comparison-demo",
      project_id: project.id,
      baseline_run_id: "run-baseline",
      candidate_run_id: "run-candidate",
      policy_snapshot: {},
      passed: false,
      checks: [
        {
          name: "pass_rate",
          passed: false,
          actual: -1,
          threshold: -0.02,
          explanation: "Pass rate dropped from 100% to 0%; allowed drop is 2%.",
        },
        {
          name: "critical_pass_rate",
          passed: false,
          actual: 0,
          threshold: 1,
          explanation: "Critical pass rate is 0%; required rate is 100%.",
        },
        {
          name: "provider_error_rate",
          passed: true,
          actual: 0,
          threshold: 0.01,
          explanation: "Provider error rate is 0%; maximum is 1%.",
        },
      ],
      created_at: now,
    }, 201);
  }
  if (pathname === "/api/runs/run-candidate/diagnose") {
    return json(route, {
      id: "diagnosis-demo",
      run_id: "run-candidate",
      provider: "gemini",
      model: "gemini-3.5-flash-lite",
      summary: "The candidate introduced a systematic letter-case regression across all cases.",
      findings: [
        "All candidate outputs were lowercased while the exact-match contract requires uppercase values.",
        "The critical case failed, so the release policy correctly blocks this candidate.",
      ],
      actions: [
        "Remove the lowercase instruction and create a new immutable prompt version.",
        "Rerun the same dataset and exact-match evaluator before comparing again.",
      ],
      citations: [
        {
          id: "evaluator-failures#exact-match-failures",
          path: "docs/knowledge/evaluator-failures.md#exact-match-failures",
          heading: "Exact match failures",
          excerpt: "Exact matching is intentionally strict: whitespace, punctuation, letter case, JSON serialization, and extra prose all matter.",
          score: 4.81,
        },
        {
          id: "regression-triage#critical-cases",
          path: "docs/knowledge/regression-triage.md#critical-cases",
          heading: "Critical cases",
          excerpt: "Treat a failed case tagged critical as a release blocker unless the case or policy is demonstrably wrong.",
          score: 3.26,
        },
      ],
      evidence: {},
      usage: { calls: 2, input_tokens: 812, output_tokens: 126 },
      created_at: now,
    });
  }
  return json(route, { detail: `Unhandled screenshot route: ${method} ${pathname}` }, 404);
});

await page.goto(baseURL, { waitUntil: "networkidle" });
await page.addStyleTag({ content: "nextjs-portal { display: none !important; }" });
await page.getByRole("heading", { name: "Sign in to your workspace" }).waitFor();
await page.screenshot({
  path: fileURLToPath(new URL("evalpulse-login.png", outputDir)),
  fullPage: true,
});

await page.getByRole("button", { name: "Sign in" }).click();
await page.getByRole("heading", { name: "Release confidence" }).waitFor();
await page.getByText("gemini-3.5-flash-lite ready").waitFor();
await page.getByRole("button", { name: "Create project" }).click();
await page.getByRole("button", { name: "Save immutable versions" }).click();
await page.getByRole("button", { name: "Validate & import" }).click();
await page.getByRole("button", { name: "Run evaluations" }).click();
await page.getByRole("button", { name: "Compare runs" }).click();
await page.getByRole("heading", { name: "Regression detected" }).waitFor();
await page.getByRole("button", { name: "Run diagnosis" }).click();
await page.getByRole("heading", { name: /systematic letter-case regression/i }).waitFor();
await page.locator(".workspace").screenshot({
  path: fileURLToPath(new URL("evalpulse-rag-diagnosis.png", outputDir)),
});

await browser.close();
