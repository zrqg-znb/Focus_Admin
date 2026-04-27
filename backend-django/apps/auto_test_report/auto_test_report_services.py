import io
from collections import Counter
from datetime import datetime
from typing import Optional

import openpyxl
from django.db import transaction
from django.db.models import F, OuterRef, Q, Subquery, Window
from django.db.models.functions import RowNumber
from django.http import HttpResponse
from ninja.errors import HttpError

from .auto_test_report_model import (
    DailyExecutionBatch,
    DailyExecutionResult,
    McuPlatform,
    TestCase,
    VehicleModel,
    RESULT_FAILED,
    RESULT_SUCCESS,
    RESULT_TIMEOUT,
    RESULT_SKIP,
)
from .auto_test_report_schemas import (
    DailyHistoryPage,
    DailyOverviewResponse,
    DailyOverviewRow,
    DailyOverviewSummary,
    DailyHistoryRow,
    DailyResultItemOut,
    DailySummaryOut,
    ImportErrorRow,
    ImportResultOut,
    SummaryStat,
)


RESULT_LABELS = {
    RESULT_SUCCESS: '成功',
    RESULT_FAILED: '失败',
    RESULT_TIMEOUT: '超时',
    RESULT_SKIP: '跳过',
}
MANUAL_REASON_RESULTS = {RESULT_FAILED, RESULT_TIMEOUT}


def _get_latest_result_order_by():
    return [
        F('start_time').desc(),
        F('reported_at').desc(),
        F('sys_create_datetime').desc(),
    ]


def build_latest_daily_results_queryset(
    *,
    execute_date=None,
    test_case_id: Optional[str] = None,
    vehicle: Optional[VehicleModel] = None,
    vehicle_id: Optional[str] = None,
):
    queryset = DailyExecutionResult.objects.filter(
        is_deleted=False,
        test_case__is_deleted=False,
        vehicle__is_deleted=False,
    )
    if vehicle is not None:
        queryset = queryset.filter(vehicle=vehicle)
    if vehicle_id:
        queryset = queryset.filter(vehicle_id=vehicle_id)
    if execute_date is not None:
        queryset = queryset.filter(execute_date=execute_date)
    if test_case_id:
        queryset = queryset.filter(test_case_id=test_case_id)
    return queryset.annotate(
        latest_rank=Window(
            expression=RowNumber(),
            partition_by=[F('vehicle_id'), F('execute_date'), F('test_case_id')],
            order_by=_get_latest_result_order_by(),
        ),
    ).filter(latest_rank=1)


def _apply_audit_fields(instance, user, *, is_create: bool = False):
    if not user:
        return
    if is_create and hasattr(instance, 'sys_creator'):
        instance.sys_creator = user
    if hasattr(instance, 'sys_modifier'):
        instance.sys_modifier = user


def _is_daily_overview_abnormal(batch: DailyExecutionBatch) -> bool:
    total_count = max(batch.total_count or 0, 0)
    success_count = max(batch.success_count or 0, 0)
    return not (total_count > 0 and success_count == total_count)


def list_platforms():
    queryset = McuPlatform.objects.filter(is_deleted=False).order_by('-sort', 'name')
    return [serialize_platform(item) for item in queryset]


def serialize_platform(item: McuPlatform):
    return {
        'id': str(item.id),
        'name': item.name,
        'version_code': item.version_code,
        'sort': item.sort,
        'is_active': item.is_active,
        'remark': item.remark,
        'vehicle_count': item.vehicles.filter(is_deleted=False).count(),
        'sys_create_datetime': item.sys_create_datetime,
        'sys_update_datetime': item.sys_update_datetime,
    }


def create_platform(user, payload):
    instance = McuPlatform(
        name=payload.name.strip(),
        version_code=payload.version_code.strip(),
        sort=payload.sort,
        is_active=payload.is_active,
        remark=(payload.remark or '').strip() or None,
    )
    _apply_audit_fields(instance, user, is_create=True)
    instance.save()
    return serialize_platform(instance)


def update_platform(user, platform_id: str, payload):
    instance = get_platform(platform_id)
    instance.name = payload.name.strip()
    instance.version_code = payload.version_code.strip()
    instance.sort = payload.sort
    instance.is_active = payload.is_active
    instance.remark = (payload.remark or '').strip() or None
    _apply_audit_fields(instance, user)
    instance.save()
    return serialize_platform(instance)


