from __future__ import annotations

from typing import Any

from ninja import Field, Schema


class AuditIssueSchema(Schema):
    id: str
    task_id: str
    file_path: str
    line_number: int | None = None
    column_number: int | None = None
    issue_type: str
    severity: str
    title: str
    message: str | None = None
    description: str | None = None
    suggestion: str | None = None
    code_snippet: str | None = None
    ai_explanation: dict[str, Any] = Field(default_factory=dict)
    status: str
    resolved_by: str | None = None
    resolved_at: str | None = None
    sys_create_datetime: str | None = None
    sys_update_datetime: str | None = None


class AuditIssueUpdateSchema(Schema):
    status: str


class AuditTaskCreateSchema(Schema):
    project_id: str
    branch_name: str | None = None
    manifest_xml: str | None = None
    group: str | None = None
    exclude_patterns: list[str] = Field(default_factory=list)
    file_paths: list[str] = Field(default_factory=list)
    rule_set_id: str | None = None
    prompt_template_id: str | None = None
    include_tests: bool = False
    include_docs: bool = False
    max_file_size: int | None = None
    analysis_depth: str = 'standard'


class AuditTaskSchema(Schema):
    id: str
    project_id: str
    project_name: str
    created_by: str
    created_by_name: str | None = None
    task_type: str
    status: str
    branch_name: str | None = None
    manifest_xml: str | None = None
    group: str | None = None
    exclude_patterns: list[str] = Field(default_factory=list)
    scan_config: dict[str, Any] = Field(default_factory=dict)
    total_files: int = 0
    scanned_files: int = 0
    total_lines: int = 0
    issues_count: int = 0
    quality_score: float = 0.0
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None
    sys_create_datetime: str | None = None
    sys_update_datetime: str | None = None


class AuditTaskDetailSchema(AuditTaskSchema):
    summary: dict[str, Any] = Field(default_factory=dict)
    issues: list[AuditIssueSchema] = Field(default_factory=list)


class AuditTaskListSchema(Schema):
    items: list[AuditTaskSchema]
    total: int


class InstantAnalysisRequestSchema(Schema):
    code_content: str = ''
    language: str = 'python'
    file_name: str | None = None


class InstantAnalysisRecordSchema(Schema):
    id: str
    language: str
    issues_count: int = 0
    quality_score: float = 0.0
    analysis_time: float = 0.0
    analysis_result: dict[str, Any] = Field(default_factory=dict)
    code_content: str | None = None
    sys_create_datetime: str | None = None


class InstantAnalysisListSchema(Schema):
    items: list[InstantAnalysisRecordSchema]
    total: int
