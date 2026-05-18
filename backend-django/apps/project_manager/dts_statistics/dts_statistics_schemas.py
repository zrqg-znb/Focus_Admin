from typing import Any, Literal, Optional

from ninja import Field, Schema
from pydantic import field_validator


def _normalize_text_list(value: Any, default: list[str] | None = None) -> list[str]:
    if value is None:
        return list(default or [])
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


def _normalize_timestamp(value: Any) -> int:
    try:
        parsed = int(value or 0)
    except Exception:
        parsed = 0
    return max(parsed, 0)


def _normalize_optional_text(value: Any) -> str:
    return str(value or "").strip()


class DtsLocalFilterSchema(Schema):
    dtsBizNoKeyword: str = ""
    parentNoKeyword: str = ""
    projectNames: list[str] = Field(default_factory=list)
    briefDescKeyword: str = ""
    iTestBackCountKeyword: str = ""
    iNumOfCloseDaysKeyword: str = ""
    iNumOfFirmDaysKeyword: str = ""
    iNumOfLocateDaysKeyword: str = ""
    iNumofModifyDaysKeyword: str = ""
    iNumofTestDaysKeyword: str = ""
    currentHandlerKeywords: list[str] = Field(default_factory=list)
    creatorKeywords: list[str] = Field(default_factory=list)
    sSubmitUserNameKeywords: list[str] = Field(default_factory=list)
    last_dts009_handlerKeywords: list[str] = Field(default_factory=list)
    last_dts010_handlerKeywords: list[str] = Field(default_factory=list)
    last_dts013_handlerKeywords: list[str] = Field(default_factory=list)
    createAtBegin: int = 0
    createAtEnd: int = 0
    dCloseTimeBegin: int = 0
    dCloseTimeEnd: int = 0
    sDeptOneNoNames: list[str] = Field(default_factory=list)
    sSubsystemNoNames: list[str] = Field(default_factory=list)
    sConfigFlowTypes: list[str] = Field(default_factory=list)
    auto_source_types: list[str] = Field(default_factory=list)
    auto_pl_group_names: list[str] = Field(default_factory=list)
    uQbiCloseTypeNames: list[str] = Field(default_factory=list)
    is_downstream_values: list[str] = Field(default_factory=list)
    need_aar_values: list[str] = Field(default_factory=list)
    need_dev_analyze_values: list[str] = Field(default_factory=list)
    need_test_analyze_values: list[str] = Field(default_factory=list)
    process_quality_type_keyword: str = ""
    qa_remark_keyword: str = ""
    dev_owner_name_keyword: list[str] = Field(default_factory=list)
    issue_intro_stage_values: list[str] = Field(default_factory=list)
    dev_feature_keyword: str = ""
    dev_sub_category_values: list[str] = Field(default_factory=list)
    dev_reason_keyword: str = ""
    dev_intro_reason_keyword: str = ""
    dev_issue_intro_point_values: list[str] = Field(default_factory=list)
    dev_issue_probability_values: list[str] = Field(default_factory=list)
    dev_common_issue_type_values: list[str] = Field(default_factory=list)
    is_base_soft_issue_values: list[str] = Field(default_factory=list)
    is_duplicate_issue_values: list[str] = Field(default_factory=list)
    duplicate_issue_no_keyword: str = ""
    dev_control_points_values: list[str] = Field(default_factory=list)
    dev_intro_point_analysis_keyword: str = ""
    dev_improvements_keyword: str = ""
    dev_non_base_desc_values: list[str] = Field(default_factory=list)
    dev_aar_link_keyword: str = ""
    dev_asset_link_keyword: str = ""
    dev_asset_type_values: list[str] = Field(default_factory=list)
    dev_status_values: list[str] = Field(default_factory=list)
    dev_remark_keyword: str = ""
    test_owner_name_keyword: list[str] = Field(default_factory=list)
    test_miss_reason_values: list[str] = Field(default_factory=list)
    test_standard_desc_keyword: str = ""
    test_improvements_keyword: str = ""
    test_non_test_desc_keyword: str = ""
    test_asset_link_keyword: str = ""
    test_status_values: list[str] = Field(default_factory=list)
    test_remark_keyword: str = ""

    @field_validator(
        "dtsBizNoKeyword",
        "parentNoKeyword",
        "briefDescKeyword",
        "iTestBackCountKeyword",
        "iNumOfCloseDaysKeyword",
        "iNumOfFirmDaysKeyword",
        "iNumOfLocateDaysKeyword",
        "iNumofModifyDaysKeyword",
        "iNumofTestDaysKeyword",
        "process_quality_type_keyword",
        "qa_remark_keyword",
        "dev_feature_keyword",
        "dev_reason_keyword",
        "dev_intro_reason_keyword",
        "dev_intro_point_analysis_keyword",
        "dev_improvements_keyword",
        "dev_aar_link_keyword",
        "dev_asset_link_keyword",
        "duplicate_issue_no_keyword",
        "dev_remark_keyword",
        "test_standard_desc_keyword",
        "test_improvements_keyword",
        "test_non_test_desc_keyword",
        "test_asset_link_keyword",
        "test_remark_keyword",
        mode="before",
    )
    @classmethod
    def normalize_local_keyword(cls, value: Any):
        return _normalize_optional_text(value)

    @field_validator(
        "createAtBegin",
        "createAtEnd",
        "dCloseTimeBegin",
        "dCloseTimeEnd",
        mode="before",
    )
    @classmethod
    def normalize_local_timestamp(cls, value: Any):
        return _normalize_timestamp(value)

    @field_validator(
        "projectNames",
        "currentHandlerKeywords",
        "creatorKeywords",
        "sSubmitUserNameKeywords",
        "last_dts009_handlerKeywords",
        "last_dts010_handlerKeywords",
        "last_dts013_handlerKeywords",
        "sDeptOneNoNames",
        "sSubsystemNoNames",
        "sConfigFlowTypes",
        "auto_source_types",
        "auto_pl_group_names",
        "uQbiCloseTypeNames",
        "is_downstream_values",
        "need_aar_values",
        "need_dev_analyze_values",
        "need_test_analyze_values",
        "issue_intro_stage_values",
        "dev_sub_category_values",
        "dev_issue_intro_point_values",
        "dev_issue_probability_values",
        "dev_common_issue_type_values",
        "dev_control_points_values",
        "dev_non_base_desc_values",
        "dev_asset_type_values",
        "dev_status_values",
        "dev_owner_name_keyword",
        "test_miss_reason_values",
        "test_status_values",
        "test_owner_name_keyword",
        mode="before",
    )
    @classmethod
    def normalize_local_text_list(cls, value: Any):
        return _normalize_text_list(value)


