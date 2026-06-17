from __future__ import annotations

from datetime import datetime
from django.db import transaction
from django.db.models import Count, F, Max, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.errors import HttpError

from apps.deepaudit.encryption import decrypt_value, encrypt_value
from core.user.user_model import User

from .models import EnvironmentFavorite, EnvironmentQueue, EnvironmentRecord, TestEnvironment
from .schemas import EnvironmentIn, EnvironmentListQuery

ENV_ADMIN_ROLE = 'env_admin'
ENVIRONMENT_USER_ROLE = 'environment_user'


def user_role_codes(user: User | None) -> set[str]:
    """读取用户启用中的系统角色 code，供本模块做二次业务权限判断。"""
    if not user:
        return set()
    return set(user.core_roles.filter(status=True).values_list('code', flat=True))


def can_manage(user: User | None) -> bool:
    """环境管理员拥有管理端 CRUD、释放任意占用和查看明文密码的最高权限。"""
    return bool(user and (user.is_superuser or ENV_ADMIN_ROLE in user_role_codes(user)))


def can_use_environment(user: User | None) -> bool:
    """环境用户可以查看明文账号密码，并执行占用、排队、插队、释放自己的占用。"""
    return bool(user and (can_manage(user) or ENVIRONMENT_USER_ROLE in user_role_codes(user)))


def can_view_secret(user: User | None) -> bool:
    """密码明文只给环境用户和环境管理员，平台默认用户永远只收到脱敏值。"""
    return can_use_environment(user)


def require_manager(user: User | None):
    if not can_manage(user):
        raise HttpError(403, '只有环境管理员可以维护环境配置')


def require_environment_user(user: User | None):
    if not can_use_environment(user):
        raise HttpError(403, '只有环境用户或环境管理员可以使用环境')


def _display_name(user: User | None) -> str:
    if not user:
        return ''
    return user.name or user.username or ''


def _mask_secret(value: str) -> str:
    if not value:
        return ''
    if len(value) <= 2:
        return '*' * len(value)
    if len(value) <= 6:
        return f'{value[:1]}***{value[-1:]}'
    return f'{value[:2]}****{value[-2:]}'


def _duration_seconds(started_at: datetime | None, ended_at: datetime | None = None) -> int:
    if not started_at:
        return 0
    end = ended_at or timezone.now()
    return max(int((end - started_at).total_seconds()), 0)


def _waiting_queues(environment_id: str):
    """统一等待队列排序，确保所有业务动作看到的队首规则完全一致。"""
    return (
        EnvironmentQueue.objects.filter(environment_id=environment_id, status='waiting')
        .select_related('user')
        .order_by('position', 'requested_at')
    )


def _renumber_waiting_queue(environment_id: str):
    """取消或完成队列项后重新编号，避免前端展示出现 1、3、4 这类断档位置。"""
    waiting = list(_waiting_queues(environment_id).only('id'))
    for index, row in enumerate(waiting, start=1):
        if row.position != index:
            row.position = index
            row.save(update_fields=['position', 'sys_update_datetime'])


def serialize_environment(env: TestEnvironment, user: User | None) -> dict:
    """把环境模型转换成前端 DTO，并在这里集中处理密码脱敏这一条安全边界。"""
    roles_can_view_secret = can_view_secret(user)
    roles_can_use = can_use_environment(user)
    raw_password = decrypt_value(env.password_encrypted)
    favorite_ids = getattr(env, '_favorite_user_ids', None)
    queue_rows = list(getattr(env, '_prefetched_waiting_queues', []))

    if favorite_ids is None and user:
        is_favorite = EnvironmentFavorite.objects.filter(environment=env, user=user).exists()
    else:
        is_favorite = bool(user and str(user.id) in {str(v) for v in (favorite_ids or [])})

    if not queue_rows:
        queue_rows = list(_waiting_queues(env.id))

    my_queue = next((q for q in queue_rows if user and str(q.user_id) == str(user.id)), None)
    first_queue = queue_rows[0] if queue_rows else None

    return {
        'id': str(env.id),
        'ip_address': env.ip_address,
        'account': env.account if roles_can_view_secret else _mask_secret(env.account),
        'password': raw_password if roles_can_view_secret else _mask_secret(raw_password),
        'can_view_secret': roles_can_view_secret,
        'can_use_environment': roles_can_use,
        'domain': env.domain,
        'domain_label': dict(TestEnvironment.DOMAIN_CHOICES).get(env.domain, env.domain),
        'category': env.category,
        'category_label': dict(TestEnvironment.CATEGORY_CHOICES).get(env.category, env.category),
        'project_name': env.project_name,
        'vehicle_model': env.vehicle_model,
        'device_material': env.device_material,
        'asset_number': env.asset_number,
        'device_display': ' / '.join([v for v in [env.device_material, env.asset_number] if v]),
        'config': env.config or {},
        'shelf_location': env.shelf_location,
        'status': env.status,
        'status_label': dict(TestEnvironment.STATUS_CHOICES).get(env.status, env.status),
        'current_user_id': str(env.current_user_id) if env.current_user_id else None,
        'current_user_name': _display_name(env.current_user),
        'occupied_at': env.occupied_at,
        'occupied_seconds': _duration_seconds(env.occupied_at) if env.status == 'occupied' else 0,
        'is_favorite': is_favorite,
        'queue_count': len(queue_rows),
        'my_queue_id': str(my_queue.id) if my_queue else None,
        'my_queue_position': my_queue.position if my_queue else None,
        'first_queue_user_name': _display_name(first_queue.user) if first_queue else '',
        'rdp_url': f'rdp://{env.ip_address}',
        'sort': env.sort,
        'sys_create_datetime': env.sys_create_datetime,
        'sys_update_datetime': env.sys_update_datetime,
    }


