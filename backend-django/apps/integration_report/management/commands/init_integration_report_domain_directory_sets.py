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
        key="integration_report_domain_directory_sets",
        parent_key="integration_report",
        name="IntegrationReportDomainDirectorySets",
        title="责任田目录配置",
        path="/integration-report/domain-directory-sets",
        component="/integration-report/domain-directory-sets/index",
        order=4,
        auth_code="integration-report:domain-directory-sets",
    ),
]

PERMISSION_SEEDS = {
    "integration_report_domain_directory_sets": [
        {
            "name": "责任田目录配置查看",
            "code": "integration-report:domain-directory-sets:view",
            "permission_type": 0,
        },
        {
            "name": "责任田目录配置列表接口",
            "code": "integration-report:api:domain-directory-sets:list",
            "permission_type": 1,
            "api_path": "/api/integration-report/domain-directory-sets",
            "http_method": "GET",
        },
        {
            "name": "责任田目录配置选项接口",
            "code": "integration-report:api:domain-directory-sets:options",
            "permission_type": 1,
            "api_path": "/api/integration-report/domain-directory-sets/options",
            "http_method": "GET",
        },
        {
            "name": "责任田目录配置详情接口",
            "code": "integration-report:api:domain-directory-sets:detail",
            "permission_type": 1,
            "api_path": "/api/integration-report/domain-directory-sets/:id",
            "http_method": "GET",
        },
        {
            "name": "责任田目录配置创建接口",
            "code": "integration-report:api:domain-directory-sets:create",
            "permission_type": 1,
            "api_path": "/api/integration-report/domain-directory-sets",
            "http_method": "POST",
        },
        {
            "name": "责任田目录配置更新接口",
            "code": "integration-report:api:domain-directory-sets:update",
            "permission_type": 1,
            "api_path": "/api/integration-report/domain-directory-sets/:id",
            "http_method": "PUT",
        },
        {
            "name": "责任田目录配置删除接口",
            "code": "integration-report:api:domain-directory-sets:delete",
            "permission_type": 1,
            "api_path": "/api/integration-report/domain-directory-sets/:id",
            "http_method": "DELETE",
        },
    ],
}


class Command(BaseCommand):
    help = "初始化集成报告责任田目录配置菜单和权限"

    def handle(self, *args, **options):
        operator = User.objects.filter(is_superuser=True).order_by("sys_create_datetime").first()
        menus = self._seed_menus(operator)
        permission_count = self._seed_permissions(menus, operator)
        MenuCacheManager.invalidate_menu_cache()
        PermissionCacheManager.invalidate_permission_cache()
        PermissionCacheManager.invalidate_global_permissions()
        self.stdout.write(
            self.style.SUCCESS(
                f"集成报告责任田目录配置初始化完成：菜单 {len(menus)} 项，权限 {permission_count} 项。"
            )
        )

    def _seed_menus(self, operator):
        """初始化责任田目录配置菜单，复用集成报告目录。"""
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
        """初始化责任田目录配置页面和接口权限。"""
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
