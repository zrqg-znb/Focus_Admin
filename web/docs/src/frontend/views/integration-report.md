# 集成报告前端附录

集成报告前端位于 `web/apps/web-ele/src/views/integration-report/`，按配置、订阅、历史、邮件日志四个视角拆分。

## 页面结构

- `config/index.vue`
  项目采集配置维护
- `subscription/index.vue`
  用户订阅页
- `history/index.vue`
  历史指标趋势页
- `email-logs/index.vue`
  邮件投递日志页

## API 入口

- `src/api/integration-report/index.ts`

主要消费：

- `listIntegrationConfigsApi`
- `createIntegrationConfigApi`
- `updateIntegrationConfigApi`
- `initIntegrationConfigsApi`
- `listIntegrationProjectsApi`
- `toggleIntegrationSubscriptionApi`
- `queryIntegrationHistoryApi`
- `listEmailDeliveriesApi`

## 实现特点

- 配置页和订阅页共享同一组配置数据，但视图目标不同
- 历史页会按 `code_metrics / dt_metrics` 分组显示指标
- 邮件日志页以表格方式承接投递审计

## 对应主线文档

- [集成报告](/modules/integration-report)
