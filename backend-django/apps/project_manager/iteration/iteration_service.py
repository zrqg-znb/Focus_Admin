from urllib.parse import quote

import openpyxl
from django.db import transaction
from django.http import Http404, HttpResponse
from django.utils import timezone

from common import fu_crud
from apps.project_manager.code_quality.code_quality_model import CodeModule
from apps.project_manager.project.project_model import Project

from .iteration_model import Iteration, IterationMetric
from .iteration_schema import (
    IterationCreateSchema,
    IterationDashboardSchema,
    IterationDetailSchema,
    IterationManualUpdateSchema,
    IterationMetricOut,
    IterationMetricSchema,
)
from .iteration_sync import get_cached_iteration_requirements, sync_project_iterations


_ENTRY_METRIC_HEADERS = (
    "迭代名称",
    "编码",
    "开始时间",
    "结束时间",
    "当前迭代",
    "健康状态",
    "DR分解率",
    "SR分解率",
)
_EXIT_METRIC_HEADERS = (
    "迭代名称",
    "编码",
    "DR置A率",
    "AR置A率",
    "DR置C率",
    "AR置C率",
    "测试自动化率",
    "用例执行率",
    "缺陷修复率",
    "代码评审率",
    "代码覆盖率",
)
_REQUIREMENT_EXPORT_HEADERS = (
    "需求ID",
    "需求标题",
    "需求类型",
    "IDPCA状态",
    "责任团队",
    "开发责任人",
    "需分解",
    "已分解",
    "人力工作量已填",
    "代码量已填",
)

@transaction.atomic
def create_iteration(request, data: IterationCreateSchema):
    data_dict = data.dict()
    
    # 互斥逻辑
    if data_dict.get('is_current'):
        Iteration.objects.filter(
            project_id=data_dict['project_id'], 
            is_current=True
        ).update(is_current=False)
        
    return fu_crud.create(request, data_dict, Iteration)

def _calculate_rates(metric: IterationMetric) -> dict:
    """计算迭代详情页展示和导出复用的比例指标。"""
    if not metric:
        return {}
    
    # SR Decomposition Rate
    sr_total = metric.need_break_sr_num
    sr_unbroken = metric.need_break_but_un_break_sr_num
    sr_breakdown_rate = (sr_total - sr_unbroken) / sr_total if sr_total > 0 else 0.0
    
    # DR Decomposition Rate
    dr_total = metric.need_break_dr_num
    dr_unbroken = metric.need_break_but_un_break_dr_num
    dr_breakdown_rate = (dr_total - dr_unbroken) / dr_total if dr_total > 0 else 0.0
    
    # AR Set A Rate
    ar_total = metric.ar_num
    ar_set_a_rate = metric.a_state_ar_num / ar_total if ar_total > 0 else 0.0
    
    # DR Set A Rate
    dr_total = metric.dr_num
    dr_set_a_rate = metric.a_state_dr_num / dr_total if dr_total > 0 else 0.0
    
    # AR Set C Rate (C + A)
    ar_set_c_rate = (metric.c_state_ar_num + metric.a_state_ar_num) / ar_total if ar_total > 0 else 0.0
    
    # DR Set C Rate (C + A)
    dr_set_c_rate = (metric.c_state_dr_num + metric.a_state_dr_num) / dr_total if dr_total > 0 else 0.0
    
    return {
        "sr_breakdown_rate": sr_breakdown_rate,
        "dr_breakdown_rate": dr_breakdown_rate,
        "ar_set_a_rate": ar_set_a_rate,
        "dr_set_a_rate": dr_set_a_rate,
        "ar_set_c_rate": ar_set_c_rate,
        "dr_set_c_rate": dr_set_c_rate,
        "sr_num": metric.sr_num,
        "dr_num": metric.dr_num,
        "ar_num": metric.ar_num,
        "test_automation_rate": metric.test_automation_rate,
        "test_case_execution_rate": metric.test_case_execution_rate,
        "bug_fix_rate": metric.bug_fix_rate,
        "code_review_rate": metric.code_review_rate,
        "code_coverage_rate": metric.code_coverage_rate,
    }


def _to_float(value) -> float | None:
    """把外部接口可能返回的数字或百分比文本转成浮点数。"""
    if value is None:
        return None

    if isinstance(value, (float, int)):
        return float(value)

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("%"):
            text = text[:-1]
        try:
            return float(text)
        except Exception:
            return None

    return None


