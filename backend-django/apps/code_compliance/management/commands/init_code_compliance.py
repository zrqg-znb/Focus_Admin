from dataclasses import dataclass

from django.core.management.base import BaseCommand

from common.fu_cache import MenuCacheManager, PermissionCacheManager
from core.dict.dict_model import Dict
from core.dict_item.dict_item_model import DictItem
from core.menu.menu_model import Menu
from core.permission.permission_model import Permission
from core.user.user_model import User


HTTP_METHOD_MAP = {"GET": 0, "POST": 1, "PUT": 2, "DELETE": 3, "PATCH": 4, "ALL": 5}
REPO_TYPE_DICT_CODE = "code_compliance_repo_type"


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
    active_path: str | None = None
    hide_in_menu: bool = False
    keep_alive: bool = True
    redirect: str | None = None


MENU_SEEDS = [
    MenuSeed(
        key="code_compliance",
        parent_key=None,
        name="CodeComplianceCatalog",
        title="代码合规",
        path="/compliance",
        component=None,
        menu_type="catalog",
        order=58,
        auth_code="code_compliance",
        icon="lucide:git-branch",
        redirect="/compliance/overview",
    ),
    MenuSeed(
        key="risk_overview",
        parent_key="code_compliance",
        name="CodeComplianceOverview",
        title="合规风险概览",
        path="/compliance/overview",
        component="/compliance/overview/index",
        order=1,
        auth_code="code_compliance:risk_overview",
        icon="lucide:shield-alert",
    ),
    MenuSeed(
        key="risk_detail",
        parent_key="code_compliance",
        name="CodeComplianceDetail",
        title="合规风险详情",
        path="/compliance/detail",
        component="/compliance/detail/index",
        order=2,
        auth_code="code_compliance:risk_overview",
        active_path="/compliance/overview",
        hide_in_menu=True,
        keep_alive=False,
    ),
    MenuSeed(
        key="repository",
        parent_key="code_compliance",
        name="ComplianceRepository",
        title="代码库管理",
        path="/compliance/repository",
        component="/compliance/repository/index",
        order=3,
        auth_code="code_compliance:repository",
        icon="lucide:folder-git-2",
    ),
    MenuSeed(
        key="branch",
        parent_key="code_compliance",
        name="ComplianceBranch",
        title="分支管理",
        path="/compliance/branch",
        component="/compliance/branch/index",
        order=4,
        auth_code="code_compliance:branch",
        icon="lucide:git-branch-plus",
    ),
]

PERMISSION_SEEDS = {
    "risk_overview": [
        {"name": "查看合规风险概览", "code": "code_compliance:risk:view", "permission_type": 0},
        {
            "name": "风险统计接口",
            "code": "code_compliance:api:risk:stats",
            "permission_type": 1,
            "api_path": "/api/code-compliance/stats*",
            "http_method": "GET",
        },
        {
            "name": "风险上传接口",
            "code": "code_compliance:api:risk:upload",
            "permission_type": 1,
            "api_path": "/api/code-compliance/upload",
            "http_method": "POST",
        },
        {
            "name": "风险模板接口",
            "code": "code_compliance:api:risk:template",
            "permission_type": 1,
            "api_path": "/api/code-compliance/template",
            "http_method": "GET",
        },
        {
            "name": "风险分支状态更新接口",
            "code": "code_compliance:api:risk:branch:update",
            "permission_type": 1,
            "api_path": "/api/code-compliance/branch/:id",
            "http_method": "PUT",
        },
    ],
    "repository": [
        {"name": "查看代码库管理", "code": "code_compliance:repository:view", "permission_type": 0},
        {
            "name": "组织树接口",
            "code": "code_compliance:api:organizations:list",
            "permission_type": 1,
            "api_path": "/api/code-compliance/base/organizations*",
            "http_method": "GET",
        },
        {
            "name": "组织创建接口",
            "code": "code_compliance:api:organizations:create",
            "permission_type": 1,
            "api_path": "/api/code-compliance/base/organizations",
            "http_method": "POST",
        },
        {
            "name": "组织更新接口",
            "code": "code_compliance:api:organizations:update",
            "permission_type": 1,
            "api_path": "/api/code-compliance/base/organizations/:id",
            "http_method": "PUT",
        },
        {
            "name": "组织删除接口",
            "code": "code_compliance:api:organizations:delete",
            "permission_type": 1,
            "api_path": "/api/code-compliance/base/organizations/:id",
            "http_method": "DELETE",
        },
        {
            "name": "组织导入接口",
            "code": "code_compliance:api:organizations:import",
            "permission_type": 1,
            "api_path": "/api/code-compliance/base/organizations/import",
            "http_method": "POST",
        },
        {
            "name": "代码库列表接口",
            "code": "code_compliance:api:repositories:list",
            "permission_type": 1,
            "api_path": "/api/code-compliance/base/repositories*",
            "http_method": "GET",
        },
        {
            "name": "代码库创建接口",
            "code": "code_compliance:api:repositories:create",
            "permission_type": 1,
            "api_path": "/api/code-compliance/base/repositories",
            "http_method": "POST",
        },
        {
            "name": "代码库更新接口",
            "code": "code_compliance:api:repositories:update",
            "permission_type": 1,
            "api_path": "/api/code-compliance/base/repositories/:id",
            "http_method": "PUT",
        },
        {
            "name": "代码库删除接口",
            "code": "code_compliance:api:repositories:delete",
            "permission_type": 1,
            "api_path": "/api/code-compliance/base/repositories/:id",
            "http_method": "DELETE",
        },
        {
            "name": "代码库导入接口",
            "code": "code_compliance:api:repositories:import",
            "permission_type": 1,
            "api_path": "/api/code-compliance/base/repositories/import",
            "http_method": "POST",
        },
        {
            "name": "代码库绑定分支接口",
            "code": "code_compliance:api:repositories:bind_branches",
            "permission_type": 1,
            "api_path": "/api/code-compliance/base/repositories/batch-bind-branches",
            "http_method": "POST",
        },
    ],
    "branch": [
        {"name": "查看分支管理", "code": "code_compliance:branch:view", "permission_type": 0},
        {
            "name": "分支列表接口",
            "code": "code_compliance:api:branches:list",
            "permission_type": 1,
            "api_path": "/api/code-compliance/base/branches*",
            "http_method": "GET",
        },
        {
            "name": "分支创建接口",
            "code": "code_compliance:api:branches:create",
            "permission_type": 1,
            "api_path": "/api/code-compliance/base/branches",
            "http_method": "POST",
        },
        {
            "name": "分支更新接口",
            "code": "code_compliance:api:branches:update",
            "permission_type": 1,
            "api_path": "/api/code-compliance/base/branches/:id",
            "http_method": "PUT",
        },
        {
            "name": "分支删除接口",
            "code": "code_compliance:api:branches:delete",
            "permission_type": 1,
            "api_path": "/api/code-compliance/base/branches/:id",
            "http_method": "DELETE",
        },
        {
            "name": "分支导入接口",
            "code": "code_compliance:api:branches:import",
            "permission_type": 1,
            "api_path": "/api/code-compliance/base/branches/import",
            "http_method": "POST",
        },
        {
            "name": "分支绑定代码库接口",
            "code": "code_compliance:api:branches:bind_repositories",
            "permission_type": 1,
            "api_path": "/api/code-compliance/base/branches/batch-bind-repositories",
            "http_method": "POST",
        },
    ],
}

