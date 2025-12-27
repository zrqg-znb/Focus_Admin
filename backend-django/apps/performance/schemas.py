from ninja import Schema, ModelSchema
from typing import List, Optional
from datetime import date
from .models import PerformanceIndicator, PerformanceIndicatorData

class PerformanceIndicatorSchema(ModelSchema):
    class Meta:
        model = PerformanceIndicator
        fields = '__all__'

class PerformanceIndicatorCreateSchema(Schema):
    code: Optional[str] = None
    name: str
    module: str
    project: str
    chip_type: str
    value_type: str
    baseline_value: float
    baseline_unit: str
    fluctuation_range: float
    fluctuation_direction: str
    owner: Optional[str] = None

class PerformanceIndicatorUpdateSchema(Schema):
    code: Optional[str] = None
    name: Optional[str] = None
    module: Optional[str] = None
    project: Optional[str] = None
    chip_type: Optional[str] = None
    value_type: Optional[str] = None
    baseline_value: Optional[float] = None
    baseline_unit: Optional[str] = None
    fluctuation_range: Optional[float] = None
    fluctuation_direction: Optional[str] = None
    owner: Optional[str] = None

class PerformanceDataUploadItem(Schema):
    code: Optional[str] = None
    name: Optional[str] = None
    value: float

class PerformanceDataUploadSchema(Schema):
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
