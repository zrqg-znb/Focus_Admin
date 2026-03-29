from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import shutil

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from ninja.errors import HttpError

from apps.deepaudit.analysis_payload import (
    get_analysis_issue_count,
    get_analysis_quality_score,
    normalize_analysis_result,
)
from apps.deepaudit.agent_task import agent_task_services
from apps.deepaudit.agent_task.agent_task_model import AgentEvent, AgentFinding, AgentTask
from apps.deepaudit.audit_rule.audit_rule_model import AuditRule, AuditRuleSet
from apps.deepaudit.audit_rule import audit_rule_services
from apps.deepaudit.constants import PROJECT_MEMBER_ROLE_ADMIN, PROJECT_MEMBER_ROLE_MEMBER, PROJECT_MEMBER_ROLE_VIEWER
from apps.deepaudit.permissions import accessible_project_queryset, get_user_id, serialize_user_brief, sync_owner_membership
from apps.deepaudit.project import project_services
from apps.deepaudit.project.project_model import AuditProject, AuditProjectMember
from apps.deepaudit.prompt_template import prompt_template_services
from apps.deepaudit.prompt_template.prompt_template_model import PromptTemplate
from apps.deepaudit.runtime import docker_available
from apps.deepaudit.scan_task import scan_task_services
from apps.deepaudit.scan_task.scan_task_model import AuditArtifact, AuditIssue, AuditTask, InstantAnalysisRecord
from apps.deepaudit.serialization import format_datetime_text, normalize_json_payload
from apps.deepaudit import storage as deepaudit_storage
from apps.deepaudit.user_config import user_config_services
from apps.deepaudit.user_config.user_config_model import AuditSshCredential, AuditUserConfig
from core.user.user_model import User


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for file_path in path.rglob('*'):
        if file_path.is_file():
            try:
                total += file_path.stat().st_size
            except OSError:
                continue
    return total


def _serialize_scan_activity(task: AuditTask) -> dict:
    return {
        'id': str(task.id),
        'task_kind': 'scan_task',
        'project_id': str(task.project_id),
        'project_name': task.project.name if task.project else '',
        'title': f'{task.project.name if task.project else "项目"} 扫描任务',
        'status': task.status,
        'issues_count': task.issues_count,
        'findings_count': 0,
        'created_by_name': serialize_user_brief(task.created_by).get('name') if task.created_by else None,
        'created_at': format_datetime_text(task.sys_create_datetime),
        'route_path': f'/deepaudit/tasks/{task.id}',
    }


def _serialize_agent_activity(task: AgentTask) -> dict:
    return {
        'id': str(task.id),
        'task_kind': 'agent_task',
        'project_id': str(task.project_id),
        'project_name': task.project.name if task.project else '',
        'title': task.name or f'{task.project.name if task.project else "项目"} Agent 审计',
        'status': task.status,
        'issues_count': 0,
        'findings_count': task.findings_count,
        'created_by_name': serialize_user_brief(task.created_by).get('name') if task.created_by else None,
        'created_at': format_datetime_text(task.sys_create_datetime),
        'route_path': f'/deepaudit/agent-audit/{task.id}',
    }


def get_dashboard_overview(user, *, limit: int = 10) -> dict:
    projects = accessible_project_queryset(user)
    scan_tasks = AuditTask.objects.filter(project__in=projects, is_deleted=False).select_related('project', 'created_by')
    agent_tasks = AgentTask.objects.filter(project__in=projects, is_deleted=False).select_related('project', 'created_by')
    issues = AuditIssue.objects.filter(task__project__in=projects, is_deleted=False)
    findings = AgentFinding.objects.filter(task__project__in=projects, is_deleted=False)

    activities = [
        *(_serialize_scan_activity(item) for item in scan_tasks.order_by('-sys_create_datetime')[:limit]),
        *(_serialize_agent_activity(item) for item in agent_tasks.order_by('-sys_create_datetime')[:limit]),
    ]
    activities.sort(key=lambda item: item.get('created_at') or '', reverse=True)

    return {
        'project_summary': {
            'total': projects.filter(is_deleted=False).count(),
            'active': projects.filter(is_deleted=False, is_active=True).count(),
            'deleted': accessible_project_queryset(user, include_deleted=True).filter(is_deleted=True).count(),
            'repository': projects.filter(source_type='repository').count(),
            'zip': projects.filter(source_type='zip').count(),
        },
        'scan_task_summary': {
            'total': scan_tasks.count(),
            'pending': scan_tasks.filter(status='pending').count(),
            'running': scan_tasks.filter(status='running').count(),
            'completed': scan_tasks.filter(status='completed').count(),
            'failed': scan_tasks.filter(status='failed').count(),
            'cancelled': scan_tasks.filter(status='cancelled').count(),
        },
        'agent_task_summary': {
            'total': agent_tasks.count(),
            'pending': agent_tasks.filter(status='pending').count(),
            'running': agent_tasks.filter(status__in=['initializing', 'running', 'planning', 'indexing', 'analyzing', 'verifying', 'reporting']).count(),
            'completed': agent_tasks.filter(status='completed').count(),
            'failed': agent_tasks.filter(status='failed').count(),
            'cancelled': agent_tasks.filter(status='cancelled').count(),
        },
        'issue_summary': {
            'total': issues.count(),
            'open': issues.filter(status='open').count(),
            'resolved': issues.filter(status='resolved').count(),
            'false_positive': issues.filter(status='false_positive').count(),
        },
        'finding_summary': {
            'total': findings.count(),
            'open': findings.filter(status='open').count(),
            'fixed': findings.filter(status='fixed').count(),
            'wont_fix': findings.filter(status='wont_fix').count(),
            'false_positive': findings.filter(status='false_positive').count(),
            'verified': findings.filter(is_verified=True).count(),
        },
        'severity_distribution': {
            'critical': issues.filter(severity='critical').count() + findings.filter(severity='critical').count(),
            'high': issues.filter(severity='high').count() + findings.filter(severity='high').count(),
            'medium': issues.filter(severity='medium').count() + findings.filter(severity='medium').count(),
            'low': issues.filter(severity='low').count() + findings.filter(severity='low').count(),
        },
        'storage_summary': {
            'zip_size': _dir_size(deepaudit_storage.ZIP_DIR),
            'report_size': _dir_size(deepaudit_storage.REPORTS_DIR),
            'artifact_size': _dir_size(deepaudit_storage.ARTIFACTS_DIR),
            'vector_db_size': _dir_size(deepaudit_storage.VECTOR_DB_DIR),
            'workspace_count': len(list(deepaudit_storage.WORKSPACE_DIR.glob('*'))) if deepaudit_storage.WORKSPACE_DIR.exists() else 0,
        },
        'recent_activities': activities[:limit],
    }


