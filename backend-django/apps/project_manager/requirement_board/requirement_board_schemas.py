from typing import List, Optional

from ninja import Field, Schema


class RequirementBoardProjectOptionSchema(Schema):
    id: str
    name: str
    design_id: Optional[str] = None
    sub_teams: List[str] = Field(default_factory=list)
    config_complete: bool = False


class RequirementBoardFilterOptionsSchema(Schema):
    projects: List[RequirementBoardProjectOptionSchema] = Field(default_factory=list)


class RequirementBoardDataQuerySchema(Schema):
    project_ids: List[str] = Field(..., description="项目 ID 列表")
    sub_teams: Optional[List[str]] = Field(None, description="责任团队列表")
    categories: Optional[List[str]] = Field(None, description="需求类型列表")
    develop_users: Optional[List[str]] = Field(None, description="开发责任人列表")
    test_users: Optional[List[str]] = Field(None, description="测试责任人列表")
    time_field: Optional[str] = Field(None, description="时间维度字段")
    time_start: Optional[str] = Field(None, description="时间区间开始")
    time_end: Optional[str] = Field(None, description="时间区间结束")
    accepted_time_start: Optional[str] = Field(
        None,
        description="验收时间开始（兼容旧参数）",
    )
    accepted_time_end: Optional[str] = Field(
        None,
        description="验收时间结束（兼容旧参数）",
    )
    page_no: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=500, description="每页条数")


class RequirementBoardSummaryQuerySchema(Schema):
    project_ids: List[str] = Field(..., description="项目 ID 列表")
    sub_teams: Optional[List[str]] = Field(None, description="责任团队列表")
    categories: Optional[List[str]] = Field(None, description="需求类型列表")
    develop_users: Optional[List[str]] = Field(None, description="开发责任人列表")
    test_users: Optional[List[str]] = Field(None, description="测试责任人列表")
    time_field: Optional[str] = Field(None, description="时间维度字段")
    time_start: Optional[str] = Field(None, description="时间区间开始")
    time_end: Optional[str] = Field(None, description="时间区间结束")
    accepted_time_start: Optional[str] = Field(
        None,
        description="验收时间开始（兼容旧参数）",
    )
    accepted_time_end: Optional[str] = Field(
        None,
        description="验收时间结束（兼容旧参数）",
    )


class RequirementBoardItemSchema(Schema):
    requirement_id: str
    title: str
    category: str
    status_code: str
    status_label: str
    raw_status: str = ""
    project_id: str
    project_name: str
    design_id: Optional[str] = None
    team_name: str
    planned_test_time: Optional[str] = None
    due_date: Optional[str] = None
    completed_time: Optional[str] = None
    accepted_time: Optional[str] = None
    is_dev_delayed: bool = False
    is_test_delayed: bool = False
    workload_kloc: float = 0.0
    workload_man_day: float = 0.0
    develop_users: List[str] = Field(default_factory=list)
    test_users: List[str] = Field(default_factory=list)
    develop_user_display: str = ""
    test_user_display: str = ""
    develop_user: str = ""
    test_user: str = ""


class RequirementBoardPageSchema(Schema):
    items: List[RequirementBoardItemSchema] = Field(default_factory=list)
    total: int = 0
    page_no: int = 1
    page_size: int = 20
    page_sum: int = 0


class RequirementStatusSummarySchema(Schema):
    status_code: str
    status_label: str
    count: int = 0
    count_rate: float = 0.0
    workload_man_day: float = 0.0
    workload_kloc: float = 0.0


class RequirementTypeSummarySchema(Schema):
    category: str
    total_count: int = 0
    total_workload_man_day: float = 0.0
    total_workload_kloc: float = 0.0


class RequirementProjectSummarySchema(Schema):
    project_id: str
    project_name: str
    total_count: int = 0
    total_workload_man_day: float = 0.0
    total_workload_kloc: float = 0.0


class RequirementCompletionSummarySchema(Schema):
    count: int = 0
    workload_man_day: float = 0.0
    workload_kloc: float = 0.0
    count_rate: float = 0.0
    workload_man_day_rate: float = 0.0
    workload_kloc_rate: float = 0.0


class RequirementTeamSummarySchema(Schema):
    team_name: str
    total_count: int = 0
    total_workload_man_day: float = 0.0
    total_workload_kloc: float = 0.0
    i_count: int = 0
    d_count: int = 0
    p_count: int = 0
    c_count: int = 0
    a_count: int = 0
    dev_done: RequirementCompletionSummarySchema
    acceptance_done: RequirementCompletionSummarySchema


class RequirementUserSummaryItemSchema(Schema):
    username: str
    task_count: int = 0
    workload_man_day: float = 0.0
    workload_kloc: float = 0.0


class RequirementUserSummarySchema(Schema):
    develop_users: List[RequirementUserSummaryItemSchema] = Field(default_factory=list)
    test_users: List[RequirementUserSummaryItemSchema] = Field(default_factory=list)


class RequirementDelayBucketSummarySchema(Schema):
    count: int = 0
    rate: float = 0.0
    preview_items: List[RequirementBoardItemSchema] = Field(default_factory=list)


class RequirementDelaySummarySchema(Schema):
    development: RequirementDelayBucketSummarySchema = Field(
        default_factory=lambda: RequirementDelayBucketSummarySchema()
    )
    acceptance: RequirementDelayBucketSummarySchema = Field(
        default_factory=lambda: RequirementDelayBucketSummarySchema()
    )


class RequirementDeliveryTrendItemSchema(Schema):
    month: str
    planned_count: int = 0
    actual_count: int = 0


class RequirementBoardSummarySchema(Schema):
    total_count: int = 0
    total_workload_man_day: float = 0.0
    total_workload_kloc: float = 0.0
    status_summary: List[RequirementStatusSummarySchema] = Field(default_factory=list)
    type_summary: List[RequirementTypeSummarySchema] = Field(default_factory=list)
    project_summary: List[RequirementProjectSummarySchema] = Field(default_factory=list)
    team_summary: List[RequirementTeamSummarySchema] = Field(default_factory=list)
    user_summary: RequirementUserSummarySchema = Field(
        default_factory=lambda: RequirementUserSummarySchema()
    )
    delay_summary: RequirementDelaySummarySchema = Field(
        default_factory=lambda: RequirementDelaySummarySchema()
    )
    development_delivery_trend: List[RequirementDeliveryTrendItemSchema] = Field(
        default_factory=list
    )
    acceptance_delivery_trend: List[RequirementDeliveryTrendItemSchema] = Field(
        default_factory=list
    )
