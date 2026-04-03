from typing import Any, Optional

from ninja import Field, Schema
from pydantic import field_validator


class UserBriefSchema(Schema):
    id: str
    username: str
    name: Optional[str] = None


class DictOptionSchema(Schema):
    label: str
    value: str


class RelationItemSchema(Schema):
    id: str
    label: str
    subtitle: Optional[str] = None


class FailureModeDictOptionsSchema(Schema):
    subsystem: list[DictOptionSchema] = Field(default_factory=list)
    module: list[DictOptionSchema] = Field(default_factory=list)
    chip: list[DictOptionSchema] = Field(default_factory=list)
    fault_category: list[DictOptionSchema] = Field(default_factory=list)
    symptom: list[DictOptionSchema] = Field(default_factory=list)
    functional_safety_level: list[DictOptionSchema] = Field(default_factory=list)
    occurrence_frequency: list[DictOptionSchema] = Field(default_factory=list)
    detectability: list[DictOptionSchema] = Field(default_factory=list)
    severity: list[DictOptionSchema] = Field(default_factory=list)
    status: list[DictOptionSchema] = Field(default_factory=list)
    measure_category: list[DictOptionSchema] = Field(default_factory=list)
    monitor_type: list[DictOptionSchema] = Field(default_factory=list)


class SearchPaginationSchema(Schema):
    page: int = Field(1, ge=1)
    pageSize: int = Field(10, gt=0)


class KeywordSearchSchema(SearchPaginationSchema):
    keyword: Optional[str] = Field(None, description='关键词')
    owner_keyword: Optional[str] = None

    @field_validator('keyword', 'owner_keyword', mode='before')
    @classmethod
    def normalize_keyword(cls, value: Any):
        if value is None:
            return None
        text = str(value).strip()
        return text or None


def _normalize_query_list(value: Any) -> list[str]:
    if value is None:
        return []

    raw_values = value if isinstance(value, list) else [value]
    normalized: list[str] = []
    seen: set[str] = set()

    for item in raw_values:
        pieces = item if isinstance(item, list) else [item]
        for piece in pieces:
            for part in str(piece or '').split(','):
                text = part.strip()
                if not text or text in seen:
                    continue
                seen.add(text)
                normalized.append(text)
    return normalized


class FailureModeSearchSchema(SearchPaginationSchema):
    keyword: Optional[str] = Field(None, description='关键词')
    subsystem: list[str] = Field(default_factory=list)
    module: list[str] = Field(default_factory=list)
    status: list[str] = Field(default_factory=list)
    author_id: Optional[str] = None
    author_keyword: Optional[str] = None

    @field_validator('keyword', 'author_id', 'author_keyword', mode='before')
    @classmethod
    def normalize_text_filters(cls, value: Any):
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator(
        'subsystem',
        'module',
        'status',
        mode='before',
    )
    @classmethod
    def normalize_dict_filter_values(cls, value: Any):
        return _normalize_query_list(value)


class HandlingMeasureSearchSchema(KeywordSearchSchema):
    measure_category: list[str] = Field(default_factory=list)

    @field_validator('measure_category', mode='before')
    @classmethod
    def normalize_measure_category(cls, value: Any):
        return _normalize_query_list(value)


class ObservationMethodSearchSchema(KeywordSearchSchema):
    monitor_type: list[str] = Field(default_factory=list)

    @field_validator('monitor_type', mode='before')
    @classmethod
    def normalize_monitor_type(cls, value: Any):
        return _normalize_query_list(value)


