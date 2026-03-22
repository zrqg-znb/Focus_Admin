from __future__ import annotations

import json
import time

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.errors import HttpError

from apps.deepaudit.analysis_payload import get_analysis_issue_count, get_analysis_quality_score, normalize_analysis_result
from apps.deepaudit.constants import ISSUE_STATUS_FALSE_POSITIVE, ISSUE_STATUS_OPEN, ISSUE_STATUS_RESOLVED
from apps.deepaudit.permissions import accessible_project_queryset, get_user_id, require_project_role, serialize_user_brief
from apps.deepaudit.reporting import ReportBuilder
from apps.deepaudit.runtime import cleanup_runtime_workspace, prepare_workspace, run_heuristic_scan
from apps.deepaudit.scan_profile import resolve_scan_profile, serialize_scan_profile
from apps.deepaudit.scan_task.scan_task_model import AuditArtifact, AuditIssue, AuditTask, InstantAnalysisRecord
from apps.deepaudit.serialization import format_datetime_text, normalize_json_payload
from apps.deepaudit.storage import save_json_artifact, save_report_file
from apps.deepaudit.user_config import user_config_services


ACTIVE_TASK_STATUSES = {'pending', 'running'}
VALID_ISSUE_STATUSES = {ISSUE_STATUS_OPEN, ISSUE_STATUS_RESOLVED, ISSUE_STATUS_FALSE_POSITIVE}


def serialize_issue(issue: AuditIssue) -> dict:
    return {
        'id': str(issue.id),
        'task_id': str(issue.task_id),
        'file_path': issue.file_path,
        'line_number': issue.line_number,
        'column_number': issue.column_number,
        'issue_type': issue.issue_type,
        'severity': issue.severity,
        'title': issue.title,
        'message': issue.message,
        'description': issue.description,
        'suggestion': issue.suggestion,
        'code_snippet': issue.code_snippet,
        'ai_explanation': issue.ai_explanation or {},
        'status': issue.status,
        'resolved_by': str(issue.resolved_by_id) if issue.resolved_by_id else None,
        'resolved_at': format_datetime_text(issue.resolved_at),
        'sys_create_datetime': format_datetime_text(issue.sys_create_datetime),
        'sys_update_datetime': format_datetime_text(issue.sys_update_datetime),
    }


def serialize_task(task: AuditTask, include_issues: bool = False) -> dict:
    project = task.project
    payload = {
        'id': str(task.id),
        'project_id': str(task.project_id),
        'project_name': project.name if project else '',
        'created_by': str(task.created_by_id),
        'created_by_name': serialize_user_brief(task.created_by).get('name') if task.created_by else None,
        'task_type': task.task_type,
        'status': task.status,
        'branch_name': task.branch_name,
        'exclude_patterns': list(task.exclude_patterns or []),
        'scan_config': dict(task.scan_config or {}),
        'total_files': task.total_files,
        'scanned_files': task.scanned_files,
        'total_lines': task.total_lines,
        'issues_count': task.issues_count,
        'quality_score': task.quality_score,
        'started_at': format_datetime_text(task.started_at),
        'completed_at': format_datetime_text(task.completed_at),
        'error_message': task.error_message,
        'sys_create_datetime': format_datetime_text(task.sys_create_datetime),
        'sys_update_datetime': format_datetime_text(task.sys_update_datetime),
    }
    payload['summary'] = {
        'severity_distribution': {
            'critical': task.issues.filter(severity='critical', is_deleted=False).count(),
            'high': task.issues.filter(severity='high', is_deleted=False).count(),
            'medium': task.issues.filter(severity='medium', is_deleted=False).count(),
            'low': task.issues.filter(severity='low', is_deleted=False).count(),
        },
        'status_distribution': {
            'open': task.issues.filter(status='open', is_deleted=False).count(),
            'resolved': task.issues.filter(status='resolved', is_deleted=False).count(),
            'false_positive': task.issues.filter(status='false_positive', is_deleted=False).count(),
        },
    }
    if include_issues:
        payload['issues'] = [serialize_issue(item) for item in task.issues.filter(is_deleted=False).order_by('-sys_create_datetime')]
    return payload