def _normalize_ratio(value) -> float:
    """把 0-1 或 0-100 口径统一归一成 0-1 比例。"""
    parsed = _to_float(value)
    if parsed is None:
        return 0.0

    ratio = parsed / 100 if parsed > 1 else parsed
    if ratio < 0:
        return 0.0
    if ratio > 1:
        return 1.0
    return ratio


def _extract_summary_ratio(summary_metrics: dict, metric_key: str) -> float:
    """从代码质量摘要中抽取指定指标比例。"""
    metric_payload = summary_metrics.get(metric_key)
    if isinstance(metric_payload, dict):
        parsed_value = _to_float(metric_payload.get("num"))
        if parsed_value is None:
            parsed_value = _to_float(metric_payload.get("display"))
        return _normalize_ratio(parsed_value)

    return _normalize_ratio(metric_payload)


def _get_iteration_quality_metrics(project: Project) -> dict:
    """读取项目配置的代码质量出口指标。"""
    if not project.enable_iteration_quality_metrics:
        return {}

    oem_name = str(project.iteration_quality_oem_name or "").strip()
    module_name = str(project.iteration_quality_module or "").strip()
    if not oem_name or not module_name:
        return {}

    module = (
        CodeModule.objects.filter(
            project=project,
            oem_name=oem_name,
            module=module_name,
            is_deleted=False,
        )
        .order_by("-sys_create_datetime")
        .first()
    )
    if not module:
        return {}

    latest_metric = (
        module.metrics.filter(is_deleted=False)
        .order_by("-record_date", "-sys_create_datetime")
        .first()
    )
    if not latest_metric:
        return {}

    summary_metrics = latest_metric.summary_metrics
    if not isinstance(summary_metrics, dict):
        summary_metrics = {}

    return {
        "quality_ut_file_coverage_rate": _extract_summary_ratio(
            summary_metrics,
            "UT_file_coverage",
        ),
        "quality_ut_line_coverage_rate": _extract_summary_ratio(
            summary_metrics,
            "UT_line_coverage",
        ),
        "quality_clean_code_rate": _normalize_ratio(latest_metric.clean_code_rate),
    }


def get_iteration_dashboard():
    projects = Project.objects.filter(
        is_deleted=False,
        enable_iteration=True,
        is_closed=False
    ).prefetch_related("managers")
    
    result = []
    for project in projects:
        # 获取当前迭代
        current_iter = Iteration.objects.filter(
            project=project,
            is_current=True
        ).first()
        
        dashboard_data = {
            "project_id": project.id,
            "project_name": project.name,
            "project_domain": project.domain,
            "project_type": project.type,
            "project_managers": ",".join([m.name for m in project.managers.all()]),
        }
        dashboard_data.update(_get_iteration_quality_metrics(project))
        
        if current_iter:
            dashboard_data.update({
                "iteration_id": str(current_iter.id),
                "current_iteration_name": current_iter.name,
                "current_iteration_code": current_iter.code,
                "start_date": current_iter.start_date,
                "end_date": current_iter.end_date,
                "is_healthy": current_iter.is_healthy,
            })
            
            latest_metric = IterationMetric.objects.filter(
                iteration=current_iter
            ).order_by('-record_date').first()
            
            if latest_metric:
                rates = _calculate_rates(latest_metric)
                dashboard_data.update(rates)
        
        result.append(IterationDashboardSchema(
            project_id=str(dashboard_data['project_id']),
            project_name=dashboard_data['project_name'],
            project_domain=dashboard_data['project_domain'],
            project_type=dashboard_data['project_type'],
            project_managers=dashboard_data['project_managers'],
            current_iteration_name=dashboard_data.get('current_iteration_name'),
            current_iteration_code=dashboard_data.get('current_iteration_code'),
            start_date=dashboard_data.get('start_date'),
            end_date=dashboard_data.get('end_date'),
            is_healthy=dashboard_data.get('is_healthy', True),
            iteration_id=dashboard_data.get('iteration_id'),
            sr_breakdown_rate=dashboard_data.get('sr_breakdown_rate', 0.0),
            dr_breakdown_rate=dashboard_data.get('dr_breakdown_rate', 0.0),
            ar_set_a_rate=dashboard_data.get('ar_set_a_rate', 0.0),
            dr_set_a_rate=dashboard_data.get('dr_set_a_rate', 0.0),
            ar_set_c_rate=dashboard_data.get('ar_set_c_rate', 0.0),
            dr_set_c_rate=dashboard_data.get('dr_set_c_rate', 0.0),
            test_automation_rate=dashboard_data.get('test_automation_rate', 0.0),
            test_case_execution_rate=dashboard_data.get('test_case_execution_rate', 0.0),
            bug_fix_rate=dashboard_data.get('bug_fix_rate', 0.0),
            code_review_rate=dashboard_data.get('code_review_rate', 0.0),
            code_coverage_rate=dashboard_data.get('code_coverage_rate', 0.0),
            quality_ut_file_coverage_rate=dashboard_data.get(
                'quality_ut_file_coverage_rate',
                0.0,
            ),
            quality_ut_line_coverage_rate=dashboard_data.get(
                'quality_ut_line_coverage_rate',
                0.0,
            ),
            quality_clean_code_rate=dashboard_data.get(
                'quality_clean_code_rate',
                0.0,
            ),
            sr_num=dashboard_data.get('sr_num', 0),
            dr_num=dashboard_data.get('dr_num', 0),
            ar_num=dashboard_data.get('ar_num', 0),
        ))
        
    return result

