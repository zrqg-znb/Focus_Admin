# 需求总结看板交付延期排行

## 背景

需求总结看板已有开发/测试交付趋势和延期风险预览，但缺少按管理维度定位延期集中区域的排行视图。新增排行后，用户可以直接看到哪些责任 PL 组或项目的开发、测试交付延期数量最高。

## 接口口径

复用现有接口：

```text
POST /api/project-manager/requirement-board/summary
```

响应新增 `delivery_delay_rankings`：

- `pl_group.development`：责任 PL 组维度的开发交付延期排行。
- `pl_group.acceptance`：责任 PL 组维度的测试交付延期排行。
- `project.development`：项目维度的开发交付延期排行。
- `project.acceptance`：项目维度的测试交付延期排行。

每行包含：

- `dimension_id`
- `dimension_name`
- `total_count`
- `delayed_count`
- `delay_rate`
- `delayed_workload_man_day`
- `delayed_workload_kloc`

## 聚合规则

- 开发延期沿用明细字段 `is_dev_delayed`。
- 测试延期沿用明细字段 `is_test_delayed`。
- PL 组维度按 `responsible_pl_group_id/name` 聚合；未识别统一归入 `dimension_id=null`、`dimension_name=未识别PL领域`。
- 项目维度按 `project_id/project_name` 聚合；未匹配项目沿用现有项目汇总兜底名称。
- 排序按 `delayed_count desc`、`delay_rate desc`、`dimension_name asc`。
- 前端图表展示 Top 10，完整结果仍由 summary 响应提供。

## 缓存说明

summary cache key 升级到 `pm:requirement-board:summary:v7`，避免命中缺少 `delivery_delay_rankings` 的旧缓存。该字段会在 prepared cache、full filtered cache 和实时扫描三条 summary 计算路径中统一生成。

## 验收点

- 总结看板在交付趋势图下方展示 PL 组、项目两组延期排行。
- 每组包含开发交付延期和测试交付延期两张横向柱状图。
- tooltip 展示总需求数、延期数、延期率和延期工作量。
- 已预热全量缓存时，summary 仍从缓存过滤结果生成排行，不重新请求数据湖。
