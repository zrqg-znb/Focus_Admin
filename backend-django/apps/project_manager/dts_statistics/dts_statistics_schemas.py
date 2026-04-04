from typing import Any, Optional

from ninja import Field, Schema
from pydantic import field_validator


class DtsStatisticsQuerySchema(Schema):
    productId: str = "250539396"
    flowStates: list[str] = Field(default_factory=lambda: ["FS99"])
    severityNos: list[str] = Field(default_factory=list)
    updateTimeBegin: int = 0
    updateTimeEnd: int = 0
    pageIndex: int = 1
    pageSize: int = 20

    @field_validator("productId", mode="before")
    @classmethod
    def normalize_product_id(cls, value: Any):
        text = str(value or "").strip()
        return text or "250539396"

    @field_validator("flowStates", mode="before")
    @classmethod
    def normalize_flow_states(cls, value: Any):
        if value is None:
            return ["FS99"]
        values = value if isinstance(value, list) else [value]
        normalized: list[str] = []
        seen: set[str] = set()
        for item in values:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        return normalized

    @field_validator("severityNos", mode="before")
    @classmethod
    def normalize_severity_nos(cls, value: Any):
        if value is None:
            return []
        values = value if isinstance(value, list) else [value]
        normalized: list[str] = []
        seen: set[str] = set()
        for item in values:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        return normalized

    @field_validator("updateTimeBegin", "updateTimeEnd", mode="before")
    @classmethod
    def normalize_timestamp(cls, value: Any):
        try:
            parsed = int(value or 0)
        except Exception:
            parsed = 0
        return max(parsed, 0)

    @field_validator("pageIndex")
    @classmethod
    def validate_page_index(cls, value: int):
        return max(int(value or 1), 1)

    @field_validator("pageSize")
    @classmethod
    def validate_page_size(cls, value: int):
        value = max(int(value or 20), 1)
        return min(value, 500)


class DtsExtensionSaveSchema(Schema):
    project_ids: list[str] = Field(default_factory=list)
    qa_category: Optional[str] = None
    pl_group_id: Optional[str] = None
    is_downstream: Optional[str] = None
    process_quality_type: Optional[str] = None
    need_dev_analyze: Optional[str] = None
    need_test_analyze: Optional[str] = None
    dev_owner_id: Optional[str] = None
    test_owner_id: Optional[str] = None
    is_dev_analyzed: Optional[str] = None
    is_test_analyzed: Optional[str] = None
    qa_remark: Optional[str] = None

    dev_sub_category: list[str] = Field(default_factory=list)
    dev_reason: Optional[str] = None
    dev_intro_reason: Optional[str] = None
    dev_improvements: list[str] = Field(default_factory=list)
    dev_non_base_desc: list[str] = Field(default_factory=list)
    dev_asset_link: Optional[str] = None
    dev_status: Optional[str] = None

    test_feature: Optional[str] = None
    test_miss_reason: list[str] = Field(default_factory=list)
    test_standard_desc: Optional[str] = None
    test_improvements: list[str] = Field(default_factory=list)
    test_non_test_desc: Optional[str] = None
    test_asset_link: Optional[str] = None
    test_status: Optional[str] = None

    @field_validator(
        "project_ids",
        "dev_sub_category",
        "dev_non_base_desc",
        "dev_improvements",
        "test_miss_reason",
        "test_improvements",
        mode="before",
    )
    @classmethod
    def normalize_string_list(cls, value: Any):
        if value is None:
            return []
        values = value if isinstance(value, list) else [value]
        normalized: list[str] = []
        seen: set[str] = set()
        for item in values:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        return normalized

    @field_validator(
        "qa_category",
        "pl_group_id",
        "is_downstream",
        "process_quality_type",
        "need_dev_analyze",
        "need_test_analyze",
        "dev_owner_id",
        "test_owner_id",
        "is_dev_analyzed",
        "is_test_analyzed",
        "qa_remark",
        "dev_reason",
        "dev_intro_reason",
        "dev_asset_link",
        "dev_status",
        "test_feature",
        "test_standard_desc",
        "test_non_test_desc",
        "test_asset_link",
        "test_status",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: Any):
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class DataLakeDefectSchema(Schema):
    defectNo: str
    brief: str = ""
    severity: str = ""
    weight: Optional[str] = None
    submitTime: Optional[str] = None
    submitterId: Optional[str] = None
    submitTeam: Optional[str] = None
    currentHandler: Optional[str] = None
    currentTeam: Optional[str] = None
    currentStatus: Optional[str] = None
    currentStage: Optional[str] = None
    closeType: Optional[str] = None
    process_days: Optional[str] = None

    # Data Lake raw fields (read-only baseline tab).
    dtsBizNo: Optional[str] = None
    briefDesc: Optional[str] = None
    dtsStatus: Optional[str] = None
    dtsStatusName: Optional[str] = None
    serverityNo: Optional[str] = None
    serverityNoName: Optional[str] = None
    parentNo: Optional[str] = None
    createAt: Optional[str] = None
    dCloseTime: Optional[str] = None
    sDeptOneNoName: Optional[str] = None
    flowState: Optional[str] = None
    creator: Optional[str] = None
    sSubmitUserName: Optional[str] = None
    sSubmitsystemNoName: Optional[str] = None
    sTestorTestReport: Optional[str] = None
    productId: Optional[str] = None
    productName: Optional[str] = None


