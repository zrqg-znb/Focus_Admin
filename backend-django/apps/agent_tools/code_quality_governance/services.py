import json
from collections import Counter
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.errors import HttpError

from core.user.user_model import User

from .models import (
    GovernanceFinding,
    GovernanceFindingOccurrence,
    GovernanceProject,
    GovernanceProjectResponsibility,
    GovernanceResponsibility,
    GovernanceScanReport,
    GovernanceShieldApplication,
    GovernanceShieldAuditLog,
    GovernanceCaretakerAuditLog,
)
from .parsers import ParsedReport, parse_report


def _display_user(user: User | None) -> dict[str, Any] | None:
    """统一序列化用户选项。"""
    if not user:
        return None
    return {'id': str(user.id), 'name': user.name or user.username, 'username': user.username}


def _page(queryset, page: int, page_size: int) -> dict[str, Any]:
    """对治理列表执行安全分页。"""
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 20), 1), 100)
    total = queryset.count() if hasattr(queryset, 'count') and not isinstance(queryset, list) else len(queryset)
    return {'items': list(queryset[(page - 1) * page_size:page * page_size]), 'total': total}


def _scope(project_id: str, responsibility_id: str, *, active_only: bool = True) -> GovernanceProjectResponsibility:
    """获取有效的项目责任田范围。"""
    filters = {'project_id': project_id, 'responsibility_id': responsibility_id, 'is_deleted': False}
    if active_only:
        filters['is_active'] = True
    return get_object_or_404(
        GovernanceProjectResponsibility.objects.select_related('project', 'responsibility').prefetch_related('responsibility__caretakers'),
        **filters,
    )


def _serialize_project(item: GovernanceProject) -> dict[str, Any]:
    """序列化项目。"""
    return {
        'id': str(item.id), 'name': item.name, 'code': item.code, 'description': item.description,
        'is_active': item.is_active,
        'created_at': item.sys_create_datetime.isoformat() if item.sys_create_datetime else None,
    }


def _serialize_responsibility(item: GovernanceResponsibility) -> dict[str, Any]:
    """序列化责任田。"""
    caretakers = list(item.caretakers.all())
    return {
        'id': str(item.id), 'name': item.name, 'code': item.code, 'description': item.description,
        'is_active': item.is_active, 'caretakers': [_display_user(user) for user in caretakers],
        'caretaker_count': len(caretakers),
    }


def _serialize_link(item: GovernanceProjectResponsibility) -> dict[str, Any]:
    """序列化项目责任田关联。"""
    return {
        'id': str(item.id), 'project_id': str(item.project_id), 'project_name': item.project.name,
        'responsibility_id': str(item.responsibility_id), 'responsibility_name': item.responsibility.name,
        'is_active': item.is_active, 'remark': item.remark,
        'finding_count': item.finding_count, 'normal_count': item.normal_count,
        'pending_count': item.pending_count, 'pending_application_count': item.pending_application_count,
        'shielded_count': item.shielded_count, 'last_scan_at': item.last_scan_at.isoformat() if item.last_scan_at else None,
        'last_scan_status': item.last_scan_status,
    }


def list_projects(page: int, page_size: int, keyword: str = '') -> dict[str, Any]:
    """分页查询治理项目。"""
    queryset = GovernanceProject.objects.filter(is_deleted=False).order_by('name')
    if keyword.strip():
        queryset = queryset.filter(Q(name__icontains=keyword.strip()) | Q(code__icontains=keyword.strip()))
    return _page([_serialize_project(item) for item in queryset], page, page_size)


def save_project(user: User, project_id: str | None, payload) -> dict[str, Any]:
    """创建或更新治理项目，并在新建时完成初始治理范围配置。"""
    item = get_object_or_404(GovernanceProject, id=project_id, is_deleted=False) if project_id else GovernanceProject(sys_creator=user)
    item.name, item.code = payload.name.strip(), payload.code.strip()
    item.description, item.is_active, item.sys_modifier = payload.description.strip(), payload.is_active, user
    try:
        with transaction.atomic():
            item.save()
            if not project_id and payload.initial_responsibility_ids:
                onboard_project(user, str(item.id), payload.initial_responsibility_ids)
    except Exception as exc:
        if 'unique' in str(exc).lower() or 'duplicate' in str(exc).lower():
            raise HttpError(409, '项目编码已存在') from exc
        raise
    return _serialize_project(item)


def delete_project(user: User, project_id: str) -> dict[str, str]:
    """软删除治理项目。"""
    item = get_object_or_404(GovernanceProject, id=project_id, is_deleted=False)
    item.is_deleted, item.sys_modifier = True, user
    item.save(update_fields=['is_deleted', 'sys_modifier', 'sys_update_datetime'])
    return {'id': str(item.id)}


