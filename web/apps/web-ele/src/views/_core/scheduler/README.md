# New Schedule 定时任务管理（新UI）

新的定时任务管理界面，使用卡片列表组件（CardList）实现左侧任务列表，右侧显示任务详情。

## 目录结构

```
new-schedule/
├── index.vue                          # 主页面
├── data.ts                            # 工具函数和常量
├── README.md                          # 文档
└── modules/
    ├── scheduler-list-card.vue        # 左侧任务列表卡片（使用 CardList）
    ├── scheduler-job-detail.vue       # 右侧任务详情（待实现）
    └── scheduler-form-modal.vue       # 任务编辑表单模态框
```

## 功能概览

### 第一步：左侧任务列表卡片（已完成）

使用 `CardList` 公共组件实现：

- ✅ 搜索功能（按名称、编码搜索）
- ✅ 任务列表展示
- ✅ 项目选择
- ✅ 悬停显示编辑/删除按钮
- ✅ 新增任务
- ✅ 编辑任务
- ✅ 删除任务
- ✅ 任务自动选择

### 统计卡片设计（已完成）

采用 shadcn-ui Card 组件的高级设计：

- ✅ 使用 VbenCountToAnimator 做数值动画
- ✅ 左侧数值、右侧 icon 布局
- ✅ 底部说明文字
- ✅ 响应式网格（md:grid-cols-2 lg:grid-cols-4）
- ✅ 支持自定义 icon 和后缀

### 第二步：右侧任务详情（待实现）

计划实现的功能：

- ⏳ 显示选中任务的详细信息
- ⏳ 执行日志查看
- ⏳ 任务状态修改
- ⏳ 执行记录统计

## 组件说明

### index.vue

主页面组件，采用左右分布的布局：

**左侧区域**（固定宽度 400px）：
- 调度器控制面板（启动、停止、暂停、恢复）
- 任务列表卡片

**右侧区域**（伸缩）：
- 统计卡片（4 个卡片网格，使用 shadcn-ui Card 组件）
  - 每个卡片包含：标题、数值（带动画）、icon、说明文字
  - 支持响应式布局（md:grid-cols-2 lg:grid-cols-4）
- 任务详情面板

### scheduler-list-card.vue

使用 `CardList` 实现的任务列表卡片，提供：

- 基于 CardList 组件的统一界面
- 搜索和过滤
- CRUD 操作
- 模态框表单

### scheduler-job-detail.vue

任务详情组件（占位符）

### scheduler-form-modal.vue

任务编辑表单模态框，支持：

- 创建新任务
- 编辑现有任务
- 动态表单（根据触发器类型显示不同字段）

### data.ts

工具函数库：

- `getStatusName()` - 获取状态显示名称
- `getStatusType()` - 获取状态标签类型
- `getTriggerTypeOptions()` - 获取触发器类型选项
- `getJobStatusOptions()` - 获取任务状态选项
- `getTriggerTypeLabel()` - 获取触发器类型标签

## 使用 CardList 的特点

该组件充分利用了 CardList 的功能：

1. **插槽自定义**：
   - `#item` - 自定义标题行（任务名称）
   - `#details` - 自定义详细信息行（编码、类型、状态、执行次数）
   - `#actions` - 自定义操作按钮（编辑、删除）
   - `#modal` - 承载表单模态框

2. **搜索配置**：
   ```typescript
   const cardListOptions: CardListOptions<SchedulerJob> = {
     searchFields: [
       { field: 'name' },
       { field: 'code' },
     ],
     titleField: 'name',
   };
   ```

3. **事件处理**：
   - `@select` - 任务选择事件
   - `@add` - 新增按钮
   - `@edit` - 编辑按钮
   - `@delete` - 删除按钮
   - `@update:searchKeyword` - 搜索关键词变化
   - `@update:hoveredId` - 悬停状态变化

## 待实现功能

### 第二步：右侧任务详情面板

需要实现 `scheduler-job-detail.vue` 中的以下功能：

1. 任务基本信息展示
2. 执行统计信息
3. 最后执行时间和结果
4. 下次执行时间
5. 快速操作按钮
   - 手动触发执行
   - 启用/禁用
   - 查看执行日志

### 第三步及之后

- 执行日志面板
- 批量操作
- 更多高级功能

## 样式

所有样式使用 Tailwind CSS，遵循项目规范：

- 卡片间距：`gap-4`
- 内边距：`p-4`
- 圆角：`rounded-[8px]`
- 颜色方案：保持一致性

## 类型定义

所有类型从 `#/api/core/scheduler` 导入：

- `SchedulerJob` - 定时任务类型
- `SchedulerJobCreateInput` - 创建任务输入
- `SchedulerJobUpdateInput` - 更新任务输入
- `SchedulerJobListParams` - 列表查询参数

## API 调用

使用的 API 接口：

```typescript
// 列表查询
getSchedulerJobListApi(params)

// 创建任务
createSchedulerJobApi(data)

// 更新任务
updateSchedulerJobApi(id, data)

// 删除任务
deleteSchedulerJobApi(id)

// 调度器状态
getSchedulerStatusApi()
getSchedulerJobStatisticsApi()

// 调度器控制
startSchedulerApi()
shutdownSchedulerApi()
pauseSchedulerApi()
resumeSchedulerApi()
```

## 后续改进建议

1. 性能优化
   - 虚拟滚动（大量任务时）
   - 分页加载

2. UX 改进
   - 拖拽排序
   - 批量操作
   - 更详细的错误提示

3. 功能扩展
   - 任务日志实时刷新
   - 任务执行提醒
   - 任务数据导出