class DtsStatisticsQuerySchema(Schema):
    productId: str = "250539396"
    flowStates: list[str] = Field(default_factory=lambda: ["FS99"])
    severityNos: list[str] = Field(default_factory=list)
    updateTimeBegin: int = 0
    updateTimeEnd: int = 0
    dtsBizNoKeyword: str = ""
    parentNoKeyword: str = ""
    projectNames: list[str] = Field(default_factory=list)
    briefDescKeyword: str = ""
    iTestBackCountKeyword: str = ""
    iNumOfCloseDaysKeyword: str = ""
    iNumOfFirmDaysKeyword: str = ""
    iNumOfLocateDaysKeyword: str = ""
    iNumofModifyDaysKeyword: str = ""
    iNumofTestDaysKeyword: str = ""
    currentHandlerKeywords: list[str] = Field(default_factory=list)
    creatorKeywords: list[str] = Field(default_factory=list)
    sSubmitUserNameKeywords: list[str] = Field(default_factory=list)
    last_dts009_handlerKeywords: list[str] = Field(default_factory=list)
    last_dts010_handlerKeywords: list[str] = Field(default_factory=list)
    last_dts013_handlerKeywords: list[str] = Field(default_factory=list)
    createAtBegin: int = 0
    createAtEnd: int = 0
    dCloseTimeBegin: int = 0
    dCloseTimeEnd: int = 0
    sDeptOneNoNames: list[str] = Field(default_factory=list)
    sSubsystemNoNames: list[str] = Field(default_factory=list)
    sConfigFlowTypes: list[str] = Field(default_factory=list)
    auto_source_types: list[str] = Field(default_factory=list)
    auto_pl_group_names: list[str] = Field(default_factory=list)
    uQbiCloseTypeNames: list[str] = Field(default_factory=list)
    is_downstream_values: list[str] = Field(default_factory=list)
    need_aar_values: list[str] = Field(default_factory=list)
    need_dev_analyze_values: list[str] = Field(default_factory=list)
    need_test_analyze_values: list[str] = Field(default_factory=list)
    process_quality_type_keyword: str = ""
    qa_remark_keyword: str = ""
    dev_owner_name_keyword: list[str] = Field(default_factory=list)
    issue_intro_stage_values: list[str] = Field(default_factory=list)
    dev_feature_keyword: str = ""
    dev_sub_category_values: list[str] = Field(default_factory=list)
    dev_reason_keyword: str = ""
    dev_intro_reason_keyword: str = ""
    dev_issue_intro_point_values: list[str] = Field(default_factory=list)
    dev_issue_probability_values: list[str] = Field(default_factory=list)
    dev_common_issue_type_values: list[str] = Field(default_factory=list)
    is_base_soft_issue_values: list[str] = Field(default_factory=list)
    is_duplicate_issue_values: list[str] = Field(default_factory=list)
    duplicate_issue_no_keyword: str = ""
    dev_control_points_values: list[str] = Field(default_factory=list)
    dev_intro_point_analysis_keyword: str = ""
    dev_improvements_keyword: str = ""
    dev_non_base_desc_values: list[str] = Field(default_factory=list)
    dev_aar_link_keyword: str = ""
    dev_asset_link_keyword: str = ""
    dev_asset_type_values: list[str] = Field(default_factory=list)
    dev_status_values: list[str] = Field(default_factory=list)
    dev_remark_keyword: str = ""
    test_owner_name_keyword: list[str] = Field(default_factory=list)
    test_miss_reason_values: list[str] = Field(default_factory=list)
    test_standard_desc_keyword: str = ""
    test_improvements_keyword: str = ""
    test_non_test_desc_keyword: str = ""
    test_asset_link_keyword: str = ""
    test_status_values: list[str] = Field(default_factory=list)
    test_remark_keyword: str = ""
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
        return _normalize_text_list(value, default=["FS99"])

    @field_validator("severityNos", mode="before")
    @classmethod
    def normalize_severity_nos(cls, value: Any):
        return _normalize_text_list(value)

    @field_validator(
        "dtsBizNoKeyword",
        "parentNoKeyword",
        "briefDescKeyword",
        "iTestBackCountKeyword",
        "iNumOfCloseDaysKeyword",
        "iNumOfFirmDaysKeyword",
        "iNumOfLocateDaysKeyword",
        "iNumofModifyDaysKeyword",
        "iNumofTestDaysKeyword",
        "process_quality_type_keyword",
        "qa_remark_keyword",
        "dev_feature_keyword",
        "dev_reason_keyword",
        "dev_intro_reason_keyword",
        "dev_intro_point_analysis_keyword",
        "dev_improvements_keyword",
        "dev_aar_link_keyword",
        "dev_asset_link_keyword",
        "duplicate_issue_no_keyword",
        "dev_remark_keyword",
        "test_standard_desc_keyword",
        "test_improvements_keyword",
        "test_non_test_desc_keyword",
        "test_asset_link_keyword",
        "test_remark_keyword",
        mode="before",
    )
    @classmethod
    def normalize_keyword(cls, value: Any):
        return _normalize_optional_text(value)

    @field_validator(
        "projectNames",
        "currentHandlerKeywords",
        "creatorKeywords",
        "sSubmitUserNameKeywords",
        "last_dts009_handlerKeywords",
        "last_dts010_handlerKeywords",
        "last_dts013_handlerKeywords",
        "dev_owner_name_keyword",
        "test_owner_name_keyword",
        mode="before",
    )
    @classmethod
    def normalize_keyword_list(cls, value: Any):
        return _normalize_text_list(value)

    @field_validator(
        "updateTimeBegin",
        "updateTimeEnd",
        "createAtBegin",
        "createAtEnd",
        "dCloseTimeBegin",
        "dCloseTimeEnd",
        mode="before",
    )
    @classmethod
    def normalize_timestamp(cls, value: Any):
        return _normalize_timestamp(value)

    @field_validator(
        "sDeptOneNoNames",
        "sSubsystemNoNames",
        "sConfigFlowTypes",
        "auto_source_types",
        "auto_pl_group_names",
        "uQbiCloseTypeNames",
        "is_downstream_values",
        "need_aar_values",
        "need_dev_analyze_values",
        "need_test_analyze_values",
        "issue_intro_stage_values",
        "dev_sub_category_values",
        "dev_issue_intro_point_values",
        "dev_issue_probability_values",
        "dev_common_issue_type_values",
        "is_base_soft_issue_values",
        "is_duplicate_issue_values",
        "dev_control_points_values",
        "dev_non_base_desc_values",
        "dev_asset_type_values",
        "dev_status_values",
        "test_miss_reason_values",
        "test_status_values",
        mode="before",
    )
    @classmethod
    def normalize_local_filter_list(cls, value: Any):
        return _normalize_text_list(value)

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
    is_downstream: Optional[str] = None
    process_quality_type: Optional[str] = None
    need_aar: Optional[str] = None
    need_dev_analyze: Optional[str] = None
    need_test_analyze: Optional[str] = None
    dev_owner_id: Optional[str] = None
    test_owner_id: Optional[str] = None
    qa_remark: Optional[str] = None

    issue_intro_stage: Optional[str] = None
    dev_sub_category: list[str] = Field(default_factory=list)
    dev_feature: Optional[str] = None
    dev_reason: Optional[str] = None
    dev_intro_reason: Optional[str] = None
    dev_issue_intro_point: Optional[str] = None
    dev_issue_probability: Optional[str] = None
    dev_common_issue_type: Optional[str] = None
    is_base_soft_issue: Optional[str] = None
    is_duplicate_issue: Optional[str] = None
    duplicate_issue_no: Optional[str] = None
    dev_control_points: list[str] = Field(default_factory=list)
    dev_intro_point_analysis: Optional[str] = None
    dev_improvements: list[str] = Field(default_factory=list)
    dev_non_base_desc: list[str] = Field(default_factory=list)
    dev_aar_link: Optional[str] = None
    dev_asset_link: Optional[str] = None
    dev_asset_type: list[str] = Field(default_factory=list)
    dev_status: Optional[str] = None
    dev_remark: Optional[str] = None

    test_miss_reason: list[str] = Field(default_factory=list)
    test_standard_desc: Optional[str] = None
    test_improvements: list[str] = Field(default_factory=list)
    test_non_test_desc: Optional[str] = None
    test_asset_link: Optional[str] = None
    test_status: Optional[str] = None
    test_remark: Optional[str] = None

    @field_validator(
        "dev_sub_category",
        "dev_control_points",
        "dev_non_base_desc",
        "dev_improvements",
        "dev_asset_type",
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
        "is_downstream",
        "process_quality_type",
        "issue_intro_stage",
        "need_aar",
        "need_dev_analyze",
        "need_test_analyze",
        "dev_owner_id",
        "test_owner_id",
        "qa_remark",
        "dev_feature",
        "dev_reason",
        "dev_intro_reason",
        "dev_issue_intro_point",
        "dev_issue_probability",
        "dev_common_issue_type",
        "is_base_soft_issue",
        "is_duplicate_issue",
        "duplicate_issue_no",
        "dev_intro_point_analysis",
        "dev_aar_link",
        "dev_asset_link",
        "dev_status",
        "dev_remark",
        "test_standard_desc",
        "test_non_test_desc",
        "test_asset_link",
        "test_status",
        "test_remark",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: Any):
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class DtsBatchExtensionDataSchema(Schema):
    is_downstream: Optional[str] = None
    process_quality_type: Optional[str] = None
    need_aar: Optional[str] = None
    need_dev_analyze: Optional[str] = None
    need_test_analyze: Optional[str] = None
    dev_owner_id: Optional[str] = None
    test_owner_id: Optional[str] = None
    qa_remark: Optional[str] = None

    issue_intro_stage: Optional[str] = None
    dev_sub_category: Optional[list[str]] = None
    dev_feature: Optional[str] = None
    dev_reason: Optional[str] = None
    dev_intro_reason: Optional[str] = None
    dev_issue_intro_point: Optional[str] = None
    dev_issue_probability: Optional[str] = None
    dev_common_issue_type: Optional[str] = None
    is_base_soft_issue: Optional[str] = None
    is_duplicate_issue: Optional[str] = None
    duplicate_issue_no: Optional[str] = None
    dev_control_points: Optional[list[str]] = None
    dev_intro_point_analysis: Optional[str] = None
    dev_improvements: Optional[list[str]] = None
    dev_non_base_desc: Optional[list[str]] = None
    dev_aar_link: Optional[str] = None
    dev_asset_link: Optional[str] = None
    dev_asset_type: Optional[list[str]] = None
    dev_status: Optional[str] = None
    dev_remark: Optional[str] = None

    test_miss_reason: Optional[list[str]] = None
    test_standard_desc: Optional[str] = None
    test_improvements: Optional[list[str]] = None
    test_non_test_desc: Optional[str] = None
    test_asset_link: Optional[str] = None
    test_status: Optional[str] = None
    test_remark: Optional[str] = None

    @field_validator(
        "dev_sub_category",
        "dev_control_points",
        "dev_non_base_desc",
        "dev_improvements",
        "dev_asset_type",
        "test_miss_reason",
        "test_improvements",
        mode="before",
    )
    @classmethod
    def normalize_optional_string_list(cls, value: Any):
        if value is None:
            return None
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
        "is_downstream",
        "process_quality_type",
        "issue_intro_stage",
        "need_aar",
        "need_dev_analyze",
        "need_test_analyze",
        "dev_owner_id",
        "test_owner_id",
        "qa_remark",
        "dev_feature",
        "dev_reason",
        "dev_intro_reason",
        "dev_issue_intro_point",
        "dev_issue_probability",
        "dev_common_issue_type",
        "is_base_soft_issue",
        "is_duplicate_issue",
        "duplicate_issue_no",
        "dev_intro_point_analysis",
        "dev_aar_link",
        "dev_asset_link",
        "dev_status",
        "dev_remark",
        "test_standard_desc",
        "test_non_test_desc",
        "test_asset_link",
        "test_status",
        "test_remark",
        mode="before",
    )
    @classmethod
    def normalize_batch_optional_text(cls, value: Any):
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class DtsBatchExtensionSaveSchema(Schema):
    defectNos: list[str] = Field(default_factory=list)
    fieldMask: list[str] = Field(default_factory=list)
    data: DtsBatchExtensionDataSchema = Field(
        default_factory=DtsBatchExtensionDataSchema
    )

    @field_validator("defectNos", "fieldMask", mode="before")
    @classmethod
    def normalize_batch_text_list(cls, value: Any):
        return _normalize_text_list(value)


