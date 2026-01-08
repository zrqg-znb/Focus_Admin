from ninja import Router, Query
from typing import List, Optional
from django.db.models import Sum, Avg, Count, Max, Q
from django.utils import timezone
from .schemas import (
    DashboardSummarySchema, 
    CodeQualitySummary, 
    IterationSummary, 
    PerformanceSummary,
    ProjectDistribution,
    NameValue,
    UpcomingMilestone,
    FavoriteProjectDetail,
    QGNode,
    CoreMetricsSchema
)

from apps.project_manager.code_quality.code_quality_model import CodeModule, CodeMetric
from apps.project_manager.iteration.iteration_model import Iteration, IterationMetric
from apps.performance.models import PerformanceIndicator, PerformanceIndicatorData
from apps.project_manager.project.project_model import Project
from apps.project_manager.milestone.milestone_model import Milestone

router = Router(tags=["Dashboard"])

@router.get("/milestones", response=List[UpcomingMilestone], summary="即将到达的里程碑")
def get_upcoming_milestones(request, qg_types: List[str] = Query(None)):
    """
    获取即将到达的里程碑（默认未来30天）。
    支持筛选特定的 QG 点，例如 qg_types=["QG1", "QG3"]
    """
    today = timezone.now().date()
    milestones = Milestone.objects.select_related('project').filter(project__is_deleted=False, project__is_closed=False)
    
    # 确定要检查的字段
    if qg_types:
        # 用户指定了 QG 类型，如 ["QG1", "QG3"]
        # 转换为字段名 qg1_date, qg3_date
        target_fields = [f"{qg.lower()}_date" for qg in qg_types if qg.upper().startswith("QG")]
    else:
        # 默认检查所有
        target_fields = [f'qg{i}_date' for i in range(1, 9)]
        
    result = []
    
    for ms in milestones:
        for field in target_fields:
            # 安全获取属性，防止传入非法字段名导致报错
            if not hasattr(ms, field):
                continue
                
            qg_date = getattr(ms, field)
            if qg_date:
                delta = (qg_date - today).days
                if 0 <= delta <= 30: # 未来 30 天内
                    managers = ",".join([m.name for m in ms.project.managers.all()])
                    # 从字段名 qg1_date -> QG1
                    qg_name = field.replace('_date', '').upper()
                    
                    result.append(UpcomingMilestone(
                        project_name=ms.project.name,
                        project_manager=managers,
                        qg_name=qg_name,
                        qg_date=qg_date,
                        days_left=delta
                    ))
    
    # 按剩余天数排序
    result.sort(key=lambda x: x.days_left)
    return result

@router.get("/core-metrics", response=CoreMetricsSchema, summary="核心指标数据")
def get_core_metrics(request):
    # --- Code Quality ---
    active_modules = CodeModule.objects.filter(is_deleted=False).values_list('id', flat=True)
    total_projects = CodeModule.objects.filter(is_deleted=False).values('project').distinct().count()
    
    latest_metrics = []
    total_loc = 0
    total_dangerous = 0
    dup_rates = []
    
    # 优化：可以考虑使用子查询或聚合来优化，这里先保持逻辑一致
    for mod_id in active_modules:
        metric = CodeMetric.objects.filter(module_id=mod_id).order_by('-record_date').first()
        if metric:
            total_loc += metric.loc
            total_dangerous += metric.dangerous_func_count
            dup_rates.append(metric.duplication_rate)
            
    avg_dup = sum(dup_rates) / len(dup_rates) if dup_rates else 0.0
    
    code_quality_summary = CodeQualitySummary(
        total_projects=total_projects,
        total_modules=len(active_modules),
        total_loc=total_loc,
        total_issues=total_dangerous,
        avg_duplication_rate=round(avg_dup, 2),
        health_score=85.0
    )
    
    # --- Iteration ---
    current_iterations = Iteration.objects.filter(is_current=True, is_deleted=False)
    active_count = current_iterations.count()
    today = timezone.now().date()
    delayed_count = current_iterations.filter(end_date__lt=today).count()
    
    total_req = 0
    completion_rates = []
    
    for iter_obj in current_iterations:
        metric = IterationMetric.objects.filter(iteration=iter_obj).order_by('-record_date').first()
        if metric:
            total_req += metric.req_workload
            completion_rates.append(metric.req_completion_rate)
            
    avg_completion = sum(completion_rates) / len(completion_rates) if completion_rates else 0.0
    
    iteration_summary = IterationSummary(
        active_iterations=active_count,
        delayed_iterations=delayed_count,
        total_req_count=int(total_req),
        completion_rate=round(avg_completion, 2)
    )
    
    # --- Performance ---
    total_indicators = PerformanceIndicator.objects.count()
    last_data = PerformanceIndicatorData.objects.order_by('-date').first()
    abnormal_count = 0
    
    if last_data:
        target_date = last_data.date
        daily_data = PerformanceIndicatorData.objects.filter(date=target_date).select_related('indicator')
        for d in daily_data:
            limit = d.indicator.fluctuation_range
            if abs(d.fluctuation_value) > limit:
                abnormal_count += 1
                
    performance_summary = PerformanceSummary(
        total_indicators=total_indicators,
        abnormal_count=abnormal_count,
        coverage_rate=92.5
    )

    return CoreMetricsSchema(
        code_quality=code_quality_summary,
        iteration=iteration_summary,
        performance=performance_summary
    )

