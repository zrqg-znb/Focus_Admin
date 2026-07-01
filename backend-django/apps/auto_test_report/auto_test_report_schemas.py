from datetime import date, datetime
from typing import List, Optional

from ninja import Field, Schema


class PlatformIn(Schema):
    name: str
    version_code: str
    domain: str = 'cockpit'
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
    viu_codes: List[str] = Field(default_factory=list)
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
    viu_codes: List[str] = Field(default_factory=list)


class TestCaseIn(Schema):
    vehicle_id: str
    viu_code: str = ''
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
    domain: Optional[str] = None
    platform_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    viu_code: Optional[str] = None
    keyword: Optional[str] = None
    is_active: Optional[bool] = None


class ImportCaseRow(Schema):
    viu_code: Optional[str] = None
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
    viu_code: str = ''
    case_no: str
    case_name: str
    remark: Optional[str] = None
    status: str
    failure_reason: Optional[str] = None
    failure_category: Optional[str] = None
    suggested_failure_reason: Optional[str] = None
    start_time: Optional[datetime] = None
    duration_seconds: int = 0
    log_url: Optional[str] = None
    car_log_url: Optional[str] = None
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
    missing_result_count: int = 0
    total_duration_seconds: int
    stats: List[SummaryStat]
    last_report_at: Optional[datetime] = None


class DailyHistoryRow(Schema):
    id: str
    execute_date: date
    viu_code: str = ''
    status: str
    failure_reason: Optional[str] = None
    failure_category: Optional[str] = None
    start_time: Optional[datetime] = None
    duration_seconds: int = 0
    log_url: Optional[str] = None
    car_log_url: Optional[str] = None
    reported_at: Optional[datetime] = None


class DailyHistoryPage(Schema):
    items: List[DailyHistoryRow]
    total: int
    page: int
    page_size: int


class ReportResultItemIn(Schema):
    viu_code: Optional[str] = None
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
    ignored_count: int = 0
    errors: List[ImportErrorRow] = Field(default_factory=list)


class DailyResultQuery(Schema):
    vehicle_id: str
    execute_date: date
    domain: Optional[str] = None


class DailyOverviewQuery(Schema):
    execute_date: date
    domain: Optional[str] = None
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
    non_version_failure_count: int = 0
    version_failure_count: int = 0
    uncategorized_failure_count: int = 0
    missing_result_count: int = 0
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
    non_version_failure_count: int = 0
    version_failure_count: int = 0
    uncategorized_failure_count: int = 0
    missing_result_count: int = 0
    downstream_trigger_enabled: bool = False
    downstream_trigger_block_reasons: List[str] = Field(default_factory=list)
    total_duration_seconds: int
    stats: List[SummaryStat]
    last_report_at: Optional[datetime] = None


class DailyOverviewResponse(Schema):
    items: List[DailyOverviewRow]
    summary: DailyOverviewSummary


class UpdateFailureReasonIn(Schema):
    failure_reason: Optional[str] = None
    failure_category: Optional[str] = None


class DownstreamTriggerIn(Schema):
    execute_date: date
    commit_id: str


class DownstreamTriggerOut(Schema):
    triggered: bool
    dry_run: bool = True
    message: str
    execute_date: date
    commit_id: Optional[str] = None
    commit_record_id: Optional[str] = None
    usage_id: Optional[str] = None
    vehicle_count: int = 0
    total_case_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    timeout_count: int = 0
    skip_count: int = 0
    non_version_failure_count: int = 0
    version_failure_count: int = 0
    uncategorized_failure_count: int = 0
    missing_result_count: int = 0
    block_reasons: List[str] = Field(default_factory=list)


class DownstreamCommitIn(Schema):
    commit_id: str


class DownstreamCommitOut(Schema):
    id: str
    commit_id: str
    first_uploaded_at: datetime
    last_uploaded_at: datetime
    upload_count: int
    last_used_at: Optional[datetime] = None
    use_count: int


class DownstreamCommitPage(Schema):
    items: List[DownstreamCommitOut]
    total: int
    page: int
    page_size: int


class DownstreamCommitUsageOut(Schema):
    id: str
    commit_id: str
    execute_date: date
    trigger_type: str
    trigger_user_name: str = ''
    success: bool
    dry_run: bool
    message: Optional[str] = None
    used_at: datetime


class DownstreamCommitUsagePage(Schema):
    items: List[DownstreamCommitUsageOut]
    total: int
    page: int
    page_size: int
