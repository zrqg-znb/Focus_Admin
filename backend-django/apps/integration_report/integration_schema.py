from ninja import Schema
from typing import List, Optional, Dict
from datetime import date, datetime


class MetricCell(Schema):
    key: str
    name: str
    value: Optional[float] = None
    text: Optional[str] = None
    unit: Optional[str] = None
    url: Optional[str] = None
    level: str = "normal"  # normal|warning|danger


class ProjectConfigOut(Schema):
    id: str  # Config ID
    name: str  # Config Name
    project_id: str
    project_name: str
    project_domain: str
    project_type: str
    project_managers: str
    managers: str  # Config managers
    enabled: bool
    subscribed: bool
    latest_date: Optional[date] = None
    code_metrics: List[MetricCell] = []
    dt_metrics: List[MetricCell] = []


class ProjectConfigUpsertIn(Schema):
    project_id: Optional[str] = None
    name: str
    managers: List[str] = []
    enabled: bool = True
    code_check_task_id: str = ""
    bin_scope_task_id: str = ""
    build_check_task_id: str = ""
    compile_check_task_id: str = ""
    dt_project_id: str = ""


class ConfigFilterSchema(Schema):
    project_name: Optional[str] = None


class ProjectConfigManageRow(Schema):
    id: str  # Config ID
    name: str  # Config Name
    project_id: str
    project_name: str
    managers: str
    manager_ids: List[str]
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
    config_id: str
    config_name: str
    project_name: str
    code_metrics: List[MetricCell] = []
    dt_metrics: List[MetricCell] = []


class HistoryQueryOut(Schema):
    items: List[HistoryRow]


class MockCollectIn(Schema):
    record_date: Optional[date] = None
    config_ids: List[str] = []


class EmailDeliveryRow(Schema):
    id: str
    record_date: date
    user_id: str
    user_name: Optional[str] = None
    to_email: str
    subject: str
    status: str  # pending|sent|failed
    error_message: Optional[str] = None
    sys_create_datetime: Optional[datetime] = None


class EmailDeliveryQueryIn(Schema):
    status: Optional[str] = None  # pending|sent|failed
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    user_id: Optional[str] = None
    to_email: Optional[str] = None
    page: Optional[int] = 1
    page_size: Optional[int] = 20


class EmailDeliveryQueryOut(Schema):
    items: List[EmailDeliveryRow]
    count: int
    page: int
    page_size: int
