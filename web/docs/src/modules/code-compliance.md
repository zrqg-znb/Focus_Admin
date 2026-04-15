---
title: 代码合规
description: Focus 代码合规模块说明
---

<script setup lang="ts">
import { getFocusModule } from '../data/modules';

const moduleMeta = getFocusModule('code-compliance');

const apis = [
  {
    consumer: '概览页面岗位统计',
    method: 'GET',
    params: '无',
    path: '/api/code-compliance/stats/post',
    purpose: '按岗位汇总合规风险与分支处理情况',
    returns: 'OverviewSummary',
  },
  {
    consumer: '详情页用户维度统计',
    method: 'GET',
    params: 'post_id, start_date, end_date',
    path: '/api/code-compliance/stats/post/{post_id}/users',
    purpose: '返回岗位下用户级别的风险统计明细',
    returns: 'DetailSummary',
  },
  {
    consumer: '用户风险详情抽屉',
    method: 'GET',
    params: 'user_id',
    path: '/api/code-compliance/user/{user_id}/records',
    purpose: '查询某个用户关联的合规风险记录',
    returns: 'ComplianceRecord[]',
  },
  {
    consumer: '风险处理动作',
    method: 'PUT',
    params: 'status, remark',
    path: '/api/code-compliance/branch/{branch_id}',
    purpose: '更新具体分支的处理状态',
    returns: '操作成功消息',
  },
  {
    consumer: '导入页',
    method: 'POST',
    params: 'xlsx/csv 文件',
    path: '/api/code-compliance/upload',
    purpose: '批量导入合规风险数据',
    returns: 'UploadResponse',
  },
];
</script>

<FocusModuleHero :module="moduleMeta" />

## 模块定位

代码合规模块关注“规范执行是否落地”，核心对象是合规风险记录与分支处理状态。它更偏治理与整改视角，而不是泛化的代码分析平台。

## 当前已实现的能力

- 以岗位、用户、分支三个层次查看合规风险
- 支持批量上传合规风险数据
- 支持按分支更新处理状态与备注
- 支持模板下载与整改明细查看

## 实现逻辑

- 后端以 `/api/code-compliance/*` 提供统计、记录与导入接口
- 前端 API 文件为 `src/api/compliance/index.ts`
- 页面通常由概览页、详情列表与处理动作组成，偏台账与追踪型交互

## 核心 API

<FocusApiTable :items="apis" />

## 前端入口

| 页面 | 路由 | 作用 |
| --- | --- | --- |
| 总览 | `/compliance/overview` | 查看岗位与用户维度的风险分布 |
| 明细 | `/compliance/detail` | 查看用户、分支与整改记录详情 |

## 相关依赖

- [代码扫描](/modules/code-scan)
- [后端技术参考](/backend/apps/code-compliance)
- [前端页面参考](/frontend/views/code-compliance)
