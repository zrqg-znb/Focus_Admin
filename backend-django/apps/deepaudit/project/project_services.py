from __future__ import annotations

from pathlib import Path

from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError

from apps.deepaudit.constants import PROJECT_MEMBER_ROLE_OWNER
from apps.deepaudit.git_service import (
    GitServiceError,
    ensure_repository_cache,
    list_remote_branches,
    list_repository_files,
    repository_cache_enabled,
)
from apps.deepaudit.heuristics import should_exclude
from apps.deepaudit.permissions import (
    accessible_project_queryset,
    require_project_member_manage,
    require_project_role,
    serialize_member,
    serialize_user_brief,
    sync_owner_membership,
    visible_member_roles,
)
from apps.deepaudit.agent_task.agent_task_model import AgentFinding, AgentTask
from apps.deepaudit.project.project_model import AuditProject, AuditProjectMember
from apps.deepaudit.repo_specs import build_effective_project_repository_spec, build_repository_spec, normalize_repository_type
from apps.deepaudit.runtime import (
    cleanup_runtime_workspace,
    load_ssh_private_key,
    load_user_config_payload,
    prepare_workspace,
)
from apps.deepaudit.scan_task.scan_task_model import AuditArtifact, AuditIssue, AuditTask
from apps.deepaudit.serialization import format_datetime_text
from apps.deepaudit.storage import delete_project_repo_cache, delete_project_zip, get_project_zip, save_project_zip
from core.user.user_model import User


