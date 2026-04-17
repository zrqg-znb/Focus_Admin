# 性能监控前端附录

性能监控前端位于 `web/apps/web-ele/src/views/performance/`，当前重点页面是趋势看板与指标管理。

## 页面结构

- `dashboard/index.vue`
  性能监控主看板
- `dashboard/components/TrendChart.vue`
  趋势图展示

## API 入口

性能监控前端主要消费 `src/api/performance/*` 中的接口，用于：

- 指标树
- 指标列表
- 趋势数据
- 风险记录
- 导入任务

## 交互重点

- 先用树筛选分类 / 项目 / 模块
- 再加载指标列表与趋势数据
- 风险页承接异常记录的确认与处理

## 对应主线文档

- [性能监控](/modules/performance)
