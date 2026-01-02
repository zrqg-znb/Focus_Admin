from ninja import Schema, ModelSchema, Field
from typing import Optional, List
from datetime import date
from .code_quality_model import CodeModule, CodeMetric

class ModuleConfigSchema(Schema):
    project_id: str
    name: str
    owner_id: Optional[str] = None

class CodeMetricSchema(Schema):
    record_date: date
    loc: int
    function_count: int
    dangerous_func_count: int
    duplication_rate: float

class CodeMetricOut(ModelSchema):
    class Meta:
        model = CodeMetric
        fields = "__all__"

class CodeModuleOut(ModelSchema):
    owner_name: Optional[str] = Field(None, description="责任人姓名")

    class Meta:
        model = CodeModule
        fields = "__all__"
        
    @staticmethod
    def resolve_owner_name(obj):
        return obj.owner.name if obj.owner else None

class ProjectQualitySummarySchema(Schema):
    project_id: str
    project_name: str
    total_loc: int = 0
    total_function_count: int = 0
    total_dangerous_func_count: int = 0
    avg_duplication_rate: float = 0.0
    module_count: int = 0
