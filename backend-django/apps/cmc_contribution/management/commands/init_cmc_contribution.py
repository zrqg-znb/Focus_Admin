"""初始化 CMC 贡献看板菜单、权限和定时任务。"""

from django.core.management.base import BaseCommand

from common.fu_cache import MenuCacheManager, PermissionCacheManager
from core.menu.menu_model import Menu
from core.permission.permission_model import Permission
from core.user.user_model import User
from scheduler.models import SchedulerJob


class Command(BaseCommand):
    """幂等写入 CMC 看板的运行所需元数据。"""

    def handle(self, *args, **options):
        """在代码合规目录下创建页面、接口权限和每日同步任务。"""
        operator = User.objects.filter(is_superuser=True).order_by("sys_create_datetime").first()
        parent = Menu.objects.filter(name="CodeComplianceCatalog", is_deleted=False).first()
        if parent is None:
            self.stderr.write(self.style.ERROR("未找到代码合规目录，请先执行 init_code_compliance"))
            return
        menu, _ = Menu.objects.update_or_create(
            name="CmcContribution",
            defaults={
                "parent": parent, "title": "CMC贡献看板", "path": "/compliance/cmc-contribution",
                "component": "/compliance/cmc-contribution/index", "type": "menu", "order": 7,
                "authCode": "cmc_contribution", "icon": "lucide:chart-column-big", "keepAlive": True,
                "sys_creator": operator, "sys_modifier": operator,
            },
        )
        permission_rows = [
            ("查看CMC贡献看板", "cmc_contribution:view", 0, "" , "ALL"),
            ("CMC贡献查询接口", "cmc_contribution:api:view", 1, "/api/cmc-contribution/dashboard/*", "GET"),
            ("CMC贡献人员接口", "cmc_contribution:api:persons", 1, "/api/cmc-contribution/persons", "GET"),
            ("CMC同步任务查询接口", "cmc_contribution:api:task:view", 1, "/api/cmc-contribution/sync-tasks/*", "GET"),
            ("CMC手动同步接口", "cmc_contribution:api:sync", 1, "/api/cmc-contribution/sync-tasks", "POST"),
        ]
        for name, code, permission_type, api_path, http_method in permission_rows:
            Permission.objects.update_or_create(
                code=code,
                defaults={"name": name, "menu": menu, "permission_type": permission_type, "api_path": api_path, "http_method": {"GET": 0, "POST": 1, "ALL": 5}[http_method], "is_active": True, "sys_creator": operator, "sys_modifier": operator},
            )
        SchedulerJob.objects.update_or_create(
            code="cmc_contribution_daily_sync",
            defaults={
                "name": "CMC贡献数据同步", "description": "每日 01:00 同步前一天底层软件开发部 CMC 贡献数据",
                "group": "cmc_contribution", "trigger_type": "cron", "cron_expression": "0 1 * * *",
                "task_func": "apps.cmc_contribution.services.run_scheduled_cmc_contribution_sync", "task_args": "[]", "task_kwargs": "{}",
                "status": 1, "priority": 10, "max_instances": 1, "max_retries": 0, "timeout": 3600,
                "coalesce": True, "allow_concurrent": False, "sys_creator": operator, "sys_modifier": operator,
            },
        )
        MenuCacheManager.invalidate_menu_cache()
        PermissionCacheManager.invalidate_global_permissions()
        PermissionCacheManager.invalidate_permission_cache()
        self.stdout.write(self.style.SUCCESS("CMC贡献看板初始化完成"))