def delete_platform(platform_id: str):
    instance = get_platform(platform_id)
    if instance.vehicles.filter(is_deleted=False).exists():
        raise HttpError(400, '该平台下存在车型，无法删除')
    instance.soft_delete()
    return True


def get_platform(platform_id: str) -> McuPlatform:
    instance = McuPlatform.objects.filter(id=platform_id, is_deleted=False).first()
    if not instance:
        raise HttpError(404, '平台不存在')
    return instance


def list_vehicles(platform_id: Optional[str] = None, keyword: str = ''):
    queryset = VehicleModel.objects.select_related('platform').filter(is_deleted=False)
    if platform_id:
        queryset = queryset.filter(platform_id=platform_id)
    keyword = (keyword or '').strip()
    if keyword:
        queryset = queryset.filter(
            Q(name__icontains=keyword)
            | Q(vehicle_code__icontains=keyword)
            | Q(cdc_platform__icontains=keyword)
            | Q(execution_machine__icontains=keyword)
        )
    queryset = queryset.order_by('-sort', 'platform__sort', 'name')
    return [serialize_vehicle(item) for item in queryset]


def serialize_vehicle(item: VehicleModel):
    return {
        'id': str(item.id),
        'platform_id': str(item.platform_id),
        'platform_name': item.platform.name,
        'name': item.name,
        'vehicle_code': item.vehicle_code,
        'cdc_platform': item.cdc_platform,
        'execution_machine': item.execution_machine,
        'sort': item.sort,
        'is_active': item.is_active,
        'remark': item.remark,
        'sys_create_datetime': item.sys_create_datetime,
        'sys_update_datetime': item.sys_update_datetime,
    }


def list_vehicle_options():
    queryset = VehicleModel.objects.select_related('platform').filter(
        is_deleted=False,
        is_active=True,
        platform__is_deleted=False,
        platform__is_active=True,
    ).order_by('platform__sort', 'platform__name', 'name')
    return [
        {
            'id': str(item.id),
            'name': item.name,
            'vehicle_code': item.vehicle_code,
            'platform_id': str(item.platform_id),
            'platform_name': item.platform.name,
        }
        for item in queryset
    ]


def create_vehicle(user, payload):
    platform = get_platform(payload.platform_id)
    instance = VehicleModel(
        platform=platform,
        name=payload.name.strip(),
        vehicle_code=payload.vehicle_code.strip(),
        cdc_platform=payload.cdc_platform.strip(),
        execution_machine=payload.execution_machine.strip(),
        sort=payload.sort,
        is_active=payload.is_active,
        remark=(payload.remark or '').strip() or None,
    )
    _apply_audit_fields(instance, user, is_create=True)
    instance.save()
    return serialize_vehicle(instance)


def update_vehicle(user, vehicle_id: str, payload):
    instance = get_vehicle(vehicle_id)
    instance.platform = get_platform(payload.platform_id)
    instance.name = payload.name.strip()
    instance.vehicle_code = payload.vehicle_code.strip()
    instance.cdc_platform = payload.cdc_platform.strip()
    instance.execution_machine = payload.execution_machine.strip()
    instance.sort = payload.sort
    instance.is_active = payload.is_active
    instance.remark = (payload.remark or '').strip() or None
    _apply_audit_fields(instance, user)
    instance.save()
    return serialize_vehicle(instance)


def delete_vehicle(vehicle_id: str):
    instance = get_vehicle(vehicle_id)
    instance.soft_delete()
    return True


def get_vehicle(vehicle_id: str) -> VehicleModel:
    instance = VehicleModel.objects.select_related('platform').filter(id=vehicle_id, is_deleted=False).first()
    if not instance:
        raise HttpError(404, '车型不存在')
    return instance


def list_test_cases(filters):
    latest_execute_time_subquery = (
        DailyExecutionResult.objects.filter(
            test_case_id=OuterRef('pk'),
            is_deleted=False,
        )
        .order_by(
            '-execute_date',
            '-start_time',
            '-reported_at',
            '-sys_create_datetime',
        )
        .values('start_time')[:1]
    )
    queryset = (
        TestCase.objects.select_related('vehicle', 'vehicle__platform')
        .filter(is_deleted=False, vehicle__is_deleted=False)
        .annotate(latest_execute_time=Subquery(latest_execute_time_subquery))
    )
    if filters.platform_id:
        queryset = queryset.filter(vehicle__platform_id=filters.platform_id)
    if filters.vehicle_id:
        queryset = queryset.filter(vehicle_id=filters.vehicle_id)
    if filters.is_active is not None:
        queryset = queryset.filter(is_active=filters.is_active)
    keyword = (filters.keyword or '').strip()
    if keyword:
        queryset = queryset.filter(
            Q(case_no__icontains=keyword)
            | Q(case_name__icontains=keyword)
            | Q(remark__icontains=keyword)
        )
    queryset = queryset.order_by('-sort', 'case_no')
    return [serialize_test_case(item) for item in queryset]


