from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from redis import Redis
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .auth import (
    clear_session,
    ensure_demo_user,
    get_current_user,
    require_csrf,
    set_session,
    verify_password,
)
from .comparisons import compare_aggregates
from .config import get_settings
from .database import SessionLocal, get_db
from .datasets import DatasetValidationError, parse_dataset
from .diagnostics import NoFailedEvaluationsError, diagnose_failed_run
from .models import (
    Comparison,
    Dataset,
    DatasetVersion,
    EvaluationResult,
    EvaluationRun,
    Project,
    ProjectMember,
    Prompt,
    PromptVersion,
    RunDiagnosis,
    RunDispatch,
    RunEvent,
    TestCase,
    User,
)
from .providers import PermanentProviderError, TemporaryProviderError
from .schemas import (
    AiStatusResponse,
    ComparisonCreate,
    ComparisonResponse,
    DatasetCreate,
    DatasetResponse,
    DatasetVersionCreate,
    DatasetVersionResponse,
    DiagnosisResponse,
    LoginRequest,
    Message,
    ProjectCreate,
    ProjectResponse,
    PromptCreate,
    PromptResponse,
    PromptVersionCreate,
    PromptVersionResponse,
    ResultResponse,
    RunCreate,
    RunResponse,
    TestCaseResponse,
    UserResponse,
)
from .tasks import dispatch_pending

settings = get_settings()
REQUESTS = Counter("evalpulse_http_requests_total", "HTTP requests", ["method", "path", "status"])
DURATION = Histogram("evalpulse_http_request_duration_seconds", "HTTP request duration", ["path"])


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        with SessionLocal() as db:
            ensure_demo_user(db)
    except Exception:
        pass
    yield


app = FastAPI(title="EvalPulse API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Idempotency-Key", "X-CSRF-Token"],
)


@app.middleware("http")
async def measure_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    with DURATION.labels(path=request.url.path).time():
        response = await call_next(request)
    REQUESTS.labels(method=request.method, path=request.url.path, status=response.status_code).inc()
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.exception_handler(DatasetValidationError)
async def dataset_error(_: Request, exc: DatasetValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc), "code": "invalid_dataset"})


