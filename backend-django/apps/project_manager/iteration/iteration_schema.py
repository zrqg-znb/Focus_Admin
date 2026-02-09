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

class IterationMetricSchema(ModelSchema):
    """Input Schema matching the raw data"""
    class Meta:
        model = IterationMetric
        exclude = ['id', 'iteration', 'sys_create_datetime', 'sys_update_datetime', 'sys_creator', 'sys_modifier', 'is_deleted', 'sort']

class IterationMetricOut(Schema):
    id: str
    iteration_id: str
    record_date: date

    sr_num: int = 0
    dr_num: int = 0
    ar_num: int = 0

    sr_breakdown_rate: float = 0.0
    dr_breakdown_rate: float = 0.0
    ar_set_a_rate: float = 0.0
    dr_set_a_rate: float = 0.0
    ar_set_c_rate: float = 0.0
    dr_set_c_rate: float = 0.0

    # New Indicators
    test_automation_rate: float = 0.0
    test_case_execution_rate: float = 0.0
    bug_fix_rate: float = 0.0
    code_review_rate: float = 0.0
    code_coverage_rate: float = 0.0

class IterationManualUpdateSchema(Schema):
    test_automation_rate: Optional[float] = None
    test_case_execution_rate: Optional[float] = None

class IterationOut(ModelSchema):
    project_id: str
    class Meta:
        model = Iteration
        fields = "__all__"
    
    @staticmethod
    def resolve_project_id(obj):
        return str(obj.project_id)

class IterationDetailSchema(IterationOut):
    latest_metric: Optional[IterationMetricOut] = None

class IterationDashboardSchema(Schema):
    project_id: str
    project_name: str
    project_domain: str
    project_type: str
    project_managers: str
    current_iteration_name: Optional[str] = None
    current_iteration_code: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_healthy: bool = True

    # IDs
    iteration_id: Optional[str] = None
    
    # Calculated Metrics
    sr_breakdown_rate: float = 0.0
    dr_breakdown_rate: float = 0.0
    ar_set_a_rate: float = 0.0
    dr_set_a_rate: float = 0.0
    ar_set_c_rate: float = 0.0
    dr_set_c_rate: float = 0.0

    # New Indicators
    test_automation_rate: float = 0.0
    test_case_execution_rate: float = 0.0
    bug_fix_rate: float = 0.0
    code_review_rate: float = 0.0
    code_coverage_rate: float = 0.0
    
    # Raw counts for context if needed (optional)
    sr_num: int = 0
    dr_num: int = 0
    ar_num: int = 0
