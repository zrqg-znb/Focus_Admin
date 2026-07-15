from datetime import date, datetime
from typing import List, Optional

from ninja import Schema
from pydantic import Field


class ContributionFilterIn(Schema):
    source_mode: Optional[str] = None
    organization_ids: Optional[str] = None
    repository_ids: Optional[str] = None
    branch_ids: Optional[str] = None
    branch_type: Optional[str] = None
    repo_type: Optional[str] = None
    domain: Optional[str] = None
    pl_group_ids: Optional[str] = None
    author_username: Optional[str] = None
    keyword: Optional[str] = None
    merged_after: Optional[datetime] = None
    merged_before: Optional[datetime] = None


class ContributionMetricOut(Schema):
    active_repository_count: int
    active_branch_count: int
    baseline_repository_count: int = 0
    baseline_branch_count: int = 0
    missing_baseline_count: int = 0
    stock_lines: int = 0
    cr_count: int
    contributor_count: int
    added_lines: int
    removed_lines: int
    net_lines: int
    changed_lines: int


class ContributionTrendPointOut(Schema):
    date: date
    added_lines: int
    removed_lines: int
    net_lines: int
    changed_lines: int
    cr_count: int


class ContributionPlGroupTrendPointOut(Schema):
    date: date
    pl_group_name: str
    added_lines: int
    removed_lines: int
    changed_lines: int
    cr_count: int


class ContributionRankingItemOut(Schema):
    id: str
    repository_id: str
    branch_id: Optional[str] = None
    name: str
    project_id: str = ""
    branch_name: str = ""
    repository_name: str = ""
    source_mode: str = "CR"
    baseline_id: Optional[str] = None
    baseline_at: Optional[datetime] = None
    baseline_lines: int = 0
    stock_lines: int = 0
    has_baseline: bool = False
    cr_count: int
    contributor_count: int
    added_lines: int
    removed_lines: int
    net_lines: int
    changed_lines: int


class PaginatedContributionRankingOut(Schema):
    items: List[ContributionRankingItemOut] = Field(default_factory=list)
    total: int


class ContributionPersonRankingItemOut(Schema):
    author_user_id: Optional[str] = None
    author_username: str
    author_user_name: str
    author_display_name: str
    author_pl_group_id: Optional[str] = None
    author_pl_group_name: str
    repository_count: int
    branch_count: int
    cr_count: int
    added_lines: int
    removed_lines: int
    net_lines: int
    changed_lines: int


class PaginatedContributionPersonRankingOut(Schema):
    items: List[ContributionPersonRankingItemOut] = Field(default_factory=list)
    total: int


class ContributionPlGroupRankingItemOut(Schema):
    pl_group_id: str
    pl_group_name: str
    contributor_count: int
    repository_count: int
    branch_count: int
    cr_count: int
    added_lines: int
    removed_lines: int
    net_lines: int
    changed_lines: int


class PaginatedContributionPlGroupRankingOut(Schema):
    items: List[ContributionPlGroupRankingItemOut] = Field(default_factory=list)
    total: int


class ContributionCategoryItemOut(Schema):
    category: str
    category_label: str
    count: int
    cr_count: int
    added_lines: int
    removed_lines: int
    net_lines: int
    changed_lines: int


class ContributionCategoryDistributionOut(Schema):
    repo_types: List[ContributionCategoryItemOut] = Field(default_factory=list)
    domains: List[ContributionCategoryItemOut] = Field(default_factory=list)
    pl_groups: List[ContributionCategoryItemOut] = Field(default_factory=list)


class ContributionRecordOut(Schema):
    id: str
    contribution_date: date
    organization_id: Optional[str] = None
    organization_group_id: str
    organization_name: str
    repository_id: Optional[str] = None
    repository_project_id: str
    repository_name: str
    branch_id: Optional[str] = None
    branch_name: str
    branch_type: str
    branch_type_label: str
    repo_type: str
    repo_type_label: str
    domain: str
    domain_label: str
    source_mode: str
    source_change_id: str
    change_request_iid: str
    change_key: str
    title: str
    web_url: str
    merged_at: Optional[datetime] = None
    target_branch: str
    author_username: str
    author_user_id: Optional[str] = None
    author_user_name: str
    author_display_name: str
    author_pl_group_id: Optional[str] = None
    author_pl_group_name: str
    added_lines: int
    removed_lines: int
    net_lines: int
    changed_lines: int


class PaginatedContributionRecordOut(Schema):
    items: List[ContributionRecordOut] = Field(default_factory=list)
    total: int


class ContributionCollectTaskOut(Schema):
    id: str
    trigger_type: str
    trigger_type_label: str
    status: str
    status_label: str
    merged_after: datetime
    merged_before: datetime
    filter_payload: dict = Field(default_factory=dict)
    collect_diagnostics: dict = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    scanned_organization_count: int
    scanned_repository_count: int
    scanned_branch_count: int
    fetched_count: int
    created_count: int
    updated_count: int
    skipped_count: int
    aggregate_count: int
    error_message: str
    sys_create_datetime: Optional[datetime] = None


class PaginatedContributionCollectTaskOut(Schema):
    items: List[ContributionCollectTaskOut] = Field(default_factory=list)
    total: int


class ContributionCollectRunIn(Schema):
    merged_after: datetime
    merged_before: datetime
    organization_ids: List[str] = Field(default_factory=list)
    repository_ids: List[str] = Field(default_factory=list)
    branch_ids: List[str] = Field(default_factory=list)
    source_mode: Optional[str] = None


class ContributionCollectRunOut(Schema):
    accepted: bool
    message: str
    task: ContributionCollectTaskOut


class ContributionExportTaskIn(Schema):
    scope: str = "summary"
    filters: dict = Field(default_factory=dict)


class ContributionExportTaskOut(Schema):
    id: str
    scope: str
    fingerprint: str
    status: str
    progress: int
    message: str
    error_message: str
    file_name: str
    file_size: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    sys_create_datetime: Optional[datetime] = None


class ContributionExportTaskPrepareOut(Schema):
    mode: str
    task: ContributionExportTaskOut


class ContributionCodeBaselineOut(Schema):
    id: str
    organization_id: Optional[str] = None
    organization_group_id: str
    organization_name: str
    repository_id: str
    repository_project_id: str
    repository_name: str
    branch_id: Optional[str] = None
    branch_name: str
    branch_type: str
    baseline_lines: int
    baseline_at: datetime
    source: str
    source_label: str
    remark: str
    is_current: bool
    operator_name: str
    sys_create_datetime: Optional[datetime] = None


class PaginatedContributionCodeBaselineOut(Schema):
    items: List[ContributionCodeBaselineOut] = Field(default_factory=list)
    total: int


class ContributionCodeBaselineIn(Schema):
    repository_id: str
    branch_id: str
    baseline_lines: int
    baseline_at: datetime
    remark: str = ""
