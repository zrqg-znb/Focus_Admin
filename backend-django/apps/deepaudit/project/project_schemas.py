from __future__ import annotations

from typing import Any

from ninja import Field, Schema


class UserBriefSchema(Schema):
    id: str = ''
    username: str = ''
    name: str = ''


class AuditProjectBaseSchema(Schema):
    name: str
    description: str | None = None
    source_type: str = 'repository'
    repository_url: str | None = None
    repository_type: str = 'single'
    default_branch: str = 'main'
    manifest_xml: str | None = None
    group: str | None = None
    programming_languages: list[str] = Field(default_factory=list)
    is_active: bool = True


class AuditProjectCreateSchema(AuditProjectBaseSchema):
    pass


class AuditProjectUpdateSchema(Schema):
    name: str | None = None
    description: str | None = None
    source_type: str | None = None
    repository_url: str | None = None
    repository_type: str | None = None
    default_branch: str | None = None
    manifest_xml: str | None = None
    group: str | None = None
    programming_languages: list[str] | None = None
    is_active: bool | None = None


class ProjectMemberSaveSchema(Schema):
    user_id: str
    role: str = 'member'
    permissions: dict[str, Any] = Field(default_factory=dict)


class ProjectOwnerTransferSchema(Schema):
    user_id: str


class ProjectZipMetaSchema(Schema):
    has_file: bool = False
    display_name: str | None = None
    file_path: str | None = None
    size: int | None = None
    uploaded_at: str | None = None


class ProjectFileItemSchema(Schema):
    path: str
    size: int = 0


class ProjectRepositorySpecSchema(Schema):
    repository_type: str = 'single'
    repository_url: str | None = None
    branch_name: str = 'main'
    manifest_xml: str | None = None
    group: str | None = None


class ProjectFileBrowserItemSchema(Schema):
    kind: str
    name: str
    path: str
    size: int = 0
    selectable: bool = True
    unavailable_reason: str | None = None


class ProjectFileBrowserResponseSchema(Schema):
    items: list[ProjectFileBrowserItemSchema] = Field(default_factory=list)
    offset: int = 0
    limit: int = 100
    total: int = 0
    has_more: bool = False
    path: str = ''
    keyword: str = ''
    last_synced_at: int | None = None
    repository_spec: ProjectRepositorySpecSchema = Field(default_factory=ProjectRepositorySpecSchema)
    repository_signature: str = ''


class ProjectMemberSchema(UserBriefSchema):
    member_id: str
    project_id: str
    role: str
    permissions: dict[str, Any] = Field(default_factory=dict)
    sys_create_datetime: str | None = None
    sys_update_datetime: str | None = None


class ProjectTaskSummarySchema(Schema):
    scan_task_count: int = 0
    active_scan_task_count: int = 0
    agent_task_count: int = 0
    active_agent_task_count: int = 0
    findings_count: int = 0
    open_issue_count: int = 0


class ProjectStatsSchema(Schema):
    total_projects: int = 0
    active_projects: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    total_issues: int = 0
    resolved_issues: int = 0
    avg_quality_score: float = 0.0


class AuditProjectSummarySchema(Schema):
    id: str
    name: str
    description: str | None = None
    source_type: str
    repository_url: str | None = None
    repository_type: str
    default_branch: str
    manifest_xml: str | None = None
    group: str | None = None
    programming_languages: list[str] = Field(default_factory=list)
    owner: UserBriefSchema
    current_role: str = 'viewer'
    is_active: bool = True
    is_deleted: bool = False
    members_count: int = 0
    latest_task_at: str | None = None
    latest_agent_task_at: str | None = None
    sys_create_datetime: str | None = None
    sys_update_datetime: str | None = None


class AuditProjectDetailSchema(AuditProjectSummarySchema):
    task_summary: ProjectTaskSummarySchema = Field(default_factory=ProjectTaskSummarySchema)
    members: list[ProjectMemberSchema] = Field(default_factory=list)
    zip_meta: ProjectZipMetaSchema | None = None


class PaginatedProjectSchema(Schema):
    items: list[AuditProjectSummarySchema]
    total: int


class PaginatedProjectRecycleSchema(Schema):
    items: list[AuditProjectSummarySchema]
    total: int


ProjectSummarySchema = AuditProjectSummarySchema
ProjectDetailSchema = AuditProjectDetailSchema