def _record(env: TestEnvironment, user: User | None, action: str, message: str = '', **kwargs):
    """记录模块内关键动作，后续排查占用冲突和队列争议时以该表为准。"""
    EnvironmentRecord.objects.create(
        environment=env,
        operator=user,
        action=action,
        message=message,
        snapshot={
            'ip_address': env.ip_address,
            'status': env.status,
            'current_user_id': str(env.current_user_id) if env.current_user_id else None,
        },
        **kwargs,
    )


def list_environments(user: User, query: EnvironmentListQuery) -> dict:
    """用户端和管理端共用列表查询；前端能力差异由角色字段和菜单权限控制。"""
    qs = (
        TestEnvironment.objects.filter(is_deleted=False)
        .select_related('current_user')
        .annotate(waiting_count=Count('queues', filter=Q(queues__status='waiting')))
    )
    if query.domain:
        qs = qs.filter(domain=query.domain)
    if query.category:
        qs = qs.filter(category=query.category)
    if query.project_name:
        qs = qs.filter(project_name__icontains=query.project_name)
    if query.vehicle_model:
        qs = qs.filter(vehicle_model__icontains=query.vehicle_model)
    if query.keyword:
        qs = qs.filter(
            Q(ip_address__icontains=query.keyword)
            | Q(project_name__icontains=query.keyword)
            | Q(vehicle_model__icontains=query.keyword)
            | Q(device_material__icontains=query.keyword)
            | Q(asset_number__icontains=query.keyword)
            | Q(shelf_location__icontains=query.keyword)
        )
    if query.favorite_only:
        qs = qs.filter(favorites__user=user)

    favorite_env_ids = set(
        EnvironmentFavorite.objects.filter(user=user).values_list('environment_id', flat=True)
    )
    total = qs.distinct().count()
    start = max(query.page - 1, 0) * query.pageSize
    rows = list(qs.distinct().order_by('-sort', 'ip_address')[start : start + query.pageSize])
    waiting_map = {
        env.id: []
        for env in rows
    }
    if rows:
        queues = EnvironmentQueue.objects.filter(
            environment_id__in=[env.id for env in rows],
            status='waiting',
        ).select_related('user').order_by('environment_id', 'position', 'requested_at')
        for queue in queues:
            waiting_map.setdefault(queue.environment_id, []).append(queue)

    # 收藏优先是用户端核心扫描体验；分页内再稳定排序，避免打散服务端分页的性能边界。
    serialized = []
    for env in rows:
        env._favorite_user_ids = [str(user.id)] if env.id in favorite_env_ids else []
        env._prefetched_waiting_queues = waiting_map.get(env.id, [])
        serialized.append(serialize_environment(env, user))
    serialized.sort(key=lambda item: (not item['is_favorite'], item['status'] != 'idle', item['ip_address']))
    return {'items': serialized, 'total': total, 'page': query.page, 'limit': query.pageSize}


def create_environment(user: User, payload: EnvironmentIn) -> dict:
    """创建环境配置，密码一进入服务层就加密，避免明文落库。"""
    require_manager(user)
    data = payload.dict()
    password = data.pop('password', None)
    env = TestEnvironment.objects.create(
        **data,
        password_encrypted=encrypt_value(password or ''),
        sys_creator=user,
        sys_modifier=user,
    )
    _record(env, user, 'admin_update', '创建环境配置')
    return serialize_environment(env, user)


