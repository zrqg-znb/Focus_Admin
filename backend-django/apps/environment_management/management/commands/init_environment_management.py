from dataclasses import dataclass

from django.core.management.base import BaseCommand

from common.fu_cache import MenuCacheManager, PermissionCacheManager
from core.menu.menu_model import Menu
from core.permission.permission_model import Permission
from core.role.role_model import Role
from core.user.user_model import User

HTTP_METHOD_MAP = {'GET': 0, 'POST': 1, 'PUT': 2, 'DELETE': 3, 'PATCH': 4, 'ALL': 5}


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
    redirect: str | None = None
    keep_alive: bool = True


MENU_SEEDS = [
    MenuSeed(
        key='environment_management',
        parent_key=None,
        name='EnvironmentManagement',
        title='环境管理',
        path='/environment-management',
        component=None,
        menu_type='catalog',
        order=38,
        auth_code='environment-management',
        icon='lucide:server-cog',
        redirect='/environment-management/user',
    ),
    MenuSeed(
        key='environment_user',
        parent_key='environment_management',
        name='EnvironmentManagementUser',
        title='环境使用',
        path='/environment-management/user',
        component='/environment-management/user/index',
        order=1,
        auth_code='environment-management:user',
    ),
    MenuSeed(
        key='environment_admin',
        parent_key='environment_management',
        name='EnvironmentManagementAdmin',
        title='环境配置',
        path='/environment-management/admin',
        component='/environment-management/admin/index',
        order=2,
        auth_code='environment-management:admin',
    ),
]

PERMISSION_SEEDS = {
    'environment_user': [
        {'name': '环境使用查看', 'code': 'environment-management:user:view', 'permission_type': 0},
        {'name': '环境列表接口', 'code': 'environment-management:api:environments:list', 'permission_type': 1, 'api_path': '/api/environment-management/environments', 'http_method': 'GET'},
        {'name': '环境收藏接口', 'code': 'environment-management:api:favorite', 'permission_type': 1, 'api_path': '/api/environment-management/environments/:id/favorite', 'http_method': 'POST'},
        {'name': '环境取消收藏接口', 'code': 'environment-management:api:unfavorite', 'permission_type': 1, 'api_path': '/api/environment-management/environments/:id/favorite', 'http_method': 'DELETE'},
        {'name': '环境占用接口', 'code': 'environment-management:api:occupy', 'permission_type': 1, 'api_path': '/api/environment-management/environments/:id/occupy', 'http_method': 'POST'},
        {'name': '环境释放接口', 'code': 'environment-management:api:release', 'permission_type': 1, 'api_path': '/api/environment-management/environments/:id/release', 'http_method': 'POST'},
        {'name': '环境排队接口', 'code': 'environment-management:api:queue', 'permission_type': 1, 'api_path': '/api/environment-management/environments/:id/queue', 'http_method': 'POST'},
        {'name': '环境插队接口', 'code': 'environment-management:api:jump-queue', 'permission_type': 1, 'api_path': '/api/environment-management/environments/:id/jump-queue', 'http_method': 'POST'},
        {'name': '取消排队接口', 'code': 'environment-management:api:cancel-queue', 'permission_type': 1, 'api_path': '/api/environment-management/environments/:id/queue/me', 'http_method': 'DELETE'},
        {'name': '队列查看接口', 'code': 'environment-management:api:queue:list', 'permission_type': 1, 'api_path': '/api/environment-management/environments/:id/queue', 'http_method': 'GET'},
        {'name': '占用记录接口', 'code': 'environment-management:api:records:list', 'permission_type': 1, 'api_path': '/api/environment-management/environments/:id/records', 'http_method': 'GET'},
    ],
    'environment_admin': [
        {'name': '环境配置查看', 'code': 'environment-management:admin:view', 'permission_type': 0},
        {'name': '环境创建接口', 'code': 'environment-management:api:environments:create', 'permission_type': 1, 'api_path': '/api/environment-management/environments', 'http_method': 'POST'},
        {'name': '环境更新接口', 'code': 'environment-management:api:environments:update', 'permission_type': 1, 'api_path': '/api/environment-management/environments/:id', 'http_method': 'PUT'},
        {'name': '环境删除接口', 'code': 'environment-management:api:environments:delete', 'permission_type': 1, 'api_path': '/api/environment-management/environments/:id', 'http_method': 'DELETE'},
    ],
}

ROLE_SEEDS = [
    {'name': '环境用户', 'code': 'environment_user', 'description': '允许查看环境账号密码并执行占用、排队、插队、释放'},
    {'name': '环境管理员', 'code': 'env_admin', 'description': '维护环境管理模块基础配置'},
]


