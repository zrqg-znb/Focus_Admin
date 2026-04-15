---
title: 自动化测试报告
description: Focus 自动化测试报告模块说明
---

<script setup lang="ts">
import { getFocusModule } from '../data/modules';

const moduleMeta = getFocusModule('auto-test-report');

const apis = [
  {
    consumer: '平台配置页',
    method: 'GET',
    params: '无',
    path: '/api/auto-test-report/platforms',
    purpose: '查询 MCU 平台配置列表',
    returns: 'McuPlatformItem[]',
  },
  {
    consumer: '车辆配置页',
    method: 'GET',
    params: 'page, pageSize, keyword',
    path: '/api/auto-test-report/vehicles',
    purpose: '分页获取车辆与设备配置',
    returns: 'VehicleItem[]',
  },
  {
    consumer: '用例管理页',
    method: 'POST',
    params: 'xlsx 文件',
    path: '/api/auto-test-report/test-cases/import',
    purpose: '批量导入测试用例',
    returns: 'ImportResult',
  },
  {
    consumer: '日报汇总页',
    method: 'GET',
    params: 'record_date, project_id 等',
    path: '/api/auto-test-report/daily-results/summary',
    purpose: '获取每日执行结果汇总',
    returns: 'DailySummary',
  },
  {
    consumer: '日报列表页',
    method: 'GET',
    params: '分页与筛选参数',
    path: '/api/auto-test-report/daily-results/list',
    purpose: '获取每日执行结果明细',
    returns: 'DailyResultItem[]',
  },
];
</script>

<FocusModuleHero :module="moduleMeta" />

## 模块定位

自动化测试报告模块用于把测试平台、车辆配置、用例定义和每日执行结果串成一条完整的数据链，帮助团队持续观察自动化验证覆盖率和执行状态。

## 当前已实现的能力

- 平台配置、车辆配置和测试用例维护
- 用例模板下载、批量导入和批量删除
- 每日结果汇总与明细查询
- 结果可回溯到具体平台、车辆和用例

## 实现逻辑

- 前端 API 位于 `src/api/auto-test-report/index.ts`
- 页面拆分为 `vehicle-config / test-cases / daily-results`
- 配置类页面承担主数据维护，日报类页面承担结果沉淀和统计

## 核心 API

<FocusApiTable :items="apis" />

## 前端入口

| 页面 | 路由 | 作用 |
| --- | --- | --- |
| 平台 / 车辆配置 | `/auto-test-report/vehicle-config` | 维护测试载体与软硬件环境 |
| 用例管理 | `/auto-test-report/test-cases` | 维护用例定义并支持导入导出 |
| 日报结果 | `/auto-test-report/daily-results` | 查看汇总结果和执行明细 |

## 相关依赖

- [集成报告](/modules/integration-report)
- [交付矩阵](/modules/delivery-matrix)
- [后端技术参考](/backend/apps/auto-test-report)
- [前端页面参考](/frontend/views/auto-test-report)
