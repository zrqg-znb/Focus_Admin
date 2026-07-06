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
    dt_bin_task_id: str = ""
    cooddy_check_task_id: str = ""
    code_scan_project_key: str = ""
    valgrind_sub_modules: List[str] = []
    enable_dt_fuzz: bool = False
    dt_fuzz_version_name: str = ""
    dt_fuzz_branches: List[str] = []
    dt_fuzz_pbi_id: str = ""
    dt_fuzz_domain_id: str = ""
    dt_fuzz_project_id: str = ""
    code_metrics: List[MetricCell] = []
    dt_metrics: List[MetricCell] = []


class ProjectConfigUpsertIn(Schema):
    project_id: Optional[str] = None
    name: str
    managers: List[str] = []
    enabled: bool = True
    code_check_task_id: str = ""
    dt_bin_task_id: str = ""
    cooddy_check_task_id: str = ""
    bin_scope_task_id: str = ""
    build_check_task_id: str = ""
    compile_check_task_id: str = ""
    dt_project_id: str = ""
    code_scan_project_key: str = ""
    valgrind_sub_modules: List[str] = []
    enable_dt_fuzz: bool = False
    dt_fuzz_version_name: str = ""
    dt_fuzz_branches: List[str] = []
    dt_fuzz_pbi_id: str = ""
    dt_fuzz_domain_id: str = ""
    dt_fuzz_project_id: str = ""


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
    dt_bin_task_id: str
    cooddy_check_task_id: str
    bin_scope_task_id: str
    build_check_task_id: str
    compile_check_task_id: str
    dt_project_id: str
    code_scan_project_key: str
    valgrind_sub_modules: List[str]
    enable_dt_fuzz: bool = False
    dt_fuzz_version_name: str = ""
    dt_fuzz_branches: List[str] = []
    dt_fuzz_pbi_id: str = ""
    dt_fuzz_domain_id: str = ""
    dt_fuzz_project_id: str = ""


class SubscriptionToggleIn(Schema):
    enabled: bool


class HistoryRow(Schema):
    record_date: date
    config_id: str
    config_name: str
    project_name: str
    caretaker_names: str = ""
    code_metrics: List[MetricCell] = []
    dt_metrics: List[MetricCell] = []


class DtFuzzNode(Schema):
    node_key: str
    name: str = ""
    type: str = ""
    highRiskApiCover: str = ""
    highRiskApiTotal: str = ""
    highRiskApiCoverage: str = ""
    secLineCover: str = ""
    secLineTotal: str = ""
    secLineCoverage: str = ""
    secReportUrl: str = ""
    lcovLineCover: str = ""
    lcovLineTotal: str = ""
    lcovLineCoverage: str = ""
    lcovReportUrl: str = ""
    defectNumber: str = ""
    casePass: str = ""
    casePassRate: str = ""
    caseActive: str = ""
    caseActiveRate: str = ""
    caseTotal: str = ""
    reportUrl: str = ""
    branch: str = ""
    owner: str = ""
    children: List["DtFuzzNode"] = []


class DtFuzzHistoryItem(Schema):
    record_date: date
    config_id: str
    config_name: str
    project_name: str
    branch: str
    owner: str = ""
    source_due_date: str = ""
    nodes: List[DtFuzzNode] = []


class HistoryQueryOut(Schema):
    items: List[HistoryRow]
    dt_fuzz_items: List[DtFuzzHistoryItem] = []


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


class SubscriptionManagementProjectQueryIn(Schema):
    keyword: Optional[str] = None
    enabled: Optional[bool] = None
    has_subscribers: Optional[bool] = None
    has_missing_email: Optional[bool] = None
    page: Optional[int] = 1
    page_size: Optional[int] = 20


class SubscriptionManagementProjectRow(Schema):
    id: str
    name: str
    project_id: str
    project_name: str
    managers: str
    project_managers: str
    enabled: bool
    subscriber_count: int
    missing_email_count: int
    sys_update_datetime: Optional[datetime] = None


class SubscriptionManagementProjectQueryOut(Schema):
    items: List[SubscriptionManagementProjectRow]
    count: int
    page: int
    page_size: int


class SubscriptionSubscriberQueryIn(Schema):
    keyword: Optional[str] = None
    enabled: Optional[bool] = None
    page: Optional[int] = 1
    page_size: Optional[int] = 20


class SubscriptionSubscriberRow(Schema):
    id: str
    user_id: str
    username: str
    name: Optional[str] = None
    email: Optional[str] = None
    enabled: bool
    sys_update_datetime: Optional[datetime] = None


class SubscriptionSubscriberQueryOut(Schema):
    items: List[SubscriptionSubscriberRow]
    count: int
    page: int
    page_size: int


class SubscriptionUserIdsIn(Schema):
    user_ids: List[str]


class SubscriptionBatchProjectUsersIn(Schema):
    config_ids: List[str]
    user_ids: List[str]


class SubscriptionBatchResultOut(Schema):
    changed_count: int
