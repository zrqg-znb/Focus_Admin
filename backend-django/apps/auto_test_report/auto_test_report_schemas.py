from datetime import date, datetime
from typing import List, Optional

from ninja import Schema


class PlatformIn(Schema):
    name: str
    version_code: str
    sort: int = 0
    is_active: bool = True
    remark: Optional[str] = None


class PlatformOut(PlatformIn):
    id: str
    vehicle_count: int = 0
    sys_create_datetime: Optional[datetime] = None
    sys_update_datetime: Optional[datetime] = None


class VehicleIn(Schema):
    platform_id: str
    name: str
    vehicle_code: str
    cdc_platform: str
    execution_machine: str
    sort: int = 0
    is_active: bool = True
    remark: Optional[str] = None


class VehicleOut(VehicleIn):
    id: str
    platform_name: str
    sys_create_datetime: Optional[datetime] = None
    sys_update_datetime: Optional[datetime] = None


class VehicleOption(Schema):
    id: str
    name: str
    vehicle_code: str
    platform_id: str
    platform_name: str


class TestCaseIn(Schema):
    vehicle_id: str
    case_no: str
    case_name: str
    remark: Optional[str] = None
    sort: int = 0
    is_active: bool = True


class TestCaseOut(TestCaseIn):
    id: str
    vehicle_name: str
    vehicle_code: str
    platform_name: str
    latest_execute_time: Optional[datetime] = None
    sys_create_datetime: Optional[datetime] = None
    sys_update_datetime: Optional[datetime] = None


class TestCaseFilter(Schema):
    platform_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    keyword: Optional[str] = None
    is_active: Optional[bool] = None


class ImportCaseRow(Schema):
    case_no: str
    case_name: str
    remark: Optional[str] = None


class ImportCasePayload(Schema):
    vehicle_id: str
    rows: List[ImportCaseRow]


class ImportErrorRow(Schema):
    row_no: int
    message: str


class ImportResultOut(Schema):
    created_count: int
    updated_count: int
    ignored_count: int
    errors: List[ImportErrorRow]


class DailyResultItemOut(Schema):
    result_id: Optional[str] = None
    case_id: str
    case_no: str
    case_name: str
    remark: Optional[str] = None
    status: str
    failure_reason: Optional[str] = None
    suggested_failure_reason: Optional[str] = None
    start_time: Optional[datetime] = None
    duration_seconds: int = 0
    log_url: Optional[str] = None
    reported_at: Optional[datetime] = None


class UpdateTestCaseRemarkIn(Schema):
    remark: Optional[str] = None


class SummaryStat(Schema):
    key: str
    label: str
    count: int
    ratio: float


class DailySummaryOut(Schema):
    vehicle_id: str
    vehicle_name: str
    vehicle_code: str
    execute_date: date
    total_count: int
    success_count: int
    failed_count: int
    timeout_count: int
    skip_count: int
    total_duration_seconds: int
    stats: List[SummaryStat]
    last_report_at: Optional[datetime] = None


class DailyHistoryRow(Schema):
    id: str
    execute_date: date
    status: str
    failure_reason: Optional[str] = None
    start_time: Optional[datetime] = None
    duration_seconds: int = 0
    log_url: Optional[str] = None
    reported_at: Optional[datetime] = None


class DailyHistoryPage(Schema):
    items: List[DailyHistoryRow]
    total: int
    page: int
    page_size: int


class ReportResultItemIn(Schema):
    case_no: str
    start_time: datetime
    duration_seconds: int
    result: str
    log_url: Optional[str] = None


class ReportDailyResultsIn(Schema):
    vehicle_code: str
    execute_date: date
    results: List[ReportResultItemIn]


class ReportDailyResultsOut(Schema):
    vehicle_id: str
    execute_date: date
    created_count: int
    updated_count: int


class DailyResultQuery(Schema):
    vehicle_id: str
    execute_date: date


class DailyOverviewQuery(Schema):
    execute_date: date
    platform_id: Optional[str] = None
    abnormal_only: bool = False


class DailyOverviewRow(Schema):
    vehicle_id: str
    vehicle_name: str
    vehicle_code: str
    platform_id: str
    platform_name: str
    total_count: int
    success_count: int
    failed_count: int
    timeout_count: int
    skip_count: int
    total_duration_seconds: int
    last_report_at: Optional[datetime] = None
    is_abnormal: bool


class DailyOverviewSummary(Schema):
    execute_date: date
    vehicle_count: int
    abnormal_vehicle_count: int
    total_case_count: int
    success_count: int
    failed_count: int
    timeout_count: int
    skip_count: int
    total_duration_seconds: int
    stats: List[SummaryStat]
    last_report_at: Optional[datetime] = None


class DailyOverviewResponse(Schema):
    items: List[DailyOverviewRow]
    summary: DailyOverviewSummary


class UpdateFailureReasonIn(Schema):
    failure_reason: Optional[str] = None
