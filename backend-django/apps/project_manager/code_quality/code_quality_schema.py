from ninja import Schema, ModelSchema, Field
from typing import Optional, List
from datetime import date
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

class ProjectQualitySummarySchema(Schema):
    project_id: str
    project_name: str
    total_loc: int = 0
    total_function_count: int = 0
    total_dangerous_func_count: int = 0
    avg_duplication_rate: float = 0.0
    module_count: int = 0
