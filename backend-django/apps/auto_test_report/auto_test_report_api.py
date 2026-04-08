from typing import List

from ninja import File, Form, Router, Query, Schema
from ninja.files import UploadedFile

from common.fu_auth import BearerAuth as GlobalAuth

from .auto_test_report_schemas import (
    DailyHistoryPage,
    DailyResultItemOut,
    DailyResultQuery,
    DailySummaryOut,
    ImportCasePayload,
    ImportResultOut,
    PlatformIn,
    PlatformOut,
    ReportDailyResultsIn,
    ReportDailyResultsOut,
    TestCaseFilter,
    TestCaseIn,
    TestCaseOut,
    VehicleIn,
    VehicleOption,
    VehicleOut,
)
from . import auto_test_report_services as services


router = Router(tags=['AutoTestReport'], auth=GlobalAuth())
report_router = Router(tags=['AutoTestReporter'])


class VehicleListQuery(Schema):
    platform_id: str = ''
    keyword: str = ''


class BatchDeleteIn(Schema):
    ids: List[str]


@router.get('/platforms', response=List[PlatformOut], summary='平台列表')
def list_platforms(request):
    return services.list_platforms()


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
    return services.list_vehicles(filters.platform_id, filters.keyword)


@router.get('/vehicle-options', response=List[VehicleOption], summary='车型选项')
def list_vehicle_options(request):
    return services.list_vehicle_options()


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
    rows = services.parse_excel_rows(file)
    payload = ImportCasePayload(vehicle_id=vehicle_id, rows=rows)
    return services.import_test_cases(request.auth, payload)


@router.get('/test-cases/template', summary='下载测试用例导入模板')
def download_test_case_template(request):
    return services.build_test_case_template_response()


@router.get('/test-cases/export', summary='导出测试用例')
def export_test_cases(request, filters: TestCaseFilter = Query(...)):
    return services.build_test_case_export_response(filters)


@router.put('/test-cases/{case_id}', response=TestCaseOut, summary='更新测试用例')
def update_test_case(request, case_id: str, payload: TestCaseIn):
    return services.update_test_case(request.auth, case_id, payload)


@router.delete('/test-cases/{case_id}', response=bool, summary='删除测试用例')
def delete_test_case(request, case_id: str):
    return services.delete_test_case(case_id)


@router.get('/daily-results/summary', response=DailySummaryOut, summary='每日执行汇总')
def get_daily_summary(request, query: DailyResultQuery = Query(...)):
    return services.get_daily_summary(query.vehicle_id, query.execute_date)


@router.get('/daily-results/list', response=List[DailyResultItemOut], summary='每日执行结果列表')
def list_daily_results(request, query: DailyResultQuery = Query(...)):
    return services.list_daily_results(query.vehicle_id, query.execute_date)


@router.get('/test-cases/{case_id}/history', response=DailyHistoryPage, summary='测试用例历史执行')
def get_test_case_history(request, case_id: str, page: int = 1, pageSize: int = 10):
    return services.get_test_case_history(case_id, page=page, page_size=pageSize)


@report_router.post('/daily-results', response=ReportDailyResultsOut, summary='测试环境上报每日执行结果')
def report_daily_results(request, payload: ReportDailyResultsIn):
    return services.report_daily_results(payload)
