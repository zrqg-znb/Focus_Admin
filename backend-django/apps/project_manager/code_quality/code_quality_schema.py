from __future__ import annotations

from datetime import date
from typing import Any, List, Optional

from ninja import Field, ModelSchema, Schema

from .code_quality_model import CodeModule, CodeMetric


class ModuleConfigSchema(Schema):
    id: Optional[str] = None
    project_id: str
    oem_name: str
    module: str
    owner_ids: Optional[List[str]] = None


class CodeMetricSchema(Schema):
    record_date: date
    loc: int
    function_count: int
    dangerous_func_count: int
    duplication_rate: float
    is_clean_code: bool


class CodeMetricOut(ModelSchema):
    module_id: str

    class Meta:
        model = CodeMetric
        fields = "__all__"

    @staticmethod
    def resolve_module_id(obj):
        return str(obj.module_id)


class CodeModuleOut(ModelSchema):
    project_id: str
    owner_names: Optional[List[str]] = Field(None, description="责任人姓名列表")
    owner_ids: Optional[List[str]] = Field(None, description="责任人ID列表")

    class Meta:
        model = CodeModule
        fields = "__all__"
        
    @staticmethod
    def resolve_owner_names(obj):
        return [user.name for user in obj.owners.all()] if obj.owners.exists() else []

    @staticmethod
    def resolve_owner_ids(obj):
        return [str(user.id) for user in obj.owners.all()] if obj.owners.exists() else []

    @staticmethod
    def resolve_project_id(obj):
        return str(obj.project_id)


class QualityMetricValueSchema(Schema):
    key: str
    label: str
    display: str
    num: Optional[float] = None
    is_warning: bool = False
    raw: Optional[Any] = None


class QualityTreeNodeSchema(Schema):
    id: str
    node_key: str
    version_name: str
    owner_names: List[str] = Field(default_factory=list)
    owner_ids: List[str] = Field(default_factory=list)
    depth: int = 0
    clean_code_rate: float = 0.0
    is_clean_code: bool = False
    unachieved_clean_code: List[str] = Field(default_factory=list)
    warning_count: int = 0
    warning_metrics: List[str] = Field(default_factory=list)
    metric_values: List[QualityMetricValueSchema] = Field(default_factory=list)
    children: List["QualityTreeNodeSchema"] = Field(default_factory=list)


class ProjectQualitySummarySchema(Schema):
    project_id: str
    project_name: str
    project_domain: str
    project_type: str
    project_managers: str
    record_date: Optional[date] = None
    oem_name: str = ""
    total_loc: int = 0
    total_function_count: int = 0
    total_dangerous_func_count: int = 0
    avg_duplication_rate: float = 0.0
    module_count: int = 0
    clean_code_achieve_rate: float = 0.0
    clean_code_pass_modules: int = 0
    total_node_count: int = 0
    warning_node_count: int = 0
    warning_count: int = 0
    warning_metrics: List[str] = Field(default_factory=list)
    unachieved_clean_code: List[str] = Field(default_factory=list)
    metric_values: List[QualityMetricValueSchema] = Field(default_factory=list)


class QualityOverviewFilterSchema(Schema):
    project_name: Optional[str] = Field(None, description="项目名称关键词")
    project_manager: Optional[str] = Field(None, description="项目负责人关键词")
    project_type: Optional[str] = Field(None, description="项目类型筛选(vehicle/cockpit)")
    oem_name: Optional[str] = Field(None, description="OEM名称关键词")
    date: Optional[str] = Field(
        None,
        description="记录日期筛选，支持YYYY-MM-DD或YYYYMMDD",
    )


class ModuleQualityDetailSchema(Schema):
    id: str
    oem_name: str
    module: str
    owner_names: List[str]
    owner_ids: List[str]
    record_date: Optional[date] = None
    loc: int = 0
    function_count: int = 0
    dangerous_func_count: int = 0
    duplication_rate: float = 0.0
    is_clean_code: bool = False
    clean_code_rate: float = 0.0
    clean_code_total: int = 11
    unachieved_clean_code: List[str] = Field(default_factory=list)
    warning_count: int = 0
    warning_metrics: List[str] = Field(default_factory=list)
    total_node_count: int = 0
    warning_node_count: int = 0
    root_version_name: str = ""
    metric_values: List[QualityMetricValueSchema] = Field(default_factory=list)
    nodes: List[QualityTreeNodeSchema] = Field(default_factory=list)


class NodeOwnerUpdateSchema(Schema):
    module_id: str
    node_key: str
    owner_ids: List[str] = Field(default_factory=list)