def serialize_test_case(item: TestCase):
    latest_execute_time = getattr(item, 'latest_execute_time', None)
    if latest_execute_time is None:
        latest_result = (
            item.daily_results.filter(is_deleted=False)
            .order_by(
                '-execute_date',
                '-start_time',
                '-reported_at',
                '-sys_create_datetime',
            )
            .first()
        )
        latest_execute_time = latest_result.start_time if latest_result else None
    return {
        'id': str(item.id),
        'vehicle_id': str(item.vehicle_id),
        'vehicle_name': item.vehicle.name,
        'vehicle_code': item.vehicle.vehicle_code,
        'platform_name': item.vehicle.platform.name,
        'case_no': item.case_no,
        'case_name': item.case_name,
        'remark': item.remark,
        'sort': item.sort,
        'is_active': item.is_active,
        'latest_execute_time': latest_execute_time,
        'sys_create_datetime': item.sys_create_datetime,
        'sys_update_datetime': item.sys_update_datetime,
    }


def create_test_case(user, payload):
    vehicle = get_vehicle(payload.vehicle_id)
    instance = TestCase(
        vehicle=vehicle,
        case_no=payload.case_no.strip(),
        case_name=payload.case_name.strip(),
        remark=(payload.remark or '').strip() or None,
        sort=payload.sort,
        is_active=payload.is_active,
    )
    _apply_audit_fields(instance, user, is_create=True)
    instance.save()
    return serialize_test_case(instance)


def update_test_case(user, case_id: str, payload):
    instance = get_test_case(case_id)
    instance.vehicle = get_vehicle(payload.vehicle_id)
    instance.case_no = payload.case_no.strip()
    instance.case_name = payload.case_name.strip()
    instance.remark = (payload.remark or '').strip() or None
    instance.sort = payload.sort
    instance.is_active = payload.is_active
    _apply_audit_fields(instance, user)
    instance.save()
    return serialize_test_case(instance)


def update_test_case_remark(user, case_id: str, remark: Optional[str]):
    instance = get_test_case(case_id)
    instance.remark = (remark or '').strip() or None
    _apply_audit_fields(instance, user)
    instance.save()
    return serialize_test_case(instance)


def delete_test_case(case_id: str):
    instance = get_test_case(case_id)
    instance.soft_delete()
    return True


def batch_delete_test_cases(case_ids):
    queryset = TestCase.objects.filter(id__in=case_ids, is_deleted=False)
    count = 0
    for item in queryset:
        item.soft_delete()
        count += 1
    return count


def get_test_case(case_id: str) -> TestCase:
    instance = TestCase.objects.select_related('vehicle', 'vehicle__platform').filter(id=case_id, is_deleted=False).first()
    if not instance:
        raise HttpError(404, '测试用例不存在')
    return instance


@transaction.atomic
def import_test_cases(user, payload) -> ImportResultOut:
    vehicle = get_vehicle(payload.vehicle_id)
    created_count = 0
    updated_count = 0
    ignored_count = 0
    errors = []
    seen_case_nos = set()

    for index, row in enumerate(payload.rows, start=1):
        case_no = (row.case_no or '').strip()
        case_name = (row.case_name or '').strip()
        remark = (row.remark or '').strip() or None
        if not case_no:
            errors.append(ImportErrorRow(row_no=index, message='用例编号不能为空'))
            continue
        if not case_name:
            errors.append(ImportErrorRow(row_no=index, message='用例名称不能为空'))
            continue
        if case_no in seen_case_nos:
            errors.append(ImportErrorRow(row_no=index, message='Excel 内用例编号重复'))
            continue
        seen_case_nos.add(case_no)

        instance = TestCase.objects.filter(vehicle=vehicle, case_no=case_no, is_deleted=False).first()
        if not instance:
            instance = TestCase(
                vehicle=vehicle,
                case_no=case_no,
                case_name=case_name,
                remark=remark,
                is_active=True,
            )
            _apply_audit_fields(instance, user, is_create=True)
            instance.save()
            created_count += 1
            continue
        if instance.case_name != case_name or instance.remark != remark:
            instance.case_name = case_name
            instance.remark = remark
            _apply_audit_fields(instance, user)
            instance.save(update_fields=['case_name', 'remark', 'sys_modifier', 'sys_update_datetime'])
            updated_count += 1
        else:
            ignored_count += 1

    return ImportResultOut(
        created_count=created_count,
        updated_count=updated_count,
        ignored_count=ignored_count,
        errors=errors,
    )


