from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import quote
from django.db import transaction
from django.db.models import Count, Exists, F, Max, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.errors import HttpError

from apps.deepaudit.encryption import encrypt_value
from core.user.user_model import User

from .models import (
    EnvironmentAnnouncement,
    EnvironmentDeviceBinding,
    EnvironmentDeviceType,
    EnvironmentFavorite,
    EnvironmentQueue,
    EnvironmentRecord,
    EnvironmentTestDevice,
    TestEnvironment,
)
from .schemas import DeviceTypeIn, EnvironmentAnnouncementIn, EnvironmentIn, EnvironmentListQuery, TestDeviceIn

ENV_ADMIN_ROLE = 'env_admin'
ENVIRONMENT_USER_ROLE = 'environment_user'
logger = logging.getLogger(__name__)


def user_role_codes(user: User | None) -> set[str]:
    """读取用户启用中的系统角色 code，供本模块做二次业务权限判断。"""
    if not user:
        return set()
    return set(user.core_roles.filter(status=True).values_list('code', flat=True))


def can_manage(user: User | None) -> bool:
    """环境管理员拥有管理端 CRUD、释放任意占用等最高权限；密码仍不通过列表接口下发。"""
    return bool(user and (user.is_superuser or ENV_ADMIN_ROLE in user_role_codes(user)))


def can_use_environment(user: User | None) -> bool:
    """环境用户可以执行占用、排队、释放自己的占用；密码只允许后台写入，不给用户端读取。"""
    return bool(user and (can_manage(user) or ENVIRONMENT_USER_ROLE in user_role_codes(user)))


def can_view_secret(user: User | None) -> bool:
    """历史兼容函数。

    旧版本用该函数控制账号密码明文；当前安全策略是账号所有人可见、密码任何列表/详情
    接口都不下发，因此这里固定返回 False，避免前端误以为可读取密码。
    """
    return False


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


def _waiting_queues_for_update(environment_id: str):
    """事务内锁定等待队列。

    这里刻意不复用 _waiting_queues()，因为展示查询带 select_related('user')。
    业务锁定和重排只需要队列自身字段，混用关联预取再配合 only/defer 或 select_for_update
    容易触发 Django 的 deferred + select_related 冲突。
    """
    return EnvironmentQueue.objects.filter(environment_id=environment_id, status='waiting').order_by('position', 'requested_at')


def _renumber_waiting_queue(environment_id: str):
    """取消或完成队列项后重新编号，避免前端展示出现 1、3、4 这类断档位置。"""
    # 不能复用 _waiting_queues().only('id')：该查询已 select_related('user')，
    # 再 defer 掉 user 会触发 Django 的 "cannot be both deferred and traversed" 报错。
    waiting = list(
        EnvironmentQueue.objects.filter(environment_id=environment_id, status='waiting')
        .only('id', 'position')
        .order_by('position', 'requested_at')
    )
    for index, row in enumerate(waiting, start=1):
        if row.position != index:
            row.position = index
            row.save(update_fields=['position', 'sys_update_datetime'])


def send_environment_queue_notification_by_username(
    username: str,
    title: str,
    content: str,
    payload: dict | None = None,
) -> None:
    """环境队列通知占位。

    公司内网环境接入真实消息系统时，只需要替换这里的 logger.info 为真实发送逻辑。
    该函数按 username 投递，且必须保持业务旁路：任何通知异常都不能影响环境占用、
    释放、排队和取消排队的主事务。
    """
    try:
        logger.info(
            'environment queue notification placeholder username=%s title=%s content=%s payload=%s',
            username,
            title,
            content,
            payload or {},
        )
    except Exception:
        logger.exception('environment queue notification placeholder failed username=%s', username)


def _safe_send_environment_queue_notification_by_username(
    username: str,
    title: str,
    content: str,
    payload: dict | None = None,
) -> None:
    """隔离真实通知实现的异常，确保通知永远不会反向影响环境业务流程。"""
    try:
        send_environment_queue_notification_by_username(username, title, content, payload)
    except Exception:
        logger.exception('environment queue notification failed username=%s', username)


def _queue_notification_snapshot(environment_id: str) -> list[dict]:
    """记录等待队列快照，用于比较用户是否向前移动。

    快照只保留通知必需字段，刻意不包含账号、密码、RDP 等敏感信息，避免未来接入真实
    通知渠道时误把凭据带出系统边界。
    """
    return [
        {
            'user_id': str(row.user_id),
            'username': row.user.username,
            'display_name': _display_name(row.user),
            'position': row.position,
        }
        for row in _waiting_queues(environment_id)
    ]


def _environment_notification_payload(env: TestEnvironment, position: int | None, event: str, available: bool) -> dict:
    """构造通知 payload；该结构只携带环境识别和队列状态，不携带账号密码。"""
    return {
        'environment_id': str(env.id),
        'ip_address': env.ip_address,
        'project_name': env.project_name,
        'vehicle_model': env.vehicle_model,
        'position': position,
        'event': event,
        'available': available,
    }


