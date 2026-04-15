---
title: 代码扫描
description: Focus 代码扫描模块说明
---

<script setup lang="ts">
import { getFocusModule } from '../data/modules';

const moduleMeta = getFocusModule('code-scan');

const apis = [
  {
    consumer: '扫描项目配置页',
    method: 'GET',
    params: 'page, pageSize, keyword',
    path: '/api/code-scan/projects',
    purpose: '分页获取扫描项目配置',
    returns: 'PaginatedResponse<ScanProjectItem>',
  },
  {
    consumer: '任务执行按钮',
    method: 'POST',
    params: 'projectId',
    path: '/api/code-scan/tasks/{projectId}/run',
    purpose: '触发项目扫描任务执行',
    returns: '任务启动结果',
  },
  {
    consumer: '任务列表页',
    method: 'GET',
    params: 'status, tool_name, page, pageSize',
    path: '/api/code-scan/tasks',
    purpose: '获取扫描任务执行记录',
    returns: 'PaginatedResponse<ScanTaskItem>',
  },
  {
    consumer: '结果页',
    method: 'GET',
    params: 'project_id, tool_name, severity, shield_status',
    path: '/api/code-scan/results',
    purpose: '查询最新扫描结果',
    returns: 'PaginatedResponse<LatestScanResultItem>',
  },
  {
    consumer: '误报屏蔽流程',
    method: 'POST',
    params: '扫描结果 ID、申请原因',
    path: '/api/code-scan/shield/apply',
    purpose: '提交屏蔽申请',
    returns: '屏蔽申请结果',
  },
  {
    consumer: '屏蔽审批页',
    method: 'POST',
    params: 'application_id, action, comment',
    path: '/api/code-scan/shield/audit',
    purpose: '对屏蔽申请进行审批',
    returns: '审批结果',
  },
];
</script>

<FocusModuleHero :module="moduleMeta" />

## 模块定位

代码扫描模块是 Focus 的基础执行平台，负责配置扫描项目、触发扫描任务、展示结果和管理屏蔽申请。它为代码合规、DeepAudit 等更高层能力提供原始扫描底座。

## 当前已实现的能力

- 管理扫描项目、仓库地址、分支与屏蔽前缀
- 触发扫描任务并查看任务状态与日志
- 浏览最新扫描结果和工具维度统计
- 支持误报屏蔽申请与审批闭环

## 实现逻辑

- 后端统一挂载在 `/api/code-scan/*`
- 前端视图拆分为 `project / audit / result / task-log`
- 结果侧同时承载执行结果浏览和屏蔽流转，是治理动作的核心落点

## 核心 API

<FocusApiTable :items="apis" />

## 前端入口

| 页面 | 路由 | 作用 |
| --- | --- | --- |
| 扫描项目 | `/code_scan/project` | 管理仓库、分支和项目配置 |
| 审计页 | `/code_scan/audit` | 查看项目总体审计状态 |
| 扫描结果 | `/code_scan/result` | 过滤查看最新问题与屏蔽状态 |
| 任务日志 | `/code_scan/task-log` | 追踪任务执行记录和日志 |

## 相关依赖

- [代码合规](/modules/code-compliance)
- [DeepAudit 智能审计](/modules/deepaudit)
- [后端技术参考](/backend/apps/code-scan)
- [前端页面参考](/frontend/views/code-scan)
