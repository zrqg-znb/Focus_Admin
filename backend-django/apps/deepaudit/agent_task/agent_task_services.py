from __future__ import annotations

import asyncio
import json
from collections import Counter

from asgiref.sync import sync_to_async
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.errors import HttpError

from apps.deepaudit.analysis_payload import get_analysis_quality_score, get_analysis_security_score
from apps.deepaudit.agent_task.agent_task_model import AgentEvent, AgentFinding, AgentTask
from apps.deepaudit.constants import (
    AGENT_PHASE_ANALYSIS,
    AGENT_PHASE_CHOICES,
    AGENT_PHASE_INDEXING,
    AGENT_PHASE_PLANNING,
    AGENT_PHASE_REPORTING,
    AGENT_PHASE_VERIFICATION,
    FINDING_STATUS_CHOICES,
)
from apps.deepaudit.permissions import require_project_role, serialize_user_brief
from apps.deepaudit.realtime import push_task_event
from apps.deepaudit.reporting import ReportBuilder
from apps.deepaudit.runtime import cleanup_runtime_workspace, docker_available, prepare_workspace, run_heuristic_scan
from apps.deepaudit.scan_task.scan_task_model import AuditArtifact
from apps.deepaudit.serialization import format_datetime_text, normalize_json_payload
from apps.deepaudit.storage import save_json_artifact, save_report_file

PHASE_LABELS = {
    AGENT_PHASE_PLANNING: 'Planning',
    AGENT_PHASE_INDEXING: 'Indexing',
    AGENT_PHASE_ANALYSIS: 'Analysis',
    AGENT_PHASE_VERIFICATION: 'Verification',
    AGENT_PHASE_REPORTING: 'Reporting',
}

VALID_FINDING_STATUSES = {value for value, _label in FINDING_STATUS_CHOICES}
ACTIVE_STATUSES = {'pending', 'initializing', 'running', 'planning', 'indexing', 'analyzing', 'verifying', 'reporting'}
TERMINAL_STATUSES = {'completed', 'failed', 'cancelled'}
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
            'accumulated',
            'agent_name',
            'current',
            'findings_count',
            'node',
            'security_score',
            'status',
            'summary',
            'token',
            'total',
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
        'branch_name': instance.branch_name,
        'exclude_patterns': list(instance.exclude_patterns or []),
        'target_files': list(instance.target_files or []),
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
    return AgentTask.objects.create(
        project=access.project,
        created_by=user,
        name=payload.get('name') or f'{access.project.name} Agent 审计',
        description=payload.get('description') or '',
        audit_scope=payload.get('audit_scope') or {},
        target_vulnerabilities=payload.get('target_vulnerabilities') or [],
        verification_level=payload.get('verification_level') or 'sandbox',
        branch_name=payload.get('branch_name') or access.project.default_branch,
        exclude_patterns=payload.get('exclude_patterns') or [],
        target_files=payload.get('target_files') or [],
        max_iterations=int(payload.get('max_iterations') or 50),
        timeout_seconds=int(payload.get('timeout_seconds') or 1800),
        status='pending',
        current_phase=AGENT_PHASE_PLANNING,
        sys_creator=user,
        sys_modifier=user,
    )


def cancel_task(user, task_id: str) -> bool:
    instance = get_task(user, task_id)
    if instance.status not in ACTIVE_STATUSES:
        return True
    instance.status = 'cancelled'
    instance.current_step = '用户已取消任务'
    instance.completed_at = timezone.now()
    instance.sys_modifier = user
    instance.save(update_fields=['status', 'current_step', 'completed_at', 'sys_modifier', 'sys_update_datetime'])
    create_event(instance, 'task_cancel', message='用户取消了 Agent 审计任务', phase=instance.current_phase)
    return True


def mark_dispatch_failed(instance: AgentTask, message: str) -> AgentTask:
    instance.status = 'failed'
    instance.current_step = '任务队列不可用'
    instance.error_message = message
    instance.completed_at = timezone.now()
    if instance.created_by_id:
        instance.sys_modifier = instance.created_by
    instance.save(update_fields=['status', 'current_step', 'error_message', 'completed_at', 'sys_modifier', 'sys_update_datetime'])
    create_event(instance, 'task_error', phase=instance.current_phase or AGENT_PHASE_PLANNING, message=message)
    return instance


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


def build_summary(instance: AgentTask) -> dict:
    findings = instance.findings.filter(is_deleted=False)
    severity_distribution = {
        'critical': findings.filter(severity='critical').count(),
        'high': findings.filter(severity='high').count(),
        'medium': findings.filter(severity='medium').count(),
        'low': findings.filter(severity='low').count(),
    }
    vulnerability_types = Counter(findings.values_list('vulnerability_type', flat=True))
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
        'vulnerability_types': dict(vulnerability_types),
        'phases_completed': phases_completed,
    }