def get_health_report(user) -> dict:
    projects = accessible_project_queryset(user)
    user_id = get_user_id(user)
    docker_enabled = bool(getattr(settings, 'DEEPAUDIT_DOCKER_ENABLED', True))
    return {
        'docker_enabled': docker_enabled,
        'docker_available': docker_enabled and docker_available(),
        'queue': getattr(settings, 'DEEPAUDIT_QUEUE', 'deepaudit'),
        'storage_paths': [
            {'name': 'zip', 'path': str(deepaudit_storage.ZIP_DIR), 'exists': deepaudit_storage.ZIP_DIR.exists(), 'size_bytes': _dir_size(deepaudit_storage.ZIP_DIR)},
            {'name': 'workspaces', 'path': str(deepaudit_storage.WORKSPACE_DIR), 'exists': deepaudit_storage.WORKSPACE_DIR.exists(), 'size_bytes': _dir_size(deepaudit_storage.WORKSPACE_DIR)},
            {'name': 'reports', 'path': str(deepaudit_storage.REPORTS_DIR), 'exists': deepaudit_storage.REPORTS_DIR.exists(), 'size_bytes': _dir_size(deepaudit_storage.REPORTS_DIR)},
            {'name': 'artifacts', 'path': str(deepaudit_storage.ARTIFACTS_DIR), 'exists': deepaudit_storage.ARTIFACTS_DIR.exists(), 'size_bytes': _dir_size(deepaudit_storage.ARTIFACTS_DIR)},
            {'name': 'vector_db', 'path': str(deepaudit_storage.VECTOR_DB_DIR), 'exists': deepaudit_storage.VECTOR_DB_DIR.exists(), 'size_bytes': _dir_size(deepaudit_storage.VECTOR_DB_DIR)},
            {'name': 'knowledge', 'path': str(deepaudit_storage.KNOWLEDGE_DIR), 'exists': deepaudit_storage.KNOWLEDGE_DIR.exists(), 'size_bytes': _dir_size(deepaudit_storage.KNOWLEDGE_DIR)},
            {'name': 'ssh', 'path': str(deepaudit_storage.SSH_DIR), 'exists': deepaudit_storage.SSH_DIR.exists(), 'size_bytes': _dir_size(deepaudit_storage.SSH_DIR)},
        ],
        'counts': {
            'projects': projects.count(),
            'scan_tasks': AuditTask.objects.filter(project__in=projects, is_deleted=False).count(),
            'agent_tasks': AgentTask.objects.filter(project__in=projects, is_deleted=False).count(),
            'issues': AuditIssue.objects.filter(task__project__in=projects, is_deleted=False).count(),
            'findings': AgentFinding.objects.filter(task__project__in=projects, is_deleted=False).count(),
            'events': AgentEvent.objects.filter(task__project__in=projects, is_deleted=False).count(),
            'artifacts': AuditArtifact.objects.filter(Q(project__in=projects) | Q(task__project__in=projects), is_deleted=False).distinct().count(),
            'instant_records': InstantAnalysisRecord.objects.filter(user_id=user_id, is_deleted=False).count(),
        },
    }


