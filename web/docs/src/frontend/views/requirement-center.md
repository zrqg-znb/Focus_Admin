# 需求中心页面

需求中心 (`requirement-center`) 模块前端页面支持敏捷团队进行从宏观特性（Feature）到具体开发任务（Task）的全生命周期追踪。

## 页面结构

该模块分为三个主要视图以满足不同角色的管理需求：

### 1. 需求树状表格 (Tree Table)
位于 `views/requirement-center/requirement/modules/tree-table.vue`：
- **功能**：以树状结构展示具有父子关系的需求，直观反映需求拆解层级。
- **交互**：支持节点展开/折叠、在特定节点下快速新建子需求、按状态或责任人进行全局过滤。
- **使用场景**：适合产品经理在规划阶段进行需求拆分与范围管理。

### 2. 敏捷看板 (Board)
位于 `views/requirement-center/requirement/modules/board.vue`：
- **功能**：按需求状态（如：新建、开发中、测试中、已发布）划分的看板列，以卡片形式展示单个需求。
- **交互**：支持拖拽卡片变更状态；点击卡片查看和编辑需求详情。
- **使用场景**：适合研发团队在每日站会上同步进度。

### 3. 需求仪表盘 (Dashboard)
位于 `views/requirement-center/requirement/dashboard.vue`：
- **功能**：展示当前项目或特定迭代内的需求统计数据，包括燃尽图、责任人负荷图和需求状态分布饼图。
- **交互**：通过顶部筛选器切换不同的项目或迭代，图表联动刷新。
- **使用场景**：适合项目经理或 Scrum Master 评估团队吞吐量和交付风险。

### 4. 需求详情 (Detail)
位于 `views/requirement-center/requirement/detail.vue`：
- **功能**：单一需求的完整属性页，包括详细描述（支持 Markdown/富文本）、附件、历史流转记录及子需求列表。

## 数据管理与通信

- **API 封装**：接口定义在 `@/api/requirement-center/requirement.ts`。
- **响应式更新**：看板拖拽和树状节点更新后，通过调用刷新方法并局部更新 Pinia 或组件内部状态，避免全量重新拉取数据，提升用户体验。
