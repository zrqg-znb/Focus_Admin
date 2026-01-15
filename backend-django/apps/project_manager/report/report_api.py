from ninja import Router
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict

from apps.project_manager.project.project_model import Project
from apps.project_manager.code_quality.code_quality_model import CodeModule, CodeMetric
from apps.project_manager.code_quality.code_quality_service import get_project_quality_details
from apps.project_manager.iteration.iteration_model import Iteration, IterationMetric
from apps.project_manager.dts.dts_model import DtsData, DtsTeam
from apps.project_manager.milestone.milestone_model import Milestone, MilestoneQGConfig, MilestoneRiskItem

from .report_schema import (
    ProjectReportSchema, 
    RadarIndicator, 
    DtsTrendItem, 
    DtsTeamDiItem,
    DtsTeamDiTrend,
    DtsTeamDiSeries,
    CodeQualitySummary, 
    IterationSummary, 
    DtsSummary,
    IterationDetailMetrics,
    QGNode
)

router = Router(tags=["Project Report"])

@router.get("/{project_id}", response=ProjectReportSchema, summary="获取项目详细报告")
def get_project_report(request, project_id: str):
    project = get_object_or_404(Project, id=project_id)

    def calc_iteration_detail(metric: IterationMetric) -> IterationDetailMetrics:
        sr_total = metric.need_break_sr_num
        sr_unbroken = metric.need_break_but_un_break_sr_num
        sr_breakdown_rate = (sr_total - sr_unbroken) / sr_total if sr_total > 0 else 0.0

        dr_total_break = metric.need_break_dr_num
        dr_unbroken = metric.need_break_but_un_break_dr_num
        dr_breakdown_rate = (dr_total_break - dr_unbroken) / dr_total_break if dr_total_break > 0 else 0.0

        ar_total = metric.ar_num
        dr_total = metric.dr_num

        ar_set_a_rate = metric.a_state_ar_num / ar_total if ar_total > 0 else 0.0
        dr_set_a_rate = metric.a_state_dr_num / dr_total if dr_total > 0 else 0.0

        ar_set_c_rate = (metric.c_state_ar_num + metric.a_state_ar_num) / ar_total if ar_total > 0 else 0.0
        dr_set_c_rate = (metric.c_state_dr_num + metric.a_state_dr_num) / dr_total if dr_total > 0 else 0.0

        return IterationDetailMetrics(
            sr_num=metric.sr_num,
            dr_num=metric.dr_num,
            ar_num=metric.ar_num,
            sr_breakdown_rate=round(sr_breakdown_rate, 4),
            dr_breakdown_rate=round(dr_breakdown_rate, 4),
            ar_set_a_rate=round(ar_set_a_rate, 4),
            dr_set_a_rate=round(dr_set_a_rate, 4),
            ar_set_c_rate=round(ar_set_c_rate, 4),
            dr_set_c_rate=round(dr_set_c_rate, 4),
        )
    
    # --- 1. Basic Info ---
    managers = ",".join([m.name for m in project.managers.all()])
    
    # --- 2. Code Quality ---
    cq_summary = None
    cq_details = None
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
        cq_details = get_project_quality_details(project_id)
    
    # --- 3. Iteration ---
    iter_summary = None
    iter_detail = None
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
                total_req = metric.sr_num + metric.dr_num + metric.ar_num
                iter_detail = calc_iteration_detail(metric)
                
                # Completion rate (Average of AR/DR Set C rates)
                ar_total = metric.ar_num
                dr_total = metric.dr_num
                
                ar_comp = (metric.c_state_ar_num + metric.a_state_ar_num) / ar_total if ar_total > 0 else 0.0
                dr_comp = (metric.c_state_dr_num + metric.a_state_dr_num) / dr_total if dr_total > 0 else 0.0
                
                completion_rate = (ar_comp + dr_comp) / 2 if (ar_total > 0 and dr_total > 0) else (ar_comp if ar_total > 0 else dr_comp)
                completion_rate = round(completion_rate * 100, 1)
        
        iter_score = completion_rate # 0-100
        
        iter_summary = IterationSummary(
            active_iterations=active_count,
            delayed_iterations=delayed_count,
            total_req_count=int(total_req),
            completion_rate=completion_rate
        )

    # --- 4. DTS ---
    dts_summary = None
    dts_score = 0
    dts_trend = []
    dts_team_di = None
    dts_team_di_trend = None
    
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
        
        def parse_percent(value) -> float | None:
            if value is None:
                return None
            if isinstance(value, (int, float)):
                return float(value)
            s = str(value).strip()
            if not s:
                return None
            if s.endswith('%'):
                s = s[:-1]
            try:
                return float(s)
            except Exception:
                return None

        start_date = today - timedelta(days=6)
        trend_dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
        trend_date_strs = [d.strftime('%Y-%m-%d') for d in trend_dates]

        rows = DtsData.objects.filter(
            team__in=dts_teams,
            record_date__gte=start_date,
            record_date__lte=today,
        ).values(
            'record_date',
            'fatal_num',
            'major_num',
            'minor_num',
            'suggestion_num',
            'solve_rate',
            'critical_solve_rate',
        )

        by_date = defaultdict(lambda: {"fatal": 0, "major": 0, "minor": 0, "suggestion": 0, "rates": [], "critical_rates": []})
        for r in rows:
            d = r["record_date"]
            agg = by_date[d]
            agg["fatal"] += int(r.get("fatal_num") or 0)
            agg["major"] += int(r.get("major_num") or 0)
            agg["minor"] += int(r.get("minor_num") or 0)
            agg["suggestion"] += int(r.get("suggestion_num") or 0)
            sr = parse_percent(r.get("solve_rate"))
            if sr is not None:
                agg["rates"].append(sr)
            cr = parse_percent(r.get("critical_solve_rate"))
            if cr is not None:
                agg["critical_rates"].append(cr)

        for d, date_str in zip(trend_dates, trend_date_strs):
            agg = by_date.get(d)
            if not agg:
                dts_trend.append(DtsTrendItem(
                    date=date_str,
                    critical=0,
                    major=0,
                    minor=0,
                    suggestion=0,
                    solve_rate=0.0,
                    critical_solve_rate=0.0,
                ))
                continue

            avg_sr = sum(agg["rates"]) / len(agg["rates"]) if agg["rates"] else 0.0
            avg_cr = sum(agg["critical_rates"]) / len(agg["critical_rates"]) if agg["critical_rates"] else 0.0
            dts_trend.append(DtsTrendItem(
                date=date_str,
                critical=agg["fatal"] + agg["major"],
                major=agg["major"],
                minor=agg["minor"],
                suggestion=agg["suggestion"],
                solve_rate=round(avg_sr, 1),
                critical_solve_rate=round(avg_cr, 1),
            ))

        dts_team_di = []
        for team in dts_teams:
            latest = DtsData.objects.filter(team=team).order_by('-record_date').first()
            if not latest:
                continue
            dts_team_di.append(DtsTeamDiItem(
                team_name=team.team_name,
                di=float(latest.di or 0),
                target_di=float(latest.target_di) if latest.target_di is not None else None,
            ))

        di_dates = trend_date_strs
        di_values_by_team = {t.id: [None] * len(di_dates) for t in dts_teams}
        date_index = {d: idx for idx, d in enumerate(di_dates)}

        di_qs = DtsData.objects.filter(team__in=dts_teams, record_date__gte=start_date, record_date__lte=today).select_related('team')
        for row in di_qs:
            d = row.record_date.strftime('%Y-%m-%d')
            idx = date_index.get(d)
            if idx is None:
                continue
            di_values_by_team.get(row.team_id, [None] * len(di_dates))[idx] = float(row.di or 0)

        di_series = []
        for t in dts_teams:
            values = di_values_by_team.get(t.id, [None] * len(di_dates))
            di_series.append(DtsTeamDiSeries(team_name=t.team_name, values=values))
        dts_team_di_trend = DtsTeamDiTrend(dates=di_dates, series=di_series)
            
    # --- 5. Milestones ---
    milestones_list = []
    ms_score = 100
    if hasattr(project, 'milestone') and project.enable_milestone:
        ms = project.milestone
        
        # Get active risks
        risk_qgs = set()
        risk_configs = MilestoneQGConfig.objects.filter(
             milestone=ms,
             enabled=True,
             is_deleted=False
        )
        active_risks = MilestoneRiskItem.objects.filter(
             config__in=risk_configs,
             status__in=['pending', 'confirmed'],
             is_deleted=False
        ).values_list('config__qg_name', flat=True)
        risk_qgs = set(active_risks)

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
                    status=status,
                    has_risk=f'QG{i}' in risk_qgs
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
        dts_team_di=dts_team_di,
        dts_team_di_trend=dts_team_di_trend,
        code_quality=cq_summary,
        code_quality_details=cq_details,
        iteration=iter_summary,
        iteration_detail=iter_detail,
        dts_summary=dts_summary
    )
