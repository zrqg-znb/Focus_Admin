from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand

from apps.deepaudit.audit_rule.audit_rule_services import ensure_default_rule_sets
from apps.deepaudit.prompt_template.prompt_template_services import ensure_default_templates
from apps.deepaudit.scenario.scenario_services import ensure_default_scenarios
from common.fu_cache import MenuCacheManager, PermissionCacheManager
from core.menu.menu_model import Menu
from core.permission.permission_model import Permission
from core.user.user_model import User


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
    component: str | None = None
    menu_type: str = 'menu'
    order: int = 0
    redirect: str | None = None
    icon: str | None = None
    active_path: str | None = None
    hide_in_menu: bool = False
    hide_children_in_menu: bool = False
    keep_alive: bool = True
    auth_code: str | None = None
    link: str | None = None
    open_in_new_window: bool = False


MENU_SEEDS = [
    MenuSeed(
        'root',
        None,
        'FocusAudit 平台',
        'FocusAudit 平台',
        '/focusaudit',
        'BasicLayout',
        'catalog',
        90,
        None,
        'lucide:shield',
        hide_children_in_menu=True,
        link='/focusaudit-app/',
        open_in_new_window=True,
    ),
    MenuSeed('agent_audit', 'root', 'Agent审计', 'Agent审计', '/focusaudit/agent-audit', '/focusaudit/agent-audit/index', order=10, hide_in_menu=True, auth_code='deepaudit:agent-audit'),
    MenuSeed('dashboard', 'root', '仪表盘', '仪表盘', '/focusaudit/dashboard', '/focusaudit/dashboard/index', order=20, hide_in_menu=True, auth_code='deepaudit:dashboard'),
    MenuSeed('projects', 'root', '项目管理', '项目管理', '/focusaudit/projects', '/focusaudit/projects/index', order=30, hide_in_menu=True, auth_code='deepaudit:projects'),
    MenuSeed('instant_analysis', 'root', '即时分析', '即时分析', '/focusaudit/instant-analysis', '/focusaudit/instant-analysis/index', order=40, hide_in_menu=True, auth_code='deepaudit:instant-analysis'),
    MenuSeed('tasks', 'root', '任务中心', '任务中心', '/focusaudit/tasks', '/focusaudit/tasks/index', order=50, hide_in_menu=True, auth_code='deepaudit:tasks'),
    MenuSeed('rules', 'root', '审计规则', '审计规则', '/focusaudit/rules', '/focusaudit/rules/index', order=60, hide_in_menu=True, auth_code='deepaudit:rules'),
    MenuSeed('prompts', 'root', '提示词模板', '提示词模板', '/focusaudit/prompts', '/focusaudit/prompts/index', order=70, hide_in_menu=True, auth_code='deepaudit:prompts'),
    MenuSeed('scenarios', 'root', '场景管理', '场景管理', '/focusaudit/scenarios', '/focusaudit/scenarios/index', order=75, hide_in_menu=True, auth_code='deepaudit:scenarios'),
    MenuSeed('settings', 'root', '审计设置', '审计设置', '/focusaudit/settings', '/focusaudit/settings/index', order=80, hide_in_menu=True, auth_code='deepaudit:settings'),
    MenuSeed('recycle_bin', 'root', '回收站', '回收站', '/focusaudit/recycle-bin', '/focusaudit/recycle-bin/index', order=90, hide_in_menu=True, auth_code='deepaudit:recycle-bin'),
    MenuSeed('project_detail', 'projects', '项目详情', '项目详情', '/focusaudit/projects/:id', '/focusaudit/projects/detail', order=1, active_path='/focusaudit/projects', hide_in_menu=True, keep_alive=False, auth_code='deepaudit:projects:detail'),
    MenuSeed('task_detail', 'tasks', '任务详情', '任务详情', '/focusaudit/tasks/:id', '/focusaudit/tasks/detail', order=1, active_path='/focusaudit/tasks', hide_in_menu=True, keep_alive=False, auth_code='deepaudit:tasks:detail'),
    MenuSeed('agent_detail', 'agent_audit', 'Agent任务详情', 'Agent任务详情', '/focusaudit/agent-audit/:id', '/focusaudit/agent-audit/detail', order=1, active_path='/focusaudit/agent-audit', hide_in_menu=True, keep_alive=False, auth_code='deepaudit:agent-audit:detail'),
]