def list_tasks(user, *, project_id: str = '', status: str = '', task_type: str = '', page: int = 1, page_size: int = 20) -> dict:
    queryset = AuditTask.objects.filter(is_deleted=False).select_related('project', 'created_by')
    if project_id:
        access = require_project_role(user, project_id, min_role='viewer')
        queryset = queryset.filter(project=access.project)
    else:
        queryset = queryset.filter(project__in=accessible_project_queryset(user))
    if status:
        queryset = queryset.filter(status=status)
    if task_type:
        queryset = queryset.filter(task_type=task_type)
    queryset = queryset.order_by('-sys_create_datetime')
    total = queryset.count()
    start = max(page - 1, 0) * page_size
    items = [serialize_task(item) for item in queryset[start:start + page_size]]
    return {'items': items, 'total': total}


def get_task(user, task_id: str) -> AuditTask:
    task = get_object_or_404(AuditTask.objects.select_related('project', 'created_by'), id=task_id, is_deleted=False)
    require_project_role(user, task.project, min_role='viewer')
    return task


def create_task(user, payload: dict, *, task_type: str) -> AuditTask:
    access = require_project_role(user, payload.get('project_id'), min_role='member')
    scan_config = {
        'file_paths': payload.get('file_paths') or [],
        'rule_set_id': payload.get('rule_set_id'),
        'prompt_template_id': payload.get('prompt_template_id'),
        'include_tests': bool(payload.get('include_tests', False)),
        'include_docs': bool(payload.get('include_docs', False)),
        'max_file_size': payload.get('max_file_size') or 0,
        'analysis_depth': payload.get('analysis_depth') or 'standard',
    }
    profile = resolve_scan_profile(user, scan_config, strict=True)
    effective_profile = serialize_scan_profile(profile)
    scan_config['rule_set_id'] = scan_config.get('rule_set_id') or effective_profile.get('rule_set_id')
    scan_config['prompt_template_id'] = scan_config.get('prompt_template_id') or effective_profile.get('prompt_template_id')
    scan_config['effective_profile'] = effective_profile
    task = AuditTask.objects.create(
        project=access.project,
        created_by=user,
        task_type=task_type,
        status='pending',
        branch_name=(payload.get('branch_name') or access.project.default_branch or 'main'),
        exclude_patterns=payload.get('exclude_patterns') or [],
        scan_config=scan_config,
        sys_creator=user,
        sys_modifier=user,
    )
    return task


def cancel_task(user, task_id: str) -> bool:
    task = get_task(user, task_id)
    if task.status not in ACTIVE_TASK_STATUSES:
        return True
    task.status = 'cancelled'
    task.completed_at = timezone.now()
    task.sys_modifier = user
    task.save(update_fields=['status', 'completed_at', 'sys_modifier', 'sys_update_datetime'])
    return True


def mark_dispatch_failed(task: AuditTask, message: str) -> AuditTask:
    task.status = 'failed'
    task.error_message = message
    task.completed_at = timezone.now()
    if task.created_by_id:
        task.sys_modifier = task.created_by
    task.save(update_fields=['status', 'error_message', 'completed_at', 'sys_modifier', 'sys_update_datetime'])
    return task


def list_issues(user, task_id: str, *, severity: str = '', status: str = '', keyword: str = '', page: int = 1, page_size: int = 50) -> dict:
    task = get_task(user, task_id)
    queryset = task.issues.filter(is_deleted=False)
    if severity:
        queryset = queryset.filter(severity=severity)
    if status:
        queryset = queryset.filter(status=status)
    if keyword:
        queryset = queryset.filter(title__icontains=keyword)
    total = queryset.count()
    start = max(page - 1, 0) * page_size
    return {'items': [serialize_issue(item) for item in queryset[start:start + page_size]], 'total': total}


def update_issue_status(user, task_id: str, issue_id: str, status: str) -> dict:
    if status not in VALID_ISSUE_STATUSES:
        raise HttpError(422, '问题状态不合法')
    task = get_task(user, task_id)
    require_project_role(user, task.project, min_role='member')
    issue = get_object_or_404(AuditIssue, id=issue_id, task=task, is_deleted=False)
    issue.status = status
    if status == ISSUE_STATUS_OPEN:
        issue.resolved_by = None
        issue.resolved_at = None
    else:
        issue.resolved_by = user
        issue.resolved_at = timezone.now()
    issue.sys_modifier = user
    issue.save()
    return serialize_issue(issue)


def serialize_instant_record(record: InstantAnalysisRecord, include_code: bool = False) -> dict:
    analysis_result = normalize_analysis_result(record.analysis_result or {})
    return {
        'id': str(record.id),
        'language': record.language,
        'issues_count': record.issues_count or get_analysis_issue_count(analysis_result),
        'quality_score': record.quality_score or get_analysis_quality_score(analysis_result),
        'analysis_time': record.analysis_time,
        'analysis_result': analysis_result,
        'code_content': record.code_content if include_code else None,
        'sys_create_datetime': format_datetime_text(record.sys_create_datetime),
    }


