# 代码扫描前端附录

代码扫描前端位于 `web/apps/web-ele/src/views/code_scan/`，按项目配置、结果治理、审批与任务日志拆成多个页面。

## 页面结构

- `project/index.vue`
  扫描项目管理页
- `result/index.vue`
  最新结果页
- `audit/index.vue`
  屏蔽审批页
- `task-log/index.vue`
  解析任务日志页

## API 入口

- `src/api/code_scan/index.ts`

主要消费：

- `listProjectsApi`
- `listProjectOverviewApi`
- `listTasksApi`
- `listLatestResultsApi`
- `applyShieldApi`
- `listApplicationsApi`
- `auditShieldApi`

## 交互特点

- 项目页负责配置扫描项目，并跳转到结果页和日志页
- 结果页按项目读取“最新任务视图”，不是全历史结果
- 审批页负责处理 `Pending` 的屏蔽申请
- 日志页负责查看解析状态和原始日志

## 对应主线文档

- [代码扫描](/modules/code-scan)
