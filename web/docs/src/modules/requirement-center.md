---
title: 需求中心
description: Focus 需求中心模块设计说明
---

<script setup lang="ts">
import { getFocusModule } from '../data/modules';

const moduleMeta = getFocusModule('requirement-center');

const apis = [
  {
    consumer: '需求列表页',
    method: 'GET',
    params: 'page, pageSize, status, project_id, owner_id 等',
    path: '/api/requirement-center/requirements',
    purpose: '分页获取需求列表',
    returns: 'PaginatedResponse<RequirementItem>',
  },
  {
    consumer: '树形视图',
    method: 'GET',
    params: 'project_id, status, keyword',
    path: '/api/requirement-center/requirements/tree',
    purpose: '返回树状需求结构',
    returns: 'RequirementOut[]',
  },
  {
    consumer: '需求详情页',
    method: 'PUT',
    params: '需求基础字段、责任人、描述等',
    path: '/api/requirement-center/requirements/{id}',
    purpose: '更新需求详情',
    returns: 'RequirementOut',
  },
  {
    consumer: '状态流转按钮',
    method: 'POST',
    params: 'action, note',
    path: '/api/requirement-center/requirements/{id}/transition',
    purpose: '执行需求状态流转',
    returns: 'RequirementOut',
  },
  {
    consumer: '评论与协作区',
    method: 'POST',
    params: 'content, mention_ids',
    path: '/api/requirement-center/requirements/{id}/comments',
    purpose: '新增评论与协作记录',
    returns: 'RequirementCommentOut',
  },
  {
    consumer: '批量工具栏',
    method: 'POST',
    params: 'requirement_ids, owner_id / priority / note',
    path: '/api/requirement-center/requirements/batch/assign-owner',
    purpose: '批量分配责任人',
    returns: 'BatchActionOut',
  },
];
</script>

<FocusModuleHero :module="moduleMeta" />

<FocusModuleSection
  kicker="Module Purpose"
  title="模块定位"
  summary="需求中心负责把需求从想法、拆解、评审、分配到状态推进的全过程统一建模，成为 Focus 里跨角色协作最密集的业务模块之一。"
>

需求中心解决的不是“存一条需求”，而是解决需求对象在不同角色之间如何被共同理解和持续推进的问题：

- 产品经理需要拆解和规划
- 研发负责人需要分派和跟踪
- 团队成员需要评论、协作和推进状态

因此模块设计核心在于：让同一条需求可以同时被树状管理、看板推进和详情协作。

</FocusModuleSection>

<FocusModuleSection
  kicker="Design Structure"
  title="设计结构"
  summary="需求中心采用“统一需求对象 + 多视图协作”的设计，而不是为每种角色单独造一套数据模型。"
>

## 核心对象

`Requirement` 是模块核心对象，它需要同时承载：

- 父子层级关系
- 状态流转
- 责任人 / 评审人分工
- 评论与日志记录
- 批量操作和仪表盘统计

## 三种协作视图

### 1. 树状视图

解决需求拆解关系表达问题，适合规划阶段。

### 2. 看板视图

解决执行阶段的状态推进问题，适合每日协作和站会。

### 3. 详情视图

解决单条需求的深度编辑、评论和历史留痕问题。

设计重点是三种视图共享同一套需求对象，而不是三套互相同步的数据。

</FocusModuleSection>

<FocusModuleSection
  kicker="Lifecycle"
  title="需求生命周期"
  summary="需求中心的真正设计重心是状态流转，而不仅是列表查询。"
>

```text
创建需求
  ↓
拆解为子需求
  ↓
提交评审
  ↓
分配责任人
  ↓
状态流转（开发 / 测试 / 完成等）
  ↓
评论、日志与批量动作持续补充协作信息
```

模块价值在于：

- 把需求对象从静态记录变成持续推进的工作对象
- 让评审、责任分配和评论留痕都落在同一对象上

</FocusModuleSection>

<FocusModuleSection
  kicker="Functional Areas"
  title="功能分层"
  summary="当前实现主要由 4 类能力构成。"
>

### 需求建模层

- 创建、编辑、查看和拆解需求
- 维护父子层级和对象基础字段

### 协作推进层

- 提交评审
- 分配责任人
- 转交评审人
- 状态流转

### 留痕层

- 评论
- 操作日志
- 提及与协作记录

### 统计层

- 需求仪表盘
- 批量操作
- 状态与责任分布观察

</FocusModuleSection>

<FocusModuleSection
  kicker="Implementation"
  title="前后端实现逻辑"
  summary="需求中心虽然是协作模块，但实现层已经做了比较清晰的职责拆分。"
>

## 后端

- 总前缀为 `/api/requirement-center/requirements`
- 路由集中在 `requirement_api.py`
- 以需求对象为核心，围绕：
  - 列表 / 树
  - 详情 / 更新
  - 子需求
  - 提交 / 评审 / 指派 / 流转
  - 评论 / 日志
  - 批量操作
  - Dashboard 统计

## 前端

- 页面位于 `views/requirement-center/requirement`
- 主要文件包括：
  - `index.vue`
  - `detail.vue`
  - `dashboard.vue`
  - `modules/tree-table.vue`
  - `modules/board.vue`

前端设计重点：

- 通过树表与看板为不同阶段提供不同操作方式
- 通过详情页沉淀深度信息和历史记录
- 尽量避免用户在多个系统之间来回切换需求状态

</FocusModuleSection>

<FocusModuleSection
  kicker="Core APIs"
  title="核心 API 清单"
  summary="以下接口是需求中心最重要的协作入口。"
>

<FocusApiTable :items="apis" />

</FocusModuleSection>

<FocusModuleSection
  kicker="Frontend Entry"
  title="前端页面与职责"
  summary="需求中心页面结构本身就是协作模式的体现。"
>

| 页面 | 路由 | 页面职责 |
| --- | --- | --- |
| 需求主页 | `/requirement-center/requirement` | 进入需求列表、树表与看板协作 |
| 详情页 | `detail.vue` | 维护单条需求的完整信息、评论与日志 |
| 仪表盘 | `/requirement-center/requirement/dashboard` | 观察需求统计摘要 |
| 看板 | `modules/board.vue` | 以状态列方式推进需求 |
| 树表 | `modules/tree-table.vue` | 以层级结构拆解和浏览需求 |

</FocusModuleSection>

<FocusModuleSection
  kicker="Typical Scenarios"
  title="典型场景"
  summary="下面两个场景最能体现需求中心为什么不能只是一个 CRUD 页面。"
>

### 场景一：产品经理拆解需求

1. 创建一个高层需求
2. 在树状视图中逐级拆解为子需求
3. 进入详情页补充说明
4. 提交评审

### 场景二：研发团队推进需求

1. 团队在看板中查看当前需求状态
2. 为需求分配责任人
3. 通过评论沟通细节
4. 按流程推进状态并在仪表盘查看总体进展

</FocusModuleSection>

<FocusModuleSection
  kicker="Related Docs"
  title="相关文档"
  summary="需要继续查看技术实现或上下游关系时，可以从这里下钻。"
>

- [后端技术参考](/backend/apps/requirement-center)
- [前端页面参考](/frontend/views/requirement-center)
- [项目管理](/modules/project-manager)
- [工作台 / 仪表盘](/modules/dashboard)

</FocusModuleSection>
