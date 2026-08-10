from typing import List

from ninja import File, Form, Router, Query, Schema
from ninja.files import UploadedFile

from common.fu_auth import BearerAuth as GlobalAuth

from .auto_test_report_schemas import (
    DownstreamCommitIn,
    DownstreamCommitOut,
    DownstreamCommitPage,
    DownstreamCommitUsagePage,
    DailyHistoryPage,
    DailyAnalysisStatsQuery,
    DailyAnalysisStatsResponse,
    DailyOverviewQuery,
    DailyOverviewResponse,
    DailyResultItemOut,
    DailyResultQuery,
    DailySummaryOut,
    DownstreamTriggerIn,
    DownstreamTriggerOut,
    ImportCasePayload,
    ImportResultOut,
    PlatformIn,
    PlatformOut,
    ReportDailyResultsIn,
    ReportDailyResultsOut,
    TestCaseFilter,
    TestCaseIn,
    TestCaseOut,
    UpdateFailureReasonIn,
    UpdateTestCaseRemarkIn,
    VehicleIn,
    VehicleOption,
    VehicleOut,
)
from . import auto_test_report_services as services


router = Router(tags=['AutoTestReport'], auth=GlobalAuth())
report_router = Router(tags=['AutoTestReporter'])


class VehicleListQuery(Schema):
    domain: str = ''
    platform_id: str = ''
    keyword: str = ''


class BatchDeleteIn(Schema):
    ids: List[str]


@router.get('/platforms', response=List[PlatformOut], summary='平台列表')
def list_platforms(request, domain: str = Query('')):
    return services.list_platforms(domain)


@router.post('/platforms', response=PlatformOut, summary='新建平台')
def create_platform(request, payload: PlatformIn):
    return services.create_platform(request.auth, payload)


@router.put('/platforms/{platform_id}', response=PlatformOut, summary='更新平台')
def update_platform(request, platform_id: str, payload: PlatformIn):
    return services.update_platform(request.auth, platform_id, payload)


@router.delete('/platforms/{platform_id}', response=bool, summary='删除平台')
def delete_platform(request, platform_id: str):
    return services.delete_platform(platform_id)


@router.get('/vehicles', response=List[VehicleOut], summary='车型列表')
def list_vehicles(request, filters: VehicleListQuery = Query(...)):
    return services.list_vehicles(filters.domain, filters.platform_id, filters.keyword)


@router.get('/vehicle-options', response=List[VehicleOption], summary='车型选项')
def list_vehicle_options(request, domain: str = Query('')):
    return services.list_vehicle_options(domain)


@router.post('/vehicles', response=VehicleOut, summary='新建车型')
def create_vehicle(request, payload: VehicleIn):
    return services.create_vehicle(request.auth, payload)


@router.put('/vehicles/{vehicle_id}', response=VehicleOut, summary='更新车型')
def update_vehicle(request, vehicle_id: str, payload: VehicleIn):
    return services.update_vehicle(request.auth, vehicle_id, payload)


@router.delete('/vehicles/{vehicle_id}', response=bool, summary='删除车型')
def delete_vehicle(request, vehicle_id: str):
    return services.delete_vehicle(vehicle_id)


@router.get('/test-cases', response=List[TestCaseOut], summary='测试用例列表')
def list_test_cases(request, filters: TestCaseFilter = Query(...)):
    return services.list_test_cases(filters)


@router.post('/test-cases', response=TestCaseOut, summary='新建测试用例')
def create_test_case(request, payload: TestCaseIn):
    return services.create_test_case(request.auth, payload)


@router.post('/test-cases/batch-delete', response=int, summary='批量删除测试用例')
def batch_delete_test_cases(request, payload: BatchDeleteIn):
    return services.batch_delete_test_cases(payload.ids)


@router.post('/test-cases/import', response=ImportResultOut, summary='导入测试用例')
def import_test_cases(request, payload: ImportCasePayload):
    return services.import_test_cases(request.auth, payload)


@router.post('/test-cases/import-excel', response=ImportResultOut, summary='Excel导入测试用例')
def import_test_cases_excel(
    request,
    vehicle_id: str = Form(...),
    file: UploadedFile = File(...),
):
    vehicle = services.get_vehicle(vehicle_id)
    rows = services.parse_excel_rows(
        file,
        require_module=vehicle.platform.domain == services.DOMAIN_COCKPIT_SOC,
        require_viu_code=vehicle.platform.domain == services.DOMAIN_VEHICLE,
    )
    payload = ImportCasePayload(vehicle_id=vehicle_id, rows=rows)
    return services.import_test_cases(request.auth, payload)


@router.post(
    '/test-cases/import-full-excel',
    response=ImportResultOut,
    summary='Excel批量导入平台车型和用例',
)
def import_full_test_cases_excel(
    request,
    domain: str = Form(...),
    file: UploadedFile = File(...),
):
    """按领域从单个 Excel 批量维护平台、车型和用例。"""
    return services.import_full_test_case_excel(request.auth, domain, file)