def list_responsibilities(page: int, page_size: int, keyword: str = '') -> dict[str, Any]:
    """分页查询责任田。"""
    queryset = GovernanceResponsibility.objects.filter(is_deleted=False).prefetch_related('caretakers').order_by('name')
    if keyword.strip():
        queryset = queryset.filter(Q(name__icontains=keyword.strip()) | Q(code__icontains=keyword.strip()))
    return _page([_serialize_responsibility(item) for item in queryset], page, page_size)


def save_responsibility(user: User, responsibility_id: str | None, payload) -> dict[str, Any]:
    """创建或更新责任田及看护人。"""
    item = get_object_or_404(GovernanceResponsibility, id=responsibility_id, is_deleted=False) if responsibility_id else GovernanceResponsibility(sys_creator=user)
    item.name, item.code = payload.name.strip(), payload.code.strip()
    item.description, item.is_active, item.sys_modifier = payload.description.strip(), payload.is_active, user
    try:
        with transaction.atomic():
            item.save()
            caretakers = list(User.objects.filter(id__in=payload.caretaker_ids, is_deleted=False))
            if len(caretakers) != len(set(payload.caretaker_ids)):
                raise HttpError(400, '存在无效的看护人')
            old_ids = set(item.caretakers.values_list('id', flat=True))
            item.caretakers.set(caretakers)
            for caretaker in caretakers:
                if caretaker.id not in old_ids:
                    _write_caretaker_log(item, caretaker, user, 'add', '随责任田资料保存添加')
            for caretaker_id in old_ids - {user.id for user in caretakers}:
                caretaker = User.objects.filter(id=caretaker_id).first()
                if caretaker:
                    _write_caretaker_log(item, caretaker, user, 'remove', '随责任田资料保存移除')
    except HttpError:
        raise
    except Exception as exc:
        if 'unique' in str(exc).lower() or 'duplicate' in str(exc).lower():
            raise HttpError(409, '责任田编码已存在') from exc
        raise
    return _serialize_responsibility(item)


def delete_responsibility(user: User, responsibility_id: str) -> dict[str, str]:
    """软删除责任田。"""
    item = get_object_or_404(GovernanceResponsibility, id=responsibility_id, is_deleted=False)
    item.is_deleted, item.sys_modifier = True, user
    item.save(update_fields=['is_deleted', 'sys_modifier', 'sys_update_datetime'])
    return {'id': str(item.id)}


def list_links(page: int, page_size: int, keyword: str = '') -> dict[str, Any]:
    """分页查询项目责任田关联。"""
    queryset = GovernanceProjectResponsibility.objects.filter(is_deleted=False).select_related('project', 'responsibility').order_by('project__name', 'responsibility__name')
    if keyword.strip():
        queryset = queryset.filter(Q(project__name__icontains=keyword.strip()) | Q(responsibility__name__icontains=keyword.strip()))
    return _page([_serialize_link(item) for item in queryset], page, page_size)


def save_link(user: User, link_id: str | None, payload) -> dict[str, Any]:
    """创建或更新项目责任田关联。"""
    project = get_object_or_404(GovernanceProject, id=payload.project_id, is_deleted=False)
    responsibility = get_object_or_404(GovernanceResponsibility, id=payload.responsibility_id, is_deleted=False)
    item = get_object_or_404(GovernanceProjectResponsibility, id=link_id, is_deleted=False) if link_id else GovernanceProjectResponsibility(sys_creator=user)
    item.project, item.responsibility = project, responsibility
    item.is_active, item.remark, item.sys_modifier = payload.is_active, payload.remark.strip(), user
    try:
        item.save()
    except Exception as exc:
        if 'unique' in str(exc).lower() or 'duplicate' in str(exc).lower():
            raise HttpError(409, '项目与责任田关联已存在') from exc
        raise
    return _serialize_link(item)


def delete_link(user: User, link_id: str) -> dict[str, str]:
    """停用项目责任田关联并保留历史聚合数据。"""
    item = get_object_or_404(GovernanceProjectResponsibility, id=link_id, is_deleted=False)
    item.is_active, item.sys_modifier = False, user
    item.save(update_fields=['is_active', 'sys_modifier', 'sys_update_datetime'])
    return {'id': str(item.id)}


def onboard_project(user: User, project_id: str, responsibility_ids: list[str]) -> list[dict[str, Any]]:
    """为新项目建立初始治理范围，重复关系保持幂等。"""
    project = get_object_or_404(GovernanceProject, id=project_id, is_deleted=False)
    responsibilities = list(GovernanceResponsibility.objects.filter(id__in=responsibility_ids, is_deleted=False))
    if len(responsibilities) != len(set(responsibility_ids)):
        raise HttpError(400, '初始责任田中存在无效数据')
    result = []
    with transaction.atomic():
        for responsibility in responsibilities:
            link, _ = GovernanceProjectResponsibility.objects.get_or_create(
                project=project, responsibility=responsibility,
                defaults={'sys_creator': user, 'sys_modifier': user, 'is_active': True},
            )
            if not link.is_active:
                link.is_active, link.sys_modifier = True, user
                link.save(update_fields=['is_active', 'sys_modifier', 'sys_update_datetime'])
            result.append(_serialize_link(link))
    return result


