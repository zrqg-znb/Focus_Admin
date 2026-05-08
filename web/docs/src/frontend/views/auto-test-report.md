# 自动化测试报告前端附录

自动化测试报告前端位于 `web/apps/web-ele/src/views/auto-test-report/`，按主数据管理和日报分析两条主线拆分。

页面内还共享一套领域状态，可在座舱 / 车控之间切换，并同步到路由 query，保证三个页面联动一致。

## 页面结构

- `vehicle-config/index.vue`
  平台与车型配置，车控领域下支持 VIU 编号子集维护
- `test-cases/index.vue`
  用例管理，车控领域下增加 VIU 编号选择、列表列和模板差异
- `daily-results/index.vue`
  每日执行概览与明细，车控领域下在明细和历史抽屉中展示 VIU 编号
- `components/test-case-history-drawer.vue`
  单用例历史执行抽屉，显示执行结果、异常原因和 VIU 编号
- `components/domain-switcher.vue`
  页面顶部统一的领域切换器

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
- 日报页同时展示全量车型概览和单车型明细，依旧按车型聚合
- 失败/超时结果允许补录异常原因，并支持使用建议原因
- 车控视图下，页面会根据车型配置自动限制可选 VIU 编号

## 对应主线文档

- [自动化测试报告](/modules/auto-test-report)
