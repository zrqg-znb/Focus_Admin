import Dashboard from "@/pages/Dashboard";
import Projects from "@/pages/Projects";
import ProjectDetail from "@/pages/ProjectDetail";
import RecycleBin from "@/pages/RecycleBin";
import InstantAnalysis from "@/pages/InstantAnalysis";
import AuditTasks from "@/pages/AuditTasks";
import TaskDetail from "@/pages/TaskDetail";
import AgentAudit from "@/pages/AgentAudit";
import AdminDashboard from "@/pages/AdminDashboard";
import Account from "@/pages/Account";
import AuditRules from "@/pages/AuditRules";
import PromptManager from "@/pages/PromptManager";
import ScenarioManager from "@/pages/ScenarioManager";
import type { PermissionRequirement } from '@/shared/focus/focusPermission';
import {
  DEEPAUDIT_PAGE_CODES,
} from '@/shared/focus/focusPermission';
import type { ReactNode } from 'react';

export interface RouteConfig {
  name: string;
  path: string;
  element: ReactNode;
  requiredAccess?: PermissionRequirement;
  redirectToFirstAccessible?: boolean;
  visible?: boolean;
}

const routes: RouteConfig[] = [
  {
    name: "Agent审计",
    path: "/",
    element: <AgentAudit />,
    redirectToFirstAccessible: true,
    requiredAccess: DEEPAUDIT_PAGE_CODES.AGENT_AUDIT,
    visible: true,
  },
  {
    name: "Agent审计任务",
    path: "/agent-audit/:taskId",
    element: <AgentAudit />,
    requiredAccess: DEEPAUDIT_PAGE_CODES.AGENT_AUDIT,
    visible: false,
  },
  {
    name: "仪表盘",
    path: "/dashboard",
    element: <Dashboard />,
    requiredAccess: DEEPAUDIT_PAGE_CODES.DASHBOARD,
    visible: true,
  },
  {
    name: "项目管理",
    path: "/projects",
    element: <Projects />,
    requiredAccess: DEEPAUDIT_PAGE_CODES.PROJECTS,
    visible: true,
  },
  {
    name: "项目详情",
    path: "/projects/:id",
    element: <ProjectDetail />,
    requiredAccess: DEEPAUDIT_PAGE_CODES.PROJECTS,
    visible: false,
  },
  {
    name: "即时分析",
    path: "/instant-analysis",
    element: <InstantAnalysis />,
    requiredAccess: DEEPAUDIT_PAGE_CODES.INSTANT_ANALYSIS,
    visible: true,
  },
  {
    name: "审计任务",
    path: "/audit-tasks",
    element: <AuditTasks />,
    requiredAccess: DEEPAUDIT_PAGE_CODES.TASKS,
    visible: true,
  },
  {
    name: "任务详情",
    path: "/tasks/:id",
    element: <TaskDetail />,
    requiredAccess: DEEPAUDIT_PAGE_CODES.TASKS,
    visible: false,
  },
  {
    name: "审计规则",
    path: "/audit-rules",
    element: <AuditRules />,
    requiredAccess: DEEPAUDIT_PAGE_CODES.RULES,
    visible: true,
  },
  {
    name: "提示词管理",
    path: "/prompts",
    element: <PromptManager />,
    requiredAccess: DEEPAUDIT_PAGE_CODES.PROMPTS,
    visible: true,
  },
  {
    name: "场景管理",
    path: "/scenarios",
    element: <ScenarioManager />,
    requiredAccess: DEEPAUDIT_PAGE_CODES.SCENARIOS,
    visible: true,
  },
  {
    name: "系统管理",
    path: "/admin",
    element: <AdminDashboard />,
    requiredAccess: DEEPAUDIT_PAGE_CODES.SETTINGS,
    visible: true,
  },
  {
    name: "回收站",
    path: "/recycle-bin",
    element: <RecycleBin />,
    requiredAccess: DEEPAUDIT_PAGE_CODES.RECYCLE_BIN,
    visible: true,
  },
  {
    name: "账号管理",
    path: "/account",
    element: <Account />,
    visible: false, // 不在主导航显示，在侧边栏底部单独显示
  },
];

export default routes;
