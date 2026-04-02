from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db.models import Q

from common.fu_cache import MenuCacheManager, PermissionCacheManager
from core.menu.menu_model import Menu
from core.permission.permission_model import Permission
from core.user.user_model import User

HTTP_METHOD_MAP = {
    'GET': 0,
    'POST': 1,
    'PUT': 2,
    'DELETE': 3,
    'PATCH': 4,
    'ALL': 5,
}


@dataclass(frozen=True)
class MenuSeed:
    key: str
    parent_key: str | None
    name: str
    title: str
    path: str
    component: str | None
    menu_type: str = 'menu'
    order: int = 0
    auth_code: str | None = None
    icon: str | None = None
    active_path: str | None = None
    hide_in_menu: bool = False
    hide_children_in_menu: bool = False
    keep_alive: bool = True
    redirect: str | None = None
    inherit_parent_roles: bool = False
    inherit_roles_from: str | None = None


LEGACY_MENU_PATHS = ['/project-manager/failure-mode']
LEGACY_MENU_COMPONENTS = [
    '/failure-mode/index',
    '/project-manager/failure-mode/index',
    '/failure-mode/workflow/tasks/index',
    '/failure-mode/workflow/products/index',
]
OBSOLETE_MENU_REDIRECTS = {
    '/failure-mode/workflow/tasks': '/failure-mode/tasks',
    '/failure-mode/workflow/products': '/failure-mode/products/baselines',
    '/failure-mode/roles': '/failure-mode/config/roles',
}
LEGACY_API_PREFIX = '/api/project-manager/failure-mode'
TARGET_API_PREFIX = '/api/failure-mode'

MENU_SEEDS = [
    MenuSeed(
        key='failure_mode',
        parent_key=None,
        name='FailureModeCatalog',
        title='故障管理',
        path='/failure-mode',
        component=None,
        menu_type='catalog',
        order=55,
        auth_code='failure-mode',
        icon='lucide:shield-alert',
        hide_in_menu=False,
        keep_alive=True,
        redirect='/failure-mode/index',
    ),
    MenuSeed(
        key='failure_mode_index',
        parent_key='failure_mode',
        name='FailureModeIndex',
        title='故障模式数据',
        path='/failure-mode/index',
        component='/failure-mode/index',
        menu_type='menu',
        order=1,
        auth_code='failure-mode',
        icon='lucide:database',
        hide_in_menu=False,
        keep_alive=True,
    ),
    MenuSeed(
        key='failure_mode_statistics',
        parent_key='failure_mode',
        name='FailureModeStatistics',
        title='故障管理统计',
        path='/failure-mode/statistics',
        component='/failure-mode/statistics/index',
        menu_type='menu',
        order=2,
        auth_code='failure-mode:statistics',
        icon='lucide:chart-column-big',
        hide_in_menu=False,
        keep_alive=True,
    ),
    MenuSeed(
        key='failure_mode_workflow_tasks',
        parent_key='failure_mode',
        name='FailureModeTasks',
        title='任务管理',
        path='/failure-mode/tasks',
        component='/failure-mode/tasks/index',
        menu_type='menu',
        order=3,
        auth_code='failure-mode:workflow-tasks',
        icon='lucide:list-todo',
        hide_in_menu=False,
        keep_alive=True,
    ),
    MenuSeed(
        key='failure_mode_workflow_task_detail',
        parent_key='failure_mode',
        name='FailureModeTaskDetail',
        title='任务详情',
        path='/failure-mode/tasks/detail/:id',
        component='/failure-mode/tasks/detail',
        menu_type='menu',
        order=90,
        auth_code='failure-mode:workflow-tasks',
        active_path='/failure-mode/tasks',
        hide_in_menu=True,
        keep_alive=False,
        inherit_parent_roles=False,
        inherit_roles_from='failure_mode_workflow_tasks',
    ),
    MenuSeed(
        key='failure_mode_workflow_products',
        parent_key='failure_mode',
        name='FailureModeProductBaselines',
        title='产品基线',
        path='/failure-mode/products/baselines',
        component='/failure-mode/products/baselines/index',
        menu_type='menu',
        order=4,
        auth_code='failure-mode:workflow-products',
        icon='lucide:package-check',
        hide_in_menu=False,
        keep_alive=True,
    ),
    MenuSeed(
        key='failure_mode_config',
        parent_key='failure_mode',
        name='FailureModeConfigCatalog',
        title='配置管理',
        path='/failure-mode/config',
        component=None,
        menu_type='catalog',
        order=5,
        auth_code='failure-mode',
        icon='lucide:settings-2',
        hide_in_menu=False,
        keep_alive=True,
        redirect='/failure-mode/config/subsystems',
    ),
    MenuSeed(
        key='failure_mode_subsystems',
        parent_key='failure_mode_config',
        name='FailureModeSubsystemConfig',
        title='子系统配置',
        path='/failure-mode/config/subsystems',
        component='/failure-mode/config/subsystems/index',
        menu_type='menu',
        order=1,
        auth_code='failure-mode',
        icon='lucide:blocks',
        hide_in_menu=False,
        keep_alive=True,
    ),
    MenuSeed(
        key='failure_mode_roles',
        parent_key='failure_mode_config',
        name='FailureModeRoles',
        title='角色配置',
        path='/failure-mode/config/roles',
        component='/failure-mode/roles/index',
        menu_type='menu',
        order=2,
        auth_code='failure-mode:roles',
        icon='lucide:shield-check',
        hide_in_menu=False,
        keep_alive=True,
    ),
    MenuSeed(
        key='failure_mode_roles_detail',
        parent_key='failure_mode_config',
        name='FailureModeRoleDetail',
        title='角色配置详情',
        path='/failure-mode/config/roles/detail/:id',
        component='/failure-mode/roles/detail',
        menu_type='menu',
        order=91,
        auth_code='failure-mode:roles',
        active_path='/failure-mode/config/roles',
        hide_in_menu=True,
        keep_alive=False,
        inherit_parent_roles=False,
        inherit_roles_from='failure_mode_roles',
    ),
]