@router.get('/test-cases/template', summary='下载测试用例导入模板')
def download_test_case_template(request, domain: str = Query('')):
    """下载包含平台、车型和用例字段的一站式导入模板。"""
    return services.build_test_case_template_response(domain)


@router.get('/test-cases/export', summary='导出测试用例')
def export_test_cases(request, filters: TestCaseFilter = Query(...)):
    return services.build_test_case_export_response(filters)


@router.put('/test-cases/{case_id}', response=TestCaseOut, summary='更新测试用例')
def update_test_case(request, case_id: str, payload: TestCaseIn):
    return services.update_test_case(request.auth, case_id, payload)


@router.patch('/test-cases/{case_id}/remark', response=TestCaseOut, summary='更新测试用例备注')
def update_test_case_remark(request, case_id: str, payload: UpdateTestCaseRemarkIn):
    return services.update_test_case_remark(request.auth, case_id, payload.remark)


@router.delete('/test-cases/{case_id}', response=bool, summary='删除测试用例')
def delete_test_case(request, case_id: str):
    return services.delete_test_case(case_id)


@router.get('/daily-results/summary', response=DailySummaryOut, summary='每日执行汇总')
def get_daily_summary(request, query: DailyResultQuery = Query(...)):
    return services.get_daily_summary(query.vehicle_id, query.execute_date, query.domain)


@router.get('/daily-results/overview', response=DailyOverviewResponse, summary='全量每日执行概览')
def get_daily_overview(request, query: DailyOverviewQuery = Query(...)):
    """查询每日全量概览，并返回座舱下游触发门禁摘要。"""
    return services.get_daily_overview(query)


@router.get(
    '/daily-results/analysis-stats',
    response=DailyAnalysisStatsResponse,
    summary='第三方获取失败分析统计',
    auth=None,
)
def get_daily_analysis_stats(request, query: DailyAnalysisStatsQuery = Query(...)):
    """供受控第三方按领域获取当天或指定日期的车型失败分析统计，无需认证。"""
    return services.get_daily_analysis_stats(query.domain, query.execute_date)


@router.get('/daily-results/list', response=List[DailyResultItemOut], summary='每日执行结果列表')
def list_daily_results(request, query: DailyResultQuery = Query(...)):
    return services.list_daily_results(query.vehicle_id, query.execute_date, query.domain)


@router.patch('/daily-results/{result_id}/failure-reason', response=bool, summary='更新异常原因')
def update_daily_result_failure_reason(request, result_id: str, payload: UpdateFailureReasonIn):
    """更新非成功结果的异常原因和失败根因大类。"""
    return services.update_daily_result_failure_reason(
        request.auth,
        result_id,
        payload.failure_reason,
        payload.failure_category,
    )


@router.post('/daily-results/downstream-trigger', response=DownstreamTriggerOut, summary='触发座舱下游任务')
def trigger_cockpit_downstream(request, payload: DownstreamTriggerIn):
    """人工触发座舱下游任务，后端会强制校验放行条件和 commit-id。"""
    return services.trigger_cockpit_downstream(request.auth, payload.execute_date, payload.commit_id)


@router.get('/downstream-commits', response=DownstreamCommitPage, summary='Commit ID历史列表')
def list_downstream_commits(
    request,
    keyword: str = Query(''),
    uploaded_start: str = Query(''),
    uploaded_end: str = Query(''),
    page: int = Query(1),
    pageSize: int = Query(20),
):
    """分页查询 CI 上报的 commit-id 历史。"""
    return services.list_downstream_commits(
        keyword=keyword,
        uploaded_start=uploaded_start,
        uploaded_end=uploaded_end,
        page=page,
        page_size=pageSize,
    )


@router.get(
    '/downstream-commits/{commit_record_id}/usages',
    response=DownstreamCommitUsagePage,
    summary='Commit ID使用记录',
)
def list_downstream_commit_usages(
    request,
    commit_record_id: str,
    page: int = Query(1),
    pageSize: int = Query(10),
):
    """分页查询某个 commit-id 的下游触发使用记录。"""
    return services.list_downstream_commit_usages(commit_record_id, page=page, page_size=pageSize)


@router.get('/test-cases/{case_id}/history', response=DailyHistoryPage, summary='测试用例历史执行')
def get_test_case_history(request, case_id: str, page: int = 1, pageSize: int = 10):
    return services.get_test_case_history(case_id, page=page, page_size=pageSize)


@report_router.post('/daily-results', response=ReportDailyResultsOut, summary='测试环境上报每日执行结果')
def report_daily_results(request, payload: ReportDailyResultsIn):
    return services.report_daily_results(payload)


@report_router.post('/commit-ids', response=DownstreamCommitOut, summary='CI上报Commit ID')
def report_downstream_commit(request, payload: DownstreamCommitIn):
    """接收 CI 构建侧上报的 commit-id，重复上传会自动去重计数。"""
    return services.report_downstream_commit(payload)
