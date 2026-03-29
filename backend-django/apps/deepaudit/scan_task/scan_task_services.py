from __future__ import annotations

import asyncio
import json
import time

from asgiref.sync import async_to_sync, sync_to_async
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.errors import HttpError

from apps.deepaudit.analysis_payload import get_analysis_issue_count, get_analysis_quality_score, normalize_analysis_result
from apps.deepaudit.constants import ISSUE_STATUS_FALSE_POSITIVE, ISSUE_STATUS_OPEN, ISSUE_STATUS_RESOLVED
from apps.deepaudit.heuristics import detect_language_from_path
from apps.deepaudit.llm.service import LLMService
from apps.deepaudit.permissions import accessible_project_queryset, get_user_id, require_project_role, serialize_user_brief
from apps.deepaudit.reporting import ReportBuilder
from apps.deepaudit.runtime import cleanup_runtime_workspace, list_project_files, prepare_workspace
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
    result = _analyze_code_payload(
        config,
        code_content,
        language,
        file_path=str(payload.get('file_name') or f'snippet.{language}'),
        profile=profile,
    )
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


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_code_snippet(code_content: str, line_number: int | None) -> str:
    if not code_content or not line_number or line_number <= 0:
        return ''
    lines = code_content.splitlines()
    index = min(max(line_number - 1, 0), max(len(lines) - 1, 0))
    start = max(0, index - 2)
    end = min(len(lines), index + 3)
    return '\n'.join(lines[start:end]).strip()


def _normalize_issue_payload(issue: dict, *, file_path: str, code_content: str) -> dict:
    line_number = _safe_int(issue.get('line') or issue.get('line_number'))
    column_number = _safe_int(issue.get('column') or issue.get('column_number'))
    title = str(issue.get('title') or issue.get('name') or issue.get('issue_type') or issue.get('type') or 'Issue').strip() or 'Issue'
    description = str(issue.get('description') or issue.get('message') or title).strip()
    suggestion = str(issue.get('suggestion') or '').strip() or None
    ai_explanation = issue.get('ai_explanation') or issue.get('xai') or {}
    code_snippet = str(issue.get('code_snippet') or '').strip() or _build_code_snippet(code_content, line_number) or None
    return {
        'file_path': file_path,
        'line_number': line_number,
        'column_number': column_number,
        'issue_type': str(issue.get('issue_type') or issue.get('type') or issue.get('vulnerability_type') or 'maintainability').strip() or 'maintainability',
        'severity': str(issue.get('severity') or 'low').strip().lower() or 'low',
        'title': title,
        'message': description,
        'description': description,
        'suggestion': suggestion,
        'code_snippet': code_snippet,
        'ai_explanation': ai_explanation if isinstance(ai_explanation, dict) else {'detail': ai_explanation},
    }


async def _analyze_code_payload_async(
    user_config: dict,
    code_content: str,
    language: str,
    *,
    file_path: str,
    profile: dict,
) -> dict:
    service = LLMService(user_config=user_config)
    rule_set = profile.get('rule_set')
    prompt_template = profile.get('prompt_template')
    try:
        result = await service.analyze_code_with_rules(
            code_content,
            language,
            rule_set_id=str(rule_set.id) if rule_set else None,
            prompt_template_id=str(prompt_template.id) if prompt_template else None,
        )
        normalized = normalize_analysis_result(result)
        normalized['analysis_profile'] = {
            **dict(normalized.get('analysis_profile') or {}),
            'engine': 'llm',
            'analysis_depth': profile.get('analysis_depth') or 'standard',
            'rule_set_id': str(rule_set.id) if rule_set else None,
            'prompt_template_id': str(prompt_template.id) if prompt_template else None,
        }
        return normalized
    except Exception as exc:
        fallback = normalize_analysis_result(run_heuristic_scan_from_code(code_content, language, profile=profile))
        fallback['analysis_profile'] = {
            **dict(fallback.get('analysis_profile') or {}),
            'engine': 'heuristic_fallback',
            'fallback_reason': str(exc),
            'analysis_depth': profile.get('analysis_depth') or 'standard',
            'rule_set_id': str(rule_set.id) if rule_set else None,
            'prompt_template_id': str(prompt_template.id) if prompt_template else None,
        }
        return fallback


