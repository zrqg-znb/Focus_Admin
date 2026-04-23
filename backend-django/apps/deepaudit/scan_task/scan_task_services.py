from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from pathlib import Path

from asgiref.sync import async_to_sync, sync_to_async
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.errors import HttpError

from apps.deepaudit.analysis_payload import get_analysis_issue_count, get_analysis_quality_score, normalize_analysis_result
from apps.deepaudit.c_family import (
    C_FAMILY_TARGET_VULNERABILITIES,
    build_c_family_analysis_profile,
    build_candidate_context,
    build_language_profile,
    collect_candidate_units,
    default_max_file_size_for_depth,
    dedupe_issue_key,
    enrich_issue_metadata,
    get_analysis_budget,
    is_c_family_language,
    is_c_family_path,
    normalize_analysis_depth,
)
from apps.deepaudit.constants import ISSUE_STATUS_FALSE_POSITIVE, ISSUE_STATUS_OPEN, ISSUE_STATUS_RESOLVED
from apps.deepaudit.heuristics import build_summary, detect_language_from_path
from apps.deepaudit.agent_engine.tools.run_code import RunCodeTool
from apps.deepaudit.llm.service import LLMService
from apps.deepaudit.permissions import accessible_project_queryset, get_user_id, require_project_role, serialize_user_brief
from apps.deepaudit.reporting import ReportBuilder
from apps.deepaudit.repo_specs import (
    build_effective_project_repository_spec,
    build_task_repository_spec,
    format_repository_spec_for_log,
    normalize_repository_type,
    validate_repository_spec_for_execution,
)
from apps.deepaudit.runtime import cleanup_runtime_workspace, list_project_files, prepare_repository_workspace
from apps.deepaudit.runtime import validate_selected_file_paths
from apps.deepaudit.scan_profile import resolve_scan_profile, serialize_scan_profile
from apps.deepaudit.scan_task.scan_task_model import AuditArtifact, AuditIssue, AuditTask, InstantAnalysisRecord
from apps.deepaudit.serialization import format_datetime_text, normalize_json_payload
from apps.deepaudit.storage import save_json_artifact, save_report_file
from apps.deepaudit.user_config import user_config_services


ACTIVE_TASK_STATUSES = {'pending', 'running'}
VALID_ISSUE_STATUSES = {ISSUE_STATUS_OPEN, ISSUE_STATUS_RESOLVED, ISSUE_STATUS_FALSE_POSITIVE}
C_FAMILY_EXTRA_ISSUE_FIELDS = [
    'root_cause',
    'trigger_condition',
    'impact_scenario',
    'cwe_id',
    'verification_status',
    'needs_runtime_verification',
]
C_FAMILY_VERIFIABLE_TYPES = {'buffer_overflow', 'format_string', 'double_free', 'use_after_free'}
logger = logging.getLogger(__name__)


