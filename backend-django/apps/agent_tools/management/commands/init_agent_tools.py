"""初始化 AI 辅助工具菜单、权限和管理员角色。"""

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
    MenuSeed('agent_tools', None, 'AgentTools', 'AI辅助工具', '/agent-tools', None, 'catalog', 45, 'agent-tools', 'lucide:sparkles', '/agent-tools/hub'),
    MenuSeed('skill_optimizer_workbench', 'agent_tools', 'AgentHub', 'Agent Hub', '/agent-tools/hub', '/agent-tools/hub/index', auth_code='agent-tools:skill-optimizer:workbench'),
    MenuSeed('skill_optimizer_editor', 'agent_tools', 'SkillOptimizer', 'Skill 自进化', '/agent-tools/skill-optimizer', '/agent-tools/skill-optimizer/workbench/index', auth_code='agent-tools:skill-optimizer:workbench', hide_in_menu=True),
    MenuSeed('skill_optimizer_records', 'agent_tools', 'SkillOptimizerRecords', 'Skill自进化记录', '/agent-tools/skill-optimizer/records', '/agent-tools/skill-optimizer/records/index', auth_code='agent-tools:skill-optimizer:records', hide_in_menu=True),
    MenuSeed('agent_tools_providers', 'agent_tools', 'AgentToolsModelConfig', '模型配置', '/agent-tools/model-config', '/agent-tools/providers/index', auth_code='agent-tools:providers'),
    MenuSeed('code_quality_governance', 'agent_tools', 'CodeQualityGovernance', '代码问题治理', '/agent-tools/code-quality-governance', '/agent-tools/code-quality-governance/index', auth_code='agent-tools:code-quality-governance'),
]

PERMISSIONS = {
    'skill_optimizer_workbench': [
        ('技能工作台查看', 'agent-tools:skill-optimizer:workbench:view', 0, None, 'GET'),
        ('技能列表', 'agent-tools:skill-optimizer:api:skills:list', 1, '/api/agent-tools/skill-optimizer/skills', 'GET'),
        ('上传技能包', 'agent-tools:skill-optimizer:api:skills:upload', 1, '/api/agent-tools/skill-optimizer/skills/upload', 'POST'),
        ('创建优化任务', 'agent-tools:skill-optimizer:api:runs:create', 1, '/api/agent-tools/skill-optimizer/runs', 'POST'),
        ('读取优化任务', 'agent-tools:skill-optimizer:api:runs:detail', 1, '/api/agent-tools/skill-optimizer/runs/:id', 'GET'),
        ('保存优化配置', 'agent-tools:skill-optimizer:api:runs:config', 1, '/api/agent-tools/skill-optimizer/runs/:id/config', 'PUT'),
        ('重新生成优化配置', 'agent-tools:skill-optimizer:api:runs:regenerate', 1, '/api/agent-tools/skill-optimizer/runs/:id/config/regenerate', 'POST'),
        ('启动优化任务', 'agent-tools:skill-optimizer:api:runs:start', 1, '/api/agent-tools/skill-optimizer/runs/:id/start', 'POST'),
        ('取消优化任务', 'agent-tools:skill-optimizer:api:runs:cancel', 1, '/api/agent-tools/skill-optimizer/runs/:id/cancel', 'POST'),
        ('优化迭代记录', 'agent-tools:skill-optimizer:api:runs:iterations', 1, '/api/agent-tools/skill-optimizer/runs/:id/iterations', 'GET'),
        ('下载技能包', 'agent-tools:skill-optimizer:api:runs:download', 1, '/api/agent-tools/skill-optimizer/runs/:id/download', 'GET'),
    ],
    'skill_optimizer_records': [('优化记录查看', 'agent-tools:skill-optimizer:records:view', 0, None, 'GET'), ('优化记录列表', 'agent-tools:skill-optimizer:api:runs:list', 1, '/api/agent-tools/skill-optimizer/runs', 'GET')],
    'agent_tools_providers': [
        ('模型配置查看', 'agent-tools:providers:view', 0, None, 'GET'),
        ('模型档案列表', 'agent-tools:providers:api:list', 1, '/api/agent-tools/providers', 'GET'),
        ('创建模型档案', 'agent-tools:providers:api:create', 1, '/api/agent-tools/providers', 'POST'),
        ('更新模型档案', 'agent-tools:providers:api:update', 1, '/api/agent-tools/providers/:id', 'PUT'),
        ('测试模型档案', 'agent-tools:providers:api:test', 1, '/api/agent-tools/providers/:id/test', 'POST'),
    ],
    'code_quality_governance': [
        ('代码问题治理查看', 'agent-tools:code-quality-governance:view', 0, None, 'GET'),
        ('项目列表', 'agent-tools:code-quality-governance:api:projects:list', 1, '/api/agent-tools/code-quality-governance/projects', 'GET'),
        ('项目维护', 'agent-tools:code-quality-governance:api:projects:write', 1, '/api/agent-tools/code-quality-governance/projects', 'ALL'),
        ('责任田列表', 'agent-tools:code-quality-governance:api:responsibilities:list', 1, '/api/agent-tools/code-quality-governance/responsibilities', 'GET'),
        ('责任田维护', 'agent-tools:code-quality-governance:api:responsibilities:write', 1, '/api/agent-tools/code-quality-governance/responsibilities', 'ALL'),
        ('项目责任田关联维护', 'agent-tools:code-quality-governance:api:links:write', 1, '/api/agent-tools/code-quality-governance/project-responsibilities', 'ALL'),
        ('扫描结果接入', 'agent-tools:code-quality-governance:api:reports:ingest', 1, '/api/agent-tools/code-quality-governance/reports', 'POST'),
        ('扫描结果查看', 'agent-tools:code-quality-governance:api:findings:list', 1, '/api/agent-tools/code-quality-governance/findings', 'GET'),
        ('屏蔽申请', 'agent-tools:code-quality-governance:api:shield:apply', 1, '/api/agent-tools/code-quality-governance/shield-applications', 'POST'),
        ('屏蔽审批', 'agent-tools:code-quality-governance:api:shield:audit', 1, '/api/agent-tools/code-quality-governance/shield-applications/:id/approve', 'POST'),
    ],
}