class DataLakeDefectSchema(Schema):
    dtsBizNo: str
    briefDesc: Optional[str] = None
    dtsStatusName: Optional[str] = None
    serverityNoName: Optional[str] = None
    updateAt: Optional[str] = None
    parentNo: Optional[str] = None
    createAt: Optional[str] = None
    dCloseTime: Optional[str] = None
    sDeptOneNoName: Optional[str] = None
    currentHandler: Optional[str] = None
    creator: Optional[str] = None
    sSubmitUserName: Optional[str] = None
    sSubsystemNoName: Optional[str] = None
    sConfigFlowType: Optional[str] = None
    uQbiCloseTypeName: Optional[str] = None
    sProdCName: Optional[str] = None
    sProdFamilyNoName: Optional[str] = None
    sProdXtdNoName: Optional[str] = None
    iTestBackCount: Optional[str] = None
    sSuggestByReviewer: Optional[str] = None
    sTestReport: Optional[str] = None
    sTestSuggest: Optional[str] = None
    sModifyDocument: Optional[str] = None
    sTestorTestReport: Optional[str] = None
    last_dts009_handler: Optional[str] = None
    last_dts010_handler: Optional[str] = None
    last_dts013_handler: Optional[str] = None
    iNumOfCloseDays: Optional[str] = None
    iNumOfFirmDays: Optional[str] = None
    iNumOfLocateDays: Optional[str] = None
    iNumofModifyDays: Optional[str] = None
    iNumofTestDays: Optional[str] = None
    dts009ReasonAnalysis: Optional[str] = None
    dts004ReasonAnalysis: Optional[str] = None
    dts009ReasonAnalyses: Optional[str] = None
    sAchieveDescibe: Optional[str] = None

    # Helper fields used by cache/signature and summary/export rendering.
    serverityNo: Optional[str] = None
    productId: Optional[str] = None
    productName: Optional[str] = None
    projectName: Optional[str] = None
    auto_source_type: Optional[str] = None
    auto_pl_group_id: Optional[str] = None
    auto_pl_group_name: Optional[str] = None


