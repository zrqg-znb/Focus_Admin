from ninja import Router
import asyncio
from asgiref.sync import async_to_sync
from .report_schema import ProjectReportSchema, RadarIndicator
from .report_service import ReportService

router = Router(tags=["Project Report"])

@router.get("/{project_id}", response=ProjectReportSchema, summary="获取项目详细报告")
def get_project_report(request, project_id: str):
    
    async def _get_async_data():
        project = await ReportService.get_project(project_id)
        
        # Run concurrent tasks
        task_managers = ReportService.get_managers(project)
        task_cq = ReportService.get_code_quality_data(project)
        task_iter = ReportService.get_iteration_data(project)
        task_dts = ReportService.get_dts_data(project)
        task_ms = ReportService.get_milestone_data(project)
        
        results = await asyncio.gather(
            task_managers, 
            task_cq, 
            task_iter, 
            task_dts, 
            task_ms
        )
        return project, results

    # Execute async logic in sync context
    project, results = async_to_sync(_get_async_data)()
    
    managers, \
    (cq_summary, cq_details, cq_score), \
    (iter_summary, iter_detail, iter_score), \
    (
        dts_summary,
        dts_trend,
        dts_team_di,
        dts_team_di_trend,
        dts_team_issue_trend,
        dts_team_solve_rate_trend,
        dts_team_critical_rate_trend,
        dts_score,
    ), \
    (milestones_list, ms_score) = results
    
    # --- Radar & Health ---
    s_quality = cq_score
    s_iteration = iter_score
    s_dts = dts_score
    s_milestone = ms_score
    
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
        dts_team_di=dts_team_di,
        dts_team_di_trend=dts_team_di_trend,
        dts_team_issue_trend=dts_team_issue_trend,
        dts_team_solve_rate_trend=dts_team_solve_rate_trend,
        dts_team_critical_rate_trend=dts_team_critical_rate_trend,
        code_quality=cq_summary,
        code_quality_details=cq_details,
        iteration=iter_summary,
        iteration_detail=iter_detail,
        dts_summary=dts_summary
    )