def export_domain_data(user, *, project_id: str = '') -> dict:
    user_id = get_user_id(user)
    projects = accessible_project_queryset(user)
    if project_id:
        projects = projects.filter(id=project_id)

    project_list = list(projects)
    project_ids = [item.id for item in project_list]
    scan_tasks = AuditTask.objects.filter(project_id__in=project_ids, is_deleted=False).select_related('project', 'created_by')
    agent_tasks = AgentTask.objects.filter(project_id__in=project_ids, is_deleted=False).select_related('project', 'created_by')
    prompt_templates = [
        prompt_template_services.serialize_template(item)
        for item in (PromptTemplate.objects.filter(is_deleted=False).filter(Q(is_system=True) | Q(created_by_id=user_id)).distinct().order_by('-is_default', '-is_system', 'name'))
    ]
    rule_sets = [
        audit_rule_services.serialize_rule_set(item)
        for item in (AuditRuleSet.objects.filter(is_deleted=False).filter(Q(is_system=True) | Q(created_by_id=user_id)).distinct().order_by('-is_default', '-is_system', 'name'))
    ]
    instant_records = [
        scan_task_services.serialize_instant_record(item, include_code=True)
        for item in InstantAnalysisRecord.objects.filter(user_id=user_id, is_deleted=False).order_by('-sys_create_datetime')
    ]

    payload = {
        'exported_at': format_datetime_text(timezone.now()),
        'version': 'focus-deepaudit-v1',
        'projects': [project_services.serialize_project(project, include_members=True) for project in project_list],
        'scan_tasks': [scan_task_services.serialize_task(task, include_issues=True) for task in scan_tasks],
        'agent_tasks': [
            {
                'task': agent_task_services.serialize_task(task),
                'summary': agent_task_services.build_summary(task),
                'checkpoints': agent_task_services.build_phase_checkpoints(task),
                'findings': agent_task_services.list_findings(user, str(task.id)),
                'events': agent_task_services.list_events(user, str(task.id), limit=5000),
            }
            for task in agent_tasks
        ],
        'prompt_templates': prompt_templates,
        'rule_sets': rule_sets,
        'instant_records': instant_records,
        'user_config': user_config_services.get_user_config(user),
        'ssh_credential': user_config_services.get_ssh_credential(user),
    }
    return normalize_json_payload({
        'project_count': len(payload['projects']),
        'scan_task_count': len(payload['scan_tasks']),
        'agent_task_count': len(payload['agent_tasks']),
        'prompt_template_count': len(payload['prompt_templates']),
        'rule_set_count': len(payload['rule_sets']),
        'instant_record_count': len(payload['instant_records']),
        'payload': payload,
    })


def cleanup_runtime_storage(*, days: int = 1, remove_reports: bool = False) -> dict:
    threshold = timezone.now() - timedelta(days=max(days, 0))
    removed_workspaces = 0
    removed_reports = 0
    removed_files: list[str] = []

    if deepaudit_storage.WORKSPACE_DIR.exists():
        for path in deepaudit_storage.WORKSPACE_DIR.iterdir():
            try:
                modified_at = datetime.fromtimestamp(path.stat().st_mtime)
            except Exception:
                modified_at = timezone.now()
            if modified_at > threshold:
                continue
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
            removed_workspaces += 1
            removed_files.append(str(path))

    if remove_reports and deepaudit_storage.REPORTS_DIR.exists():
        for path in deepaudit_storage.REPORTS_DIR.rglob('*'):
            if not path.is_file():
                continue
            try:
                modified_at = datetime.fromtimestamp(path.stat().st_mtime)
            except Exception:
                modified_at = timezone.now()
            if modified_at > threshold:
                continue
            path.unlink(missing_ok=True)
            removed_reports += 1
            removed_files.append(str(path))

    return {
        'removed_workspaces': removed_workspaces,
        'removed_reports': removed_reports,
        'removed_files': removed_files,
    }


def _safe_remove_file(path_text: str, *, allowed_roots: tuple[Path, ...]) -> str | None:
    raw_path = str(path_text or '').strip()
    if not raw_path:
        return None
    target = Path(raw_path)
    try:
        resolved = target.resolve()
    except OSError:
        return None
    if not resolved.exists() or not resolved.is_file():
        return None

    allowed = False
    for root in allowed_roots:
        try:
            resolved.relative_to(root.resolve())
            allowed = True
            break
        except ValueError:
            continue
    if not allowed:
        return None

    resolved.unlink(missing_ok=True)
    return str(resolved)


def clear_domain_data(user) -> dict:
    user_id = get_user_id(user)
    if not user_id:
        raise HttpError(401, '未获取到当前用户')

    owned_projects = AuditProject.objects.filter(owner_id=user_id)
    project_ids = list(owned_projects.values_list('id', flat=True))
    owned_project_scope = Q(project_id__in=project_ids) | Q(task__project_id__in=project_ids)

    scan_tasks = AuditTask.objects.filter(project_id__in=project_ids)
    agent_tasks = AgentTask.objects.filter(project_id__in=project_ids)
    issues = AuditIssue.objects.filter(task__project_id__in=project_ids)
    findings = AgentFinding.objects.filter(task__project_id__in=project_ids)
    events = AgentEvent.objects.filter(task__project_id__in=project_ids)
    artifacts = AuditArtifact.objects.filter(owned_project_scope).distinct()
    instant_records = InstantAnalysisRecord.objects.filter(user_id=user_id)
    prompt_templates = PromptTemplate.objects.filter(created_by_id=user_id, is_system=False)
    rule_sets = AuditRuleSet.objects.filter(created_by_id=user_id, is_system=False)
    user_configs = AuditUserConfig.objects.filter(user_id=user_id)
    ssh_credentials = AuditSshCredential.objects.filter(user_id=user_id)
    memberships = AuditProjectMember.objects.filter(project_id__in=project_ids)

    deleted = {
        'projects': owned_projects.count(),
        'project_members': memberships.count(),
        'scan_tasks': scan_tasks.count(),
        'issues': issues.count(),
        'agent_tasks': agent_tasks.count(),
        'findings': findings.count(),
        'events': events.count(),
        'artifacts': artifacts.count(),
        'instant_records': instant_records.count(),
        'prompt_templates': prompt_templates.count(),
        'rule_sets': rule_sets.count(),
        'user_config': user_configs.count(),
        'ssh_credential': ssh_credentials.count(),
    }

    removed_files: list[str] = []
    removable_paths = {
        str(path)
        for path in artifacts.values_list('file_path', flat=True)
        if path
    }

    with transaction.atomic():
        for project_id in project_ids:
            deepaudit_storage.delete_project_zip(str(project_id))
        for path_text in removable_paths:
            removed = _safe_remove_file(
                path_text,
                allowed_roots=(deepaudit_storage.ARTIFACTS_DIR, deepaudit_storage.REPORTS_DIR, deepaudit_storage.ZIP_DIR),
            )
            if removed:
                removed_files.append(removed)

        prompt_templates.delete()
        rule_sets.delete()
        instant_records.delete()
        ssh_credentials.delete()
        user_configs.delete()
        owned_projects.delete()

    return {
        'message': '当前用户 DeepAudit 域数据已清空',
        'deleted': deleted,
        'removed_files': removed_files,
    }