class DtsMergedDefectSchema(DataLakeDefectSchema):
    is_downstream: Optional[str] = None
    process_quality_type: Optional[str] = None
    need_aar: Optional[str] = None
    need_dev_analyze: Optional[str] = None
    need_test_analyze: Optional[str] = None
    dev_owner_id: Optional[str] = None
    dev_owner_name: Optional[str] = None
    test_owner_id: Optional[str] = None
    test_owner_name: Optional[str] = None
    qa_remark: Optional[str] = None

    issue_intro_stage: Optional[str] = None
    dev_sub_category: list[str] = Field(default_factory=list)
    dev_feature: Optional[str] = None
    dev_reason: Optional[str] = None
    dev_intro_reason: Optional[str] = None
    dev_issue_intro_point: Optional[str] = None
    dev_issue_probability: Optional[str] = None
    dev_common_issue_type: Optional[str] = None
    is_base_soft_issue: Optional[str] = None
    is_duplicate_issue: Optional[str] = None
    duplicate_issue_no: Optional[str] = None
    dev_control_points: list[str] = Field(default_factory=list)
    dev_intro_point_analysis: Optional[str] = None
    dev_improvements: list[str] = Field(default_factory=list)
    dev_non_base_desc: list[str] = Field(default_factory=list)
    dev_aar_link: Optional[str] = None
    dev_asset_link: Optional[str] = None
    dev_status: Optional[str] = None
    dev_remark: Optional[str] = None

    test_miss_reason: list[str] = Field(default_factory=list)
    test_standard_desc: Optional[str] = None
    test_improvements: list[str] = Field(default_factory=list)
    test_non_test_desc: Optional[str] = None
    test_asset_link: Optional[str] = None
    test_status: Optional[str] = None
    test_remark: Optional[str] = None


