from ninja import Schema, ModelSchema, Field
from typing import Optional, List
from datetime import date
from .iteration_model import Iteration, IterationMetric

class IterationCreateSchema(Schema):
    project_id: str
    name: str
    code: str
    start_date: date
    end_date: date
    is_current: bool = False
    is_healthy: bool = True

class IterationUpdateSchema(Schema):
    name: Optional[str] = None
    code: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None
    is_healthy: Optional[bool] = None

class IterationMetricSchema(Schema):
    record_date: date
    req_decomposition_rate: float
    req_drift_rate: float
    req_completion_rate: float
    req_workload: float
    completed_workload: float

class IterationMetricOut(ModelSchema):
    class Meta:
        model = IterationMetric
        fields = "__all__"

class IterationOut(ModelSchema):
    class Meta:
        model = Iteration
        fields = "__all__"

class IterationDetailSchema(IterationOut):
    latest_metric: Optional[IterationMetricOut] = None