def refresh_project_iteration(project_id: str):
    project = Project.objects.get(id=project_id)
    sync_project_iterations(project)
    return True


def get_project_iterations(project_id: str):
    iterations = Iteration.objects.filter(
        project_id=project_id,
        is_deleted=False
    ).order_by('-start_date')
    
    result = []
    for iteration in iterations:
        # 获取最新指标
        latest_metric = IterationMetric.objects.filter(
            iteration=iteration
        ).order_by('-record_date').first()
        
        detail = IterationDetailSchema.from_orm(iteration)
        if latest_metric:
            rates = _calculate_rates(latest_metric)
            detail.latest_metric = IterationMetricOut(
                id=str(latest_metric.id),
                iteration_id=str(latest_metric.iteration_id),
                record_date=latest_metric.record_date,
                sr_num=latest_metric.sr_num,
                dr_num=latest_metric.dr_num,
                ar_num=latest_metric.ar_num,
                sr_breakdown_rate=rates.get("sr_breakdown_rate", 0.0),
                dr_breakdown_rate=rates.get("dr_breakdown_rate", 0.0),
                ar_set_a_rate=rates.get("ar_set_a_rate", 0.0),
                dr_set_a_rate=rates.get("dr_set_a_rate", 0.0),
                ar_set_c_rate=rates.get("ar_set_c_rate", 0.0),
                dr_set_c_rate=rates.get("dr_set_c_rate", 0.0),
                test_automation_rate=rates.get("test_automation_rate", 0.0),
                test_case_execution_rate=rates.get("test_case_execution_rate", 0.0),
                bug_fix_rate=rates.get("bug_fix_rate", 0.0),
                code_review_rate=rates.get("code_review_rate", 0.0),
                code_coverage_rate=rates.get("code_coverage_rate", 0.0),
            )
            
        result.append(detail)
        
    return result


def _paginate_items(items: list[dict], page: int, page_size: int) -> dict:
    """对缓存明细做内存分页，保持前端 zq-table 分页协议。"""
    page = max(int(page or 1), 1)
    page_size = max(int(page_size or 20), 1)
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": items[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def _normalize_requirement_type(value: str | None) -> str | None:
    """规范化需求类型筛选值。"""
    normalized = str(value or "").strip().lower()
    if normalized in {"sr", "dr", "ar"}:
        return normalized
    return None


def _normalize_idpca_status(value: str | None) -> str | None:
    """规范化 IDPCA 状态筛选值。"""
    normalized = str(value or "").strip().upper()
    if normalized in {"I", "D", "P", "C", "A"}:
        return normalized
    return None


def _normalize_owner_display(value) -> str:
    """把开发责任人字段统一成逗号分隔的展示文本。"""
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, tuple):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def _resolve_develop_owner(item: dict) -> str:
    """按字段优先级解析需求开发责任人，并兼容历史 owner 字段。"""
    for field_name in ("develop_owner", "develop_user", "develop_users", "owner"):
        owner = _normalize_owner_display(item.get(field_name))
        if owner:
            return owner
    return ""


