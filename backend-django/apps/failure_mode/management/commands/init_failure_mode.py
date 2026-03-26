from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db.models import Q

from core.menu.menu_model import Menu
from core.permission.permission_model import Permission
from core.user.user_model import User
from common.fu_cache import MenuCacheManager, PermissionCacheManager

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
    component: str
    menu_type: str = 'menu'
    order: int = 0
    auth_code: str | None = None
    icon: str | None = None
    hide_in_menu: bool = False
    hide_children_in_menu: bool = False
    keep_alive: bool = True


LEGACY_MENU_PATHS = ['/project-manager/failure-mode']
LEGACY_MENU_COMPONENTS = ['/failure-mode/index', '/project-manager/failure-mode/index']
LEGACY_API_PREFIX = '/api/project-manager/failure-mode'
TARGET_API_PREFIX = '/api/failure-mode'

MENU_SEEDS = [
    MenuSeed(
        key='failure_mode',
        parent_key=None,
        name='FailureMode',
        title='故障管理',
        path='/failure-mode',
        component='/failure-mode/index',
        menu_type='menu',
        order=55,
        auth_code='failure-mode',
        icon='lucide:shield-alert',
        hide_in_menu=False,
        keep_alive=True,
    ),
]

PERMISSION_SEEDS = {
    'failure_mode': [
        {'name': '查看故障管理页面', 'code': 'failure-mode:view', 'permission_type': 0},
        {'name': '新增故障模式', 'code': 'failure-mode:create', 'permission_type': 0},
        {'name': '编辑故障模式', 'code': 'failure-mode:update', 'permission_type': 0},
        {'name': '删除故障模式', 'code': 'failure-mode:delete', 'permission_type': 0},
        {'name': '获取故障管理字典选项', 'code': 'failure-mode:api:dict-options', 'permission_type': 1, 'api_path': '/api/failure-mode/dict-options', 'http_method': 'GET'},
        {'name': '获取故障模式列表', 'code': 'failure-mode:api:list', 'permission_type': 1, 'api_path': '/api/failure-mode/failure-modes', 'http_method': 'GET'},
        {'name': '创建故障模式', 'code': 'failure-mode:api:create', 'permission_type': 1, 'api_path': '/api/failure-mode/failure-modes', 'http_method': 'POST'},
        {'name': '更新故障模式', 'code': 'failure-mode:api:update', 'permission_type': 1, 'api_path': '/api/failure-mode/failure-modes/{failure_mode_id}', 'http_method': 'PUT'},
        {'name': '删除故障模式', 'code': 'failure-mode:api:delete', 'permission_type': 1, 'api_path': '/api/failure-mode/failure-modes/{failure_mode_id}', 'http_method': 'DELETE'},
        {'name': '获取产线拦截策略列表', 'code': 'failure-mode:api:interception:list', 'permission_type': 1, 'api_path': '/api/failure-mode/interception-strategies', 'http_method': 'GET'},
        {'name': '保存产线拦截策略', 'code': 'failure-mode:api:interception:save', 'permission_type': 1, 'api_path': '/api/failure-mode/interception-strategies', 'http_method': 'POST'},
        {'name': '获取故障处理措施列表', 'code': 'failure-mode:api:measure:list', 'permission_type': 1, 'api_path': '/api/failure-mode/handling-measures', 'http_method': 'GET'},
        {'name': '保存故障处理措施', 'code': 'failure-mode:api:measure:save', 'permission_type': 1, 'api_path': '/api/failure-mode/handling-measures', 'http_method': 'POST'},
        {'name': '获取维测手段列表', 'code': 'failure-mode:api:observation:list', 'permission_type': 1, 'api_path': '/api/failure-mode/observation-methods', 'http_method': 'GET'},
        {'name': '保存维测手段', 'code': 'failure-mode:api:observation:save', 'permission_type': 1, 'api_path': '/api/failure-mode/observation-methods', 'http_method': 'POST'},
        {'name': '获取华佗诊断方案列表', 'code': 'failure-mode:api:huatuo:list', 'permission_type': 1, 'api_path': '/api/failure-mode/huatuo-diagnoses', 'http_method': 'GET'},
        {'name': '保存华佗诊断方案', 'code': 'failure-mode:api:huatuo:save', 'permission_type': 1, 'api_path': '/api/failure-mode/huatuo-diagnoses', 'http_method': 'POST'},
        {'name': '获取测试用例列表', 'code': 'failure-mode:api:test-case:list', 'permission_type': 1, 'api_path': '/api/failure-mode/test-cases', 'http_method': 'GET'},
        {'name': '保存测试用例', 'code': 'failure-mode:api:test-case:save', 'permission_type': 1, 'api_path': '/api/failure-mode/test-cases', 'http_method': 'POST'},
    ],
}


class Command(BaseCommand):
    help = '初始化故障管理模块菜单和权限'

    def handle(self, *args, **options):
        operator = User.objects.filter(is_superuser=True).order_by('sys_create_datetime').first()
        if operator is None:
            self.stdout.write(self.style.ERROR('未找到超级管理员，无法初始化菜单权限'))
            return

        menus = self._seed_menus(operator)
        permission_count = self._seed_permissions(menus, operator)
        self._cleanup_stale_legacy_permissions(menus)
        MenuCacheManager.invalidate_menu_cache()
        PermissionCacheManager.invalidate_permission_cache()
        PermissionCacheManager.invalidate_global_permissions()
        self.stdout.write(
            self.style.SUCCESS(
                f'故障管理模块初始化完成：菜单 {len(menus)} 项，权限 {permission_count} 项。',
            )
        )

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
            menu.icon = seed.icon
            menu.order = seed.order
            menu.hideInMenu = seed.hide_in_menu
            menu.hideChildrenInMenu = seed.hide_children_in_menu
            menu.keepAlive = seed.keep_alive
            menu.sys_modifier = operator
            menu.save()
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
        Permission.objects.filter(menu=legacy_menu).update(menu=target_menu)

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

    def _build_legacy_permission_code(self, code: str):
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
