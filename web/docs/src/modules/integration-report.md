---
title: 集成报告
description: Focus 集成报告模块说明
---

<script setup lang="ts">
import { getFocusModule } from '../data/modules';

const moduleMeta = getFocusModule('integration-report');

const apis = [
  {
    consumer: '项目配置列表',
    method: 'GET',
    params: 'page, pageSize, keyword',
    path: '/api/integration-report/projects',
    purpose: '分页获取集成项目配置',
    returns: 'PaginatedResponse<ProjectConfigOut>',
  },
  {
    consumer: '配置管理页',
    method: 'GET',
    params: 'page, pageSize, status',
    path: '/api/integration-report/configs',
    purpose: '分页获取报告配置项',
    returns: 'PaginatedResponse<ProjectConfigManageRow>',
  },
  {
    consumer: '初始化配置',
    method: 'POST',
    params: '无',
    path: '/api/integration-report/configs/init',
    purpose: '初始化默认集成配置',
    returns: '初始化数量',
  },
  {
    consumer: '采集和联调',
    method: 'POST',
    params: 'recordDate, configId 等',
    path: '/api/integration-report/mock/collect',
    purpose: '执行模拟采集，用于联调和排障',
    returns: '执行结果',
  },
  {
    consumer: '历史页',
    method: 'GET',
    params: 'page, pageSize, start_date, end_date, status',
    path: '/api/integration-report/history',
    purpose: '查询采集和发送历史',
    returns: 'HistoryQueryOut',
  },
  {
    consumer: '邮件投递记录页',
    method: 'GET',
    params: 'status, user_id, to_email, page, pageSize',
    path: '/api/integration-report/email-deliveries',
    purpose: '查询邮件发送结果',
    returns: 'PaginatedResponse<EmailDeliveryRow>',
  },
];
</script>

<FocusModuleHero :module="moduleMeta" />

## 模块定位

集成报告用于承接外部系统数据、生成项目报告并对外发送。它强调的不是一次性导出，而是可配置、可采集、可追踪、可订阅的报告服务链路。

## 当前已实现的能力

- 管理集成项目与配置项
- 初始化默认配置并执行模拟采集
- 维护订阅关系和推送动作
- 查询历史采集记录与邮件投递记录

## 实现逻辑

- 后端 API 挂载在 `/api/integration-report/*`
- 前端页面拆分为 `config / history / subscription / email-logs`
- 交互围绕“配置 -> 采集 -> 历史 -> 投递”闭环展开

## 核心 API

<FocusApiTable :items="apis" />

## 前端入口

| 页面 | 路由 | 作用 |
| --- | --- | --- |
| 配置管理 | `/integration-report/config` | 管理项目与报告配置 |
| 历史记录 | `/integration-report/history` | 查看采集与生成历史 |
| 订阅管理 | `/integration-report/subscription` | 配置报告订阅关系 |
| 邮件日志 | `/integration-report/email-logs` | 查看投递状态与失败记录 |

## 相关依赖

- [交付矩阵](/modules/delivery-matrix)
- [自动化测试报告](/modules/auto-test-report)
- [后端技术参考](/backend/apps/integration-report)
- [前端页面参考](/frontend/views/integration-report)