def _analyze_code_payload(
    user_config: dict,
    code_content: str,
    language: str,
    *,
    file_path: str,
    profile: dict,
) -> dict:
    return async_to_sync(_analyze_code_payload_async)(
        user_config,
        code_content,
        language,
        file_path=file_path,
        profile=profile,
    )


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


def delete_all_instant_records(user) -> bool:
    InstantAnalysisRecord.objects.filter(user_id=get_user_id(user), is_deleted=False).update(
        is_deleted=True,
        sys_modifier=user,
        sys_update_datetime=timezone.now(),
    )
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


def _persist_scan_issues(task_id: str, created_by_id, file_path: str, code_content: str, issues: list[dict]) -> int:
    issue_models: list[AuditIssue] = []
    for raw_issue in issues:
        normalized_issue = _normalize_issue_payload(raw_issue, file_path=file_path, code_content=code_content)
        issue_models.append(
            AuditIssue(
                task_id=task_id,
                file_path=normalized_issue['file_path'],
                line_number=normalized_issue['line_number'],
                column_number=normalized_issue['column_number'],
                issue_type=normalized_issue['issue_type'],
                severity=normalized_issue['severity'],
                title=normalized_issue['title'],
                message=normalized_issue['message'],
                description=normalized_issue['description'],
                suggestion=normalized_issue['suggestion'],
                code_snippet=normalized_issue['code_snippet'],
                ai_explanation=normalized_issue['ai_explanation'],
                status='open',
                sys_creator_id=created_by_id,
                sys_modifier_id=created_by_id,
            )
        )
    if issue_models:
        AuditIssue.objects.bulk_create(issue_models)
    return len(issue_models)


def _update_scan_progress(task_id: str, created_by_id, *, scanned_files: int, total_lines: int, issues_count: int, quality_score: float) -> None:
    AuditTask.objects.filter(id=task_id).update(
        scanned_files=scanned_files,
        total_lines=total_lines,
        issues_count=issues_count,
        quality_score=quality_score,
        sys_modifier_id=created_by_id,
        sys_update_datetime=timezone.now(),
    )