def parse_excel_rows(file_obj) -> list[dict]:
    try:
        content = file_obj.read()
        workbook = openpyxl.load_workbook(
            filename=io.BytesIO(content),
            read_only=True,
            data_only=True,
        )
    except Exception as exc:
        raise HttpError(400, f'Excel 解析失败: {exc}')

    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise HttpError(400, 'Excel 内容为空')

    header = [str(item or '').strip() for item in rows[0]]
    try:
        case_no_index = header.index('用例编号')
        case_name_index = header.index('用例名称')
    except ValueError:
        raise HttpError(400, 'Excel 模板缺少必填列：用例编号、用例名称')
    remark_index = header.index('备注') if '备注' in header else None

    parsed_rows = []
    for row in rows[1:]:
        if not row:
            continue
        case_no = str(row[case_no_index] or '').strip()
        case_name = str(row[case_name_index] or '').strip()
        if not case_no and not case_name:
            continue
        parsed_rows.append({
            'case_no': case_no,
            'case_name': case_name,
            'remark': str(row[remark_index] or '').strip() if remark_index is not None else '',
        })
    return parsed_rows


def build_test_case_template_response():
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = '测试用例模板'
    sheet.append(['用例编号', '用例名称', '备注'])
    sheet.append(['CASE-001', '示例自动化用例', '固定备注示例'])
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = (
        "attachment; filename*=UTF-8''auto_test_case_template.xlsx"
    )
    workbook.save(response)
    return response


def build_test_case_export_response(filters):
    rows = list_test_cases(filters)
    workbook = openpyxl.Workbook(write_only=True)
    sheet = workbook.create_sheet('测试用例')
    sheet.append([
        'MCU平台',
        '车型',
        '车型编号',
        '用例编号',
        '用例名称',
        '备注',
        '最近执行时间',
        '更新时间',
    ])
    for item in rows:
        sheet.append([
            item['platform_name'],
            item['vehicle_name'],
            item['vehicle_code'],
            item['case_no'],
            item['case_name'],
            item.get('remark') or '',
            item.get('latest_execute_time') or '',
            item.get('sys_update_datetime') or '',
        ])
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = (
        "attachment; filename*=UTF-8''auto_test_cases.xlsx"
    )
    workbook.save(response)
    return response


@transaction.atomic
def report_daily_results(payload):
    vehicle = VehicleModel.objects.filter(
        vehicle_code=payload.vehicle_code,
        is_deleted=False,
        is_active=True,
    ).first()
    if not vehicle:
        raise HttpError(404, '车型不存在')

    active_cases = {
        item.case_no: item
        for item in TestCase.objects.filter(vehicle=vehicle, is_deleted=False, is_active=True)
    }
    if not active_cases:
        raise HttpError(400, '该车型下未配置有效测试用例')

    created_count = 0
    now = datetime.now()
    for item in payload.results:
        case_no = (item.case_no or '').strip()
        test_case = active_cases.get(case_no)
        if not test_case:
            raise HttpError(400, f'未找到用例编号: {case_no}')
        DailyExecutionResult.objects.create(
            vehicle=vehicle,
            execute_date=payload.execute_date,
            test_case=test_case,
            start_time=item.start_time,
            duration_seconds=max(int(item.duration_seconds or 0), 0),
            result=item.result,
            failure_reason=None,
            log_url=(item.log_url or '').strip() or None,
        )
        created_count += 1

    recalculate_daily_batch(vehicle.id, payload.execute_date, now)
    return {
        'vehicle_id': str(vehicle.id),
        'execute_date': payload.execute_date,
        'created_count': created_count,
        'updated_count': created_count,
    }


