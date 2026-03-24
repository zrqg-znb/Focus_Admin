from dataclasses import dataclass

from django.core.management.base import BaseCommand

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


MENU_SEEDS = [
    MenuSeed(
        key='project_manager_root',
        parent_key=None,
        name='ProjectManager',
        title='项目管理',
        path='/project-manager',
        component='BasicLayout',
        menu_type='catalog',
        order=60,
        icon='lucide:folder-kanban',
        hide_in_menu=False,
        hide_children_in_menu=False,
        keep_alive=True,
    ),
    MenuSeed(
        key='failure_mode',
        parent_key='project_manager_root',
        name='FailureMode',
        title='故障模式',
        path='/project-manager/failure-mode',
        component='/project-manager/failure-mode/index',
        menu_type='menu',
        order=65,
        auth_code='project_manager:failure-mode',
        icon='lucide:shield-alert',
        hide_in_menu=False,
        keep_alive=True,
    ),
]

PERMISSION_SEEDS = {
    'failure_mode': [
        {'name': '查看故障模式页面', 'code': 'project_manager:failure-mode:view', 'permission_type': 0},
        {'name': '新增故障模式', 'code': 'project_manager:failure-mode:create', 'permission_type': 0},
        {'name': '编辑故障模式', 'code': 'project_manager:failure-mode:update', 'permission_type': 0},
        {'name': '删除故障模式', 'code': 'project_manager:failure-mode:delete', 'permission_type': 0},
        {'name': '获取故障模式字典选项', 'code': 'project_manager:api:failure-mode:dict-options', 'permission_type': 1, 'api_path': '/api/project-manager/failure-mode/dict-options', 'http_method': 'GET'},
        {'name': '获取故障模式列表', 'code': 'project_manager:api:failure-mode:list', 'permission_type': 1, 'api_path': '/api/project-manager/failure-mode/failure-modes', 'http_method': 'GET'},
        {'name': '创建故障模式', 'code': 'project_manager:api:failure-mode:create', 'permission_type': 1, 'api_path': '/api/project-manager/failure-mode/failure-modes', 'http_method': 'POST'},
        {'name': '更新故障模式', 'code': 'project_manager:api:failure-mode:update', 'permission_type': 1, 'api_path': '/api/project-manager/failure-mode/failure-modes/{failure_mode_id}', 'http_method': 'PUT'},
        {'name': '删除故障模式', 'code': 'project_manager:api:failure-mode:delete', 'permission_type': 1, 'api_path': '/api/project-manager/failure-mode/failure-modes/{failure_mode_id}', 'http_method': 'DELETE'},
        {'name': '获取产线拦截策略列表', 'code': 'project_manager:api:failure-mode:interception:list', 'permission_type': 1, 'api_path': '/api/project-manager/failure-mode/interception-strategies', 'http_method': 'GET'},
        {'name': '保存产线拦截策略', 'code': 'project_manager:api:failure-mode:interception:save', 'permission_type': 1, 'api_path': '/api/project-manager/failure-mode/interception-strategies', 'http_method': 'POST'},
        {'name': '获取故障处理措施列表', 'code': 'project_manager:api:failure-mode:measure:list', 'permission_type': 1, 'api_path': '/api/project-manager/failure-mode/handling-measures', 'http_method': 'GET'},
        {'name': '保存故障处理措施', 'code': 'project_manager:api:failure-mode:measure:save', 'permission_type': 1, 'api_path': '/api/project-manager/failure-mode/handling-measures', 'http_method': 'POST'},
        {'name': '获取维测手段列表', 'code': 'project_manager:api:failure-mode:observation:list', 'permission_type': 1, 'api_path': '/api/project-manager/failure-mode/observation-methods', 'http_method': 'GET'},
        {'name': '保存维测手段', 'code': 'project_manager:api:failure-mode:observation:save', 'permission_type': 1, 'api_path': '/api/project-manager/failure-mode/observation-methods', 'http_method': 'POST'},
        {'name': '获取华佗诊断方案列表', 'code': 'project_manager:api:failure-mode:huatuo:list', 'permission_type': 1, 'api_path': '/api/project-manager/failure-mode/huatuo-diagnoses', 'http_method': 'GET'},
        {'name': '保存华佗诊断方案', 'code': 'project_manager:api:failure-mode:huatuo:save', 'permission_type': 1, 'api_path': '/api/project-manager/failure-mode/huatuo-diagnoses', 'http_method': 'POST'},
        {'name': '获取测试用例列表', 'code': 'project_manager:api:failure-mode:test-case:list', 'permission_type': 1, 'api_path': '/api/project-manager/failure-mode/test-cases', 'http_method': 'GET'},
        {'name': '保存测试用例', 'code': 'project_manager:api:failure-mode:test-case:save', 'permission_type': 1, 'api_path': '/api/project-manager/failure-mode/test-cases', 'http_method': 'POST'},
    ],
}


class Command(BaseCommand):
    help = '初始化故障模式模块菜单和权限'

    def handle(self, *args, **options):
        operator = User.objects.filter(is_superuser=True).order_by('sys_create_datetime').first()
        if operator is None:
            self.stdout.write(self.style.ERROR('未找到超级管理员，无法初始化菜单权限'))
            return

        menus = self._seed_menus(operator)
        permission_count = self._seed_permissions(menus, operator)
        MenuCacheManager.invalidate_menu_cache()
        PermissionCacheManager.invalidate_permission_cache()
        PermissionCacheManager.invalidate_global_permissions()
        self.stdout.write(
            self.style.SUCCESS(
                f'故障模式模块初始化完成：菜单 {len(menus)} 项，权限 {permission_count} 项。',
            )
        )

    def _seed_menus(self, operator: User):
        created: dict[str, Menu] = {}
        for seed in MENU_SEEDS:
            parent = created.get(seed.parent_key) if seed.parent_key else None
            menu, _ = Menu.objects.get_or_create(
                path=seed.path,
                defaults={
                    'parent': parent,
                    'name': seed.name,
                    'title': seed.title,
                    'authCode': seed.auth_code,
                    'type': seed.menu_type,
                    'component': seed.component,
                    'icon': seed.icon,
                    'order': seed.order,
                    'hideInMenu': seed.hide_in_menu,
                    'hideChildrenInMenu': seed.hide_children_in_menu,
                    'keepAlive': seed.keep_alive,
                    'sys_creator': operator,
                    'sys_modifier': operator,
                },
            )
            menu.parent = parent
            menu.name = seed.name
            menu.title = seed.title
            menu.authCode = seed.auth_code
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
                Permission.objects.update_or_create(
                    menu=menu,
                    code=item['code'],
                    defaults={
                        'name': item['name'],
                        'permission_type': item['permission_type'],
                        'api_path': item.get('api_path') or None,
                        'http_method': HTTP_METHOD_MAP.get(item.get('http_method') or 'GET', 0),
                        'description': item.get('name'),
                        'is_active': True,
                        'sys_creator': operator,
                        'sys_modifier': operator,
                    },
                )
                total += 1
        return total
