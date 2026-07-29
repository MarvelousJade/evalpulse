from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(ApiModel):
    message: str


class LoginRequest(ApiModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)


class UserResponse(ApiModel):
    id: str
    email: str
    display_name: str


class ProjectCreate(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)


class ProjectResponse(ApiModel):
    id: str
    name: str
    description: str
    owner_id: str
    created_at: datetime


class PromptCreate(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=20_000)
    variables: list[str] = Field(default_factory=list, max_length=50)


class PromptVersionCreate(ApiModel):
    text: str = Field(min_length=1, max_length=20_000)
    variables: list[str] = Field(default_factory=list, max_length=50)


class PromptVersionResponse(ApiModel):
    id: str
    prompt_id: str
    version: int
    text: str
    variables: list[str]
    created_at: datetime


class PromptResponse(ApiModel):
    id: str
    project_id: str
    name: str
    versions: list[PromptVersionResponse]


class DatasetCreate(ApiModel):
    name: str = Field(min_length=1, max_length=120)


class DatasetResponse(ApiModel):
    id: str
    project_id: str
    name: str


class DatasetVersionCreate(ApiModel):
    format: Literal["json", "csv"]
    content: str = Field(min_length=2)


class DatasetVersionResponse(ApiModel):
    id: str
    dataset_id: str
    version: int
    source_format: str
    row_count: int
    content_sha256: str
    created_at: datetime


class TestCaseResponse(ApiModel):
    id: str
    position: int
    input: dict[str, Any]
    expected: Any
    tags: list[str]


class EvaluatorSpec(ApiModel):
    type: Literal[
        "exact_match",
        "case_insensitive_exact_match",
        "contains_all",
        "regex",
        "valid_json",
        "json_schema",
        "required_json_keys",
        "max_latency",
    ]
    options: dict[str, Any] = Field(default_factory=dict)


class RunCreate(ApiModel):
    prompt_version_id: str
    dataset_version_id: str
    provider: Literal["mock", "gemini"] = "mock"
    provider_config: dict[str, Any] = Field(default_factory=dict)
    evaluators: list[EvaluatorSpec] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_provider_config(self) -> RunCreate:
        if self.provider != "gemini":
            return self
        if self.provider_config:
            raise ValueError("Gemini provider_config is server-controlled and must be empty")
        return self


class RunResponse(ApiModel):
    id: str
    project_id: str
    prompt_version_id: str
    dataset_version_id: str
    status: str
    provider: str
    evaluators: list[dict[str, Any]]
    aggregate: dict[str, Any]
    cancel_requested: bool
    failure_reason: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ScoreResponse(ApiModel):
    name: str
    passed: bool
    value: float | None
    explanation: str


class ResultResponse(ApiModel):
    id: str
    test_case_id: str
    output: Any
    latency_ms: float
    input_tokens: int
    output_tokens: int
    passed: bool
    error_type: str | None
    error_message: str | None
    scores: list[ScoreResponse]


class AiStatusResponse(ApiModel):
    enabled: bool
    provider: str
    model: str
    max_cases_per_run: int
    max_output_tokens: int
    daily_request_limit: int


class CitationResponse(ApiModel):
    id: str
    path: str
    heading: str
    excerpt: str
    score: float


class DiagnosisResponse(ApiModel):
    id: str
    run_id: str
    provider: str
    model: str
    summary: str
    findings: list[str]
    actions: list[str]
    citations: list[CitationResponse]
    evidence: dict[str, Any]
    usage: dict[str, Any]
    created_at: datetime


class ComparisonCreate(ApiModel):
    baseline_run_id: str
    candidate_run_id: str
    policy: dict[str, Any] = Field(
        default_factory=lambda: {
            "max_pass_rate_drop": 0.02,
            "critical_pass_rate": 1.0,
            "max_p95_latency_increase": 0.20,
            "max_provider_error_rate": 0.01,
        }
    )


class ComparisonResponse(ApiModel):
    id: str
    project_id: str
    baseline_run_id: str
    candidate_run_id: str
    policy_snapshot: dict[str, Any]
    passed: bool
    checks: list[dict[str, Any]]
    created_at: datetime
