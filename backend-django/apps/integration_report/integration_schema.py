from ninja import Schema
from typing import List, Optional, Dict
from datetime import date


class MetricCell(Schema):
    key: str
    name: str
    value: Optional[float] = None
    text: Optional[str] = None
    unit: Optional[str] = None
    url: Optional[str] = None
    level: str = "normal"  # normal|warning|danger


class ProjectConfigOut(Schema):
    project_id: str
    project_name: str
    project_domain: str
    project_type: str
    project_managers: str
    enabled: bool
    subscribed: bool
    latest_date: Optional[date] = None
    code_metrics: List[MetricCell] = []
    dt_metrics: List[MetricCell] = []


class ProjectConfigUpsertIn(Schema):
    enabled: bool = True
    code_check_task_id: str = ""
    bin_scope_task_id: str = ""
    build_check_task_id: str = ""
    compile_check_task_id: str = ""
    dt_project_id: str = ""


class ProjectConfigManageRow(Schema):
    project_id: str
    project_name: str
    enabled: bool
    code_check_task_id: str
    bin_scope_task_id: str
    build_check_task_id: str
    compile_check_task_id: str
    dt_project_id: str


class SubscriptionToggleIn(Schema):
    enabled: bool


class HistoryRow(Schema):
    record_date: date
    project_id: str
    project_name: str
    code_metrics: List[MetricCell] = []
    dt_metrics: List[MetricCell] = []


class HistoryQueryOut(Schema):
    items: List[HistoryRow]