def update_environment(user: User, environment_id: str, payload: EnvironmentIn) -> dict:
    """更新环境配置；编辑时 password 为空字符串表示清空，None 表示不修改。"""
    require_manager(user)
    env = get_object_or_404(TestEnvironment, id=environment_id, is_deleted=False)
    data = payload.dict()
    password = data.pop('password', None)
    for field, value in data.items():
        setattr(env, field, value)
    if password is not None:
        env.password_encrypted = encrypt_value(password)
    env.sys_modifier = user
    env.save()
    _record(env, user, 'admin_update', '更新环境配置')
    return serialize_environment(env, user)


def delete_environment(user: User, environment_id: str) -> bool:
    """软删除环境；仍被占用的环境不允许删除，避免破坏占用审计链路。"""
    require_manager(user)
    env = get_object_or_404(TestEnvironment, id=environment_id, is_deleted=False)
    if env.status == 'occupied':
        raise HttpError(400, '环境正在占用中，释放后才能删除')
    env.soft_delete()
    EnvironmentQueue.objects.filter(environment=env, status='waiting').update(status='cancelled')
    _record(env, user, 'admin_update', '删除环境配置')
    return True


def set_favorite(user: User, environment_id: str, enabled: bool) -> dict:
    """收藏是个人视图偏好，平台默认用户也可以使用，不参与占用权限判断。"""
    env = get_object_or_404(TestEnvironment, id=environment_id, is_deleted=False)
    if enabled:
        EnvironmentFavorite.objects.get_or_create(environment=env, user=user)
    else:
        EnvironmentFavorite.objects.filter(environment=env, user=user).delete()
    return serialize_environment(env, user)


def occupy_environment(user: User, environment_id: str) -> dict:
    """申请占用环境；只有环境用户/管理员可执行，并用行锁避免并发抢占。"""
    require_environment_user(user)
    with transaction.atomic():
        env = TestEnvironment.objects.select_for_update().select_related('current_user').get(id=environment_id, is_deleted=False)
        if env.current_user_id and str(env.current_user_id) == str(user.id):
            return {'success': True, 'message': '你已占用该环境', 'environment': serialize_environment(env, user)}
        if env.status == 'occupied':
            raise HttpError(400, '环境正在被占用，请先排队')
        waiting = list(_waiting_queues(env.id).select_for_update())
        if waiting and str(waiting[0].user_id) != str(user.id):
            raise HttpError(400, f'当前队首为 {_display_name(waiting[0].user)}，暂不能占用')

        # 只有环境空闲且无他人排在前面时才直接占用；如果本人是队首，占用成功后关闭自己的等待记录。
        env.status = 'occupied'
        env.current_user = user
        env.occupied_at = timezone.now()
        env.sys_modifier = user
        env.save(update_fields=['status', 'current_user', 'occupied_at', 'sys_modifier', 'sys_update_datetime'])
        EnvironmentQueue.objects.filter(environment=env, user=user, status='waiting').update(status='done')
        _renumber_waiting_queue(env.id)
        _record(env, user, 'occupy', '占用环境', started_at=env.occupied_at)
    return {'success': True, 'message': '占用成功，可以打开 RDP', 'environment': serialize_environment(env, user)}


def release_environment(user: User, environment_id: str) -> dict:
    """释放环境；释放后只提示队首，不自动转交，避免无人确认时长期占用。"""
    if not can_use_environment(user):
        raise HttpError(403, '只有环境用户或环境管理员可以释放环境')
    with transaction.atomic():
        env = TestEnvironment.objects.select_for_update().select_related('current_user').get(id=environment_id, is_deleted=False)
        if env.status != 'occupied' or not env.current_user_id:
            raise HttpError(400, '环境当前未被占用')
        if str(env.current_user_id) != str(user.id) and not can_manage(user):
            raise HttpError(403, '只有当前占用人或环境管理员可以释放')
        started_at = env.occupied_at
        ended_at = timezone.now()
        duration = _duration_seconds(started_at, ended_at)
        released_user = _display_name(env.current_user)
        env.status = 'idle'
        env.current_user = None
        env.occupied_at = None
        env.sys_modifier = user
        env.save(update_fields=['status', 'current_user', 'occupied_at', 'sys_modifier', 'sys_update_datetime'])
        first_queue = _waiting_queues(env.id).first()
        message = f'{released_user} 释放环境'
        if first_queue:
            message = f'{message}，队首用户 { _display_name(first_queue.user) } 可手动占用'
        _record(env, user, 'release', message, started_at=started_at, ended_at=ended_at, duration_seconds=duration)
    return {'success': True, 'message': message, 'environment': serialize_environment(env, user)}


