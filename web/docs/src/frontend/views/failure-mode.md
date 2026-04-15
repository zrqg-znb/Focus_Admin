# 故障模式页面

故障模式 (`failure-mode`) 模块页面用于在产品设计、开发及测试阶段记录并追踪系统潜在或已发生的故障模式，支持工作流管理与统计分析。

## 页面结构

该模块页面主要包含以下子领域：

### 1. 故障模式库 (Failure Mode)
位于 `views/failure-mode/index.vue` 及相关组件目录：
- **功能**：维护核心故障模式条目（Failure Mode），记录故障现象、原因、严重程度和 RPN 风险指数。
- **核心组件**：
  - `FailureModeDrawer.vue`：用于创建和编辑故障模式详细信息的右侧抽屉。
  - `RelationInsightDrawer.vue`：通过图谱形式展示该故障与产品线、基线、子系统的级联关系。
  - `StringListEditor.vue`：用于编辑故障模式中的多项列表（如修复措施、规避方案）。

### 2. 故障处理工作流 (Workflow)
位于 `views/failure-mode/workflow/`：
- **功能**：管理分配到特定角色的故障模式任务，跟踪处理状态。
- **核心组件**：
  - `TaskCreateDrawer.vue`：创建新故障分析或验证任务。
  - `FailureModeTransferDialog.vue`：用于任务交接或责任人转移的弹窗。
  - `LandingConfigDrawer.vue`：落地配置抽屉，确保分析出的对策能在对应基线或项目中实施。

### 3. 统计看板 (Statistics)
位于 `views/failure-mode/statistics/` 和 `product-statistics/`：
- **功能**：以多维度的图表形式展示各子系统的故障分布和高风险项趋势。
- **核心组件**：
  - `StatisticsBarChart.vue`：柱状图组件，按严重等级或子系统分类展示故障数。
  - `StatisticsPieChart.vue`：饼图组件，展示故障状态的占比。

### 4. 基础配置 (Config/Products/Roles)
- **功能**：管理产品线 (Products)、基线 (Baselines)、子系统结构 (Subsystems) 以及处理角色 (Roles)。
- **核心组件**：`SubsystemConfigDrawer.vue` 用于维护层级化的子系统架构。

## 交互设计

- 故障模式信息庞大，大量使用了抽屉 (`Drawer`) 和 弹窗 (`Dialog`) 来分离“列表浏览”与“详细编辑”操作。
- 表单中多处使用了树形选择器，用于关联多层级的子系统或产品基线。
