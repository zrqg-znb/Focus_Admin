---
title: 交付矩阵
description: Focus 交付矩阵模块说明
---

<script setup lang="ts">
import { getFocusModule } from '../data/modules';

const moduleMeta = getFocusModule('delivery-matrix');

const apis = [
  {
    consumer: '矩阵树视图',
    method: 'GET',
    params: '无',
    path: '/api/delivery-matrix/tree',
    purpose: '返回交付矩阵组织树和岗位信息',
    returns: 'OrgNode[]',
  },
  {
    consumer: '管理端新建节点',
    method: 'POST',
    params: 'name, parent_id, linked_project_id, positions',
    path: '/api/delivery-matrix/nodes',
    purpose: '创建交付矩阵节点',
    returns: 'OrgNode',
  },
  {
    consumer: '节点编辑',
    method: 'PUT',
    params: 'name, description, parent_id, sort_order',
    path: '/api/delivery-matrix/nodes/{id}',
    purpose: '更新节点基础信息',
    returns: 'OrgNode',
  },
  {
    consumer: '岗位维护',
    method: 'PUT',
    params: 'positions[]',
    path: '/api/delivery-matrix/nodes/{id}/positions',
    purpose: '维护节点下岗位与责任人信息',
    returns: 'PositionStaff[]',
  },
];
</script>

<FocusModuleHero :module="moduleMeta" />

## 模块定位

交付矩阵用于从组织与项目群视角观察交付责任分布，不再局限于单项目页面。它适合回答“谁负责哪块交付、哪个节点挂着哪个项目、当前组织结构是否合理”这类管理问题。

## 当前已实现的能力

- 用树结构维护交付组织节点
- 节点可关联项目，形成组织与项目的映射
- 节点下可维护岗位和岗位人员
- 支持管理端和看板端两类使用视图

## 实现逻辑

- 前端 API 位于 `src/api/delivery-matrix/index.ts`
- 页面分为 `dashboard` 与 `admin` 两类视图
- 后端围绕树节点、岗位和父子关系展开，适合做组织层管理

## 核心 API

<FocusApiTable :items="apis" />

## 前端入口

| 页面 | 路由 | 作用 |
| --- | --- | --- |
| 交付看板 | `/delivery-matrix/dashboard` | 查看交付矩阵整体结构 |
| 管理端 | `/delivery-matrix/admin` | 维护节点、岗位和项目映射 |

## 相关依赖

- [项目管理](/modules/project-manager)
- [集成报告](/modules/integration-report)
- [后端技术参考](/backend/apps/delivery-matrix)
- [前端页面参考](/frontend/views/delivery-matrix)
