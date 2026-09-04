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
        GovernanceProjectResponsibility.objects.select_related('project', 'responsibility').prefetch_related('responsibility__approvers'),
        **filters,
    )


def _serialize_project(item: GovernanceProject) -> dict[str, Any]:
    """序列化项目。"""
    return {
        'id': str(item.id), 'name': item.name, 'code': item.code, 'repository': item.repository,
        'branch': item.branch, 'description': item.description, 'is_active': item.is_active,
        'created_at': item.sys_create_datetime.isoformat() if item.sys_create_datetime else None,
    }


def _serialize_responsibility(item: GovernanceResponsibility) -> dict[str, Any]:
    """序列化责任田。"""
    approvers = list(item.approvers.all())
    return {
        'id': str(item.id), 'name': item.name, 'code': item.code, 'description': item.description,
        'is_active': item.is_active, 'owner': _display_user(item.owner),
        'approvers': [_display_user(user) for user in approvers],
    }


def _serialize_link(item: GovernanceProjectResponsibility) -> dict[str, Any]:
    """序列化项目责任田关联。"""
    return {
        'id': str(item.id), 'project_id': str(item.project_id), 'project_name': item.project.name,
        'responsibility_id': str(item.responsibility_id), 'responsibility_name': item.responsibility.name,
        'is_active': item.is_active, 'remark': item.remark,
    }


def list_projects(page: int, page_size: int, keyword: str = '') -> dict[str, Any]:
    """分页查询治理项目。"""
    queryset = GovernanceProject.objects.filter(is_deleted=False).order_by('name')
    if keyword.strip():
        queryset = queryset.filter(Q(name__icontains=keyword.strip()) | Q(code__icontains=keyword.strip()))
    return _page([_serialize_project(item) for item in queryset], page, page_size)


def save_project(user: User, project_id: str | None, payload) -> dict[str, Any]:
    """创建或更新治理项目。"""
    item = get_object_or_404(GovernanceProject, id=project_id, is_deleted=False) if project_id else GovernanceProject(sys_creator=user)
    item.name, item.code, item.repository, item.branch = payload.name.strip(), payload.code.strip(), payload.repository.strip(), payload.branch.strip() or 'master'
    item.description, item.is_active, item.sys_modifier = payload.description.strip(), payload.is_active, user
    try:
        item.save()
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
    queryset = GovernanceResponsibility.objects.filter(is_deleted=False).select_related('owner').prefetch_related('approvers').order_by('name')
    if keyword.strip():
        queryset = queryset.filter(Q(name__icontains=keyword.strip()) | Q(code__icontains=keyword.strip()))
    return _page([_serialize_responsibility(item) for item in queryset], page, page_size)


def save_responsibility(user: User, responsibility_id: str | None, payload) -> dict[str, Any]:
    """创建或更新责任田及审批人员。"""
    item = get_object_or_404(GovernanceResponsibility, id=responsibility_id, is_deleted=False) if responsibility_id else GovernanceResponsibility(sys_creator=user)
    item.name, item.code = payload.name.strip(), payload.code.strip()
    item.description, item.is_active, item.sys_modifier = payload.description.strip(), payload.is_active, user
    item.owner = User.objects.filter(id=payload.owner_id, is_deleted=False).first() if payload.owner_id else None
    try:
        with transaction.atomic():
            item.save()
            approvers = list(User.objects.filter(id__in=payload.approver_ids, is_deleted=False))
            if len(approvers) != len(set(payload.approver_ids)):
                raise HttpError(400, '存在无效的审批人员')
            item.approvers.set(approvers)
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
    """软删除项目责任田关联。"""
    item = get_object_or_404(GovernanceProjectResponsibility, id=link_id, is_deleted=False)
    item.is_deleted, item.sys_modifier = True, user
    item.save(update_fields=['is_deleted', 'sys_modifier', 'sys_update_datetime'])
    return {'id': str(item.id)}


def _report_counts(parsed: ParsedReport) -> dict[str, int]:
    """从实际解析结果生成五级严重度统计。"""
    counts = Counter(item.severity for item in parsed.findings)
    return {f'{severity}_count': counts.get(severity, 0) for severity in ('blocker', 'critical', 'major', 'minor', 'info')}


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
    except Exception as exc:
        report.status, report.error_message, report.completed_at = 'failed', str(exc), timezone.now()
        report.save(update_fields=['status', 'error_message', 'completed_at', 'sys_update_datetime'])
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
            if not finding.project_responsibility.responsibility.approvers.filter(id=approver.id, is_deleted=False).exists():
                raise HttpError(400, f'审批人不在责任田「{finding.project_responsibility.responsibility.name}」审批范围内')
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
    return _serialize_application(application)


def list_users() -> list[dict[str, Any]]:
    """返回可用于负责人和审批人选择的用户。"""
    users = User.objects.filter(is_deleted=False, user_status=1).order_by('name', 'username')
    return [_display_user(user) for user in users]


def list_audit_logs(application_id: str) -> list[dict[str, Any]]:
    """返回屏蔽申请审计历史。"""
    logs = GovernanceShieldAuditLog.objects.filter(application_id=application_id, is_deleted=False).select_related('operator').order_by('sys_create_datetime')
    return [{'id': str(item.id), 'action': item.action, 'operator': _display_user(item.operator), 'from_status': item.from_status, 'to_status': item.to_status, 'comment': item.comment, 'created_at': item.sys_create_datetime.isoformat() if item.sys_create_datetime else None} for item in logs]
