# 需求中心前端附录

需求中心前端位于 `web/apps/web-ele/src/views/requirement-center/`，当前以需求看板和工作区面板为核心。

## 页面结构

- `requirement/dashboard.vue`
  需求总览与统计入口

## 关联组件

- 工作台中的 `RequirementWorkspacePanel`
  会复用需求中心的聚合能力

## 实现特点

- 需求中心既有独立页面，也有嵌入式工作区能力
- 前端更偏聚合视图，而不是单纯 CRUD 表格

## 对应主线文档

- [需求中心](/modules/requirement-center)