PERMISSION_SEEDS = {
    'dashboard': [
        {'name': '查看仪表盘', 'code': 'deepaudit:dashboard:view', 'permission_type': 0},
        {'name': '获取仪表盘概览', 'code': 'deepaudit:api:dashboard:overview', 'permission_type': 1, 'api_path': '/api/deepaudit/dashboard/overview', 'http_method': 'GET'},
    ],
    'projects': [
        {'name': '新建项目', 'code': 'deepaudit:projects:create', 'permission_type': 0},
        {'name': '编辑项目', 'code': 'deepaudit:projects:update', 'permission_type': 0},
        {'name': '删除项目', 'code': 'deepaudit:projects:delete', 'permission_type': 0},
        {'name': '恢复项目', 'code': 'deepaudit:projects:restore', 'permission_type': 0},
        {'name': '管理成员', 'code': 'deepaudit:projects:members', 'permission_type': 0},
        {'name': '导出报告', 'code': 'deepaudit:reports:export', 'permission_type': 0},
        {'name': '获取项目列表', 'code': 'deepaudit:api:projects:list', 'permission_type': 1, 'api_path': '/api/deepaudit/projects', 'http_method': 'GET'},
        {'name': '创建项目接口', 'code': 'deepaudit:api:projects:create', 'permission_type': 1, 'api_path': '/api/deepaudit/projects', 'http_method': 'POST'},
        {'name': '获取项目详情', 'code': 'deepaudit:api:projects:detail', 'permission_type': 1, 'api_path': '/api/deepaudit/projects/:id', 'http_method': 'GET'},
        {'name': '更新项目接口', 'code': 'deepaudit:api:projects:update', 'permission_type': 1, 'api_path': '/api/deepaudit/projects/:id', 'http_method': 'PUT'},
        {'name': '删除项目接口', 'code': 'deepaudit:api:projects:delete', 'permission_type': 1, 'api_path': '/api/deepaudit/projects/:id', 'http_method': 'DELETE'},
        {'name': '恢复项目接口', 'code': 'deepaudit:api:projects:restore', 'permission_type': 1, 'api_path': '/api/deepaudit/projects/:id/restore', 'http_method': 'POST'},
        {'name': '彻底删除项目接口', 'code': 'deepaudit:api:projects:purge', 'permission_type': 1, 'api_path': '/api/deepaudit/projects/:id/purge', 'http_method': 'DELETE'},
        {'name': '项目回收站', 'code': 'deepaudit:api:projects:recycle', 'permission_type': 1, 'api_path': '/api/deepaudit/projects/recycle-bin', 'http_method': 'GET'},
        {'name': '项目统计', 'code': 'deepaudit:api:projects:stats', 'permission_type': 1, 'api_path': '/api/deepaudit/projects/stats', 'http_method': 'GET'},
        {'name': '上传ZIP', 'code': 'deepaudit:api:projects:zip-upload', 'permission_type': 1, 'api_path': '/api/deepaudit/projects/:id/zip', 'http_method': 'POST'},
        {'name': '获取ZIP信息', 'code': 'deepaudit:api:projects:zip-get', 'permission_type': 1, 'api_path': '/api/deepaudit/projects/:id/zip', 'http_method': 'GET'},
        {'name': '删除ZIP', 'code': 'deepaudit:api:projects:zip-delete', 'permission_type': 1, 'api_path': '/api/deepaudit/projects/:id/zip', 'http_method': 'DELETE'},
        {'name': '获取分支列表', 'code': 'deepaudit:api:projects:branches', 'permission_type': 1, 'api_path': '/api/deepaudit/projects/:id/branches', 'http_method': 'GET'},
        {'name': '获取项目文件', 'code': 'deepaudit:api:projects:files', 'permission_type': 1, 'api_path': '/api/deepaudit/projects/:id/files', 'http_method': 'GET'},
    ],
    'project_detail': [
        {'name': '访问项目详情', 'code': 'deepaudit:projects:detail:view', 'permission_type': 0},
    ],
    'tasks': [
        {'name': '创建扫描任务', 'code': 'deepaudit:tasks:create', 'permission_type': 0},
        {'name': '取消任务', 'code': 'deepaudit:tasks:cancel', 'permission_type': 0},
        {'name': '更新问题状态', 'code': 'deepaudit:issues:update', 'permission_type': 0},
        {'name': '获取任务列表', 'code': 'deepaudit:api:tasks:list', 'permission_type': 1, 'api_path': '/api/deepaudit/tasks', 'http_method': 'GET'},
        {'name': '获取任务详情', 'code': 'deepaudit:api:tasks:detail', 'permission_type': 1, 'api_path': '/api/deepaudit/tasks/:id', 'http_method': 'GET'},
        {'name': '获取问题列表', 'code': 'deepaudit:api:tasks:issues', 'permission_type': 1, 'api_path': '/api/deepaudit/tasks/:id/issues', 'http_method': 'GET'},
        {'name': '更新问题状态接口', 'code': 'deepaudit:api:tasks:issue-update', 'permission_type': 1, 'api_path': '/api/deepaudit/tasks/:id/issues/:id', 'http_method': 'PUT'},
        {'name': '取消任务接口', 'code': 'deepaudit:api:tasks:cancel', 'permission_type': 1, 'api_path': '/api/deepaudit/tasks/:id/cancel', 'http_method': 'POST'},
    ],
    'task_detail': [
        {'name': '访问任务详情', 'code': 'deepaudit:tasks:detail:view', 'permission_type': 0},
    ],
    'agent_audit': [
        {'name': '创建Agent任务', 'code': 'deepaudit:agent-tasks:create', 'permission_type': 0},
        {'name': '取消Agent任务', 'code': 'deepaudit:agent-tasks:cancel', 'permission_type': 0},
        {'name': '获取Agent任务列表', 'code': 'deepaudit:api:agent-tasks:list', 'permission_type': 1, 'api_path': '/api/deepaudit/agent-tasks', 'http_method': 'GET'},
        {'name': '创建Agent任务接口', 'code': 'deepaudit:api:agent-tasks:create', 'permission_type': 1, 'api_path': '/api/deepaudit/agent-tasks', 'http_method': 'POST'},
        {'name': '获取Agent详情', 'code': 'deepaudit:api:agent-tasks:detail', 'permission_type': 1, 'api_path': '/api/deepaudit/agent-tasks/:id', 'http_method': 'GET'},
        {'name': '取消Agent任务接口', 'code': 'deepaudit:api:agent-tasks:cancel', 'permission_type': 1, 'api_path': '/api/deepaudit/agent-tasks/:id/cancel', 'http_method': 'POST'},
        {'name': '获取Agent事件', 'code': 'deepaudit:api:agent-tasks:events', 'permission_type': 1, 'api_path': '/api/deepaudit/agent-tasks/:id/events', 'http_method': 'GET'},
        {'name': '获取Agent发现', 'code': 'deepaudit:api:agent-tasks:findings', 'permission_type': 1, 'api_path': '/api/deepaudit/agent-tasks/:id/findings', 'http_method': 'GET'},
        {'name': '更新Agent发现', 'code': 'deepaudit:api:agent-tasks:finding-update', 'permission_type': 1, 'api_path': '/api/deepaudit/agent-tasks/:id/findings/:id', 'http_method': 'PUT'},
        {'name': '获取Agent摘要', 'code': 'deepaudit:api:agent-tasks:summary', 'permission_type': 1, 'api_path': '/api/deepaudit/agent-tasks/:id/summary', 'http_method': 'GET'},
        {'name': '获取Agent检查点', 'code': 'deepaudit:api:agent-tasks:checkpoints', 'permission_type': 1, 'api_path': '/api/deepaudit/agent-tasks/:id/checkpoints', 'http_method': 'GET'},
        {'name': '获取Agent检查点详情', 'code': 'deepaudit:api:agent-tasks:checkpoint-detail', 'permission_type': 1, 'api_path': '/api/deepaudit/agent-tasks/:id/checkpoints/:id', 'http_method': 'GET'},
        {'name': '从检查点恢复Agent任务', 'code': 'deepaudit:api:agent-tasks:checkpoint-resume', 'permission_type': 1, 'api_path': '/api/deepaudit/agent-tasks/:id/checkpoints/:id/resume', 'http_method': 'POST'},
        {'name': '获取Agent树', 'code': 'deepaudit:api:agent-tasks:tree', 'permission_type': 1, 'api_path': '/api/deepaudit/agent-tasks/:id/tree', 'http_method': 'GET'},
    ],
    'agent_detail': [
        {'name': '访问Agent详情', 'code': 'deepaudit:agent-tasks:detail:view', 'permission_type': 0},
    ],
    'instant_analysis': [
        {'name': '即时分析', 'code': 'deepaudit:instant-analysis:run', 'permission_type': 0},
        {'name': '即时分析接口', 'code': 'deepaudit:api:scan:instant', 'permission_type': 1, 'api_path': '/api/deepaudit/scan/instant', 'http_method': 'POST'},
        {'name': '即时分析历史', 'code': 'deepaudit:api:scan:instant-history', 'permission_type': 1, 'api_path': '/api/deepaudit/scan/instant/history', 'http_method': 'GET'},
        {'name': '即时分析详情', 'code': 'deepaudit:api:scan:instant-detail', 'permission_type': 1, 'api_path': '/api/deepaudit/scan/instant/history/:id', 'http_method': 'GET'},
        {'name': '删除即时分析', 'code': 'deepaudit:api:scan:instant-delete', 'permission_type': 1, 'api_path': '/api/deepaudit/scan/instant/history/:id', 'http_method': 'DELETE'},
        {'name': '清空即时分析', 'code': 'deepaudit:api:scan:instant-clear', 'permission_type': 1, 'api_path': '/api/deepaudit/scan/instant/history', 'http_method': 'DELETE'},
        {'name': '仓库扫描接口', 'code': 'deepaudit:api:scan:repository', 'permission_type': 1, 'api_path': '/api/deepaudit/scan/repository', 'http_method': 'POST'},
        {'name': 'ZIP扫描接口', 'code': 'deepaudit:api:scan:zip', 'permission_type': 1, 'api_path': '/api/deepaudit/scan/zip', 'http_method': 'POST'},
    ],
    'rules': [
        {'name': '管理规则集', 'code': 'deepaudit:rules:manage', 'permission_type': 0},
        {'name': '获取规则集列表', 'code': 'deepaudit:api:rules:list', 'permission_type': 1, 'api_path': '/api/deepaudit/rules', 'http_method': 'GET'},
        {'name': '创建规则集', 'code': 'deepaudit:api:rules:create', 'permission_type': 1, 'api_path': '/api/deepaudit/rules', 'http_method': 'POST'},
        {'name': '获取规则集详情', 'code': 'deepaudit:api:rules:detail', 'permission_type': 1, 'api_path': '/api/deepaudit/rules/:id', 'http_method': 'GET'},
        {'name': '更新规则集', 'code': 'deepaudit:api:rules:update', 'permission_type': 1, 'api_path': '/api/deepaudit/rules/:id', 'http_method': 'PUT'},
        {'name': '删除规则集', 'code': 'deepaudit:api:rules:delete', 'permission_type': 1, 'api_path': '/api/deepaudit/rules/:id', 'http_method': 'DELETE'},
        {'name': '设置默认规则集', 'code': 'deepaudit:api:rules:set-default', 'permission_type': 1, 'api_path': '/api/deepaudit/rules/:id/set-default', 'http_method': 'POST'},
        {'name': '导出规则集', 'code': 'deepaudit:api:rules:export', 'permission_type': 1, 'api_path': '/api/deepaudit/rules/:id/export', 'http_method': 'GET'},
        {'name': '导入规则集', 'code': 'deepaudit:api:rules:import', 'permission_type': 1, 'api_path': '/api/deepaudit/rules/import', 'http_method': 'POST'},
        {'name': '新增规则', 'code': 'deepaudit:api:rules:add-rule', 'permission_type': 1, 'api_path': '/api/deepaudit/rules/:id/rules', 'http_method': 'POST'},
        {'name': '更新规则', 'code': 'deepaudit:api:rules:update-rule', 'permission_type': 1, 'api_path': '/api/deepaudit/rules/:id/rules/:id', 'http_method': 'PUT'},
        {'name': '删除规则', 'code': 'deepaudit:api:rules:delete-rule', 'permission_type': 1, 'api_path': '/api/deepaudit/rules/:id/rules/:id', 'http_method': 'DELETE'},
        {'name': '切换规则状态', 'code': 'deepaudit:api:rules:toggle-rule', 'permission_type': 1, 'api_path': '/api/deepaudit/rules/:id/rules/:id/toggle', 'http_method': 'PUT'},
    ],
    'prompts': [
        {'name': '管理提示词', 'code': 'deepaudit:prompts:manage', 'permission_type': 0},
        {'name': '获取提示词列表', 'code': 'deepaudit:api:prompts:list', 'permission_type': 1, 'api_path': '/api/deepaudit/prompts', 'http_method': 'GET'},
        {'name': '创建提示词', 'code': 'deepaudit:api:prompts:create', 'permission_type': 1, 'api_path': '/api/deepaudit/prompts', 'http_method': 'POST'},
        {'name': '获取提示词详情', 'code': 'deepaudit:api:prompts:detail', 'permission_type': 1, 'api_path': '/api/deepaudit/prompts/:id', 'http_method': 'GET'},
        {'name': '更新提示词', 'code': 'deepaudit:api:prompts:update', 'permission_type': 1, 'api_path': '/api/deepaudit/prompts/:id', 'http_method': 'PUT'},
        {'name': '删除提示词', 'code': 'deepaudit:api:prompts:delete', 'permission_type': 1, 'api_path': '/api/deepaudit/prompts/:id', 'http_method': 'DELETE'},
        {'name': '设置默认提示词', 'code': 'deepaudit:api:prompts:set-default', 'permission_type': 1, 'api_path': '/api/deepaudit/prompts/:id/set-default', 'http_method': 'POST'},
        {'name': '测试提示词', 'code': 'deepaudit:api:prompts:test', 'permission_type': 1, 'api_path': '/api/deepaudit/prompts/test', 'http_method': 'POST'},
    ],
    'scenarios': [
        {'name': '管理场景', 'code': 'deepaudit:scenarios:manage', 'permission_type': 0},
        {'name': '获取场景列表', 'code': 'deepaudit:api:scenarios:list', 'permission_type': 1, 'api_path': '/api/deepaudit/scenarios', 'http_method': 'GET'},
        {'name': '创建场景', 'code': 'deepaudit:api:scenarios:create', 'permission_type': 1, 'api_path': '/api/deepaudit/scenarios', 'http_method': 'POST'},
        {'name': '获取场景详情', 'code': 'deepaudit:api:scenarios:detail', 'permission_type': 1, 'api_path': '/api/deepaudit/scenarios/:id', 'http_method': 'GET'},
        {'name': '更新场景', 'code': 'deepaudit:api:scenarios:update', 'permission_type': 1, 'api_path': '/api/deepaudit/scenarios/:id', 'http_method': 'PUT'},
        {'name': '复制场景', 'code': 'deepaudit:api:scenarios:copy', 'permission_type': 1, 'api_path': '/api/deepaudit/scenarios/:id/copy', 'http_method': 'POST'},
        {'name': '删除场景', 'code': 'deepaudit:api:scenarios:delete', 'permission_type': 1, 'api_path': '/api/deepaudit/scenarios/:id', 'http_method': 'DELETE'},
        {'name': '设为默认场景', 'code': 'deepaudit:api:scenarios:set-default', 'permission_type': 1, 'api_path': '/api/deepaudit/scenarios/:id/set-default', 'http_method': 'POST'},
    ],
    'settings': [
        {'name': '保存个人设置', 'code': 'deepaudit:settings:save', 'permission_type': 0},
        {'name': '获取我的设置', 'code': 'deepaudit:api:settings:get', 'permission_type': 1, 'api_path': '/api/deepaudit/settings/me', 'http_method': 'GET'},
        {'name': '获取默认设置', 'code': 'deepaudit:api:settings:defaults', 'permission_type': 1, 'api_path': '/api/deepaudit/settings/defaults', 'http_method': 'GET'},
        {'name': '保存我的设置接口', 'code': 'deepaudit:api:settings:update', 'permission_type': 1, 'api_path': '/api/deepaudit/settings/me', 'http_method': 'PUT'},
        {'name': '重置我的设置', 'code': 'deepaudit:api:settings:reset', 'permission_type': 1, 'api_path': '/api/deepaudit/settings/me', 'http_method': 'DELETE'},
        {'name': '测试LLM连接', 'code': 'deepaudit:api:settings:test-llm', 'permission_type': 1, 'api_path': '/api/deepaudit/settings/test-llm', 'http_method': 'POST'},
        {'name': '获取LLM Provider', 'code': 'deepaudit:api:settings:llm-providers', 'permission_type': 1, 'api_path': '/api/deepaudit/settings/llm-providers', 'http_method': 'GET'},
        {'name': '获取Embedding配置', 'code': 'deepaudit:api:embedding:get', 'permission_type': 1, 'api_path': '/api/deepaudit/embedding/config', 'http_method': 'GET'},
        {'name': '更新Embedding配置', 'code': 'deepaudit:api:embedding:update', 'permission_type': 1, 'api_path': '/api/deepaudit/embedding/config', 'http_method': 'PUT'},
        {'name': '获取Embedding Provider', 'code': 'deepaudit:api:embedding:providers', 'permission_type': 1, 'api_path': '/api/deepaudit/embedding/providers', 'http_method': 'GET'},
        {'name': '获取Embedding模型', 'code': 'deepaudit:api:embedding:models', 'permission_type': 1, 'api_path': '/api/deepaudit/embedding/models/:provider', 'http_method': 'GET'},
        {'name': '测试Embedding', 'code': 'deepaudit:api:embedding:test', 'permission_type': 1, 'api_path': '/api/deepaudit/embedding/test', 'http_method': 'POST'},
        {'name': '获取SSH凭据', 'code': 'deepaudit:api:ssh:get', 'permission_type': 1, 'api_path': '/api/deepaudit/ssh-keys', 'http_method': 'GET'},
        {'name': '保存SSH凭据', 'code': 'deepaudit:api:ssh:save', 'permission_type': 1, 'api_path': '/api/deepaudit/ssh-keys', 'http_method': 'POST'},
        {'name': '生成SSH凭据', 'code': 'deepaudit:api:ssh:generate', 'permission_type': 1, 'api_path': '/api/deepaudit/ssh-keys/generate', 'http_method': 'POST'},
        {'name': '测试SSH凭据', 'code': 'deepaudit:api:ssh:test', 'permission_type': 1, 'api_path': '/api/deepaudit/ssh-keys/test', 'http_method': 'POST'},
        {'name': '清空SSH known_hosts', 'code': 'deepaudit:api:ssh:known-hosts-clear', 'permission_type': 1, 'api_path': '/api/deepaudit/ssh-keys/known-hosts', 'http_method': 'DELETE'},
        {'name': '删除SSH凭据', 'code': 'deepaudit:api:ssh:delete', 'permission_type': 1, 'api_path': '/api/deepaudit/ssh-keys', 'http_method': 'DELETE'},
    ],
    'rag': [
        {'name': '查看RAG状态', 'code': 'deepaudit:rag:status', 'permission_type': 0},
        {'name': '重建RAG索引', 'code': 'deepaudit:rag:rebuild', 'permission_type': 0},
        {'name': '查询RAG索引', 'code': 'deepaudit:rag:query', 'permission_type': 0},
        {'name': '查看知识库', 'code': 'deepaudit:knowledge:view', 'permission_type': 0},
        {'name': '管理知识库', 'code': 'deepaudit:knowledge:manage', 'permission_type': 0},
        {'name': '获取RAG状态接口', 'code': 'deepaudit:api:rag:status', 'permission_type': 1, 'api_path': '/api/deepaudit/rag/projects/:id/status', 'http_method': 'GET'},
        {'name': '重建RAG索引接口', 'code': 'deepaudit:api:rag:rebuild', 'permission_type': 1, 'api_path': '/api/deepaudit/rag/projects/:id/rebuild', 'http_method': 'POST'},
        {'name': '查询RAG索引接口', 'code': 'deepaudit:api:rag:query', 'permission_type': 1, 'api_path': '/api/deepaudit/rag/projects/:id/query', 'http_method': 'POST'},
        {'name': '获取知识库状态接口', 'code': 'deepaudit:api:knowledge:status', 'permission_type': 1, 'api_path': '/api/deepaudit/rag/knowledge/status', 'http_method': 'GET'},
        {'name': '获取知识库列表接口', 'code': 'deepaudit:api:knowledge:list', 'permission_type': 1, 'api_path': '/api/deepaudit/rag/knowledge/modules', 'http_method': 'GET'},
        {'name': '获取知识库详情接口', 'code': 'deepaudit:api:knowledge:detail', 'permission_type': 1, 'api_path': '/api/deepaudit/rag/knowledge/modules/:id', 'http_method': 'GET'},
        {'name': '搜索知识库接口', 'code': 'deepaudit:api:knowledge:search', 'permission_type': 1, 'api_path': '/api/deepaudit/rag/knowledge/search', 'http_method': 'POST'},
        {'name': '重建知识库接口', 'code': 'deepaudit:api:knowledge:rebuild', 'permission_type': 1, 'api_path': '/api/deepaudit/rag/knowledge/rebuild', 'http_method': 'POST'},
        {'name': '创建知识条目接口', 'code': 'deepaudit:api:knowledge:save', 'permission_type': 1, 'api_path': '/api/deepaudit/rag/knowledge/modules', 'http_method': 'POST'},
        {'name': '上传知识文件接口', 'code': 'deepaudit:api:knowledge:upload', 'permission_type': 1, 'api_path': '/api/deepaudit/rag/knowledge/upload', 'http_method': 'POST'},
        {'name': '删除知识条目接口', 'code': 'deepaudit:api:knowledge:delete', 'permission_type': 1, 'api_path': '/api/deepaudit/rag/knowledge/modules/:id', 'http_method': 'DELETE'},
        {'name': '校验知识模块接口', 'code': 'deepaudit:api:knowledge:validate', 'permission_type': 1, 'api_path': '/api/deepaudit/rag/knowledge/validate', 'http_method': 'POST'},
    ],
    'recycle_bin': [
        {'name': '查看回收站', 'code': 'deepaudit:recycle-bin:view', 'permission_type': 0},
    ],
    'agent_audit_reports': [],
}


