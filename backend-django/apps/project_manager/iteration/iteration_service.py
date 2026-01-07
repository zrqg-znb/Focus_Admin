from django.db import transaction
from common import fu_crud
from apps.project_manager.project.project_model import Project
from .iteration_model import Iteration, IterationMetric
from .iteration_schema import IterationCreateSchema, IterationMetricSchema, IterationDetailSchema, IterationDashboardSchema
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
                dashboard_data.update({
                    "req_decomposition_rate": latest_metric.req_decomposition_rate,
                    "req_drift_rate": latest_metric.req_drift_rate,
                    "req_completion_rate": latest_metric.req_completion_rate,
                    "req_workload": latest_metric.req_workload,
                    "completed_workload": latest_metric.completed_workload,
                })
        
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
            req_decomposition_rate=dashboard_data.get('req_decomposition_rate', 0.0),
            req_drift_rate=dashboard_data.get('req_drift_rate', 0.0),
            req_completion_rate=dashboard_data.get('req_completion_rate', 0.0),
            req_workload=dashboard_data.get('req_workload', 0.0),
            completed_workload=dashboard_data.get('completed_workload', 0.0)
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
            detail.latest_metric = latest_metric
        result.append(detail)
        
    return result

def record_daily_metric(iteration_id: str, data: IterationMetricSchema):
    metric, created = IterationMetric.objects.update_or_create(
        iteration_id=iteration_id,
        record_date=data.record_date,
        defaults=data.dict(exclude={'record_date'})
    )
    return metric