PERMISSION_SEEDS = {
    'failure_mode': [
        {'name': '查看故障管理页面', 'code': 'failure-mode:view', 'permission_type': 0},
        {'name': '新增故障模式', 'code': 'failure-mode:create', 'permission_type': 0},
        {'name': '编辑故障模式', 'code': 'failure-mode:update', 'permission_type': 0},
        {'name': '删除故障模式', 'code': 'failure-mode:delete', 'permission_type': 0},
        {'name': '获取故障管理字典选项', 'code': 'failure-mode:api:dict-options', 'permission_type': 1, 'api_path': '/api/failure-mode/dict-options', 'http_method': 'GET'},
        {'name': '获取故障模式列表', 'code': 'failure-mode:api:list', 'permission_type': 1, 'api_path': '/api/failure-mode/failure-modes/search', 'http_method': 'POST'},
        {'name': '创建故障模式', 'code': 'failure-mode:api:create', 'permission_type': 1, 'api_path': '/api/failure-mode/failure-modes', 'http_method': 'POST'},
        {'name': '获取故障模式详情', 'code': 'failure-mode:api:detail', 'permission_type': 1, 'api_path': '/api/failure-mode/failure-modes/{failure_mode_id}', 'http_method': 'GET'},
        {'name': '获取故障模式洞察', 'code': 'failure-mode:api:insight', 'permission_type': 1, 'api_path': '/api/failure-mode/failure-modes/{failure_mode_id}/insight', 'http_method': 'GET'},
        {'name': '更新故障模式', 'code': 'failure-mode:api:update', 'permission_type': 1, 'api_path': '/api/failure-mode/failure-modes/{failure_mode_id}', 'http_method': 'PUT'},
        {'name': '删除故障模式', 'code': 'failure-mode:api:delete', 'permission_type': 1, 'api_path': '/api/failure-mode/failure-modes/{failure_mode_id}', 'http_method': 'DELETE'},
        {'name': '获取产线拦截策略列表', 'code': 'failure-mode:api:interception:list', 'permission_type': 1, 'api_path': '/api/failure-mode/interception-strategies/search', 'http_method': 'POST'},
        {'name': '保存产线拦截策略', 'code': 'failure-mode:api:interception:save', 'permission_type': 1, 'api_path': '/api/failure-mode/interception-strategies', 'http_method': 'POST'},
        {'name': '获取产线拦截策略洞察', 'code': 'failure-mode:api:interception:insight', 'permission_type': 1, 'api_path': '/api/failure-mode/interception-strategies/{item_id}/insight', 'http_method': 'GET'},
        {'name': '获取故障处理措施列表', 'code': 'failure-mode:api:measure:list', 'permission_type': 1, 'api_path': '/api/failure-mode/handling-measures/search', 'http_method': 'POST'},
        {'name': '保存故障处理措施', 'code': 'failure-mode:api:measure:save', 'permission_type': 1, 'api_path': '/api/failure-mode/handling-measures', 'http_method': 'POST'},
        {'name': '获取维测手段列表', 'code': 'failure-mode:api:observation:list', 'permission_type': 1, 'api_path': '/api/failure-mode/observation-methods/search', 'http_method': 'POST'},
        {'name': '保存维测手段', 'code': 'failure-mode:api:observation:save', 'permission_type': 1, 'api_path': '/api/failure-mode/observation-methods', 'http_method': 'POST'},
        {'name': '获取华佗诊断方案列表', 'code': 'failure-mode:api:huatuo:list', 'permission_type': 1, 'api_path': '/api/failure-mode/huatuo-diagnoses/search', 'http_method': 'POST'},
        {'name': '保存华佗诊断方案', 'code': 'failure-mode:api:huatuo:save', 'permission_type': 1, 'api_path': '/api/failure-mode/huatuo-diagnoses', 'http_method': 'POST'},
        {'name': '获取测试用例列表', 'code': 'failure-mode:api:test-case:list', 'permission_type': 1, 'api_path': '/api/failure-mode/test-cases/search', 'http_method': 'POST'},
        {'name': '保存测试用例', 'code': 'failure-mode:api:test-case:save', 'permission_type': 1, 'api_path': '/api/failure-mode/test-cases', 'http_method': 'POST'},
        {'name': '获取子系统配置列表', 'code': 'failure-mode:api:subsystem-config:list', 'permission_type': 1, 'api_path': '/api/failure-mode/subsystem-configs/search', 'http_method': 'POST'},
        {'name': '创建子系统配置', 'code': 'failure-mode:api:subsystem-config:create', 'permission_type': 1, 'api_path': '/api/failure-mode/subsystem-configs', 'http_method': 'POST'},
        {'name': '获取子系统配置详情', 'code': 'failure-mode:api:subsystem-config:detail', 'permission_type': 1, 'api_path': '/api/failure-mode/subsystem-configs/{item_id}', 'http_method': 'GET'},
        {'name': '更新子系统配置', 'code': 'failure-mode:api:subsystem-config:update', 'permission_type': 1, 'api_path': '/api/failure-mode/subsystem-configs/{item_id}', 'http_method': 'PUT'},
        {'name': '删除子系统配置', 'code': 'failure-mode:api:subsystem-config:delete', 'permission_type': 1, 'api_path': '/api/failure-mode/subsystem-configs/{item_id}', 'http_method': 'DELETE'},
        {'name': '获取子系统联动选项', 'code': 'failure-mode:api:subsystem-config:options', 'permission_type': 1, 'api_path': '/api/failure-mode/subsystem-configs/options', 'http_method': 'GET'},
    ],
    'failure_mode_statistics': [
        {'name': '查看故障管理统计页面', 'code': 'failure-mode:statistics:view', 'permission_type': 0},
        {'name': '获取故障管理统计摘要', 'code': 'failure-mode:statistics:api:summary', 'permission_type': 1, 'api_path': '/api/failure-mode/statistics/summary', 'http_method': 'POST'},
        {'name': '获取故障管理子系统统计表', 'code': 'failure-mode:statistics:api:subsystems', 'permission_type': 1, 'api_path': '/api/failure-mode/statistics/subsystems/search', 'http_method': 'POST'},
    ],
    'failure_mode_workflow_tasks': [
        {'name': '查看故障工作流任务', 'code': 'failure-mode:workflow-tasks:view', 'permission_type': 0},
        {'name': '任务工作流相关接口', 'code': 'failure-mode:workflow-tasks:api', 'permission_type': 1, 'api_path': '/api/failure-mode/workflow/tasks*', 'http_method': 'ALL'},
    ],
    'failure_mode_workflow_products': [
        {'name': '查看产品基线', 'code': 'failure-mode:workflow-products:view', 'permission_type': 0},
        {'name': '产品基线相关接口', 'code': 'failure-mode:workflow-products:api', 'permission_type': 1, 'api_path': '/api/failure-mode/workflow/products*', 'http_method': 'ALL'},
    ],
    'failure_mode_roles': [
        {'name': '查看角色配置页面', 'code': 'failure-mode:roles:view', 'permission_type': 0},
    ],
    'failure_mode_roles_detail': [
        {'name': '查看角色配置详情', 'code': 'failure-mode:roles:detail:view', 'permission_type': 0},
    ],
    'failure_mode_workflow_task_detail': [
        {'name': '查看任务详情', 'code': 'failure-mode:workflow-tasks:detail:view', 'permission_type': 0},
    ],
}


