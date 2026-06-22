# 集成报告 DT_FUZZ 数据接入

## 背景

每日集成报告需要在现有代码检测、DT 测试数据之外展示公司 DT_FUZZ 数据。DT_FUZZ 数据按邮件项目配置启用，并按配置中的多个分支分别采集。

## 行为

- 邮件项目配置新增 DT_FUZZ 开关与 `versionName`、`branch`、`pbiId`、`domian-id`、`project-id` 参数。
- 启用 DT_FUZZ 时五类参数均必填，`branch` 支持多值。
- 每日采集时每个分支请求一次数据湖，`dueDate` 固定为 `YYYY-MM-DD 12:00:00`。
- 如果当天请求返回空数据，自动降级请求前一天的 `12:00:00`。
- 当前环境无法访问数据湖，`IntegrationDataFetcher.fetch_dt_fuzz` 使用确定性 mock 数据，并保留真实请求 payload 的字段名。
- `/api/integration-report/history` 返回 `dt_fuzz_items`，前端每日数据页通过最后一个 `DT_FUZZ 数据` tab 展示。

## 边界

- DT_FUZZ 首版只进入页面展示，不进入每日邮件。
- 前端树形表格默认全部收缩，仅用户手动展开时展示子节点。
- `domian-id` 按数据湖接口给定拼写保留。
