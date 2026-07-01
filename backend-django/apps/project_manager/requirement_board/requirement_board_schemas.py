from typing import List, Optional

from ninja import Field, Schema


class RequirementBoardProjectOptionSchema(Schema):
    id: str
    name: str
    code: str = ""
    domain: str = ""
    type: str = ""
    design_id: Optional[str] = None
    sub_teams: List[str] = Field(default_factory=list)
    config_complete: bool = False
    is_favorited: bool = False


class RequirementBoardFilterPayloadSchema(Schema):
    project_ids: List[str] = Field(default_factory=list, description="项目 ID 列表")
    sub_teams: Optional[List[str]] = Field(None, description="责任团队列表")
    categories: Optional[List[str]] = Field(None, description="需求类型列表")
    schedule_state: Optional[List[str]] = Field(
        None,
        description="排期状态列表（I/D/P/C/A）",
    )
    verification_policies: Optional[List[str]] = Field(
        None,
        description="验证策略列表",
    )
    requirement_id_keyword: Optional[str] = Field(None, description="需求 ID 关键词")
    title_keyword: Optional[str] = Field(None, description="需求标题关键词")
    develop_user: Optional[List[str]] = Field(None, description="开发责任人列表（username）")
    test_user: Optional[List[str]] = Field(None, description="测试责任人列表（username）")
    responsible_pl_group_ids: Optional[List[str]] = Field(
        None,
        description="责任PL组列表，unknown 表示未识别PL领域",
    )
    develop_users: Optional[List[str]] = Field(None, description="开发责任人列表")
    test_users: Optional[List[str]] = Field(None, description="测试责任人列表")
    time_field: Optional[str] = Field(None, description="时间维度字段")
    time_start: Optional[str] = Field(None, description="时间区间开始")
    time_end: Optional[str] = Field(None, description="时间区间结束")
    planned_test_time_start: Optional[str] = Field(None, description="计划转测时间开始")
    planned_test_time_end: Optional[str] = Field(None, description="计划转测时间结束")
    due_date_start: Optional[str] = Field(None, description="计划完成时间开始")
    due_date_end: Optional[str] = Field(None, description="计划完成时间结束")
    completed_time_start: Optional[str] = Field(None, description="开发完成时间开始")
    completed_time_end: Optional[str] = Field(None, description="开发完成时间结束")
    accepted_time_start: Optional[str] = Field(
        None,
        description="测试完成时间开始",
    )
    accepted_time_end: Optional[str] = Field(
        None,
        description="测试完成时间结束",
    )
    dev_delay_status: Optional[str] = Field(None, description="开发延期筛选 all/normal/delayed")
    test_delay_status: Optional[str] = Field(None, description="测试延期筛选 all/normal/delayed")


class RequirementBoardFilterOptionsSchema(Schema):
    projects: List[RequirementBoardProjectOptionSchema] = Field(default_factory=list)
    saved_filter: Optional[RequirementBoardFilterPayloadSchema] = None


class RequirementBoardQueryPreparePayloadSchema(RequirementBoardFilterPayloadSchema):
    project_ids: List[str] = Field(..., description="项目 ID 列表")


class RequirementBoardQueryTaskSchema(Schema):
    id: str
    fingerprint: str = ""
    status: str = ""
    message: str = ""
    error_message: str = ""
    progress: int = 0
    scanned_pages: int = 0
    total_pages: int = 0
    matched_count: int = 0
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class RequirementBoardQueryPrepareResponseSchema(Schema):
    mode: str
    task: Optional[RequirementBoardQueryTaskSchema] = None


class RequirementBoardDataQuerySchema(RequirementBoardFilterPayloadSchema):
    project_ids: List[str] = Field(..., description="项目 ID 列表")
    page_no: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=500, description="每页条数")


class RequirementBoardSummaryQuerySchema(RequirementBoardFilterPayloadSchema):
    project_ids: List[str] = Field(..., description="项目 ID 列表")


class RequirementBoardExportQuerySchema(RequirementBoardSummaryQuerySchema):
    pass


class RequirementBoardItemSchema(Schema):
    requirement_id: str
    title: str
    category: str
    verification_policy: str = ""
    verification_policy_label: str = ""
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
    responsible_pl_group_id: Optional[str] = None
    responsible_pl_group_name: str = ""
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


class RequirementPlGroupSummarySchema(Schema):
    pl_group_id: Optional[str] = None
    pl_group_name: str
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


class RequirementDispatchRateSchema(Schema):
    p_total: int = 0
    develop_owner_count: int = 0
    develop_owner_rate: float = 0.0
    test_owner_count: int = 0
    test_owner_rate: float = 0.0


class RequirementPlanRefreshRateSchema(Schema):
    planned_test_time_count: int = 0
    planned_test_time_rate: float = 0.0
    due_date_count: int = 0
    due_date_rate: float = 0.0


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


class RequirementDeliveryDelayRankingItemSchema(Schema):
    dimension_id: Optional[str] = None
    dimension_name: str
    total_count: int = 0
    delayed_count: int = 0
    delay_rate: float = 0.0
    delayed_workload_man_day: float = 0.0
    delayed_workload_kloc: float = 0.0


class RequirementDeliveryDelayRankingBucketSchema(Schema):
    development: List[RequirementDeliveryDelayRankingItemSchema] = Field(
        default_factory=list
    )
    acceptance: List[RequirementDeliveryDelayRankingItemSchema] = Field(
        default_factory=list
    )


class RequirementDeliveryDelayRankingSummarySchema(Schema):
    pl_group: RequirementDeliveryDelayRankingBucketSchema = Field(
        default_factory=lambda: RequirementDeliveryDelayRankingBucketSchema()
    )
    project: RequirementDeliveryDelayRankingBucketSchema = Field(
        default_factory=lambda: RequirementDeliveryDelayRankingBucketSchema()
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
    pl_group_summary: List[RequirementPlGroupSummarySchema] = Field(default_factory=list)
    user_summary: RequirementUserSummarySchema = Field(
        default_factory=lambda: RequirementUserSummarySchema()
    )
    dispatch_rate: RequirementDispatchRateSchema = Field(
        default_factory=lambda: RequirementDispatchRateSchema()
    )
    plan_refresh_rate: RequirementPlanRefreshRateSchema = Field(
        default_factory=lambda: RequirementPlanRefreshRateSchema()
    )
    delay_summary: RequirementDelaySummarySchema = Field(
        default_factory=lambda: RequirementDelaySummarySchema()
    )
    delivery_delay_rankings: RequirementDeliveryDelayRankingSummarySchema = Field(
        default_factory=lambda: RequirementDeliveryDelayRankingSummarySchema()
    )
    development_delivery_trend: List[RequirementDeliveryTrendItemSchema] = Field(
        default_factory=list
    )
    acceptance_delivery_trend: List[RequirementDeliveryTrendItemSchema] = Field(
        default_factory=list
    )
