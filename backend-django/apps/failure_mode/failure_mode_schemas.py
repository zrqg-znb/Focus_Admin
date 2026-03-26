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


class KeywordFilterSchema(Schema):
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


class FailureModeFilterSchema(KeywordFilterSchema):
    subsystem: list[str] = Field(default_factory=list)
    module: list[str] = Field(default_factory=list)
    status: list[str] = Field(default_factory=list)
    author_id: Optional[str] = None
    author_keyword: Optional[str] = None

    @field_validator(
        'subsystem',
        'module',
        'status',
        mode='before',
    )
    @classmethod
    def normalize_dict_filter_values(cls, value: Any):
        return _normalize_query_list(value)

    @field_validator('author_id', 'author_keyword', mode='before')
    @classmethod
    def normalize_text_filters(cls, value: Any):
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class HandlingMeasureFilterSchema(KeywordFilterSchema):
    measure_category: list[str] = Field(default_factory=list)

    @field_validator('measure_category', mode='before')
    @classmethod
    def normalize_measure_category(cls, value: Any):
        return _normalize_query_list(value)


class ObservationMethodFilterSchema(KeywordFilterSchema):
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
    interception_strategy_ids: list[str] = Field(default_factory=list)
    interception_strategy_items: list[RelationItemSchema] = Field(default_factory=list)
    handling_measure_ids: list[str] = Field(default_factory=list)
    handling_measure_items: list[RelationItemSchema] = Field(default_factory=list)
    observation_method_ids: list[str] = Field(default_factory=list)
    observation_method_items: list[RelationItemSchema] = Field(default_factory=list)
    huatuo_diagnosis_ids: list[str] = Field(default_factory=list)
    huatuo_diagnosis_items: list[RelationItemSchema] = Field(default_factory=list)
    sys_create_datetime: Optional[str] = None
    sys_update_datetime: Optional[str] = None


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


class SaveSuccessSchema(Schema):
    success: bool = True