class Command(BaseCommand):
    help = '初始化 Agent Tools 和 Skill Optimizer 菜单、权限及管理员角色'

    def handle(self, *args, **options):
        """幂等写入菜单、权限并把全部权限授予 Agent Tools 管理员。"""
        operator = User.objects.filter(is_superuser=True).order_by('sys_create_datetime').first()
        # 清理已废弃的目录树，避免旧 /ai-tools 与当前菜单同时出现在侧边栏。
        Menu.objects.filter(path__in=[
            '/tools', '/tools/agent-skills',
            '/ai-tools', '/ai-tools/agent-hub', '/ai-tools/agent-skills',
            '/ai-tools/agent-skills/records', '/ai-tools/model-config',
            '/agent-tools', '/agent-tools/agent-hub', '/agent-tools/hub',
            '/agent-tools/skill-optimizer', '/agent-tools/skill-optimizer/records',
            '/agent-tools/model-config',
        ]).delete()
        menus = self._seed_menus(operator)
        self._seed_permissions(menus, operator)
        user_role, _ = Role.objects.update_or_create(code='tools_user', defaults={'name': 'AI 辅助工具用户', 'description': '使用已授权的 AI 辅助工具', 'role_type': 1, 'status': True, 'priority': 50, 'sys_creator': operator, 'sys_modifier': operator})
        admin_role, _ = Role.objects.update_or_create(code='tools_admin', defaults={'name': 'AI 辅助工具管理员', 'description': '维护模型档案和 AI 辅助工具', 'role_type': 1, 'status': True, 'priority': 50, 'sys_creator': operator, 'sys_modifier': operator})
        user_menus = [menus['agent_tools'], menus['skill_optimizer_workbench'], menus['skill_optimizer_editor'], menus['agent_tools_providers'], menus['code_quality_governance']]
        user_permissions = Permission.objects.filter(code__startswith='agent-tools:skill-optimizer:') | Permission.objects.filter(code__startswith='agent-tools:providers:') | Permission.objects.filter(code__startswith='agent-tools:code-quality-governance:')
        user_role.menu.add(*user_menus)
        user_role.permission.add(*user_permissions)
        admin_role.menu.add(*menus.values())
        admin_role.permission.add(*user_permissions)
        MenuCacheManager.invalidate_menu_cache(); PermissionCacheManager.invalidate_permission_cache(); PermissionCacheManager.invalidate_global_permissions()
        self.stdout.write(self.style.SUCCESS('Agent Tools 初始化完成。'))

    def _seed_menus(self, operator):
        """初始化 Agent Tools 一级目录及 Skill Optimizer 子页面。"""
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