def get_data_statistics(user) -> dict:
    projects = accessible_project_queryset(user)
    user_id = get_user_id(user)
    return {
        'model_counts': {
            'projects': projects.count(),
            'scan_tasks': AuditTask.objects.filter(project__in=projects, is_deleted=False).count(),
            'issues': AuditIssue.objects.filter(task__project__in=projects, is_deleted=False).count(),
            'agent_tasks': AgentTask.objects.filter(project__in=projects, is_deleted=False).count(),
            'findings': AgentFinding.objects.filter(task__project__in=projects, is_deleted=False).count(),
            'events': AgentEvent.objects.filter(task__project__in=projects, is_deleted=False).count(),
            'artifacts': AuditArtifact.objects.filter(Q(project__in=projects) | Q(task__project__in=projects), is_deleted=False).distinct().count(),
            'instant_records': InstantAnalysisRecord.objects.filter(user_id=user_id, is_deleted=False).count(),
            'prompt_templates': PromptTemplate.objects.filter(is_deleted=False).filter(Q(is_system=True) | Q(created_by_id=user_id)).distinct().count(),
            'rule_sets': AuditRuleSet.objects.filter(is_deleted=False).filter(Q(is_system=True) | Q(created_by_id=user_id)).distinct().count(),
        },
        'orphan_counts': {
            'artifacts_without_binding': AuditArtifact.objects.filter(project__isnull=True, task__isnull=True, is_deleted=False).count(),
            'findings_without_path': AgentFinding.objects.filter(task__project__in=projects, is_deleted=False, file_path__isnull=True).count(),
            'issues_without_line': AuditIssue.objects.filter(task__project__in=projects, is_deleted=False, line_number__isnull=True).count(),
        },
    }


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if not text:
            return None
        parsed = None
        for parser in (
            datetime.fromisoformat,
            lambda item: datetime.strptime(item, '%Y-%m-%d %H:%M:%S'),
        ):
            try:
                parsed = parser(text.replace('Z', '+00:00'))
                break
            except (TypeError, ValueError):
                continue
        if parsed is None:
            return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _normalize_import_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(payload or {})
    if isinstance(raw.get('payload'), dict):
        return dict(raw['payload'])
    if isinstance(raw.get('data'), dict):
        return dict(raw['data'])
    return raw