def _selected_files_missing_message(missing: list[str]) -> str:
    sample = ', '.join(missing[:5])
    suffix = f' 示例: {sample}' if sample else ''
    return f'所选文件在当前代码工作区中不存在，共 {len(missing)} 个。{suffix}'


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
        'repository_url': task.repository_url,
        'repository_type': normalize_repository_type(task.repository_type),
        'branch_name': task.branch_name,
        'manifest_xml': task.manifest_xml,
        'group': task.group,
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
    requested_repository_type = payload.get('repository_type')
    requested_repository_url = str(payload.get('repository_url') or '').strip()
    repository_spec = build_effective_project_repository_spec(
        access.project,
        repository_url=payload.get('repository_url'),
        repository_type=payload.get('repository_type'),
        branch_name=payload.get('branch_name'),
        manifest_xml=payload.get('manifest_xml'),
        group=payload.get('group'),
    )
    if access.project.source_type == 'repository':
        if not repository_spec['repository_url']:
            raise HttpError(422, '仓库任务必须填写 repository_url')
        if normalize_repository_type(repository_spec['repository_type']) == 'multi' and not repository_spec['manifest_xml']:
            raise HttpError(422, '多仓任务必须填写 manifest_xml')
    project_repository_type = normalize_repository_type(access.project.repository_type)
    project_repository_url = str(access.project.repository_url or '').strip()
    if requested_repository_type is not None and normalize_repository_type(requested_repository_type) != project_repository_type:
        logger.warning(
            'DeepAudit scan task create request repository_type mismatch: project_id=%s user_id=%s requested_repository_type=%s project_repository_type=%s final_repository_type=%s',
            access.project.id,
            getattr(user, 'id', ''),
            normalize_repository_type(requested_repository_type),
            project_repository_type,
            repository_spec['repository_type'],
        )
    if requested_repository_url and requested_repository_url != project_repository_url:
        logger.warning(
            'DeepAudit scan task create request repository_url mismatch: project_id=%s user_id=%s requested_repository_url=%s project_repository_url=%s final_repository_url=%s',
            access.project.id,
            getattr(user, 'id', ''),
            requested_repository_url,
            project_repository_url or '-',
            repository_spec['repository_url'] or '-',
        )
    scan_config = {
        'file_paths': payload.get('file_paths') or [],
        'rule_set_id': payload.get('rule_set_id'),
        'prompt_template_id': payload.get('prompt_template_id'),
        'include_tests': bool(payload.get('include_tests', False)),
        'include_docs': bool(payload.get('include_docs', False)),
        'max_file_size': payload.get('max_file_size') or 0,
        'analysis_depth': normalize_analysis_depth(payload.get('analysis_depth')),
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
        repository_url=repository_spec['repository_url'] or None,
        repository_type=repository_spec['repository_type'],
        branch_name=repository_spec['branch_name'],
        manifest_xml=repository_spec['manifest_xml'] or None,
        group=repository_spec['group'] or None,
        exclude_patterns=payload.get('exclude_patterns') or [],
        scan_config=scan_config,
        sys_creator=user,
        sys_modifier=user,
    )
    logger.info(
        'DeepAudit scan task %s created for project %s with repository snapshot: %s',
        task.id,
        access.project.id,
        format_repository_spec_for_log(repository_spec),
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
    file_name = str(payload.get('file_name') or f'snippet.{_language_extension(language)}')
    config = user_config_services.get_user_config(user)
    scan_config = dict((config.get('other_config') or {}).get('scan_config') or {})
    prompt_template_id = str(payload.get('prompt_template_id') or '').strip()
    if prompt_template_id:
        scan_config['prompt_template_id'] = prompt_template_id
    language_profile = _build_effective_language_profile(
        [{'path': file_name}],
        selected_file_paths=[file_name],
    )
    scan_config['analysis_depth'] = normalize_analysis_depth(scan_config.get('analysis_depth'))
    scan_config['language_profile'] = language_profile
    profile = resolve_scan_profile(user, scan_config, strict=bool(prompt_template_id))
    if _should_use_c_family_path(
        language=language,
        file_path=file_name,
        language_profile=language_profile,
    ):
        result = async_to_sync(_analyze_c_family_candidates_async)(
            user_payload=config,
            files=[
                {
                    'path': file_name,
                    'content': code_content,
                    'lines': max(1, code_content.count('\n') + 1),
                }
            ],
            profile=profile,
            language_profile=language_profile,
            workspace=Path('/tmp'),
            llm_concurrency=1,
            llm_gap_ms=0,
            selected_file_paths=[file_name],
        )
    else:
        result = _analyze_code_payload(
            config,
            code_content,
            language,
            file_path=file_name,
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


def _language_extension(language: str) -> str:
    return {
        'python': 'py',
        'typescript': 'ts',
        'javascript': 'js',
        'java': 'java',
        'go': 'go',
        'rust': 'rs',
        'vue': 'vue',
        'c': 'c',
        'cpp': 'cpp',
        'csharp': 'cs',
        'php': 'php',
        'ruby': 'rb',
        'swift': 'swift',
        'kotlin': 'kt',
    }.get(str(language or '').strip().lower(), 'txt')


def run_heuristic_scan_from_code(code_content: str, language: str, *, profile: dict | None = None) -> dict:
    from apps.deepaudit.heuristics import build_summary, scan_content

    effective_profile = dict(profile or {})
    issues = scan_content(
        code_content or '',
        f'snippet.{_language_extension(language)}',
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


def _build_effective_language_profile(
    files: list[dict],
    *,
    selected_file_paths: list[str] | None = None,
) -> dict:
    return build_language_profile(files, selected_file_paths=selected_file_paths)


def _should_use_c_family_path(
    *,
    language: str | None = None,
    file_path: str | None = None,
    language_profile: dict | None = None,
) -> bool:
    if is_c_family_language(language) or is_c_family_path(file_path):
        return True
    return bool((language_profile or {}).get('is_c_family_dominant'))


def _effective_scan_profile_for_files(user, scan_config: dict, files: list[dict]) -> tuple[dict, dict]:
    language_profile = _build_effective_language_profile(
        files,
        selected_file_paths=scan_config.get('file_paths') or [],
    )
    runtime_scan_config = dict(scan_config or {})
    runtime_scan_config['analysis_depth'] = normalize_analysis_depth(
        runtime_scan_config.get('analysis_depth'),
    )
    runtime_scan_config['language_profile'] = language_profile
    profile = resolve_scan_profile(user, runtime_scan_config, strict=False)
    return profile, language_profile


async def _verify_c_family_issue_async(
    issue: dict,
    *,
    file_lookup: dict[str, dict],
    language: str,
) -> tuple[str, dict[str, object]]:
    issue_type = str(issue.get('issue_type') or '').strip().lower()
    if issue_type not in C_FAMILY_VERIFIABLE_TYPES:
        return 'unverified', {'reason': 'verification_not_supported'}
    if not docker_available():
        return 'unverified', {'reason': 'sandbox_unavailable'}

    file_path = str(issue.get('file_path') or '').strip()
    file_content = str((file_lookup.get(file_path) or {}).get('content') or '')
    if not file_content.strip():
        return 'unverified', {'reason': 'missing_source'}

    verifier = RunCodeTool(project_root='.')
    result = await verifier.execute(
        code=file_content,
        language=language,
        timeout=45,
        description=f'FocusAudit runtime verification for {issue_type}',
    )
    combined_output = '\n'.join(
        [
            str(result.data or ''),
            str(result.error or ''),
        ]
    ).lower()
    metadata = dict(result.metadata or {})
    metadata.update(
        {
            'verification_tool': 'run_code',
            'verification_success': bool(result.success),
        }
    )
    if any(
        marker in combined_output
        for marker in (
            'addresssanitizer',
            'undefinedbehaviorsanitizer',
            'runtime error:',
            'heap-use-after-free',
            'double-free',
            'stack-buffer-overflow',
            'format string',
        )
    ):
        return 'confirmed', metadata
    if result.success:
        return 'unverified', metadata
    return 'unsupported', metadata


def _strip_internal_issue_fields(issue: dict) -> dict:
    payload = dict(issue)
    payload.pop('_candidate_index', None)
    payload.pop('_candidate_name', None)
    return payload


async def _analyze_c_family_candidates_async(
    *,
    user_payload: dict,
    files: list[dict],
    profile: dict,
    language_profile: dict,
    workspace: Path,
    llm_concurrency: int,
    llm_gap_ms: int,
    selected_file_paths: list[str] | None = None,
) -> dict:
    service = LLMService(user_config=user_payload)
    file_lookup = {str(item.get('path') or ''): item for item in files}
    analysis_depth = normalize_analysis_depth(profile.get('analysis_depth'))
    candidates = collect_candidate_units(
        files,
        analysis_depth=analysis_depth,
        selected_file_paths=selected_file_paths,
    )
    if not candidates:
        return normalize_analysis_result(
            {
                'issues': [],
                **build_summary(
                    [],
                    sum(int(item.get('lines') or 0) for item in files),
                    len(files),
                    severity_weights=profile.get('severity_weights'),
                    analysis_depth=analysis_depth,
                    prompt_context=profile.get('prompt_context'),
                    rule_patterns=profile.get('rule_patterns'),
                ),
                'analysis_profile': build_c_family_analysis_profile(
                    analysis_depth=analysis_depth,
                    language_profile=language_profile,
                    context_sources=[],
                    prompt_template_id=str(getattr(profile.get('prompt_template'), 'id', '') or '') or None,
                    rule_set_id=str(getattr(profile.get('rule_set'), 'id', '') or '') or None,
                ),
            }
        )

    semaphore = asyncio.Semaphore(max(1, llm_concurrency))
    gap_seconds = max(0.0, llm_gap_ms / 1000.0)
    results: list[dict] = []
    shared_context_sources: list[str] = []

    async def analyze_candidate(index: int, candidate) -> dict:
        if gap_seconds > 0:
            await asyncio.sleep(index * gap_seconds)
        context_text, context_sources = build_candidate_context(
            workspace,
            candidate,
            all_candidates=candidates,
            file_lookup=file_lookup,
            analysis_depth=analysis_depth,
        )
        async with semaphore:
            try:
                result = await service.analyze_code_with_rules(
                    candidate.content,
                    candidate.language,
                    rule_set_id=str(getattr(profile.get('rule_set'), 'id', '') or '') or None,
                    prompt_template_id=str(getattr(profile.get('prompt_template'), 'id', '') or '') or None,
                    additional_context=context_text,
                    issue_types=list(C_FAMILY_TARGET_VULNERABILITIES),
                    extra_issue_fields=C_FAMILY_EXTRA_ISSUE_FIELDS,
                )
                normalized = normalize_analysis_result(result)
                engine = 'llm_c_family'
            except Exception as exc:
                logger.warning(
                    'DeepAudit C-family candidate analysis fell back to heuristic scan: file=%s line=%s reason=%s',
                    candidate.file_path,
                    candidate.line_start,
                    exc,
                )
                normalized = normalize_analysis_result(
                    run_heuristic_scan_from_code(
                        candidate.content,
                        candidate.language,
                        profile=profile,
                    )
                )
                engine = 'heuristic_fallback'
            return {
                'candidate': candidate,
                'context_sources': context_sources,
                'normalized': normalized,
                'engine': engine,
            }

    tasks = [
        asyncio.create_task(analyze_candidate(index, candidate))
        for index, candidate in enumerate(candidates)
    ]
    for future in asyncio.as_completed(tasks):
        results.append(await future)
    await asyncio.gather(*tasks, return_exceptions=True)

    issues_by_key: dict[tuple[str, int, str], dict] = {}
    verify_budget = int(get_analysis_budget(analysis_depth).get('max_verify') or 0)
    verifiable_queue: list[dict] = []

    for result in results:
        candidate = result['candidate']
        context_sources = list(result.get('context_sources') or [])
        shared_context_sources.extend(context_sources)
        for raw_issue in list((result.get('normalized') or {}).get('issues') or []):
            enriched = enrich_issue_metadata(
                raw_issue,
                candidate=candidate,
                language_profile=language_profile,
                context_sources=context_sources,
                verification_status='unverified',
            )
            enriched['_candidate_index'] = candidates.index(candidate)
            key = dedupe_issue_key(enriched)
            existing = issues_by_key.get(key)
            if existing:
                severity_rank = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
                if severity_rank.get(str(enriched.get('severity') or 'low').lower(), 0) <= severity_rank.get(
                    str(existing.get('severity') or 'low').lower(),
                    0,
                ):
                    continue
            issues_by_key[key] = enriched

    deduped_issues = list(issues_by_key.values())
    deduped_issues.sort(
        key=lambda item: (
            {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}.get(str(item.get('severity') or 'low').lower(), 0),
            1 if str(item.get('issue_type') or '') in C_FAMILY_VERIFIABLE_TYPES else 0,
            float(item.get('confidence') or 0.0),
        ),
        reverse=True,
    )

    for issue in deduped_issues:
        if verify_budget <= 0:
            break
        if str(issue.get('issue_type') or '') not in C_FAMILY_VERIFIABLE_TYPES:
            continue
        verification_status, verification_details = await _verify_c_family_issue_async(
            issue,
            file_lookup=file_lookup,
            language=str((file_lookup.get(issue.get('file_path')) or {}).get('language') or detect_language_from_path(str(issue.get('file_path') or ''))),
        )
        issue.update(
            enrich_issue_metadata(
                issue,
                candidate=candidates[int(issue.pop('_candidate_index', 0))],
                language_profile=language_profile,
                context_sources=issue.get('context_sources') or [],
                verification_status=verification_status,
                verification_details=verification_details,
            )
        )
        verify_budget -= 1

    final_issues = [_strip_internal_issue_fields(issue) for issue in deduped_issues]
    summary = build_summary(
        final_issues,
        sum(int(item.get('lines') or 0) for item in files),
        len(files),
        severity_weights=profile.get('severity_weights'),
        analysis_depth=analysis_depth,
        prompt_context=profile.get('prompt_context'),
        rule_patterns=profile.get('rule_patterns'),
    )
    payload = {
        'issues': final_issues,
        **summary,
        'analysis_profile': build_c_family_analysis_profile(
            analysis_depth=analysis_depth,
            language_profile=language_profile,
            context_sources=shared_context_sources,
            prompt_template_id=str(getattr(profile.get('prompt_template'), 'id', '') or '') or None,
            rule_set_id=str(getattr(profile.get('rule_set'), 'id', '') or '') or None,
        ),
    }
    return normalize_analysis_result(payload)


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
            'language_profile': dict(profile.get('language_profile') or {}),
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
            'language_profile': dict(profile.get('language_profile') or {}),
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


def _persist_grouped_scan_issues(task_id: str, created_by_id, files: list[dict], issues: list[dict]) -> int:
    file_lookup = {str(item.get('path') or ''): str(item.get('content') or '') for item in files}
    grouped: dict[str, list[dict]] = defaultdict(list)
    for issue in issues:
        file_path = str(issue.get('file_path') or '').strip()
        if not file_path:
            continue
        grouped[file_path].append(issue)
    created = 0
    for file_path, items in grouped.items():
        created += _persist_scan_issues(
            task_id,
            created_by_id,
            file_path,
            file_lookup.get(file_path, ''),
            items,
        )
    return created


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
        scan_config['analysis_depth'] = normalize_analysis_depth(scan_config.get('analysis_depth'))
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
        repository_spec = build_task_repository_spec(task)
        if task.project.source_type == 'repository':
            repository_spec = validate_repository_spec_for_execution(repository_spec)
        logger.info(
            'DeepAudit scan task %s will initialize repository workspace for project %s: %s',
            task.id,
            task.project_id,
            format_repository_spec_for_log(repository_spec),
        )
        if (
            task.project.source_type == 'repository'
            and (
                normalize_repository_type(task.project.repository_type) != repository_spec['repository_type']
                or str(task.project.repository_url or '').strip() != repository_spec['repository_url']
            )
        ):
            logger.warning(
                'DeepAudit scan task %s is using snapshotted repository spec instead of current project config: current_repository_type=%s current_repository_url=%s',
                task.id,
                normalize_repository_type(task.project.repository_type),
                str(task.project.repository_url or '').strip() or '-',
            )
        workspace, user_payload = prepare_repository_workspace(
            task.project,
            repository_spec=repository_spec,
            user_id=str(task.created_by_id),
            force_multi_sync=repository_spec['repository_type'] == 'multi',
            log_context={
                'task_kind': 'scan',
                'task_id': str(task.id),
                'user_id': str(task.created_by_id),
            },
        )
        runtime_scan_config = (user_payload.get('other_config') or {}).get('scan_config') or {}
        validated_file_paths = scan_config.get('file_paths') or []
        if validated_file_paths:
            selection_check = validate_selected_file_paths(
                workspace,
                file_paths=validated_file_paths,
            )
            if selection_check['missing']:
                if selection_check['existing']:
                    logger.warning(
                        'DeepAudit scan task %s found missing selected files after workspace refresh and will continue with remaining files: missing_count=%s existing_count=%s missing_samples=%s %s',
                        task.id,
                        len(selection_check['missing']),
                        len(selection_check['existing']),
                        selection_check['missing'][:5],
                        format_repository_spec_for_log(repository_spec),
                    )
                    validated_file_paths = selection_check['existing']
                else:
                    message = _selected_files_missing_message(selection_check['missing'])
                    logger.error(
                        'DeepAudit scan task %s failed because all selected files are missing from workspace: %s %s',
                        task.id,
                        message,
                        format_repository_spec_for_log(repository_spec),
                    )
                    task.status = 'failed'
                    task.error_message = message
                    task.completed_at = timezone.now()
                    task.save(
                        update_fields=[
                            'status',
                            'error_message',
                            'completed_at',
                            'sys_update_datetime',
                        ]
                    )
                    return
        effective_max_file_size = (
            scan_config.get('max_file_size')
            or runtime_scan_config.get('max_file_size')
            or default_max_file_size_for_depth(scan_config.get('analysis_depth'))
        )
        files = list_project_files(
            workspace,
            exclude_patterns=task.exclude_patterns or [],
            file_paths=validated_file_paths,
            include_tests=bool(scan_config.get('include_tests', False)),
            include_docs=bool(scan_config.get('include_docs', False)),
            max_file_size=effective_max_file_size,
        )
        max_analyze_files = int(runtime_scan_config.get('max_analyze_files') or 0)
        if max_analyze_files > 0:
            files = files[:max_analyze_files]
        runtime_profile_config = dict(scan_config)
        runtime_profile_config['file_paths'] = validated_file_paths
        profile, language_profile = _effective_scan_profile_for_files(task.created_by, runtime_profile_config, files)
        effective_profile = serialize_scan_profile(profile)
        scan_config['effective_profile'] = effective_profile
        scan_config['analysis_profile'] = dict(profile.get('analysis_profile') or {})
        scan_config['rule_set_id'] = scan_config.get('rule_set_id') or effective_profile.get('rule_set_id')
        scan_config['prompt_template_id'] = scan_config.get('prompt_template_id') or effective_profile.get('prompt_template_id')
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
        if language_profile.get('is_c_family_dominant'):
            analysis_result = asyncio.run(
                _analyze_c_family_candidates_async(
                    user_payload=user_payload,
                    files=files,
                    profile=profile,
                    language_profile=language_profile,
                    workspace=workspace,
                    llm_concurrency=llm_concurrency,
                    llm_gap_ms=llm_gap_ms,
                    selected_file_paths=validated_file_paths,
                )
            )
            total_issues = _persist_grouped_scan_issues(
                str(task.id),
                task.created_by_id,
                files,
                list(analysis_result.get('issues') or []),
            )
            total_lines = int(analysis_result.get('total_lines') or sum(int(item.get('lines') or 0) for item in files))
            scanned_files = len(files)
            quality_score = float(analysis_result.get('quality_score') or (100.0 if scanned_files > 0 else 0.0))
            scan_config['analysis_profile'] = dict(analysis_result.get('analysis_profile') or {})
            task.scanned_files = scanned_files
            task.total_lines = total_lines
            task.issues_count = total_issues
            task.quality_score = round(quality_score, 2)
        else:
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
                task.scan_config = scan_config
                task.save(update_fields=['status', 'completed_at', 'total_lines', 'issues_count', 'quality_score', 'scan_config', 'sys_update_datetime'])
                return
            if len(files) > 0 and scanned_files == 0 and failed_files > 0:
                task.status = 'failed'
                task.error_message = '所有文件分析均失败，请检查 LLM 配置或网络连通性'
                task.completed_at = timezone.now()
                task.quality_score = 0.0
                task.scan_config = scan_config
                task.save(update_fields=['status', 'error_message', 'completed_at', 'quality_score', 'scan_config', 'sys_update_datetime'])
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
