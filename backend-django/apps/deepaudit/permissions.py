from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.db.models import Q, QuerySet
from django.conf import settings
from ninja.errors import HttpError

from apps.deepaudit.constants import (
    PROJECT_MEMBER_ROLE_ADMIN,
    PROJECT_MEMBER_ROLE_MEMBER,
    PROJECT_MEMBER_ROLE_OWNER,
    PROJECT_MEMBER_ROLE_VIEWER,
)
from apps.deepaudit.project.project_model import AuditProject, AuditProjectMember
from apps.deepaudit.serialization import format_datetime_text


ROLE_PRIORITY = {
    PROJECT_MEMBER_ROLE_VIEWER: 10,
    PROJECT_MEMBER_ROLE_MEMBER: 20,
    PROJECT_MEMBER_ROLE_ADMIN: 30,
    PROJECT_MEMBER_ROLE_OWNER: 40,
    'superadmin': 100,
}


@dataclass(frozen=True)
class ProjectAccess:
    project: AuditProject
    role: str
    is_owner: bool = False
    is_superadmin: bool = False

    @property
    def can_manage_members(self) -> bool:
        return self.is_superadmin or self.role in {
            PROJECT_MEMBER_ROLE_OWNER,
            PROJECT_MEMBER_ROLE_ADMIN,
        }

    @property
    def can_manage_project(self) -> bool:
        return self.is_superadmin or self.role in {
            PROJECT_MEMBER_ROLE_OWNER,
            PROJECT_MEMBER_ROLE_ADMIN,
        }

    @property
    def can_delete_project(self) -> bool:
        return self.is_superadmin or self.role == PROJECT_MEMBER_ROLE_OWNER


ROLE_LABELS = {
    PROJECT_MEMBER_ROLE_OWNER: 'owner',
    PROJECT_MEMBER_ROLE_ADMIN: 'admin',
    PROJECT_MEMBER_ROLE_MEMBER: 'member',
    PROJECT_MEMBER_ROLE_VIEWER: 'viewer',
    'superadmin': 'superadmin',
}


DEFAULT_ROLE = PROJECT_MEMBER_ROLE_VIEWER


def department_wide_read_enabled() -> bool:
    """Whether every authenticated department user can view active audit projects."""
    return bool(getattr(settings, 'DEEPAUDIT_DEPARTMENT_WIDE_READ', True))


def get_user_id(user) -> str:
    return str(getattr(user, 'id', '') or '')


def normalize_role(value: str | None) -> str:
    role = str(value or DEFAULT_ROLE).strip().lower()
    if role not in ROLE_PRIORITY:
        raise HttpError(422, f'不支持的项目角色: {value}')
    return role


def is_superadmin(user) -> bool:
    if not user:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    try:
        return user.core_roles.filter(code__iexact='superadmin', status=True).exists()
    except Exception:
        return False


def accessible_project_queryset(user, include_deleted: bool = False) -> QuerySet[AuditProject]:
    queryset = AuditProject.objects.all().select_related('owner').prefetch_related('members__user')
    if not include_deleted:
        queryset = queryset.filter(is_deleted=False)
    if is_superadmin(user):
        return queryset.distinct()
    user_id = get_user_id(user)
    if not user_id:
        return queryset.none()
    # Department deployments share active projects, tasks, findings, and reports.
    # Deleted projects remain visible only to their existing members and administrators.
    if department_wide_read_enabled():
        if not include_deleted:
            return queryset.distinct()
        return queryset.filter(
            Q(is_deleted=False) | Q(owner_id=user_id) | Q(members__user_id=user_id)
        ).distinct()
    return queryset.filter(Q(owner_id=user_id) | Q(members__user_id=user_id)).distinct()


def get_project_access(user, project_or_id: AuditProject | str, *, include_deleted: bool = False) -> ProjectAccess:
    project: AuditProject
    if isinstance(project_or_id, AuditProject):
        project = project_or_id
    else:
        queryset = accessible_project_queryset(user, include_deleted=include_deleted)
        project = queryset.filter(id=project_or_id).first()
        if not project:
            raise HttpError(404, '项目不存在或无访问权限')

    if project.is_deleted and not include_deleted:
        raise HttpError(404, '项目不存在或已删除')

    if is_superadmin(user):
        return ProjectAccess(project=project, role='superadmin', is_superadmin=True)

    user_id = get_user_id(user)
    if not user_id:
        raise HttpError(403, '无项目访问权限')
    if str(project.owner_id) == user_id:
        return ProjectAccess(project=project, role=PROJECT_MEMBER_ROLE_OWNER, is_owner=True)

    membership = project.members.filter(user_id=user_id, is_deleted=False).order_by('-sys_create_datetime').first()
    if membership:
        return ProjectAccess(project=project, role=normalize_role(membership.role))

    if department_wide_read_enabled() and not project.is_deleted:
        return ProjectAccess(project=project, role=PROJECT_MEMBER_ROLE_VIEWER)

    raise HttpError(403, '无项目访问权限')


def require_project_role(
    user,
    project_or_id: AuditProject | str,
    *,
    min_role: str = PROJECT_MEMBER_ROLE_VIEWER,
    include_deleted: bool = False,
) -> ProjectAccess:
    access = get_project_access(user, project_or_id, include_deleted=include_deleted)
    required_role = normalize_role(min_role)
    if ROLE_PRIORITY[access.role] < ROLE_PRIORITY[required_role]:
        raise HttpError(403, '当前角色无权执行此操作')
    return access


def require_project_member_manage(user, project_or_id: AuditProject | str) -> ProjectAccess:
    access = require_project_role(user, project_or_id, min_role=PROJECT_MEMBER_ROLE_ADMIN)
    if not access.can_manage_members:
        raise HttpError(403, '当前角色无权管理项目成员')
    return access


def sync_owner_membership(project: AuditProject, user) -> AuditProjectMember:
    member, _ = AuditProjectMember.objects.get_or_create(
        project=project,
        user=user,
        defaults={
            'role': PROJECT_MEMBER_ROLE_OWNER,
            'sys_creator': user,
            'sys_modifier': user,
        },
    )
    changed = False
    if member.role != PROJECT_MEMBER_ROLE_OWNER:
        member.role = PROJECT_MEMBER_ROLE_OWNER
        changed = True
    if member.is_deleted:
        member.is_deleted = False
        changed = True
    if changed:
        member.sys_modifier = user
        member.save(update_fields=['role', 'is_deleted', 'sys_modifier', 'sys_update_datetime'])
    return member


def serialize_user_brief(user) -> dict:
    if not user:
        return {'id': '', 'username': '', 'name': ''}
    return {
        'id': str(getattr(user, 'id', '') or ''),
        'username': str(getattr(user, 'username', '') or ''),
        'name': str(getattr(user, 'name', '') or getattr(user, 'username', '') or ''),
    }


def serialize_member(member: AuditProjectMember) -> dict:
    payload = serialize_user_brief(member.user)
    payload.update(
        {
            'member_id': str(member.id),
            'project_id': str(member.project_id),
            'role': member.role,
            'permissions': member.permissions or {},
            'sys_create_datetime': format_datetime_text(member.sys_create_datetime),
            'sys_update_datetime': format_datetime_text(member.sys_update_datetime),
        }
    )
    return payload


def visible_member_roles() -> Iterable[str]:
    return (
        PROJECT_MEMBER_ROLE_OWNER,
        PROJECT_MEMBER_ROLE_ADMIN,
        PROJECT_MEMBER_ROLE_MEMBER,
        PROJECT_MEMBER_ROLE_VIEWER,
    )