async def _scan_files_with_concurrency(
    *,
    task_id: str,
    created_by_id,
    files: list[dict],
    user_payload: dict,
    profile: dict,
    llm_concurrency: int,
    llm_gap_ms: int,
) -> dict:
    semaphore = asyncio.Semaphore(max(1, llm_concurrency))
    gap_seconds = max(0.0, llm_gap_ms / 1000.0)
    cancelled_checker = sync_to_async(_is_cancelled, thread_sensitive=True)
    persist_issues = sync_to_async(_persist_scan_issues, thread_sensitive=True)
    update_progress = sync_to_async(_update_scan_progress, thread_sensitive=True)

    async def analyze_file(index: int, file_item: dict) -> dict:
        code_content = str(file_item.get('content') or '')
        if not code_content.strip():
            return {'status': 'skipped'}
        file_path = str(file_item.get('path') or '')
        language = detect_language_from_path(file_path)
        if gap_seconds > 0:
            await asyncio.sleep(index * gap_seconds)
        if await cancelled_checker(task_id):
            return {'status': 'cancelled'}
        async with semaphore:
            if await cancelled_checker(task_id):
                return {'status': 'cancelled'}
            analysis = await _analyze_code_payload_async(
                user_payload,
                code_content,
                language,
                file_path=file_path,
                profile=profile,
            )
            return {
                'status': 'success',
                'file_path': file_path,
                'code_content': code_content,
                'analysis': analysis,
                'lines': int(analysis.get('total_lines') or file_item.get('lines') or 0),
                'quality_score': float(analysis.get('quality_score') or 0),
                'issues': list(analysis.get('issues') or []),
            }

    tasks = [asyncio.create_task(analyze_file(index, file_item)) for index, file_item in enumerate(files)]
    scanned_files = 0
    skipped_files = 0
    failed_files = 0
    total_lines = 0
    total_issues = 0
    quality_scores: list[float] = []

    try:
        for future in asyncio.as_completed(tasks):
            try:
                result = await future
            except asyncio.CancelledError:
                raise
            except Exception:
                failed_files += 1
                continue

            status = str(result.get('status') or '').strip().lower()
            if status == 'cancelled':
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                return {
                    'cancelled': True,
                    'scanned_files': scanned_files,
                    'skipped_files': skipped_files,
                    'failed_files': failed_files,
                    'total_lines': total_lines,
                    'total_issues': total_issues,
                    'quality_scores': quality_scores,
                }
            if status == 'skipped':
                skipped_files += 1
                continue
            if status != 'success':
                failed_files += 1
                continue

            created_count = await persist_issues(
                task_id,
                created_by_id,
                str(result.get('file_path') or ''),
                str(result.get('code_content') or ''),
                list(result.get('issues') or []),
            )
            scanned_files += 1
            total_lines += int(result.get('lines') or 0)
            total_issues += created_count
            quality_score = float(result.get('quality_score') or 0)
            if quality_score > 0:
                quality_scores.append(quality_score)
            await update_progress(
                task_id,
                created_by_id,
                scanned_files=scanned_files,
                total_lines=total_lines,
                issues_count=total_issues,
                quality_score=round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else 0.0,
            )
    finally:
        await asyncio.gather(*tasks, return_exceptions=True)

    return {
        'cancelled': False,
        'scanned_files': scanned_files,
        'skipped_files': skipped_files,
        'failed_files': failed_files,
        'total_lines': total_lines,
        'total_issues': total_issues,
        'quality_scores': quality_scores,
    }


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
        workspace, user_payload = prepare_workspace(task.project, branch_name=task.branch_name, user_id=str(task.created_by_id))
        runtime_scan_config = (user_payload.get('other_config') or {}).get('scan_config') or {}
        files = list_project_files(
            workspace,
            exclude_patterns=task.exclude_patterns or [],
            file_paths=scan_config.get('file_paths') or [],
            include_tests=bool(scan_config.get('include_tests', False)),
            include_docs=bool(scan_config.get('include_docs', False)),
            max_file_size=scan_config.get('max_file_size') or runtime_scan_config.get('max_file_size') or 0,
        )
        max_analyze_files = int(runtime_scan_config.get('max_analyze_files') or 0)
        if max_analyze_files > 0:
            files = files[:max_analyze_files]
        llm_concurrency = max(1, int(runtime_scan_config.get('llm_concurrency') or 1))
        llm_gap_ms = max(0, int(runtime_scan_config.get('llm_gap_ms') or 0))
        task.total_files = len(files)
        task.scanned_files = 0
        task.total_lines = 0
        task.issues_count = 0
        task.quality_score = 0
        task.save(update_fields=['total_files', 'scanned_files', 'total_lines', 'issues_count', 'quality_score', 'sys_update_datetime'])
        if _is_cancelled(task.id):
            return
        task.issues.filter(is_deleted=False).delete()
        summary = asyncio.run(
            _scan_files_with_concurrency(
                task_id=str(task.id),
                created_by_id=task.created_by_id,
                files=files,
                user_payload=user_payload,
                profile=profile,
                llm_concurrency=llm_concurrency,
                llm_gap_ms=llm_gap_ms,
            )
        )
        if summary.get('cancelled'):
            return
        total_lines = int(summary.get('total_lines') or 0)
        total_issues = int(summary.get('total_issues') or 0)
        scanned_files = int(summary.get('scanned_files') or 0)
        skipped_files = int(summary.get('skipped_files') or 0)
        failed_files = int(summary.get('failed_files') or 0)
        quality_scores = [float(item) for item in (summary.get('quality_scores') or [])]

        if len(files) > 0 and scanned_files == 0 and skipped_files == len(files):
            task.status = 'completed'
            task.completed_at = timezone.now()
            task.total_lines = 0
            task.issues_count = 0
            task.quality_score = 100.0
            task.save(update_fields=['status', 'completed_at', 'total_lines', 'issues_count', 'quality_score', 'sys_update_datetime'])
            return
        if len(files) > 0 and scanned_files == 0 and failed_files > 0:
            task.status = 'failed'
            task.error_message = '所有文件分析均失败，请检查 LLM 配置或网络连通性'
            task.completed_at = timezone.now()
            task.quality_score = 0.0
            task.save(update_fields=['status', 'error_message', 'completed_at', 'quality_score', 'sys_update_datetime'])
            return
        task.total_lines = total_lines
        task.issues_count = total_issues
        task.quality_score = round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else (100.0 if scanned_files > 0 else 0.0)
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