def build_checkpoints(instance: AgentTask) -> list[dict]:
    checkpoints = []
    latest_by_phase = {}
    for event in instance.events.filter(is_deleted=False).order_by('sequence'):
        if not event.phase:
            continue
        latest_by_phase[event.phase] = event
    for phase in [choice[0] for choice in AGENT_PHASE_CHOICES]:
        event = latest_by_phase.get(phase)
        if not event:
            checkpoints.append({'phase': phase, 'status': 'pending', 'sequence': 0, 'message': None, 'timestamp': None})
            continue
        status = 'completed' if event.event_type == 'phase_complete' else 'running'
        checkpoints.append(
            {
                'phase': phase,
                'status': status,
                'sequence': event.sequence,
                'message': event.message,
                'timestamp': format_datetime_text(event.sys_create_datetime),
            }
        )
    return checkpoints


def build_tree(instance: AgentTask) -> list[dict]:
    checkpoints = {item['phase']: item for item in build_checkpoints(instance)}
    nodes = []
    for phase in [choice[0] for choice in AGENT_PHASE_CHOICES]:
        checkpoint = checkpoints[phase]
        nodes.append(
            {
                'id': f'{instance.id}:{phase}',
                'label': PHASE_LABELS.get(phase, phase.title()),
                'phase': phase,
                'status': checkpoint['status'],
                'progress': float(checkpoint['sequence'] or 0),
                'children': [],
            }
        )
    return nodes


def export_agent_json_response(user, task_id: str) -> HttpResponse:
    instance = get_task(user, task_id)
    payload = normalize_json_payload({
        'task': serialize_task(instance),
        'summary': build_summary(instance),
        'checkpoints': build_checkpoints(instance),
        'findings': list_findings(user, task_id),
        'events': list_events(user, task_id, limit=1000),
    })
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


def export_agent_pdf_response(user, task_id: str) -> HttpResponse:
    instance = get_task(user, task_id)
    findings = list_findings(user, task_id)
    pdf_bytes = ReportBuilder.build_agent_report(serialize_task(instance), findings, instance.project.name)
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
    next_sequence = (instance.events.filter(is_deleted=False).aggregate_max_sequence if False else None)
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
    return event


def execute_agent_task(task_id: str) -> None:
    """
    Celery Task 入口
    在这里重写，抛弃旧的 heurustic scan，直接使用真正的 OrchestratorAgent 执行全链路
    """
    instance = AgentTask.objects.select_related('project', 'created_by').filter(id=task_id).first()
    if not instance:
        return
    workspace = None
    try:
        docker_ready = docker_available()
        effective_verification = instance.verification_level
        if effective_verification in {'sandbox', 'generate_poc_only'} and not docker_ready:
            effective_verification = 'analysis_only'
        instance.status = 'running'
        instance.started_at = timezone.now()
        instance.error_message = ''
        instance.save(update_fields=['status', 'started_at', 'error_message', 'sys_update_datetime'])
        
        # 克隆或解压代码空间
        workspace, user_payload = prepare_workspace(instance.project, branch_name=instance.branch_name, user_id=str(instance.created_by_id))
        
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
            "target_files": instance.target_files or [],
            "llm_config": user_payload.get("llm_config", {}),
            "other_config": user_payload.get("other_config", {}),
            "max_iterations": instance.max_iterations or 50,
        }
        
        # 桥接到真实的 LangGraph Agent 架构 (在 celery 线程中跑 async)
        from apps.deepaudit.agent_task.agent_runner import run_orchestrator_agent_sync
        run_orchestrator_agent_sync(str(instance.id), input_data, str(workspace))
        
        # Agent 完成后收集 DB 数据进行计分等操作
        instance.refresh_from_db()
        findings = instance.findings.filter(is_deleted=False)
        instance.findings_count = findings.count()
        instance.critical_count = findings.filter(severity='critical').count()
        instance.high_count = findings.filter(severity='high').count()
        instance.medium_count = findings.filter(severity='medium').count()
        instance.low_count = findings.filter(severity='low').count()
        instance.status = 'completed'
        instance.completed_at = timezone.now()
        instance.save()
        
    except Exception as exc:
        instance.refresh_from_db()
        instance.status = 'failed'
        instance.error_message = str(exc)
        instance.completed_at = timezone.now()
        instance.save(update_fields=['status', 'error_message', 'completed_at', 'sys_update_datetime'])
        raise
    finally:
        cleanup_runtime_workspace(workspace)