def batch_save_links(user: User, payload) -> list[dict[str, Any]]:
    """在矩阵中批量建立项目与责任田关系。"""
    projects = list(GovernanceProject.objects.filter(id__in=payload.project_ids, is_deleted=False))
    responsibilities = list(GovernanceResponsibility.objects.filter(id__in=payload.responsibility_ids, is_deleted=False))
    if len(projects) != len(set(payload.project_ids)) or len(responsibilities) != len(set(payload.responsibility_ids)):
        raise HttpError(400, '批量关联包含无效的项目或责任田')
    result = []
    with transaction.atomic():
        for project in projects:
            for responsibility in responsibilities:
                link, _ = GovernanceProjectResponsibility.objects.get_or_create(
                    project=project, responsibility=responsibility,
                    defaults={'remark': payload.remark.strip(), 'sys_creator': user, 'sys_modifier': user},
                )
                if not link.is_active:
                    link.is_active, link.sys_modifier = True, user
                    link.save(update_fields=['is_active', 'sys_modifier', 'sys_update_datetime'])
                result.append(_serialize_link(link))
    return result


def matrix_data() -> dict[str, Any]:
    """返回项目责任田矩阵及其风险聚合信息。"""
    projects = list(GovernanceProject.objects.filter(is_deleted=False, is_active=True).order_by('name'))
    responsibilities = list(GovernanceResponsibility.objects.filter(is_deleted=False, is_active=True).order_by('name'))
    links = GovernanceProjectResponsibility.objects.filter(is_deleted=False).select_related('project', 'responsibility')
    link_map = {(str(item.project_id), str(item.responsibility_id)): _serialize_link(item) for item in links}
    return {
        'projects': [{'id': str(item.id), 'name': item.name, 'code': item.code} for item in projects],
        'responsibilities': [{'id': str(item.id), 'name': item.name, 'code': item.code} for item in responsibilities],
        'cells': list(link_map.values()),
    }


def _write_caretaker_log(responsibility, caretaker, operator, action: str, comment: str):
    """记录看护人变更，便于责任边界追溯。"""
    return GovernanceCaretakerAuditLog.objects.create(
        responsibility=responsibility, caretaker=caretaker, operator=operator,
        action=action, comment=comment, sys_creator=operator, sys_modifier=operator,
    )


def update_caretaker(user: User, responsibility_id: str, caretaker_id: str, action: str, comment: str = '') -> dict[str, Any]:
    """增删责任田看护人并记录审计日志。"""
    responsibility = get_object_or_404(GovernanceResponsibility, id=responsibility_id, is_deleted=False)
    caretaker = get_object_or_404(User, id=caretaker_id, is_deleted=False, user_status=1)
    with transaction.atomic():
        if action == 'add':
            responsibility.caretakers.add(caretaker)
        elif action == 'remove':
            responsibility.caretakers.remove(caretaker)
        else:
            raise HttpError(400, '看护人操作只能是 add 或 remove')
        _write_caretaker_log(responsibility, caretaker, user, action, comment.strip())
    return _serialize_responsibility(responsibility)


def _report_counts(parsed: ParsedReport) -> dict[str, int]:
    """从实际解析结果生成五级严重度统计。"""
    counts = Counter(item.severity for item in parsed.findings)
    return {f'{severity}_count': counts.get(severity, 0) for severity in ('blocker', 'critical', 'major', 'minor', 'info')}


def refresh_scope_aggregate(scope: GovernanceProjectResponsibility) -> None:
    """刷新关系单元格快照，避免项目和责任田详情重复扫描明细表。"""
    findings = GovernanceFinding.objects.filter(project_responsibility=scope, is_deleted=False)
    applications = GovernanceShieldApplication.objects.filter(project_responsibility=scope, is_deleted=False, status='Pending')
    report = GovernanceScanReport.objects.filter(project_responsibility=scope, is_deleted=False).order_by('-sys_create_datetime').first()
    scope.finding_count = findings.count()
    scope.normal_count = findings.filter(shield_status__in=['Normal', 'Rejected']).count()
    scope.pending_count = findings.filter(shield_status='Pending').count()
    scope.shielded_count = findings.filter(shield_status='Shielded').count()
    scope.pending_application_count = applications.count()
    scope.last_scan_at = report.sys_create_datetime if report else None
    scope.last_scan_status = report.status if report else ''
    scope.save(update_fields=['finding_count', 'normal_count', 'pending_count', 'shielded_count', 'pending_application_count', 'last_scan_at', 'last_scan_status', 'sys_update_datetime'])