def recalculate_daily_batch(vehicle_id: str, execute_date, last_report_at=None):
    vehicle = get_vehicle(vehicle_id)
    all_case_count = TestCase.objects.filter(vehicle=vehicle, is_deleted=False, is_active=True).count()
    results = list(build_latest_daily_results_queryset(vehicle=vehicle, execute_date=execute_date))
    counter = Counter(item.result for item in results)
    total_duration_seconds = sum(max(item.duration_seconds or 0, 0) for item in results)
    skip_count = max(all_case_count - len(results), 0)

    batch, _ = DailyExecutionBatch.objects.get_or_create(
        vehicle=vehicle,
        execute_date=execute_date,
    )
    batch.total_count = all_case_count
    batch.success_count = counter.get(RESULT_SUCCESS, 0)
    batch.failed_count = counter.get(RESULT_FAILED, 0)
    batch.timeout_count = counter.get(RESULT_TIMEOUT, 0)
    batch.skip_count = skip_count
    batch.total_duration_seconds = total_duration_seconds
    if last_report_at is not None:
        batch.last_report_at = last_report_at
    batch.save()
    return batch


def get_suggested_failure_reason(vehicle_id: str, test_case_id: str, execute_date):
    item = (
        DailyExecutionResult.objects.filter(
            vehicle_id=vehicle_id,
            test_case_id=test_case_id,
            is_deleted=False,
            result__in=list(MANUAL_REASON_RESULTS),
        )
        .exclude(execute_date=execute_date)
        .exclude(failure_reason__isnull=True)
        .exclude(failure_reason__exact='')
        .order_by(
            '-execute_date',
            '-start_time',
            '-reported_at',
            '-sys_create_datetime',
        )
        .first()
    )
    return item.failure_reason if item else None


def get_daily_summary(vehicle_id: str, execute_date) -> DailySummaryOut:
    vehicle = get_vehicle(vehicle_id)
    batch = recalculate_daily_batch(vehicle.id, execute_date)
    total = max(batch.total_count, 0)

    def stat(key, count):
        ratio = round((count / total), 4) if total else 0
        return SummaryStat(key=key, label=RESULT_LABELS[key], count=count, ratio=ratio)

    return DailySummaryOut(
        vehicle_id=str(vehicle.id),
        vehicle_name=vehicle.name,
        vehicle_code=vehicle.vehicle_code,
        execute_date=execute_date,
        total_count=batch.total_count,
        success_count=batch.success_count,
        failed_count=batch.failed_count,
        timeout_count=batch.timeout_count,
        skip_count=batch.skip_count,
        total_duration_seconds=batch.total_duration_seconds,
        stats=[
            stat(RESULT_SUCCESS, batch.success_count),
            stat(RESULT_FAILED, batch.failed_count),
            stat(RESULT_TIMEOUT, batch.timeout_count),
            stat(RESULT_SKIP, batch.skip_count),
        ],
        last_report_at=batch.last_report_at,
    )


