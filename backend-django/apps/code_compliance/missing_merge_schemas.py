from datetime import datetime
from typing import List, Optional

from ninja import Schema
from pydantic import Field

from .base_schemas import OrganizationOut, PaginatedRepositoryOut, RepositoryOut


class MissingMergeOperationLogOut(Schema):
    id: str
    operation_type: str
    operation_type_label: str
    source: str
    source_label: str
    from_status: str
    from_status_label: str
    to_status: str
    to_status_label: str
    operator_id: Optional[str] = None
    operator_name: str
    remark: str
    operated_at: datetime


class MissingMergeRecordOut(Schema):
    id: str
    organization_id: Optional[str] = None
    organization_group_id: str
    organization_name: str
    repository_id: Optional[str] = None
    repository_project_id: str
    repository_name: str
    project_id: str
    trunk_branch: str
    release_branch: str
    change_request_iid: str
    change_key: str
    title: str
    description: str
    web_url: str
    added_lines: int
    removed_lines: int
    merged_at: Optional[datetime] = None
    target_branch: str
    author_username: str
    author_user_id: Optional[str] = None
    author_user_name: str
    author_pl_group_id: Optional[str] = None
    author_pl_group_name: str
    detected_at: datetime
    status: str
    status_label: str
    handled_by_id: Optional[str] = None
    handled_by_name: Optional[str] = None
    handled_at: Optional[datetime] = None
    handle_remark: str
    operation_logs: List[MissingMergeOperationLogOut] = Field(default_factory=list)
    sys_create_datetime: Optional[datetime] = None
    sys_update_datetime: Optional[datetime] = None


class PaginatedMissingMergeRecordOut(Schema):
    items: List[MissingMergeRecordOut] = Field(default_factory=list)
    total: int


class MissingMergeRecordStatusIn(Schema):
    status: str
    handle_remark: Optional[str] = None


class MissingMergeScanTaskOut(Schema):
    id: str
    trigger_type: str
    trigger_type_label: str
    status: str
    status_label: str
    merged_after: datetime
    merged_before: datetime
    filter_payload: dict = Field(default_factory=dict)
    scan_diagnostics: dict = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    scanned_organization_count: int
    scanned_repository_count: int
    scanned_branch_pair_count: int
    detected_count: int
    created_count: int
    updated_count: int
    fixed_count: int
    error_message: str
    sys_create_datetime: Optional[datetime] = None
    sys_update_datetime: Optional[datetime] = None


class PaginatedMissingMergeScanTaskOut(Schema):
    items: List[MissingMergeScanTaskOut] = Field(default_factory=list)
    total: int


class MissingMergeScanRunOut(Schema):
    accepted: bool
    message: str
    task: MissingMergeScanTaskOut


class MissingMergePlGroupOptionOut(Schema):
    id: str
    name: str
    code: str = ""


class MissingMergeOptionsOut(Schema):
    organizations: List[OrganizationOut] = Field(default_factory=list)
    repositories: List[RepositoryOut] = Field(default_factory=list)
    pl_groups: List[MissingMergePlGroupOptionOut] = Field(default_factory=list)


class MissingMergePlDashboardSummaryOut(Schema):
    total_count: int
    open_count: int
    fixed_count: int
    ignored_count: int
    pl_group_count: int
    missing_merged_at_count: int
    merged_after: Optional[datetime] = None
    merged_before: Optional[datetime] = None


class MissingMergePlDashboardTrendSeriesOut(Schema):
    pl_group_id: Optional[str] = None
    pl_group_name: str
    data: List[int] = Field(default_factory=list)


class MissingMergePlDashboardStatusOut(Schema):
    status: str
    status_label: str
    count: int


class MissingMergePlDashboardGroupOut(Schema):
    pl_group_id: Optional[str] = None
    pl_group_name: str
    total_count: int
    open_count: int
    fixed_count: int
    ignored_count: int
    latest_detected_at: Optional[datetime] = None


class MissingMergePlDashboardOut(Schema):
    summary: MissingMergePlDashboardSummaryOut
    weeks: List[str] = Field(default_factory=list)
    months: List[str] = Field(default_factory=list)
    trend_series: List[MissingMergePlDashboardTrendSeriesOut] = Field(default_factory=list)
    status_distribution: List[MissingMergePlDashboardStatusOut] = Field(default_factory=list)
    pl_groups: List[MissingMergePlDashboardGroupOut] = Field(default_factory=list)


class MissingMergeRepositoryOptionsOut(PaginatedRepositoryOut):
    pass


class MissingMergeScanRunIn(Schema):
    merged_after: datetime
    merged_before: datetime
    organization_id: Optional[str] = None
    repository_id: Optional[str] = None
    repository_ids: List[str] = Field(default_factory=list)