def _serialize_finding(item: GovernanceFinding, *, occurrence: GovernanceFindingOccurrence | None = None) -> dict[str, Any]:
    """序列化问题及最近命中详情。"""
    row = {
        'id': str(item.id), 'project_id': str(item.project_responsibility.project_id),
        'project_name': item.project_responsibility.project.name,
        'responsibility_id': str(item.project_responsibility.responsibility_id),
        'responsibility_name': item.project_responsibility.responsibility.name,
        'identity_key': item.identity_key, 'issue_key': item.issue_key, 'fingerprint': item.fingerprint,
        'rule_id': item.rule_id, 'rule_version': item.rule_version, 'category': item.category,
        'severity': item.severity, 'shield_status': item.shield_status, 'latest_tool_name': item.latest_tool_name,
        'latest_file_path': item.latest_file_path, 'latest_line': item.latest_line, 'latest_message': item.latest_message,
        'first_seen_at': item.first_seen_at.isoformat() if item.first_seen_at else None,
        'last_seen_at': item.last_seen_at.isoformat() if item.last_seen_at else None,
    }
    if occurrence:
        row.update({
            'occurrence_id': str(occurrence.id), 'file_path': occurrence.file_path,
            'start_line': occurrence.start_line, 'end_line': occurrence.end_line,
            'message': occurrence.message, 'evidence': occurrence.evidence,
            'identity': occurrence.identity, 'legacy_fingerprints': occurrence.legacy_fingerprints,
            'confidence': occurrence.confidence, 'raw_finding': occurrence.raw_finding,
            'report_id': str(occurrence.report_id), 'tool_name': occurrence.report.tool_name,
            'report_complete': occurrence.report.complete,
        })
    return row


def ingest_report(user: User, project_id: str, responsibility_id: str, tool_name: str, payload: dict[str, Any], source: str = 'api') -> dict[str, Any]:
    """创建扫描报告并原子化写入问题命中。"""
    scope = _scope(project_id, responsibility_id)
    report = GovernanceScanReport.objects.create(
        project_responsibility=scope, repository=str(payload.get('repository') or ''), tool_name=tool_name.strip(),
        complete=True, raw_created_at=str(payload.get('created_at') or ''), raw_payload=payload,
        source=source, status='processing', sys_creator=user, sys_modifier=user,
    )
    try:
        parsed = parse_report(payload)
        now = timezone.now()
        counts = _report_counts(parsed)
        with transaction.atomic():
            report.complete = parsed.complete
            report.repository, report.raw_created_at = parsed.repository, parsed.raw_created_at
            report.status, report.completed_at = 'success', now
            report.finding_count = len(parsed.findings)
            for key, value in counts.items():
                setattr(report, key, value)
            report.save()
            for finding_data in parsed.findings:
                finding, created = GovernanceFinding.objects.get_or_create(
                    project_responsibility=scope, identity_key=finding_data.identity_key,
                    defaults={
                        'issue_key': finding_data.issue_key, 'fingerprint': finding_data.fingerprint,
                        'rule_id': finding_data.rule_id, 'rule_version': finding_data.rule_version,
                        'category': finding_data.category, 'severity': finding_data.severity,
                        'first_seen_at': now, 'last_seen_at': now, 'first_report': report, 'last_report': report,
                        'latest_tool_name': tool_name, 'latest_file_path': finding_data.file_path,
                        'latest_line': finding_data.start_line, 'latest_message': finding_data.message,
                        'sys_creator': user, 'sys_modifier': user,
                    },
                )
                if not created:
                    finding.last_seen_at, finding.last_report = now, report
                    finding.latest_tool_name, finding.latest_file_path = tool_name, finding_data.file_path
                    finding.latest_line, finding.latest_message = finding_data.start_line, finding_data.message
                    finding.issue_key = finding.issue_key or finding_data.issue_key
                    finding.fingerprint = finding_data.fingerprint or finding.fingerprint
                    finding.rule_id = finding_data.rule_id or finding.rule_id
                    finding.rule_version = finding_data.rule_version or finding.rule_version
                    finding.category = finding_data.category or finding.category
                    finding.severity = finding_data.severity
                    finding.sys_modifier = user
                    finding.save()
                GovernanceFindingOccurrence.objects.create(
                    report=report, finding=finding, file_path=finding_data.file_path,
                    start_line=finding_data.start_line, end_line=finding_data.end_line,
                    message=finding_data.message, evidence=finding_data.evidence, identity=finding_data.identity,
                    legacy_fingerprints=finding_data.legacy_fingerprints, confidence=finding_data.confidence,
                    raw_finding=finding_data.raw_finding, sys_creator=user, sys_modifier=user,
                )
            refresh_scope_aggregate(scope)
    except Exception as exc:
        report.status, report.error_message, report.completed_at = 'failed', str(exc), timezone.now()
        report.save(update_fields=['status', 'error_message', 'completed_at', 'sys_update_datetime'])
        refresh_scope_aggregate(scope)
        if isinstance(exc, ValueError):
            raise HttpError(422, str(exc)) from exc
        raise
    return serialize_report(report)