def get_daily_overview(query) -> DailyOverviewResponse:
    vehicles = VehicleModel.objects.select_related('platform').filter(
        is_deleted=False,
        is_active=True,
        platform__is_deleted=False,
        platform__is_active=True,
    )
    if query.platform_id:
        vehicles = vehicles.filter(platform_id=query.platform_id)

    rows: list[DailyOverviewRow] = []
    total_case_count = 0
    success_count = 0
    failed_count = 0
    timeout_count = 0
    skip_count = 0
    total_duration_seconds = 0
    abnormal_vehicle_count = 0
    latest_report_at = None

    for vehicle in vehicles:
        batch = recalculate_daily_batch(vehicle.id, query.execute_date)
        is_abnormal = _is_daily_overview_abnormal(batch)
        if query.abnormal_only and not is_abnormal:
            continue

        row = DailyOverviewRow(
            vehicle_id=str(vehicle.id),
            vehicle_name=vehicle.name,
            vehicle_code=vehicle.vehicle_code,
            platform_id=str(vehicle.platform_id),
            platform_name=vehicle.platform.name,
            total_count=batch.total_count,
            success_count=batch.success_count,
            failed_count=batch.failed_count,
            timeout_count=batch.timeout_count,
            skip_count=batch.skip_count,
            total_duration_seconds=batch.total_duration_seconds,
            last_report_at=batch.last_report_at,
            is_abnormal=is_abnormal,
        )
        rows.append(row)
        total_case_count += batch.total_count
        success_count += batch.success_count
        failed_count += batch.failed_count
        timeout_count += batch.timeout_count
        skip_count += batch.skip_count
        total_duration_seconds += batch.total_duration_seconds
        abnormal_vehicle_count += int(is_abnormal)
        if batch.last_report_at and (
            latest_report_at is None or batch.last_report_at > latest_report_at
        ):
            latest_report_at = batch.last_report_at

    rows.sort(
        key=lambda item: (
            0 if item.is_abnormal else 1,
            -item.failed_count,
            -item.timeout_count,
            item.vehicle_name,
        )
    )

    visible_vehicle_count = len(rows)

    def stat(key, count):
        ratio = round((count / total_case_count), 4) if total_case_count else 0
        return SummaryStat(key=key, label=RESULT_LABELS[key], count=count, ratio=ratio)

    summary = DailyOverviewSummary(
        execute_date=query.execute_date,
        vehicle_count=visible_vehicle_count,
        abnormal_vehicle_count=abnormal_vehicle_count,
        total_case_count=total_case_count,
        success_count=success_count,
        failed_count=failed_count,
        timeout_count=timeout_count,
        skip_count=skip_count,
        total_duration_seconds=total_duration_seconds,
        stats=[
            stat(RESULT_SUCCESS, success_count),
            stat(RESULT_FAILED, failed_count),
            stat(RESULT_TIMEOUT, timeout_count),
            stat(RESULT_SKIP, skip_count),
        ],
        last_report_at=latest_report_at,
    )
    return DailyOverviewResponse(items=rows, summary=summary)


def list_daily_results(vehicle_id: str, execute_date):
    vehicle = get_vehicle(vehicle_id)
    cases = list(
        TestCase.objects.filter(vehicle=vehicle, is_deleted=False, is_active=True).order_by('-sort', 'case_no')
    )
    result_map = {
        item.test_case_id: item
        for item in build_latest_daily_results_queryset(
            vehicle=vehicle,
            execute_date=execute_date,
        ).select_related('test_case')
    }
    items = []
    for case in cases:
        result = result_map.get(case.id)
        items.append(
            DailyResultItemOut(
                result_id=str(result.id) if result else None,
                case_id=str(case.id),
                case_no=case.case_no,
                case_name=case.case_name,
                remark=case.remark,
                status=result.result if result else RESULT_SKIP,
                failure_reason=result.failure_reason if result else None,
                suggested_failure_reason=(
                    get_suggested_failure_reason(str(vehicle.id), str(case.id), execute_date)
                    if result and result.result in MANUAL_REASON_RESULTS and not result.failure_reason
                    else None
                ),
                start_time=result.start_time if result else None,
                duration_seconds=result.duration_seconds if result else 0,
                log_url=result.log_url if result else None,
                reported_at=result.reported_at if result else None,
            )
        )
    return items


def update_daily_result_failure_reason(user, result_id: str, failure_reason: Optional[str]):
    instance = DailyExecutionResult.objects.filter(id=result_id, is_deleted=False).first()
    if not instance:
        raise HttpError(404, '执行结果不存在')
    if instance.result not in MANUAL_REASON_RESULTS:
        raise HttpError(400, '仅失败或超时结果支持填写异常原因')
    instance.failure_reason = (failure_reason or '').strip() or None
    _apply_audit_fields(instance, user)
    instance.save()
    return True


def get_test_case_history(case_id: str, page: int = 1, page_size: int = 10) -> DailyHistoryPage:
    test_case = get_test_case(case_id)
    queryset = DailyExecutionResult.objects.filter(
        test_case=test_case,
        vehicle_id=test_case.vehicle_id,
        is_deleted=False,
    ).order_by(
        '-execute_date',
        '-start_time',
        '-reported_at',
        '-sys_create_datetime',
    )
    total = queryset.count()
    start = max(page - 1, 0) * page_size
    rows = [
        DailyHistoryRow(
            id=str(item.id),
            execute_date=item.execute_date,
            status=item.result,
            failure_reason=item.failure_reason,
            start_time=item.start_time,
            duration_seconds=item.duration_seconds,
            log_url=item.log_url,
            reported_at=item.reported_at,
        )
        for item in queryset[start:start + page_size]
    ]
    return DailyHistoryPage(items=rows, total=total, page=page, page_size=page_size)