def _normalize_languages(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_values = value.replace(',', '\n').splitlines()
    else:
        raw_values = value
    items: list[str] = []
    seen: set[str] = set()
    for item in raw_values:
        text = str(item or '').strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        items.append(text)
    return items


def _resolve_project_repository_spec(project: AuditProject | None, payload: dict) -> dict[str, str]:
    repository_url = payload.get('repository_url') if 'repository_url' in payload else getattr(project, 'repository_url', '')
    repository_type = payload.get('repository_type') if 'repository_type' in payload else getattr(project, 'repository_type', 'single')
    default_branch = payload.get('default_branch') if 'default_branch' in payload else getattr(project, 'default_branch', 'main')
    manifest_xml = payload.get('manifest_xml') if 'manifest_xml' in payload else getattr(project, 'manifest_xml', '')
    group = payload.get('group') if 'group' in payload else getattr(project, 'group', '')
    repo_type = normalize_repository_type(repository_type)
    branch_text = str(default_branch or '').strip()
    manifest_text = str(manifest_xml or '').strip()
    if repo_type == 'multi':
        if not branch_text:
            raise HttpError(422, '多仓项目必须填写 default_branch')
        if not manifest_text:
            raise HttpError(422, '多仓项目必须填写 manifest_xml')
    spec = build_repository_spec(
        repository_url,
        default_branch,
        repository_type=repo_type,
        manifest_xml=manifest_xml,
        group=group,
    )
    return spec


def _project_zip_meta(project: AuditProject) -> dict:
    artifact = project.artifacts.filter(kind='project_zip', is_deleted=False).order_by('-sys_create_datetime').first()
    zip_path = get_project_zip(project.id)
    if not artifact and not zip_path:
        return {'has_file': False}
    path = Path(artifact.file_path) if artifact and artifact.file_path else zip_path
    return {
        'has_file': bool(path and path.exists()),
        'display_name': artifact.display_name if artifact else (path.name if path else None),
        'file_path': str(path) if path else None,
        'size': path.stat().st_size if path and path.exists() else None,
        'uploaded_at': format_datetime_text(artifact.sys_create_datetime) if artifact else None,
    }


def _project_task_summary(project: AuditProject) -> dict:
    scan_tasks = project.tasks.filter(is_deleted=False)
    agent_tasks = project.agent_tasks.filter(is_deleted=False)
    return {
        'scan_task_count': scan_tasks.count(),
        'active_scan_task_count': scan_tasks.filter(status__in=['pending', 'running']).count(),
        'agent_task_count': agent_tasks.count(),
        'active_agent_task_count': agent_tasks.filter(
            status__in=['pending', 'initializing', 'running', 'planning', 'indexing', 'analyzing', 'verifying', 'reporting']
        ).count(),
        'findings_count': agent_tasks.aggregate(total=Count('findings'))['total'] or 0,
        'open_issue_count': AuditIssue.objects.filter(task__project=project, is_deleted=False, status='open').count(),
    }


def _invalidate_project_repo_cache(project_id: str) -> None:
    delete_project_repo_cache(str(project_id))


def serialize_project(project: AuditProject, current_role: str = 'viewer', include_members: bool = False) -> dict:
    payload = {
        'id': str(project.id),
        'name': project.name,
        'description': project.description,
        'source_type': project.source_type,
        'repository_url': project.repository_url,
        'repository_type': normalize_repository_type(project.repository_type),
        'default_branch': project.default_branch,
        'manifest_xml': project.manifest_xml,
        'group': project.group,
        'programming_languages': list(project.programming_languages or []),
        'owner': serialize_user_brief(project.owner),
        'current_role': current_role,
        'is_active': project.is_active,
        'is_deleted': project.is_deleted,
        'members_count': project.members.filter(is_deleted=False).count(),
        'latest_task_at': format_datetime_text(project.tasks.filter(is_deleted=False).aggregate(value=Max('sys_create_datetime'))['value']),
        'latest_agent_task_at': format_datetime_text(project.agent_tasks.filter(is_deleted=False).aggregate(value=Max('sys_create_datetime'))['value']),
        'sys_create_datetime': format_datetime_text(project.sys_create_datetime),
        'sys_update_datetime': format_datetime_text(project.sys_update_datetime),
    }
    if include_members:
        payload['members'] = [
            serialize_member(member)
            for member in project.members.filter(is_deleted=False).select_related('user').order_by('role', 'sys_create_datetime')
        ]
        payload['task_summary'] = _project_task_summary(project)
        payload['zip_meta'] = _project_zip_meta(project)
    return payload


def get_project_stats(user) -> dict:
    projects = accessible_project_queryset(user, include_deleted=True)
    active_projects = projects.filter(is_deleted=False, is_active=True)
    scan_tasks = AuditTask.objects.filter(project__in=projects, is_deleted=False)
    agent_tasks = AgentTask.objects.filter(project__in=projects, is_deleted=False)
    quality_scores = list(
        scan_tasks.filter(status='completed', quality_score__gt=0).values_list('quality_score', flat=True)
    ) + list(
        agent_tasks.filter(status='completed', quality_score__gt=0).values_list('quality_score', flat=True)
    )
    avg_quality_score = round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else 0.0
    resolved_finding_statuses = {'fixed', 'wont_fix', 'false_positive', 'resolved'}
    return {
        'total_projects': projects.count(),
        'active_projects': active_projects.count(),
        'total_tasks': scan_tasks.count() + agent_tasks.count(),
        'completed_tasks': scan_tasks.filter(status='completed').count() + agent_tasks.filter(status='completed').count(),
        'total_issues': AuditIssue.objects.filter(task__project__in=projects, is_deleted=False).count()
        + AgentFinding.objects.filter(task__project__in=projects, is_deleted=False).count(),
        'resolved_issues': AuditIssue.objects.filter(task__project__in=projects, is_deleted=False, status='resolved').count()
        + AgentFinding.objects.filter(task__project__in=projects, is_deleted=False, status__in=resolved_finding_statuses).count(),
        'avg_quality_score': avg_quality_score,
    }


def list_projects(user, *, keyword: str = '', source_type: str = '', page: int = 1, page_size: int = 20, recycle: bool = False) -> dict:
    queryset = accessible_project_queryset(user, include_deleted=recycle)
    queryset = queryset.filter(is_deleted=recycle).select_related('owner')
    if keyword:
        queryset = queryset.filter(
            Q(name__icontains=keyword) | Q(description__icontains=keyword) | Q(repository_url__icontains=keyword)
        )
    if source_type:
        queryset = queryset.filter(source_type=source_type)
    total = queryset.count()
    start = max(page - 1, 0) * page_size
    items = []
    for project in queryset[start:start + page_size]:
        current_role = require_project_role(user, project, min_role='viewer', include_deleted=recycle).role
        items.append(serialize_project(project, current_role=current_role))
    return {'items': items, 'total': total}


def create_project(user, payload: dict) -> AuditProject:
    repository_spec = _resolve_project_repository_spec(None, payload)
    project = AuditProject.objects.create(
        name=str(payload.get('name') or '').strip(),
        description=str(payload.get('description') or '').strip() or None,
        source_type=str(payload.get('source_type') or 'repository').strip() or 'repository',
        repository_url=repository_spec['repository_url'] or None,
        repository_type=repository_spec['repository_type'],
        default_branch=repository_spec['branch_name'],
        manifest_xml=repository_spec['manifest_xml'] or None,
        group=repository_spec['group'] or None,
        programming_languages=_normalize_languages(payload.get('programming_languages')),
        owner=user,
        is_active=bool(payload.get('is_active', True)),
        sys_creator=user,
        sys_modifier=user,
    )
    sync_owner_membership(project, user)
    return project


def update_project(user, project_id: str, payload: dict) -> AuditProject:
    access = require_project_role(user, project_id, min_role='admin')
    project = access.project
    cache_fields = ('source_type', 'repository_url', 'repository_type', 'default_branch', 'manifest_xml', 'group')
    cache_before = {
        'source_type': str(project.source_type or '').strip(),
        'repository_url': str(project.repository_url or '').strip(),
        'repository_type': normalize_repository_type(project.repository_type),
        'default_branch': str(project.default_branch or '').strip(),
        'manifest_xml': str(project.manifest_xml or '').strip(),
        'group': str(project.group or '').strip(),
    }
    repository_spec = _resolve_project_repository_spec(project, payload)
    for field in ('name', 'description', 'source_type', 'is_active'):
        if field not in payload or payload[field] is None:
            continue
        value = payload[field]
        if field in {'name', 'description', 'source_type'}:
            value = str(value).strip() or None
        setattr(project, field, value)
    project.repository_url = repository_spec['repository_url'] or None
    project.repository_type = repository_spec['repository_type']
    project.default_branch = repository_spec['branch_name']
    project.manifest_xml = repository_spec['manifest_xml'] or None
    project.group = repository_spec['group'] or None
    if payload.get('programming_languages') is not None:
        project.programming_languages = _normalize_languages(payload.get('programming_languages'))
    project.sys_modifier = user
    project.save()
    cache_after = {
        'source_type': str(project.source_type or '').strip(),
        'repository_url': str(project.repository_url or '').strip(),
        'repository_type': normalize_repository_type(project.repository_type),
        'default_branch': str(project.default_branch or '').strip(),
        'manifest_xml': str(project.manifest_xml or '').strip(),
        'group': str(project.group or '').strip(),
    }
    if any(cache_before[field] != cache_after[field] for field in cache_fields):
        _invalidate_project_repo_cache(project.id)
    return project


def get_project_detail(user, project_id: str, *, include_deleted: bool = False) -> dict:
    access = require_project_role(user, project_id, min_role='viewer', include_deleted=include_deleted)
    return serialize_project(access.project, current_role=access.role, include_members=True)


def delete_project(user, project_id: str) -> bool:
    access = require_project_role(user, project_id, min_role='owner')
    project = access.project
    project.is_deleted = True
    project.sys_modifier = user
    project.save(update_fields=['is_deleted', 'sys_modifier', 'sys_update_datetime'])
    project.members.update(is_deleted=True, sys_modifier=user)
    _invalidate_project_repo_cache(project.id)
    return True


def restore_project(user, project_id: str) -> bool:
    access = require_project_role(user, project_id, min_role='owner', include_deleted=True)
    project = access.project
    project.is_deleted = False
    project.sys_modifier = user
    project.save(update_fields=['is_deleted', 'sys_modifier', 'sys_update_datetime'])
    project.members.filter(user=project.owner).update(is_deleted=False, role=PROJECT_MEMBER_ROLE_OWNER)
    sync_owner_membership(project, project.owner)
    return True


def purge_project(user, project_id: str) -> bool:
    access = require_project_role(user, project_id, min_role='owner', include_deleted=True)
    delete_project_zip(access.project.id)
    _invalidate_project_repo_cache(access.project.id)
    access.project.delete()
    return True


def list_members(user, project_id: str) -> list[dict]:
    access = require_project_role(user, project_id, min_role='viewer')
    members = access.project.members.filter(is_deleted=False).select_related('user').order_by('-sort', 'role', 'sys_create_datetime')
    return [serialize_member(member) for member in members]


def add_member(user, project_id: str, payload: dict) -> dict:
    access = require_project_member_manage(user, project_id)
    target_user = get_object_or_404(User, id=payload.get('user_id'))
    if str(target_user.id) == str(access.project.owner_id):
        raise HttpError(400, '项目拥有者已自动作为 owner 成员存在')
    role = str(payload.get('role') or 'member').strip().lower()
    if role not in set(visible_member_roles()) - {PROJECT_MEMBER_ROLE_OWNER}:
        raise HttpError(422, '成员角色不合法')
    member, created = AuditProjectMember.objects.get_or_create(
        project=access.project,
        user=target_user,
        defaults={
            'role': role,
            'permissions': payload.get('permissions') or {},
            'sys_creator': user,
            'sys_modifier': user,
        },
    )
    if not created:
        member.role = role
        member.permissions = payload.get('permissions') or {}
        member.is_deleted = False
        member.sys_modifier = user
        member.save()
    return serialize_member(member)


def update_member(user, project_id: str, member_id: str, payload: dict) -> dict:
    access = require_project_member_manage(user, project_id)
    member = get_object_or_404(AuditProjectMember.objects.select_related('user'), id=member_id, project=access.project)
    if str(member.user_id) == str(access.project.owner_id):
        raise HttpError(400, '不能直接修改项目拥有者角色，请使用转移所有权功能')
    role = str(payload.get('role') or member.role).strip().lower()
    if role not in set(visible_member_roles()) - {PROJECT_MEMBER_ROLE_OWNER}:
        raise HttpError(422, '成员角色不合法')
    member.role = role
    member.permissions = payload.get('permissions') or member.permissions or {}
    member.sys_modifier = user
    member.is_deleted = False
    member.save()
    return serialize_member(member)


def remove_member(user, project_id: str, member_id: str) -> bool:
    access = require_project_member_manage(user, project_id)
    member = get_object_or_404(AuditProjectMember, id=member_id, project=access.project)
    if str(member.user_id) == str(access.project.owner_id):
        raise HttpError(400, '不能移除项目拥有者')
    member.is_deleted = True
    member.sys_modifier = user
    member.save(update_fields=['is_deleted', 'sys_modifier', 'sys_update_datetime'])
    return True


def transfer_owner(user, project_id: str, target_user_id: str) -> bool:
    access = require_project_role(user, project_id, min_role='owner')
    project = access.project
    target_user = get_object_or_404(User, id=target_user_id)
    if str(target_user.id) == str(project.owner_id):
        return True
    old_owner = project.owner
    project.owner = target_user
    project.sys_modifier = user
    project.save(update_fields=['owner', 'sys_modifier', 'sys_update_datetime'])
    sync_owner_membership(project, target_user)
    AuditProjectMember.objects.filter(project=project, user=old_owner).update(role='admin', is_deleted=False, sys_modifier=user)
    return True


def upload_project_zip(user, project_id: str, file_name: str, file_bytes: bytes) -> dict:
    access = require_project_role(user, project_id, min_role='member')
    project = access.project
    _invalidate_project_repo_cache(project.id)
    target = save_project_zip(project.id, file_name, file_bytes)
    artifact = project.artifacts.filter(kind='project_zip').first()
    if artifact:
        artifact.display_name = file_name
        artifact.file_path = str(target)
        artifact.uploaded_by = user
        artifact.sys_modifier = user
        artifact.metadata = {'size': len(file_bytes)}
        artifact.is_deleted = False
        artifact.save()
    else:
        AuditArtifact.objects.create(
            project=project,
            uploaded_by=user,
            kind='project_zip',
            display_name=file_name,
            file_path=str(target),
            mime_type='application/zip',
            metadata={'size': len(file_bytes)},
            sys_creator=user,
            sys_modifier=user,
        )
    if project.source_type != 'zip':
        project.source_type = 'zip'
        project.sys_modifier = user
        project.save(update_fields=['source_type', 'sys_modifier', 'sys_update_datetime'])
    return _project_zip_meta(project)


def get_project_zip_meta(user, project_id: str) -> dict:
    access = require_project_role(user, project_id, min_role='viewer')
    return _project_zip_meta(access.project)


def delete_zip_file(user, project_id: str) -> bool:
    access = require_project_role(user, project_id, min_role='admin')
    deleted = delete_project_zip(access.project.id)
    access.project.artifacts.filter(kind='project_zip').update(is_deleted=True, sys_modifier=user)
    return deleted


def list_branches(user, project_id: str) -> list[str]:
    access = require_project_role(user, project_id, min_role='viewer')
    project = access.project
    if project.source_type != 'repository' or not project.repository_url:
        return [project.default_branch or 'main']

    user_id = str(getattr(user, 'id', '') or project.owner_id)
    user_payload = load_user_config_payload(user_id)
    ssh_private_key = load_ssh_private_key(user_id)
    try:
        branches = list_remote_branches(
            project,
            project.repository_url,
            user_payload,
            ssh_private_key=ssh_private_key,
        )
        return branches or [project.default_branch or 'main']
    except Exception:
        return [project.default_branch or 'main']


def list_files(
    user,
    project_id: str,
    *,
    branch_name: str | None = None,
    manifest_xml: str | None = None,
    group: str | None = None,
    exclude_patterns: list[str] | None = None,
) -> list[dict]:
    access = require_project_role(user, project_id, min_role='viewer')
    project = access.project
    user_id = str(getattr(user, 'id', '') or project.owner_id)
    if project.source_type == 'repository' and repository_cache_enabled():
        repository_spec = build_effective_project_repository_spec(
            project,
            branch_name=branch_name,
            manifest_xml=manifest_xml,
            group=group,
        )
        user_payload = load_user_config_payload(user_id)
        ssh_private_key = load_ssh_private_key(user_id)
        try:
            cache_repo = ensure_repository_cache(
                project,
                repository_spec['repository_url'] or '',
                repository_spec['branch_name'],
                user_payload,
                ssh_private_key=ssh_private_key,
                repository_type=repository_spec['repository_type'],
                manifest_xml=repository_spec['manifest_xml'],
                group=repository_spec['group'],
                allow_stale_on_failure=True,
            )
        except GitServiceError as exc:
            raise HttpError(400, str(exc)) from exc
        return list_repository_files(
            cache_repo,
            exclude_patterns=exclude_patterns or [],
            repository_type=repository_spec['repository_type'],
        )

    workspace = None
    try:
        workspace, _payload = prepare_workspace(
            project,
            branch_name=branch_name,
            user_id=user_id,
            manifest_xml=manifest_xml,
            group=group,
        )
        rows = []
        for path in workspace.rglob('*'):
            if not path.is_file():
                continue
            relative_path = str(path.relative_to(workspace)).replace('\\', '/')
            if should_exclude(relative_path, exclude_patterns):
                continue
            rows.append({'path': relative_path, 'size': path.stat().st_size})
        rows.sort(key=lambda item: item['path'])
        return rows
    finally:
        cleanup_runtime_workspace(workspace)
