from ninja import Schema, ModelSchema, Field
from typing import List, Optional, Any, Union
from datetime import date
from .models import PerformanceIndicator, PerformanceIndicatorData, PerformanceIndicatorImportTask, PerformanceRiskRecord

class PerformanceIndicatorSchema(ModelSchema):
    owner_id: Optional[str] = Field(None, alias="owner.id")
    owner_name: Optional[str] = Field(None, alias="owner.name") # Assuming User model has 'name' or 'username'
    
    class Meta:
        model = PerformanceIndicator
        fields = '__all__'
        exclude = ['owner'] # Exclude the default owner field which might be an object

    @staticmethod
    def resolve_owner_name(obj):
        if obj.owner:
            return obj.owner.name or obj.owner.username
        return None

class PerformanceIndicatorCreateSchema(Schema):
    code: Optional[str] = None
    category: str
    name: str
    module: str
    project: str
    chip_type: str
    value_type: str
    baseline_value: float
    baseline_unit: str
    fluctuation_range: float
    fluctuation_direction: str
    owner_id: Optional[str] = None

class PerformanceIndicatorUpdateSchema(Schema):
    code: Optional[str] = None
    category: Optional[str] = None
    name: Optional[str] = None
    module: Optional[str] = None
    project: Optional[str] = None
    chip_type: Optional[str] = None
    value_type: Optional[str] = None
    baseline_value: Optional[float] = None
    baseline_unit: Optional[str] = None
    fluctuation_range: Optional[float] = None
    fluctuation_direction: Optional[str] = None
    owner_id: Optional[str] = None

class PerformanceBatchDeleteSchema(Schema):
    ids: List[str]

class PerformanceBatchUpdateSchema(Schema):
    ids: List[str]
    field: str
    value: Union[str, int, float, bool, None]

    class Config:
        arbitrary_types_allowed = True

class PerformanceDataUploadItem(Schema):
    code: Optional[str] = None
    name: Optional[str] = None
    value: float

class PerformanceDataUploadSchema(Schema):
    category: Optional[str] = None
    project: str
    module: str
    chip_type: str
    date: date
    data: List[PerformanceDataUploadItem]

class PerformanceDataUploadResponse(Schema):
    success_count: int
    errors: List[str]

class PerformanceDataTrendSchema(Schema):
    date: date
    value: float
    fluctuation_value: float

class PerformanceTreeNodeSchema(Schema):
    key: str
    label: str
    type: str
    children: List['PerformanceTreeNodeSchema'] = []

class PerformanceChipTypeSchema(Schema):
    chip_type: str

class PerformanceImportTaskStartResponse(Schema):
    task_id: str

class PerformanceImportTaskSchema(ModelSchema):
    class Meta:
        model = PerformanceIndicatorImportTask
        fields = [
            'id',
            'status',
            'progress',
            'filename',
            'total_rows',
            'processed_rows',
            'success_count',
            'error_count',
            'message',
            'errors',
            'started_at',
            'finished_at',
            'sys_create_datetime',
        ]

class PerformanceRiskRecordSchema(ModelSchema):
    indicator_name: Optional[str] = Field(None, alias="indicator.name")
    project: Optional[str] = Field(None, alias="indicator.project")
    module: Optional[str] = Field(None, alias="indicator.module")
    chip_type: Optional[str] = Field(None, alias="indicator.chip_type")
    owner_name: Optional[str] = Field(None, alias="owner.name")

    class Meta:
        model = PerformanceRiskRecord
        fields = '__all__'
        exclude = ['indicator', 'data', 'owner']

class PerformanceRiskQuerySchema(Schema):
    category: Optional[str] = None
    project: Optional[str] = None
    module: Optional[str] = None
    chip_type: Optional[str] = None
    status: Optional[str] = None
    indicator_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class PerformanceRiskConfirmSchema(Schema):
    resolved: bool
    reason: str

class PerformanceRiskResolveSchema(Schema):
    reason: Optional[str] = None
