---
title: 工作台 / 仪表盘
description: Focus 工作台与仪表盘模块说明
---

<script setup lang="ts">
import { getFocusModule } from '../data/modules';

const moduleMeta = getFocusModule('dashboard');

const apis = [
  {
    consumer: '工作台首页首屏聚合',
    method: 'GET',
    params: 'scope=all|favorites',
    path: '/api/dashboard/core-metrics',
    purpose: '返回代码质量、迭代、性能、DTS 等核心指标摘要',
    returns: 'CoreMetrics',
  },
  {
    consumer: '项目分布图、领域占比图',
    method: 'GET',
    params: 'scope',
    path: '/api/dashboard/project-distribution',
    purpose: '返回项目按领域、类型、平台的分布统计',
    returns: 'ProjectDistribution',
  },
  {
    consumer: '工作台项目时间轴',
    method: 'GET',
    params: 'scope, page, page_size, name',
    path: '/api/dashboard/project-timelines',
    purpose: '分页返回收藏项目或全部项目的时间轴与质量摘要',
    returns: 'PaginatedResponse<FavoriteProjectDetail>',
  },
  {
    consumer: '里程碑预警区块',
    method: 'GET',
    params: 'qg_types, scope, page, page_size',
    path: '/api/dashboard/milestones',
    purpose: '返回即将到达的里程碑节点和剩余天数',
    returns: 'PaginatedResponse<UpcomingMilestone>',
  },
];
</script>

<FocusModuleHero :module="moduleMeta" />

## 模块定位

工作台 / 仪表盘是用户进入 Focus 后看到的第一层聚合视图。它不负责维护具体业务数据，而是把项目管理、性能监控、需求中心和质量模块的摘要信息整合在一起，帮助不同角色快速判断当前优先级。

## 当前已实现的能力

### Analytics 总览

- 展示代码质量、迭代、性能、DTS 等多类核心指标摘要
- 提供项目维度、平台维度的分布图，用于观察结构性风险
- 支持即将到来的里程碑视图，帮助管理者快速定位时间压力

### Workspace 工作台

- 提供收藏项目、关注项目与个人工作区入口
- 用项目时间轴、里程碑节点和健康度摘要串联多模块信息
- 作为需求、性能、项目管理页面的快速跳转入口

## 实现逻辑

### 后端

- 聚合接口统一挂在 `/api/dashboard/*`
- 后端在接口层完成跨模块数据汇总，减少前端拼接成本
- `performance`、`project_manager`、`dts` 等模块的摘要结果在这里被整合成工作台视图

### 前端

- 页面位于 `views/dashboard/analytics` 与 `views/dashboard/workspace`
- API 封装在 `web/apps/web-ele/src/api/dashboard.ts`
- 页面通过并发请求获取聚合数据，再按卡片、图表和时间轴呈现

## 典型流程

1. 用户登录后进入工作台
2. 页面并发请求核心指标、项目分布、项目时间轴和里程碑列表
3. 用户从工作台卡片继续进入项目管理、性能监控或需求中心做深度处理

## 核心 API

<FocusApiTable :items="apis" />

## 前端入口

| 页面 | 路由 | 作用 |
| --- | --- | --- |
| Analytics | `/dashboard/analytics` | 偏管理视角的全局统计和趋势展示 |
| Workspace | `/dashboard/workspace` | 偏执行视角的项目工作台和快捷入口 |

## 相关依赖

- [项目管理](/modules/project-manager)
- [性能监控](/modules/performance)
- [需求中心](/modules/requirement-center)
- [前端页面参考](/frontend/views/dashboard)