def _notify_queue_changes_after_commit(
    env: TestEnvironment,
    before_snapshot: list[dict],
    event: str,
    notify_available_head: bool,
) -> None:
    """提交事务后通知队列变化。

    发送动作通过 transaction.on_commit 延迟到数据库提交之后执行，确保通知系统不可用时
    不会让主流程回滚。只通知两类正向变化：用户排位前进、环境空闲且轮到队首用户。
    """
    environment_id = str(env.id)

    def _send_notifications():
        try:
            fresh_env = TestEnvironment.objects.get(id=environment_id)
            after_snapshot = _queue_notification_snapshot(environment_id)
            before_by_user_id = {item['user_id']: item for item in before_snapshot}
            available_head_user_id = after_snapshot[0]['user_id'] if notify_available_head and fresh_env.status == 'idle' and after_snapshot else None

            for item in after_snapshot:
                old_item = before_by_user_id.get(item['user_id'])
                is_available_head = item['user_id'] == available_head_user_id
                if is_available_head:
                    _safe_send_environment_queue_notification_by_username(
                        item['username'],
                        '环境已轮到你使用',
                        f"环境 {fresh_env.ip_address} 已空闲，当前轮到你使用，请及时手动占用。",
                        _environment_notification_payload(fresh_env, item['position'], event, True),
                    )
                    # 队首用户收到“轮到自己”即可，避免同一次变化里再收到“位置前进”造成打扰。
                    continue

                if old_item and item['position'] < old_item['position']:
                    _safe_send_environment_queue_notification_by_username(
                        item['username'],
                        '环境队列位置已前进',
                        f"环境 {fresh_env.ip_address} 的队列位置已前进到第 {item['position']} 位。",
                        _environment_notification_payload(fresh_env, item['position'], event, False),
                    )
        except Exception:
            logger.exception('environment queue notification callback failed environment_id=%s event=%s', environment_id, event)

    transaction.on_commit(_send_notifications)


def _notify_auto_occupied_after_commit(env: TestEnvironment, assigned_user: User, event: str) -> None:
    """提交事务后通知队首用户已被自动分配环境。

    手动释放后的自动转交已经在事务内把环境状态改成 occupied，因此不能复用“环境空闲且轮到
    队首”的通知文案。这里单独通知被转交用户：环境已经归他占用，但仍不包含账号、密码或 RDP
    凭据，真实消息系统接入时也必须保持这个边界。
    """
    environment_id = str(env.id)
    username = assigned_user.username

    def _send_notification():
        try:
            fresh_env = TestEnvironment.objects.get(id=environment_id)
            _safe_send_environment_queue_notification_by_username(
                username,
                '环境已自动分配给你',
                f"环境 {fresh_env.ip_address} 已由队首自动占用，请及时确认使用。",
                _environment_notification_payload(fresh_env, None, event, True),
            )
        except Exception:
            logger.exception('environment auto occupied notification failed environment_id=%s username=%s', environment_id, username)

    transaction.on_commit(_send_notification)


def _device_type_path(device_type: EnvironmentDeviceType | None) -> str:
    """把设备类型向上追溯为路径，用于列表 Tag 展示和级联选项文案。"""
    if not device_type:
        return ''
    names = []
    current = device_type
    visited = set()
    while current and current.id not in visited:
        visited.add(current.id)
        names.append(current.name)
        current = current.parent
    return ' / '.join(reversed(names))


def serialize_device(device: EnvironmentTestDevice) -> dict:
    type_path = _device_type_path(device.device_type)
    return {
        'id': str(device.id),
        'device_type_id': str(device.device_type_id),
        'device_type_name': device.device_type.name,
        'device_type_path': type_path,
        'name': device.name,
        'display_name': f'{type_path} / {device.name}' if type_path else device.name,
        'sort': device.sort,
        'is_active': device.is_active,
        'remark': device.remark or '',
        'sys_create_datetime': device.sys_create_datetime,
        'sys_update_datetime': device.sys_update_datetime,
    }


def _serialize_environment_device_binding(binding: EnvironmentDeviceBinding) -> dict:
    """序列化环境拥有的测试外设实例；主数据来自测试设备，资产编号和备注来自环境绑定。"""
    test_device = getattr(binding, 'test_device', None)
    device_type = test_device.device_type if test_device else binding.device_type
    type_path = _device_type_path(device_type)
    device_name = (test_device.name if test_device else binding.device_name) or device_type.name
    return {
        'id': str(binding.id),
        'device_id': str(test_device.id) if test_device else None,
        'device_type_id': str(device_type.id),
        'device_type_name': device_type.name,
        'device_type_path': type_path,
        'device_name': device_name,
        'name': device_name,
        'display_name': device_name,
        'asset_number': binding.asset_number or '',
        'remark': binding.remark or '',
        'sort': binding.sort,
    }


def _environment_device_bindings(env: TestEnvironment) -> list[EnvironmentDeviceBinding]:
    """读取环境设备实例；若旧数据尚未迁移出 M2M，则兼容转换为展示用实例结构。"""
    prefetched_bindings = getattr(env, '_prefetched_device_bindings', None)
    if prefetched_bindings is not None:
        return list(prefetched_bindings)
    prefetched_cache = getattr(env, '_prefetched_objects_cache', {})
    if 'device_bindings' in prefetched_cache:
        bindings = [row for row in prefetched_cache['device_bindings'] if not row.is_deleted]
        if bindings:
            return sorted(bindings, key=lambda row: (row.sort, row.sys_create_datetime))
    bindings = list(
        env.device_bindings.filter(is_deleted=False)
        .select_related('test_device', 'test_device__device_type', 'test_device__device_type__parent', 'device_type', 'device_type__parent')
        .order_by('sort', 'sys_create_datetime')
    )
    if bindings:
        return bindings
    legacy_devices = list(env.devices.select_related('device_type', 'device_type__parent').all())
    return [
        EnvironmentDeviceBinding(
            id=device.id,
            environment=env,
            test_device=device,
            device_type=device.device_type,
            device_name=device.name,
            asset_number='',
            remark=device.remark or '',
            sort=device.sort,
        )
        for device in legacy_devices
    ]