class DtsSnapshotMetaSchema(Schema):
    productId: str = ""
    productName: str = ""
    version: str = ""
    generatedAt: Optional[str] = None
    windowBegin: int = 0
    windowEnd: int = 0
    rowCount: int = 0
    isStale: bool = False


class DtsListResponseSchema(Schema):
    total: int
    items: list[DtsMergedDefectSchema]
    snapshot: Optional[DtsSnapshotMetaSchema] = None


class DtsSaveResponseSchema(Schema):
    success: bool


class DtsBatchSaveFailedItemSchema(Schema):
    defectNo: str
    errorMessage: str


class DtsBatchSaveResponseSchema(Schema):
    successCount: int = 0
    failedCount: int = 0
    failedItems: list[DtsBatchSaveFailedItemSchema] = Field(default_factory=list)


class DtsDistributionItemSchema(Schema):
    label: str
    value: int


class DtsPlGroupCompletionItemSchema(Schema):
    label: str
    filled_count: int
    total_count: int
    filled_rate: float


class DtsTrendSummarySchema(Schema):
    granularity: Literal["day", "week"]
    labels: list[str] = Field(default_factory=list)
    total_values: list[int] = Field(default_factory=list)
    closed_values: list[int] = Field(default_factory=list)
    major_values: list[int] = Field(default_factory=list)
    critical_values: list[int] = Field(default_factory=list)


