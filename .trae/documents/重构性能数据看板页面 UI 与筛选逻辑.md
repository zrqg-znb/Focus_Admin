# 重构性能数据看板页面

## 目标
重构 `/Users/zrq/CodeSpace/PythonProjects/Focus_Admin/web/apps/web-ele/src/views/performance/dashboard/index.vue`，优化 UI 和筛选逻辑。

## 实施步骤

1.  **移除统计卡片**：
    - 删除 `pageStats` 状态定义及相关计算逻辑 (`recomputeStats`)。
    - 删除模板中的统计卡片部分。

2.  **重构筛选区域布局**：
    - 将顶部筛选区改为两行布局或更合理的 Flex 布局。
    - **左侧显眼位置**放置“车控/座舱”切换，使用 `ElRadioGroup` 配合 `RadioButton` 样式，调整 CSS 使其看起来像 Tab 切换。
    - **筛选控件**：
        - **项目**：`ElSelect`，选项来源于 `treeData`。
        - **模块**：新增 `ElSelect`，选项根据选中的项目从 `treeData` 中动态获取。
        - **芯片类型**：新增 `ElSelect`，选项通过调用 `getChipTypesApi` 动态获取。
        - **日期范围**：保留 `ElDatePicker`。

3.  **实现级联响应逻辑**：
    - 监听 `category` 变化：重置 `project`、`module`、`chip_type`。
    - 监听 `project` 变化：
        - 重置 `module`、`chip_type`。
        - 从 `treeData` 中提取当前项目的 `module` 列表。
        - 调用 `getChipTypesApi({ project: ... })` 获取当前项目的芯片类型列表。
    - 监听 `module`、`chip_type`、`dateRange` 变化：触发表格重新查询。

4.  **表格查询参数更新**：
    - 更新 `gridOptions.proxyConfig.ajax.query` 中的参数，加入 `module` 和 `chip_type`。

5.  **UI 样式优化**：
    - 使用 Tailwind CSS 类名优化间距和对齐。
    - 确保筛选控件对齐整齐。

## 验证
- 确认筛选条件级联生效（切项目 -> 模块/芯片选项变）。
- 确认表格数据根据筛选条件正确过滤。
- 确认 UI 布局符合“应用切换”的感觉。