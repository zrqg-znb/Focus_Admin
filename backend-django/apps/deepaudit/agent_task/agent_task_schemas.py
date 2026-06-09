from __future__ import annotations

from typing import Any

from ninja import Field, Schema


class AgentTaskCreateSchema(Schema):
    project_id: str
    name: str | None = None
    description: str | None = None
    audit_scope: dict[str, Any] = Field(default_factory=dict)
    target_vulnerabilities: list[str] = Field(default_factory=list)
    verification_level: str = 'sandbox'
    repository_signature: str | None = None
    repository_url: str | None = None
    repository_type: str | None = None
    branch_name: str | None = None
    manifest_xml: str | None = None
    group: str | None = None
    exclude_patterns: list[str] = Field(default_factory=list)
    target_files: list[str] = Field(default_factory=list)
    max_iterations: int = 50
    timeout_seconds: int = 1800


class AgentFindingStatusUpdateSchema(Schema):
    status: str


class AgentTaskSchema(Schema):
    id: str
    project_id: str
    project_name: str
    created_by: str
    created_by_name: str | None = None
    name: str | None = None
    description: str | None = None
    task_type: str = 'agent_audit'
    status: str
    current_phase: str | None = None
    current_step: str | None = None
    audit_scope: dict[str, Any] = Field(default_factory=dict)
    target_vulnerabilities: list[str] = Field(default_factory=list)
    verification_level: str = 'sandbox'
    repository_url: str | None = None
    repository_type: str = 'single'
    repository_signature: str | None = None
    branch_name: str | None = None
    manifest_xml: str | None = None
    group: str | None = None
    exclude_patterns: list[str] = Field(default_factory=list)
    target_files: list[str] = Field(default_factory=list)
    selected_target_count: int = 0
    selected_directory_count: int = 0
    resolved_file_count: int = 0
    workspace_source: str | None = None
    workspace_path: str | None = None
    cache_repo: str | None = None
    last_synced_at: int | None = None
    max_iterations: int = 0
    timeout_seconds: int = 0
    total_files: int = 0
    indexed_files: int = 0
    analyzed_files: int = 0
    files_with_findings: int = 0
    total_chunks: int = 0
    total_iterations: int = 0
    tool_calls_count: int = 0
    tokens_used: int = 0
    findings_count: int = 0
    inventory_report: dict[str, Any] = Field(default_factory=dict)
    inventory_items_count: int = 0
    verified_count: int = 0
    false_positive_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    quality_score: float = 0.0
    security_score: float = 0.0
    progress_percentage: float = 0.0
    audit_plan: list[dict[str, Any]] = Field(default_factory=list)
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    sys_create_datetime: str | None = None
    sys_update_datetime: str | None = None


class AgentTaskListSchema(Schema):
    items: list[AgentTaskSchema]
    total: int


class AgentFindingSchema(Schema):
    id: str
    task_id: str
    vulnerability_type: str
    severity: str
    title: str
    description: str | None = None
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str | None = None
    is_verified: bool = False
    ai_confidence: float = 0.0
    status: str
    suggestion: str | None = None
    recommendation: str | None = None
    fix_code: str | None = None
    ai_explanation: str | None = None
    matched_line: str | None = None
    evidence: str | None = None
    validation: dict[str, Any] = Field(default_factory=dict)
    verification_method: str | None = None
    verification_details: str | None = None
    poc: dict[str, Any] = Field(default_factory=dict)
    sys_create_datetime: str | None = None
    sys_update_datetime: str | None = None


class AgentEventSchema(Schema):
    id: str
    task_id: str
    event_type: str
    phase: str | None = None
    message: str | None = None
    sequence: int = 0
    tool_name: str | None = None
    tool_input: dict[str, Any] = Field(default_factory=dict)
    tool_output: dict[str, Any] = Field(default_factory=dict)
    tool_duration_ms: int | None = None
    progress_percent: float | None = None
    finding_id: str | None = None
    tokens_used: int | None = None
    event_metadata: dict[str, Any] = Field(default_factory=dict)
    sys_create_datetime: str | None = None


class AgentSummarySchema(Schema):
    task_id: str
    status: str
    progress_percentage: float = 0.0
    security_score: float = 0.0
    quality_score: float = 0.0
    statistics: dict[str, int] = Field(default_factory=dict)
    severity_distribution: dict[str, int] = Field(default_factory=dict)
    vulnerability_types: dict[str, int] = Field(default_factory=dict)
    phases_completed: list[str] = Field(default_factory=list)
    duration_seconds: float | None = None


class AgentCheckpointSchema(Schema):
    id: str | None = None
    phase: str
    status: str
    sequence: int
    message: str | None = None
    timestamp: str | None = None
    agent_id: str | None = None
    agent_name: str | None = None
    agent_type: str | None = None
    iteration: int = 0
    checkpoint_type: str | None = None


class AgentCheckpointDetailSchema(AgentCheckpointSchema):
    task_id: str
    task_status: str
    progress_percentage: float = 0.0
    events: list[dict] = Field(default_factory=list)
    statistics: dict[str, int] = Field(default_factory=dict)
    state_data: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentTreeNodeSchema(Schema):
    id: str
    agent_id: str
    agent_name: str
    agent_type: str
    parent_agent_id: str | None = None
    depth: int = 0
    task_description: str | None = None
    knowledge_modules: list[str] = Field(default_factory=list)
    status: str
    result_summary: str | None = None
    findings_count: int = 0
    iterations: int = 0
    tokens_used: int = 0
    tool_calls: int = 0
    duration_ms: int | None = None
    children: list['AgentTreeNodeSchema'] = Field(default_factory=list)
