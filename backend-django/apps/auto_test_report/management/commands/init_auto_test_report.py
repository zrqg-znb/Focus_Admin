from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db.models import Q

from common.fu_cache import MenuCacheManager, PermissionCacheManager
from core.menu.menu_model import Menu
from core.permission.permission_model import Permission
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
    keep_alive: bool = True
    redirect: str | None = None
    hide_in_menu: bool = False


MENU_SEEDS = [
    MenuSeed(
        key='auto_test_report',
        parent_key=None,
        name='AutoTestReport',
        title='自动化测试',
        path='/auto-test-report',
        component=None,
        menu_type='catalog',
        order=37,
        auth_code='auto-test-report',
        icon='lucide:test-tube-diagonal',
        keep_alive=True,
        redirect='/auto-test-report/vehicle-config',
    ),
    MenuSeed(
        key='auto_test_vehicle_config',
        parent_key='auto_test_report',
        name='AutoTestVehicleConfig',
        title='车型配置',
        path='/auto-test-report/vehicle-config',
        component='/auto-test-report/vehicle-config/index',
        order=1,
        auth_code='auto-test-report:vehicle-config',
    ),
    MenuSeed(
        key='auto_test_cases',
        parent_key='auto_test_report',
        name='AutoTestCaseList',
        title='用例管理',
        path='/auto-test-report/test-cases',
        component='/auto-test-report/test-cases/index',
        order=2,
        auth_code='auto-test-report:test-cases',
    ),
    MenuSeed(
        key='auto_test_daily_results',
        parent_key='auto_test_report',
        name='AutoTestDailyResults',
        title='每日结果',
        path='/auto-test-report/daily-results',
        component='/auto-test-report/daily-results/index',
        order=3,
        auth_code='auto-test-report:daily-results',
    ),
]

