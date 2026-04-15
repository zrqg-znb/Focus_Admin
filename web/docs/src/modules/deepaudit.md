---
title: DeepAudit 智能审计
description: Focus DeepAudit 模块设计说明
---

<script setup lang="ts">
import { getFocusModule } from '../data/modules';

const moduleMeta = getFocusModule('deepaudit');

const apis = [
  {
    consumer: '项目接入页',
    method: 'GET',
    params: 'page, keyword 等',
    path: '/api/deepaudit/projects',
    purpose: '管理审计项目、仓库和绑定关系',
    returns: 'Project 列表',
  },
  {
    consumer: '成员管理页',
    method: 'POST',
    params: 'project_id, user_id, role',
    path: '/api/deepaudit/members/{project_id}',
    purpose: '管理项目成员与权限分工',
    returns: 'ProjectMemberSchema',
  },
  {
    consumer: '扫描与即时分析入口',
    method: 'POST',
    params: '项目、分支、规则、模型、扫描策略',
    path: '/api/deepaudit/scan/*',
    purpose: '发起扫描或即时分析任务',
    returns: '扫描任务结果',
  },
  {
    consumer: 'Agent 任务页',
    method: 'GET',
    params: 'task_id 或分页参数',
    path: '/api/deepaudit/agent-tasks/*',
    purpose: '查询多智能体任务的执行过程与输出',
    returns: 'AgentTask 结果',
  },
  {
    consumer: '规则与提示词管理',
    method: 'GET',
    params: '分页与过滤参数',
    path: '/api/deepaudit/rules / /api/deepaudit/prompts',
    purpose: '管理审计规则和提示词模板',
    returns: '规则 / 模板列表',
  },
  {
    consumer: '报告导出',
    method: 'GET',
    params: 'task_id / record_id',
    path: '/api/deepaudit/reports/tasks/{task_id}/pdf',
    purpose: '导出扫描任务或即时分析报告',
    returns: 'PDF / JSON 文件',
  },
];
</script>

<FocusModuleHero :module="moduleMeta" />

<FocusModuleSection
  kicker="Module Purpose"
  title="模块定位"
  summary="DeepAudit 是 Focus 中承接智能代码审计的能力中心，负责把扫描、知识库、模型和多智能体协作组织成一套可运行的系统。"
>

DeepAudit 的任务不是简单做一次“AI 问答”，而是构建一条可重复执行的智能审计流水线：

- 先接入代码仓库与项目上下文
- 再基于规则、模型和知识库组织分析任务
- 最后输出结构化报告，并沉淀任务过程与审计结论

它既是独立业务模块，也是 Focus 的平台级智能能力中心。

</FocusModuleSection>

<FocusModuleSection
  kicker="Design Structure"
  title="设计结构"
  summary="DeepAudit 的设计天然比普通业务模块更复杂，因为它需要同时管理项目、任务、模型、知识库和报告。"
>

## 结构分层

### 1. 项目接入层

- 管理仓库、成员、所有权和访问凭据
- 确保扫描任务有明确的代码上下文和协作边界

### 2. 扫描与任务层

- 包含扫描任务、即时分析任务和 Agent 任务
- 区分“任务发起入口”和“任务执行过程”

### 3. 智能能力层

- 规则：定义审计关注点
- Prompt：定义模型交互策略
- RAG：引入特定漏洞、框架和经验知识
- Embedding / Settings：决定知识检索和模型配置方式

### 4. 报告与看板层

- Dashboard 负责宏观观察任务与结果
- Reports 负责导出 PDF/JSON 等可交付成果

</FocusModuleSection>

<FocusModuleSection
  kicker="Key Objects"
  title="核心对象关系"
  summary="DeepAudit 的复杂度主要来自任务对象与智能能力对象之间的组合关系。"
>

