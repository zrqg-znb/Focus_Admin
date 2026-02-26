from django.db import transaction
from common import fu_crud
from apps.project_manager.project.project_model import Project
from apps.project_manager.code_quality.code_quality_model import CodeModule
from .iteration_model import Iteration, IterationMetric
from .iteration_schema import IterationCreateSchema, IterationMetricSchema, IterationDetailSchema, IterationDashboardSchema, IterationMetricOut, IterationManualUpdateSchema
from .iteration_sync import sync_project_iterations

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
    metric_payload = summary_metrics.get(metric_key)
    if isinstance(metric_payload, dict):
        parsed_value = _to_float(metric_payload.get("num"))
        if parsed_value is None:
            parsed_value = _to_float(metric_payload.get("display"))
        return _normalize_ratio(parsed_value)

    return _normalize_ratio(metric_payload)


def _get_iteration_quality_metrics(project: Project) -> dict:
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

def record_daily_metric(iteration_id: str, data: IterationMetricSchema):
    metric, created = IterationMetric.objects.update_or_create(
        iteration_id=iteration_id,
        record_date=data.record_date,
        defaults=data.dict(exclude={'record_date'})
    )
    return metric

def update_manual_metric(iteration_id: str, data: IterationManualUpdateSchema):
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
