from __future__ import annotations

import asyncio
import json
import logging
import re
from collections import Counter
from pathlib import Path

from asgiref.sync import sync_to_async
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.errors import HttpError

from apps.deepaudit.agent_task.agent_task_model import AgentCheckpoint, AgentEvent, AgentFinding, AgentTask
from apps.deepaudit.c_family import C_FAMILY_TARGET_VULNERABILITIES, project_likely_c_family
from apps.deepaudit.constants import (
    AGENT_PHASE_ANALYSIS,
    AGENT_PHASE_CHOICES,
    AGENT_PHASE_INDEXING,
    AGENT_PHASE_PLANNING,
    AGENT_PHASE_RECONNAISSANCE,
    AGENT_PHASE_REPORTING,
    AGENT_PHASE_VERIFICATION,
    FINDING_STATUS_CHOICES,
)
from apps.deepaudit.heuristics import normalize_severity_weight
from apps.deepaudit.permissions import require_project_role, serialize_user_brief
from apps.deepaudit.realtime import push_task_event
from apps.deepaudit.reporting import ReportBuilder
from apps.deepaudit.repo_specs import (
    build_effective_project_repository_spec,
    build_project_repository_binding,
    build_task_repository_binding,
    build_task_repository_spec,
    format_repository_spec_for_log,
    normalize_repository_type,
    repository_spec_signature,
    validate_repository_spec_for_execution,
)
from apps.deepaudit.runtime import cleanup_runtime_workspace, docker_available, prepare_repository_workspace
from apps.deepaudit.runtime import resolve_selected_file_paths, summarize_selected_targets, validate_selected_file_paths
from apps.deepaudit.scan_task.scan_task_model import AuditArtifact
from apps.deepaudit.serialization import format_datetime_text, normalize_json_payload
from apps.deepaudit.db_runtime import close_runtime_db_connections, ensure_runtime_db_connection, run_with_fresh_connection
from apps.deepaudit.storage import save_json_artifact, save_report_file
from apps.deepaudit.tasks import dispatch_deepaudit_task, run_agent_task

PHASE_LABELS = {
    AGENT_PHASE_PLANNING: 'Planning',
    AGENT_PHASE_INDEXING: 'Indexing',
    AGENT_PHASE_RECONNAISSANCE: 'Reconnaissance',
    AGENT_PHASE_ANALYSIS: 'Analysis',
    AGENT_PHASE_VERIFICATION: 'Verification',
    AGENT_PHASE_REPORTING: 'Reporting',
}

VALID_FINDING_STATUSES = {value for value, _label in FINDING_STATUS_CHOICES}
ACTIVE_STATUSES = {'pending', 'initializing', 'running', 'planning', 'indexing', 'analyzing', 'verifying', 'reporting'}
REPOSITORY_REBINDABLE_STATUSES = {'initializing', 'pending', 'queued'}
TERMINAL_STATUSES = {'completed', 'failed', 'cancelled'}
MAX_PERSISTED_CHECKPOINTS = 50
TASK_STEP_MAX_LENGTH = 255
CHECKPOINT_NAME_MAX_LENGTH = 255
THINKING_EVENT_TYPES = {
    'thinking',
    'thinking_start',
    'thinking_token',
    'thinking_end',
    'llm_start',
    'llm_thought',
    'llm_decision',
    'llm_complete',
    'llm_action',
    'llm_observation',
}
TOOL_EVENT_TYPES = {
    'tool_call',
    'tool_result',
    'tool_start',
    'tool_end',
    'tool_call_start',
    'tool_call_input',
    'tool_call_output',
    'tool_call_end',
}


def truncate_runtime_text(value: str | None, *, max_length: int = TASK_STEP_MAX_LENGTH) -> str | None:
    text = str(value or '').strip()
    if not text:
        return None
    if len(text) <= max_length:
        return text
    return f'{text[: max_length - 1].rstrip()}…'

TASK_STATUS_BY_PHASE = {
    AGENT_PHASE_PLANNING: 'planning',
    AGENT_PHASE_INDEXING: 'indexing',
    AGENT_PHASE_RECONNAISSANCE: 'running',
    AGENT_PHASE_ANALYSIS: 'analyzing',
    AGENT_PHASE_VERIFICATION: 'verifying',
    AGENT_PHASE_REPORTING: 'reporting',
}

REPORT_LANGUAGE_BY_EXTENSION = {
    '.c': 'c',
    '.cpp': 'cpp',
    '.cs': 'csharp',
    '.go': 'go',
    '.java': 'java',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.kt': 'kotlin',
    '.php': 'php',
    '.py': 'python',
    '.rb': 'ruby',
    '.rs': 'rust',
    '.sh': 'bash',
    '.sql': 'sql',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.vue': 'vue',
}

TOOL_COUNT_EVENT_TYPES = {'tool_call', 'tool_start', 'tool_call_start'}
UNSET = object()
logger = logging.getLogger(__name__)


def _build_repository_snapshot_metadata(
    repository_spec: dict[str, str],
    *,
    task_id: str | None = None,
    project_id: str | None = None,
    project_repository_type: str | None = None,
    requested_repository_type: str | None = None,
) -> dict[str, str]:
    metadata = {
        'repository_type': normalize_repository_type(repository_spec.get('repository_type')),
        'repository_url': str(repository_spec.get('repository_url') or '').strip(),
        'repository_signature': repository_spec_signature(repository_spec),
        'branch_name': str(repository_spec.get('branch_name') or '').strip(),
        'manifest_xml': str(repository_spec.get('manifest_xml') or '').strip(),
        'group': str(repository_spec.get('group') or '').strip(),
    }
    if task_id:
        metadata['task_id'] = str(task_id)
    if project_id:
        metadata['project_id'] = str(project_id)
    if project_repository_type is not None:
        metadata['project_repository_type'] = normalize_repository_type(project_repository_type)
    if requested_repository_type is not None:
        metadata['requested_repository_type'] = normalize_repository_type(requested_repository_type)
    return metadata


def _repository_runtime_metadata(user_payload: dict | None) -> dict[str, str]:
    metadata = dict((user_payload or {}).get('_repository_runtime') or {})
    return {key: str(value or '') for key, value in metadata.items()}


def _selection_repository_signature_error() -> str:
    return '仓库规格已变化，请重新选择文件/目录后再启动任务'


def _missing_selection_repository_signature_error() -> str:
    return '已选择文件或目录，但当前文件选择会话未绑定仓库规格，请重新选择文件/目录后再启动任务'


def _validate_selection_repository_signature(
    *,
    selected_paths: list[str],
    requested_signature: str,
    effective_signature: str,
) -> None:
    if not selected_paths:
        return
    if not requested_signature:
        raise HttpError(422, _missing_selection_repository_signature_error())
    if requested_signature == effective_signature:
        return
    raise HttpError(409, _selection_repository_signature_error())


def _persist_repository_signature_metadata(
    agent_config: dict,
    *,
    repository_signature: str,
    project_repository_signature: str,
) -> dict:
    next_config = dict(agent_config or {})
    next_config['repository_signature'] = repository_signature
    next_config['project_repository_signature'] = project_repository_signature
    return next_config


def _refresh_pending_task_repository_snapshot(
    instance: AgentTask,
    *,
    allow_project_rebind: bool,
) -> tuple[dict[str, str], bool]:
    repository_binding = build_task_repository_binding(instance)
    repository_spec = repository_binding['repository_spec']
    if instance.project.source_type != 'repository':
        return repository_spec, False

    project_repository_spec = repository_binding['project_repository_spec']
    repository_signature = str(repository_binding['repository_signature'])
    project_repository_signature = str(repository_binding['project_repository_signature'])
    agent_config = dict(instance.agent_config or {})
    stored_project_repository_signature = str(
        agent_config.get('project_repository_signature') or ''
    ).strip()
    should_rebind = False
    if allow_project_rebind:
        if stored_project_repository_signature:
            should_rebind = stored_project_repository_signature != project_repository_signature
        else:
            should_rebind = repository_signature != project_repository_signature

    if should_rebind:
        instance.repository_url = project_repository_spec['repository_url'] or None
        instance.repository_type = project_repository_spec['repository_type']
        instance.branch_name = project_repository_spec['branch_name']
        instance.manifest_xml = project_repository_spec['manifest_xml'] or None
        instance.group = project_repository_spec['group'] or None
        instance.agent_config = _persist_repository_signature_metadata(
            agent_config,
            repository_signature=project_repository_signature,
            project_repository_signature=project_repository_signature,
        )
        run_with_fresh_connection(
            instance.save,
            update_fields=[
                'repository_url',
                'repository_type',
                'branch_name',
                'manifest_xml',
                'group',
                'agent_config',
                'sys_update_datetime',
            ],
        )
        return project_repository_spec, True

    if (
        agent_config.get('repository_signature') != repository_signature
        or agent_config.get('project_repository_signature') != project_repository_signature
    ):
        instance.agent_config = _persist_repository_signature_metadata(
            agent_config,
            repository_signature=repository_signature,
            project_repository_signature=project_repository_signature,
        )
        run_with_fresh_connection(
            instance.save,
            update_fields=['agent_config', 'sys_update_datetime'],
        )
    return repository_spec, False


def _to_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _report_language_from_path(file_path: str | None) -> str:
    suffix = Path(str(file_path or '')).suffix.lower()
    return REPORT_LANGUAGE_BY_EXTENSION.get(suffix, '')


def _severity_distribution_from_findings(findings: list[AgentFinding]) -> dict[str, int]:
    distribution = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    for finding in findings:
        severity = str(getattr(finding, 'severity', '') or '').strip().lower()
        if severity in distribution:
            distribution[severity] += 1
    return distribution


