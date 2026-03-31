# 故障模式 (Failure Mode) 工作流前端页面实施方案

## 1. 需求摘要 (Summary)
在完成故障模式工作流后端的基础上，前端需要新增以下视图与功能：
1. **工作流任务管理页面**：针对管理员、版本 SE、特性 SE 提供任务列表查看、状态筛选及操作入口。
2. **任务处理（梳理）与故障模式绑定**：特性 SE 在处理任务时，通过表格查看已绑定的数据，并通过一个“穿梭框（或左右选择弹窗）”组件对故障模式进行增删改查及绑定。
3. **产品基线页面**：按产品筛选，通过表格展示该产品当前已绑定的故障模式基线数据。

## 2. 现状分析 (Current State Analysis)
- 前端框架为 Vue3 + Element Plus + VbenAdmin 5.x。
- 现有 `failure-mode` 模块的列表展示**均使用项目内封装的 `ZqTable`**，为保持模块内体验和性能一致，新页面也将采用 `ZqTable`（已确认）。
- 现有的侧边栏编辑弹窗多使用 `ZqDrawer`，而关联选择功能多使用左右布局的 `ElDialog`（如 `RelationSelectorDialog.vue`），这非常契合“穿梭框”的需求。
- 后端菜单与路由通过 `init_failure_mode.py` 动态下发，前端页面路径与组件名称需严格匹配。

## 3. 提议更改 (Proposed Changes)

### 3.1 前端 API 层
- **新增文件**: `web/apps/web-ele/src/api/failure_mode_workflow.ts`
- **What**: 封装与后端 `/api/failure-mode/workflow/*` 对应的接口函数和 TypeScript 类型定义。
- **包含**: 
  - 产品列表 (`listProducts`)，更新产品归属人 (`updateProductOwner`)
  - 获取产品故障模式基线 (`listProductFailureModes`)
  - 任务列表 (`listTasks`)，创建任务 (`createTask`)，更新任务 (`updateTask`)
  - 获取任务关联故障模式 (`getTaskFailureModes`)，绑定故障模式 (`bindTaskFailureModes`)
  - 提交评审 (`submitTask`)，评审关闭 (`closeTask`)

### 3.2 工作流任务页面 (Task Management)
- **新增文件**: 
  - `web/apps/web-ele/src/views/failure-mode/workflow/tasks/index.vue`
  - `web/apps/web-ele/src/views/failure-mode/workflow/tasks/data.ts`
- **What & How**:
  - 页面顶部提供“任务状态”下拉筛选。
  - 使用 `useZqTable` 展示任务列表，列包含：任务名、类型、产品、子系统、状态、创建人、责任人、时间等。
  - **操作列逻辑**：
    - **版本 SE/管理员**：可见“新建任务”按钮（弹窗选择产品、子系统、责任人等）。在状态为“评审中”时可见“评审关闭”按钮（弹窗输入纪要）。
    - **特性 SE**：在状态为“梳理中”时可见“处理任务”按钮，点击打开任务详情/处理抽屉。

### 3.3 任务处理组件与穿梭框 (Task Handling & Transfer)
- **新增文件**:
  - `web/apps/web-ele/src/views/failure-mode/workflow/tasks/components/TaskHandlingDrawer.vue` (任务处理抽屉)
  - `web/apps/web-ele/src/views/failure-mode/workflow/tasks/components/FailureModeTransferDialog.vue` (故障模式穿梭框)
- **What & How**:
  - **`TaskHandlingDrawer`**: 抽屉组件。展示任务基本信息。主体为一个 `ZqTable`，列出当前任务已绑定的故障模式。包含一个“关联/编辑故障模式”按钮，点击后打开穿梭框弹窗。
  - **`FailureModeTransferDialog`**: 左右分栏对话框（参考现有 `RelationSelectorDialog` 体验）。
    - 左侧为全量 `FailureMode` 列表（支持分页、关键词/子系统搜索）。
    - 右侧为当前选中的 `FailureMode` 列表。
    - 点击“确定”时调用 `bindTaskFailureModes` 接口进行数据保存。

### 3.4 产品基线页面 (Product Baseline)
- **新增文件**:
  - `web/apps/web-ele/src/views/failure-mode/workflow/products/index.vue`
  - `web/apps/web-ele/src/views/failure-mode/workflow/products/data.ts`
- **What & How**:
  - 顶部表单栏：必选/单选一个“产品 (Product)”，支持按产品名称或 ID 过滤。也可以选择按“子系统”二级过滤。
  - 主体区域使用 `ZqTable` 展示 `ProductFailureMode` 列表（即每个产品下最终落盘的故障模式），列包含：产品名称、子系统、故障模式简述、创建时间等。

### 3.5 后端路由与菜单配置更新
- **修改文件**: `backend-django/apps/failure_mode/management/commands/init_failure_mode.py`
- **What**: 将新页面注册到动态菜单系统中。
- **配置**:
  - 父级菜单（如果需要可以创建一个“工作流管理”目录，或者直接放在 `failure_mode` 根目录下）。
  - 添加 `FailureModeTasks` 菜单项：`path: '/failure-mode/workflow/tasks'`, `component: '/failure-mode/workflow/tasks/index'`
  - 添加 `FailureModeProducts` 菜单项：`path: '/failure-mode/workflow/products'`, `component: '/failure-mode/workflow/products/index'`

## 4. 假设与决策 (Assumptions & Decisions)
1. **决策**: 放弃全局的 `VbenVxeGrid`，改用当前模块已有的 `ZqTable` 以保持 `failure-mode` 模块内的高度一致性。
2. **假设**: 穿梭框 (Transfer) 因为可能涉及大量故障模式数据，标准的 Element Plus `<el-transfer>` 在分页和复杂列搜索上较弱，因此采用类似双列表左右布局的自定义 `ElDialog`（左侧带分页与搜索搜索，右侧显示选中项），这也是高级后台常用的“穿梭框”替代形态。
3. **决策**: 在“产品基线”页面，如果默认不选产品可能数据量过大，初始加载时默认查询列表或由用户手动选择产品后再发起查询。

## 5. 验证步骤 (Verification Steps)
1. 编写完前端页面后，执行 `python manage.py init_failure_mode` 同步路由，并确认前端刷新后菜单中出现了“任务管理”和“产品基线”。
2. 启动前端服务，以不同角色（管理员、版本 SE、特性 SE）登录，验证：
   - 任务列表的按钮显示是否符合权限预期。
   - 特性 SE 点击“处理”，使用穿梭框双列弹窗选择故障模式并绑定，保存后表格更新。
   - 版本 SE 点击“关闭任务”，填写纪要后任务状态流转。
3. 在“产品基线”页面，筛选特定产品，验证是否能正确展示刚才任务中同步过来的故障模式数据。