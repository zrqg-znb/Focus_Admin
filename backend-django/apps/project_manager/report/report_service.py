from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict
from asgiref.sync import sync_to_async
import asyncio

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
    DtsTeamTrend,
    DtsTeamTrendSeries,
    CodeQualitySummary, 
    IterationSummary, 
    DtsSummary,
    IterationDetailMetrics,
    QGNode
)

class ReportService:
    
    @staticmethod
    async def get_project(project_id: str) -> Project:
        return await sync_to_async(get_object_or_404)(Project, id=project_id)

    @staticmethod
    async def get_managers(project: Project) -> str:
        def _get_managers():
            return ",".join([m.name for m in project.managers.all()])
        return await sync_to_async(_get_managers)()

    @staticmethod
    async def get_code_quality_data(project: Project):
        if not project.enable_quality:
            return None, None, 100

        def _fetch_data():
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
            cq_score = max(0, 100 - (total_issues * 2) - (avg_dup * 2))
            
            summary = CodeQualitySummary(
                total_projects=1,
                total_modules=len(modules),
                total_loc=total_loc,
                total_issues=total_issues,
                avg_duplication_rate=round(avg_dup, 2),
                health_score=round(cq_score, 1)
            )
            # get_project_quality_details is likely sync, wrap it? 
            # Assuming get_project_quality_details performs DB queries.
            details = get_project_quality_details(str(project.id))
            return summary, details, cq_score

        return await sync_to_async(_fetch_data)()

    @staticmethod
    async def get_iteration_data(project: Project):
        if not project.enable_iteration:
            return None, None, 100

        def _fetch_data():
            current_iter = Iteration.objects.filter(project=project, is_current=True).first()
            active_count = 1 if current_iter else 0
            
            today = timezone.now().date()
            delayed_count = 0
            if current_iter and current_iter.end_date < today:
                delayed_count = 1
                
            total_req = 0
            completion_rate = 0.0
            iter_detail = None
            
            if current_iter:
                metric = IterationMetric.objects.filter(iteration=current_iter).order_by('-record_date').first()
                if metric:
                    total_req = metric.sr_num + metric.dr_num + metric.ar_num
                    
                    # calc_iteration_detail logic inline or helper
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

                    iter_detail = IterationDetailMetrics(
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
                    
                    ar_comp = (metric.c_state_ar_num + metric.a_state_ar_num) / ar_total if ar_total > 0 else 0.0
                    dr_comp = (metric.c_state_dr_num + metric.a_state_dr_num) / dr_total if dr_total > 0 else 0.0
                    
                    completion_rate = (ar_comp + dr_comp) / 2 if (ar_total > 0 and dr_total > 0) else (ar_comp if ar_total > 0 else dr_comp)
                    completion_rate = round(completion_rate * 100, 1)
            
            iter_score = completion_rate
            
            summary = IterationSummary(
                active_iterations=active_count,
                delayed_iterations=delayed_count,
                total_req_count=int(total_req),
                completion_rate=completion_rate
            )
            return summary, iter_detail, iter_score

        return await sync_to_async(_fetch_data)()

    @staticmethod
    async def get_dts_data(project: Project):
        if not project.enable_dts:
            return None, [], None, None, None, None, None, 100

        def _fetch_data():
            dts_teams = DtsTeam.objects.filter(project=project)
            base_teams = dts_teams.filter(parent_team__isnull=True)
            if not base_teams.exists():
                base_teams = dts_teams
            today = timezone.now().date()
            dts_data_qs = DtsData.objects.filter(team__in=base_teams, record_date=today)
            
            dts_agg = dts_data_qs.aggregate(
                total=Sum('major_num') + Sum('minor_num') + Sum('suggestion_num') + Sum('fatal_num'),
                critical=Sum('fatal_num')
            )
            
            rates = []
            for d in dts_data_qs:
                try:
                    rates.append(float(d.solve_rate.replace('%', '')))
                except:
                    pass
            avg_rate = sum(rates) / len(rates) if rates else 0.0
            dts_score = avg_rate
            
            dts_summary = DtsSummary(
                total_issues=dts_agg.get('total') or 0,
                critical_issues=dts_agg.get('critical') or 0,
                avg_solve_time=2.5,
                solve_rate=round(avg_rate, 1)
            )
            
            # Trend (aggregated)
            start_date = today - timedelta(days=6)
            trend_dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
            trend_date_strs = [d.strftime('%Y-%m-%d') for d in trend_dates]

            rows = DtsData.objects.filter(
                team__in=base_teams,
                record_date__gte=start_date,
                record_date__lte=today,
            ).values(
                'record_date', 'fatal_num', 'major_num', 'minor_num', 
                'suggestion_num', 'solve_rate', 'critical_solve_rate'
            )

            def parse_percent(value):
                if value is None: return None
                if isinstance(value, (int, float)): return float(value)
                s = str(value).strip()
                if not s: return None
                if s.endswith('%'): s = s[:-1]
                try: return float(s)
                except: return None

            by_date = defaultdict(lambda: {"fatal": 0, "major": 0, "minor": 0, "suggestion": 0, "rates": [], "critical_rates": []})
            for r in rows:
                d = r["record_date"]
                agg = by_date[d]
                agg["fatal"] += int(r.get("fatal_num") or 0)
                agg["major"] += int(r.get("major_num") or 0)
                agg["minor"] += int(r.get("minor_num") or 0)
                agg["suggestion"] += int(r.get("suggestion_num") or 0)
                sr = parse_percent(r.get("solve_rate"))
                if sr is not None: agg["rates"].append(sr)
                cr = parse_percent(r.get("critical_solve_rate"))
                if cr is not None: agg["critical_rates"].append(cr)

            dts_trend = []
            for d, date_str in zip(trend_dates, trend_date_strs):
                agg = by_date.get(d)
                if not agg:
                    dts_trend.append(DtsTrendItem(
                        date=date_str, critical=0, major=0, minor=0, suggestion=0, 
                        solve_rate=0.0, critical_solve_rate=0.0
                    ))
                    continue

                avg_sr = sum(agg["rates"]) / len(agg["rates"]) if agg["rates"] else 0.0
                avg_cr = sum(agg["critical_rates"]) / len(agg["critical_rates"]) if agg["critical_rates"] else 0.0
                dts_trend.append(DtsTrendItem(
                    date=date_str,
                    critical=agg["fatal"],
                    major=agg["major"],
                    minor=agg["minor"],
                    suggestion=agg["suggestion"],
                    solve_rate=round(avg_sr, 1),
                    critical_solve_rate=round(avg_cr, 1),
                ))

            # Team Issue Trend & Solve Rate Trend
            date_index = {d: idx for idx, d in enumerate(trend_date_strs)}
            issue_values_by_team = {t.id: [0.0] * len(trend_date_strs) for t in dts_teams}
            solve_rate_by_team = {t.id: [None] * len(trend_date_strs) for t in dts_teams}
            critical_rate_by_team = {t.id: [None] * len(trend_date_strs) for t in dts_teams}

            team_rows = DtsData.objects.filter(
                team__in=dts_teams,
                record_date__gte=start_date,
                record_date__lte=today,
            ).values(
                'team_id',
                'record_date',
                'fatal_num',
                'major_num',
                'minor_num',
                'suggestion_num',
                'solve_rate',
                'critical_solve_rate',
            )

            for row in team_rows:
                date_str = row['record_date'].strftime('%Y-%m-%d')
                idx = date_index.get(date_str)
                if idx is None:
                    continue
                total_issues = (
                    (row.get('fatal_num') or 0)
                    + (row.get('major_num') or 0)
                    + (row.get('minor_num') or 0)
                    + (row.get('suggestion_num') or 0)
                )
                issue_values_by_team.get(row['team_id'], [0.0] * len(trend_date_strs))[idx] = float(total_issues)
                solve_rate_by_team.get(row['team_id'], [None] * len(trend_date_strs))[idx] = parse_percent(row.get('solve_rate'))
                critical_rate_by_team.get(row['team_id'], [None] * len(trend_date_strs))[idx] = parse_percent(row.get('critical_solve_rate'))

            dts_team_issue_trend = DtsTeamTrend(
                dates=trend_date_strs,
                series=[
                    DtsTeamTrendSeries(team_name=t.team_name, values=issue_values_by_team.get(t.id, [0.0] * len(trend_date_strs)))
                    for t in dts_teams
                ],
            )
            dts_team_solve_rate_trend = DtsTeamTrend(
                dates=trend_date_strs,
                series=[
                    DtsTeamTrendSeries(team_name=t.team_name, values=solve_rate_by_team.get(t.id, [None] * len(trend_date_strs)))
                    for t in dts_teams
                ],
            )
            dts_team_critical_rate_trend = DtsTeamTrend(
                dates=trend_date_strs,
                series=[
                    DtsTeamTrendSeries(team_name=t.team_name, values=critical_rate_by_team.get(t.id, [None] * len(trend_date_strs)))
                    for t in dts_teams
                ],
            )

            # Team DI
            dts_team_di = []
            for team in dts_teams:
                latest = DtsData.objects.filter(team=team).order_by('-record_date').first()
                if not latest: continue
                dts_team_di.append(DtsTeamDiItem(
                    team_name=team.team_name,
                    di=float(latest.di or 0),
                    target_di=float(latest.target_di) if latest.target_di is not None else None,
                ))

            # DI Trend
            di_dates = trend_date_strs
            di_values_by_team = {t.id: [None] * len(di_dates) for t in dts_teams}
            date_index = {d: idx for idx, d in enumerate(di_dates)}

            di_qs = DtsData.objects.filter(team__in=dts_teams, record_date__gte=start_date, record_date__lte=today).select_related('team')
            for row in di_qs:
                d = row.record_date.strftime('%Y-%m-%d')
                idx = date_index.get(d)
                if idx is None: continue
                di_values_by_team.get(row.team_id, [None] * len(di_dates))[idx] = float(row.di or 0)

            di_series = []
            for t in dts_teams:
                values = di_values_by_team.get(t.id, [None] * len(di_dates))
                di_series.append(DtsTeamDiSeries(team_name=t.team_name, values=values))
            dts_team_di_trend = DtsTeamDiTrend(dates=di_dates, series=di_series)
            
            return (
                dts_summary,
                dts_trend,
                dts_team_di,
                dts_team_di_trend,
                dts_team_issue_trend,
                dts_team_solve_rate_trend,
                dts_team_critical_rate_trend,
                dts_score,
            )

        return await sync_to_async(_fetch_data)()

    @staticmethod
    async def get_milestone_data(project: Project):
        ms_score = 100
        # Check if project has milestone (reverse relation or O2O)
        # hasattr check in sync context
        def _fetch_data():
            if not (hasattr(project, 'milestone') and project.enable_milestone):
                return [], ms_score

            ms = project.milestone
            today = timezone.now().date()
            milestones_list = []
            
            risk_configs = MilestoneQGConfig.objects.filter(
                 milestone=ms, enabled=True, is_deleted=False
            )
            active_risks = MilestoneRiskItem.objects.filter(
                 config__in=risk_configs,
                 status__in=['pending', 'confirmed'],
                 is_deleted=False
            ).select_related('config')
            
            risk_map = {}
            for risk in active_risks:
                qg = risk.config.qg_name
                current = risk_map.get(qg)
                if risk.status == 'pending':
                    risk_map[qg] = 'pending'
                elif risk.status == 'confirmed':
                    if current != 'pending':
                        risk_map[qg] = 'confirmed'

            for i in range(1, 9):
                field_name = f'qg{i}_date'
                qg_date = getattr(ms, field_name)
                if qg_date:
                    status = 'pending'
                    if qg_date < today:
                        status = 'completed'
                    
                    qg_name = f'QG{i}'
                    risk_status = risk_map.get(qg_name)
                    
                    milestones_list.append(QGNode(
                        name=qg_name,
                        date=qg_date,
                        status=status,
                        has_risk=bool(risk_status),
                        risk_status=risk_status
                    ))
            
            return milestones_list, ms_score

        return await sync_to_async(_fetch_data)()