def serialize_report(item: GovernanceScanReport) -> dict[str, Any]:
    """序列化扫描报告摘要。"""
    return {
        'id': str(item.id), 'project_id': str(item.project_responsibility.project_id),
        'project_name': item.project_responsibility.project.name,
        'responsibility_id': str(item.project_responsibility.responsibility_id),
        'responsibility_name': item.project_responsibility.responsibility.name,
        'repository': item.repository, 'tool_name': item.tool_name, 'complete': item.complete,
        'created_at': item.raw_created_at, 'status': item.status, 'source': item.source,
        'finding_count': item.finding_count, 'blocker_count': item.blocker_count,
        'critical_count': item.critical_count, 'major_count': item.major_count,
        'minor_count': item.minor_count, 'info_count': item.info_count,
        'error_message': item.error_message, 'completed_at': item.completed_at.isoformat() if item.completed_at else None,
    }


def list_reports(page: int, page_size: int, project_id: str = '', responsibility_id: str = '') -> dict[str, Any]:
    """分页查询扫描报告。"""
    queryset = GovernanceScanReport.objects.filter(is_deleted=False).select_related('project_responsibility__project', 'project_responsibility__responsibility')
    if project_id:
        queryset = queryset.filter(project_responsibility__project_id=project_id)
    if responsibility_id:
        queryset = queryset.filter(project_responsibility__responsibility_id=responsibility_id)
    return _page([serialize_report(item) for item in queryset], page, page_size)


def get_report(report_id: str) -> dict[str, Any]:
    """查询单份扫描报告及其原始数据。"""
    item = get_object_or_404(GovernanceScanReport.objects.select_related('project_responsibility__project', 'project_responsibility__responsibility'), id=report_id, is_deleted=False)
    result = serialize_report(item)
    result['raw_payload'] = item.raw_payload
    return result


def list_findings(page: int, page_size: int, project_id: str = '', responsibility_id: str = '', tool_name: str = '', severity: str = '', shield_status: str = '', keyword: str = '') -> dict[str, Any]:
    """分页查询最近问题明细。"""
    queryset = GovernanceFinding.objects.filter(is_deleted=False).select_related('project_responsibility__project', 'project_responsibility__responsibility')
    if project_id:
        queryset = queryset.filter(project_responsibility__project_id=project_id)
    if responsibility_id:
        queryset = queryset.filter(project_responsibility__responsibility_id=responsibility_id)
    if tool_name:
        queryset = queryset.filter(latest_tool_name=tool_name)
    if severity:
        queryset = queryset.filter(severity=severity)
    if shield_status:
        queryset = queryset.filter(shield_status=shield_status)
    if keyword.strip():
        value = keyword.strip()
        queryset = queryset.filter(Q(latest_message__icontains=value) | Q(latest_file_path__icontains=value) | Q(rule_id__icontains=value) | Q(identity_key__icontains=value))
    return _page([_serialize_finding(item) for item in queryset], page, page_size)


def get_finding(finding_id: str) -> dict[str, Any]:
    """查询问题详情及最近命中原始字段。"""
    finding = get_object_or_404(GovernanceFinding.objects.select_related('project_responsibility__project', 'project_responsibility__responsibility'), id=finding_id, is_deleted=False)
    occurrence = finding.occurrences.select_related('report').order_by('-sys_create_datetime').first()
    result = _serialize_finding(finding, occurrence=occurrence)
    result['applications'] = [_serialize_application(item) for item in finding.shield_applications.select_related('applicant', 'approver')]
    result['occurrences'] = [_serialize_finding(finding, occurrence=item) for item in finding.occurrences.select_related('report').order_by('-sys_create_datetime')[:30]]
    return result


