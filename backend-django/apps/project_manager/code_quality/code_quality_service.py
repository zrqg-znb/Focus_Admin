from django.db.models import Sum, Avg
from common import fu_crud
from apps.project_manager.project.project_model import Project
from .code_quality_model import CodeModule, CodeMetric
from .code_quality_schema import ModuleConfigSchema, CodeMetricSchema, ProjectQualitySummarySchema, ModuleQualityDetailSchema

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
        last_record_date = None
        
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
                if not last_record_date or latest_metric.record_date > last_record_date:
                    last_record_date = latest_metric.record_date
        
        avg_dup = sum(duplication_rates) / len(duplication_rates) if duplication_rates else 0.0
        
        managers = ",".join([m.name for m in project.managers.all()])
        
        result.append(ProjectQualitySummarySchema(
            project_id=project.id,
            project_name=project.name,
            project_domain=project.domain,
            project_type=project.type,
            project_managers=managers,
            record_date=last_record_date,
            total_loc=total_loc,
            total_function_count=total_funcs,
            total_dangerous_func_count=total_dangerous,
            avg_duplication_rate=round(avg_dup, 2),
            module_count=len(modules)
        ))
        
    return result

def get_project_quality_details(project_id: str):
    modules = CodeModule.objects.filter(
        project_id=project_id, 
        is_deleted=False
    ).prefetch_related('owners')
    
    result = []
    for module in modules:
        latest_metric = CodeMetric.objects.filter(
            module=module
        ).order_by('-record_date').first()
        
        owner_names = [u.name for u in module.owners.all()]
        owner_ids = [str(u.id) for u in module.owners.all()]
        
        detail = ModuleQualityDetailSchema(
            id=str(module.id),
            oem_name=module.oem_name,
            module=module.module,
            owner_names=owner_names,
            owner_ids=owner_ids,
            record_date=latest_metric.record_date if latest_metric else None,
            loc=latest_metric.loc if latest_metric else 0,
            function_count=latest_metric.function_count if latest_metric else 0,
            dangerous_func_count=latest_metric.dangerous_func_count if latest_metric else 0,
            duplication_rate=latest_metric.duplication_rate if latest_metric else 0.0,
            is_clean_code=latest_metric.is_clean_code if latest_metric else False
        )
        result.append(detail)
    return result

def refresh_project_quality(project_id: str):
    project = Project.objects.get(id=project_id)
    sync_project_quality_metrics(project)
    return True


from .quality_sync import sync_project_quality_metrics

from django.db import IntegrityError
from ninja.errors import HttpError

def config_module(request, data: ModuleConfigSchema):
    data_dict = data.dict()
    module_id = data_dict.pop('id', None)
    owner_ids = data_dict.pop('owner_ids', [])
    
    project_id = data_dict.get('project_id')
    oem_name = data_dict.get('oem_name')
    module_name = data_dict.get('module')

    try:
        if module_id:
            # 更新模式
            module = CodeModule.objects.get(id=module_id)
            # 检查是否有重复（排除自身）
            if CodeModule.objects.filter(project_id=project_id, oem_name=oem_name, module=module_name).exclude(id=module_id).exists():
                raise HttpError(409, f"模块 {oem_name}-{module_name} 已存在")
            
            module.oem_name = oem_name
            module.module = module_name
            module.project_id = project_id
            module.save()
        else:
            # 创建模式
            # 检查是否已存在
            existing = CodeModule.objects.filter(project_id=project_id, oem_name=oem_name, module=module_name).first()
            if existing:
                # 如果已存在，直接更新（比如责任人变化）
                module = existing
            else:
                module = fu_crud.create(request, data_dict, CodeModule)
    except IntegrityError:
        raise HttpError(409, f"模块 {oem_name}-{module_name} 已存在")
    
    if owner_ids is not None:
        module.owners.set(owner_ids)
        
    # 配置完成后，立即触发一次同步，获取初始数据
    try:
        # 需要获取 Project 对象
        project = Project.objects.get(id=project_id)
        if project.enable_quality:
            sync_project_quality_metrics(project)
    except Exception as e:
        print(f"Initial quality sync failed: {e}")
        
    return module

def record_module_metric(module_id: str, data: CodeMetricSchema):
    metric, created = CodeMetric.objects.update_or_create(
        module_id=module_id,
        record_date=data.record_date,
        defaults=data.dict(exclude={'record_date'})
    )
    return metric