def enqueue_environment(user: User, environment_id: str, queue_type: str) -> dict:
    """进入等待队列；插队只改变等待顺序，不会抢占当前正在使用的人。"""
    require_environment_user(user)
    with transaction.atomic():
        env = TestEnvironment.objects.select_for_update().get(id=environment_id, is_deleted=False)
        if env.current_user_id and str(env.current_user_id) == str(user.id):
            raise HttpError(400, '你已占用该环境，无需排队')
        existing = EnvironmentQueue.objects.filter(environment=env, user=user, status='waiting').first()
        if existing:
            raise HttpError(400, '你已在该环境队列中')

        # 插队只改变等待队列顺序，不会抢占当前占用人；为了保持队列稳定，插队排在所有已有插队之后、普通队列之前。
        waiting = list(_waiting_queues(env.id).select_for_update())
        if queue_type == 'jump':
            jump_count = sum(1 for row in waiting if row.queue_type == 'jump')
            insert_position = jump_count + 1
            EnvironmentQueue.objects.filter(environment=env, status='waiting', position__gte=insert_position).update(position=F('position') + 1)
        else:
            insert_position = (EnvironmentQueue.objects.filter(environment=env, status='waiting').aggregate(max_pos=Max('position'))['max_pos'] or 0) + 1
        queue = EnvironmentQueue.objects.create(
            environment=env,
            user=user,
            queue_type=queue_type,
            position=insert_position,
            sys_creator=user,
            sys_modifier=user,
        )
        _renumber_waiting_queue(env.id)
        _record(env, user, 'jump_queue' if queue_type == 'jump' else 'queue', f'{dict(EnvironmentQueue.QUEUE_TYPE_CHOICES).get(queue_type)}成功，当前位置 {queue.position}')
    return serialize_environment(env, user)


def cancel_my_queue(user: User, environment_id: str) -> dict:
    """取消自己的等待记录；取消后重新压紧队列位置。"""
    require_environment_user(user)
    with transaction.atomic():
        env = TestEnvironment.objects.select_for_update().get(id=environment_id, is_deleted=False)
        queue = EnvironmentQueue.objects.filter(environment=env, user=user, status='waiting').first()
        if not queue:
            raise HttpError(400, '你不在该环境队列中')
        queue.status = 'cancelled'
        queue.sys_modifier = user
        queue.save(update_fields=['status', 'sys_modifier', 'sys_update_datetime'])
        _renumber_waiting_queue(env.id)
        _record(env, user, 'cancel_queue', '取消排队')
    return serialize_environment(env, user)


def list_queue(user: User, environment_id: str) -> list[dict]:
    """查看当前等待队列，平台默认用户也可以查看排队情况。"""
    get_object_or_404(TestEnvironment, id=environment_id, is_deleted=False)
    return [
        {
            'id': str(row.id),
            'user_id': str(row.user_id),
            'user_name': _display_name(row.user),
            'queue_type': row.queue_type,
            'queue_type_label': dict(EnvironmentQueue.QUEUE_TYPE_CHOICES).get(row.queue_type, row.queue_type),
            'position': row.position,
            'requested_at': row.requested_at,
            'is_me': str(row.user_id) == str(user.id),
        }
        for row in _waiting_queues(environment_id)
    ]


def list_records(environment_id: str, page: int = 1, page_size: int = 20) -> dict:
    """查看操作记录，默认用于用户端记录抽屉。"""
    get_object_or_404(TestEnvironment, id=environment_id, is_deleted=False)
    qs = EnvironmentRecord.objects.filter(environment_id=environment_id).select_related('operator')
    total = qs.count()
    start = max(page - 1, 0) * page_size
    rows = qs[start : start + page_size]
    return {
        'items': [
            {
                'id': str(row.id),
                'operator_id': str(row.operator_id) if row.operator_id else None,
                'operator_name': _display_name(row.operator),
                'action': row.action,
                'action_label': dict(EnvironmentRecord.ACTION_CHOICES).get(row.action, row.action),
                'message': row.message,
                'started_at': row.started_at,
                'ended_at': row.ended_at,
                'duration_seconds': row.duration_seconds,
                'sys_create_datetime': row.sys_create_datetime,
            }
            for row in rows
        ],
        'total': total,
        'page': page,
        'limit': page_size,
    }
