from django.db import transaction
from common import fu_crud
from apps.project_manager.project.project_model import Project
from .iteration_model import Iteration, IterationMetric
from .iteration_schema import IterationCreateSchema, IterationMetricSchema, IterationDetailSchema, IterationDashboardSchema, IterationMetricOut
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
    }

def get_iteration_dashboard():
    projects = Project.objects.filter(
        is_deleted=False,
        enable_iteration=True,
        is_closed=False
    )
    
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
        
        if current_iter:
            dashboard_data.update({
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
            sr_breakdown_rate=dashboard_data.get('sr_breakdown_rate', 0.0),
            dr_breakdown_rate=dashboard_data.get('dr_breakdown_rate', 0.0),
            ar_set_a_rate=dashboard_data.get('ar_set_a_rate', 0.0),
            dr_set_a_rate=dashboard_data.get('dr_set_a_rate', 0.0),
            ar_set_c_rate=dashboard_data.get('ar_set_c_rate', 0.0),
            dr_set_c_rate=dashboard_data.get('dr_set_c_rate', 0.0),
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