class Command(BaseCommand):
    help = '初始化 FocusAudit 菜单、权限以及默认模板/规则集'

    def handle(self, *args, **options):
        operator = User.objects.filter(is_superuser=True).order_by('sys_create_datetime').first()
        menus = self._seed_menus(operator)
        permission_count = self._seed_permissions(menus, operator)
        template_count = ensure_default_templates()
        rule_count = ensure_default_rule_sets()
        scenario_count = ensure_default_scenarios()
        MenuCacheManager.invalidate_menu_cache()
        PermissionCacheManager.invalidate_permission_cache()
        PermissionCacheManager.invalidate_global_permissions()
        self.stdout.write(self.style.SUCCESS(
            f'FocusAudit 初始化完成：菜单 {len(menus)} 项，权限 {permission_count} 项，模板 {template_count} 项，规则集 {rule_count} 项，场景 {scenario_count} 项。'
        ))

    def _seed_menus(self, operator):
        created = {}
        for seed in MENU_SEEDS:
            parent = created.get(seed.parent_key)
            menu = self._find_existing_menu(seed, parent)
            if not menu:
                menu = Menu(
                    parent=parent,
                    path=seed.path,
                    sys_creator=operator,
                )

            menu.parent = parent
            menu.path = seed.path
            menu.name = seed.name
            menu.title = seed.title
            menu.authCode = seed.auth_code
            menu.type = seed.menu_type
            menu.component = seed.component
            menu.redirect = seed.redirect
            menu.activePath = seed.active_path
            menu.icon = seed.icon
            menu.order = seed.order
            menu.hideInMenu = seed.hide_in_menu
            menu.hideChildrenInMenu = seed.hide_children_in_menu
            menu.keepAlive = seed.keep_alive
            menu.link = seed.link
            menu.openInNewWindow = seed.open_in_new_window
            menu.sys_modifier = operator
            menu.save()
            created[seed.key] = menu
        return created

    @staticmethod
    def _legacy_path(path: str | None) -> str | None:
        if not path:
            return path
        if path.startswith('/focusaudit'):
            return path.replace('/focusaudit', '/deepaudit', 1)
        return path

    @staticmethod
    def _legacy_link(link: str | None) -> str | None:
        if not link:
            return link
        if link.startswith('/focusaudit-app'):
            return link.replace('/focusaudit-app', '/deepaudit-app', 1)
        return link

    def _find_existing_menu(self, seed: MenuSeed, parent):
        exact_match = Menu.objects.filter(parent=parent, path=seed.path).order_by('sys_create_datetime').first()
        if exact_match:
            return exact_match

        legacy_path = self._legacy_path(seed.path)
        if legacy_path and legacy_path != seed.path:
            legacy_match = Menu.objects.filter(parent=parent, path=legacy_path).order_by('sys_create_datetime').first()
            if legacy_match:
                return legacy_match

        if seed.link:
            link_candidates = [seed.link]
            legacy_link = self._legacy_link(seed.link)
            if legacy_link and legacy_link != seed.link:
                link_candidates.append(legacy_link)
            link_match = Menu.objects.filter(parent=parent, link__in=link_candidates).order_by('sys_create_datetime').first()
            if link_match:
                return link_match

        return None

    def _seed_permissions(self, menus, operator) -> int:
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
                        'description': item.get('description') or item['name'],
                        'is_active': True,
                        'sys_creator': operator,
                        'sys_modifier': operator,
                    },
                )
                total += 1
        return total