def _normalize_requirement_item(item: dict) -> dict:
    """规范化迭代需求明细，保证列表接口和导出字段口径一致。"""
    requirement_type = (
        _normalize_requirement_type(str(item.get("requirement_type") or ""))
        or "sr"
    )
    idpca_status = _normalize_idpca_status(str(item.get("idpca_status") or "")) or "I"
    return {
        "requirement_id": str(item.get("requirement_id") or ""),
        "title": str(item.get("title") or ""),
        "requirement_type": requirement_type,
        "idpca_status": idpca_status,
        "owner_team": str(item.get("owner_team") or ""),
        "develop_owner": _resolve_develop_owner(item),
        "need_breakdown": bool(item.get("need_breakdown")),
        "is_decomposed": bool(item.get("is_decomposed", True)),
        "workload_man_filled": bool(item.get("workload_man_filled")),
        "workload_loc_filled": bool(item.get("workload_loc_filled")),
    }


def list_iteration_requirements(
    iteration_id: str,
    page: int = 1,
    page_size: int = 20,
    idpca_status: str | None = None,
    requirement_type: str | None = None,
):
    """查询迭代需求 IDPCA 明细，支持类型和状态筛选。"""
    iteration = (
        Iteration.objects.select_related("project")
        .filter(id=iteration_id, is_deleted=False)
        .first()
    )
    if not iteration:
        return _paginate_items([], page, page_size)

    status_filter = _normalize_idpca_status(idpca_status)
    type_filter = _normalize_requirement_type(requirement_type)
    requirement_items = get_cached_iteration_requirements(iteration)

    filtered: list[dict] = []
    for item in requirement_items:
        normalized_item = _normalize_requirement_item(item)
        if type_filter and normalized_item["requirement_type"] != type_filter:
            continue
        if status_filter and normalized_item["idpca_status"] != status_filter:
            continue
        filtered.append(normalized_item)

    return _paginate_items(filtered, page, page_size)


def list_unresolved_requirements(
    iteration_id: str,
    page: int = 1,
    page_size: int = 20,
    requirement_type: str | None = None,
):
    """查询需要分解但尚未完成分解的迭代需求。"""
    iteration = (
        Iteration.objects.select_related("project")
        .filter(id=iteration_id, is_deleted=False)
        .first()
    )
    if not iteration:
        return _paginate_items([], page, page_size)

    type_filter = _normalize_requirement_type(requirement_type)
    requirement_items = get_cached_iteration_requirements(iteration)

    filtered: list[dict] = []
    for item in requirement_items:
        normalized_item = _normalize_requirement_item(item)
        if not normalized_item["need_breakdown"] or normalized_item["is_decomposed"]:
            continue
        if type_filter and normalized_item["requirement_type"] != type_filter:
            continue
        filtered.append(normalized_item)

    return _paginate_items(filtered, page, page_size)


def record_daily_metric(iteration_id: str, data: IterationMetricSchema):
    """记录指定迭代某一天的指标快照。"""
    metric, _ = IterationMetric.objects.update_or_create(
        iteration_id=iteration_id,
        record_date=data.record_date,
        defaults=data.dict(exclude={'record_date'})
    )
    return metric

def update_manual_metric(iteration_id: str, data: IterationManualUpdateSchema):
    """更新详情页允许手工维护的最新迭代指标。"""
    # Find the latest metric for this iteration, or create one for today if not exists
    # But usually we are updating the existing one shown in dashboard
    
    # Logic: Get the latest metric. If it exists, update it.
    # If not, create one for today?
    # The dashboard shows the latest metric.
    
    metric = IterationMetric.objects.filter(iteration_id=iteration_id).order_by('-record_date').first()
    
    if not metric:
        # Create a new one for today if no metric exists at all
        # But this case is rare if sync is working.
        from datetime import date
        metric = IterationMetric.objects.create(
            iteration_id=iteration_id,
            record_date=date.today()
        )
        
    if data.test_automation_rate is not None:
        metric.test_automation_rate = data.test_automation_rate
    if data.test_case_execution_rate is not None:
        metric.test_case_execution_rate = data.test_case_execution_rate
        
    metric.save()
    return True


def _format_bool(value: bool) -> str:
    """把布尔值转成导出文件里的中文展示。"""
    return "是" if value else "否"


def _format_rate(value: float | int | None) -> str:
    """把 0-1 比例转成导出文件里的百分比文本。"""
    if value is None:
        return "-"
    return f"{float(value) * 100:.1f}%"


def _append_sheet(
    workbook: openpyxl.Workbook,
    title: str,
    headers: tuple[str, ...],
    rows,
):
    """创建导出 sheet 并按行写入数据。"""
    worksheet = workbook.create_sheet(title=title)
    worksheet.append(list(headers))
    for row in rows:
        worksheet.append(list(row))


