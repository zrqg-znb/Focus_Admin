from typing import List, Optional
from ninja import Router, Schema
from django.db.models import Q

from common.fu_auth import BearerAuth as GlobalAuth
from apps.project_manager.project.project_model import Project
from .iteration_model import Iteration, IterationMetric
from .iteration_schema import (
    IterationCreateSchema, 
    IterationDetailSchema, 
    IterationMetricSchema,
    IterationMetricOut,
    IterationOut
)
from . import iteration_service

router = Router(tags=["Iteration"], auth=GlobalAuth())

class IterationOverviewSchema(Schema):
    project_id: str
    project_name: str
    current_iteration: Optional[IterationOut] = None
    latest_metric: Optional[IterationMetricOut] = None

@router.get("/overview", response=List[IterationOverviewSchema], summary="迭代看板概览")
def get_iteration_overview(request):
    # 优化查询：预加载当前迭代
    projects = Project.objects.filter(
        enable_iteration=True, 
        is_deleted=False
    ).prefetch_related(
        'iterations'
    )
    
    result = []
    
    for p in projects:
        # 在内存中过滤当前迭代，避免 N+1 查询
        # 注意：这里假设每个项目只有一个当前迭代，或者我们只取第一个
        current_iter = next((i for i in p.iterations.all() if i.is_current and not i.is_deleted), None)
        
        item = IterationOverviewSchema(
            project_id=p.id,
            project_name=p.name,
            current_iteration=current_iter
        )
        
        # 获取最新指标
        if current_iter:
            # 这里的指标获取仍然可能导致 N+1，进一步优化需要预加载 metrics
            # 考虑到指标表数据量可能较大，且我们只需要最新的一条，
            # 可以使用 Subquery 或者在这里单独查询（如果项目数不多）
            # 为了彻底解决 N+1，我们可以在上面 prefetch_related('iterations__metrics')
            # 但 metrics 数据量大，全部加载内存消耗大。
            # 折衷方案：对于概览页，只查最新的一条。
            # 如果项目数较多（如 > 50），建议使用 Subquery。
            # 这里演示使用 ORM 的 Subquery 优化（如果 models 支持反向查询）
            # 但为了保持代码简单且易读，且假设概览页项目不会成千上万，
            # 我们先保持单独查询，或者使用 prefetch_related 并只取最新的（Python处理）
            
            # 优化方案：批量查询所有涉及到的迭代的最新指标
            # 但由于 API 结构限制，我们这里先保持简单查询，或者在 Service 层做更复杂的优化
            # 这里演示最简单的内存优化：假定 metrics 不多，或者接受 1 次额外查询
            latest_metric = IterationMetric.objects.filter(
                iteration=current_iter
            ).order_by('-record_date').first()
            item.latest_metric = latest_metric
            
        result.append(item)
        
    return result

@router.get("/project/{project_id}", response=List[IterationDetailSchema], summary="获取项目迭代列表")
def list_project_iterations(request, project_id: str):
    return iteration_service.get_project_iterations(project_id)

@router.post("/", response=IterationOut, summary="创建迭代")
def create_iteration(request, data: IterationCreateSchema):
    return iteration_service.create_iteration(request, data)

@router.post("/{iteration_id}/metrics", response=IterationMetricOut, summary="录入迭代指标")
def record_daily_metric(request, iteration_id: str, data: IterationMetricSchema):
    return iteration_service.record_daily_metric(iteration_id, data)
