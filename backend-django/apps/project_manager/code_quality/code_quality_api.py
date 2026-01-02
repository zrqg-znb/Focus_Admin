from typing import List, Dict
from ninja import Router, Schema
from datetime import date, timedelta
from django.utils import timezone

from common.fu_auth import BearerAuth as GlobalAuth
from .code_quality_schema import (
    ProjectQualitySummarySchema, 
    ModuleConfigSchema, 
    CodeModuleOut,
    CodeMetricSchema,
    CodeMetricOut
)
from .code_quality_model import CodeModule, CodeMetric
from . import code_quality_service

router = Router(tags=["CodeQuality"], auth=GlobalAuth())

class ModuleQualityDetailSchema(Schema):
    module_info: CodeModuleOut
    metrics_history: List[CodeMetricOut]

@router.get("/overview", response=List[ProjectQualitySummarySchema], summary="代码质量看板概览")
def get_quality_overview(request):
    return code_quality_service.get_quality_overview()

@router.post("/modules", response=CodeModuleOut, summary="配置代码模块")
def config_module(request, data: ModuleConfigSchema):
    return code_quality_service.config_module(request, data)

@router.get("/project/{project_id}/details", response=List[ModuleQualityDetailSchema], summary="获取项目代码质量详情")
def get_project_quality_details(request, project_id: str):
    # 获取最近30天的时间
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    
    # 优化查询：预加载 metrics
    modules = CodeModule.objects.filter(
        project_id=project_id, 
        is_deleted=False
    ).prefetch_related('metrics')
    
    result = []
    
    for module in modules:
        # 在内存中过滤 metrics，避免 N+1 查询
        # 注意：如果 metrics 非常多，这种方式可能会消耗内存
        # 但既然限制了最近30天，通常数据量可控
        metrics = [
            m for m in module.metrics.all() 
            if m.record_date >= thirty_days_ago
        ]
        # 内存排序
        metrics.sort(key=lambda x: x.record_date)
        
        result.append(ModuleQualityDetailSchema(
            module_info=module,
            metrics_history=metrics
        ))
        
    return result

@router.post("/module/{module_id}/metrics", response=CodeMetricOut, summary="录入模块指标")
def record_module_metric(request, module_id: str, data: CodeMetricSchema):
    return code_quality_service.record_module_metric(module_id, data)
