from django.db import transaction
from common import fu_crud
from .iteration_model import Iteration, IterationMetric
from .iteration_schema import IterationCreateSchema, IterationMetricSchema, IterationDetailSchema

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
