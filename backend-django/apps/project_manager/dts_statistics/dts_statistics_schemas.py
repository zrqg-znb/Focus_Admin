from typing import Any, Optional

from ninja import Field, Schema
from pydantic import field_validator


class DtsStatisticsQuerySchema(Schema):
    project_ids: list[str] = Field(default_factory=list)
    column_type: str = Field("openDefects", description="openDefects/closeDefects/totalDefects")
    start_time: str
    end_time: str
    page_no: int = 1
    page_size: int = 20

    @field_validator("project_ids", mode="before")
    @classmethod
    def normalize_project_ids(cls, value: Any):
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

    @field_validator("column_type")
    @classmethod
    def validate_column_type(cls, value: str):
        value = (value or "").strip() or "openDefects"
        allowed = {"openDefects", "closeDefects", "totalDefects"}
        if value not in allowed:
            raise ValueError("column_type 不合法")
        return value

    @field_validator("page_no")
    @classmethod
    def validate_page_no(cls, value: int):
        return max(int(value or 1), 1)

    @field_validator("page_size")
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
    dev_non_base_desc: Optional[str] = None
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
        "dev_non_base_desc",
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


class DtsMergedDefectSchema(DataLakeDefectSchema):
    project_ids: list[str] = Field(default_factory=list)
    project_names: list[str] = Field(default_factory=list)
    team_names: list[str] = Field(default_factory=list)

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
    dev_non_base_desc: Optional[str] = None
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
    qa_category_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    dev_sub_category_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    test_miss_reason_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    pl_group_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    project_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
    action_status_dist: list[DtsDistributionItemSchema] = Field(default_factory=list)