class Command(BaseCommand):
    help = '初始化故障管理模块菜单和权限'

    def handle(self, *args, **options):
        operator = User.objects.filter(is_superuser=True).order_by('sys_create_datetime').first()
        if operator is None:
            self.stdout.write(self.style.ERROR('未找到超级管理员，无法初始化菜单权限'))
            return

        snapshots = self._snapshot_relations_before_reset()
        self._reset_failure_mode_tree()
        menus = self._seed_menus(operator)
        permission_count = self._seed_permissions(menus, operator)
        self._restore_relations_after_reset(menus, snapshots)
        MenuCacheManager.invalidate_menu_cache()
        PermissionCacheManager.invalidate_permission_cache()
        PermissionCacheManager.invalidate_global_permissions()
        self.stdout.write(
            self.style.SUCCESS(
                f'故障管理模块初始化完成：菜单 {len(menus)} 项，权限 {permission_count} 项。',
            )
        )

    def _seed_permission_rows(self):
        for items in PERMISSION_SEEDS.values():
            for item in items:
                yield item

    def _normalize_menu_path(self, path: str | None):
        path = path or ''
        if path in LEGACY_MENU_PATHS:
            return '/failure-mode'
        if path in OBSOLETE_MENU_REDIRECTS:
            return OBSOLETE_MENU_REDIRECTS[path]
        if path.startswith('/failure-mode/roles/detail'):
            return '/failure-mode/config/roles/detail/:id'
        if path.startswith('/failure-mode/roles'):
            return '/failure-mode/config/roles'
        if path.startswith('/failure-mode/workflow/tasks'):
            return '/failure-mode/tasks'
        if path.startswith('/failure-mode/workflow/products'):
            return '/failure-mode/products/baselines'
        return path

    def _normalize_permission_code(self, code: str | None):
        code = (code or '').strip()
        if not code:
            return None
        valid_codes = {item['code'] for item in self._seed_permission_rows()}
        if code in valid_codes:
            return code
        if code.startswith('project_manager:api:failure-mode:statistics:'):
            suffix = code.removeprefix('project_manager:api:failure-mode:statistics:')
            normalized = f'failure-mode:statistics:api:{suffix}'
            return normalized if normalized in valid_codes else None
        if code.startswith('project_manager:failure-mode:statistics:'):
            suffix = code.removeprefix('project_manager:failure-mode:statistics:')
            normalized = f'failure-mode:statistics:{suffix}'
            return normalized if normalized in valid_codes else None
        if code.startswith('project_manager:api:failure-mode:'):
            suffix = code.removeprefix('project_manager:api:failure-mode:')
            normalized = f'failure-mode:api:{suffix}'
            return normalized if normalized in valid_codes else None
        if code.startswith('project_manager:failure-mode:'):
            suffix = code.removeprefix('project_manager:failure-mode:')
            normalized = f'failure-mode:{suffix}'
            return normalized if normalized in valid_codes else None
        return None

    def _snapshot_relations_before_reset(self):
        menu_role_map: dict[str, set[str]] = {}
        permission_role_map: dict[str, set[str]] = {}

        menu_queryset = Menu.objects.filter(
            Q(path__icontains='failure-mode')
            | Q(component__icontains='failure-mode')
            | Q(authCode__startswith='failure-mode')
            | Q(authCode__startswith='project_manager:failure-mode')
        ).prefetch_related('core_roles')

        for menu in menu_queryset:
            normalized_path = self._normalize_menu_path(menu.path)
            if not normalized_path:
                continue
            menu_role_map.setdefault(normalized_path, set()).update(
                menu.core_roles.values_list('id', flat=True)
            )

        permission_queryset = Permission.objects.filter(
            Q(menu__in=menu_queryset)
            | Q(code__startswith='failure-mode')
            | Q(code__startswith='project_manager:failure-mode')
            | Q(code__startswith='project_manager:api:failure-mode')
            | Q(api_path__startswith=TARGET_API_PREFIX)
            | Q(api_path__startswith=LEGACY_API_PREFIX)
        ).prefetch_related('roles')
        for permission in permission_queryset:
            normalized_code = self._normalize_permission_code(permission.code)
            if not normalized_code:
                continue
            permission_role_map.setdefault(normalized_code, set()).update(
                permission.roles.values_list('id', flat=True)
            )

        return {
            'menu_roles': menu_role_map,
            'permission_roles': permission_role_map,
        }

    def _reset_failure_mode_tree(self):
        menu_queryset = Menu.objects.filter(
            Q(path__icontains='failure-mode')
            | Q(component__icontains='failure-mode')
            | Q(authCode__startswith='failure-mode')
            | Q(authCode__startswith='project_manager:failure-mode')
        )
        menu_ids = list(menu_queryset.values_list('id', flat=True))
        Permission.objects.filter(
            Q(menu_id__in=menu_ids)
            | Q(code__startswith='failure-mode')
            | Q(code__startswith='project_manager:failure-mode')
            | Q(code__startswith='project_manager:api:failure-mode')
            | Q(api_path__startswith=TARGET_API_PREFIX)
            | Q(api_path__startswith=LEGACY_API_PREFIX)
        ).delete()
        menu_queryset.delete()

    def _restore_relations_after_reset(self, menus: dict[str, Menu], snapshots: dict[str, dict[str, set[str]]]):
        path_to_menu = {menu.path: menu for menu in menus.values()}
        for path, role_ids in snapshots.get('menu_roles', {}).items():
            menu = path_to_menu.get(path)
            if menu and role_ids:
                menu.core_roles.add(*role_ids)

        seeded_permissions = {
            permission.code: permission
            for permission in Permission.objects.filter(
                menu_id__in=[menu.id for menu in menus.values()]
            )
        }
        for code, role_ids in snapshots.get('permission_roles', {}).items():
            permission = seeded_permissions.get(code)
            if permission and role_ids:
                permission.roles.add(*role_ids)

    def _seed_menus(self, operator: User):
        created: dict[str, Menu] = {}
        for seed in MENU_SEEDS:
            parent = created.get(seed.parent_key) if seed.parent_key else None
            menu = Menu.objects.filter(path=seed.path).first()
            legacy_menu = self._find_legacy_menu(seed)

            if menu and legacy_menu and legacy_menu.id != menu.id:
                self._merge_menu_relations(legacy_menu, menu)
                legacy_menu.delete()
            elif menu is None and legacy_menu is not None:
                menu = legacy_menu
            elif menu is None:
                menu = Menu(path=seed.path, sys_creator=operator)

            menu.parent = parent
            menu.name = seed.name
            menu.title = seed.title
            menu.authCode = seed.auth_code
            menu.path = seed.path
            menu.type = seed.menu_type
            menu.component = seed.component
            if seed.redirect:
                menu.redirect = seed.redirect
            menu.activePath = seed.active_path
            menu.icon = seed.icon
            menu.order = seed.order
            menu.hideInMenu = seed.hide_in_menu
            menu.hideChildrenInMenu = seed.hide_children_in_menu
            menu.keepAlive = seed.keep_alive
            menu.sys_modifier = operator
            menu.save()
            if seed.inherit_parent_roles and parent:
                self._inherit_parent_roles(parent, menu)
            elif seed.inherit_roles_from and seed.inherit_roles_from in created:
                self._inherit_parent_roles(created[seed.inherit_roles_from], menu)
            created[seed.key] = menu
        return created

    def _seed_permissions(self, menus: dict[str, Menu], operator: User) -> int:
        total = 0
        for menu_key, items in PERMISSION_SEEDS.items():
            menu = menus.get(menu_key)
            if not menu:
                continue
            for item in items:
                permission = self._find_permission_candidate(menu, item)
                if permission is None:
                    permission = Permission(menu=menu, code=item['code'], sys_creator=operator)

                permission.menu = menu
                permission.code = item['code']
                permission.name = item['name']
                permission.permission_type = item['permission_type']
                permission.api_path = item.get('api_path') or None
                permission.http_method = HTTP_METHOD_MAP.get(item.get('http_method') or 'GET', 0)
                permission.description = item.get('name')
                permission.is_active = True
                permission.sys_modifier = operator
                permission.save()
                if not permission.roles.exists():
                    role_ids = list(menu.core_roles.values_list('id', flat=True))
                    if role_ids:
                        permission.roles.add(*role_ids)
                total += 1
        return total

    def _find_legacy_menu(self, seed: MenuSeed):
        return (
            Menu.objects.filter(
                Q(path__in=LEGACY_MENU_PATHS)
                | Q(authCode__startswith='project_manager:failure-mode')
                | Q(parent__title='项目管理', path__icontains='failure-mode')
                | Q(parent__title='项目管理', component__in=LEGACY_MENU_COMPONENTS)
            )
            .exclude(path=seed.path)
            .order_by('order', 'sys_create_datetime')
            .first()
        )

    def _merge_menu_relations(self, legacy_menu: Menu, target_menu: Menu):
        for role in legacy_menu.core_roles.all():
            role.menu.add(target_menu)
        Menu.objects.filter(parent=legacy_menu).update(parent=target_menu)
        legacy_permissions = list(Permission.objects.filter(menu=legacy_menu))
        for legacy_permission in legacy_permissions:
            target_permission = (
                Permission.objects.filter(menu=target_menu, code=legacy_permission.code).first()
                or (
                    Permission.objects.filter(
                        menu=target_menu,
                        api_path=legacy_permission.api_path,
                        http_method=legacy_permission.http_method,
                    ).first()
                    if legacy_permission.api_path
                    else None
                )
            )
            if target_permission is not None:
                self._merge_permission_relations(legacy_permission, target_permission)
                continue
            legacy_permission.menu = target_menu
            legacy_permission.save(update_fields=['menu', 'sys_update_datetime'])

    def _inherit_parent_roles(self, parent_menu: Menu, child_menu: Menu):
        for role in parent_menu.core_roles.all():
            role.menu.add(child_menu)

    def _find_permission_candidate(self, menu: Menu, item: dict):
        desired_code = item['code']
        desired_api_path = item.get('api_path') or None
        legacy_code = self._build_legacy_permission_code(desired_code)
        legacy_api_path = self._build_legacy_api_path(desired_api_path)

        existing = Permission.objects.filter(menu=menu, code=desired_code).first()
        if existing is None and legacy_code:
            existing = Permission.objects.filter(menu=menu, code=legacy_code).first()
        if existing is None and desired_api_path:
            existing = Permission.objects.filter(menu=menu, api_path=desired_api_path).first()
        if existing is None and legacy_api_path:
            existing = Permission.objects.filter(menu=menu, api_path=legacy_api_path).first()

        if existing is None:
            return None

        if legacy_code:
            for duplicate in Permission.objects.filter(menu=menu, code=legacy_code).exclude(id=existing.id):
                self._merge_permission_relations(duplicate, existing)
        if legacy_api_path:
            for duplicate in Permission.objects.filter(menu=menu, api_path=legacy_api_path).exclude(id=existing.id):
                self._merge_permission_relations(duplicate, existing)
        for duplicate in Permission.objects.filter(menu=menu, code=desired_code).exclude(id=existing.id):
            self._merge_permission_relations(duplicate, existing)

        return existing

    def _merge_permission_relations(self, legacy_permission: Permission, target_permission: Permission):
        for role in legacy_permission.roles.all():
            role.permission.add(target_permission)
        legacy_permission.delete()

    def _cleanup_stale_legacy_permissions(self, menus: dict[str, Menu]):
        menu_ids = [menu.id for menu in menus.values()]
        Permission.objects.filter(
            menu_id__in=menu_ids,
        ).filter(
            Q(code__startswith='project_manager:')
            | Q(api_path__startswith=LEGACY_API_PREFIX)
        ).delete()

    def _cleanup_obsolete_menus(self, menus: dict[str, Menu]):
        for obsolete_path, target_path in OBSOLETE_MENU_REDIRECTS.items():
            target_menu = Menu.objects.filter(path=target_path).first()
            if target_menu is None:
                continue
            obsolete_menus = Menu.objects.filter(path=obsolete_path).exclude(id=target_menu.id)
            for obsolete_menu in obsolete_menus:
                self._merge_menu_relations(obsolete_menu, target_menu)
                obsolete_menu.delete()

    def _build_legacy_permission_code(self, code: str):
        if code.startswith('failure-mode:statistics:api:'):
            suffix = code.removeprefix('failure-mode:statistics:api:')
            return f'project_manager:api:failure-mode:statistics:{suffix}'
        if code.startswith('failure-mode:statistics:'):
            suffix = code.removeprefix('failure-mode:statistics:')
            return f'project_manager:failure-mode:statistics:{suffix}'
        if code.startswith('failure-mode:api:'):
            suffix = code.removeprefix('failure-mode:api:')
            return f'project_manager:api:failure-mode:{suffix}'
        if code.startswith('failure-mode:'):
            suffix = code.removeprefix('failure-mode:')
            return f'project_manager:failure-mode:{suffix}'
        return None

    def _build_legacy_api_path(self, api_path: str | None):
        if not api_path:
            return None
        if api_path.startswith(TARGET_API_PREFIX):
            return api_path.replace(TARGET_API_PREFIX, LEGACY_API_PREFIX, 1)
        return None
