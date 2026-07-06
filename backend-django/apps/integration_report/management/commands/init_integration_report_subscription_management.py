from dataclasses import dataclass

from django.core.management.base import BaseCommand

from common.fu_cache import MenuCacheManager, PermissionCacheManager
from core.menu.menu_model import Menu
from core.permission.permission_model import Permission
from core.user.user_model import User

HTTP_METHOD_MAP = {"GET": 0, "POST": 1, "PUT": 2, "DELETE": 3, "PATCH": 4, "ALL": 5}


@dataclass(frozen=True)
class MenuSeed:
    key: str
    parent_key: str | None
    name: str
    title: str
    path: str
    component: str | None
    menu_type: str = "menu"
    order: int = 0
    auth_code: str | None = None
    icon: str | None = None
    redirect: str | None = None
    keep_alive: bool = True


MENU_SEEDS = [
    MenuSeed(
        key="integration_report",
        parent_key=None,
        name="IntegrationReport",
        title="集成报告",
        path="/integration-report",
        component=None,
        menu_type="catalog",
        order=36,
        auth_code="integration-report",
        icon="lucide:chart-no-axes-combined",
        redirect="/integration-report/subscription-management",
    ),
    MenuSeed(
        key="integration_report_subscription_management",
        parent_key="integration_report",
        name="IntegrationReportSubscriptionManagement",
        title="邮件订阅管理",
        path="/integration-report/subscription-management",
        component="/integration-report/subscription-management/index",
        order=5,
        auth_code="integration-report:subscription-management",
    ),
]

PERMISSION_SEEDS = {
    "integration_report_subscription_management": [
        {
            "name": "邮件订阅管理查看",
            "code": "integration-report:subscription-management:view",
            "permission_type": 0,
        },
        {
            "name": "订阅项目列表接口",
            "code": "integration-report:api:subscription-management:projects",
            "permission_type": 1,
            "api_path": "/api/integration-report/subscription-management/projects",
            "http_method": "GET",
        },
        {
            "name": "订阅人列表接口",
            "code": "integration-report:api:subscription-management:subscribers:list",
            "permission_type": 1,
            "api_path": "/api/integration-report/subscription-management/projects/:id/subscribers",
            "http_method": "GET",
        },
        {
            "name": "订阅人全量保存接口",
            "code": "integration-report:api:subscription-management:subscribers:replace",
            "permission_type": 1,
            "api_path": "/api/integration-report/subscription-management/projects/:id/subscribers",
            "http_method": "PUT",
        },
        {
            "name": "订阅人批量追加接口",
            "code": "integration-report:api:subscription-management:subscribers:add",
            "permission_type": 1,
            "api_path": "/api/integration-report/subscription-management/projects/:id/subscribers/batch-add",
            "http_method": "POST",
        },
        {
            "name": "多项目订阅人批量追加接口",
            "code": "integration-report:api:subscription-management:projects:subscribers:add",
            "permission_type": 1,
            "api_path": "/api/integration-report/subscription-management/projects/subscribers/batch-add",
            "http_method": "POST",
        },
        {
            "name": "订阅人批量移除接口",
            "code": "integration-report:api:subscription-management:subscribers:remove",
            "permission_type": 1,
            "api_path": "/api/integration-report/subscription-management/projects/:id/subscribers/batch-remove",
            "http_method": "POST",
        },
    ],
}


class Command(BaseCommand):
    help = "初始化集成报告邮件订阅管理菜单和权限"

    def handle(self, *args, **options):
        operator = User.objects.filter(is_superuser=True).order_by("sys_create_datetime").first()
        menus = self._seed_menus(operator)
        permission_count = self._seed_permissions(menus, operator)
        MenuCacheManager.invalidate_menu_cache()
        PermissionCacheManager.invalidate_permission_cache()
        PermissionCacheManager.invalidate_global_permissions()
        self.stdout.write(
            self.style.SUCCESS(
                f"集成报告邮件订阅管理初始化完成：菜单 {len(menus)} 项，权限 {permission_count} 项。"
            )
        )

    def _seed_menus(self, operator):
        """初始化邮件订阅管理菜单，保留现有集成报告目录的其他子菜单。"""
        created = {}
        for seed in MENU_SEEDS:
            parent = created.get(seed.parent_key)
            menu, _ = Menu.objects.update_or_create(
                path=seed.path,
                defaults={
                    "parent": parent,
                    "name": seed.name,
                    "title": seed.title,
                    "authCode": seed.auth_code,
                    "type": seed.menu_type,
                    "component": seed.component,
                    "redirect": seed.redirect,
                    "icon": seed.icon,
                    "order": seed.order,
                    "keepAlive": seed.keep_alive,
                    "sys_creator": operator,
                    "sys_modifier": operator,
                },
            )
            created[seed.key] = menu
        return created

    def _seed_permissions(self, menus, operator):
        """初始化订阅管理页面和接口权限。"""
        total = 0
        for menu_key, rows in PERMISSION_SEEDS.items():
            menu = menus[menu_key]
            for row in rows:
                Permission.objects.update_or_create(
                    menu=menu,
                    code=row["code"],
                    defaults={
                        "name": row["name"],
                        "permission_type": row["permission_type"],
                        "api_path": row.get("api_path"),
                        "http_method": HTTP_METHOD_MAP.get(row.get("http_method", "GET"), 0),
                        "is_active": True,
                        "sort": total,
                        "sys_creator": operator,
                        "sys_modifier": operator,
                    },
                )
                total += 1
        return total