def dashboard_summary(project_id: str = '', responsibility_id: str = '') -> dict[str, Any]:
    """统计治理看板核心指标及分组数据。"""
    findings = GovernanceFinding.objects.filter(is_deleted=False)
    reports = GovernanceScanReport.objects.filter(is_deleted=False, status='success')
    applications = GovernanceShieldApplication.objects.filter(is_deleted=False)
    scope_filter = {}
    if project_id:
        scope_filter['project_responsibility__project_id'] = project_id
    if responsibility_id:
        scope_filter['project_responsibility__responsibility_id'] = responsibility_id
    findings, applications = findings.filter(**scope_filter), applications.filter(**scope_filter)
    reports = reports.filter(**scope_filter)
    severity = dict(findings.values('severity').annotate(count=Count('id')).values_list('severity', 'count'))
    project_rank = list(findings.values('project_responsibility__project__name').annotate(count=Count('id')).order_by('-count')[:10])
    responsibility_rank = list(findings.values('project_responsibility__responsibility__name').annotate(count=Count('id')).order_by('-count')[:10])
    tool_rank = list(findings.values('latest_tool_name').annotate(count=Count('id')).order_by('-count'))
    latest = reports.order_by('-sys_create_datetime').first()
    return {
        'total': findings.count(), 'normal': findings.filter(shield_status__in=['Normal', 'Rejected']).count(),
        'pending': findings.filter(shield_status='Pending').count(), 'shielded': findings.filter(shield_status='Shielded').count(),
        'pending_applications': applications.filter(status='Pending').count(), 'severity': severity,
        'project_rank': [{'name': item['project_responsibility__project__name'], 'count': item['count']} for item in project_rank],
        'responsibility_rank': [{'name': item['project_responsibility__responsibility__name'], 'count': item['count']} for item in responsibility_rank],
        'tool_rank': [{'name': item['latest_tool_name'] or '未命名工具', 'count': item['count']} for item in tool_rank],
        'latest_report': serialize_report(latest) if latest else None,
    }


def dashboard_trend(project_id: str = '', responsibility_id: str = '', days: int = 30) -> list[dict[str, Any]]:
    """返回最近指定天数的扫描问题趋势。"""
    days = min(max(int(days or 30), 7), 90)
    queryset = GovernanceScanReport.objects.filter(is_deleted=False, status='success', sys_create_datetime__gte=timezone.now() - timedelta(days=days))
    if project_id:
        queryset = queryset.filter(project_responsibility__project_id=project_id)
    if responsibility_id:
        queryset = queryset.filter(project_responsibility__responsibility_id=responsibility_id)
    totals: Counter[str] = Counter()
    for report in queryset.only('sys_create_datetime', 'finding_count'):
        totals[report.sys_create_datetime.date().isoformat()] += report.finding_count
    today = timezone.localdate()
    return [{'date': (today - timedelta(days=days - index - 1)).isoformat(), 'count': totals.get((today - timedelta(days=days - index - 1)).isoformat(), 0)} for index in range(days)]


def _serialize_application(item: GovernanceShieldApplication) -> dict[str, Any]:
    """序列化屏蔽申请及问题上下文。"""
    finding = item.finding
    return {
        'id': str(item.id), 'finding_id': str(item.finding_id), 'project_id': str(item.project_responsibility.project_id),
        'project_name': item.project_responsibility.project.name, 'responsibility_id': str(item.project_responsibility.responsibility_id),
        'responsibility_name': item.project_responsibility.responsibility.name, 'applicant': _display_user(item.applicant),
        'approver': _display_user(item.approver), 'reason': item.reason, 'status': item.status,
        'audit_comment': item.audit_comment, 'approved_at': item.approved_at.isoformat() if item.approved_at else None,
        'created_at': item.sys_create_datetime.isoformat() if item.sys_create_datetime else None,
        'severity': finding.severity, 'file_path': finding.latest_file_path, 'rule_id': finding.rule_id,
        'message': finding.latest_message,
    }


def create_application(user: User, payload) -> list[dict[str, Any]]:
    """批量创建屏蔽申请并同步问题状态。"""
    if not payload.finding_ids or not payload.reason.strip():
        raise HttpError(400, '至少选择一个问题并填写屏蔽理由')
    approver = get_object_or_404(User, id=payload.approver_id, is_deleted=False)
    created: list[GovernanceShieldApplication] = []
    with transaction.atomic():
        findings = list(GovernanceFinding.objects.select_for_update().select_related('project_responsibility__responsibility').filter(id__in=payload.finding_ids, is_deleted=False))
        if len(findings) != len(set(payload.finding_ids)):
            raise HttpError(404, '存在无效问题')
        for finding in findings:
            if not User.objects.filter(id=approver.id, is_deleted=False, user_status=1).exists():
                raise HttpError(400, '指定审批人不是有效系统用户')
            if finding.shield_status == 'Shielded':
                raise HttpError(400, '已屏蔽问题不能重复申请')
            if GovernanceShieldApplication.objects.filter(finding=finding, status='Pending', is_deleted=False).exists():
                raise HttpError(409, '存在待审批申请，不能重复提交')
            application = GovernanceShieldApplication.objects.create(
                project_responsibility=finding.project_responsibility, finding=finding, applicant=user,
                approver=approver, reason=payload.reason.strip(), status='Pending', sys_creator=user, sys_modifier=user,
            )
            finding.shield_status, finding.sys_modifier = 'Pending', user
            finding.save(update_fields=['shield_status', 'sys_modifier', 'sys_update_datetime'])
            GovernanceShieldAuditLog.objects.create(application=application, action='create', operator=user, from_status='', to_status='Pending', comment=payload.reason.strip(), sys_creator=user, sys_modifier=user)
            created.append(application)
        for scope in {finding.project_responsibility for finding in findings}:
            refresh_scope_aggregate(scope)
    return [_serialize_application(item) for item in created]