```text
DeepAudit Project
  ├─ Members
  ├─ SSH Keys
  ├─ Scan Tasks
  ├─ Agent Tasks
  ├─ Audit Rules
  ├─ Prompt Templates
  └─ Reports

Knowledge & Intelligence Layer
  ├─ RAG Corpus
  ├─ Embedding Settings
  ├─ Prompt Templates
  └─ Rule Configs
```

设计要点：

- 项目对象负责界定分析上下文
- 任务对象负责记录每次执行过程
- 规则、Prompt 和知识库对象负责影响分析质量
- 报告对象负责沉淀最终可交付结果

</FocusModuleSection>

<FocusModuleSection
  kicker="Execution Flow"
  title="关键执行流程"
  summary="DeepAudit 最核心的不是页面，而是分析任务如何从发起走向结果沉淀。"
>

## 审计任务流

```text
配置项目与成员
  ↓
配置规则 / Prompt / 模型 / 知识库
  ↓
发起扫描或即时分析
  ↓
任务进入 Agent 协作与流式执行
  ↓
结果沉淀为任务记录与报告
```

## 为什么要拆成多对象

- 扫描任务和 Agent 任务分开，是为了区分“业务任务”与“智能体执行细节”
- 规则和 Prompt 分开，是为了让审计策略与模型表达方式可以独立迭代
- 报告独立导出，是为了让分析结果可以被审计、留档和复盘

</FocusModuleSection>

<FocusModuleSection
  kicker="Implementation"
  title="前后端实现逻辑"
  summary="DeepAudit 目前已经具备比较清晰的智能系统分层。"
>

## 后端

- 聚合路由位于 `backend-django/apps/deepaudit/router.py`
- 子域包括：
  - `projects`
  - `members`
  - `tasks`
  - `scan`
  - `agent-tasks`
  - `rules`
  - `prompts`
  - `settings`
  - `embedding`
  - `rag`
  - `reports`
  - `dashboard`
  - `data-tools`

后端实现重点：

- 统一编排审计项目与任务上下文
- 连接模型、提示词、知识库与规则
- 支持任务执行过程中的导出与追踪

## 前端

- DeepAudit 当前是独立前端应用 `web/apps/web-deepaudit`
- 更强调流式反馈、报告展示和任务过程可视化
- 与主 `web-ele` 应用相比，它更像一个专门的智能审计工作台

</FocusModuleSection>

<FocusModuleSection
  kicker="Core APIs"
  title="核心 API 清单"
  summary="以下接口代表了 DeepAudit 从项目接入到审计交付的关键路径。"
>

<FocusApiTable :items="apis" />

</FocusModuleSection>

<FocusModuleSection
  kicker="Frontend Entry"
  title="前端入口与主要页面"
  summary="DeepAudit 是独立应用，因此其页面心智与普通管理页不同。"
>

主要页面包括：

- 首页 / 审计入口
- 项目管理
- 扫描任务与即时分析
- 仪表盘
- 审计报告展示
- 审计流日志

这些页面共同服务“创建任务 -> 查看过程 -> 输出结果”的智能审计主线。

</FocusModuleSection>

<FocusModuleSection
  kicker="Typical Scenarios"
  title="典型场景"
  summary="DeepAudit 适合两类高价值场景。"
>

### 场景一：研发团队在合并前做一次智能审计

1. 选择项目和代码范围
2. 发起扫描或即时分析
3. 查看模型输出和结构化建议
4. 导出报告，进入整改流程

### 场景二：平台团队维护审计策略

1. 更新规则和 Prompt 模板
2. 补充特定漏洞或框架知识库
3. 通过多项目任务观察策略效果
4. 持续优化智能审计质量

</FocusModuleSection>

<FocusModuleSection
  kicker="Related Docs"
  title="相关文档"
  summary="需要继续查看技术实现或系统全局关系，可以从这里下钻。"
>

- [后端技术参考](/backend/apps/deepaudit)
- [系统架构](/overview/architecture)
- [代码扫描](/modules/code-scan)

</FocusModuleSection>
