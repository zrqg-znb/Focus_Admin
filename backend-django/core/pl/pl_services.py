#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PL 资源组服务层。"""
from types import SimpleNamespace
from typing import Iterable, List, Optional

from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError

from core.pl.pl_model import PlGroup
from core.user.user_model import User


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _get_user(user_id: str) -> User:
    return get_object_or_404(User, id=user_id)


def _get_group(pl_id: str) -> PlGroup:
    return get_object_or_404(PlGroup.objects.select_related('pl_user'), id=pl_id)


def _ensure_code_unique(code: Optional[str], exclude_id: Optional[str] = None):
    if not code:
        return
    query = PlGroup.objects.filter(code=code)
    if exclude_id:
        query = query.exclude(id=exclude_id)
    if query.exists():
        raise HttpError(400, f'资源组编码已存在: {code}')


def _apply_fields(group: PlGroup, payload: dict):
    for field in ('name', 'code', 'status', 'description', 'sort'):
        if field in payload:
            setattr(group, field, payload[field])


def build_pl_group_queryset(filters) -> QuerySet:
    queryset = PlGroup.objects.all()
    if filters is not None:
        for attr, value in filters.dict().items():
            if getattr(filters, attr) == '':
                setattr(filters, attr, None)
        queryset = filters.filter(queryset)
    return queryset.select_related('pl_user').annotate(member_count=Count('members', distinct=True))


@transaction.atomic
def create_pl_group(request, payload) -> PlGroup:
    data = payload.dict()
    data['name'] = data['name'].strip()
    data['code'] = _normalize_optional_text(data.get('code'))
    data['description'] = _normalize_optional_text(data.get('description'))
    _ensure_code_unique(data.get('code'))

    pl_user = _get_user(data.pop('pl_user_id'))
    creator_id = getattr(getattr(request, 'auth', None), 'id', None)
    if creator_id:
        data['sys_creator_id'] = creator_id
    group = PlGroup.objects.create(
        pl_user=pl_user,
        **data,
    )
    group.members.add(pl_user)
    return _get_group(group.id)


@transaction.atomic
def update_pl_group(request, pl_id: str, payload, partial: bool = False) -> PlGroup:
    group = _get_group(pl_id)
    data = payload.dict(exclude_unset=partial)

    if 'name' in data and data['name'] is not None:
        data['name'] = data['name'].strip()
    if 'code' in data:
        data['code'] = _normalize_optional_text(data.get('code'))
        _ensure_code_unique(data['code'], exclude_id=pl_id)
    if 'description' in data:
        data['description'] = _normalize_optional_text(data.get('description'))

    pl_user_id = data.pop('pl_user_id', None)
    _apply_fields(group, data)
    if pl_user_id:
        pl_user = _get_user(pl_user_id)
        group.pl_user = pl_user
    modifier_id = getattr(getattr(request, 'auth', None), 'id', None)
    if modifier_id:
        group.sys_modifier_id = modifier_id
    group.save()
    group.members.add(group.pl_user)
    return _get_group(group.id)


@transaction.atomic
def delete_pl_group(pl_id: str) -> PlGroup:
    group = _get_group(pl_id)
    member_count = group.get_member_count()
    group_snapshot = SimpleNamespace(
        id=group.id,
        name=group.name,
        code=group.code,
        status=group.status,
        description=group.description,
        sort=group.sort,
        pl_user=group.pl_user,
        pl_user_id=group.pl_user_id,
        member_count=member_count,
        sys_create_datetime=group.sys_create_datetime,
        sys_update_datetime=group.sys_update_datetime,
    )
    group.members.clear()
    group.delete()
    return group_snapshot


@transaction.atomic
def batch_delete_pl_groups(ids: Iterable[str]):
    failed_ids: List[str] = []
    count = 0
    for pl_id in ids:
        try:
            delete_pl_group(pl_id)
            count += 1
        except HttpError:
            failed_ids.append(pl_id)
    return count, failed_ids


def list_all_pl_groups() -> QuerySet:
    return (
        PlGroup.objects.filter(status=True)
        .select_related('pl_user')
        .annotate(member_count=Count('members', distinct=True))
        .order_by('-status', '-sort', 'name')
    )


def get_pl_group_detail(pl_id: str) -> PlGroup:
    return _get_group(pl_id)


def batch_update_pl_group_status(ids: Iterable[str], status: bool) -> int:
    return PlGroup.objects.filter(id__in=list(ids)).update(status=status)


def get_pl_group_users(pl_id: str, name: Optional[str] = None) -> QuerySet:
    group = _get_group(pl_id)
    users = group.members.select_related('dept').all().order_by('name', 'username')
    if name:
        keyword = name.strip()
        if keyword:
            users = users.filter(Q(name__icontains=keyword) | Q(username__icontains=keyword))
    return users


@transaction.atomic
def add_pl_group_users(pl_id: str, user_ids: Iterable[str]):
    group = _get_group(pl_id)
    ids = [user_id for user_id in user_ids if user_id]
    if not ids:
        raise HttpError(400, '用户ID列表不能为空')

    users = list(User.objects.filter(id__in=ids))
    found_ids = {user.id for user in users}
    missing_ids = [user_id for user_id in ids if user_id not in found_ids]
    if missing_ids:
        missing_label = ', '.join([str(item) for item in missing_ids])
        raise HttpError(404, f"用户不存在: {missing_label}")

    before_ids = set(group.members.values_list('id', flat=True))
    group.members.add(*users)
    group.members.add(group.pl_user)
    after_ids = set(group.members.values_list('id', flat=True))
    return len(after_ids - before_ids)


@transaction.atomic
def remove_pl_group_users(pl_id: str, user_ids: Iterable[str]):
    group = _get_group(pl_id)
    ids = [user_id for user_id in user_ids if user_id]
    if not ids:
        raise HttpError(400, '用户ID不能为空')
    if group.pl_user_id in ids:
        raise HttpError(400, '当前PL不能被移除，请先更换PL负责人')

    users = list(User.objects.filter(id__in=ids))
    found_ids = {user.id for user in users}
    missing_ids = [user_id for user_id in ids if user_id not in found_ids]
    if missing_ids:
        missing_label = ', '.join([str(item) for item in missing_ids])
        raise HttpError(404, f"用户不存在: {missing_label}")

    existing_ids = set(group.members.values_list('id', flat=True))
    removable_ids = [user.id for user in users if user.id in existing_ids]
    if removable_ids:
        group.members.remove(*removable_ids)
    return len(removable_ids)