class ListTextSchemaMixin(Schema):
    @staticmethod
    def _normalize_string_list(value: Any) -> list[str]:
        if value is None:
            return []
        values = value if isinstance(value, list) else [value]
        normalized: list[str] = []
        seen: set[str] = set()
        for item in values:
            text = str(item or '').strip()
            if not text or text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        return normalized

    @staticmethod
    def _normalize_optional_text(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _normalize_html_text(value: Any) -> str:
        if value is None:
            return ''
        return str(value).strip()


class FailureModeCreateSchema(ListTextSchemaMixin):
    brief: str
    subsystem: Optional[str] = None
    module: Optional[str] = None
    chips: list[str] = Field(default_factory=list)
    fault_categories: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    effect_html: str = ''
    root_cause_html: str = ''
    functional_safety_level: Optional[str] = None
    occurrence_frequency: Optional[str] = None
    detectability: Optional[str] = None
    severity: Optional[str] = None
    author_ids: list[str] = Field(default_factory=list)
    related_dts_nos: list[str] = Field(default_factory=list)
    status: Optional[str] = None
    interception_required: bool = False
    huatuo_required: bool = False
    required_handling_measure_categories: list[str] = Field(default_factory=list)
    required_observation_method_types: list[str] = Field(default_factory=list)
    interception_strategy_ids: list[str] = Field(default_factory=list)
    handling_measure_ids: list[str] = Field(default_factory=list)
    observation_method_ids: list[str] = Field(default_factory=list)
    huatuo_diagnosis_ids: list[str] = Field(default_factory=list)

    @field_validator(
        'chips',
        'fault_categories',
        'symptoms',
        'author_ids',
        'related_dts_nos',
        'required_handling_measure_categories',
        'required_observation_method_types',
        'interception_strategy_ids',
        'handling_measure_ids',
        'observation_method_ids',
        'huatuo_diagnosis_ids',
        mode='before',
    )
    @classmethod
    def normalize_list_fields(cls, value: Any):
        return cls._normalize_string_list(value)

    @field_validator(
        'brief',
        'subsystem',
        'module',
        'functional_safety_level',
        'occurrence_frequency',
        'detectability',
        'severity',
        'status',
        mode='before',
    )
    @classmethod
    def normalize_text_fields(cls, value: Any):
        return cls._normalize_optional_text(value)

    @field_validator('effect_html', 'root_cause_html', mode='before')
    @classmethod
    def normalize_html_fields(cls, value: Any):
        return cls._normalize_html_text(value)


class FailureModeUpdateSchema(FailureModeCreateSchema):
    brief: Optional[str] = None
    effect_html: Optional[str] = None
    root_cause_html: Optional[str] = None
    interception_required: Optional[bool] = None
    huatuo_required: Optional[bool] = None

    @field_validator('effect_html', 'root_cause_html', mode='before')
    @classmethod
    def normalize_optional_html_fields(cls, value: Any):
        if value is None:
            return None
        return cls._normalize_html_text(value)


class FailureModeOutSchema(Schema):
    id: str
    brief: str
    subsystem: Optional[str] = None
    module: Optional[str] = None
    chips: list[str] = Field(default_factory=list)
    fault_categories: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    effect_html: str = ''
    root_cause_html: str = ''
    functional_safety_level: Optional[str] = None
    occurrence_frequency: Optional[str] = None
    detectability: Optional[str] = None
    severity: Optional[str] = None
    author_ids: list[str] = Field(default_factory=list)
    author_info: list[UserBriefSchema] = Field(default_factory=list)
    related_dts_nos: list[str] = Field(default_factory=list)
    status: Optional[str] = None
    source_type: str = 'manual'
    source_task_id: Optional[str] = None
    source_task_no: Optional[str] = None
    interception_required: bool = False
    huatuo_required: bool = False
    required_handling_measure_categories: list[str] = Field(default_factory=list)
    required_observation_method_types: list[str] = Field(default_factory=list)
    interception_strategy_ids: list[str] = Field(default_factory=list)
    interception_strategy_items: list[RelationItemSchema] = Field(default_factory=list)
    handling_measure_ids: list[str] = Field(default_factory=list)
    handling_measure_items: list[RelationItemSchema] = Field(default_factory=list)
    observation_method_ids: list[str] = Field(default_factory=list)
    observation_method_items: list[RelationItemSchema] = Field(default_factory=list)
    huatuo_diagnosis_ids: list[str] = Field(default_factory=list)
    huatuo_diagnosis_items: list[RelationItemSchema] = Field(default_factory=list)
    task_change_type: Optional[str] = None
    has_task_draft: bool = False
    editable_in_task: bool = False
    task_edit_mode: Optional[str] = None
    sys_create_datetime: Optional[str] = None
    sys_update_datetime: Optional[str] = None


class FailureModePageSchema(Schema):
    items: list[FailureModeOutSchema] = Field(default_factory=list)
    total: int


class FailureModeInsightProductRowSchema(Schema):
    product_id: str
    product_name: str
    owner_info: Optional[UserBriefSchema] = None
    subsystems: list[str] = Field(default_factory=list)
    landed_at: Optional[str] = None


class FailureModeInsightOutSchema(Schema):
    id: str
    brief: str
    subsystem: Optional[str] = None
    status: Optional[str] = None
    landed_product_count: int
    total_product_count: int
    product_rows: list[FailureModeInsightProductRowSchema] = Field(
        default_factory=list,
    )


class OwnerResourceCreateSchema(ListTextSchemaMixin):
    owner_ids: list[str] = Field(default_factory=list)

    @field_validator('owner_ids', mode='before')
    @classmethod
    def normalize_owner_ids(cls, value: Any):
        return cls._normalize_string_list(value)


class InterceptionStrategyCreateSchema(OwnerResourceCreateSchema):
    interception_item: str
    version_detection_html: str = ''
    station: Optional[str] = None

    @field_validator('interception_item', 'station', mode='before')
    @classmethod
    def normalize_text_fields(cls, value: Any):
        return cls._normalize_optional_text(value)

    @field_validator('version_detection_html', mode='before')
    @classmethod
    def normalize_html_field(cls, value: Any):
        return cls._normalize_html_text(value)


class InterceptionStrategyUpdateSchema(InterceptionStrategyCreateSchema):
    interception_item: Optional[str] = None
    version_detection_html: Optional[str] = None

    @field_validator('version_detection_html', mode='before')
    @classmethod
    def normalize_optional_html_field(cls, value: Any):
        if value is None:
            return None
        return cls._normalize_html_text(value)


class InterceptionStrategyOutSchema(Schema):
    id: str
    interception_item: str
    version_detection_html: str = ''
    station: Optional[str] = None
    owner_ids: list[str] = Field(default_factory=list)
    owner_info: list[UserBriefSchema] = Field(default_factory=list)
    display_name: str
    sys_create_datetime: Optional[str] = None
    sys_update_datetime: Optional[str] = None


class InterceptionStrategyPageSchema(Schema):
    items: list[InterceptionStrategyOutSchema] = Field(default_factory=list)
    total: int


class InterceptionInsightFailureModeRowSchema(Schema):
    failure_mode_id: str
    failure_mode_brief: str
    subsystem: Optional[str] = None
    status: Optional[str] = None
    product_names: list[str] = Field(default_factory=list)
    landed_product_count: int


class InterceptionInsightProductRowSchema(Schema):
    product_id: str
    product_name: str
    owner_info: Optional[UserBriefSchema] = None
    failure_mode_briefs: list[str] = Field(default_factory=list)


class InterceptionInsightOutSchema(Schema):
    id: str
    interception_item: str
    station: Optional[str] = None
    related_failure_mode_count: int
    landed_product_count: int
    total_product_count: int
    failure_mode_rows: list[InterceptionInsightFailureModeRowSchema] = Field(
        default_factory=list,
    )
    product_rows: list[InterceptionInsightProductRowSchema] = Field(
        default_factory=list,
    )


class HandlingMeasureInsightOutSchema(Schema):
    id: str
    measure: str
    measure_category: Optional[str] = None
    related_test_case_count: int
    related_failure_mode_count: int
    landed_product_count: int
    total_product_count: int
    failure_mode_rows: list[InterceptionInsightFailureModeRowSchema] = Field(
        default_factory=list,
    )
    product_rows: list[InterceptionInsightProductRowSchema] = Field(
        default_factory=list,
    )


class ObservationMethodInsightOutSchema(Schema):
    id: str
    display_name: str
    monitor_type: Optional[str] = None
    log_id: Optional[str] = None
    log_keyword: Optional[str] = None
    log_path: Optional[str] = None
    related_failure_mode_count: int
    landed_product_count: int
    total_product_count: int
    failure_mode_rows: list[InterceptionInsightFailureModeRowSchema] = Field(
        default_factory=list,
    )
    product_rows: list[InterceptionInsightProductRowSchema] = Field(
        default_factory=list,
    )


class HuatuoDiagnosisInsightOutSchema(Schema):
    id: str
    description: str
    related_failure_mode_count: int
    landed_product_count: int
    total_product_count: int
    failure_mode_rows: list[InterceptionInsightFailureModeRowSchema] = Field(
        default_factory=list,
    )
    product_rows: list[InterceptionInsightProductRowSchema] = Field(
        default_factory=list,
    )


class TestCaseInsightOutSchema(Schema):
    id: str
    brief: str
    cida_link: Optional[str] = None
    related_handling_measure_count: int
    related_failure_mode_count: int
    landed_product_count: int
    total_product_count: int
    failure_mode_rows: list[InterceptionInsightFailureModeRowSchema] = Field(
        default_factory=list,
    )
    product_rows: list[InterceptionInsightProductRowSchema] = Field(
        default_factory=list,
    )


class HandlingMeasureCreateSchema(OwnerResourceCreateSchema):
    measure_category: Optional[str] = None
    measure: str
    measure_detail_html: str = ''
    measure_effect: Optional[str] = None
    test_case_ids: list[str] = Field(default_factory=list)

    @field_validator('test_case_ids', mode='before')
    @classmethod
    def normalize_test_case_ids(cls, value: Any):
        return cls._normalize_string_list(value)

    @field_validator('measure_category', 'measure', 'measure_effect', mode='before')
    @classmethod
    def normalize_text_fields(cls, value: Any):
        return cls._normalize_optional_text(value)

    @field_validator('measure_detail_html', mode='before')
    @classmethod
    def normalize_html_field(cls, value: Any):
        return cls._normalize_html_text(value)


class HandlingMeasureUpdateSchema(HandlingMeasureCreateSchema):
    measure_category: Optional[str] = None
    measure: Optional[str] = None
    measure_detail_html: Optional[str] = None
    measure_effect: Optional[str] = None

    @field_validator('measure_detail_html', mode='before')
    @classmethod
    def normalize_optional_html_field(cls, value: Any):
        if value is None:
            return None
        return cls._normalize_html_text(value)


class HandlingMeasureOutSchema(Schema):
    id: str
    measure_category: Optional[str] = None
    measure: str
    measure_detail_html: str = ''
    measure_effect: str = ''
    owner_ids: list[str] = Field(default_factory=list)
    owner_info: list[UserBriefSchema] = Field(default_factory=list)
    test_case_ids: list[str] = Field(default_factory=list)
    test_case_items: list[RelationItemSchema] = Field(default_factory=list)
    display_name: str
    sys_create_datetime: Optional[str] = None
    sys_update_datetime: Optional[str] = None


class HandlingMeasurePageSchema(Schema):
    items: list[HandlingMeasureOutSchema] = Field(default_factory=list)
    total: int


class ObservationMethodCreateSchema(OwnerResourceCreateSchema):
    monitor_type: Optional[str] = None
    log_id: Optional[str] = None
    log_keyword: Optional[str] = None
    log_path: Optional[str] = None

    @field_validator('monitor_type', 'log_id', 'log_keyword', 'log_path', mode='before')
    @classmethod
    def normalize_text_fields(cls, value: Any):
        return cls._normalize_optional_text(value)


class ObservationMethodUpdateSchema(ObservationMethodCreateSchema):
    pass


class ObservationMethodOutSchema(Schema):
    id: str
    monitor_type: Optional[str] = None
    log_id: Optional[str] = None
    log_keyword: Optional[str] = None
    log_path: Optional[str] = None
    owner_ids: list[str] = Field(default_factory=list)
    owner_info: list[UserBriefSchema] = Field(default_factory=list)
    display_name: str
    sys_create_datetime: Optional[str] = None
    sys_update_datetime: Optional[str] = None


class ObservationMethodPageSchema(Schema):
    items: list[ObservationMethodOutSchema] = Field(default_factory=list)
    total: int


class HuatuoDiagnosisCreateSchema(OwnerResourceCreateSchema):
    description: str

    @field_validator('description', mode='before')
    @classmethod
    def normalize_description(cls, value: Any):
        return cls._normalize_optional_text(value)


class HuatuoDiagnosisUpdateSchema(HuatuoDiagnosisCreateSchema):
    description: Optional[str] = None


class HuatuoDiagnosisOutSchema(Schema):
    id: str
    description: str
    owner_ids: list[str] = Field(default_factory=list)
    owner_info: list[UserBriefSchema] = Field(default_factory=list)
    display_name: str
    sys_create_datetime: Optional[str] = None
    sys_update_datetime: Optional[str] = None


class HuatuoDiagnosisPageSchema(Schema):
    items: list[HuatuoDiagnosisOutSchema] = Field(default_factory=list)
    total: int


class TestCaseCreateSchema(OwnerResourceCreateSchema):
    brief: str
    detail_html: str = ''
    cida_link: Optional[str] = None

    @field_validator('brief', 'cida_link', mode='before')
    @classmethod
    def normalize_text_fields(cls, value: Any):
        return cls._normalize_optional_text(value)

    @field_validator('detail_html', mode='before')
    @classmethod
    def normalize_html_field(cls, value: Any):
        return cls._normalize_html_text(value)


class TestCaseUpdateSchema(TestCaseCreateSchema):
    brief: Optional[str] = None
    detail_html: Optional[str] = None
    cida_link: Optional[str] = None

    @field_validator('detail_html', mode='before')
    @classmethod
    def normalize_optional_html_field(cls, value: Any):
        if value is None:
            return None
        return cls._normalize_html_text(value)


class TestCaseOutSchema(Schema):
    id: str
    brief: str
    detail_html: str = ''
    cida_link: Optional[str] = None
    owner_ids: list[str] = Field(default_factory=list)
    owner_info: list[UserBriefSchema] = Field(default_factory=list)
    display_name: str
    sys_create_datetime: Optional[str] = None
    sys_update_datetime: Optional[str] = None


class TestCasePageSchema(Schema):
    items: list[TestCaseOutSchema] = Field(default_factory=list)
    total: int


class FailureModeSubsystemConfigSearchSchema(KeywordSearchSchema):
    pass


class FailureModeSubsystemConfigCreateSchema(ListTextSchemaMixin):
    subsystem: str
    module_options: list[str] = Field(default_factory=list)
    chip_options: list[str] = Field(default_factory=list)

    @field_validator('subsystem', mode='before')
    @classmethod
    def normalize_subsystem(cls, value: Any):
        return cls._normalize_optional_text(value)

    @field_validator('module_options', 'chip_options', mode='before')
    @classmethod
    def normalize_option_lists(cls, value: Any):
        return cls._normalize_string_list(value)


class FailureModeSubsystemConfigUpdateSchema(FailureModeSubsystemConfigCreateSchema):
    subsystem: Optional[str] = None


class FailureModeSubsystemConfigOutSchema(Schema):
    id: str
    subsystem: str
    module_options: list[str] = Field(default_factory=list)
    chip_options: list[str] = Field(default_factory=list)
    sys_create_datetime: Optional[str] = None
    sys_update_datetime: Optional[str] = None


class FailureModeSubsystemConfigPageSchema(Schema):
    items: list[FailureModeSubsystemConfigOutSchema] = Field(default_factory=list)
    total: int


class FailureModeSubsystemLinkedOptionSchema(Schema):
    subsystem: str
    module_options: list[str] = Field(default_factory=list)
    chip_options: list[str] = Field(default_factory=list)


class FailureModeSubsystemConfigOptionsSchema(Schema):
    subsystem_options: list[DictOptionSchema] = Field(default_factory=list)
    module_options: list[DictOptionSchema] = Field(default_factory=list)
    chip_options: list[DictOptionSchema] = Field(default_factory=list)
    items: list[FailureModeSubsystemLinkedOptionSchema] = Field(default_factory=list)


class FailureModeStatisticsSubsystemSearchSchema(KeywordSearchSchema):
    subsystems: list[str] = Field(default_factory=list)

    @field_validator('subsystems', mode='before')
    @classmethod
    def normalize_statistics_subsystems(cls, value: Any):
        return _normalize_query_list(value)


class FailureModeStatisticsSummarySearchSchema(Schema):
    subsystems: list[str] = Field(default_factory=list)

    @field_validator('subsystems', mode='before')
    @classmethod
    def normalize_statistics_summary_subsystems(cls, value: Any):
        return _normalize_query_list(value)


class FailureModeStatisticsChartDatumSchema(Schema):
    name: str
    value: int


class FailureModeStatisticsSummarySchema(Schema):
    subsystem_counts: list[FailureModeStatisticsChartDatumSchema] = Field(default_factory=list)
    interception_status: list[FailureModeStatisticsChartDatumSchema] = Field(default_factory=list)
    huatuo_status: list[FailureModeStatisticsChartDatumSchema] = Field(default_factory=list)
    handling_detection_status: list[FailureModeStatisticsChartDatumSchema] = Field(default_factory=list)
    handling_prevention_status: list[FailureModeStatisticsChartDatumSchema] = Field(default_factory=list)
    handling_self_heal_status: list[FailureModeStatisticsChartDatumSchema] = Field(default_factory=list)
    observation_pipeline_log_status: list[FailureModeStatisticsChartDatumSchema] = Field(default_factory=list)
    observation_dmd_status: list[FailureModeStatisticsChartDatumSchema] = Field(default_factory=list)
    observation_fmp_status: list[FailureModeStatisticsChartDatumSchema] = Field(default_factory=list)


class FailureModeStatisticsSubsystemRowSchema(Schema):
    subsystem: str
    failure_mode_count: int
    interception_relation_count: int
    handling_detection_relation_count: int
    handling_prevention_relation_count: int
    handling_self_heal_relation_count: int
    observation_pipeline_log_relation_count: int
    observation_dmd_relation_count: int
    observation_fmp_relation_count: int
    huatuo_relation_count: int
    pending_failure_mode_count: int
    pending_rate: float
    status_light: str


class FailureModeStatisticsSubsystemPageSchema(Schema):
    items: list[FailureModeStatisticsSubsystemRowSchema] = Field(default_factory=list)
    total: int


class FailureModeProductStatisticsSummarySchema(FailureModeStatisticsSummarySchema):
    pass


class FailureModeProductStatisticsOverviewItemSchema(Schema):
    product_id: str
    product_name: str
    owner_info: Optional[UserBriefSchema] = None
    baseline_failure_mode_count: int
    pending_failure_mode_count: int
    pending_rate: float
    status_light: str


class FailureModeProductStatisticsSearchSchema(SearchPaginationSchema):
    product_ids: list[str] = Field(default_factory=list)
    keyword: Optional[str] = None
    subsystems: list[str] = Field(default_factory=list)

    @field_validator('keyword', mode='before')
    @classmethod
    def normalize_product_statistics_text(cls, value: Any):
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator('product_ids', 'subsystems', mode='before')
    @classmethod
    def normalize_product_statistics_lists(cls, value: Any):
        return _normalize_query_list(value)


class FailureModeProductStatisticsSummarySearchSchema(Schema):
    product_ids: list[str] = Field(default_factory=list)
    subsystems: list[str] = Field(default_factory=list)

    @field_validator('product_ids', 'subsystems', mode='before')
    @classmethod
    def normalize_product_statistics_summary_lists(cls, value: Any):
        return _normalize_query_list(value)


class FailureModeProductStatisticsSubsystemRowSchema(
    FailureModeStatisticsSubsystemRowSchema,
):
    pass


class FailureModeProductStatisticsSubsystemPageSchema(Schema):
    items: list[FailureModeProductStatisticsSubsystemRowSchema] = Field(
        default_factory=list,
    )
    total: int


class SaveSuccessSchema(Schema):
    success: bool = True


# --- Workflow & Product Schemas ---

class FailureModeRolePreviewOutSchema(Schema):
    subsystem: str
    feature_se_info: list[UserBriefSchema] = Field(default_factory=list)
    member_info: list[UserBriefSchema] = Field(default_factory=list)


class FailureModeProductOutSchema(Schema):
    id: str
    project_id: str
    project_name: str
    owner_id: Optional[str] = None
    owner_info: Optional[UserBriefSchema] = None
    owner_assignment_id: Optional[str] = None
    can_manage_roles: bool = False
    role_preview: list[FailureModeRolePreviewOutSchema] = Field(default_factory=list)
    sys_create_datetime: Optional[str] = None
    sys_update_datetime: Optional[str] = None

class FailureModeProductPageSchema(Schema):
    items: list[FailureModeProductOutSchema] = Field(default_factory=list)
    total: int

class FailureModeProductUpdateSchema(Schema):
    owner_id: Optional[str] = None


class FailureModeTaskOutSchema(Schema):
    id: str
    task_no: str
    name: str
    task_type: str
    status: str
    product_id: str
    product_name: str
    subsystem: str
    creator_id: Optional[str] = None
    creator_info: Optional[UserBriefSchema] = None
    assignee_id: Optional[str] = None
    assignee_info: Optional[UserBriefSchema] = None
    current_processor_id: Optional[str] = None
    current_processor_info: Optional[UserBriefSchema] = None
    available_actions: list[str] = Field(default_factory=list)
    review_result: str = ''
    review_minutes_html: str = ''
    review_attachment_ids: list[str] = Field(default_factory=list)
    accepted_at: Optional[str] = None
    submitted_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    closed_at: Optional[str] = None
    sys_create_datetime: Optional[str] = None
    sys_update_datetime: Optional[str] = None

class FailureModeTaskPageSchema(Schema):
    items: list[FailureModeTaskOutSchema] = Field(default_factory=list)
    total: int

class FailureModeTaskCreateSchema(Schema):
    name: str
    task_type: str
    product_id: str
    subsystem: str
    assignee_id: str

class FailureModeTaskUpdateSchema(Schema):
    name: Optional[str] = None
    assignee_id: Optional[str] = None

class TaskReassignSchema(Schema):
    assignee_id: str

class TaskRecallSchema(Schema):
    reason: str = ''

class TaskRejectSchema(Schema):
    reason: str

class TaskCloseSchema(Schema):
    review_result: str = 'approved'
    review_minutes_html: str
    review_attachment_ids: list[str] = Field(default_factory=list)

class TaskFailureModeBindSchema(Schema):
    failure_mode_ids: list[str] = Field(default_factory=list)

class TaskFailureModeSearchSchema(SearchPaginationSchema):
    keyword: Optional[str] = Field(None, description='关键词')

class ProductFailureModeOutSchema(Schema):
    id: str
    product_id: str
    subsystem: str
    failure_mode_id: str
    failure_mode_brief: str
    sys_create_datetime: Optional[str] = None

class ProductFailureModePageSchema(Schema):
    items: list[ProductFailureModeOutSchema] = Field(default_factory=list)
    total: int


class FailureModeRoleAssignmentOutSchema(Schema):
    id: str
    user_id: str
    user_info: UserBriefSchema
    role: str
    product_id: Optional[str] = None
    subsystem: str = ''
    is_active: bool = True
    sys_create_datetime: Optional[str] = None
    sys_update_datetime: Optional[str] = None


class ProductRoleAssignmentSaveItemSchema(Schema):
    user_id: str
    role: str
    subsystem: str

    @field_validator('user_id', 'role', 'subsystem', mode='before')
    @classmethod
    def normalize_role_assignment_text(cls, value: Any):
        text = str(value or '').strip()
        return text


class ProductRoleAssignmentBatchSaveSchema(Schema):
    assignments: list[ProductRoleAssignmentSaveItemSchema] = Field(default_factory=list)


class VisibleSubsystemOutSchema(Schema):
    label: str
    value: str


class FailureModeTaskLogOutSchema(Schema):
    id: str
    action: str
    from_status: str = ''
    to_status: str = ''
    note: str = ''
    operator_id: Optional[str] = None
    operator_info: Optional[UserBriefSchema] = None
    extra_data: dict[str, Any] = Field(default_factory=dict)
    sys_create_datetime: Optional[str] = None