def _build_requirement_export_row(item: dict) -> list:
    """生成需求明细导出行，责任人统一使用开发责任人。"""
    return [
        item["requirement_id"],
        item["title"],
        item["requirement_type"].upper(),
        item["idpca_status"],
        item["owner_team"],
        item["develop_owner"],
        _format_bool(item["need_breakdown"]),
        _format_bool(item["is_decomposed"]),
        _format_bool(item["workload_man_filled"]),
        _format_bool(item["workload_loc_filled"]),
    ]


def _build_export_response(workbook: openpyxl.Workbook, filename: str) -> HttpResponse:
    """把 openpyxl 工作簿包装成浏览器可下载响应。"""
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    quoted_filename = quote(filename)
    response["Content-Disposition"] = (
        f"attachment; filename*=UTF-8''{quoted_filename}"
    )
    workbook.save(response)
    return response


def export_iteration_detail(iteration_id: str) -> HttpResponse:
    """导出单个迭代的基础信息、指标、需求 IDPCA 和未分解需求。"""
    iteration = (
        Iteration.objects.select_related("project")
        .filter(id=iteration_id, is_deleted=False)
        .first()
    )
    if not iteration:
        raise Http404("迭代不存在或已删除")

    latest_metric = (
        IterationMetric.objects.filter(iteration=iteration)
        .order_by("-record_date")
        .first()
    )
    rates = _calculate_rates(latest_metric) if latest_metric else {}

    requirement_items = [
        _normalize_requirement_item(item)
        for item in get_cached_iteration_requirements(iteration)
    ]
    unresolved_items = [
        item
        for item in requirement_items
        if item["need_breakdown"] and not item["is_decomposed"]
    ]

    workbook = openpyxl.Workbook(write_only=True)
    _append_sheet(
        workbook,
        "迭代基础信息",
        (
            "项目名称",
            "迭代名称",
            "编码",
            "开始时间",
            "结束时间",
            "当前迭代",
            "健康状态",
            "最新指标日期",
        ),
        [
            [
                iteration.project.name,
                iteration.name,
                iteration.code,
                iteration.start_date.isoformat() if iteration.start_date else "",
                iteration.end_date.isoformat() if iteration.end_date else "",
                _format_bool(iteration.is_current),
                "健康" if iteration.is_healthy else "风险",
                latest_metric.record_date.isoformat() if latest_metric else "",
            ]
        ],
    )
    _append_sheet(
        workbook,
        "入口指标",
        _ENTRY_METRIC_HEADERS,
        [
            [
                iteration.name,
                iteration.code,
                iteration.start_date.isoformat() if iteration.start_date else "",
                iteration.end_date.isoformat() if iteration.end_date else "",
                _format_bool(iteration.is_current),
                "健康" if iteration.is_healthy else "风险",
                _format_rate(rates.get("dr_breakdown_rate", 0.0)),
                _format_rate(rates.get("sr_breakdown_rate", 0.0)),
            ]
        ],
    )
    _append_sheet(
        workbook,
        "出口指标",
        _EXIT_METRIC_HEADERS,
        [
            [
                iteration.name,
                iteration.code,
                _format_rate(rates.get("dr_set_a_rate", 0.0)),
                _format_rate(rates.get("ar_set_a_rate", 0.0)),
                _format_rate(rates.get("dr_set_c_rate", 0.0)),
                _format_rate(rates.get("ar_set_c_rate", 0.0)),
                _format_rate(rates.get("test_automation_rate", 0.0)),
                _format_rate(rates.get("test_case_execution_rate", 0.0)),
                _format_rate(rates.get("bug_fix_rate", 0.0)),
                _format_rate(rates.get("code_review_rate", 0.0)),
                _format_rate(rates.get("code_coverage_rate", 0.0)),
            ]
        ],
    )
    _append_sheet(
        workbook,
        "需求IDPCA状态",
        _REQUIREMENT_EXPORT_HEADERS,
        (_build_requirement_export_row(item) for item in requirement_items),
    )
    _append_sheet(
        workbook,
        "未分解需求",
        _REQUIREMENT_EXPORT_HEADERS,
        (_build_requirement_export_row(item) for item in unresolved_items),
    )

    timestamp = timezone.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{iteration.project.name}-{iteration.name}-迭代详情-{timestamp}.xlsx"
    return _build_export_response(workbook, filename)