class DtsHeatmapRowSchema(Schema):
    label: str
    values: list[int] = Field(default_factory=list)


class DtsHeatmapMatrixSchema(Schema):
    columns: list[str] = Field(default_factory=list)
    rows: list[DtsHeatmapRowSchema] = Field(default_factory=list)


class DtsSummarySchema(Schema):
    total_count: int
    open_count: int
    closed_count: int
    avg_process_days: float

    qa_filled_count: int
    qa_completion_rate: float
    dev_filled_count: int
    dev_completion_rate: float
    test_filled_count: int
    test_completion_rate: float
    low_level_count: int
    low_level_rate: float

    severity_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    status_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    flow_type_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    team_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    close_type_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    source_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    auto_pl_group_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    pl_group_dev_completion_dist: list[DtsPlGroupCompletionItemSchema] = Field(
        default_factory=list
    )
    handler_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    process_days_bucket_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    issue_intro_stage_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    dev_action_status_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    test_action_status_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    dev_sub_category_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    test_miss_reason_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    project_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    action_status_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    update_trend: Optional[DtsTrendSummarySchema] = None
    pl_group_severity_matrix: Optional[DtsHeatmapMatrixSchema] = None
    snapshot: Optional[DtsSnapshotMetaSchema] = None


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
    dtsBizNoKeyword: str = ""
    parentNoKeyword: str = ""
    projectNames: list[str] = Field(default_factory=list)
    briefDescKeyword: str = ""
    iTestBackCountKeyword: str = ""
    iNumOfCloseDaysKeyword: str = ""
    iNumOfFirmDaysKeyword: str = ""
    iNumOfLocateDaysKeyword: str = ""
    iNumofModifyDaysKeyword: str = ""
    iNumofTestDaysKeyword: str = ""
    currentHandlerKeywords: list[str] = Field(default_factory=list)
    creatorKeywords: list[str] = Field(default_factory=list)
    sSubmitUserNameKeywords: list[str] = Field(default_factory=list)
    last_dts009_handlerKeywords: list[str] = Field(default_factory=list)
    last_dts010_handlerKeywords: list[str] = Field(default_factory=list)
    last_dts013_handlerKeywords: list[str] = Field(default_factory=list)
    createAtBegin: int = 0
    createAtEnd: int = 0
    dCloseTimeBegin: int = 0
    dCloseTimeEnd: int = 0
    sDeptOneNoNames: list[str] = Field(default_factory=list)
    sSubsystemNoNames: list[str] = Field(default_factory=list)
    sConfigFlowTypes: list[str] = Field(default_factory=list)
    auto_source_types: list[str] = Field(default_factory=list)
    auto_pl_group_names: list[str] = Field(default_factory=list)
    uQbiCloseTypeNames: list[str] = Field(default_factory=list)
    is_downstream_values: list[str] = Field(default_factory=list)
    need_aar_values: list[str] = Field(default_factory=list)
    need_dev_analyze_values: list[str] = Field(default_factory=list)
    need_test_analyze_values: list[str] = Field(default_factory=list)
    process_quality_type_keyword: str = ""
    qa_remark_keyword: str = ""
    dev_owner_name_keyword: list[str] = Field(default_factory=list)
    issue_intro_stage_values: list[str] = Field(default_factory=list)
    dev_feature_keyword: str = ""
    dev_sub_category_values: list[str] = Field(default_factory=list)
    dev_reason_keyword: str = ""
    dev_intro_reason_keyword: str = ""
    dev_issue_intro_point_values: list[str] = Field(default_factory=list)
    dev_issue_probability_values: list[str] = Field(default_factory=list)
    dev_common_issue_type_values: list[str] = Field(default_factory=list)
    is_base_soft_issue_values: list[str] = Field(default_factory=list)
    is_duplicate_issue_values: list[str] = Field(default_factory=list)
    duplicate_issue_no_keyword: str = ""
    dev_control_points_values: list[str] = Field(default_factory=list)
    dev_intro_point_analysis_keyword: str = ""
    dev_improvements_keyword: str = ""
    dev_non_base_desc_values: list[str] = Field(default_factory=list)
    dev_aar_link_keyword: str = ""
    dev_asset_link_keyword: str = ""
    dev_asset_type_values: list[str] = Field(default_factory=list)
    dev_status_values: list[str] = Field(default_factory=list)
    dev_remark_keyword: str = ""
    test_owner_name_keyword: list[str] = Field(default_factory=list)
    test_miss_reason_values: list[str] = Field(default_factory=list)
    test_standard_desc_keyword: str = ""
    test_improvements_keyword: str = ""
    test_non_test_desc_keyword: str = ""
    test_asset_link_keyword: str = ""
    test_status_values: list[str] = Field(default_factory=list)
    test_remark_keyword: str = ""

    @field_validator("productId", mode="before")
    @classmethod
    def normalize_product_id(cls, value: Any):
        text = str(value or "").strip()
        return text or "250539396"

    @field_validator("flowStates", mode="before")
    @classmethod
    def normalize_flow_states(cls, value: Any):
        return _normalize_text_list(value, default=["FS99"])

    @field_validator("severityNos", mode="before")
    @classmethod
    def normalize_severity_nos(cls, value: Any):
        return _normalize_text_list(value)

    @field_validator(
        "dtsBizNoKeyword",
        "parentNoKeyword",
        "briefDescKeyword",
        "iTestBackCountKeyword",
        "iNumOfCloseDaysKeyword",
        "iNumOfFirmDaysKeyword",
        "iNumOfLocateDaysKeyword",
        "iNumofModifyDaysKeyword",
        "iNumofTestDaysKeyword",
        "process_quality_type_keyword",
        "qa_remark_keyword",
        "dev_feature_keyword",
        "dev_reason_keyword",
        "dev_intro_reason_keyword",
        "dev_intro_point_analysis_keyword",
        "dev_improvements_keyword",
        "dev_aar_link_keyword",
        "dev_asset_link_keyword",
        "duplicate_issue_no_keyword",
        "dev_remark_keyword",
        "test_standard_desc_keyword",
        "test_improvements_keyword",
        "test_non_test_desc_keyword",
        "test_asset_link_keyword",
        "test_remark_keyword",
        mode="before",
    )
    @classmethod
    def normalize_keyword(cls, value: Any):
        return _normalize_optional_text(value)

    @field_validator(
        "projectNames",
        "currentHandlerKeywords",
        "creatorKeywords",
        "sSubmitUserNameKeywords",
        "last_dts009_handlerKeywords",
        "last_dts010_handlerKeywords",
        "last_dts013_handlerKeywords",
        "dev_owner_name_keyword",
        "test_owner_name_keyword",
        mode="before",
    )
    @classmethod
    def normalize_export_keyword_list(cls, value: Any):
        return _normalize_text_list(value)

    @field_validator(
        "updateTimeBegin",
        "updateTimeEnd",
        "createAtBegin",
        "createAtEnd",
        "dCloseTimeBegin",
        "dCloseTimeEnd",
        mode="before",
    )
    @classmethod
    def normalize_timestamp(cls, value: Any):
        return _normalize_timestamp(value)

    @field_validator(
        "sDeptOneNoNames",
        "sSubsystemNoNames",
        "sConfigFlowTypes",
        "auto_source_types",
        "auto_pl_group_names",
        "uQbiCloseTypeNames",
        "is_downstream_values",
        "need_aar_values",
        "need_dev_analyze_values",
        "need_test_analyze_values",
        "issue_intro_stage_values",
        "dev_sub_category_values",
        "dev_issue_intro_point_values",
        "dev_issue_probability_values",
        "dev_common_issue_type_values",
        "is_base_soft_issue_values",
        "is_duplicate_issue_values",
        "dev_control_points_values",
        "dev_non_base_desc_values",
        "dev_asset_type_values",
        "dev_status_values",
        "test_miss_reason_values",
        "test_status_values",
        mode="before",
    )
    @classmethod
    def normalize_local_filter_list(cls, value: Any):
        return _normalize_text_list(value)


