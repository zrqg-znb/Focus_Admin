from django.core.management.base import BaseCommand

from common.fu_cache import MenuCacheManager
from core.menu.menu_model import Menu
from core.user.user_model import User


class Command(BaseCommand):
    help = "初始化项目发布计划看板菜单"

    def handle(self, *args, **options):
        operator = (
            User.objects.filter(is_superuser=True)
            .order_by("sys_create_datetime")
            .first()
        )
        if not operator:
            self.stdout.write(self.style.ERROR("未找到超级管理员，无法初始化菜单"))
            return

        root, _ = Menu.objects.update_or_create(
            path="/project-manager",
            parent=None,
            defaults={
                "name": "ProjectManager",
                "title": "项目管理",
                "authCode": "project_manager",
                "type": "catalog",
                "component": "BasicLayout",
                "icon": "lucide:folder-kanban",
                "order": 60,
                "sys_creator": operator,
                "sys_modifier": operator,
            },
        )
        Menu.objects.update_or_create(
            path="/project-manager/release-plan",
            parent=root,
            defaults={
                "name": "ProjectReleasePlan",
                "title": "发布计划看板",
                "authCode": "project_manager:release-plan",
                "type": "menu",
                "component": "/project-manager/release-plan/index",
                "icon": "lucide:calendar-days",
                "order": 75,
                "keepAlive": True,
                "sys_creator": operator,
                "sys_modifier": operator,
            },
        )
        MenuCacheManager.invalidate_menu_cache()
        self.stdout.write(self.style.SUCCESS("项目发布计划看板菜单初始化完成"))
