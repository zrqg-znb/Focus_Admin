from typing import Any
from datetime import datetime

from ninja import Schema
from pydantic import Field


class SkillOut(Schema):
    id: str
    name: str
    description: str
    original_filename: str
    file_manifest: list[str]
    sys_creator_name: str = ''
    sys_create_datetime: datetime | None = None


class PageOut(Schema):
    items: list[Any]
    total: int


class RunCreateIn(Schema):
    skill_id: str
    provider_id: str
    max_rounds: int = Field(default=5, ge=1, le=20)


class RunConfigIn(Schema):
    scenarios: list[dict]
    evaluations: list[dict]


class RunOut(Schema):
    id: str
    skill_id: str
    skill_name: str
    provider_id: str
    provider_name: str
    provider_model: str
    status: str
    max_rounds: int
    scenarios: list[dict]
    evaluations: list[dict]
    baseline_score: float
    final_score: float
    original_skill_md: str
    improved_skill_md: str
    error_message: str
    cancel_requested: bool
    started_at: datetime | None = None
    completed_at: datetime | None = None
    sys_creator_name: str = ''
    sys_create_datetime: datetime | None = None


class IterationOut(Schema):
    id: str
    round_number: int
    status: str
    score_before: float
    score_after: float
    kept: bool
    strategy: str
    diagnosis: str
    description: str
    evaluation_summary: list[dict]
    sys_create_datetime: datetime | None = None


class TraceOut(Schema):
    id: str
    round_number: int
    stage: str
    status: str
    request_content: str
    response_content: str
    error_message: str
    duration_ms: int
    sys_create_datetime: datetime | None = None