def authorize_project(db: Session, project_id: str, user: User) -> Project:
    project = db.scalar(
        select(Project)
        .join(ProjectMember)
        .where(Project.id == project_id, ProjectMember.user_id == user.id)
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _gemini_requests_reserved_today(db: Session) -> int:
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    value = db.scalar(
        select(func.sum(DatasetVersion.row_count))
        .select_from(EvaluationRun)
        .join(DatasetVersion, DatasetVersion.id == EvaluationRun.dataset_version_id)
        .where(EvaluationRun.provider == "gemini", EvaluationRun.created_at >= today)
    )
    return int(value or 0)


@app.post("/api/auth/login", response_model=UserResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)) -> User:
    user = db.scalar(select(User).where(User.email == body.email.casefold()))
    if user is None or not verify_password(user.password_hash, body.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    set_session(response, user)
    return user


@app.post("/api/auth/logout", response_model=Message, dependencies=[Depends(require_csrf)])
def logout(response: Response) -> Message:
    clear_session(response)
    return Message(message="Signed out")


@app.get("/api/auth/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@app.get("/api/ai/status", response_model=AiStatusResponse)
def ai_status(_: User = Depends(get_current_user)) -> AiStatusResponse:
    return AiStatusResponse(
        enabled=settings.llm_configured,
        provider="gemini",
        model=settings.gemini_model,
        max_cases_per_run=settings.llm_max_cases_per_run,
        max_output_tokens=settings.llm_max_output_tokens,
        daily_request_limit=settings.llm_daily_request_limit,
    )


@app.get("/api/projects", response_model=list[ProjectResponse])
def list_projects(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Project]:
    return list(
        db.scalars(
            select(Project)
            .join(ProjectMember)
            .where(ProjectMember.user_id == user.id)
            .order_by(Project.created_at.desc())
        )
    )


@app.post(
    "/api/projects",
    response_model=ProjectResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
def create_project(
    body: ProjectCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Project:
    project = Project(name=body.name, description=body.description, owner_id=user.id)
    project.members.append(ProjectMember(user_id=user.id, role="owner"))
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Project:
    return authorize_project(db, project_id, user)


@app.post(
    "/api/projects/{project_id}/prompts",
    response_model=PromptResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
def create_prompt(
    project_id: str,
    body: PromptCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Prompt:
    authorize_project(db, project_id, user)
    prompt = Prompt(project_id=project_id, name=body.name)
    prompt.versions.append(
        PromptVersion(version=1, text=body.text, variables=body.variables, created_by_id=user.id)
    )
    db.add(prompt)
    db.commit()
    return db.scalar(
        select(Prompt).options(selectinload(Prompt.versions)).where(Prompt.id == prompt.id)
    )  # type: ignore[return-value]


@app.post(
    "/api/prompts/{prompt_id}/versions",
    response_model=PromptVersionResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
def create_prompt_version(
    prompt_id: str,
    body: PromptVersionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PromptVersion:
    prompt = db.get(Prompt, prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    authorize_project(db, prompt.project_id, user)
    latest = (
        db.scalar(
            select(func.max(PromptVersion.version)).where(PromptVersion.prompt_id == prompt_id)
        )
        or 0
    )
    version = PromptVersion(
        prompt_id=prompt_id,
        version=latest + 1,
        text=body.text,
        variables=body.variables,
        created_by_id=user.id,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@app.get("/api/prompts/{prompt_id}/versions", response_model=list[PromptVersionResponse])
def list_prompt_versions(
    prompt_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[PromptVersion]:
    prompt = db.get(Prompt, prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    authorize_project(db, prompt.project_id, user)
    return list(
        db.scalars(
            select(PromptVersion)
            .where(PromptVersion.prompt_id == prompt_id)
            .order_by(PromptVersion.version)
        )
    )


@app.post(
    "/api/projects/{project_id}/datasets",
    response_model=DatasetResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
def create_dataset(
    project_id: str,
    body: DatasetCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dataset:
    authorize_project(db, project_id, user)
    dataset = Dataset(project_id=project_id, name=body.name)
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


@app.post(
    "/api/datasets/{dataset_id}/versions",
    response_model=DatasetVersionResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
def create_dataset_version(
    dataset_id: str,
    body: DatasetVersionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetVersion:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    authorize_project(db, dataset.project_id, user)
    parsed = parse_dataset(
        body.content, body.format, settings.max_dataset_bytes, settings.max_dataset_rows
    )
    latest = (
        db.scalar(
            select(func.max(DatasetVersion.version)).where(DatasetVersion.dataset_id == dataset_id)
        )
        or 0
    )
    version = DatasetVersion(
        dataset_id=dataset_id,
        version=latest + 1,
        source_format=body.format,
        schema_snapshot=parsed.schema,
        row_count=len(parsed.cases),
        content_sha256=parsed.digest,
        created_by_id=user.id,
    )
    version.cases = [TestCase(position=index, **case) for index, case in enumerate(parsed.cases)]
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@app.get("/api/dataset-versions/{version_id}/cases", response_model=list[TestCaseResponse])
def list_cases(
    version_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[TestCase]:
    version = db.get(DatasetVersion, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Dataset version not found")
    authorize_project(db, version.dataset.project_id, user)
    return list(
        db.scalars(
            select(TestCase)
            .where(TestCase.dataset_version_id == version_id)
            .order_by(TestCase.position)
        )
    )


@app.post(
    "/api/projects/{project_id}/runs",
    response_model=RunResponse,
    status_code=202,
    dependencies=[Depends(require_csrf)],
)
def create_run(
    project_id: str,
    body: RunCreate,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=120)],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvaluationRun:
    authorize_project(db, project_id, user)
    existing = db.scalar(
        select(EvaluationRun).where(
            EvaluationRun.created_by_id == user.id, EvaluationRun.idempotency_key == idempotency_key
        )
    )
    if existing:
        return existing
    prompt_version = db.get(PromptVersion, body.prompt_version_id)
    dataset_version = db.get(DatasetVersion, body.dataset_version_id)
    if prompt_version is None or prompt_version.prompt.project_id != project_id:
        raise HTTPException(status_code=422, detail="Prompt version does not belong to project")
    if dataset_version is None or dataset_version.dataset.project_id != project_id:
        raise HTTPException(status_code=422, detail="Dataset version does not belong to project")
    if body.provider == "gemini":
        if not settings.llm_configured:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Gemini is disabled; set LLM_ENABLED=true and GEMINI_API_KEY on the server"
                ),
            )
        if dataset_version.row_count > settings.llm_max_cases_per_run:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Gemini runs are limited to {settings.llm_max_cases_per_run} cases; "
                    "split this dataset or use the mock provider"
                ),
            )
        reserved = _gemini_requests_reserved_today(db)
        if reserved + dataset_version.row_count > settings.llm_daily_request_limit:
            raise HTTPException(
                status_code=429,
                detail="The server-side daily Gemini request allowance is exhausted",
            )
    run = EvaluationRun(
        project_id=project_id,
        prompt_version_id=body.prompt_version_id,
        dataset_version_id=body.dataset_version_id,
        created_by_id=user.id,
        idempotency_key=idempotency_key,
        provider=body.provider,
        provider_config=body.provider_config,
        evaluators=[spec.model_dump(mode="json") for spec in body.evaluators],
    )
    db.add(run)
    db.flush()
    db.add(RunDispatch(run_id=run.id))
    db.add(
        RunEvent(run_id=run.id, sequence=1, event_type="run.queued", payload={"status": "queued"})
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate = db.scalar(
            select(EvaluationRun).where(
                EvaluationRun.created_by_id == user.id,
                EvaluationRun.idempotency_key == idempotency_key,
            )
        )
        if duplicate is None:
            raise
        return duplicate
    with suppress(Exception):
        dispatch_pending(limit=1)
    db.refresh(run)
    return run


def authorized_run(db: Session, run_id: str, user: User) -> EvaluationRun:
    run = db.get(EvaluationRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    authorize_project(db, run.project_id, user)
    return run


@app.get("/api/runs/{run_id}", response_model=RunResponse)
def get_run(
    run_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> EvaluationRun:
    return authorized_run(db, run_id, user)


@app.get("/api/runs/{run_id}/results", response_model=list[ResultResponse])
def get_results(
    run_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[EvaluationResult]:
    authorized_run(db, run_id, user)
    return list(
        db.scalars(
            select(EvaluationResult)
            .options(selectinload(EvaluationResult.scores))
            .where(EvaluationResult.run_id == run_id)
            .order_by(EvaluationResult.created_at)
        )
    )


@app.post(
    "/api/runs/{run_id}/diagnose",
    response_model=DiagnosisResponse,
    dependencies=[Depends(require_csrf)],
)
def diagnose_run(
    run_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> RunDiagnosis:
    run = authorized_run(db, run_id, user)
    existing = db.scalar(select(RunDiagnosis).where(RunDiagnosis.run_id == run_id))
    if existing is not None:
        return existing
    if run.status not in {"completed", "failed"}:
        raise HTTPException(status_code=409, detail="Only terminal runs can be diagnosed")
    if not settings.llm_configured:
        raise HTTPException(
            status_code=503,
            detail="AI diagnosis is disabled; configure the server-side Gemini integration",
        )
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    diagnosis_count = (
        db.scalar(select(func.count(RunDiagnosis.id)).where(RunDiagnosis.created_at >= today)) or 0
    )
    if diagnosis_count >= settings.llm_daily_diagnosis_limit:
        raise HTTPException(status_code=429, detail="The daily AI diagnosis allowance is exhausted")
    try:
        draft = diagnose_failed_run(db, run_id, settings)
    except NoFailedEvaluationsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except TemporaryProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PermanentProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    diagnosis = RunDiagnosis(
        run_id=run_id,
        provider=draft.provider,
        model=draft.model,
        summary=draft.summary,
        findings=draft.findings,
        actions=draft.actions,
        citations=draft.citations,
        evidence=draft.evidence,
        usage=draft.usage,
    )
    db.add(diagnosis)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate = db.scalar(select(RunDiagnosis).where(RunDiagnosis.run_id == run_id))
        if duplicate is None:
            raise
        return duplicate
    db.refresh(diagnosis)
    return diagnosis


@app.post(
    "/api/runs/{run_id}/cancel", response_model=RunResponse, dependencies=[Depends(require_csrf)]
)
def cancel_run(
    run_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> EvaluationRun:
    run = authorized_run(db, run_id, user)
    if run.status not in {"queued", "running"}:
        raise HTTPException(status_code=409, detail=f"Cannot cancel a {run.status} run")
    run.cancel_requested = True
    if run.status == "queued":
        run.status = "cancelled"
        run.finished_at = func.now()
    sequence = db.scalar(select(func.max(RunEvent.sequence)).where(RunEvent.run_id == run.id)) or 0
    db.add(
        RunEvent(
            run_id=run.id, sequence=sequence + 1, event_type="run.cancel.requested", payload={}
        )
    )
    db.commit()
    with suppress(Exception):
        Redis.from_url(settings.redis_url).setex(f"evalpulse:cancel:{run.id}", 3600, "1")
    db.refresh(run)
    return run


@app.get("/api/runs/{run_id}/events")
async def stream_events(
    run_id: str,
    request: Request,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    authorized_run(db, run_id, user)
    start = int(last_event_id or 0)

    async def events() -> AsyncIterator[str]:
        sequence = start
        idle_ticks = 0
        while not await request.is_disconnected():
            with SessionLocal() as event_db:
                durable = list(
                    event_db.scalars(
                        select(RunEvent)
                        .where(RunEvent.run_id == run_id, RunEvent.sequence > sequence)
                        .order_by(RunEvent.sequence)
                    )
                )
                run_state = event_db.get(EvaluationRun, run_id)
            for event in durable:
                sequence = event.sequence
                payload = {"type": event.event_type, **event.payload}
                yield f"id: {sequence}\nevent: {event.event_type}\ndata: {json.dumps(payload)}\n\n"
                idle_ticks = 0
            if (
                run_state
                and run_state.status in {"completed", "failed", "cancelled"}
                and not durable
            ):
                break
            idle_ticks += 1
            if idle_ticks % 15 == 0:
                yield ": keep-alive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post(
    "/api/projects/{project_id}/comparisons",
    response_model=ComparisonResponse,
    status_code=201,
    dependencies=[Depends(require_csrf)],
)
def create_comparison(
    project_id: str,
    body: ComparisonCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Comparison:
    authorize_project(db, project_id, user)
    baseline = authorized_run(db, body.baseline_run_id, user)
    candidate = authorized_run(db, body.candidate_run_id, user)
    if baseline.project_id != project_id or candidate.project_id != project_id:
        raise HTTPException(status_code=422, detail="Runs must belong to the selected project")
    if baseline.status != "completed" or candidate.status != "completed":
        raise HTTPException(status_code=409, detail="Both runs must be completed")
    passed, checks = compare_aggregates(baseline.aggregate, candidate.aggregate, body.policy)
    comparison = Comparison(
        project_id=project_id,
        baseline_run_id=baseline.id,
        candidate_run_id=candidate.id,
        policy_snapshot=body.policy,
        passed=passed,
        checks=checks,
        created_by_id=user.id,
    )
    db.add(comparison)
    db.commit()
    db.refresh(comparison)
    return comparison


@app.get("/api/comparisons/{comparison_id}", response_model=ComparisonResponse)
def get_comparison(
    comparison_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Comparison:
    comparison = db.get(Comparison, comparison_id)
    if comparison is None:
        raise HTTPException(status_code=404, detail="Comparison not found")
    authorize_project(db, comparison.project_id, user)
    return comparison


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ready"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
