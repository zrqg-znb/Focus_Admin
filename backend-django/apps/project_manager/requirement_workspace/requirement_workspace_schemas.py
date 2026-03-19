from typing import List, Optional

from ninja import Field, Schema


class RequirementWorkspaceFieldOverviewSchema(Schema):
    field_key: str
    field_label: str
    applicable_count: int = 0
    filled_count: int = 0
    missing_count: int = 0
    filled_rate: float = 0.0


class RequirementWorkspacePreviewItemSchema(Schema):
    project_id: str = ""
    project_name: str = ""
    team_name: str = ""
    requirement_id: str = ""
    title: str = ""
    status_code: str = ""
    status_label: str = ""
    planned_test_time: Optional[str] = None
    due_date: Optional[str] = None
    completed_time: Optional[str] = None
    accepted_time: Optional[str] = None
    develop_user_display: str = ""
    test_user_display: str = ""


class RequirementWorkspaceMissingPreviewSchema(Schema):
    planned_test_time: List[RequirementWorkspacePreviewItemSchema] = Field(
        default_factory=list,
    )
    due_date: List[RequirementWorkspacePreviewItemSchema] = Field(default_factory=list)
    develop_users: List[RequirementWorkspacePreviewItemSchema] = Field(
        default_factory=list,
    )
    test_users: List[RequirementWorkspacePreviewItemSchema] = Field(default_factory=list)
    workload_man_day: List[RequirementWorkspacePreviewItemSchema] = Field(
        default_factory=list,
    )
    workload_kloc: List[RequirementWorkspacePreviewItemSchema] = Field(
        default_factory=list,
    )


class RequirementWorkspaceDelayPreviewSchema(Schema):
    development: List[RequirementWorkspacePreviewItemSchema] = Field(
        default_factory=list,
    )
    acceptance: List[RequirementWorkspacePreviewItemSchema] = Field(
        default_factory=list,
    )


class RequirementWorkspaceProjectFieldSchema(Schema):
    applicable_count: int = 0
    filled_count: int = 0
    missing_count: int = 0
    filled_rate: float = 0.0


class RequirementWorkspaceProjectFieldsSchema(Schema):
    planned_test_time: RequirementWorkspaceProjectFieldSchema = Field(
        default_factory=lambda: RequirementWorkspaceProjectFieldSchema(),
    )
    due_date: RequirementWorkspaceProjectFieldSchema = Field(
        default_factory=lambda: RequirementWorkspaceProjectFieldSchema(),
    )
    develop_users: RequirementWorkspaceProjectFieldSchema = Field(
        default_factory=lambda: RequirementWorkspaceProjectFieldSchema(),
    )
    test_users: RequirementWorkspaceProjectFieldSchema = Field(
        default_factory=lambda: RequirementWorkspaceProjectFieldSchema(),
    )
    workload_man_day: RequirementWorkspaceProjectFieldSchema = Field(
        default_factory=lambda: RequirementWorkspaceProjectFieldSchema(),
    )
    workload_kloc: RequirementWorkspaceProjectFieldSchema = Field(
        default_factory=lambda: RequirementWorkspaceProjectFieldSchema(),
    )


class RequirementWorkspaceProjectDelaySchema(Schema):
    development_count: int = 0
    development_rate: float = 0.0
    acceptance_count: int = 0
    acceptance_rate: float = 0.0


class RequirementWorkspaceProjectRowSchema(Schema):
    project_id: str = ""
    project_name: str = ""
    total_count: int = 0
    fields: RequirementWorkspaceProjectFieldsSchema = Field(
        default_factory=lambda: RequirementWorkspaceProjectFieldsSchema(),
    )
    delay: RequirementWorkspaceProjectDelaySchema = Field(
        default_factory=lambda: RequirementWorkspaceProjectDelaySchema(),
    )
    completion_score: float = 0.0


class RequirementWorkspaceLatestSchema(Schema):
    generated_at: Optional[str] = None
    scope: str = ""
    project_count: int = 0
    requirement_count: int = 0
    field_overview: List[RequirementWorkspaceFieldOverviewSchema] = Field(
        default_factory=list,
    )
    project_rows: List[RequirementWorkspaceProjectRowSchema] = Field(
        default_factory=list,
    )
    missing_previews: RequirementWorkspaceMissingPreviewSchema = Field(
        default_factory=lambda: RequirementWorkspaceMissingPreviewSchema(),
    )
    delay_previews: RequirementWorkspaceDelayPreviewSchema = Field(
        default_factory=lambda: RequirementWorkspaceDelayPreviewSchema(),
    )