def run_instant_analysis(user, payload: dict) -> dict:
    started = time.perf_counter()
    code_content = str(payload.get('code_content') or '')
    language = str(payload.get('language') or 'text')
    config = user_config_services.get_user_config(user)
    scan_config = (config.get('other_config') or {}).get('scan_config') or {}
    profile = resolve_scan_profile(user, scan_config, strict=False)
    result = normalize_analysis_result(run_heuristic_scan_from_code(code_content, language, profile=profile))
    record = InstantAnalysisRecord.objects.create(
        user=user,
        language=language,
        code_content=code_content,
        analysis_result=result,
        issues_count=get_analysis_issue_count(result),
        quality_score=get_analysis_quality_score(result),
        analysis_time=round(time.perf_counter() - started, 3),
        sys_creator=user,
        sys_modifier=user,
    )
    return serialize_instant_record(record, include_code=True)


def run_heuristic_scan_from_code(code_content: str, language: str, *, profile: dict | None = None) -> dict:
    extension = {
        'python': 'py',
        'typescript': 'ts',
        'javascript': 'js',
        'java': 'java',
        'go': 'go',
        'rust': 'rs',
        'vue': 'vue',
    }.get(language.lower(), 'txt')
    from apps.deepaudit.heuristics import build_summary, scan_content

    effective_profile = dict(profile or {})
    issues = scan_content(
        code_content or '',
        f'snippet.{extension}',
        rule_patterns=effective_profile.get('rule_patterns'),
        prompt_context=effective_profile.get('prompt_context'),
        analysis_depth=effective_profile.get('analysis_depth') or 'standard',
    )
    summary = build_summary(
        issues,
        (code_content or '').count('\n') + 1,
        1,
        severity_weights=effective_profile.get('severity_weights'),
        analysis_depth=effective_profile.get('analysis_depth') or 'standard',
        prompt_context=effective_profile.get('prompt_context'),
        rule_patterns=effective_profile.get('rule_patterns'),
    )
    return {'issues': issues, **summary}


def list_instant_records(user, *, page: int = 1, page_size: int = 20, language: str = '') -> dict:
    queryset = InstantAnalysisRecord.objects.filter(user_id=get_user_id(user), is_deleted=False).order_by('-sys_create_datetime')
    if language:
        queryset = queryset.filter(language=language)
    total = queryset.count()
    start = max(page - 1, 0) * page_size
    items = [serialize_instant_record(item) for item in queryset[start:start + page_size]]
    return {'items': items, 'total': total}


def get_instant_record(user, record_id: str) -> InstantAnalysisRecord:
    return get_object_or_404(InstantAnalysisRecord, id=record_id, user_id=get_user_id(user), is_deleted=False)


def delete_instant_record(user, record_id: str) -> bool:
    record = get_instant_record(user, record_id)
    record.is_deleted = True
    record.sys_modifier = user
    record.save(update_fields=['is_deleted', 'sys_modifier', 'sys_update_datetime'])
    return True


def export_task_json_payload(task: AuditTask) -> dict:
    return {
        'task': serialize_task(task, include_issues=False),
        'issues': [serialize_issue(item) for item in task.issues.filter(is_deleted=False).order_by('-sys_create_datetime')],
    }