class Command(BaseCommand):
    help = '初始化环境管理菜单、权限和系统角色'

    def handle(self, *args, **options):
        operator = User.objects.filter(is_superuser=True).order_by('sys_create_datetime').first()
        menus = self._seed_menus(operator)
        permission_count = self._seed_permissions(menus, operator)
        roles = self._seed_roles(operator)
        binding_count = self._bind_role_permissions_and_menus(roles, menus)
        MenuCacheManager.invalidate_menu_cache()
        PermissionCacheManager.invalidate_permission_cache()
        PermissionCacheManager.invalidate_global_permissions()
        self.stdout.write(
            self.style.SUCCESS(
                f'环境管理初始化完成：菜单 {len(menus)} 项，权限 {permission_count} 项，角色 {len(roles)} 项，授权 {binding_count} 项。'
            )
        )

    def _seed_menus(self, operator):
        """初始化前端菜单；平台默认角色只会拿到用户端菜单，管理员拿到全部菜单。"""
        created = {}
        for seed in MENU_SEEDS:
            parent = created.get(seed.parent_key)
            menu, _ = Menu.objects.update_or_create(
                path=seed.path,
                defaults={
                    'parent': parent,
                    'name': seed.name,
                    'title': seed.title,
                    'authCode': seed.auth_code,
                    'type': seed.menu_type,
                    'component': seed.component,
                    'redirect': seed.redirect,
                    'icon': seed.icon,
                    'order': seed.order,
                    'keepAlive': seed.keep_alive,
                    'sys_creator': operator,
                    'sys_modifier': operator,
                },
            )
            created[seed.key] = menu
        return created

    def _seed_permissions(self, menus, operator):
        """初始化接口权限；认证中间件会按 api_path + http_method 做第一层拦截。"""
        total = 0
        for menu_key, rows in PERMISSION_SEEDS.items():
            menu = menus[menu_key]
            for row in rows:
                Permission.objects.update_or_create(
                    menu=menu,
                    code=row['code'],
                    defaults={
                        'name': row['name'],
                        'permission_type': row['permission_type'],
                        'api_path': row.get('api_path'),
                        'http_method': HTTP_METHOD_MAP.get(row.get('http_method', 'GET'), 0),
                        'is_active': True,
                        'sort': total,
                        'sys_creator': operator,
                        'sys_modifier': operator,
                    },
                )
                total += 1
        return total

    def _seed_roles(self, operator):
        """只新增环境用户和环境管理员；平台用户沿用系统已有的“默认”角色。"""
        roles = {}
        for row in ROLE_SEEDS:
            role, _ = Role.objects.update_or_create(
                code=row['code'],
                defaults={
                    'name': row['name'],
                    'description': row['description'],
                    'role_type': 1,
                    'status': True,
                    'priority': 50,
                    'sys_creator': operator,
                    'sys_modifier': operator,
                },
            )
            roles[row['code']] = role
        return roles

    def _bind_role_permissions_and_menus(self, roles, menus):
        """把权限挂到角色上。

        - 默认角色（平台用户）：只能进入用户端并查看列表、队列、记录。
        - environment_user：继承用户端能力，并可收藏、占用、排队、插队、释放。
        - env_admin：拥有本模块全部菜单和接口权限。
        """
        readonly_permissions = Permission.objects.filter(
            code__in=[
                'environment-management:api:environments:list',
                'environment-management:api:queue:list',
                'environment-management:api:records:list',
            ]
        )
        environment_user_permissions = Permission.objects.filter(
            code__in=[
                'environment-management:api:environments:list',
                'environment-management:api:favorite',
                'environment-management:api:unfavorite',
                'environment-management:api:occupy',
                'environment-management:api:release',
                'environment-management:api:queue',
                'environment-management:api:jump-queue',
                'environment-management:api:cancel-queue',
                'environment-management:api:queue:list',
                'environment-management:api:records:list',
            ]
        )
        admin_permissions = Permission.objects.filter(code__startswith='environment-management:')
        user_menus = [menus['environment_management'], menus['environment_user']]
        admin_menus = [menus['environment_management'], menus['environment_user'], menus['environment_admin']]
        binding_count = 0
        default_role = Role.objects.filter(name='默认').first()
        if default_role:
            default_role.permission.add(*readonly_permissions)
            default_role.menu.add(*user_menus)
            binding_count += readonly_permissions.count()
        environment_user_role = roles.get('environment_user')
        if environment_user_role:
            environment_user_role.permission.add(*environment_user_permissions)
            environment_user_role.menu.add(*user_menus)
            binding_count += environment_user_permissions.count()
        admin_role = roles.get('env_admin')
        if admin_role:
            admin_role.permission.add(*admin_permissions)
            admin_role.menu.add(*admin_menus)
            binding_count += admin_permissions.count()
        return binding_count