class DtsFieldSetRequestSchema(DtsStatisticsExportSchema):
    fields: list[str] = Field(default_factory=list)

    @field_validator("fields", mode="before")
    @classmethod
    def normalize_fields(cls, value: Any):
        return _normalize_text_list(value)


class DtsFieldSetResponseSchema(Schema):
    fieldSets: dict[str, list[str]] = Field(default_factory=dict)


class DtsQueryTaskSchema(Schema):
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


class DtsQueryPrepareResponseSchema(Schema):
    mode: str
    task: Optional[DtsQueryTaskSchema] = None


class DtsExportTaskSchema(Schema):
    id: str
    fingerprint: str = ""
    status: str = ""
    message: str = ""
    error_message: str = ""
    progress: int = 0
    file_name: Optional[str] = None
    file_size: int = 0
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class DtsExportPrepareResponseSchema(Schema):
    mode: str
    task: Optional[DtsExportTaskSchema] = None


class DtsDictOptionSchema(Schema):
    label: str
    value: str


class DtsDictOptionsSchema(Schema):
    """
    DTS 模块字典选项聚合接口返回结构。

    说明：为减少前端多次请求，将 DTS 统计页/填报 Drawer 所需字典一次性打包返回。
    """

    yes_no: list[DtsDictOptionSchema] = Field(default_factory=list)
    issue_intro_stage: list[DtsDictOptionSchema] = Field(default_factory=list)
    dev_sub_category: list[DtsDictOptionSchema] = Field(default_factory=list)
    dev_issue_intro_point: list[DtsDictOptionSchema] = Field(default_factory=list)
    dev_issue_probability: list[DtsDictOptionSchema] = Field(default_factory=list)
    dev_common_issue_type: list[DtsDictOptionSchema] = Field(default_factory=list)
    dev_control_points: list[DtsDictOptionSchema] = Field(default_factory=list)
    dev_non_base_desc: list[DtsDictOptionSchema] = Field(default_factory=list)
    dev_asset_type: list[DtsDictOptionSchema] = Field(default_factory=list)
    test_miss_reason: list[DtsDictOptionSchema] = Field(default_factory=list)
    action_status: list[DtsDictOptionSchema] = Field(default_factory=list)
