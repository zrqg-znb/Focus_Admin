"""初始化 Tools 菜单、权限和管理员角色。"""

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
    order: int = 45
    auth_code: str | None = None
    icon: str | None = None
    redirect: str | None = None
    hide_in_menu: bool = False


MENU_SEEDS = [
    MenuSeed('tools', None, 'AiTools', 'AI辅助工具', '/ai-tools', None, 'catalog', 45, 'ai-tools', 'lucide:sparkles', '/ai-tools/agent-hub'),
    MenuSeed('agent_skills_workbench', 'tools', 'AgentHub', 'Agent Hub', '/ai-tools/agent-hub', '/tools/agent-hub/index', auth_code='tools:agent-skills:workbench'),
    MenuSeed('agent_skills_editor', 'tools', 'AgentSkillsEditor', 'Skill 自进化', '/ai-tools/agent-skills', '/tools/agent-skills/workbench/index', auth_code='tools:agent-skills:workbench', hide_in_menu=True),
    MenuSeed('agent_skills_records', 'tools', 'AgentSkillsRecords', 'Skill自进化记录', '/ai-tools/agent-skills/records', '/tools/agent-skills/records/index', auth_code='tools:agent-skills:records', hide_in_menu=True),
    MenuSeed('agent_skills_providers', 'tools', 'AiModelConfig', '模型配置', '/ai-tools/model-config', '/tools/agent-skills/providers/index', auth_code='tools:agent-skills:providers'),
]

PERMISSIONS = {
    'agent_skills_workbench': [
        ('技能工作台查看', 'tools:agent-skills:workbench:view', 0, None, 'GET'),
        ('技能列表', 'tools:agent-skills:api:skills:list', 1, '/api/tools/agent-skills/skills', 'GET'),
        ('上传技能包', 'tools:agent-skills:api:skills:upload', 1, '/api/tools/agent-skills/skills/upload', 'POST'),
        ('模型档案选项', 'tools:agent-skills:api:providers:list', 1, '/api/tools/agent-skills/providers', 'GET'),
        ('创建优化任务', 'tools:agent-skills:api:runs:create', 1, '/api/tools/agent-skills/runs', 'POST'),
        ('读取优化任务', 'tools:agent-skills:api:runs:detail', 1, '/api/tools/agent-skills/runs/:id', 'GET'),
        ('保存优化配置', 'tools:agent-skills:api:runs:config', 1, '/api/tools/agent-skills/runs/:id/config', 'PUT'),
        ('重新生成优化配置', 'tools:agent-skills:api:runs:regenerate', 1, '/api/tools/agent-skills/runs/:id/config/regenerate', 'POST'),
        ('启动优化任务', 'tools:agent-skills:api:runs:start', 1, '/api/tools/agent-skills/runs/:id/start', 'POST'),
        ('取消优化任务', 'tools:agent-skills:api:runs:cancel', 1, '/api/tools/agent-skills/runs/:id/cancel', 'POST'),
        ('优化迭代记录', 'tools:agent-skills:api:runs:iterations', 1, '/api/tools/agent-skills/runs/:id/iterations', 'GET'),
        ('下载技能包', 'tools:agent-skills:api:runs:download', 1, '/api/tools/agent-skills/runs/:id/download', 'GET'),
    ],
    'agent_skills_records': [('优化记录查看', 'tools:agent-skills:records:view', 0, None, 'GET'), ('优化记录列表', 'tools:agent-skills:api:runs:list', 1, '/api/tools/agent-skills/runs', 'GET')],
    'agent_skills_providers': [
        ('模型配置查看', 'tools:agent-skills:providers:view', 0, None, 'GET'),
        ('创建模型档案', 'tools:agent-skills:api:providers:create', 1, '/api/tools/agent-skills/providers', 'POST'),
        ('更新模型档案', 'tools:agent-skills:api:providers:update', 1, '/api/tools/agent-skills/providers/:id', 'PUT'),
        ('测试模型档案', 'tools:agent-skills:api:providers:test', 1, '/api/tools/agent-skills/providers/:id/test', 'POST'),
    ],
}


class Command(BaseCommand):
    help = '初始化 Tools 和 Agent Skills 菜单、权限及管理员角色'

    def handle(self, *args, **options):
        """幂等写入菜单、权限并把全部权限授予 Tools 管理员。"""
        operator = User.objects.filter(is_superuser=True).order_by('sys_create_datetime').first()
        Menu.objects.filter(path__in=['/tools', '/tools/agent-skills/workbench', '/tools/agent-skills/records', '/tools/agent-skills/providers']).delete()
        menus = self._seed_menus(operator)
        self._seed_permissions(menus, operator)
        user_role, _ = Role.objects.update_or_create(code='tools_user', defaults={'name': 'Tools 用户', 'description': '使用 Tools 下已授权的 AI 工具', 'role_type': 1, 'status': True, 'priority': 50, 'sys_creator': operator, 'sys_modifier': operator})
        admin_role, _ = Role.objects.update_or_create(code='tools_admin', defaults={'name': 'Tools 管理员', 'description': '维护 Tools 下的模型档案和 AI 工具', 'role_type': 1, 'status': True, 'priority': 50, 'sys_creator': operator, 'sys_modifier': operator})
        user_menus = [menus['tools'], menus['agent_skills_workbench'], menus['agent_skills_editor'], menus['agent_skills_providers']]
        user_permissions = Permission.objects.filter(code__startswith='tools:agent-skills:')
        user_role.menu.add(*user_menus)
        user_role.permission.add(*user_permissions)
        admin_role.menu.add(*menus.values())
        admin_role.permission.add(*Permission.objects.filter(code__startswith='tools:agent-skills:'))
        MenuCacheManager.invalidate_menu_cache(); PermissionCacheManager.invalidate_permission_cache(); PermissionCacheManager.invalidate_global_permissions()
        self.stdout.write(self.style.SUCCESS('Tools 初始化完成。'))

    def _seed_menus(self, operator):
        """初始化 Tools 一级目录及 Agent Skills 子页面。"""
        created = {}
        for seed in MENU_SEEDS:
            menu, _ = Menu.objects.update_or_create(path=seed.path, defaults={'parent': created.get(seed.parent_key), 'name': seed.name, 'title': seed.title,
                'authCode': seed.auth_code, 'type': seed.menu_type, 'component': seed.component, 'redirect': seed.redirect, 'icon': seed.icon,
                'order': seed.order, 'keepAlive': True, 'hideInMenu': seed.hide_in_menu, 'sys_creator': operator, 'sys_modifier': operator})
            created[seed.key] = menu
        return created

    def _seed_permissions(self, menus, operator):
        """写入页面按钮权限和 API 路径权限。"""
        for menu_key, rows in PERMISSIONS.items():
            for order, (name, code, permission_type, api_path, method) in enumerate(rows):
                Permission.objects.update_or_create(menu=menus[menu_key], code=code, defaults={'name': name, 'permission_type': permission_type,
                    'api_path': api_path, 'http_method': HTTP_METHOD_MAP[method], 'is_active': True, 'sort': order, 'sys_creator': operator, 'sys_modifier': operator})