@router.get("/project-distribution", response=ProjectDistribution, summary="项目分布数据")
def get_project_distribution(request):
    projects = Project.objects.filter(is_deleted=False)
    
    domain_counts = projects.values('domain').annotate(count=Count('id'))
    by_domain = [NameValue(name=item['domain'] or "未分类", value=item['count']) for item in domain_counts]
    
    type_counts = projects.values('type').annotate(count=Count('id'))
    by_type = [NameValue(name=item['type'] or "未分类", value=item['count']) for item in type_counts]
    
    return ProjectDistribution(
        by_domain=by_domain,
        by_type=by_type
    )

@router.get("/favorites", response=List[FavoriteProjectDetail], summary="收藏项目详情")
def get_favorite_projects(request):
    user = request.auth
    if not user:
        return []
        
    favorites = Project.objects.filter(favorited_by=user, is_deleted=False)
    result = []
    today = timezone.now().date()
    
    for proj in favorites:
        # 1. 基础数据
        managers = ",".join([m.name for m in proj.managers.all()])
        
        # 2. 代码质量
        modules = CodeModule.objects.filter(project=proj, is_deleted=False)
        proj_loc = 0
        health_score = 100.0
        
        for mod in modules:
            metric = CodeMetric.objects.filter(module=mod).order_by('-record_date').first()
            if metric:
                proj_loc += metric.loc
                health_score -= metric.dangerous_func_count
                if metric.duplication_rate > 5:
                    health_score -= (metric.duplication_rate - 5)
        
        health_score = max(0, min(100, health_score))
        
        # 3. 迭代进度
        current_iter = Iteration.objects.filter(project=proj, is_current=True).first()
        iter_name = current_iter.name if current_iter else None
        iter_progress = 0.0
        if current_iter:
            iter_metric = IterationMetric.objects.filter(iteration=current_iter).order_by('-record_date').first()
            if iter_metric:
                iter_progress = iter_metric.req_completion_rate
        
        # 4. 里程碑
        milestones_list = []
        if hasattr(proj, 'milestone'):
            ms = proj.milestone
            for i in range(1, 9):
                field_name = f'qg{i}_date'
                qg_date = getattr(ms, field_name)
                if qg_date:
                    status = 'pending'
                    if qg_date < today:
                        status = 'completed'
                    
                    milestones_list.append(QGNode(
                        name=f'QG{i}',
                        date=qg_date,
                        status=status
                    ))
        
        result.append(FavoriteProjectDetail(
            id=str(proj.id),
            name=proj.name,
            domain=proj.domain,
            type=proj.type,
            managers=managers,
            loc=proj_loc,
            health_score=round(health_score, 1),
            current_iteration=iter_name,
            iteration_progress=iter_progress,
            milestones=milestones_list
        ))
        
    return result

@router.get("/summary", response=DashboardSummarySchema, summary="工作台聚合数据 (Deprecated)")
def get_dashboard_summary(request):
    # 为了保持向后兼容，或者作为全量接口保留
    # 实际上内部可以复用上面的函数，但为了避免重复查询开销，这里先保留原样或直接调用上面的函数组合
    # 考虑到性能，前端将切换到细粒度接口，此接口可能仅作备用
    
    core = get_core_metrics(request)
    dist = get_project_distribution(request)
    favs = get_favorite_projects(request)
    milestones = get_upcoming_milestones(request)
    
    return DashboardSummarySchema(
        code_quality=core.code_quality,
        iteration=core.iteration,
        performance=core.performance,
        project_distribution=dist,
        upcoming_milestones=milestones,
        favorite_projects=favs
    )