REPO_TYPE_ITEMS = [
    ("product", "产品仓"),
    ("platform", "平台仓"),
    ("component", "组件仓"),
    ("tool", "工具仓"),
    ("test", "测试仓"),
]


class Command(BaseCommand):
    help = "初始化代码合规菜单、权限与基础字典"

    def handle(self, *args, **options):
        """补齐新旧代码合规菜单、权限和仓库类型字典。"""
        operator = User.objects.filter(is_superuser=True).order_by("sys_create_datetime").first()
        menus = self._seed_menus(operator)
        permission_count = self._seed_permissions(menus, operator)
        dict_count = self._seed_repo_type_dict(operator)

        MenuCacheManager.invalidate_menu_cache()
        PermissionCacheManager.invalidate_permission_cache()
        PermissionCacheManager.invalidate_global_permissions()
        self.stdout.write(
            self.style.SUCCESS(
                f"代码合规初始化完成：菜单 {len(menus)} 项，权限 {permission_count} 项，字典项 {dict_count} 项。"
            )
        )

    def _seed_menus(self, operator):
        """按路径幂等创建菜单，不清理旧风险入口。"""
        created = {}
        for seed in MENU_SEEDS:
            parent = created.get(seed.parent_key)
            menu, _ = Menu.objects.update_or_create(
                path=seed.path,
                defaults={
                    "activePath": seed.active_path,
                    "authCode": seed.auth_code,
                    "component": seed.component,
                    "hideInMenu": seed.hide_in_menu,
                    "icon": seed.icon,
                    "keepAlive": seed.keep_alive,
                    "name": seed.name,
                    "order": seed.order,
                    "parent": parent,
                    "redirect": seed.redirect,
                    "sys_creator": operator,
                    "sys_modifier": operator,
                    "title": seed.title,
                    "type": seed.menu_type,
                },
            )
            created[seed.key] = menu
        return created

    def _seed_permissions(self, menus, operator):
        """按菜单和权限编码幂等创建按钮/API 权限。"""
        total = 0
        for menu_key, rows in PERMISSION_SEEDS.items():
            menu = menus[menu_key]
            for row in rows:
                Permission.objects.update_or_create(
                    code=row["code"],
                    menu=menu,
                    defaults={
                        "api_path": row.get("api_path"),
                        "http_method": HTTP_METHOD_MAP.get(row.get("http_method", "GET"), 0),
                        "is_active": True,
                        "name": row["name"],
                        "permission_type": row["permission_type"],
                        "sort": total,
                        "sys_creator": operator,
                        "sys_modifier": operator,
                    },
                )
                total += 1
        return total

    def _seed_repo_type_dict(self, operator):
        """初始化代码合规仓库类型字典，保留后续人工扩展空间。"""
        repo_type_dict, _ = Dict.objects.update_or_create(
            code=REPO_TYPE_DICT_CODE,
            defaults={
                "name": "代码合规仓库类型",
                "remark": "代码合规基础数据一期使用的仓库类型字典",
                "status": True,
                "sys_creator": operator,
                "sys_modifier": operator,
            },
        )
        count = 0
        for sort, (value, label) in enumerate(REPO_TYPE_ITEMS, start=1):
            # 按 value 幂等更新，避免重复运行命令产生重复字典项。
            item = DictItem.objects.filter(dict=repo_type_dict, value=value).first()
            if item is None:
                item = DictItem(dict=repo_type_dict, value=value)
            item.label = label
            item.status = True
            item.sort = sort
            item.sys_creator = item.sys_creator or operator
            item.sys_modifier = operator
            item.save()
            count += 1
        return count
