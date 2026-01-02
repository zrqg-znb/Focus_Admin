from django.db.models import Sum, Avg
from common import fu_crud
from apps.project_manager.project.project_model import Project
from .code_quality_model import CodeModule, CodeMetric
from .code_quality_schema import ModuleConfigSchema, CodeMetricSchema, ProjectQualitySummarySchema

def get_quality_overview():
    projects = Project.objects.filter(
        is_deleted=False,
        enable_quality=True,
        is_closed=False
    )
    
    result = []
    for project in projects:
        modules = CodeModule.objects.filter(project=project, is_deleted=False)
        
        total_loc = 0
        total_funcs = 0
        total_dangerous = 0
        duplication_rates = []
        
        for module in modules:
            # 获取该模块最新一天的指标
            latest_metric = CodeMetric.objects.filter(
                module=module
            ).order_by('-record_date').first()
            
            if latest_metric:
                total_loc += latest_metric.loc
                total_funcs += latest_metric.function_count
                total_dangerous += latest_metric.dangerous_func_count
                duplication_rates.append(latest_metric.duplication_rate)
        
        avg_dup = sum(duplication_rates) / len(duplication_rates) if duplication_rates else 0.0
        
        result.append(ProjectQualitySummarySchema(
            project_id=project.id,
            project_name=project.name,
            total_loc=total_loc,
            total_function_count=total_funcs,
            total_dangerous_func_count=total_dangerous,
            avg_duplication_rate=round(avg_dup, 2),
            module_count=len(modules)
        ))
        
    return result

def config_module(request, data: ModuleConfigSchema):
    return fu_crud.create(request, data.dict(), CodeModule)

def record_module_metric(module_id: str, data: CodeMetricSchema):
    metric, created = CodeMetric.objects.update_or_create(
        module_id=module_id,
        record_date=data.record_date,
        defaults=data.dict(exclude={'record_date'})
    )
    return metric