def list_applications(user: User, page: int, page_size: int, mode: str = 'pending', status: str = '', project_id: str = '', responsibility_id: str = '') -> dict[str, Any]:
    """分页查询我的审批或申请记录。"""
    queryset = GovernanceShieldApplication.objects.filter(is_deleted=False).select_related('project_responsibility__project', 'project_responsibility__responsibility', 'finding', 'applicant', 'approver')
    if mode == 'my_audit':
        queryset = queryset.filter(approver=user)
    elif mode == 'my_apply':
        queryset = queryset.filter(applicant=user)
    if status:
        queryset = queryset.filter(status=status)
    if project_id:
        queryset = queryset.filter(project_responsibility__project_id=project_id)
    if responsibility_id:
        queryset = queryset.filter(project_responsibility__responsibility_id=responsibility_id)
    return _page([_serialize_application(item) for item in queryset], page, page_size)


def audit_application(user: User, application_id: str, status: str, comment: str) -> dict[str, Any]:
    """事务化审批屏蔽申请。"""
    if status not in {'Approved', 'Rejected'}:
        raise HttpError(400, '审批状态只能是 Approved 或 Rejected')
    with transaction.atomic():
        application = get_object_or_404(GovernanceShieldApplication.objects.select_for_update().select_related('finding', 'project_responsibility__responsibility'), id=application_id, is_deleted=False)
        if application.approver_id != user.id:
            raise HttpError(403, '只有指定审批人可以处理该申请')
        if application.status != 'Pending':
            raise HttpError(409, '该申请已处理，不能重复审批')
        old_status = application.status
        application.status, application.audit_comment, application.approved_at, application.sys_modifier = status, comment.strip(), timezone.now(), user
        application.save(update_fields=['status', 'audit_comment', 'approved_at', 'sys_modifier', 'sys_update_datetime'])
        finding = application.finding
        finding.shield_status, finding.sys_modifier = ('Shielded' if status == 'Approved' else 'Rejected'), user
        finding.save(update_fields=['shield_status', 'sys_modifier', 'sys_update_datetime'])
        GovernanceShieldAuditLog.objects.create(application=application, action='approve' if status == 'Approved' else 'reject', operator=user, from_status=old_status, to_status=status, comment=comment.strip(), sys_creator=user, sys_modifier=user)
        refresh_scope_aggregate(application.project_responsibility)
    return _serialize_application(application)


def list_users() -> list[dict[str, Any]]:
    """返回可用于负责人和审批人选择的用户。"""
    users = User.objects.filter(is_deleted=False, user_status=1).order_by('name', 'username')
    return [_display_user(user) for user in users]


def list_audit_logs(application_id: str) -> list[dict[str, Any]]:
    """返回屏蔽申请审计历史。"""
    logs = GovernanceShieldAuditLog.objects.filter(application_id=application_id, is_deleted=False).select_related('operator').order_by('sys_create_datetime')
    return [{'id': str(item.id), 'action': item.action, 'operator': _display_user(item.operator), 'from_status': item.from_status, 'to_status': item.to_status, 'comment': item.comment, 'created_at': item.sys_create_datetime.isoformat() if item.sys_create_datetime else None} for item in logs]


def _scope_summary(scope: GovernanceProjectResponsibility) -> dict[str, Any]:
    """序列化关系单元格，作为项目/责任田详情的统一聚合结构。"""
    return _serialize_link(scope)


def project_overview(project_id: str) -> dict[str, Any]:
    """返回项目 360° 概览及责任田、扫描和问题聚合。"""
    project = get_object_or_404(GovernanceProject, id=project_id, is_deleted=False)
    links = list(GovernanceProjectResponsibility.objects.filter(project=project, is_deleted=False).select_related('responsibility').order_by('responsibility__name'))
    reports = GovernanceScanReport.objects.filter(project_responsibility__project=project, is_deleted=False).select_related('project_responsibility__responsibility').order_by('-sys_create_datetime')[:10]
    findings = GovernanceFinding.objects.filter(project_responsibility__project=project, is_deleted=False)
    return {
        'project': _serialize_project(project),
        'finding_count': findings.count(),
        'normal_count': findings.filter(shield_status__in=['Normal', 'Rejected']).count(),
        'pending_application_count': GovernanceShieldApplication.objects.filter(project_responsibility__project=project, status='Pending', is_deleted=False).count(),
        'severity': dict(findings.values('severity').annotate(count=Count('id')).values_list('severity', 'count')),
        'responsibilities': [_scope_summary(item) for item in links],
        'recent_reports': [serialize_report(item) for item in reports],
    }


