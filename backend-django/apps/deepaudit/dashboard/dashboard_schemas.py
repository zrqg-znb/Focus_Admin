from __future__ import annotations

from typing import Any

from ninja import Field, Schema


class RecentActivitySchema(Schema):
    id: str
    task_kind: str
    project_id: str
    project_name: str
    title: str
    status: str
    issues_count: int = 0
    findings_count: int = 0
    created_by_name: str | None = None
    created_at: str | None = None
    route_path: str | None = None


class DashboardOverviewSchema(Schema):
    project_summary: dict[str, int] = Field(default_factory=dict)
    scan_task_summary: dict[str, int] = Field(default_factory=dict)
    agent_task_summary: dict[str, int] = Field(default_factory=dict)
    issue_summary: dict[str, int] = Field(default_factory=dict)
    finding_summary: dict[str, int] = Field(default_factory=dict)
    severity_distribution: dict[str, int] = Field(default_factory=dict)
    storage_summary: dict[str, int] = Field(default_factory=dict)
    recent_activities: list[RecentActivitySchema] = Field(default_factory=list)


class HealthStoragePathSchema(Schema):
    name: str
    path: str
    exists: bool = False
    size_bytes: int = 0


class HealthReportSchema(Schema):
    docker_enabled: bool = True
    docker_available: bool = False
    queue: str = 'deepaudit'
    storage_paths: list[HealthStoragePathSchema] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)


class DataCleanupRequestSchema(Schema):
    days: int = 1
    remove_reports: bool = False


class DataCleanupResultSchema(Schema):
    removed_workspaces: int = 0
    removed_reports: int = 0
    removed_files: list[str] = Field(default_factory=list)


class DataClearResultSchema(Schema):
    message: str = '清空完成'
    deleted: dict[str, int] = Field(default_factory=dict)
    removed_files: list[str] = Field(default_factory=list)


class DataExportSchema(Schema):
    project_count: int = 0
    scan_task_count: int = 0
    agent_task_count: int = 0
    prompt_template_count: int = 0
    rule_set_count: int = 0
    instant_record_count: int = 0
    payload: dict[str, Any] = Field(default_factory=dict)


class DataImportRequestSchema(Schema):
    payload: dict[str, Any] = Field(default_factory=dict)


class DataImportResultSchema(Schema):
    message: str = '导入完成'
    imported: dict[str, int] = Field(default_factory=dict)
    skipped: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class DataStatisticsSchema(Schema):
    model_counts: dict[str, int] = Field(default_factory=dict)
    orphan_counts: dict[str, int] = Field(default_factory=dict)