def _normalize_languages(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [item.strip() for item in value.replace(',', '\n').splitlines()]
    else:
        items = [str(item).strip() for item in value]
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not item:
            continue
        lowered = item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(item)
    return result


def _resolve_member_user(member_payload: dict[str, Any], current_user) -> User | None:
    user_id = str(member_payload.get('id') or member_payload.get('user_id') or '').strip()
    if user_id and user_id == str(current_user.id):
        return current_user
    if user_id:
        target = User.objects.filter(id=user_id).first()
        if target:
            return target
    username = str(member_payload.get('username') or '').strip()
    if username:
        target = User.objects.filter(username=username).first()
        if target:
            return target
    return None


def _import_members_for_project(project: AuditProject, members: list[dict[str, Any]], current_user, imported: dict[str, int], skipped: dict[str, int], warnings: list[str]) -> None:
    for member_payload in members:
        if not isinstance(member_payload, dict):
            skipped['project_members'] += 1
            continue
        target_user = _resolve_member_user(member_payload, current_user)
        if not target_user:
            skipped['project_members'] += 1
            warnings.append(f'项目 {project.name} 的成员 {member_payload.get("username") or member_payload.get("id") or "unknown"} 未在 Focus 用户表中找到，已跳过。')
            continue
        if str(target_user.id) == str(project.owner_id):
            sync_owner_membership(project, current_user)
            continue
        role = str(member_payload.get('role') or PROJECT_MEMBER_ROLE_MEMBER).strip().lower()
        if role not in {PROJECT_MEMBER_ROLE_ADMIN, PROJECT_MEMBER_ROLE_MEMBER, PROJECT_MEMBER_ROLE_VIEWER}:
            role = PROJECT_MEMBER_ROLE_MEMBER
        member, created = AuditProjectMember.objects.get_or_create(
            project=project,
            user=target_user,
            defaults={
                'role': role,
                'permissions': member_payload.get('permissions') or {},
                'sys_creator': current_user,
                'sys_modifier': current_user,
            },
        )
        if not created:
            member.role = role
            member.permissions = member_payload.get('permissions') or member.permissions or {}
            member.is_deleted = False
            member.sys_modifier = current_user
            member.save(update_fields=['role', 'permissions', 'is_deleted', 'sys_modifier', 'sys_update_datetime'])
        imported['project_members'] += 1


def _upsert_project(item: dict[str, Any], current_user, imported: dict[str, int], skipped: dict[str, int], warnings: list[str]) -> AuditProject | None:
    project_id = str(item.get('id') or '').strip()
    if not project_id:
        skipped['projects'] += 1
        return None
    project = AuditProject.objects.filter(id=project_id).first()
    if project and str(project.owner_id) != str(current_user.id) and not getattr(current_user, 'is_superuser', False):
        skipped['projects'] += 1
        warnings.append(f'项目 {item.get("name") or project_id} 已存在但不属于当前用户，已跳过。')
        return None
    payload = {
        'name': str(item.get('name') or '导入项目').strip() or '导入项目',
        'description': str(item.get('description') or '').strip() or None,
        'source_type': str(item.get('source_type') or 'repository').strip() or 'repository',
        'repository_url': str(item.get('repository_url') or '').strip() or None,
        'repository_type': str(item.get('repository_type') or 'other').strip() or 'other',
        'default_branch': str(item.get('default_branch') or 'main').strip() or 'main',
        'programming_languages': _normalize_languages(item.get('programming_languages')),
        'is_active': bool(item.get('is_active', True)),
    }
    if not project:
        project = AuditProject.objects.create(
            id=project_id,
            owner=current_user,
            sys_creator=current_user,
            sys_modifier=current_user,
            **payload,
        )
    else:
        for field, value in payload.items():
            setattr(project, field, value)
        project.owner = current_user
        project.is_deleted = False
        project.sys_modifier = current_user
        project.save()
    sync_owner_membership(project, current_user)
    imported['projects'] += 1
    return project


def _upsert_scan_task(task_payload: dict[str, Any], project: AuditProject, current_user) -> AuditTask:
    task_id = str(task_payload.get('id') or '').strip()
    summary_payload = dict(task_payload.get('summary') or {})
    defaults = {
        'project': project,
        'created_by': current_user,
        'sys_creator': current_user,
        'sys_modifier': current_user,
    }
    task, created = AuditTask.objects.get_or_create(id=task_id, defaults=defaults) if task_id else (AuditTask(**defaults), True)
    task.project = project
    task.created_by = current_user
    task.task_type = str(task_payload.get('task_type') or 'repository').strip() or 'repository'
    task.status = str(task_payload.get('status') or 'pending').strip() or 'pending'
    task.branch_name = str(task_payload.get('branch_name') or '').strip() or None
    task.exclude_patterns = list(task_payload.get('exclude_patterns') or [])
    task.scan_config = dict(task_payload.get('scan_config') or {})
    task.total_files = int(task_payload.get('total_files') or 0)
    task.scanned_files = int(task_payload.get('scanned_files') or 0)
    task.total_lines = int(task_payload.get('total_lines') or 0)
    task.issues_count = int(task_payload.get('issues_count') or summary_payload.get('total_issues') or 0)
    task.quality_score = float(task_payload.get('quality_score') or summary_payload.get('quality_score') or 0.0)
    task.started_at = _parse_datetime(task_payload.get('started_at'))
    task.completed_at = _parse_datetime(task_payload.get('completed_at'))
    task.error_message = str(task_payload.get('error_message') or '').strip() or None
    task.is_deleted = False
    task.sys_modifier = current_user
    if created and task_id:
        task.id = task_id
    task.save()
    return task


def _upsert_issue(issue_payload: dict[str, Any], task: AuditTask, current_user) -> AuditIssue:
    issue_id = str(issue_payload.get('id') or '').strip()
    defaults = {
        'task': task,
        'sys_creator': current_user,
        'sys_modifier': current_user,
    }
    issue, created = AuditIssue.objects.get_or_create(id=issue_id, defaults=defaults) if issue_id else (AuditIssue(**defaults), True)
    issue.task = task
    issue.file_path = str(issue_payload.get('file_path') or '').strip() or '-'
    issue.line_number = issue_payload.get('line_number')
    issue.column_number = issue_payload.get('column_number')
    issue.issue_type = str(issue_payload.get('issue_type') or 'security').strip() or 'security'
    issue.severity = str(issue_payload.get('severity') or 'medium').strip() or 'medium'
    issue.title = str(issue_payload.get('title') or '导入问题').strip() or '导入问题'
    issue.message = str(issue_payload.get('message') or issue.title).strip() or issue.title
    issue.description = str(issue_payload.get('description') or '').strip() or None
    issue.suggestion = str(issue_payload.get('suggestion') or '').strip() or None
    issue.code_snippet = issue_payload.get('code_snippet') or None
    issue.ai_explanation = dict(issue_payload.get('ai_explanation') or {})
    issue.status = str(issue_payload.get('status') or 'open').strip() or 'open'
    issue.resolved_at = _parse_datetime(issue_payload.get('resolved_at'))
    issue.resolved_by = current_user if issue.resolved_at else None
    issue.is_deleted = False
    issue.sys_modifier = current_user
    if created and issue_id:
        issue.id = issue_id
    issue.save()
    return issue


def _upsert_agent_task(task_payload: dict[str, Any], project: AuditProject, current_user, summary_payload: dict[str, Any] | None = None) -> AgentTask:
    task_id = str(task_payload.get('id') or '').strip()
    summary_payload = dict(summary_payload or {})
    severity_distribution = dict(summary_payload.get('severity_distribution') or {})
    defaults = {
        'project': project,
        'created_by': current_user,
        'sys_creator': current_user,
        'sys_modifier': current_user,
    }
    task, created = AgentTask.objects.get_or_create(id=task_id, defaults=defaults) if task_id else (AgentTask(**defaults), True)
    task.project = project
    task.created_by = current_user
    task.name = str(task_payload.get('name') or '').strip() or None
    task.description = str(task_payload.get('description') or '').strip() or None
    task.task_type = str(task_payload.get('task_type') or 'agent_audit').strip() or 'agent_audit'
    task.audit_scope = dict(task_payload.get('audit_scope') or {})
    task.target_vulnerabilities = list(task_payload.get('target_vulnerabilities') or [])
    task.verification_level = str(task_payload.get('verification_level') or 'sandbox').strip() or 'sandbox'
    task.branch_name = str(task_payload.get('branch_name') or '').strip() or None
    task.exclude_patterns = list(task_payload.get('exclude_patterns') or [])
    task.target_files = list(task_payload.get('target_files') or [])
    task.max_iterations = int(task_payload.get('max_iterations') or 50)
    task.timeout_seconds = int(task_payload.get('timeout_seconds') or 1800)
    task.status = str(task_payload.get('status') or 'pending').strip() or 'pending'
    task.current_phase = str(task_payload.get('current_phase') or '').strip() or None
    task.current_step = str(task_payload.get('current_step') or '').strip() or None
    task.error_message = str(task_payload.get('error_message') or '').strip() or None
    task.total_files = int(task_payload.get('total_files') or 0)
    task.indexed_files = int(task_payload.get('indexed_files') or 0)
    task.analyzed_files = int(task_payload.get('analyzed_files') or 0)
    task.files_with_findings = int(task_payload.get('files_with_findings') or 0)
    task.total_chunks = int(task_payload.get('total_chunks') or 0)
    task.total_iterations = int(task_payload.get('total_iterations') or 0)
    task.tool_calls_count = int(task_payload.get('tool_calls_count') or 0)
    task.tokens_used = int(task_payload.get('tokens_used') or 0)
    task.findings_count = int(task_payload.get('findings_count') or 0)
    task.verified_count = int(task_payload.get('verified_count') or 0)
    task.false_positive_count = int(task_payload.get('false_positive_count') or 0)
    task.critical_count = int(task_payload.get('critical_count') or severity_distribution.get('critical') or 0)
    task.high_count = int(task_payload.get('high_count') or severity_distribution.get('high') or 0)
    task.medium_count = int(task_payload.get('medium_count') or severity_distribution.get('medium') or 0)
    task.low_count = int(task_payload.get('low_count') or severity_distribution.get('low') or 0)
    task.quality_score = float(task_payload.get('quality_score') or summary_payload.get('quality_score') or 0.0)
    task.security_score = float(task_payload.get('security_score') or summary_payload.get('security_score') or 0.0)
    task.audit_plan = list(task_payload.get('audit_plan') or [])
    task.started_at = _parse_datetime(task_payload.get('started_at'))
    task.completed_at = _parse_datetime(task_payload.get('completed_at'))
    task.is_deleted = False
    task.sys_modifier = current_user
    if created and task_id:
        task.id = task_id
    task.save()
    return task


def _upsert_finding(finding_payload: dict[str, Any], task: AgentTask, current_user) -> AgentFinding:
    finding_id = str(finding_payload.get('id') or '').strip()
    defaults = {
        'task': task,
        'sys_creator': current_user,
        'sys_modifier': current_user,
    }
    finding, created = AgentFinding.objects.get_or_create(id=finding_id, defaults=defaults) if finding_id else (AgentFinding(**defaults), True)
    finding.task = task
    finding.vulnerability_type = str(finding_payload.get('vulnerability_type') or 'security').strip() or 'security'
    finding.severity = str(finding_payload.get('severity') or 'medium').strip() or 'medium'
    finding.title = str(finding_payload.get('title') or '导入发现').strip() or '导入发现'
    finding.description = str(finding_payload.get('description') or '').strip() or None
    finding.file_path = str(finding_payload.get('file_path') or '').strip() or None
    finding.line_start = finding_payload.get('line_start')
    finding.line_end = finding_payload.get('line_end')
    finding.code_snippet = finding_payload.get('code_snippet') or None
    finding.is_verified = bool(finding_payload.get('is_verified', False))
    finding.ai_confidence = float(finding_payload.get('ai_confidence') or 0.0)
    finding.status = str(finding_payload.get('status') or 'open').strip() or 'open'
    finding.suggestion = str(finding_payload.get('suggestion') or '').strip() or None
    finding.poc = dict(finding_payload.get('poc') or {})
    finding.is_deleted = False
    finding.sys_modifier = current_user
    if created and finding_id:
        finding.id = finding_id
    finding.save()
    return finding


def _upsert_event(event_payload: dict[str, Any], task: AgentTask, current_user, finding_lookup: dict[str, AgentFinding]) -> AgentEvent:
    event_id = str(event_payload.get('id') or '').strip()
    defaults = {
        'task': task,
        'sys_creator': current_user,
        'sys_modifier': current_user,
    }
    event, created = AgentEvent.objects.get_or_create(id=event_id, defaults=defaults) if event_id else (AgentEvent(**defaults), True)
    event.task = task
    event.event_type = str(event_payload.get('event_type') or 'info').strip() or 'info'
    event.phase = str(event_payload.get('phase') or '').strip() or None
    event.message = str(event_payload.get('message') or '').strip() or None
    event.sequence = int(event_payload.get('sequence') or 0)
    event.tool_name = str(event_payload.get('tool_name') or '').strip() or None
    event.tool_input = dict(event_payload.get('tool_input') or {})
    event.tool_output = dict(event_payload.get('tool_output') or {})
    event.tool_duration_ms = event_payload.get('tool_duration_ms')
    event.progress_percent = event_payload.get('progress_percent')
    event.tokens_used = event_payload.get('tokens_used')
    event.event_metadata = dict(event_payload.get('event_metadata') or {})
    event.finding = finding_lookup.get(str(event_payload.get('finding_id') or '').strip())
    event.is_deleted = False
    event.sys_modifier = current_user
    if created and event_id:
        event.id = event_id
    event.save()
    return event


def _upsert_prompt_template(item: dict[str, Any], current_user, imported: dict[str, int], skipped: dict[str, int], warnings: list[str]) -> None:
    template_id = str(item.get('id') or '').strip()
    template = PromptTemplate.objects.filter(id=template_id).first() if template_id else None
    if template and template.is_system and str(template.created_by_id or '') != str(current_user.id):
        skipped['prompt_templates'] += 1
        return
    if not template:
        template = PromptTemplate(created_by=current_user, sys_creator=current_user, sys_modifier=current_user)
        if template_id:
            template.id = template_id
    template.name = str(item.get('name') or '导入提示词').strip() or '导入提示词'
    template.description = str(item.get('description') or '').strip() or None
    template.template_type = str(item.get('template_type') or 'system').strip() or 'system'
    template.content_zh = item.get('content_zh') or None
    template.content_en = item.get('content_en') or None
    template.variables = dict(item.get('variables') or {})
    template.is_default = bool(item.get('is_default', False))
    template.is_system = False
    template.is_active = bool(item.get('is_active', True))
    template.created_by = current_user
    template.is_deleted = False
    template.sys_modifier = current_user
    template.save()
    imported['prompt_templates'] += 1


def _upsert_rule_set(item: dict[str, Any], current_user, imported: dict[str, int], skipped: dict[str, int], warnings: list[str]) -> None:
    rule_set_id = str(item.get('id') or '').strip()
    rule_set = AuditRuleSet.objects.filter(id=rule_set_id).first() if rule_set_id else None
    if rule_set and rule_set.is_system and str(rule_set.created_by_id or '') != str(current_user.id):
        skipped['rule_sets'] += 1
        return
    if not rule_set:
        rule_set = AuditRuleSet(created_by=current_user, sys_creator=current_user, sys_modifier=current_user)
        if rule_set_id:
            rule_set.id = rule_set_id
    rule_set.name = str(item.get('name') or '导入规则集').strip() or '导入规则集'
    rule_set.description = str(item.get('description') or '').strip() or None
    rule_set.language = str(item.get('language') or 'all').strip() or 'all'
    rule_set.rule_type = str(item.get('rule_type') or 'custom').strip() or 'custom'
    rule_set.severity_weights = dict(item.get('severity_weights') or {})
    rule_set.is_default = bool(item.get('is_default', False))
    rule_set.is_system = False
    rule_set.is_active = bool(item.get('is_active', True))
    rule_set.created_by = current_user
    rule_set.is_deleted = False
    rule_set.sys_modifier = current_user
    rule_set.save()
    imported['rule_sets'] += 1

    for rule_item in item.get('rules') or []:
        if not isinstance(rule_item, dict):
            skipped['rules'] += 1
            continue
        rule_code = str(rule_item.get('rule_code') or '').strip()
        rule_id = str(rule_item.get('id') or '').strip()
        rule = AuditRule.objects.filter(id=rule_id).first() if rule_id else None
        if not rule and rule_code:
            rule = rule_set.rules.filter(rule_code=rule_code).first()
        if not rule:
            rule = AuditRule(rule_set=rule_set, sys_creator=current_user, sys_modifier=current_user)
            if rule_id:
                rule.id = rule_id
        rule.rule_set = rule_set
        rule.rule_code = rule_code or f'IMPORTED_{timezone.now().timestamp()}'
        rule.name = str(rule_item.get('name') or rule.rule_code).strip() or rule.rule_code
        rule.description = str(rule_item.get('description') or '').strip() or None
        rule.category = str(rule_item.get('category') or 'security').strip() or 'security'
        rule.severity = str(rule_item.get('severity') or 'medium').strip() or 'medium'
        rule.custom_prompt = str(rule_item.get('custom_prompt') or '').strip() or None
        rule.fix_suggestion = str(rule_item.get('fix_suggestion') or '').strip() or None
        rule.reference_url = str(rule_item.get('reference_url') or '').strip() or None
        rule.enabled = bool(rule_item.get('enabled', True))
        rule.is_deleted = False
        rule.sys_modifier = current_user
        rule.save()
        imported['rules'] += 1


def _upsert_instant_record(item: dict[str, Any], current_user) -> InstantAnalysisRecord:
    record_id = str(item.get('id') or '').strip()
    analysis_result = normalize_analysis_result(item.get('analysis_result') or {})
    defaults = {
        'user': current_user,
        'sys_creator': current_user,
        'sys_modifier': current_user,
    }
    record, created = InstantAnalysisRecord.objects.get_or_create(id=record_id, defaults=defaults) if record_id else (InstantAnalysisRecord(**defaults), True)
    record.user = current_user
    record.language = str(item.get('language') or 'text').strip() or 'text'
    record.code_content = str(item.get('code_content') or '')
    record.analysis_result = analysis_result
    record.issues_count = int(item.get('issues_count') or get_analysis_issue_count(analysis_result))
    record.quality_score = float(item.get('quality_score') or get_analysis_quality_score(analysis_result))
    record.analysis_time = float(item.get('analysis_time') or 0.0)
    record.is_deleted = False
    record.sys_modifier = current_user
    if created and record_id:
        record.id = record_id
    record.save()
    return record


def import_domain_data(user, payload: dict[str, Any] | None) -> dict:
    data = _normalize_import_payload(payload)
    if not data:
        raise HttpError(400, '导入数据为空或结构不合法')

    imported = {
        'projects': 0,
        'project_members': 0,
        'scan_tasks': 0,
        'issues': 0,
        'agent_tasks': 0,
        'findings': 0,
        'events': 0,
        'prompt_templates': 0,
        'rule_sets': 0,
        'rules': 0,
        'instant_records': 0,
        'user_config': 0,
        'ssh_credential': 0,
    }
    skipped = {key: 0 for key in imported}
    warnings: list[str] = []

    with transaction.atomic():
        project_map: dict[str, AuditProject] = {}
        for item in data.get('projects') or []:
            if not isinstance(item, dict):
                skipped['projects'] += 1
                continue
            project = _upsert_project(item, user, imported, skipped, warnings)
            if not project:
                continue
            project_map[str(project.id)] = project
            _import_members_for_project(project, item.get('members') or [], user, imported, skipped, warnings)

        for member_payload in data.get('project_members') or []:
            if not isinstance(member_payload, dict):
                skipped['project_members'] += 1
                continue
            project_id = str(member_payload.get('project_id') or '').strip()
            project = project_map.get(project_id) or AuditProject.objects.filter(id=project_id).first()
            if not project:
                skipped['project_members'] += 1
                continue
            _import_members_for_project(project, [member_payload], user, imported, skipped, warnings)

        for item in data.get('prompt_templates') or data.get('prompts') or []:
            if not isinstance(item, dict):
                skipped['prompt_templates'] += 1
                continue
            _upsert_prompt_template(item, user, imported, skipped, warnings)

        for item in data.get('rule_sets') or []:
            if not isinstance(item, dict):
                skipped['rule_sets'] += 1
                continue
            _upsert_rule_set(item, user, imported, skipped, warnings)

        if isinstance(data.get('user_config'), dict) and data.get('user_config'):
            user_config_services.update_user_config(user, data['user_config'])
            imported['user_config'] = 1

        ssh_payload = data.get('ssh_credential') or data.get('ssh')
        if isinstance(ssh_payload, dict) and ssh_payload:
            user_config_services.save_ssh_credential(
                user,
                {
                    'private_key': ssh_payload.get('private_key') or '',
                    'public_key': ssh_payload.get('public_key') or '',
                    'known_hosts': ssh_payload.get('known_hosts') or '',
                },
            )
            imported['ssh_credential'] = 1

        for item in data.get('instant_records') or data.get('instant_analyses') or []:
            if not isinstance(item, dict):
                skipped['instant_records'] += 1
                continue
            _upsert_instant_record(item, user)
            imported['instant_records'] += 1

        separate_issue_map: dict[str, list[dict[str, Any]]] = {}
        for issue_item in data.get('issues') or []:
            if not isinstance(issue_item, dict):
                skipped['issues'] += 1
                continue
            separate_issue_map.setdefault(str(issue_item.get('task_id') or ''), []).append(issue_item)

        task_map: dict[str, AuditTask] = {}
        for item in data.get('scan_tasks') or data.get('tasks') or []:
            if not isinstance(item, dict):
                skipped['scan_tasks'] += 1
                continue
            task_payload = item.get('task') if isinstance(item.get('task'), dict) else item
            project_id = str(task_payload.get('project_id') or '').strip()
            project = project_map.get(project_id) or AuditProject.objects.filter(id=project_id).first()
            if not project:
                skipped['scan_tasks'] += 1
                warnings.append(f'扫描任务 {task_payload.get("id") or "unknown"} 缺少可用项目，已跳过。')
                continue
            task = _upsert_scan_task(task_payload, project, user)
            task_map[str(task.id)] = task
            imported['scan_tasks'] += 1
            issues = task_payload.get('issues') or item.get('issues') or separate_issue_map.get(str(task.id), [])
            for issue_payload in issues:
                if not isinstance(issue_payload, dict):
                    skipped['issues'] += 1
                    continue
                _upsert_issue(issue_payload, task, user)
                imported['issues'] += 1

        for task_id, issues in separate_issue_map.items():
            if task_id in task_map:
                continue
            task = AuditTask.objects.filter(id=task_id).first()
            if not task:
                continue
            for issue_payload in issues:
                if not isinstance(issue_payload, dict):
                    skipped['issues'] += 1
                    continue
                _upsert_issue(issue_payload, task, user)
                imported['issues'] += 1

        for item in data.get('agent_tasks') or []:
            if not isinstance(item, dict):
                skipped['agent_tasks'] += 1
                continue
            task_payload = item.get('task') if isinstance(item.get('task'), dict) else item
            summary_payload = item.get('summary') if isinstance(item.get('summary'), dict) else None
            project_id = str(task_payload.get('project_id') or '').strip()
            project = project_map.get(project_id) or AuditProject.objects.filter(id=project_id).first()
            if not project:
                skipped['agent_tasks'] += 1
                warnings.append(f'Agent 任务 {task_payload.get("id") or "unknown"} 缺少可用项目，已跳过。')
                continue
            task = _upsert_agent_task(task_payload, project, user, summary_payload=summary_payload)
            imported['agent_tasks'] += 1
            finding_lookup: dict[str, AgentFinding] = {}
            for finding_payload in item.get('findings') or []:
                if not isinstance(finding_payload, dict):
                    skipped['findings'] += 1
                    continue
                finding = _upsert_finding(finding_payload, task, user)
                finding_lookup[str(finding.id)] = finding
                imported['findings'] += 1
            for event_payload in item.get('events') or []:
                if not isinstance(event_payload, dict):
                    skipped['events'] += 1
                    continue
                _upsert_event(event_payload, task, user, finding_lookup)
                imported['events'] += 1

    return {
        'message': 'DeepAudit 域数据导入完成',
        'imported': imported,
        'skipped': skipped,
        'warnings': warnings,
    }