def responsibility_overview(responsibility_id: str) -> dict[str, Any]:
    """返回责任田 360° 概览及看护人、项目和问题聚合。"""
    responsibility = get_object_or_404(GovernanceResponsibility.objects.prefetch_related('caretakers'), id=responsibility_id, is_deleted=False)
    links = list(GovernanceProjectResponsibility.objects.filter(responsibility=responsibility, is_deleted=False).select_related('project').order_by('project__name'))
    findings = GovernanceFinding.objects.filter(project_responsibility__responsibility=responsibility, is_deleted=False)
    reports = GovernanceScanReport.objects.filter(project_responsibility__responsibility=responsibility, is_deleted=False).select_related('project_responsibility__project').order_by('-sys_create_datetime')[:10]
    return {
        'responsibility': _serialize_responsibility(responsibility),
        'finding_count': findings.count(),
        'normal_count': findings.filter(shield_status__in=['Normal', 'Rejected']).count(),
        'pending_application_count': GovernanceShieldApplication.objects.filter(project_responsibility__responsibility=responsibility, status='Pending', is_deleted=False).count(),
        'severity': dict(findings.values('severity').annotate(count=Count('id')).values_list('severity', 'count')),
        'projects': [_scope_summary(item) for item in links],
        'recent_reports': [serialize_report(item) for item in reports],
    }


def workbench_summary(user: User) -> dict[str, Any]:
    """返回治理工作台首屏指标、待办、异常和风险排行。"""
    projects = GovernanceProject.objects.filter(is_deleted=False, is_active=True)
    responsibilities = GovernanceResponsibility.objects.filter(is_deleted=False, is_active=True)
    links = GovernanceProjectResponsibility.objects.filter(is_deleted=False, is_active=True)
    findings = GovernanceFinding.objects.filter(is_deleted=False)
    applications = GovernanceShieldApplication.objects.filter(is_deleted=False, status='Pending')
    reports = GovernanceScanReport.objects.filter(is_deleted=False)
    risk_findings = findings.filter(shield_status__in=['Normal', 'Rejected'])
    recent_reports = reports.filter(status='failed').order_by('-sys_create_datetime')[:5]
    incomplete_reports = reports.filter(status='success', complete=False).order_by('-sys_create_datetime')[:5]
    rank = list(risk_findings.values('project_responsibility__project__name').annotate(count=Count('id')).order_by('-count')[:8])
    responsibility_rank = list(risk_findings.values('project_responsibility__responsibility__name').annotate(count=Count('id')).order_by('-count')[:8])
    todos = applications.filter(approver=user).select_related('project_responsibility__project', 'project_responsibility__responsibility', 'finding', 'applicant').order_by('finding__severity', 'sys_create_datetime')[:8]
    return {
        'project_count': projects.count(), 'responsibility_count': responsibilities.count(), 'link_count': links.count(),
        'finding_count': findings.count(), 'normal_count': risk_findings.count(), 'pending_application_count': applications.count(),
        'shielded_count': findings.filter(shield_status='Shielded').count(),
        'my_todo_count': applications.filter(approver=user).count(),
        'risk_projects': [{'name': item['project_responsibility__project__name'], 'count': item['count']} for item in rank],
        'risk_responsibilities': [{'name': item['project_responsibility__responsibility__name'], 'count': item['count']} for item in responsibility_rank],
        'scan_exceptions': [serialize_report(item) for item in list(recent_reports) + list(incomplete_reports)],
        'my_todos': [_serialize_application(item) for item in todos],
        'recent_reports': [serialize_report(item) for item in reports.order_by('-sys_create_datetime')[:8]],
    }


def workbench_todos(user: User) -> dict[str, Any]:
    """返回待我审批、我的申请和扫描异常的统一待办。"""
    return {
        'my_audit': list_applications(user, 1, 20, 'my_audit', 'Pending')['items'],
        'my_apply': list_applications(user, 1, 20, 'my_apply')['items'],
        'scan_exceptions': [serialize_report(item) for item in GovernanceScanReport.objects.filter(is_deleted=False).exclude(status='success', complete=True).order_by('-sys_create_datetime')[:20]],
    }


def workbench_risk_ranking() -> dict[str, Any]:
    """返回项目和责任田待治理问题风险排行。"""
    base = GovernanceFinding.objects.filter(is_deleted=False, shield_status__in=['Normal', 'Rejected'])
    return {
        'projects': list(base.values('project_responsibility__project_id', 'project_responsibility__project__name').annotate(count=Count('id')).order_by('-count')[:20]),
        'responsibilities': list(base.values('project_responsibility__responsibility_id', 'project_responsibility__responsibility__name').annotate(count=Count('id')).order_by('-count')[:20]),
    }