def export_task_json_response(user, task_id: str) -> HttpResponse:
    task = get_task(user, task_id)
    payload = normalize_json_payload(export_task_json_payload(task))
    artifact_path = save_json_artifact(f'task-{task.id}.json', payload)
    AuditArtifact.objects.update_or_create(
        task=task,
        kind='task_json_report',
        defaults={
            'project': task.project,
            'uploaded_by': user,
            'display_name': f'task-{task.id}.json',
            'file_path': str(artifact_path),
            'mime_type': 'application/json',
            'metadata': {'type': 'task_json_report'},
            'sys_creator': user,
            'sys_modifier': user,
            'is_deleted': False,
        },
    )
    response = HttpResponse(json.dumps(payload, ensure_ascii=False, indent=2), content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="task-{task.id}.json"'
    return response


def export_task_pdf_response(user, task_id: str) -> HttpResponse:
    task = get_task(user, task_id)
    issues = [serialize_issue(item) for item in task.issues.filter(is_deleted=False).order_by('-sys_create_datetime')]
    pdf_bytes = ReportBuilder.build_task_report(serialize_task(task), issues, task.project.name)
    report_path = save_report_file(f'task-{task.id}.pdf', pdf_bytes)
    AuditArtifact.objects.update_or_create(
        task=task,
        kind='task_pdf_report',
        defaults={
            'project': task.project,
            'uploaded_by': user,
            'display_name': f'task-{task.id}.pdf',
            'file_path': str(report_path),
            'mime_type': 'application/pdf',
            'metadata': {'type': 'task_pdf_report'},
            'sys_creator': user,
            'sys_modifier': user,
            'is_deleted': False,
        },
    )
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="task-{task.id}.pdf"'
    return response


def export_instant_json_response(user, record_id: str) -> HttpResponse:
    record = get_instant_record(user, record_id)
    payload = normalize_json_payload(serialize_instant_record(record, include_code=True))
    response = HttpResponse(json.dumps(payload, ensure_ascii=False, indent=2), content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="instant-{record.id}.json"'
    return response


def export_instant_pdf_response(user, record_id: str) -> HttpResponse:
    record = get_instant_record(user, record_id)
    pdf_bytes = ReportBuilder.build_instant_report(record.language, normalize_analysis_result(record.analysis_result or {}))
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="instant-{record.id}.pdf"'
    return response


def _is_cancelled(task_id: str) -> bool:
    return AuditTask.objects.filter(id=task_id, status='cancelled').exists()


def execute_scan_task(task_id: str) -> None:
    task = AuditTask.objects.select_related('project', 'created_by').filter(id=task_id).first()
    if not task:
        return
    workspace = None
    try:
        if task.status == 'cancelled':
            return
        scan_config = dict(task.scan_config or {})
        profile = resolve_scan_profile(task.created_by, scan_config, strict=False)
        effective_profile = serialize_scan_profile(profile)
        scan_config['effective_profile'] = effective_profile
        scan_config['rule_set_id'] = scan_config.get('rule_set_id') or effective_profile.get('rule_set_id')
        scan_config['prompt_template_id'] = scan_config.get('prompt_template_id') or effective_profile.get('prompt_template_id')
        task.status = 'running'
        task.started_at = timezone.now()
        task.error_message = ''
        task.scan_config = scan_config
        task.save(update_fields=['status', 'started_at', 'error_message', 'scan_config', 'sys_update_datetime'])
        workspace, _user_payload = prepare_workspace(task.project, branch_name=task.branch_name, user_id=str(task.created_by_id))
        result = run_heuristic_scan(
            workspace,
            exclude_patterns=task.exclude_patterns or [],
            file_paths=scan_config.get('file_paths') or [],
            include_tests=bool(scan_config.get('include_tests', False)),
            include_docs=bool(scan_config.get('include_docs', False)),
            max_file_size=scan_config.get('max_file_size') or 0,
            rule_patterns=profile.get('rule_patterns'),
            prompt_context=profile.get('prompt_context'),
            analysis_depth=profile.get('analysis_depth') or 'standard',
            severity_weights=profile.get('severity_weights'),
        )
        if _is_cancelled(task.id):
            return
        task.issues.filter(is_deleted=False).delete()
        issue_models = []
        for issue in result['issues']:
            issue_models.append(
                AuditIssue(
                    task=task,
                    file_path=issue['file_path'],
                    line_number=issue['line_number'],
                    column_number=issue.get('column_number'),
                    issue_type=issue['issue_type'],
                    severity=issue['severity'],
                    title=issue['title'],
                    message=issue['title'],
                    description=issue.get('description'),
                    suggestion=issue.get('suggestion'),
                    code_snippet=issue.get('code_snippet'),
                    ai_explanation=issue.get('ai_explanation') or {},
                    status='open',
                    sys_creator=task.created_by,
                    sys_modifier=task.created_by,
                )
            )
        if issue_models:
            AuditIssue.objects.bulk_create(issue_models)
        task.total_files = result['total_files']
        task.scanned_files = result['total_files']
        task.total_lines = result['total_lines']
        task.issues_count = len(result['issues'])
        task.quality_score = get_analysis_quality_score(result)
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.scan_config = scan_config
        task.save()
    except Exception as exc:
        task.status = 'failed'
        task.error_message = str(exc)
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'error_message', 'completed_at', 'sys_update_datetime'])
        raise
    finally:
        cleanup_runtime_workspace(workspace)