def _vulnerability_types_from_findings(findings: list[AgentFinding]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for finding in findings:
        vuln_type = str(getattr(finding, 'vulnerability_type', '') or '').strip() or 'unknown'
        counter[vuln_type] += 1
    return dict(counter)


def _calculate_task_scores(findings: list[AgentFinding]) -> tuple[float, float]:
    penalty = sum(
        normalize_severity_weight(str(getattr(finding, 'severity', '') or '').strip().lower())
        for finding in findings
    )
    quality_score = max(0.0, 100.0 - penalty)
    security_score = max(0.0, 100.0 - penalty * 1.2)
    return round(quality_score, 2), round(security_score, 2)


def _duration_seconds(instance: AgentTask) -> float | None:
    if not instance.started_at or not instance.completed_at:
        return None
    return round(max((instance.completed_at - instance.started_at).total_seconds(), 0.0), 2)


FILE_COUNT_PATTERNS = (
    re.compile(r'包含\s*(\d+)\s*个指定文件'),
    re.compile(r'审计范围(?:限定)?为\s*(\d+)\s*个指定文件'),
    re.compile(r'搜索了\s*(\d+)\s*个文件'),
    re.compile(r'扫描(?:了)?\s*(\d+)\s*个文件'),
    re.compile(r'分析(?:了)?\s*(\d+)\s*个文件'),
    re.compile(r'(\d+)\s*/\s*(\d+)\s*个文件'),
)


def _extract_file_count_hints(message: str | None) -> tuple[int, int]:
    text = str(message or '').strip()
    if not text:
        return 0, 0

    current = 0
    total = 0
    for pattern in FILE_COUNT_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        groups = match.groups()
        if len(groups) == 1:
            total = max(total, _to_int(groups[0]))
            current = max(current, total)
        elif len(groups) >= 2:
            current = max(current, _to_int(groups[0]))
            total = max(total, _to_int(groups[1]))
    return current, total


def _serialize_report_payload(instance: AgentTask) -> dict:
    findings = list(instance.findings.filter(is_deleted=False).order_by('-sys_create_datetime'))
    return normalize_json_payload(
        {
            'task': serialize_task(instance),
            'summary': build_summary(instance, findings=findings),
            'checkpoints': build_phase_checkpoints(instance),
            'findings': [serialize_finding(item) for item in findings],
            'events': [serialize_event(item) for item in instance.events.filter(is_deleted=False).order_by('sequence')[:1000]],
        }
    )


def _render_agent_markdown_report(instance: AgentTask, payload: dict) -> str:
    task = payload.get('task') or {}
    summary = payload.get('summary') or {}
    findings = payload.get('findings') or []
    severity_distribution = summary.get('severity_distribution') or {}
    vulnerability_types = summary.get('vulnerability_types') or {}

    lines = [
        '# DeepAudit 代码审计报告',
        '',
        f"- 项目名称: {task.get('project_name') or instance.project.name}",
        f"- 任务 ID: {task.get('id') or instance.id}",
        f"- 任务名称: {task.get('name') or instance.name or 'Agent 审计任务'}",
        f"- 任务状态: {task.get('status') or instance.status}",
        f"- 当前阶段: {task.get('current_phase') or instance.current_phase or AGENT_PHASE_REPORTING}",
        f"- 生成时间: {format_datetime_text(timezone.now())}",
        '',
        '## 审计概览',
        '',
        f"- 安全评分: {task.get('security_score', 0):.2f} / 100",
        f"- 质量评分: {task.get('quality_score', 0):.2f} / 100",
        f"- 漏洞总数: {task.get('findings_count', len(findings))}",
        f"- 已验证漏洞: {task.get('verified_count', 0)}",
        f"- 误报数量: {task.get('false_positive_count', 0)}",
        f"- 工具调用: {task.get('tool_calls_count', 0)}",
        f"- Token 消耗: {task.get('tokens_used', 0)}",
        '',
        '## 严重级别分布',
        '',
        f"- Critical: {severity_distribution.get('critical', 0)}",
        f"- High: {severity_distribution.get('high', 0)}",
        f"- Medium: {severity_distribution.get('medium', 0)}",
        f"- Low: {severity_distribution.get('low', 0)}",
        '',
        '## 漏洞类型分布',
        '',
    ]

    if vulnerability_types:
        for vuln_type, count in sorted(vulnerability_types.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {vuln_type}: {count}")
    else:
        lines.append('- 未发现漏洞类型统计')

    lines.extend(['', '## 审计结论', ''])
    if findings:
        high_risk = severity_distribution.get('critical', 0) + severity_distribution.get('high', 0)
        lines.append(
            f"本次 Agent 审计共识别 {len(findings)} 个问题，其中高风险问题 {high_risk} 个。"
            ' 请优先修复 Critical / High 级别问题，并结合验证结果安排复测。'
        )
    else:
        lines.append('本次 Agent 审计未输出有效漏洞发现，请结合运行日志复核分析范围与提示词配置。')

    lines.extend(['', f"## 审计发现明细 ({len(findings)})", ''])
    if not findings:
        lines.append('当前没有可导出的漏洞明细。')
        return '\n'.join(lines).strip() + '\n'

    for index, finding in enumerate(findings, start=1):
        severity = str(finding.get('severity') or 'unknown').upper()
        file_path = finding.get('file_path') or '未知文件'
        line_start = finding.get('line_start')
        line_end = finding.get('line_end')
        suggestion = finding.get('suggestion') or '建议结合业务上下文补充修复方案。'
        description = finding.get('description') or '暂无详细描述。'
        code_snippet = finding.get('code_snippet') or ''
        vuln_type = finding.get('vulnerability_type') or 'unknown'
        verdict = (finding.get('poc') or {}).get('verdict')
        verification_label = '已验证' if finding.get('is_verified') else '待验证'
        if verdict == 'false_positive' or finding.get('status') == 'false_positive':
            verification_label = '误报'

        lines.extend(
            [
                f"### {index}. {finding.get('title') or '未命名问题'} [{severity}]",
                '',
                f"- 漏洞类型: {vuln_type}",
                f"- 文件位置: {file_path}",
                f"- 行号范围: {line_start or '-'}{' - ' + str(line_end) if line_end and line_end != line_start else ''}",
                f"- 验证状态: {verification_label}",
                f"- 置信度: {_to_float(finding.get('ai_confidence') or 0.0):.2f}",
                '',
                '#### 问题描述',
                '',
                description,
                '',
                '#### 修复建议',
                '',
                suggestion,
                '',
            ]
        )

        if code_snippet:
            language = _report_language_from_path(file_path)
            lines.extend(
                [
                    '#### 证据片段',
                    '',
                    f"```{language}".rstrip(),
                    code_snippet,
                    '```',
                    '',
                ]
            )

    lines.extend(
        [
            '## 后续建议',
            '',
            '1. 优先处理 Critical / High 级别问题，并补充回归验证。',
            '2. 对已验证问题补齐单元测试或安全回归用例，避免再次引入。',
            '3. 若存在误报，请在任务中标记并沉淀规则，减少后续噪音。',
        ]
    )
    return '\n'.join(lines).strip() + '\n'


def serialize_finding(instance: AgentFinding) -> dict:
    return {
        'id': str(instance.id),
        'task_id': str(instance.task_id),
        'vulnerability_type': instance.vulnerability_type,
        'severity': instance.severity,
        'title': instance.title,
        'description': instance.description,
        'file_path': instance.file_path,
        'line_start': instance.line_start,
        'line_end': instance.line_end,
        'code_snippet': instance.code_snippet,
        'is_verified': instance.is_verified,
        'ai_confidence': instance.ai_confidence,
        'status': instance.status,
        'suggestion': instance.suggestion,
        'poc': instance.poc or {},
        'sys_create_datetime': format_datetime_text(instance.sys_create_datetime),
        'sys_update_datetime': format_datetime_text(instance.sys_update_datetime),
    }


def serialize_event(instance: AgentEvent) -> dict:
    return {
        'id': str(instance.id),
        'task_id': str(instance.task_id),
        'event_type': instance.event_type,
        'phase': instance.phase,
        'message': instance.message,
        'sequence': instance.sequence,
        'tool_name': instance.tool_name,
        'tool_input': instance.tool_input or {},
        'tool_output': instance.tool_output or {},
        'tool_duration_ms': instance.tool_duration_ms,
        'progress_percent': instance.progress_percent,
        'finding_id': str(instance.finding_id) if instance.finding_id else None,
        'tokens_used': instance.tokens_used,
        'event_metadata': instance.event_metadata or {},
        'sys_create_datetime': format_datetime_text(instance.sys_create_datetime),
    }


def serialize_stream_event(instance: AgentEvent, *, include_tool_calls: bool = True) -> dict:
    metadata = normalize_json_payload(instance.event_metadata or {})
    payload = {
        'id': str(instance.id),
        'task_id': str(instance.task_id),
        'type': instance.event_type,
        'event_type': instance.event_type,
        'phase': instance.phase,
        'message': instance.message,
        'sequence': instance.sequence,
        'timestamp': instance.sys_create_datetime.isoformat() if instance.sys_create_datetime else None,
    }

    if instance.progress_percent is not None:
        payload['progress_percent'] = instance.progress_percent
    if instance.tokens_used is not None:
        payload['tokens_used'] = instance.tokens_used
    if instance.finding_id:
        payload['finding_id'] = str(instance.finding_id)

    if metadata:
        payload['metadata'] = metadata
        for key in (
            'agent_id',
            'accumulated',
            'agent_name',
            'agent_type',
            'current',
            'findings_count',
            'iteration',
            'node',
            'parent_agent_id',
            'security_score',
            'status',
            'summary',
            'token',
            'total',
            'tool_calls',
        ):
            if key in metadata and key not in payload:
                payload[key] = metadata[key]

    if include_tool_calls and instance.tool_name:
        tool_input = normalize_json_payload(instance.tool_input or {})
        tool_output = normalize_json_payload(instance.tool_output or {})
        payload.update(
            {
                'tool_name': instance.tool_name,
                'tool_input': tool_input,
                'tool_output': tool_output,
                'tool_duration_ms': instance.tool_duration_ms,
                'tool': {
                    'name': instance.tool_name,
                    'input': tool_input,
                    'output': tool_output,
                    'duration_ms': instance.tool_duration_ms,
                },
            }
        )

    return normalize_json_payload(payload)


def _format_sse_event(payload: dict) -> str:
    event_type = str(payload.get('type') or payload.get('event_type') or 'message')
    data = normalize_json_payload({**payload, 'type': event_type})
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def serialize_task(instance: AgentTask) -> dict:
    agent_config = dict(instance.agent_config or {})
    selection_stats = dict(agent_config.get('selection_stats') or {})
    repository_runtime = dict(agent_config.get('repository_runtime') or {})
    return {
        'id': str(instance.id),
        'project_id': str(instance.project_id),
        'project_name': instance.project.name if instance.project else '',
        'created_by': str(instance.created_by_id),
        'created_by_name': serialize_user_brief(instance.created_by).get('name') if instance.created_by else None,
        'name': instance.name,
        'description': instance.description,
        'task_type': instance.task_type,
        'status': instance.status,
        'current_phase': instance.current_phase,
        'current_step': instance.current_step,
        'audit_scope': instance.audit_scope or {},
        'target_vulnerabilities': list(instance.target_vulnerabilities or []),
        'verification_level': instance.verification_level,
        'repository_url': instance.repository_url,
        'repository_type': normalize_repository_type(instance.repository_type),
        'repository_signature': str(
            agent_config.get('repository_signature')
            or repository_spec_signature(build_task_repository_spec(instance))
        ),
        'branch_name': instance.branch_name,
        'manifest_xml': instance.manifest_xml,
        'group': instance.group,
        'exclude_patterns': list(instance.exclude_patterns or []),
        'target_files': list(instance.target_files or []),
        'selected_target_count': _to_int(selection_stats.get('selected_target_count'), len(instance.target_files or [])),
        'selected_directory_count': _to_int(selection_stats.get('selected_directory_count'), 0),
        'resolved_file_count': _to_int(selection_stats.get('resolved_file_count'), 0),
        'workspace_source': str(repository_runtime.get('workspace_source') or ''),
        'max_iterations': instance.max_iterations,
        'timeout_seconds': instance.timeout_seconds,
        'total_files': instance.total_files,
        'indexed_files': instance.indexed_files,
        'analyzed_files': instance.analyzed_files,
        'files_with_findings': instance.files_with_findings,
        'total_chunks': instance.total_chunks,
        'total_iterations': instance.total_iterations,
        'tool_calls_count': instance.tool_calls_count,
        'tokens_used': instance.tokens_used,
        'findings_count': instance.findings_count,
        'verified_count': instance.verified_count,
        'false_positive_count': instance.false_positive_count,
        'critical_count': instance.critical_count,
        'high_count': instance.high_count,
        'medium_count': instance.medium_count,
        'low_count': instance.low_count,
        'quality_score': instance.quality_score,
        'security_score': instance.security_score,
        'progress_percentage': instance.progress_percentage,
        'audit_plan': instance.audit_plan or [],
        'error_message': instance.error_message,
        'started_at': format_datetime_text(instance.started_at),
        'completed_at': format_datetime_text(instance.completed_at),
        'sys_create_datetime': format_datetime_text(instance.sys_create_datetime),
        'sys_update_datetime': format_datetime_text(instance.sys_update_datetime),
    }


def _accessible_queryset(user):
    from apps.deepaudit.permissions import accessible_project_queryset

    projects = accessible_project_queryset(user)
    return AgentTask.objects.filter(project__in=projects, is_deleted=False).select_related('project', 'created_by')


def list_tasks(user, *, project_id: str = '', status: str = '', page: int = 1, page_size: int = 20) -> dict:
    queryset = _accessible_queryset(user)
    if project_id:
        access = require_project_role(user, project_id, min_role='viewer')
        queryset = queryset.filter(project=access.project)
    if status:
        queryset = queryset.filter(status=status)
    total = queryset.count()
    start = max(page - 1, 0) * page_size
    items = [serialize_task(item) for item in queryset.order_by('-sys_create_datetime')[start:start + page_size]]
    return {'items': items, 'total': total}


def get_task(user, task_id: str) -> AgentTask:
    instance = get_object_or_404(AgentTask.objects.select_related('project', 'created_by'), id=task_id, is_deleted=False)
    require_project_role(user, instance.project, min_role='viewer')
    return instance


def create_task(user, payload: dict) -> AgentTask:
    access = require_project_role(user, payload.get('project_id'), min_role='member')
    project_repository_type = normalize_repository_type(access.project.repository_type)
    requested_repository_type = payload.get('repository_type')
    requested_repository_url = str(payload.get('repository_url') or '').strip()
    normalized_requested_repository_type = (
        normalize_repository_type(requested_repository_type)
        if requested_repository_type is not None
        else None
    )
    repository_type_mismatch = (
        normalized_requested_repository_type is not None
        and normalized_requested_repository_type != project_repository_type
    )
    if repository_type_mismatch:
        logger.warning(
            'DeepAudit agent task create request repository_type mismatch and will use project config: '
            'project_id=%s user_id=%s requested_repository_type=%s project_repository_type=%s',
            access.project.id,
            getattr(user, 'id', ''),
            normalized_requested_repository_type,
            project_repository_type,
        )
    if requested_repository_url and requested_repository_url != str(access.project.repository_url or '').strip():
        logger.warning(
            'DeepAudit agent task create request repository_url mismatch: project_id=%s user_id=%s requested_repository_url=%s project_repository_url=%s',
            access.project.id,
            getattr(user, 'id', ''),
            requested_repository_url,
            str(access.project.repository_url or '').strip() or '-',
        )
    logger.debug(
        'DeepAudit agent task create payload repository hints: project_id=%s requested_repository_type=%s '
        'branch_name=%s manifest_xml=%s group=%s',
        access.project.id,
        normalized_requested_repository_type or '-',
        str(payload.get('branch_name') or '').strip() or '-',
        str(payload.get('manifest_xml') or '').strip() or '-',
        str(payload.get('group') or '').strip() or '-',
    )
    repository_binding = build_project_repository_binding(
        access.project,
        branch_name=payload.get('branch_name'),
        manifest_xml=payload.get('manifest_xml'),
        group=payload.get('group'),
    )
    repository_spec = repository_binding['repository_spec']
    project_repository_spec = repository_binding['project_repository_spec']
    repository_signature = str(repository_binding['repository_signature'])
    project_repository_signature = str(repository_binding['project_repository_signature'])
    if access.project.source_type == 'repository':
        if not repository_spec['repository_url']:
            raise HttpError(422, '仓库任务必须填写 repository_url')
        if normalize_repository_type(repository_spec['repository_type']) == 'multi' and not repository_spec['manifest_xml']:
            raise HttpError(422, '多仓任务必须填写 manifest_xml')
        _validate_selection_repository_signature(
            selected_paths=list(payload.get('target_files') or []),
            requested_signature=str(payload.get('repository_signature') or '').strip(),
            effective_signature=repository_signature,
        )
    target_vulnerabilities = list(payload.get('target_vulnerabilities') or [])
    if not target_vulnerabilities and project_likely_c_family(
        access.project,
        file_paths=payload.get('target_files') or [],
    ):
        target_vulnerabilities = list(C_FAMILY_TARGET_VULNERABILITIES)
    agent_config = dict(payload.get('agent_config') or {})
    agent_config = _persist_repository_signature_metadata(
        agent_config,
        repository_signature=repository_signature,
        project_repository_signature=project_repository_signature,
    )
    agent_config.setdefault(
        'selection_stats',
        {
            'selected_target_count': len(payload.get('target_files') or []),
            'selected_directory_count': 0,
            'resolved_file_count': 0,
        },
    )
    instance = AgentTask.objects.create(
        project=access.project,
        created_by=user,
        name=payload.get('name') or f'{access.project.name} Agent 审计',
        description=payload.get('description') or '',
        audit_scope=payload.get('audit_scope') or {},
        target_vulnerabilities=target_vulnerabilities,
        verification_level=payload.get('verification_level') or 'sandbox',
        repository_url=repository_spec['repository_url'] or None,
        repository_type=repository_spec['repository_type'],
        branch_name=repository_spec['branch_name'],
        manifest_xml=repository_spec['manifest_xml'] or None,
        group=repository_spec['group'] or None,
        exclude_patterns=payload.get('exclude_patterns') or [],
        target_files=payload.get('target_files') or [],
        agent_config=agent_config,
        max_iterations=int(payload.get('max_iterations') or 50),
        timeout_seconds=int(payload.get('timeout_seconds') or 1800),
        status='pending',
        current_phase=AGENT_PHASE_PLANNING,
        sys_creator=user,
        sys_modifier=user,
    )
    metadata = _build_repository_snapshot_metadata(
        repository_spec,
        task_id=str(instance.id),
        project_id=str(access.project.id),
        project_repository_type=project_repository_type,
        requested_repository_type=normalized_requested_repository_type,
    )
    if repository_type_mismatch:
        create_event(
            instance,
            'warning',
            phase=instance.current_phase,
            message='请求仓库类型与项目配置不一致，已按项目当前配置创建 Agent 任务',
            metadata=metadata,
        )
    logger.info(
        'DeepAudit agent task %s created with repository snapshot for project %s: %s',
        instance.id,
        access.project.id,
        format_repository_spec_for_log(repository_spec),
    )
    create_event(
        instance,
        'info',
        phase=instance.current_phase,
        message='Agent任务已入队，仓库快照已保存，等待 Worker 启动',
        metadata=metadata,
    )
    return instance


def cancel_task(user, task_id: str) -> bool:
    instance = get_task(user, task_id)
    if instance.status not in ACTIVE_STATUSES:
        return True
    instance.status = 'cancelled'
    instance.current_step = truncate_runtime_text('用户已取消任务')
    instance.completed_at = timezone.now()
    instance.sys_modifier = user
    instance.save(update_fields=['status', 'current_step', 'completed_at', 'sys_modifier', 'sys_update_datetime'])
    create_event(instance, 'task_cancel', message='用户取消了 Agent 审计任务', phase=instance.current_phase)
    return True


def mark_dispatch_failed(instance: AgentTask, message: str) -> AgentTask:
    instance.status = 'failed'
    instance.current_step = truncate_runtime_text('任务队列不可用')
    instance.error_message = message
    instance.completed_at = timezone.now()
    if instance.created_by_id:
        instance.sys_modifier = instance.created_by
    instance.save(update_fields=['status', 'current_step', 'error_message', 'completed_at', 'sys_modifier', 'sys_update_datetime'])
    create_event(instance, 'task_error', phase=instance.current_phase or AGENT_PHASE_PLANNING, message=message)
    return instance


def _is_restorable_checkpoint(checkpoint: AgentCheckpoint | None) -> bool:
    if not checkpoint:
        return False
    try:
        from apps.deepaudit.agent_engine.core.persistence import agent_persistence

        return agent_persistence.is_restorable_payload(checkpoint.state_data or {})
    except Exception:
        return False


def _resolve_resume_checkpoint(source_task: AgentTask, checkpoint: AgentCheckpoint) -> AgentCheckpoint | None:
    if _is_restorable_checkpoint(checkpoint) and str(checkpoint.agent_type or '').strip().lower() == 'orchestrator':
        return checkpoint

    orchestrator_candidates = source_task.persisted_checkpoints.filter(
        is_deleted=False,
        agent_type='orchestrator',
        sys_create_datetime__lte=checkpoint.sys_create_datetime,
    ).order_by('-sys_create_datetime')
    for candidate in orchestrator_candidates:
        if _is_restorable_checkpoint(candidate):
            return candidate

    latest_orchestrator = source_task.persisted_checkpoints.filter(
        is_deleted=False,
        agent_type='orchestrator',
    ).order_by('-sys_create_datetime')
    for candidate in latest_orchestrator:
        if _is_restorable_checkpoint(candidate):
            return candidate

    if _is_restorable_checkpoint(checkpoint):
        return checkpoint
    return None


def resume_task_from_checkpoint(user, task_id: str, checkpoint_id: str) -> AgentTask:
    source_task = get_task(user, task_id)
    require_project_role(user, source_task.project, min_role='member')
    selected_checkpoint = get_object_or_404(
        AgentCheckpoint.objects.filter(is_deleted=False),
        id=checkpoint_id,
        task=source_task,
    )
    resume_checkpoint = _resolve_resume_checkpoint(source_task, selected_checkpoint)
    if not resume_checkpoint:
        raise HttpError(422, '所选检查点不包含可恢复的运行时状态，请选择带状态快照的检查点后重试')

    payload = {
        'project_id': str(source_task.project_id),
        'name': f"{source_task.name or source_task.project.name} [resume]",
        'description': source_task.description or '',
        'audit_scope': {
            **dict(source_task.audit_scope or {}),
            'resume_from_checkpoint_id': str(resume_checkpoint.id),
            'resume_from_task_id': str(source_task.id),
            'resume_agent_id': resume_checkpoint.agent_id,
            'resume_requested_checkpoint_id': str(selected_checkpoint.id),
        },
        'target_vulnerabilities': list(source_task.target_vulnerabilities or []),
        'verification_level': source_task.verification_level or 'sandbox',
        'exclude_patterns': list(source_task.exclude_patterns or []),
        'target_files': list(source_task.target_files or []),
        'agent_config': {
            **dict(source_task.agent_config or {}),
            'resume': {
                'mode': 'checkpoint_state',
                'source_task_id': str(source_task.id),
                'requested_checkpoint_id': str(selected_checkpoint.id),
                'resume_checkpoint_id': str(resume_checkpoint.id),
                'resume_agent_id': str(resume_checkpoint.agent_id),
                'resume_agent_type': str(resume_checkpoint.agent_type or '').strip().lower() or 'orchestrator',
            },
        },
        'max_iterations': int(source_task.max_iterations or 50),
        'timeout_seconds': int(source_task.timeout_seconds or 1800),
    }
    resumed_task = create_task(user, payload)
    resumed_task.description = (
        f"{resumed_task.description}\n\nResumed from checkpoint {resume_checkpoint.id} ({resume_checkpoint.checkpoint_name or resume_checkpoint.checkpoint_type})."
    ).strip()
    resumed_task.audit_scope = payload['audit_scope']
    resumed_task.agent_config = {
        **dict(resumed_task.agent_config or {}),
        **dict(payload['agent_config'] or {}),
    }
    resumed_task.sys_modifier = user
    resumed_task.save(update_fields=['description', 'audit_scope', 'agent_config', 'sys_modifier', 'sys_update_datetime'])
    dispatch_error = dispatch_deepaudit_task(run_agent_task, str(resumed_task.id))
    if dispatch_error:
        return mark_dispatch_failed(resumed_task, dispatch_error)
    create_event(
        resumed_task,
        'info',
        phase=resumed_task.current_phase,
        message=f'从检查点 {resume_checkpoint.id} 恢复任务状态并重新继续执行',
        metadata={
            'source_task_id': str(source_task.id),
            'source_checkpoint_id': str(resume_checkpoint.id),
            'requested_checkpoint_id': str(selected_checkpoint.id),
        },
    )
    return resumed_task


def list_events(user, task_id: str, *, after_sequence: int = 0, limit: int = 200) -> list[dict]:
    instance = get_task(user, task_id)
    queryset = instance.events.filter(is_deleted=False)
    if after_sequence > 0:
        queryset = queryset.filter(sequence__gt=after_sequence)
    return [serialize_event(item) for item in queryset.order_by('sequence')[: max(limit, 1)]]


def stream_events_response(
    user,
    task_id: str,
    *,
    include_thinking: bool = True,
    include_tool_calls: bool = True,
    after_sequence: int = 0,
) -> StreamingHttpResponse:
    instance = get_task(user, task_id)

    skip_types: set[str] = set()
    if not include_thinking:
        skip_types.update(THINKING_EVENT_TYPES)
    if not include_tool_calls:
        skip_types.update(TOOL_EVENT_TYPES)

    @sync_to_async
    def load_stream_state(last_sequence: int):
        def _load():
            events = list(
                AgentEvent.objects.filter(task=instance, is_deleted=False, sequence__gt=last_sequence)
                .order_by('sequence')[:100]
            )
            current_task = AgentTask.objects.filter(id=instance.id, is_deleted=False).only(
                'status',
                'findings_count',
                'security_score',
            ).first()
            return events, current_task

        return run_with_fresh_connection(_load)

    async def event_generator():
        last_sequence = max(after_sequence, 0)
        poll_interval = 1.0
        heartbeat_interval = 15.0
        max_idle = 60.0
        heartbeat_elapsed = 0.0
        idle_time = 0.0

        while True:
            events, current_task = await load_stream_state(last_sequence)

            if events:
                idle_time = 0.0
                for event in events:
                    last_sequence = event.sequence
                    if event.event_type in skip_types:
                        continue
                    yield _format_sse_event(
                        serialize_stream_event(event, include_tool_calls=include_tool_calls),
                    )
            else:
                idle_time += poll_interval

            heartbeat_elapsed += poll_interval
            status = current_task.status if current_task else None

            if status in TERMINAL_STATUSES:
                yield _format_sse_event(
                    {
                        'type': 'task_end',
                        'status': status,
                        'message': f'任务已{status}',
                        'findings_count': current_task.findings_count if current_task else 0,
                        'security_score': current_task.security_score if current_task else 0,
                    }
                )
                break

            if heartbeat_elapsed >= heartbeat_interval:
                heartbeat_elapsed = 0.0
                yield _format_sse_event(
                    {
                        'type': 'heartbeat',
                        'timestamp': timezone.now().isoformat(),
                    }
                )

            if idle_time >= max_idle:
                break

            await asyncio.sleep(poll_interval)

    response = StreamingHttpResponse(
        event_generator(),
        content_type='text/event-stream; charset=utf-8',
    )
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    response['X-Accel-Buffering'] = 'no'
    return response


def list_findings(user, task_id: str, *, severity: str = '', vulnerability_type: str = '', status: str = '') -> list[dict]:
    instance = get_task(user, task_id)
    queryset = instance.findings.filter(is_deleted=False)
    if severity:
        queryset = queryset.filter(severity=severity)
    if vulnerability_type:
        queryset = queryset.filter(vulnerability_type=vulnerability_type)
    if status:
        queryset = queryset.filter(status=status)
    return [serialize_finding(item) for item in queryset.order_by('-sys_create_datetime')]


def update_finding_status(user, task_id: str, finding_id: str, status: str) -> dict:
    if status not in VALID_FINDING_STATUSES:
        raise HttpError(422, '发现状态不合法')
    instance = get_task(user, task_id)
    require_project_role(user, instance.project, min_role='member')
    finding = get_object_or_404(AgentFinding, id=finding_id, task=instance, is_deleted=False)
    finding.status = status
    finding.is_verified = status in {'fixed', 'wont_fix'} or finding.is_verified
    finding.sys_modifier = user
    finding.save()
    create_event(instance, 'finding_update', message=f'发现状态更新为 {status}', phase=instance.current_phase, finding=finding, metadata={'status': status})
    return serialize_finding(finding)


def refresh_task_snapshot(
    task_or_id: AgentTask | str,
    *,
    status=UNSET,
    current_phase=UNSET,
    current_step=UNSET,
    completed_at=UNSET,
    error_message=UNSET,
) -> AgentTask | None:
    def _refresh() -> AgentTask | None:
        if isinstance(task_or_id, AgentTask):
            instance = AgentTask.objects.filter(id=task_or_id.id, is_deleted=False).first()
        else:
            instance = AgentTask.objects.filter(id=task_or_id, is_deleted=False).first()

        if not instance:
            return None

        events = list(instance.events.filter(is_deleted=False).order_by('sequence'))
        findings = list(instance.findings.filter(is_deleted=False))

        severity_distribution = _severity_distribution_from_findings(findings)
        vulnerability_types = _vulnerability_types_from_findings(findings)
        quality_score, security_score = _calculate_task_scores(findings)

        tokens_by_agent: dict[str, int] = {}
        tools_by_agent: dict[str, int] = {}
        iterations_by_agent: dict[str, int] = {}
        agent_config = dict(instance.agent_config or {})
        selection_stats = dict(agent_config.get('selection_stats') or {})
        selected_target_count = _to_int(selection_stats.get('selected_target_count'), len(instance.target_files or []))
        selected_directory_count = _to_int(selection_stats.get('selected_directory_count'), 0)
        resolved_file_count = _to_int(selection_stats.get('resolved_file_count'), 0)
        target_file_count = resolved_file_count
        if target_file_count <= 0 and selected_directory_count <= 0:
            target_file_count = selected_target_count
        indexed_files = instance.indexed_files
        analyzed_files = instance.analyzed_files
        total_files = max(instance.total_files, target_file_count)
        latest_phase = instance.current_phase
        latest_step = truncate_runtime_text(instance.current_step)

        for event in events:
            metadata = dict(event.event_metadata or {})
            agent_id = str(metadata.get('agent_id') or metadata.get('agent_name') or '').strip()
            if agent_id:
                tokens_by_agent[agent_id] = max(
                    tokens_by_agent.get(agent_id, 0),
                    _to_int(metadata.get('tokens_used'), _to_int(event.tokens_used, 0)),
                )
                tools_by_agent[agent_id] = max(
                    tools_by_agent.get(agent_id, 0),
                    _to_int(metadata.get('tool_calls'), 0),
                )
                iterations_by_agent[agent_id] = max(
                    iterations_by_agent.get(agent_id, 0),
                    _to_int(metadata.get('iteration'), 0),
                )

            if event.phase:
                latest_phase = event.phase
            if event.message:
                latest_step = truncate_runtime_text(event.message)

            current = _to_int(metadata.get('current'))
            total = _to_int(metadata.get('total'))
            hinted_current, hinted_total = _extract_file_count_hints(event.message)
            current = max(current, hinted_current)
            total = max(total, hinted_total)
            if total > 0:
                total_files = max(total_files, total)
            resolved_hint = _to_int(metadata.get('resolved_file_count'))
            if resolved_hint > 0:
                total_files = max(total_files, resolved_hint)
            if event.phase == AGENT_PHASE_INDEXING and current > 0:
                indexed_files = max(indexed_files, current)
            if event.phase == AGENT_PHASE_ANALYSIS and current > 0:
                analyzed_files = max(analyzed_files, current)

            if event.event_type in {'dispatch', 'dispatch_complete'} and total > 0:
                total_files = max(total_files, total)
            if current > 0 and event.event_type in {'llm_observation', 'progress', 'info'}:
                analyzed_files = max(analyzed_files, current)

        if total_files <= 0 and target_file_count > 0:
            total_files = target_file_count

        if instance.status in TERMINAL_STATUSES and total_files > 0:
            analysis_reached = any([
                analyzed_files > 0,
                findings,
                any(event.event_type in {'dispatch', 'dispatch_complete', 'tool_call', 'tool_result'} for event in events),
            ])
            if analysis_reached:
                analyzed_files = max(analyzed_files, total_files)
            if indexed_files <= 0 and any(event.event_type in {'dispatch', 'dispatch_complete'} for event in events):
                indexed_files = max(indexed_files, min(analyzed_files or total_files, total_files))

        findings_count = len(findings)
        files_with_findings = len({str(item.file_path).strip() for item in findings if str(item.file_path or '').strip()})
        verified_count = sum(1 for item in findings if item.is_verified)
        false_positive_count = sum(
            1
            for item in findings
            if item.status == 'false_positive' or str((item.poc or {}).get('verdict') or '').strip().lower() == 'false_positive'
        )

        if status is UNSET:
            computed_status = instance.status
            if computed_status not in TERMINAL_STATUSES and latest_phase:
                computed_status = TASK_STATUS_BY_PHASE.get(latest_phase, computed_status or 'running')
        else:
            computed_status = status

        new_values = {
            'current_phase': latest_phase if current_phase is UNSET else current_phase,
            'current_step': latest_step if current_step is UNSET else truncate_runtime_text(current_step),
            'status': computed_status,
            'total_files': total_files,
            'indexed_files': indexed_files,
            'analyzed_files': analyzed_files,
            'files_with_findings': files_with_findings,
            'total_iterations': sum(iterations_by_agent.values()),
            'tool_calls_count': sum(tools_by_agent.values()) or sum(1 for item in events if item.event_type in TOOL_COUNT_EVENT_TYPES),
            'tokens_used': sum(tokens_by_agent.values()),
            'findings_count': findings_count,
            'verified_count': verified_count,
            'false_positive_count': false_positive_count,
            'critical_count': severity_distribution['critical'],
            'high_count': severity_distribution['high'],
            'medium_count': severity_distribution['medium'],
            'low_count': severity_distribution['low'],
            'quality_score': quality_score,
            'security_score': security_score,
            'completed_at': instance.completed_at if completed_at is UNSET else completed_at,
            'error_message': instance.error_message if error_message is UNSET else error_message,
        }

        update_fields: list[str] = []
        for field, value in new_values.items():
            if getattr(instance, field) != value:
                setattr(instance, field, value)
                update_fields.append(field)

        if update_fields:
            instance.save(update_fields=update_fields + ['sys_update_datetime'])
        return instance

    return run_with_fresh_connection(_refresh)


def build_summary(instance: AgentTask, *, findings: list[AgentFinding] | None = None) -> dict:
    findings = findings or list(instance.findings.filter(is_deleted=False))
    severity_distribution = _severity_distribution_from_findings(findings)
    vulnerability_types = _vulnerability_types_from_findings(findings)
    phases_completed = list(
        instance.events.filter(event_type='phase_complete', is_deleted=False)
        .order_by('sequence')
        .values_list('phase', flat=True)
        .distinct()
    )
    return {
        'task_id': str(instance.id),
        'status': instance.status,
        'progress_percentage': instance.progress_percentage,
        'security_score': instance.security_score,
        'quality_score': instance.quality_score,
        'severity_distribution': severity_distribution,
        'vulnerability_types': vulnerability_types,
        'phases_completed': phases_completed,
        'statistics': {
            'total_files': instance.total_files,
            'indexed_files': instance.indexed_files,
            'analyzed_files': instance.analyzed_files,
            'files_with_findings': instance.files_with_findings,
            'total_chunks': instance.total_chunks,
            'findings_count': instance.findings_count,
            'verified_count': instance.verified_count,
            'false_positive_count': instance.false_positive_count,
        },
        'duration_seconds': _duration_seconds(instance),
    }


def build_phase_checkpoints(instance: AgentTask) -> list[dict]:
    phase_order = [choice[0] for choice in AGENT_PHASE_CHOICES]
    checkpoint_map = {
        phase: {
            'id': phase,
            'phase': phase,
            'status': 'pending',
            'sequence': 0,
            'message': None,
            'timestamp': None,
        }
        for phase in phase_order
    }

    persisted_by_phase: dict[str, AgentCheckpoint] = {}
    for checkpoint in instance.persisted_checkpoints.filter(is_deleted=False).order_by('-sys_create_datetime'):
        phase = str((checkpoint.checkpoint_metadata or {}).get('phase') or '').strip()
        if phase and phase not in persisted_by_phase:
            persisted_by_phase[phase] = checkpoint

    for event in instance.events.filter(is_deleted=False).order_by('sequence'):
        phase = event.phase
        if not phase or phase not in checkpoint_map:
            continue

        checkpoint = checkpoint_map[phase]
        if event.event_type == 'phase_start':
            checkpoint['status'] = 'running'
        elif event.event_type == 'phase_complete':
            checkpoint['status'] = 'completed'
        elif checkpoint['status'] == 'pending':
            checkpoint['status'] = 'running'

        if checkpoint['status'] != 'completed' or event.event_type in {'phase_start', 'phase_complete'}:
            checkpoint['sequence'] = event.sequence
            checkpoint['message'] = event.message
            checkpoint['timestamp'] = format_datetime_text(event.sys_create_datetime)

    active_phase = str(instance.current_phase or '').strip()
    if active_phase in checkpoint_map:
        if instance.status in {'failed', 'cancelled'} and checkpoint_map[active_phase]['status'] not in {'pending', 'completed'}:
            checkpoint_map[active_phase]['status'] = instance.status
            checkpoint_map[active_phase]['message'] = instance.current_step or checkpoint_map[active_phase]['message']
        elif instance.status == 'completed' and checkpoint_map[active_phase]['status'] != 'completed':
            checkpoint_map[active_phase]['status'] = 'completed'
            checkpoint_map[active_phase]['message'] = instance.current_step or checkpoint_map[active_phase]['message']

    inferred_completed: set[str] = {AGENT_PHASE_PLANNING}
    has_file_scope = any([
        instance.total_files > 0,
        instance.indexed_files > 0,
        instance.analyzed_files > 0,
        instance.findings_count > 0,
        instance.tokens_used > 0,
        instance.tool_calls_count > 0,
    ])
    if has_file_scope or instance.status in TERMINAL_STATUSES:
        inferred_completed.add(AGENT_PHASE_RECONNAISSANCE)

    analysis_reached = any([
        instance.analyzed_files > 0,
        instance.findings_count > 0,
        active_phase in {AGENT_PHASE_ANALYSIS, AGENT_PHASE_VERIFICATION, AGENT_PHASE_REPORTING},
        instance.status in {'analyzing', 'verifying', 'reporting', 'completed', 'failed', 'cancelled'},
    ])
    if analysis_reached:
        inferred_completed.add(AGENT_PHASE_ANALYSIS)

    verification_reached = any([
        instance.verification_level != 'analysis_only' and instance.status == 'completed',
        instance.verified_count > 0,
        instance.false_positive_count > 0,
        active_phase in {AGENT_PHASE_VERIFICATION, AGENT_PHASE_REPORTING},
        instance.status == 'verifying',
    ])
    if verification_reached:
        inferred_completed.add(AGENT_PHASE_VERIFICATION)

    reporting_reached = any([
        active_phase == AGENT_PHASE_REPORTING,
        instance.status == 'completed',
        bool(instance.completed_at),
    ])
    if reporting_reached:
        inferred_completed.add(AGENT_PHASE_REPORTING)

    legacy_timestamp = format_datetime_text(instance.completed_at or instance.started_at or instance.sys_update_datetime)
    for phase in phase_order:
        checkpoint = checkpoint_map[phase]
        if checkpoint['status'] != 'pending' or phase not in inferred_completed:
            continue

        inferred_status = 'completed'
        if active_phase == phase and instance.status not in TERMINAL_STATUSES:
            inferred_status = 'running'
        checkpoint_map[phase] = {
            **checkpoint,
            'id': phase,
            'status': inferred_status,
            'message': checkpoint['message'] or f'{PHASE_LABELS.get(phase, phase.title())} (legacy inferred)',
            'timestamp': checkpoint['timestamp'] or legacy_timestamp,
        }

    for phase, persisted in persisted_by_phase.items():
        if phase not in checkpoint_map:
            continue
        metadata = dict(persisted.checkpoint_metadata or {})
        checkpoint_map[phase] = {
            **checkpoint_map[phase],
            'id': str(persisted.id),
            'status': str(persisted.status or checkpoint_map[phase]['status']),
            'sequence': _to_int(metadata.get('sequence'), checkpoint_map[phase]['sequence']),
            'message': persisted.checkpoint_name or checkpoint_map[phase]['message'],
            'timestamp': format_datetime_text(persisted.sys_create_datetime) or checkpoint_map[phase]['timestamp'],
            'agent_id': persisted.agent_id,
            'agent_name': persisted.agent_name,
            'agent_type': persisted.agent_type,
            'iteration': persisted.iteration,
            'checkpoint_type': persisted.checkpoint_type,
        }

    return [checkpoint_map[phase] for phase in phase_order]


def serialize_persisted_checkpoint(checkpoint: AgentCheckpoint) -> dict:
    metadata = dict(checkpoint.checkpoint_metadata or {})
    return {
        'id': str(checkpoint.id),
        'phase': str(metadata.get('phase') or checkpoint.agent_type or ''),
        'status': checkpoint.status,
        'sequence': _to_int(metadata.get('sequence'), 0),
        'message': checkpoint.checkpoint_name,
        'timestamp': format_datetime_text(checkpoint.sys_create_datetime),
        'agent_id': checkpoint.agent_id,
        'agent_name': checkpoint.agent_name,
        'agent_type': checkpoint.agent_type,
        'iteration': checkpoint.iteration,
        'checkpoint_type': checkpoint.checkpoint_type,
    }


def list_checkpoints(instance: AgentTask, *, agent_id: str = '', limit: int = 20) -> list[dict]:
    queryset = instance.persisted_checkpoints.filter(is_deleted=False)
    normalized_agent_id = str(agent_id or '').strip()
    if normalized_agent_id:
        queryset = queryset.filter(agent_id=normalized_agent_id)
    checkpoints = list(queryset.order_by('-sys_create_datetime')[: max(1, min(limit, 100))])
    if checkpoints:
        return [serialize_persisted_checkpoint(item) for item in checkpoints]
    return build_phase_checkpoints(instance)


def build_checkpoints(instance: AgentTask) -> list[dict]:
    return build_phase_checkpoints(instance)


def persist_checkpoint(
    task_or_id: AgentTask | str,
    *,
    checkpoint_type: str = 'auto',
    checkpoint_name: str | None = None,
    phase: str | None = None,
    sequence: int | None = None,
) -> AgentCheckpoint | None:
    ensure_runtime_db_connection()
    instance = refresh_task_snapshot(task_or_id)
    if not instance:
        return None

    recent_events = list(instance.events.filter(is_deleted=False).order_by('-sequence')[:20])
    latest_event = recent_events[0] if recent_events else None
    metadata = dict((latest_event.event_metadata or {}) if latest_event else {})
    checkpoint_phase = str(phase or metadata.get('phase') or instance.current_phase or '').strip() or None
    agent_id = str(metadata.get('agent_id') or metadata.get('agent_name') or instance.id).strip() or str(instance.id)
    agent_name = str(metadata.get('agent_name') or 'Orchestrator').strip() or 'Orchestrator'
    agent_type = str(metadata.get('agent_type') or 'orchestrator').strip() or 'orchestrator'
    parent_agent_id = str(metadata.get('parent_agent_id') or '').strip() or None
    iteration = _to_int(metadata.get('iteration'), 0)

    findings = instance.findings.filter(is_deleted=False).order_by('-sys_create_datetime')[:20]
    state_data = {
        'task': serialize_task(instance),
        'summary': build_summary(instance),
        'tree': build_tree(instance),
        'recent_events': [
            {
                'sequence': event.sequence,
                'event_type': event.event_type,
                'phase': event.phase,
                'message': event.message,
                'timestamp': format_datetime_text(event.sys_create_datetime),
            }
            for event in reversed(recent_events)
        ],
        'recent_findings': [serialize_finding(finding) for finding in findings],
    }
    checkpoint = AgentCheckpoint.objects.create(
        task=instance,
        agent_id=agent_id,
        agent_name=agent_name,
        agent_type=agent_type,
        parent_agent_id=parent_agent_id,
        state_data=state_data,
        iteration=iteration,
        status=instance.status,
        total_tokens=instance.tokens_used,
        tool_calls=instance.tool_calls_count,
        findings_count=instance.findings_count,
        checkpoint_type=checkpoint_type,
            checkpoint_name=truncate_runtime_text(
                checkpoint_name or instance.current_step or instance.current_phase or checkpoint_type,
                max_length=CHECKPOINT_NAME_MAX_LENGTH,
            ),
        checkpoint_metadata={
            'phase': checkpoint_phase,
            'sequence': sequence or (latest_event.sequence if latest_event else 0),
        },
        sys_creator=instance.created_by,
        sys_modifier=instance.created_by,
    )
    stale_ids = list(
        instance.persisted_checkpoints.filter(is_deleted=False)
        .order_by('-sys_create_datetime')
        .values_list('id', flat=True)[MAX_PERSISTED_CHECKPOINTS:]
    )
    if stale_ids:
        AgentCheckpoint.objects.filter(id__in=stale_ids).update(is_deleted=True, sys_modifier=instance.created_by)
    close_runtime_db_connections()
    return checkpoint


def get_checkpoint_detail(instance: AgentTask, checkpoint_id: str) -> dict:
    checkpoint_key = str(checkpoint_id or '').strip()
    persisted = instance.persisted_checkpoints.filter(id=checkpoint_key, is_deleted=False).first()
    if persisted:
        state_data = dict(persisted.state_data or {})
        metadata = dict(persisted.checkpoint_metadata or {})
        payload = serialize_persisted_checkpoint(persisted)
        return {
            **payload,
            'task_id': str(instance.id),
            'task_status': instance.status,
            'progress_percentage': instance.progress_percentage,
            'events': list(state_data.get('recent_events') or []),
            'statistics': {
                'total_files': _to_int(state_data.get('task', {}).get('total_files'), instance.total_files),
                'indexed_files': _to_int(state_data.get('summary', {}).get('statistics', {}).get('indexed_files'), instance.indexed_files),
                'analyzed_files': _to_int(state_data.get('summary', {}).get('statistics', {}).get('analyzed_files'), instance.analyzed_files),
                'findings_count': persisted.findings_count,
                'verified_count': _to_int(state_data.get('summary', {}).get('statistics', {}).get('verified_count'), instance.verified_count),
                'false_positive_count': _to_int(state_data.get('summary', {}).get('statistics', {}).get('false_positive_count'), instance.false_positive_count),
                'tool_calls_count': persisted.tool_calls,
            },
            'state_data': state_data,
            'metadata': metadata,
        }
    checkpoints = {item['id'] or item['phase']: item for item in build_phase_checkpoints(instance)}
    checkpoint = checkpoints.get(checkpoint_key)
    if not checkpoint:
        raise HttpError(404, '检查点不存在')
    phase_events = instance.events.filter(is_deleted=False, phase=checkpoint['phase']).order_by('sequence')[:50]
    return {
        **checkpoint,
        'task_id': str(instance.id),
        'task_status': instance.status,
        'progress_percentage': instance.progress_percentage,
        'events': [
            {
                'sequence': event.sequence,
                'event_type': event.event_type,
                'message': event.message,
                'timestamp': format_datetime_text(event.sys_create_datetime),
                'tool_name': event.tool_name,
                'progress_percent': event.progress_percent,
            }
            for event in phase_events
        ],
        'statistics': {
            'total_files': instance.total_files,
            'indexed_files': instance.indexed_files,
            'analyzed_files': instance.analyzed_files,
            'findings_count': instance.findings_count,
            'verified_count': instance.verified_count,
            'false_positive_count': instance.false_positive_count,
            'tool_calls_count': instance.tool_calls_count,
        },
        'state_data': {},
        'metadata': {},
    }


def _normalize_tree_status(value: str | None, *, default: str = 'running') -> str:
    status = str(value or '').strip().lower()
    if status in {'completed', 'running', 'failed', 'waiting', 'created'}:
        return status
    if status in {'cancelled', 'stopped', 'stopping'}:
        return 'failed'
    return default


def _merge_tree_status(current: str, incoming: str) -> str:
    priority = {
        'created': 1,
        'waiting': 2,
        'running': 3,
        'completed': 4,
        'failed': 5,
    }
    if priority.get(incoming, 0) >= priority.get(current, 0):
        return incoming
    return current


def _build_agent_tree_from_events(instance: AgentTask) -> list[dict] | None:
    events = list(instance.events.filter(is_deleted=False).order_by('sequence'))
    nodes: dict[str, dict] = {}
    has_agent_metadata = False

    for event in events:
        metadata = dict(event.event_metadata or {})
        agent_id = str(metadata.get('agent_id') or '').strip()
        if not agent_id:
            continue

        has_agent_metadata = True
        node = nodes.setdefault(
            agent_id,
            {
                'id': agent_id,
                'agent_id': agent_id,
                'agent_name': str(metadata.get('agent_name') or agent_id),
                'agent_type': str(metadata.get('agent_type') or 'orchestrator'),
                'parent_agent_id': str(metadata.get('parent_agent_id') or '').strip() or None,
                'depth': 0,
                'task_description': str(metadata.get('task') or '').strip() or None,
                'knowledge_modules': [],
                'status': 'running',
                'result_summary': None,
                'findings_count': 0,
                'iterations': 0,
                'tokens_used': 0,
                'tool_calls': 0,
                'duration_ms': None,
                'children': [],
                '_first_sequence': event.sequence,
                '_first_timestamp': event.sys_create_datetime,
                '_last_timestamp': event.sys_create_datetime,
            },
        )

        node['agent_name'] = str(metadata.get('agent_name') or node['agent_name'])
        node['agent_type'] = str(metadata.get('agent_type') or node['agent_type'])
        node['parent_agent_id'] = str(metadata.get('parent_agent_id') or node['parent_agent_id'] or '').strip() or None
        if metadata.get('task'):
            node['task_description'] = str(metadata.get('task')).strip() or node['task_description']
        if metadata.get('summary'):
            node['result_summary'] = str(metadata.get('summary')).strip() or node['result_summary']

        node['iterations'] = max(node['iterations'], _to_int(metadata.get('iteration')))
        node['tokens_used'] = max(node['tokens_used'], _to_int(metadata.get('tokens_used'), _to_int(event.tokens_used)))
        node['tool_calls'] = max(node['tool_calls'], _to_int(metadata.get('tool_calls')))
        node['findings_count'] = max(node['findings_count'], _to_int(metadata.get('findings_count')))
        if event.sys_create_datetime:
            node['_last_timestamp'] = event.sys_create_datetime

        status_hint = metadata.get('status')
        if event.event_type in {'error', 'task_error'}:
            status_hint = 'failed'
        elif event.event_type in {'task_complete'}:
            status_hint = 'completed'
        node['status'] = _merge_tree_status(
            node['status'],
            _normalize_tree_status(status_hint, default=node['status']),
        )

    if not has_agent_metadata:
        return None

    def resolve_depth(agent_id: str, stack: set[str] | None = None) -> int:
        node = nodes[agent_id]
        parent_id = node.get('parent_agent_id')
        if not parent_id or parent_id not in nodes:
            return 0
        active_stack = stack or set()
        if agent_id in active_stack:
            return 0
        active_stack.add(agent_id)
        depth = resolve_depth(parent_id, active_stack) + 1
        active_stack.remove(agent_id)
        return depth

    for node in nodes.values():
        node['depth'] = resolve_depth(node['agent_id'])
        first_timestamp = node.pop('_first_timestamp', None)
        last_timestamp = node.pop('_last_timestamp', None)
        node.pop('_first_sequence', None)
        if first_timestamp and last_timestamp:
            node['duration_ms'] = max(int((last_timestamp - first_timestamp).total_seconds() * 1000), 0)

    ordered_nodes = sorted(
        nodes.values(),
        key=lambda item: (item['depth'], item['parent_agent_id'] or '', item['agent_name']),
    )
    for node in ordered_nodes:
        if not node.get('parent_agent_id'):
            node['findings_count'] = max(node['findings_count'], instance.findings_count)
    return ordered_nodes


def _build_phase_fallback_tree(instance: AgentTask) -> list[dict]:
    root_id = f'{instance.id}:orchestrator'
    nodes = [
        {
            'id': root_id,
            'agent_id': root_id,
            'agent_name': 'Orchestrator',
            'agent_type': 'orchestrator',
            'parent_agent_id': None,
            'depth': 0,
            'task_description': instance.current_step,
            'knowledge_modules': [],
            'status': _normalize_tree_status(instance.status, default='running'),
            'result_summary': None,
            'findings_count': instance.findings_count,
            'iterations': instance.total_iterations,
            'tokens_used': instance.tokens_used,
            'tool_calls': instance.tool_calls_count,
            'duration_ms': _to_int((_duration_seconds(instance) or 0) * 1000),
            'children': [],
        }
    ]

    for checkpoint in build_phase_checkpoints(instance):
        if checkpoint['status'] == 'pending':
            continue
        phase = checkpoint['phase']
        phase_type = {
            AGENT_PHASE_RECONNAISSANCE: 'recon',
            AGENT_PHASE_ANALYSIS: 'analysis',
            AGENT_PHASE_VERIFICATION: 'verification',
        }.get(phase, 'orchestrator')
        nodes.append(
            {
                'id': f'{instance.id}:{phase}',
                'agent_id': f'{instance.id}:{phase}',
                'agent_name': PHASE_LABELS.get(phase, phase.title()),
                'agent_type': phase_type,
                'parent_agent_id': root_id,
                'depth': 1,
                'task_description': checkpoint['message'],
                'knowledge_modules': [],
                'status': _normalize_tree_status(checkpoint['status'], default='running'),
                'result_summary': checkpoint['message'],
                'findings_count': 0,
                'iterations': 0,
                'tokens_used': 0,
                'tool_calls': 0,
                'duration_ms': None,
                'children': [],
            }
        )

    return nodes


def build_tree(instance: AgentTask) -> list[dict]:
    return _build_agent_tree_from_events(instance) or _build_phase_fallback_tree(instance)


def export_agent_json_response(user, task_id: str) -> HttpResponse:
    instance = refresh_task_snapshot(get_task(user, task_id)) or get_task(user, task_id)
    payload = _serialize_report_payload(instance)
    artifact_path = save_json_artifact(f'agent-task-{instance.id}.json', payload)
    AuditArtifact.objects.update_or_create(
        project=instance.project,
        kind='agent_json_report',
        defaults={
            'uploaded_by': user,
            'display_name': f'agent-task-{instance.id}.json',
            'file_path': str(artifact_path),
            'mime_type': 'application/json',
            'metadata': {'task_id': str(instance.id)},
            'sys_creator': user,
            'sys_modifier': user,
            'is_deleted': False,
        },
    )
    response = HttpResponse(json.dumps(payload, ensure_ascii=False, indent=2), content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="agent-task-{instance.id}.json"'
    return response


def export_agent_markdown_response(user, task_id: str) -> HttpResponse:
    instance = refresh_task_snapshot(get_task(user, task_id)) or get_task(user, task_id)
    payload = _serialize_report_payload(instance)
    markdown = _render_agent_markdown_report(instance, payload)
    report_path = save_report_file(f'agent-task-{instance.id}.md', markdown.encode('utf-8'))
    AuditArtifact.objects.update_or_create(
        project=instance.project,
        kind='agent_markdown_report',
        defaults={
            'uploaded_by': user,
            'display_name': f'agent-task-{instance.id}.md',
            'file_path': str(report_path),
            'mime_type': 'text/markdown',
            'metadata': {'task_id': str(instance.id)},
            'sys_creator': user,
            'sys_modifier': user,
            'is_deleted': False,
        },
    )
    response = HttpResponse(markdown, content_type='text/markdown; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="agent-task-{instance.id}.md"'
    return response


def export_agent_pdf_response(user, task_id: str) -> HttpResponse:
    instance = refresh_task_snapshot(get_task(user, task_id)) or get_task(user, task_id)
    payload = _serialize_report_payload(instance)
    pdf_bytes = ReportBuilder.build_agent_report(
        payload.get('task') or serialize_task(instance),
        payload.get('findings') or [],
        instance.project.name,
    )
    report_path = save_report_file(f'agent-task-{instance.id}.pdf', pdf_bytes)
    AuditArtifact.objects.update_or_create(
        project=instance.project,
        kind='agent_pdf_report',
        defaults={
            'uploaded_by': user,
            'display_name': f'agent-task-{instance.id}.pdf',
            'file_path': str(report_path),
            'mime_type': 'application/pdf',
            'metadata': {'task_id': str(instance.id)},
            'sys_creator': user,
            'sys_modifier': user,
            'is_deleted': False,
        },
    )
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="agent-task-{instance.id}.pdf"'
    return response


def export_agent_report_response(user, task_id: str, *, format: str = 'markdown') -> HttpResponse:
    normalized_format = str(format or 'markdown').strip().lower()
    if normalized_format == 'json':
        return export_agent_json_response(user, task_id)
    if normalized_format == 'pdf':
        return export_agent_pdf_response(user, task_id)
    if normalized_format == 'markdown':
        return export_agent_markdown_response(user, task_id)
    raise HttpError(422, f'不支持的报告格式: {format}')


def create_event(
    instance: AgentTask,
    event_type: str,
    *,
    phase: str | None = None,
    message: str | None = None,
    tool_name: str | None = None,
    tool_input: dict | None = None,
    tool_output: dict | None = None,
    tool_duration_ms: int | None = None,
    progress_percent: float | None = None,
    finding: AgentFinding | None = None,
    tokens_used: int | None = None,
    metadata: dict | None = None,
) -> AgentEvent:
    current_sequence = instance.events.filter(is_deleted=False).order_by('-sequence').values_list('sequence', flat=True).first() or 0
    event = AgentEvent.objects.create(
        task=instance,
        event_type=event_type,
        phase=phase,
        message=message,
        sequence=current_sequence + 1,
        tool_name=tool_name,
        tool_input=tool_input or {},
        tool_output=tool_output or {},
        tool_duration_ms=tool_duration_ms,
        progress_percent=progress_percent,
        finding=finding,
        tokens_used=tokens_used,
        event_metadata=metadata or {},
        sys_creator=instance.created_by,
        sys_modifier=instance.created_by,
    )
    push_task_event(str(instance.id), serialize_event(event))
    refresh_task_snapshot(instance.id)
    return event


def _build_repository_event_callback(task_id: str):
    def _callback(level: str, message: str, metadata: dict | None = None) -> None:
        event_type = 'warning' if str(level or '').strip().lower() == 'warning' else 'info'

        def _emit() -> None:
            current = AgentTask.objects.select_related('created_by').filter(id=task_id, is_deleted=False).first()
            if not current:
                return
            create_event(
                current,
                event_type,
                phase=current.current_phase or AGENT_PHASE_PLANNING,
                message=message,
                metadata=metadata or {},
            )

        try:
            run_with_fresh_connection(_emit)
        except Exception as exc:
            logger.warning('DeepAudit failed to persist repository init event for agent task %s: %s', task_id, exc)

    return _callback


def execute_agent_task(task_id: str) -> None:
    """
    Celery Task 入口
    在这里重写，抛弃旧的 heurustic scan，直接使用真正的 OrchestratorAgent 执行全链路
    """
    close_runtime_db_connections()
    instance = run_with_fresh_connection(
        AgentTask.objects.select_related('project', 'created_by').filter(id=task_id).first
    )
    if not instance:
        return
    workspace = None
    try:
        initial_status = str(instance.status or '').strip().lower()
        docker_ready = docker_available()
        effective_verification = instance.verification_level
        if effective_verification in {'sandbox', 'generate_poc_only'} and not docker_ready:
            effective_verification = 'analysis_only'
        instance.status = 'running'
        instance.started_at = timezone.now()
        instance.error_message = ''
        run_with_fresh_connection(
            instance.save,
            update_fields=['status', 'started_at', 'error_message', 'sys_update_datetime'],
        )
        
        # 克隆或解压代码空间
        repository_spec, repository_snapshot_rebound = _refresh_pending_task_repository_snapshot(
            instance,
            allow_project_rebind=initial_status in REPOSITORY_REBINDABLE_STATUSES,
        )
        if instance.project.source_type == 'repository':
            repository_spec = validate_repository_spec_for_execution(repository_spec)
        repository_metadata = _build_repository_snapshot_metadata(
            repository_spec,
            task_id=str(instance.id),
            project_id=str(instance.project_id),
            project_repository_type=instance.project.repository_type,
        )
        if repository_snapshot_rebound:
            logger.info(
                'DeepAudit agent task %s detected project repository spec drift before workspace init and switched to latest project config: %s',
                instance.id,
                format_repository_spec_for_log(repository_spec),
            )
            create_event(
                instance,
                'info',
                phase=instance.current_phase or AGENT_PHASE_PLANNING,
                message='检测到项目仓库规格变化，已切换到最新配置执行',
                metadata=repository_metadata,
            )
        logger.info(
            'DeepAudit agent task %s will initialize repository workspace for project %s: %s',
            instance.id,
            instance.project_id,
            format_repository_spec_for_log(repository_spec),
        )
        logger.debug(
            'DeepAudit agent task %s execution snapshot metadata: %s',
            instance.id,
            json.dumps(repository_metadata, ensure_ascii=False, sort_keys=True),
        )
        create_event(
            instance,
            'info',
            phase=instance.current_phase or AGENT_PHASE_PLANNING,
            message='开始按任务快照准备仓库工作区',
            metadata=repository_metadata,
        )
        current_project_spec = build_effective_project_repository_spec(instance.project)
        if (
            instance.project.source_type == 'repository'
            and repository_spec_signature(current_project_spec) != repository_spec_signature(repository_spec)
        ):
            logger.warning(
                'DeepAudit agent task %s is using repository spec different from current project config: task_spec=%s current_project_spec=%s',
                instance.id,
                format_repository_spec_for_log(repository_spec),
                format_repository_spec_for_log(current_project_spec),
            )
            create_event(
                instance,
                'warning',
                phase=instance.current_phase or AGENT_PHASE_PLANNING,
                message='任务执行将使用创建时快照的仓库规格，而不是项目当前配置',
                metadata=repository_metadata,
            )

        repository_event_callback = _build_repository_event_callback(str(instance.id))
        # repository_* 只锁定任务规格；多仓执行仍需要重新同步缓存，最终工作区来源看 workspace_source。
        workspace, user_payload = prepare_repository_workspace(
            instance.project,
            repository_spec=repository_spec,
            user_id=str(instance.created_by_id),
            force_multi_sync=repository_spec['repository_type'] == 'multi',
            event_callback=repository_event_callback,
            log_context={
                'task_kind': 'agent',
                'task_id': str(instance.id),
                'user_id': str(instance.created_by_id),
            },
        )
        repository_runtime = _repository_runtime_metadata(user_payload)
        workspace_source = str(repository_runtime.get('workspace_source') or '').strip()
        if (
            normalize_repository_type(repository_spec.get('repository_type')) == 'multi'
            and not workspace_source.startswith('multi_repo_')
        ):
            message = (
                '多仓任务工作区来源异常，当前工作区不是多仓缓存/同步产物，已中止执行。'
                f' workspace_source={workspace_source or "-"}'
            )
            logger.error(
                'DeepAudit agent task %s failed due to invalid multi workspace source: %s %s',
                instance.id,
                workspace_source or '-',
                format_repository_spec_for_log(repository_spec),
            )
            instance.status = 'failed'
            instance.current_step = truncate_runtime_text('多仓工作区来源异常')
            instance.error_message = message
            instance.completed_at = timezone.now()
            run_with_fresh_connection(
                instance.save,
                update_fields=[
                    'status',
                    'current_step',
                    'error_message',
                    'completed_at',
                    'sys_update_datetime',
                ],
            )
            create_event(
                instance,
                'task_error',
                phase=instance.current_phase or AGENT_PHASE_PLANNING,
                message=message,
                metadata={**repository_metadata, **repository_runtime},
            )
            return
        validated_target_files = list(instance.target_files or [])
        if validated_target_files:
            selection_check = validate_selected_file_paths(
                workspace,
                file_paths=validated_target_files,
            )
            if selection_check['missing']:
                metadata = {
                    **repository_metadata,
                    'missing_count': len(selection_check['missing']),
                    'existing_count': len(selection_check['existing']),
                    'missing_samples': selection_check['missing'][:5],
                    'workspace': str(workspace),
                }
                if selection_check['existing']:
                    logger.warning(
                        'DeepAudit agent task %s found missing selected paths after workspace refresh and will continue with remaining paths: missing_count=%s existing_count=%s missing_samples=%s %s',
                        instance.id,
                        len(selection_check['missing']),
                        len(selection_check['existing']),
                        selection_check['missing'][:5],
                        format_repository_spec_for_log(repository_spec),
                    )
                    create_event(
                        instance,
                        'warning',
                        phase=instance.current_phase or AGENT_PHASE_PLANNING,
                        message='部分目标目录或文件在当前代码工作区中不存在，已跳过缺失项继续审计',
                        metadata=metadata,
                    )
                    validated_target_files = selection_check['existing']
                else:
                    message = (
                        f'所选目标目录或文件在当前代码工作区中均不存在，共 {len(selection_check["missing"])} 项。'
                        f' 示例: {", ".join(selection_check["missing"][:5])}'
                    )
                    logger.error(
                        'DeepAudit agent task %s failed because all selected paths are missing from workspace: %s %s',
                        instance.id,
                        message,
                        format_repository_spec_for_log(repository_spec),
                    )
                    instance.status = 'failed'
                    instance.current_step = truncate_runtime_text('目标文件不存在')
                    instance.error_message = message
                    instance.completed_at = timezone.now()
                    run_with_fresh_connection(
                        instance.save,
                        update_fields=[
                            'status',
                            'current_step',
                            'error_message',
                            'completed_at',
                            'sys_update_datetime',
                        ],
                    )
                    create_event(
                        instance,
                        'task_error',
                        phase=instance.current_phase or AGENT_PHASE_PLANNING,
                        message=message,
                        metadata=metadata,
                    )
                    return
        resolved_target_files = list(validated_target_files)
        if validated_target_files:
            resolved_target_files = resolve_selected_file_paths(
                workspace,
                exclude_patterns=instance.exclude_patterns or [],
                file_paths=validated_target_files,
                include_tests=True,
                include_docs=True,
            )
            if not resolved_target_files:
                message = '所选目标目录或文件在当前代码工作区中未命中任何可审计文本文件，请检查目录内容或排除规则。'
                logger.error(
                    'DeepAudit agent task %s failed because selected targets resolved to zero auditable files: selected_count=%s %s',
                    instance.id,
                    len(validated_target_files),
                    format_repository_spec_for_log(repository_spec),
                )
                instance.status = 'failed'
                instance.current_step = truncate_runtime_text('目标文件为空')
                instance.error_message = message
                instance.completed_at = timezone.now()
                run_with_fresh_connection(
                    instance.save,
                    update_fields=[
                        'status',
                        'current_step',
                        'error_message',
                        'completed_at',
                        'sys_update_datetime',
                    ],
                )
                create_event(
                    instance,
                    'task_error',
                    phase=instance.current_phase or AGENT_PHASE_PLANNING,
                    message=message,
                    metadata={
                        **repository_metadata,
                        'workspace': str(workspace),
                        'selected_count': len(validated_target_files),
                        'resolved_file_count': 0,
                    },
                )
                return
            if resolved_target_files != validated_target_files:
                logger.info(
                    'DeepAudit agent task %s expanded selected targets to concrete files: selected_count=%s resolved_file_count=%s %s',
                    instance.id,
                    len(validated_target_files),
                    len(resolved_target_files),
                    format_repository_spec_for_log(repository_spec),
                )
                create_event(
                    instance,
                    'info',
                    phase=instance.current_phase or AGENT_PHASE_PLANNING,
                    message='已将所选目录展开为具体文件范围',
                    metadata={
                        **repository_metadata,
                        'workspace': str(workspace),
                        'selected_count': len(validated_target_files),
                        'resolved_file_count': len(resolved_target_files),
                        'resolved_samples': resolved_target_files[:10],
                    },
                )
        selection_stats = summarize_selected_targets(
            workspace,
            file_paths=validated_target_files,
            resolved_file_paths=resolved_target_files,
        )
        selection_stats['resolved_file_count'] = len(resolved_target_files) if validated_target_files else 0
        resolved_target_prefixes = {f'{path}/' for path in resolved_target_files}
        selected_directory_samples = [
            path
            for path in validated_target_files
            if any(prefix.startswith(f'{path}/') for prefix in resolved_target_prefixes)
        ]
        selection_runtime = {
            'validated_target_files': list(validated_target_files),
            'selected_directory_count': len(selected_directory_samples),
            'selected_directory_samples': selected_directory_samples[:10],
            'resolved_target_files': list(resolved_target_files),
            'resolved_file_count': len(resolved_target_files) if validated_target_files else 0,
            'resolved_samples': resolved_target_files[:10],
        }
        logger.info(
            'DeepAudit agent task %s prepared resolved target scope before runner: selected_count=%s directory_count=%s resolved_file_count=%s directory_samples=%s resolved_samples=%s %s',
            instance.id,
            len(validated_target_files),
            len(selected_directory_samples),
            len(resolved_target_files),
            selected_directory_samples[:5],
            resolved_target_files[:5],
            format_repository_spec_for_log(repository_spec),
        )
        instance.agent_config = {
            **dict(instance.agent_config or {}),
            'selection_stats': selection_stats,
            'selection_runtime': selection_runtime,
            'repository_runtime': repository_runtime,
        }
        instance.total_files = len(resolved_target_files) if validated_target_files else instance.total_files
        run_with_fresh_connection(
            instance.save,
            update_fields=['agent_config', 'total_files', 'sys_update_datetime'],
        )

        # 准备交给 Agent 的上下文数据
        input_data = {
            "task_id": str(instance.id),
            "project_id": str(instance.project_id),
            "project_name": instance.project.name,
            "project_path": str(workspace),
            "audit_scope": instance.audit_scope or {},
            "agent_config": instance.agent_config or {},
            "target_vulnerabilities": instance.target_vulnerabilities or [],
            "verification_level": effective_verification,
            "exclude_patterns": instance.exclude_patterns or [],
            "target_files": resolved_target_files,
            "llm_config": user_payload.get("llm_config", {}),
            "other_config": user_payload.get("other_config", {}),
            "max_iterations": instance.max_iterations or 50,
        }
        
        # 桥接到真实的 LangGraph Agent 架构 (在 celery 线程中跑 async)
        from apps.deepaudit.agent_task.agent_runner import run_orchestrator_agent_sync
        run_orchestrator_agent_sync(str(instance.id), input_data, str(workspace))
        
        refresh_task_snapshot(
            str(instance.id),
            status='completed',
            current_phase=AGENT_PHASE_REPORTING,
            current_step='报告生成完成',
            completed_at=timezone.now(),
            error_message='',
        )
        
    except Exception as exc:
        refresh_task_snapshot(
            str(instance.id),
            status='failed',
            current_step=str(exc),
            completed_at=timezone.now(),
            error_message=str(exc),
        )
        raise
    finally:
        close_runtime_db_connections()
        cleanup_runtime_workspace(workspace)