PERMISSION_SEEDS = {
    'auto_test_vehicle_config': [
        {'name': '车型配置查看', 'code': 'auto-test-report:vehicle-config:view', 'permission_type': 0},
        {'name': '平台列表接口', 'code': 'auto-test-report:api:platforms:list', 'permission_type': 1, 'api_path': '/api/auto-test-report/platforms', 'http_method': 'GET'},
        {'name': '平台创建接口', 'code': 'auto-test-report:api:platforms:create', 'permission_type': 1, 'api_path': '/api/auto-test-report/platforms', 'http_method': 'POST'},
        {'name': '平台更新接口', 'code': 'auto-test-report:api:platforms:update', 'permission_type': 1, 'api_path': '/api/auto-test-report/platforms/:id', 'http_method': 'PUT'},
        {'name': '平台删除接口', 'code': 'auto-test-report:api:platforms:delete', 'permission_type': 1, 'api_path': '/api/auto-test-report/platforms/:id', 'http_method': 'DELETE'},
        {'name': '车型列表接口', 'code': 'auto-test-report:api:vehicles:list', 'permission_type': 1, 'api_path': '/api/auto-test-report/vehicles', 'http_method': 'GET'},
        {'name': '车型创建接口', 'code': 'auto-test-report:api:vehicles:create', 'permission_type': 1, 'api_path': '/api/auto-test-report/vehicles', 'http_method': 'POST'},
        {'name': '车型更新接口', 'code': 'auto-test-report:api:vehicles:update', 'permission_type': 1, 'api_path': '/api/auto-test-report/vehicles/:id', 'http_method': 'PUT'},
        {'name': '车型删除接口', 'code': 'auto-test-report:api:vehicles:delete', 'permission_type': 1, 'api_path': '/api/auto-test-report/vehicles/:id', 'http_method': 'DELETE'},
        {'name': '车型选项接口', 'code': 'auto-test-report:api:vehicle-options:list', 'permission_type': 1, 'api_path': '/api/auto-test-report/vehicle-options', 'http_method': 'GET'},
    ],
    'auto_test_cases': [
        {'name': '用例管理查看', 'code': 'auto-test-report:test-cases:view', 'permission_type': 0},
        {'name': '用例列表接口', 'code': 'auto-test-report:api:test-cases:list', 'permission_type': 1, 'api_path': '/api/auto-test-report/test-cases', 'http_method': 'GET'},
        {'name': '用例创建接口', 'code': 'auto-test-report:api:test-cases:create', 'permission_type': 1, 'api_path': '/api/auto-test-report/test-cases', 'http_method': 'POST'},
        {'name': '用例更新接口', 'code': 'auto-test-report:api:test-cases:update', 'permission_type': 1, 'api_path': '/api/auto-test-report/test-cases/:id', 'http_method': 'PUT'},
        {'name': '用例删除接口', 'code': 'auto-test-report:api:test-cases:delete', 'permission_type': 1, 'api_path': '/api/auto-test-report/test-cases/:id', 'http_method': 'DELETE'},
        {'name': '用例批量删除接口', 'code': 'auto-test-report:api:test-cases:batch-delete', 'permission_type': 1, 'api_path': '/api/auto-test-report/test-cases/batch-delete', 'http_method': 'POST'},
        {'name': '用例导入接口', 'code': 'auto-test-report:api:test-cases:import', 'permission_type': 1, 'api_path': '/api/auto-test-report/test-cases/import', 'http_method': 'POST'},
        {'name': '用例Excel导入接口', 'code': 'auto-test-report:api:test-cases:import-excel', 'permission_type': 1, 'api_path': '/api/auto-test-report/test-cases/import-excel', 'http_method': 'POST'},
        {'name': '用例模板接口', 'code': 'auto-test-report:api:test-cases:template', 'permission_type': 1, 'api_path': '/api/auto-test-report/test-cases/template', 'http_method': 'GET'},
        {'name': '用例导出接口', 'code': 'auto-test-report:api:test-cases:export', 'permission_type': 1, 'api_path': '/api/auto-test-report/test-cases/export', 'http_method': 'GET'},
        {'name': '用例历史接口', 'code': 'auto-test-report:api:test-cases:history', 'permission_type': 1, 'api_path': '/api/auto-test-report/test-cases/:id/history', 'http_method': 'GET'},
    ],
    'auto_test_daily_results': [
        {'name': '每日结果查看', 'code': 'auto-test-report:daily-results:view', 'permission_type': 0},
        {'name': '每日汇总接口', 'code': 'auto-test-report:api:daily-results:summary', 'permission_type': 1, 'api_path': '/api/auto-test-report/daily-results/summary', 'http_method': 'GET'},
        {'name': '每日结果列表接口', 'code': 'auto-test-report:api:daily-results:list', 'permission_type': 1, 'api_path': '/api/auto-test-report/daily-results/list', 'http_method': 'GET'},
        {'name': '测试环境上报接口', 'code': 'auto-test-report:api:report:daily-results', 'permission_type': 1, 'api_path': '/api/auto-test-report/report/daily-results', 'http_method': 'POST'},
    ],
}


class Command(BaseCommand):
    help = '初始化自动化测试日报菜单与权限并清理旧数据'

    def handle(self, *args, **options):
        operator = User.objects.filter(is_superuser=True).order_by('sys_create_datetime').first()
        self._cleanup_stale_data()
        menus = self._seed_menus(operator)
        count = self._seed_permissions(menus, operator)
        MenuCacheManager.invalidate_menu_cache()
        PermissionCacheManager.invalidate_permission_cache()
        PermissionCacheManager.invalidate_global_permissions()
        self.stdout.write(self.style.SUCCESS(f'自动化测试日报初始化完成：菜单 {len(menus)} 项，权限 {count} 项。'))

    def _cleanup_stale_data(self):
        Permission.objects.filter(
            Q(code='auto-test-report:api:vehicles:rotate-token')
            | Q(api_path='/api/auto-test-report/vehicles/:id/rotate-token')
        ).delete()
        Menu.objects.filter(
            Q(path__startswith='/auto-test-report')
            & ~Q(path__in=[s.path for s in MENU_SEEDS])
        ).delete()

    def _seed_menus(self, operator):
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
                    'hideInMenu': seed.hide_in_menu,
                    'keepAlive': seed.keep_alive,
                    'sys_creator': operator,
                    'sys_modifier': operator,
                },
            )
            created[seed.key] = menu
        return created

    def _seed_permissions(self, menus, operator):
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