class DtsMergedDefectSchema(DataLakeDefectSchema):
    project_ids: list[str] = Field(default_factory=list)
    project_names: list[str] = Field(default_factory=list)
    team_names: list[str] = Field(default_factory=list)
    project_name: Optional[str] = None
    team_name: Optional[str] = None

    qa_category: Optional[str] = None
    pl_group_id: Optional[str] = None
    pl_group_name: Optional[str] = None
    is_downstream: Optional[str] = None
    process_quality_type: Optional[str] = None
    need_dev_analyze: Optional[str] = None
    need_test_analyze: Optional[str] = None
    dev_owner_id: Optional[str] = None
    dev_owner_name: Optional[str] = None
    test_owner_id: Optional[str] = None
    test_owner_name: Optional[str] = None
    is_dev_analyzed: Optional[str] = None
    is_test_analyzed: Optional[str] = None
    qa_remark: Optional[str] = None

    dev_sub_category: list[str] = Field(default_factory=list)
    dev_reason: Optional[str] = None
    dev_intro_reason: Optional[str] = None
    dev_improvements: list[str] = Field(default_factory=list)
    dev_non_base_desc: list[str] = Field(default_factory=list)
    dev_asset_link: Optional[str] = None
    dev_status: Optional[str] = None

    test_feature: Optional[str] = None
    test_miss_reason: list[str] = Field(default_factory=list)
    test_standard_desc: Optional[str] = None
    test_improvements: list[str] = Field(default_factory=list)
    test_non_test_desc: Optional[str] = None
    test_asset_link: Optional[str] = None
    test_status: Optional[str] = None


class DtsListResponseSchema(Schema):
    total: int
    items: list[DtsMergedDefectSchema]


class DtsSaveResponseSchema(Schema):
    success: bool


class DtsDistributionItemSchema(Schema):
    label: str
    value: int


class DtsSummarySchema(Schema):
    total_count: int
    open_count: int
    closed_count: int
    avg_process_days: float

    qa_filled_count: int
    qa_completion_rate: float
    dev_analyzed_count: int
    dev_analysis_completion_rate: float
    test_analyzed_count: int
    test_analysis_completion_rate: float

    severity_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    status_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    team_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    stage_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    close_type_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    handler_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    qa_category_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    dev_sub_category_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    test_miss_reason_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    pl_group_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    project_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    action_status_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)


class DtsStatisticsExportSchema(Schema):
    """
    Export does not require paging fields. Keep it separated from list query schema
    to avoid accidental coupling on page_no/page_size on the frontend.
    """

    productId: str = "250539396"
    flowStates: list[str] = Field(default_factory=lambda: ["FS99"])
    severityNos: list[str] = Field(default_factory=list)
    updateTimeBegin: int = 0
    updateTimeEnd: int = 0

    @field_validator("productId", mode="before")
    @classmethod
    def normalize_product_id(cls, value: Any):
        text = str(value or "").strip()
        return text or "250539396"

    @field_validator("flowStates", mode="before")
    @classmethod
    def normalize_flow_states(cls, value: Any):
        if value is None:
            return ["FS99"]
        values = value if isinstance(value, list) else [value]
        normalized: list[str] = []
        seen: set[str] = set()
        for item in values:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        return normalized

    @field_validator("severityNos", mode="before")
    @classmethod
    def normalize_severity_nos(cls, value: Any):
        if value is None:
            return []
        values = value if isinstance(value, list) else [value]
        normalized: list[str] = []
        seen: set[str] = set()
        for item in values:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        return normalized

    @field_validator("updateTimeBegin", "updateTimeEnd", mode="before")
    @classmethod
    def normalize_timestamp(cls, value: Any):
        try:
            parsed = int(value or 0)
        except Exception:
            parsed = 0
        return max(parsed, 0)


class DtsDictOptionSchema(Schema):
    label: str
    value: str


class DtsDictOptionsSchema(Schema):
    """
    DTS 模块字典选项聚合接口返回结构。

    说明：为减少前端多次请求，将 DTS 统计页/填报 Drawer 所需字典一次性打包返回。
    """

    yes_no: list[DtsDictOptionSchema] = Field(default_factory=list)
    qa_category: list[DtsDictOptionSchema] = Field(default_factory=list)
    process_quality_type: list[DtsDictOptionSchema] = Field(default_factory=list)
    dev_sub_category: list[DtsDictOptionSchema] = Field(default_factory=list)
    dev_non_base_desc: list[DtsDictOptionSchema] = Field(default_factory=list)
    test_miss_reason: list[DtsDictOptionSchema] = Field(default_factory=list)
    action_status: list[DtsDictOptionSchema] = Field(default_factory=list)
