# 自动化测试报告前端附录

自动化测试报告前端位于 `web/apps/web-ele/src/views/auto-test-report/`，按主数据管理和日报分析两条主线拆分。

## 页面结构

- `vehicle-config/index.vue`
  平台与车型配置
- `test-cases/index.vue`
  用例管理
- `daily-results/index.vue`
  每日执行概览与明细
- `components/test-case-history-drawer.vue`
  单用例历史执行抽屉

## API 入口

- `src/api/auto-test-report/index.ts`

主要消费：

- `listPlatformsApi`
- `listVehiclesApi`
- `listTestCasesApi`
- `importTestCasesApi`
- `getDailySummaryApi`
- `getDailyOverviewApi`
- `listDailyResultsApi`
- `updateDailyResultFailureReasonApi`
- `getTestCaseHistoryApi`

## 实现特点

- 车型配置页可以直接跳转日报页
- 日报页同时展示全量车型概览和单车型明细
- 失败/超时结果允许补录异常原因，并支持使用建议原因

## 对应主线文档

- [自动化测试报告](/modules/auto-test-report)
