"use client";

import {
  ApiError,
  Comparison,
  DatasetVersion,
  Project,
  PromptVersion,
  Run,
  User,
  api,
} from "@evalpulse/api-client";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

const demoDataset = JSON.stringify(
  [
    {
      input: { mock_response: "APPROVED" },
      expected: "APPROVED",
      tags: ["critical"],
    },
    { input: { mock_response: "READY" }, expected: "READY", tags: ["smoke"] },
    { input: { mock_response: "VERIFIED" }, expected: "VERIFIED", tags: [] },
  ],
  null,
  2,
);

function errorMessage(error: unknown): string {
  return error instanceof ApiError || error instanceof Error ? error.message : "Something went wrong";
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function RunCard({ label, run }: { label: string; run: Run | null }) {
  const total = run?.aggregate.total ?? 0;
  const completed = run?.aggregate.completed ?? 0;
  const progress = run?.status === "completed" ? 100 : total ? (completed / total) * 100 : 8;
  return (
    <article className="run-card">
      <div className="row split">
        <div>
          <p className="eyebrow">{label}</p>
          <h3>{run ? `Run ${run.id.slice(0, 8)}` : "Not started"}</h3>
        </div>
        <span className={`status ${run?.status ?? "idle"}`}>{run?.status ?? "idle"}</span>
      </div>
      <div className="progress" aria-label={`${label} progress`}>
        <span style={{ width: `${Math.max(0, Math.min(progress, 100))}%` }} />
      </div>
      <div className="run-metrics">
        <Metric label="Pass rate" value={run?.aggregate.pass_rate == null ? "—" : `${Math.round(run.aggregate.pass_rate * 100)}%`} />
        <Metric label="P95 latency" value={run?.aggregate.p95_latency_ms == null ? "—" : `${run.aggregate.p95_latency_ms.toFixed(1)} ms`} />
      </div>
    </article>
  );
}

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [loadingSession, setLoadingSession] = useState(true);
  const [email, setEmail] = useState("demo@evalpulse.local");
  const [password, setPassword] = useState("evalpulse-demo");
  const [projectName, setProjectName] = useState("Release confidence");
  const [baselineText, setBaselineText] = useState("Return the supplied response exactly.");
  const [candidateText, setCandidateText] = useState("[lowercase] Return the supplied response exactly.");
  const [datasetContent, setDatasetContent] = useState(demoDataset);
  const [project, setProject] = useState<Project | null>(null);
  const [baselineVersion, setBaselineVersion] = useState<PromptVersion | null>(null);
  const [candidateVersion, setCandidateVersion] = useState<PromptVersion | null>(null);
  const [datasetVersion, setDatasetVersion] = useState<DatasetVersion | null>(null);
  const [baselineRun, setBaselineRun] = useState<Run | null>(null);
  const [candidateRun, setCandidateRun] = useState<Run | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const baselineRunId = baselineRun?.id;
  const candidateRunId = candidateRun?.id;
  const baselineStatus = baselineRun?.status;
  const candidateStatus = candidateRun?.status;
  const activeRunIds = useMemo(
    () =>
      [
        [baselineRunId, baselineStatus],
        [candidateRunId, candidateStatus],
      ]
        .filter(
          (entry): entry is [string, Run["status"]] =>
            Boolean(entry[0] && entry[1] && ["queued", "running"].includes(entry[1])),
        )
        .map(([runId]) => runId),
    [baselineRunId, baselineStatus, candidateRunId, candidateStatus],
  );

  useEffect(() => {
    api.me().then(setUser).catch(() => undefined).finally(() => setLoadingSession(false));
  }, []);

  const refreshRuns = useCallback(async () => {
    const [baseline, candidate] = await Promise.all([
      baselineRunId ? api.run(baselineRunId) : Promise.resolve(null),
      candidateRunId ? api.run(candidateRunId) : Promise.resolve(null),
    ]);
    if (baseline) setBaselineRun(baseline);
    if (candidate) setCandidateRun(candidate);
  }, [baselineRunId, candidateRunId]);

  useEffect(() => {
    if (!baselineRun || !candidateRun) return;
    if (
      [baselineRun.status, candidateRun.status].every((state) =>
        ["completed", "failed", "cancelled"].includes(state),
      )
    )
      return;
    const interval = window.setInterval(
      () => refreshRuns().catch((reason) => setError(errorMessage(reason))),
      900,
    );
    return () => window.clearInterval(interval);
  }, [baselineRun, candidateRun, refreshRuns]);

  useEffect(() => {
    const streams = activeRunIds.map((runId) => {
      const stream = new EventSource(`/api/runs/${runId}/events`, { withCredentials: true });
      stream.onmessage = () => refreshRuns().catch((reason) => setError(errorMessage(reason)));
      stream.addEventListener("run.progress", stream.onmessage);
      stream.addEventListener("run.completed", stream.onmessage);
      return stream;
    });
    return () => streams.forEach((stream) => stream.close());
  }, [activeRunIds, refreshRuns]);

  const completed = baselineRun?.status === "completed" && candidateRun?.status === "completed";
  const currentStep = useMemo(() => {
    if (!project) return 1;
    if (!candidateVersion) return 2;
    if (!datasetVersion) return 3;
    if (!baselineRun || !candidateRun) return 4;
    return 5;
  }, [project, candidateVersion, datasetVersion, baselineRun, candidateRun]);

  async function act(name: string, operation: () => Promise<void>) {
    setBusy(name);
    setError(null);
    try {
      await operation();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(null);
    }
  }

  function signIn(event: FormEvent) {
    event.preventDefault();
    void act("login", async () => setUser(await api.login(email, password)));
  }

  function createProject(event: FormEvent) {
    event.preventDefault();
    void act("project", async () => {
      setProject(await api.createProject(projectName, "A deterministic release-gate workspace"));
    });
  }

  function createPrompts(event: FormEvent) {
    event.preventDefault();
    if (!project) return;
    void act("prompts", async () => {
      const prompt = await api.createPrompt(project.id, "Support response", baselineText);
      setBaselineVersion(prompt.versions[0]);
      setCandidateVersion(await api.createPromptVersion(prompt.id, candidateText));
    });
  }

  function importDataset(event: FormEvent) {
    event.preventDefault();
    if (!project) return;
    void act("dataset", async () => {
      JSON.parse(datasetContent);
      const dataset = await api.createDataset(project.id, "Release checks");
      setDatasetVersion(await api.importDataset(dataset.id, datasetContent));
    });
  }

  function startRuns() {
    if (!project || !baselineVersion || !candidateVersion || !datasetVersion) return;
    void act("runs", async () => {
      const evaluators = [{ type: "exact_match" as const, options: {} }];
      const nonce = crypto.randomUUID();
      const [baseline, candidate] = await Promise.all([
        api.createRun(project.id, baselineVersion.id, datasetVersion.id, `baseline-${nonce}`, evaluators),
        api.createRun(project.id, candidateVersion.id, datasetVersion.id, `candidate-${nonce}`, evaluators),
      ]);
      setBaselineRun(baseline);
      setCandidateRun(candidate);
    });
  }

  function compareRuns() {
    if (!project || !baselineRun || !candidateRun) return;
    void act("comparison", async () => {
      await refreshRuns();
      setComparison(await api.compare(project.id, baselineRun.id, candidateRun.id));
    });
  }

  if (loadingSession) {
    return <main className="center-state"><div className="spinner" /><p>Restoring your workspace…</p></main>;
  }

  if (!user) {
    return (
      <main className="login-shell">
        <section className="login-story">
          <div className="brand"><span className="brand-mark">EP</span> EvalPulse</div>
          <div>
            <p className="eyebrow">Regression testing for prompts</p>
            <h1>Ship prompt changes with evidence, not instinct.</h1>
            <p className="lede">Run reproducible evaluations, catch quality regressions, and explain every release decision.</p>
          </div>
          <div className="proof-row"><span>Deterministic</span><span>Auditable</span><span>Provider-free</span></div>
        </section>
        <section className="login-panel">
          <form className="auth-card" onSubmit={signIn}>
            <p className="eyebrow">Welcome back</p>
            <h2>Sign in to your workspace</h2>
            <p className="muted">Demo credentials are pre-filled. The free API can take up to a minute to wake.</p>
            <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" /></label>
            <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" /></label>
            {error && <div className="error" role="alert">{error}</div>}
            <button className="primary wide" disabled={busy === "login"}>{busy === "login" ? "Connecting…" : "Sign in"}</button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">EP</span> EvalPulse</div>
        <nav aria-label="Primary"><a className="active" href="#workspace">Evaluation lab</a><a href="#runs">Run monitor</a><a href="#comparison">Regression report</a></nav>
        <div className="sidebar-foot"><span className="avatar">{user.display_name.slice(0, 2).toUpperCase()}</span><div><strong>{user.display_name}</strong><small>{user.email}</small></div></div>
      </aside>
      <section className="workspace" id="workspace">
        <header className="topbar"><div><p className="eyebrow">Evaluation lab</p><h1>Release confidence</h1></div><div className="live-pill"><span /> Mock provider ready</div></header>
        {error && <div className="error banner" role="alert"><strong>Couldn’t complete that step.</strong> {error}<button onClick={() => setError(null)} aria-label="Dismiss error">×</button></div>}
        <div className="stepper" aria-label="Workflow progress">
          {["Project", "Prompts", "Dataset", "Evaluate", "Compare"].map((label, index) => <div key={label} className={currentStep >= index + 1 ? "step current" : "step"}><span>{index + 1}</span>{label}</div>)}
        </div>

        <section className="grid two">
          <form className={`panel ${project ? "complete" : ""}`} onSubmit={createProject}>
            <div className="panel-heading"><div><p className="eyebrow">Step 1</p><h2>Create a project</h2></div>{project && <span className="check">✓</span>}</div>
            <p className="muted">Projects isolate prompts, datasets, runs, and authorization.</p>
            <label>Project name<input value={projectName} onChange={(event) => setProjectName(event.target.value)} disabled={Boolean(project)} /></label>
            <button className="secondary" disabled={Boolean(project) || busy === "project"}>{project ? "Project created" : busy === "project" ? "Creating…" : "Create project"}</button>
          </form>

          <form className={`panel ${candidateVersion ? "complete" : ""}`} onSubmit={createPrompts}>
            <div className="panel-heading"><div><p className="eyebrow">Step 2</p><h2>Version the prompt</h2></div>{candidateVersion && <span className="check">✓</span>}</div>
            <div className="prompt-pair"><label><span>Baseline <b>v1</b></span><textarea value={baselineText} onChange={(event) => setBaselineText(event.target.value)} disabled={Boolean(candidateVersion)} /></label><label><span>Candidate <b>v2</b></span><textarea value={candidateText} onChange={(event) => setCandidateText(event.target.value)} disabled={Boolean(candidateVersion)} /></label></div>
            <button className="secondary" disabled={!project || Boolean(candidateVersion) || busy === "prompts"}>{candidateVersion ? "Versions locked" : busy === "prompts" ? "Saving…" : "Save immutable versions"}</button>
          </form>
        </section>

        <section className={`panel dataset-panel ${datasetVersion ? "complete" : ""}`}>
          <form onSubmit={importDataset}>
            <div className="panel-heading"><div><p className="eyebrow">Step 3</p><h2>Import the evaluation dataset</h2><p className="muted">Each case includes model input, an expected value, and optional tags.</p></div><div className="dataset-meta">{datasetVersion ? <><strong>{datasetVersion.row_count}</strong><span>validated cases</span></> : <><strong>JSON</strong><span>max 2,000 cases</span></>}</div></div>
            <label className="code-label">Dataset content<textarea className="code" value={datasetContent} onChange={(event) => setDatasetContent(event.target.value)} disabled={Boolean(datasetVersion)} spellCheck={false} /></label>
            <div className="row split"><span className="hint">Critical tags enforce the strictest release threshold.</span><button className="secondary" disabled={!candidateVersion || Boolean(datasetVersion) || busy === "dataset"}>{datasetVersion ? "Dataset validated" : busy === "dataset" ? "Validating…" : "Validate & import"}</button></div>
          </form>
        </section>

        <section className="section-block" id="runs">
          <div className="section-heading"><div><p className="eyebrow">Step 4</p><h2>Evaluate both versions</h2><p className="muted">Workers persist every case result before publishing live progress.</p></div><button className="primary" onClick={startRuns} disabled={!datasetVersion || Boolean(baselineRun) || busy === "runs"}>{busy === "runs" ? "Queueing…" : baselineRun ? "Runs queued" : "Run evaluations"}</button></div>
          <div className="grid two"><RunCard label="Baseline · v1" run={baselineRun} /><RunCard label="Candidate · v2" run={candidateRun} /></div>
        </section>

        <section className="section-block" id="comparison">
          <div className="section-heading"><div><p className="eyebrow">Step 5</p><h2>Regression decision</h2><p className="muted">Every policy is evaluated independently against the candidate.</p></div><button className="primary" onClick={compareRuns} disabled={!completed || Boolean(comparison) || busy === "comparison"}>{busy === "comparison" ? "Comparing…" : comparison ? "Report generated" : "Compare runs"}</button></div>
          {!comparison ? <div className="empty-report"><span className="report-icon">↗</span><h3>{completed ? "Runs are ready to compare" : "Waiting for completed runs"}</h3><p>The report will show exact measurements and thresholds for every release gate.</p></div> : <div className={`decision ${comparison.passed ? "pass" : "fail"}`}><div className="decision-head"><div><p className="eyebrow">Release decision</p><h3>{comparison.passed ? "Candidate passed" : "Regression detected"}</h3></div><span>{comparison.passed ? "PASS" : "FAIL"}</span></div><div className="checks">{comparison.checks.map((check) => <div className="check-row" key={check.name}><span className={check.passed ? "check-dot pass" : "check-dot fail"}>{check.passed ? "✓" : "!"}</span><div><strong>{check.name.replaceAll("_", " ")}</strong><p>{check.explanation}</p></div><b>{check.passed ? "Passed" : "Failed"}</b></div>)}</div></div>}
        </section>
      </section>
    </main>
  );
}
