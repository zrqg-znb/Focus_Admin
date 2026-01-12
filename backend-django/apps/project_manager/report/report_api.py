from ninja import Router
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import random

from apps.project_manager.project.project_model import Project
from apps.project_manager.code_quality.code_quality_model import CodeModule, CodeMetric
from apps.project_manager.iteration.iteration_model import Iteration, IterationMetric
from apps.project_manager.dts.dts_model import DtsData, DtsTeam
from apps.project_manager.milestone.milestone_model import Milestone

from .report_schema import (
    ProjectReportSchema, 
    RadarIndicator, 
    DtsTrendItem, 
    CodeQualitySummary, 
    IterationSummary, 
    DtsSummary,
    QGNode
)

router = Router(tags=["Project Report"])

@router.get("/{project_id}", response=ProjectReportSchema, summary="获取项目详细报告")
def get_project_report(request, project_id: str):
    project = get_object_or_404(Project, id=project_id)
    
    # --- 1. Basic Info ---
    managers = ",".join([m.name for m in project.managers.all()])
    
    # --- 2. Code Quality ---
    cq_summary = None
    cq_score = 0
    if project.enable_quality:
        modules = CodeModule.objects.filter(project=project, is_deleted=False)
        total_loc = 0
        total_issues = 0
        dup_rates = []
        
        for mod in modules:
            metric = CodeMetric.objects.filter(module=mod).order_by('-record_date').first()
            if metric:
                total_loc += metric.loc
                total_issues += metric.dangerous_func_count
                dup_rates.append(metric.duplication_rate)
        
        avg_dup = sum(dup_rates) / len(dup_rates) if dup_rates else 0.0
        # Simple score calc: 100 - (issues * 2) - (dup * 2)
        cq_score = max(0, 100 - (total_issues * 2) - (avg_dup * 2))
        
        cq_summary = CodeQualitySummary(
            total_projects=1,
            total_modules=len(modules),
            total_loc=total_loc,
            total_issues=total_issues,
            avg_duplication_rate=round(avg_dup, 2),
            health_score=round(cq_score, 1)
        )
    
    # --- 3. Iteration ---
    iter_summary = None
    iter_score = 0
    if project.enable_iteration:
        current_iter = Iteration.objects.filter(project=project, is_current=True).first()
        active_count = 1 if current_iter else 0
        # Mock delayed check
        today = timezone.now().date()
        delayed_count = 0
        if current_iter and current_iter.end_date < today:
            delayed_count = 1
            
        total_req = 0
        completion_rate = 0.0
        
        if current_iter:
            metric = IterationMetric.objects.filter(iteration=current_iter).order_by('-record_date').first()
            if metric:
                total_req = metric.req_workload
                completion_rate = metric.req_completion_rate
        
        iter_score = completion_rate # Simple mapping
        
        iter_summary = IterationSummary(
            active_iterations=active_count,
            delayed_iterations=delayed_count,
            total_req_count=int(total_req),
            completion_rate=round(completion_rate, 2)
        )

    # --- 4. DTS ---
    dts_summary = None
    dts_score = 0
    dts_trend = []
    
    if project.enable_dts:
        # Summary (Latest)
        dts_teams = DtsTeam.objects.filter(project=project)
        today = timezone.now().date()
        # Try to get today's data, else fallback
        dts_data_qs = DtsData.objects.filter(team__in=dts_teams, record_date=today)
        
        dts_agg = dts_data_qs.aggregate(
            total=Sum('major_num') + Sum('minor_num') + Sum('suggestion_num') + Sum('fatal_num'),
            critical=Sum('fatal_num') + Sum('major_num')
        )
        
        # Calculate avg solve rate
        rates = []
        for d in dts_data_qs:
            try:
                rates.append(float(d.solve_rate.replace('%', '')))
            except:
                pass
        avg_rate = sum(rates) / len(rates) if rates else 0.0
        dts_score = avg_rate # Use solve rate as score
        
        dts_summary = DtsSummary(
            total_issues=dts_agg.get('total') or 0,
            critical_issues=dts_agg.get('critical') or 0,
            avg_solve_time=2.5, # Mock
            solve_rate=round(avg_rate, 1)
        )
        
        # Trend (Last 7 days Mock)
        # In a real app, we would query DtsData grouped by date
        for i in range(6, -1, -1):
            date_str = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            # Mock fluctuation
            base_total = (dts_summary.total_issues or 10) + random.randint(-5, 5)
            base_rate = (dts_summary.solve_rate or 90) + random.uniform(-5, 5)
            
            dts_trend.append(DtsTrendItem(
                date=date_str,
                critical=max(0, int(base_total * 0.1)),
                major=max(0, int(base_total * 0.2)),
                minor=max(0, int(base_total * 0.4)),
                suggestion=max(0, int(base_total * 0.3)),
                solve_rate=round(min(100, max(0, base_rate)), 1),
                critical_solve_rate=round(min(100, max(0, base_rate - 5)), 1)
            ))
            
    # --- 5. Milestones ---
    milestones_list = []
    ms_score = 100
    if hasattr(project, 'milestone') and project.enable_milestone:
        ms = project.milestone
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
    
    # --- 6. Radar & Health ---
    # Calculate overall health
    # Weights: Quality 30%, Iteration 30%, DTS 30%, Milestone 10%
    # Normalize scores to 0-100
    s_quality = cq_score if project.enable_quality else 100
    s_iteration = iter_score if project.enable_iteration else 100
    s_dts = dts_score if project.enable_dts else 100
    s_milestone = ms_score # Simplified
    
    health_score = (s_quality * 0.3) + (s_iteration * 0.3) + (s_dts * 0.3) + (s_milestone * 0.1)
    
    health_level = 'healthy'
    if health_score < 60:
        health_level = 'error'
    elif health_score < 80:
        health_level = 'warning'
        
    radar_data = [
        RadarIndicator(name="代码质量", value=round(s_quality, 1)),
        RadarIndicator(name="迭代进度", value=round(s_iteration, 1)),
        RadarIndicator(name="问题单解决", value=round(s_dts, 1)),
        RadarIndicator(name="里程碑达成", value=round(s_milestone, 1)),
        RadarIndicator(name="需求交付", value=round(s_iteration, 1)), # Duplicate for pentagon shape
    ]
    
    return ProjectReportSchema(
        project_id=str(project.id),
        project_name=project.name,
        manager=managers,
        health_score=round(health_score, 1),
        health_level=health_level,
        radar_data=radar_data,
        milestones=milestones_list,
        dts_trend=dts_trend,
        code_quality=cq_summary,
        iteration=iter_summary,
        dts_summary=dts_summary
    )