def serialize_environment(env: TestEnvironment, user: User | None) -> dict:
    """把环境模型转换成前端 DTO；密码只允许写入，不再通过列表或详情接口下发。"""
    roles_can_use = can_use_environment(user)
    favorite_ids = getattr(env, '_favorite_user_ids', None)
    # 列表页会预灌等待队列；用 None 区分“未预取”和“已预取但队列为空”，避免空队列环境额外 N+1 查询。
    prefetched_queue_rows = getattr(env, '_prefetched_waiting_queues', None)
    queue_rows = list(prefetched_queue_rows) if prefetched_queue_rows is not None else None

    if favorite_ids is None and user:
        is_favorite = EnvironmentFavorite.objects.filter(environment=env, user=user).exists()
    else:
        is_favorite = bool(user and str(user.id) in {str(v) for v in (favorite_ids or [])})

    if queue_rows is None:
        queue_rows = list(_waiting_queues(env.id))

    my_queue = next((q for q in queue_rows if user and str(q.user_id) == str(user.id)), None)
    first_queue = queue_rows[0] if queue_rows else None
    devices = [_serialize_environment_device_binding(binding) for binding in _environment_device_bindings(env)]

    return {
        'id': str(env.id),
        'ip_address': env.ip_address,
        'account': env.account or '',
        'can_view_secret': False,
        'can_use_environment': roles_can_use,
        'domain': env.domain,
        'domain_label': dict(TestEnvironment.DOMAIN_CHOICES).get(env.domain, env.domain),
        'category': env.category,
        'category_label': dict(TestEnvironment.CATEGORY_CHOICES).get(env.category, env.category),
        'bomid': env.bomid or '',
        'project_name': env.project_name,
        'vehicle_model': env.vehicle_model,
        'device_ids': [device['device_id'] or device['id'] for device in devices],
        'devices': devices,
        'device_display': '，'.join([device['device_name'] for device in devices]),
        'config_description': env.config_description or '',
        'asset_number': env.asset_number or '',
        'shelf_location': env.shelf_location,
        'remark': env.remark or '',
        'status': env.status,
        'status_label': dict(TestEnvironment.STATUS_CHOICES).get(env.status, env.status),
        'current_user_id': str(env.current_user_id) if env.current_user_id else None,
        'current_user_name': _display_name(env.current_user),
        'is_current_user_occupying': bool(user and env.current_user_id and str(env.current_user_id) == str(user.id)),
        'occupied_at': env.occupied_at,
        'occupied_seconds': _duration_seconds(env.occupied_at) if env.status == 'occupied' else 0,
        'is_favorite': is_favorite,
        'queue_count': len(queue_rows),
        'my_queue_id': str(my_queue.id) if my_queue else None,
        'my_queue_position': my_queue.position if my_queue else None,
        'first_queue_user_name': _display_name(first_queue.user) if first_queue else '',
        'rdp_url': f'rdp://{env.ip_address}',
        # Windows 不默认注册 rdp:// 协议；前端主入口使用项目自定义 focus-rdp://，由一次性安装脚本转发到 mstsc.exe。
        'rdp_launcher_url': f'focus-rdp://open?host={quote(env.ip_address, safe="")}',
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


def _get_active_devices(device_ids: list[str]) -> list[EnvironmentTestDevice]:
    """校验环境绑定的设备 ID，避免前端传入已禁用或不存在的设备。"""
    normalized_ids = [str(item).strip() for item in device_ids if str(item).strip()]
    invalid_type_ids = [item for item in normalized_ids if item.startswith('type:')]
    if invalid_type_ids:
        raise HttpError(400, '测试设备只能选择具体设备，不能选择设备类型')
    if not normalized_ids:
        return []
    devices = list(
        EnvironmentTestDevice.objects.filter(id__in=normalized_ids, is_active=True, is_deleted=False)
        .select_related('device_type')
    )
    if len(devices) != len(set(normalized_ids)):
        raise HttpError(400, '存在无效或已禁用的测试设备')
    return devices


def _get_active_device_types(device_type_ids: list[str]) -> dict[str, EnvironmentDeviceType]:
    """校验环境设备实例使用的类型，禁止绑定不存在、禁用或已删除的类型。"""
    normalized_ids = [str(item).strip() for item in device_type_ids if str(item).strip()]
    if not normalized_ids:
        return {}
    rows = list(EnvironmentDeviceType.objects.filter(id__in=normalized_ids, is_active=True, is_deleted=False))
    if len(rows) != len(set(normalized_ids)):
        raise HttpError(400, '存在无效或已禁用的测试设备类型')
    return {str(row.id): row for row in rows}


def _build_device_binding_rows(devices_payload: list, legacy_device_ids: list[str], user: User | None) -> list[EnvironmentDeviceBinding]:
    """把新旧设备入参统一转换为环境设备实例。

    新前端提交 devices 数组，每一项先选择测试设备主数据，再补充环境内资产编号和备注；
    若旧前端短期仍提交 device_ids，则按旧设备主数据生成实例，给部署升级留出兼容窗口。
    """
    binding_rows: list[EnvironmentDeviceBinding] = []
    if devices_payload:
        payload_rows = [item.dict() if hasattr(item, 'dict') else dict(item) for item in devices_payload]
        device_ids = [row.get('device_id') for row in payload_rows if row.get('device_id')]
        device_map = {str(device.id): device for device in _get_active_devices(device_ids)}
        type_map = _get_active_device_types([row.get('device_type_id', '') for row in payload_rows if not row.get('device_id')])
        for index, row in enumerate(payload_rows):
            device_id = str(row.get('device_id') or '').strip()
            if device_id:
                test_device = device_map[device_id]
                device_type = test_device.device_type
                device_name = test_device.name
            else:
                # 兼容上一版临时前端提交的 device_type_id/device_name；新前端不再走这个分支。
                test_device = None
                device_type_id = str(row.get('device_type_id', '')).strip()
                if not device_type_id:
                    raise HttpError(400, '请选择测试设备')
                device_type = type_map[device_type_id]
                device_name = (row.get('device_name') or '').strip() or device_type.name
            binding_rows.append(
                EnvironmentDeviceBinding(
                    test_device=test_device,
                    device_type=device_type,
                    device_name=device_name,
                    asset_number=(row.get('asset_number') or '').strip(),
                    remark=row.get('remark') or '',
                    sort=row.get('sort', index),
                    sys_creator=user,
                    sys_modifier=user,
                )
            )
        return binding_rows

    for device in _get_active_devices(legacy_device_ids or []):
        binding_rows.append(
            EnvironmentDeviceBinding(
                test_device=device,
                device_type=device.device_type,
                device_name=device.name,
                asset_number='',
                remark=device.remark or '',
                sort=device.sort,
                sys_creator=user,
                sys_modifier=user,
            )
        )
    return binding_rows


def _sync_environment_device_bindings(env: TestEnvironment, binding_rows: list[EnvironmentDeviceBinding], user: User | None):
    """全量保存环境设备实例；环境表单每次提交都是覆盖式编辑。"""
    EnvironmentDeviceBinding.objects.filter(environment=env).delete()
    for row in binding_rows:
        row.environment = env
        row.sys_modifier = user
    EnvironmentDeviceBinding.objects.bulk_create(binding_rows)


def _serialize_device_type_node(device_type: EnvironmentDeviceType, children_map: dict[str | None, list[EnvironmentDeviceType]]) -> dict:
    return {
        'id': str(device_type.id),
        'parent_id': str(device_type.parent_id) if device_type.parent_id else None,
        'name': device_type.name,
        'sort': device_type.sort,
        'is_active': device_type.is_active,
        'children': [
            _serialize_device_type_node(child, children_map)
            for child in children_map.get(device_type.id, [])
        ],
    }


def list_device_type_tree(active_only: bool = False) -> list[dict]:
    """返回测试设备类型树，供管理端左侧树和级联选择器复用。"""
    qs = EnvironmentDeviceType.objects.filter(is_deleted=False).select_related('parent').order_by('sort', 'name')
    if active_only:
        qs = qs.filter(is_active=True)
    rows = list(qs)
    children_map: dict[str | None, list[EnvironmentDeviceType]] = {}
    for row in rows:
        children_map.setdefault(row.parent_id, []).append(row)
    return [_serialize_device_type_node(row, children_map) for row in children_map.get(None, [])]


def create_device_type(user: User, payload: DeviceTypeIn) -> dict:
    """新增测试设备类型；类型支持多级树，但同一父级下名称不能重复。"""
    require_manager(user)
    parent = None
    if payload.parent_id:
        parent = get_object_or_404(EnvironmentDeviceType, id=payload.parent_id, is_deleted=False)
    if EnvironmentDeviceType.objects.filter(parent=parent, name=payload.name.strip(), is_deleted=False).exists():
        raise HttpError(400, '同级下已存在相同设备类型')
    EnvironmentDeviceType.objects.create(
        parent=parent,
        name=payload.name.strip(),
        sort=payload.sort,
        is_active=payload.is_active,
        sys_creator=user,
        sys_modifier=user,
    )
    return list_device_type_tree()


def update_device_type(user: User, type_id: str, payload: DeviceTypeIn) -> dict:
    """更新测试设备类型；禁止把节点挂到自己或自己的后代下面。"""
    require_manager(user)
    device_type = get_object_or_404(EnvironmentDeviceType, id=type_id, is_deleted=False)
    parent = None
    if payload.parent_id:
        if str(payload.parent_id) == str(type_id):
            raise HttpError(400, '父级类型不能选择自己')
        parent = get_object_or_404(EnvironmentDeviceType, id=payload.parent_id, is_deleted=False)
        current = parent
        while current:
            if str(current.id) == str(type_id):
                raise HttpError(400, '父级类型不能选择自己的子级')
            current = current.parent
    duplicate = EnvironmentDeviceType.objects.filter(
        parent=parent,
        name=payload.name.strip(),
        is_deleted=False,
    ).exclude(id=type_id).exists()
    if duplicate:
        raise HttpError(400, '同级下已存在相同设备类型')
    device_type.parent = parent
    device_type.name = payload.name.strip()
    device_type.sort = payload.sort
    device_type.is_active = payload.is_active
    device_type.sys_modifier = user
    device_type.save()
    return list_device_type_tree()


def delete_device_type(user: User, type_id: str) -> bool:
    """删除类型前检查子类型和设备，避免留下孤立设备。"""
    require_manager(user)
    device_type = get_object_or_404(EnvironmentDeviceType, id=type_id, is_deleted=False)
    if EnvironmentDeviceType.objects.filter(parent=device_type, is_deleted=False).exists():
        raise HttpError(400, '该类型下存在子类型，不能删除')
    if EnvironmentTestDevice.objects.filter(device_type=device_type, is_deleted=False).exists():
        raise HttpError(400, '该类型下存在测试设备，不能删除')
    if EnvironmentDeviceBinding.objects.filter(device_type=device_type, environment__is_deleted=False).exists():
        raise HttpError(400, '该类型已被环境使用，请先从环境配置中移除')
    device_type.soft_delete()
    return True


def list_devices(
    device_type_id: str | None = None,
    keyword: str | None = None,
    active_only: bool = False,
    device_type_ids: str | None = None,
    name: str | None = None,
    type_keyword: str | None = None,
    is_active_values: str | None = None,
    remark: str | None = None,
) -> list[dict]:
    """查询测试设备主数据，支持设备管理表头筛选。

    旧的 device_type_id/keyword/active_only 继续兼容；新增字段用于表头筛选，
    多选值同样采用逗号字符串，统一交给 _split_query_values 处理。
    """
    qs = EnvironmentTestDevice.objects.filter(is_deleted=False).select_related('device_type', 'device_type__parent')
    if active_only:
        qs = qs.filter(is_active=True, device_type__is_active=True)
    if device_type_id:
        qs = qs.filter(device_type_id=device_type_id)
    selected_type_ids = _split_query_values(device_type_ids)
    if selected_type_ids:
        qs = qs.filter(device_type_id__in=selected_type_ids)
    if keyword:
        qs = qs.filter(Q(name__icontains=keyword) | Q(remark__icontains=keyword) | Q(device_type__name__icontains=keyword))
    if name:
        qs = qs.filter(name__icontains=name)
    if type_keyword:
        qs = qs.filter(Q(device_type__name__icontains=type_keyword) | Q(device_type__parent__name__icontains=type_keyword))
    active_values = _split_query_values(is_active_values)
    if active_values:
        normalized = {item.lower() for item in active_values}
        bool_values = []
        if normalized & {'true', '1', 'yes'}:
            bool_values.append(True)
        if normalized & {'false', '0', 'no'}:
            bool_values.append(False)
        if bool_values:
            qs = qs.filter(is_active__in=bool_values)
    if remark:
        qs = qs.filter(remark__icontains=remark)
    return [serialize_device(device) for device in qs.order_by('device_type__sort', 'sort', 'name')]


def create_device(user: User, payload: TestDeviceIn) -> dict:
    """在某个设备类型下新增具体测试外设。"""
    require_manager(user)
    device_type = get_object_or_404(EnvironmentDeviceType, id=payload.device_type_id, is_deleted=False)
    if EnvironmentTestDevice.objects.filter(device_type=device_type, name=payload.name.strip(), is_deleted=False).exists():
        raise HttpError(400, '该类型下已存在相同设备名称')
    device = EnvironmentTestDevice.objects.create(
        device_type=device_type,
        name=payload.name.strip(),
        sort=payload.sort,
        is_active=payload.is_active,
        remark=payload.remark or '',
        sys_creator=user,
        sys_modifier=user,
    )
    return serialize_device(device)


def update_device(user: User, device_id: str, payload: TestDeviceIn) -> dict:
    """更新测试设备基础信息，已绑定环境的设备也允许改名以同步展示。"""
    require_manager(user)
    device = get_object_or_404(EnvironmentTestDevice, id=device_id, is_deleted=False)
    device_type = get_object_or_404(EnvironmentDeviceType, id=payload.device_type_id, is_deleted=False)
    duplicate = EnvironmentTestDevice.objects.filter(
        device_type=device_type,
        name=payload.name.strip(),
        is_deleted=False,
    ).exclude(id=device_id).exists()
    if duplicate:
        raise HttpError(400, '该类型下已存在相同设备名称')
    device.device_type = device_type
    device.name = payload.name.strip()
    device.sort = payload.sort
    device.is_active = payload.is_active
    device.remark = payload.remark or ''
    device.sys_modifier = user
    device.save()
    return serialize_device(device)


def delete_device(user: User, device_id: str) -> bool:
    """删除设备前检查环境绑定关系，防止环境列表出现失效引用。"""
    require_manager(user)
    device = get_object_or_404(EnvironmentTestDevice, id=device_id, is_deleted=False)
    if device.environments.filter(is_deleted=False).exists():
        raise HttpError(400, '该测试设备已绑定环境，请先解绑后再删除')
    if EnvironmentDeviceBinding.objects.filter(test_device=device, environment__is_deleted=False).exists():
        raise HttpError(400, '该测试设备已绑定环境，请先解绑后再删除')
    device.soft_delete()
    return True


def list_device_options() -> list[dict]:
    """构造级联多选数据。

    类型节点只承担路径容器职责，不能作为最终绑定值；前端会过滤 type: 前缀，
    后端 _get_active_devices() 也会再次拒绝 type: 值，避免绕过前端提交类型节点。
    """
    type_rows = list(
        EnvironmentDeviceType.objects.filter(is_deleted=False, is_active=True)
        .select_related('parent')
        .order_by('sort', 'name')
    )
    devices = list(
        EnvironmentTestDevice.objects.filter(is_deleted=False, is_active=True, device_type__is_active=True)
        .select_related('device_type')
        .order_by('sort', 'name')
    )
    type_children: dict[str | None, list[EnvironmentDeviceType]] = {}
    for row in type_rows:
        type_children.setdefault(row.parent_id, []).append(row)
    device_children: dict[str, list[EnvironmentTestDevice]] = {}
    for device in devices:
        device_children.setdefault(device.device_type_id, []).append(device)

    def build_type_node(row: EnvironmentDeviceType) -> dict:
        children = [build_type_node(child) for child in type_children.get(row.id, [])]
        children.extend(
            {'value': str(device.id), 'label': device.name, 'disabled': False, 'node_type': 'device', 'children': []}
            for device in device_children.get(row.id, [])
        )
        return {'value': f'type:{row.id}', 'label': row.name, 'disabled': False, 'node_type': 'type', 'children': children}

    return [build_type_node(row) for row in type_children.get(None, [])]


def _split_query_values(value: str | None) -> list[str]:
    """解析前端表头多选筛选值。

    表头筛选统一用逗号字符串提交，避免不同 HTTP 客户端对数组 query 参数序列化
    方式不一致。这里集中做去空格、去空值和去重，后续筛选逻辑只处理干净列表。
    """
    if not value:
        return []
    result: list[str] = []
    seen = set()
    for item in str(value).split(','):
        normalized = item.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _option(label: str, value: str) -> dict:
    """构造前端筛选下拉项，保持所有选项结构一致。"""
    return {'label': label, 'value': value}


def list_filter_options(user: User) -> dict:
    """聚合环境管理表头筛选选项。

    下拉选项来自未软删的业务数据，避免前端只能按当前页推导选项而导致跨页筛选不完整。
    返回内容不包含账号、密码、RDP 地址等敏感或动作相关字段。
    """
    env_qs = TestEnvironment.objects.filter(is_deleted=False)
    device_qs = EnvironmentTestDevice.objects.filter(is_deleted=False).select_related('device_type', 'device_type__parent')
    binding_qs = EnvironmentDeviceBinding.objects.filter(environment__is_deleted=False, is_deleted=False)
    current_users = (
        env_qs.exclude(current_user__isnull=True)
        .select_related('current_user')
        .order_by('current_user__name', 'current_user__username')
    )

    def distinct_text_options(values):
        return [_option(value, value) for value in sorted({(item or '').strip() for item in values if (item or '').strip()})]

    device_options = []
    seen_device_values = set()
    for device in device_qs.order_by('device_type__sort', 'sort', 'name'):
        label = serialize_device(device)['display_name']
        if device.name not in seen_device_values:
            seen_device_values.add(device.name)
            device_options.append(_option(label, device.name))

    device_type_options = []
    for device_type in EnvironmentDeviceType.objects.filter(is_deleted=False).select_related('parent').order_by('sort', 'name'):
        device_type_options.append(_option(_device_type_path(device_type), str(device_type.id)))

    current_user_options = []
    seen_current_user_ids = set()
    for row in current_users:
        user_id = str(row.current_user_id) if row.current_user_id else ''
        if user_id and user_id not in seen_current_user_ids:
            seen_current_user_ids.add(user_id)
            current_user_options.append(_option(_display_name(row.current_user), user_id))

    return {
        'domains': [_option(label, value) for value, label in TestEnvironment.DOMAIN_CHOICES],
        'categories': [_option(label, value) for value, label in TestEnvironment.CATEGORY_CHOICES],
        'statuses': [_option(label, value) for value, label in TestEnvironment.STATUS_CHOICES],
        'favorite_states': [_option('已收藏', 'favorite'), _option('未收藏', 'not_favorite')],
        'queue_states': [_option('有排队', 'has_queue'), _option('无排队', 'no_queue'), _option('我在排队', 'my_queue')],
        'projects': distinct_text_options(env_qs.values_list('project_name', flat=True)),
        'vehicle_models': distinct_text_options(env_qs.values_list('vehicle_model', flat=True)),
        'device_options': list_device_options(),
        'devices': device_options,
        'current_users': current_user_options,
        'device_types': device_type_options,
        'device_statuses': [_option('启用', 'true'), _option('禁用', 'false')],
        'binding_device_assets': distinct_text_options(binding_qs.values_list('asset_number', flat=True)),
    }


def list_environments(user: User, query: EnvironmentListQuery) -> dict:
    """用户端和管理端共用列表查询；前端能力差异由角色字段和菜单权限控制。"""
    favorite_subquery = EnvironmentFavorite.objects.filter(
        environment_id=OuterRef('pk'),
        user=user,
    )
    qs = (
        TestEnvironment.objects.filter(is_deleted=False)
        .select_related('current_user')
        .prefetch_related('device_bindings__test_device__device_type__parent', 'device_bindings__device_type__parent')
        .annotate(
            waiting_count=Count('queues', filter=Q(queues__status='waiting')),
            is_favorite_sort=Exists(favorite_subquery),
        )
    )
    if query.domain:
        qs = qs.filter(domain=query.domain)
    if query.category:
        qs = qs.filter(category=query.category)
    domains = _split_query_values(query.domains)
    if domains:
        qs = qs.filter(domain__in=domains)
    categories = _split_query_values(query.categories)
    if categories:
        qs = qs.filter(category__in=categories)
    statuses = _split_query_values(query.statuses)
    if statuses:
        qs = qs.filter(status__in=statuses)
    project_names = _split_query_values(query.project_names)
    if project_names:
        # 项目和车型在表头中来自后端聚合选项，使用精确多选，避免把逗号串误当模糊关键词。
        qs = qs.filter(project_name__in=project_names)
    vehicle_models = _split_query_values(query.vehicle_models)
    if vehicle_models:
        qs = qs.filter(vehicle_model__in=vehicle_models)
    device_ids = _split_query_values(query.device_ids)
    if device_ids:
        # 测试设备多选是“同时具备”语义：每追加一次反向关联 filter，
        # Django 会生成独立 JOIN，从而要求同一个环境存在每一个被选中的设备绑定。
        for device_id in device_ids:
            qs = qs.filter(device_bindings__test_device_id=device_id)
    device_names = _split_query_values(query.device_names)
    if device_names:
        qs = qs.filter(Q(device_bindings__device_name__in=device_names) | Q(device_bindings__test_device__name__in=device_names))
    current_user_ids = _split_query_values(query.current_user_ids)
    if current_user_ids:
        qs = qs.filter(current_user_id__in=current_user_ids)
    if query.project_name:
        qs = qs.filter(project_name__icontains=query.project_name)
    if query.vehicle_model:
        qs = qs.filter(vehicle_model__icontains=query.vehicle_model)
    if query.ip_address:
        qs = qs.filter(ip_address__icontains=query.ip_address)
    if query.account:
        qs = qs.filter(account__icontains=query.account)
    if query.bomid:
        qs = qs.filter(bomid__icontains=query.bomid)
    if query.device_keyword:
        qs = qs.filter(
            Q(device_bindings__device_name__icontains=query.device_keyword)
            | Q(device_bindings__test_device__name__icontains=query.device_keyword)
            | Q(device_bindings__device_type__name__icontains=query.device_keyword)
            | Q(device_bindings__test_device__device_type__name__icontains=query.device_keyword)
        )
    if query.current_user_name:
        qs = qs.filter(Q(current_user__name__icontains=query.current_user_name) | Q(current_user__username__icontains=query.current_user_name))
    if query.asset_number:
        qs = qs.filter(asset_number__icontains=query.asset_number)
    if query.config_description:
        qs = qs.filter(config_description__icontains=query.config_description)
    if query.remark:
        qs = qs.filter(remark__icontains=query.remark)
    if query.shelf_location:
        qs = qs.filter(shelf_location__icontains=query.shelf_location)
    if query.updated_start:
        qs = qs.filter(sys_update_datetime__gte=query.updated_start)
    if query.updated_end:
        qs = qs.filter(sys_update_datetime__lte=query.updated_end)
    if query.keyword:
        qs = qs.filter(
            Q(ip_address__icontains=query.keyword)
            | Q(bomid__icontains=query.keyword)
            | Q(asset_number__icontains=query.keyword)
            | Q(project_name__icontains=query.keyword)
            | Q(vehicle_model__icontains=query.keyword)
            | Q(device_bindings__device_name__icontains=query.keyword)
            | Q(device_bindings__test_device__name__icontains=query.keyword)
            | Q(device_bindings__asset_number__icontains=query.keyword)
            | Q(device_bindings__remark__icontains=query.keyword)
            | Q(device_bindings__device_type__name__icontains=query.keyword)
            | Q(device_bindings__test_device__device_type__name__icontains=query.keyword)
            | Q(config_description__icontains=query.keyword)
            | Q(shelf_location__icontains=query.keyword)
            | Q(remark__icontains=query.keyword)
        )
    if query.favorite_only:
        qs = qs.filter(favorites__user=user)
    favorite_states = _split_query_values(query.favorite_state)
    if 'favorite' in favorite_states and 'not_favorite' not in favorite_states:
        qs = qs.filter(favorites__user=user)
    elif 'not_favorite' in favorite_states and 'favorite' not in favorite_states:
        qs = qs.exclude(favorites__user=user)
    queue_states = _split_query_values(query.queue_state)
    if 'has_queue' in queue_states and 'no_queue' not in queue_states:
        qs = qs.filter(waiting_count__gt=0)
    elif 'no_queue' in queue_states and 'has_queue' not in queue_states:
        qs = qs.filter(waiting_count=0)
    if 'my_queue' in queue_states:
        qs = qs.filter(queues__user=user, queues__status='waiting')

    favorite_env_ids = set(
        EnvironmentFavorite.objects.filter(user=user).values_list('environment_id', flat=True)
    )
    total = qs.distinct().count()
    start = max(query.page - 1, 0) * query.pageSize
    # 收藏置顶必须发生在数据库分页之前，否则生产数据量大时只会在当前页内置顶。
    # status 目前只有 idle/occupied，按字符串升序即可实现空闲优先，再回到模块原有排序。
    rows = list(qs.distinct().order_by('-is_favorite_sort', 'status', '-sort', 'ip_address')[start : start + query.pageSize])
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

    serialized = []
    for env in rows:
        env._favorite_user_ids = [str(user.id)] if env.id in favorite_env_ids else []
        env._prefetched_waiting_queues = waiting_map.get(env.id, [])
        serialized.append(serialize_environment(env, user))
    return {'items': serialized, 'total': total, 'page': query.page, 'limit': query.pageSize}


def create_environment(user: User, payload: EnvironmentIn) -> dict:
    """创建环境配置，密码一进入服务层就加密，避免明文落库。"""
    require_manager(user)
    data = payload.dict()
    password = data.pop('password', None)
    devices_payload = data.pop('devices', [])
    device_ids = data.pop('device_ids', [])
    binding_rows = _build_device_binding_rows(devices_payload, device_ids, user)
    env = TestEnvironment.objects.create(
        **data,
        password_encrypted=encrypt_value(password or ''),
        sys_creator=user,
        sys_modifier=user,
    )
    _sync_environment_device_bindings(env, binding_rows, user)
    _record(env, user, 'admin_update', '创建环境配置')
    return serialize_environment(env, user)


def update_environment(user: User, environment_id: str, payload: EnvironmentIn) -> dict:
    """更新环境配置；编辑时 password 为空字符串表示清空，None 表示不修改。"""
    require_manager(user)
    env = get_object_or_404(TestEnvironment, id=environment_id, is_deleted=False)
    data = payload.dict()
    password = data.pop('password', None)
    devices_payload = data.pop('devices', [])
    device_ids = data.pop('device_ids', [])
    binding_rows = _build_device_binding_rows(devices_payload, device_ids, user)
    for field, value in data.items():
        setattr(env, field, value)
    if password is not None:
        env.password_encrypted = encrypt_value(password)
    env.sys_modifier = user
    env.save()
    _sync_environment_device_bindings(env, binding_rows, user)
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
    """收藏是环境用户的个人视图偏好；平台默认用户在权限层保持只读。"""
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
        waiting = list(_waiting_queues_for_update(env.id).select_for_update())
        if waiting and str(waiting[0].user_id) != str(user.id):
            queue_user = User.objects.filter(id=waiting[0].user_id).first()
            raise HttpError(400, f'当前队首为 {_display_name(queue_user)}，暂不能占用')
        before_queue_snapshot = _queue_notification_snapshot(env.id)

        # 只有环境空闲且无他人排在前面时才直接占用；如果本人是队首，占用成功后关闭自己的等待记录。
        env.status = 'occupied'
        env.current_user = user
        env.occupied_at = timezone.now()
        env.sys_modifier = user
        env.save(update_fields=['status', 'current_user', 'occupied_at', 'sys_modifier', 'sys_update_datetime'])
        EnvironmentQueue.objects.filter(environment=env, user=user, status='waiting').update(status='done')
        _renumber_waiting_queue(env.id)
        _record(env, user, 'occupy', '占用环境', started_at=env.occupied_at)
        _notify_queue_changes_after_commit(env, before_queue_snapshot, 'occupy', notify_available_head=False)
    return {'success': True, 'message': '占用成功，可以打开 RDP', 'environment': serialize_environment(env, user)}


def release_environment(user: User, environment_id: str) -> dict:
    """释放环境；如果存在等待队列，立即自动转交给队首用户。

    手动释放代表当前使用人已经明确交还环境，此时继续让队首手动刷新再占用会造成资源空档。
    因此本函数在同一事务中完成“释放旧占用 + 队首自动占用 + 剩余队列重排”，保证前端刷新
    后看到的是稳定的新占用状态。
    """
    if not can_use_environment(user):
        raise HttpError(403, '只有环境用户或环境管理员可以释放环境')
    with transaction.atomic():
        env = TestEnvironment.objects.select_for_update().select_related('current_user').get(id=environment_id, is_deleted=False)
        if env.status != 'occupied' or not env.current_user_id:
            raise HttpError(400, '环境当前未被占用')
        if str(env.current_user_id) != str(user.id) and not can_manage(user):
            raise HttpError(403, '只有当前占用人或环境管理员可以释放')
        before_queue_snapshot = _queue_notification_snapshot(env.id)
        started_at = env.occupied_at
        ended_at = timezone.now()
        duration = _duration_seconds(started_at, ended_at)
        released_user = _display_name(env.current_user)
        waiting = list(_waiting_queues_for_update(env.id).select_for_update())
        first_queue = waiting[0] if waiting else None
        assigned_user = User.objects.filter(id=first_queue.user_id).first() if first_queue else None

        if assigned_user:
            # 有等待队列时直接转交队首：队首的 waiting 记录完成，剩余队列重新编号。
            # sys_modifier 记录触发释放动作的人，实际占用人通过 current_user 与 occupy 记录表达。
            env.status = 'occupied'
            env.current_user = assigned_user
            env.occupied_at = ended_at
            env.sys_modifier = user
            env.save(update_fields=['status', 'current_user', 'occupied_at', 'sys_modifier', 'sys_update_datetime'])
            first_queue.status = 'done'
            first_queue.sys_modifier = user
            first_queue.save(update_fields=['status', 'sys_modifier', 'sys_update_datetime'])
            _renumber_waiting_queue(env.id)
            message = f'{released_user} 释放环境，已自动转交给队首用户 { _display_name(assigned_user) }'
            _record(env, user, 'release', message, started_at=started_at, ended_at=ended_at, duration_seconds=duration)
            _record(env, assigned_user, 'occupy', '释放后自动占用环境', started_at=ended_at)
            _notify_auto_occupied_after_commit(env, assigned_user, 'release_auto_transfer')
            _notify_queue_changes_after_commit(env, before_queue_snapshot, 'release_auto_transfer', notify_available_head=False)
        else:
            env.status = 'idle'
            env.current_user = None
            env.occupied_at = None
            env.sys_modifier = user
            env.save(update_fields=['status', 'current_user', 'occupied_at', 'sys_modifier', 'sys_update_datetime'])
            message = f'{released_user} 释放环境'
            _record(env, user, 'release', message, started_at=started_at, ended_at=ended_at, duration_seconds=duration)
    return {'success': True, 'message': message, 'environment': serialize_environment(env, user)}


def auto_release_all_occupied_environments() -> dict:
    """自动释放全部占用环境，并清理历史等待队列。

    该函数供每日凌晨定时任务调用，目标是把第二天的环境使用状态归零。和手动释放不同，
    定时释放发生在无人确认的时间点，因此只释放占用、取消旧 waiting 队列，不做自动转交，
    也不发送队列位置变化通知，避免凌晨给用户推送无意义消息。
    """
    released_environment_ids: list[str] = []
    cancelled_queue_count = 0
    with transaction.atomic():
        environments = list(
            TestEnvironment.objects.select_for_update()
            .select_related('current_user')
            .filter(is_deleted=False, status='occupied', current_user__isnull=False)
            .order_by('ip_address')
        )
        for env in environments:
            started_at = env.occupied_at
            ended_at = timezone.now()
            duration = _duration_seconds(started_at, ended_at)
            released_user = _display_name(env.current_user) or '未知用户'

            env.status = 'idle'
            env.current_user = None
            env.occupied_at = None
            env.sys_modifier = None
            env.save(update_fields=['status', 'current_user', 'occupied_at', 'sys_modifier', 'sys_update_datetime'])

            # 定时任务清理的是隔夜排队意图，采用 cancelled 保留审计痕迹，不物理删除队列数据。
            queue_cancelled = EnvironmentQueue.objects.filter(environment=env, status='waiting').update(
                status='cancelled',
                sys_modifier=None,
                sys_update_datetime=ended_at,
            )
            cancelled_queue_count += queue_cancelled
            message = f'系统自动释放环境，原占用人 {released_user}，已清理等待队列 {queue_cancelled} 人'
            _record(
                env,
                None,
                'auto_release',
                message,
                started_at=started_at,
                ended_at=ended_at,
                duration_seconds=duration,
            )
            released_environment_ids.append(str(env.id))

    return {
        'released_count': len(released_environment_ids),
        'environment_ids': released_environment_ids,
        'cancelled_queue_count': cancelled_queue_count,
    }


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
        waiting = list(_waiting_queues_for_update(env.id).select_for_update())
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
        before_queue_snapshot = _queue_notification_snapshot(env.id)
        queue.status = 'cancelled'
        queue.sys_modifier = user
        queue.save(update_fields=['status', 'sys_modifier', 'sys_update_datetime'])
        _renumber_waiting_queue(env.id)
        _record(env, user, 'cancel_queue', '取消排队')
        _notify_queue_changes_after_commit(env, before_queue_snapshot, 'cancel_queue', notify_available_head=True)
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


def _serialize_announcement(row: EnvironmentAnnouncement | None) -> dict:
    return {
        'id': str(row.id) if row else None,
        'title': row.title if row else '',
        'content_html': row.content_html if row else '',
        'enabled': row.enabled if row else False,
        'updated_at': row.sys_update_datetime if row else None,
    }


def get_announcement() -> dict:
    """读取环境操作公告；没有配置时返回禁用空公告，方便前端直接判断 enabled。"""
    row = EnvironmentAnnouncement.objects.filter(is_deleted=False).order_by('-sys_update_datetime').first()
    return _serialize_announcement(row)


def save_announcement(user: User, payload: EnvironmentAnnouncementIn) -> dict:
    """保存环境操作公告。

    本模块只保留一份当前公告配置，管理员反复编辑同一条记录，避免用户端弹出多条公告造成干扰。
    """
    require_manager(user)
    row = EnvironmentAnnouncement.objects.filter(is_deleted=False).order_by('-sys_update_datetime').first()
    if not row:
        row = EnvironmentAnnouncement(sys_creator=user)
    row.title = (payload.title or '').strip()
    row.content_html = payload.content_html or ''
    row.enabled = payload.enabled
    row.sys_modifier = user
    row.save()
    return _serialize_announcement(row)
