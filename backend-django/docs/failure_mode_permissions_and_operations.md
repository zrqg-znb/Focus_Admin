# 故障模式 App 权限与操作文档（当前实现 + 差异）

本文档基于当前仓库实现整理，时间口径为 `2026-04-03`。

> 前端主路由：`/failure-mode/*`  
> 后端 API 前缀：`/api/failure-mode/*`

---

## Summary

- 当前故障模式 App 采用两层权限模型：
  - 系统侧权限：由菜单、页面权限、接口权限控制“能不能进页面、能不能调 API”。
  - 模块侧权限：由 `FailureModeRoleAssignment` 和 `FailureModeAccessPolicy` 控制“能看到哪些产品/子系统数据、能执行哪些工作流动作”。
- 当前代码里，主数据页和子系统配置页更偏“系统权限驱动”；工作流、产品基线、角色配置、产品统计更偏“系统权限 + 模块角色数据范围”双重驱动。
- 这份文档按“当前实现”为准，同时标出需要注意的差异和治理风险。

---

## 1. 权限模型总览

### 1.1 系统侧角色与权限

- 系统超级管理员：`is_superuser`，天然拥有全部能力。
- 系统核心角色：`core_roles.code = fm_admin`，在模块内会被识别为管理员。
- 系统菜单/页面权限：由初始化菜单和 permission code 控制页面可见性。
- 系统接口权限：由 permission code 绑定 API 路径控制接口调用资格。

### 1.2 模块内角色

- `fm_admin`
  - 模块管理员，作用域为全局。
  - 当前代码支持，但前端“角色配置页”没有分配入口。
  - 实际建议通过系统超级管理员或 core role `fm_admin` 赋予。
- `version_se`
  - 产品级角色，作用域是“产品”，不带子系统。
  - 当前通过 `FailureModeProduct.owner` 同步生成，是产品主版本 SE。
- `feature_se`
  - 子系统级角色，作用域是“产品 + 子系统”。
  - 可被指派为任务责任人。
- `member`
  - 子系统级只读角色，作用域是“产品 + 子系统”。
  - 不参与工作流动作。

### 1.3 两层权限的职责边界

- 系统侧权限决定：
  - 页面是否能进入。
  - API 是否具备基础调用资格。
- 模块侧权限决定：
  - 看到哪些产品、子系统、任务、基线。
  - 是否能发起任务、接收任务、提交流转、驳回、关闭、改派。
- 当前实现里，很多按钮不是前端直接按 permission code 隐藏，而是：
  - 工作流页面靠后端返回的 `available_actions` 控制。
  - 角色配置页靠后端返回的 `can_manage_roles` 控制。
  - 主数据页和子系统配置页当前几乎没有业务角色级按钮收口，更多依赖系统 API 权限。

---

## 2. 系统权限清单

### 2.1 页面权限 code

- `failure-mode:view`
  - 故障模式数据页。
  - 同时被“配置管理目录”“子系统配置页”复用。
- `failure-mode:statistics:view`
  - 故障管理统计页。
- `failure-mode:product-statistics:view`
  - 产品故障统计页。
- `failure-mode:workflow-tasks:view`
  - 任务管理页。
- `failure-mode:workflow-tasks:detail:view`
  - 任务详情页。
- `failure-mode:workflow-products:view`
  - 产品基线页。
- `failure-mode:roles:view`
  - 角色配置页。
- `failure-mode:roles:detail:view`
  - 角色配置详情页。

### 2.2 主数据与配置 API 权限

- 故障模式主数据
  - `failure-mode:api:dict-options`
  - `failure-mode:api:list`
  - `failure-mode:api:create`
  - `failure-mode:api:detail`
  - `failure-mode:api:insight`
  - `failure-mode:api:update`
  - `failure-mode:api:delete`
- 产线拦截策略
  - `failure-mode:api:interception:list`
  - `failure-mode:api:interception:save`
  - `failure-mode:api:interception:insight`
- 故障处理措施
  - `failure-mode:api:measure:list`
  - `failure-mode:api:measure:save`
  - `failure-mode:api:measure:insight`
- 维测手段
  - `failure-mode:api:observation:list`
  - `failure-mode:api:observation:save`
  - `failure-mode:api:observation:insight`
- 华佗诊断方案
  - `failure-mode:api:huatuo:list`
  - `failure-mode:api:huatuo:save`
  - `failure-mode:api:huatuo:insight`
- 测试用例
  - `failure-mode:api:test-case:list`
  - `failure-mode:api:test-case:save`
  - `failure-mode:api:test-case:insight`
- 子系统配置
  - `failure-mode:api:subsystem-config:list`
  - `failure-mode:api:subsystem-config:create`
  - `failure-mode:api:subsystem-config:detail`
  - `failure-mode:api:subsystem-config:update`
  - `failure-mode:api:subsystem-config:delete`
  - `failure-mode:api:subsystem-config:options`

### 2.3 统计与工作流 API 权限

- 故障管理统计
  - `failure-mode:statistics:api:summary`
  - `failure-mode:statistics:api:subsystems`
- 产品故障统计
  - `failure-mode:api:product-statistics:overview`
  - `failure-mode:api:product-statistics:summary`
  - `failure-mode:api:product-statistics:subsystems`
- 工作流任务
  - `failure-mode:workflow-tasks:api`
  - 当前是通配权限，覆盖 `/api/failure-mode/workflow/tasks*`
- 工作流产品
  - `failure-mode:workflow-products:api`
  - 当前是通配权限，覆盖 `/api/failure-mode/workflow/products*`

### 2.4 当前系统权限差异

- 新增的统计选项接口当前代码已存在，但 permission seed 未补齐：
  - `GET /api/failure-mode/statistics/subsystems/options`
  - `POST /api/failure-mode/statistics/products/subsystems/options`
- 工作流任务接口当前只有一个粗粒度通配权限，不区分“创建/接收/提交/驳回/关闭”等动作。
- 工作流产品接口当前也只有一个粗粒度通配权限，不区分“查看基线/查看角色/编辑角色/更新 owner”等动作。

---

## 3. 模块内角色与数据范围

### 3.1 管理员 `fm_admin`

- 识别方式
  - 系统超级管理员。
  - core role `fm_admin`。
  - 模块角色 `FailureModeRoleAssignment.role = fm_admin`。
- 数据范围
  - 全部产品、全部子系统、全部任务、全部基线、全部角色配置。
- 工作流动作
  - 可发起任务。
  - 可改派。
  - 可驳回。
  - 可关闭。
  - 可查看全部日志和详情。
- 当前差异
  - 前端角色配置页没有给 `fm_admin` 提供分配入口。

### 3.2 产品主版本 SE `version_se`

- 识别方式
  - `FailureModeProduct.owner`。
  - 同步生成 `role = version_se` 的授权记录。
- 数据范围
  - 负责产品下全部子系统数据。
  - 该产品下全部任务、基线、角色配置可见。
- 工作流动作
  - 可发起该产品任务。
  - 可改派该产品任务责任人。
  - 评审阶段可驳回。
  - 评审阶段可关闭。
- 角色管理
  - 可编辑该产品角色配置。
  - 可设置主版本 SE。
  - 可维护该产品子系统下的特性 SE、普通成员。

### 3.3 特性 SE `feature_se`

- 识别方式
  - `role = feature_se`，作用域为“产品 + 子系统”。
- 数据范围
  - 可见自己负责“产品 + 子系统”的产品角色信息、基线、任务。
  - 若任务明确指派给自己，任务始终可见。
- 工作流动作
  - `CREATED` 可接收任务。
  - `PROCESSING` 可维护工作集、快速新增、编辑、提交评审。
  - `REVIEWING` 可撤回。
- 不具备
  - 不可发起任务。
  - 不可驳回。
  - 不可关闭。
  - 不可编辑角色配置。

### 3.4 普通成员 `member`

- 识别方式
  - `role = member`，作用域为“产品 + 子系统”。
- 数据范围
  - 只读可见自己被授权范围内的数据。
- 工作流动作
  - 不参与接收、提交、撤回、驳回、关闭、改派。
- 页面权限前提
  - 即便业务角色有范围，如果系统页面权限没给到，仍无法进入页面。

---

## 4. 页面 / API / 按钮权限矩阵

### 4.1 故障模式数据页 `/failure-mode/index`

- 页面权限
  - `failure-mode:view`
- 主要 API
  - `GET /api/failure-mode/dict-options`
  - `POST /api/failure-mode/failure-modes/search`
  - `POST /api/failure-mode/failure-modes`
  - `GET /api/failure-mode/failure-modes/{id}`
  - `PUT /api/failure-mode/failure-modes/{id}`
  - `DELETE /api/failure-mode/failure-modes/{id}`
  - 以及各主数据资源的 `search / create / detail / update / delete / insight`
- 按钮与入口
  - “新增故障模式”
  - 行内“编辑”“删除”
  - 标题列点击“关系洞察”
  - 其他主数据 Tab 也都有“新增 / 编辑 / 删除”
- 当前实现口径
  - 前端按钮默认显示，不按模块角色隐藏。
  - 后端主数据接口没有模块角色 403 校验，主要依赖系统 API 权限。
  - 故障模式创建/编辑时，“关联产品”只选择产品；子系统统一取故障模式表单里的 `subsystem` 字段。
  - “发起任务”页里的任务工作范围仍然是“关联产品 + 子系统”，不受该口径影响。
- 建议归属
  - 这页应视为系统主数据维护页。
  - 推荐只给系统管理员、模块管理员、少量主数据维护人分配系统 CRUD 权限。
  - 不建议把这页作为 feature SE 日常入口。

### 4.2 子系统配置页 `/failure-mode/config/subsystems`

- 页面权限
  - 当前复用 `failure-mode:view`
- 主要 API
  - `/api/failure-mode/subsystem-configs/search`
  - `/api/failure-mode/subsystem-configs`
  - `/api/failure-mode/subsystem-configs/{id}`
  - `/api/failure-mode/subsystem-configs/options`
- 按钮
  - “新增子系统配置”
  - 行内“编辑”“删除”
- 当前实现口径
  - 前端按钮默认显示。
  - 后端无模块角色级拦截，主要依赖系统 API 权限。
- 建议归属
  - 系统配置类页面。
  - 推荐由系统管理员或模块管理员维护。

### 4.3 故障管理统计页 `/failure-mode/statistics`

- 页面权限
  - `failure-mode:statistics:view`
- 主要 API
  - `POST /api/failure-mode/statistics/summary`
  - `POST /api/failure-mode/statistics/subsystems/search`
  - `GET /api/failure-mode/statistics/subsystems/options`
- 按钮
  - 仅查询、筛选、刷新，无状态流转动作。
- 当前实现口径
  - 当前是系统权限驱动。
  - 没有模块角色数据范围收口，统计口径是全局故障库。
- 建议归属
  - 管理层、模块管理员、主数据维护人。

### 4.4 产品故障统计页 `/failure-mode/product-statistics`

- 页面权限
  - `failure-mode:product-statistics:view`
- 主要 API
  - `POST /api/failure-mode/statistics/products/overview`
  - `POST /api/failure-mode/statistics/products/summary`
  - `POST /api/failure-mode/statistics/products/subsystems/search`
  - `POST /api/failure-mode/statistics/products/subsystems/options`
- 数据范围
  - 只统计 `Project.type = 平台项目`
  - 只返回当前用户在模块角色范围内可见的产品
- 按钮
  - 全选平台项目
  - 多选产品
  - 多选子系统
  - 刷新分析
- 当前实现口径
  - 只读页。
  - 系统页面权限 + 模块角色可见范围共同控制。

### 4.5 产品基线页 `/failure-mode/products/baselines`

- 页面权限
  - `failure-mode:workflow-products:view`
- 主要 API
  - `GET /api/failure-mode/workflow/products`
  - `GET /api/failure-mode/workflow/products/{product_id}/visible-subsystems`
  - `GET /api/failure-mode/workflow/products/{product_id}/failure-modes`
- 按钮
  - “查询”
  - “前往角色配置”
- 数据范围
  - 管理员可看全部产品基线。
  - 版本 SE 可看自己产品。
  - 特性 SE / member 只看自己“产品 + 子系统”范围。
- 按钮权限
  - “前往角色配置”当前只按是否选中产品显示，不按编辑权限隐藏。
  - 进入角色详情后是否可编辑，取决于 `can_manage_roles`。

### 4.6 角色配置页 `/failure-mode/config/roles`

- 页面权限
  - `failure-mode:roles:view`
- 主要 API
  - `GET /api/failure-mode/workflow/products?project_type=平台项目`
- 数据范围
  - 只显示平台项目。
  - 只显示当前用户可见的产品。
- 按钮
  - “进入配置详情”
- 当前实现口径
  - 任何有可见范围的协作者都可查看。
  - 这里只是列表与预览，不承担编辑。

### 4.7 角色配置详情页 `/failure-mode/config/roles/detail/:id`

- 页面权限
  - `failure-mode:roles:detail:view`
- 主要 API
  - `GET /api/failure-mode/workflow/products?project_type=平台项目`
  - `GET /api/failure-mode/workflow/products/{id}/roles`
  - `GET /api/failure-mode/workflow/products/{id}/visible-subsystems`
  - `PUT /api/failure-mode/workflow/products/{id}/owner`
  - `PUT /api/failure-mode/workflow/products/{id}/roles`
- 页面状态
  - 只读查看：所有可见范围用户。
  - 可编辑：仅 `fm_admin` 或该产品 `version_se`。
- 按钮分配
  - 只读用户
    - 无“进入编辑模式”
    - 无“保存配置”
    - 只能看主版本 SE、特性 SE、普通成员矩阵
  - 管理用户
    - “进入编辑模式”
    - “取消编辑”
    - “保存配置”
    - 编辑主版本 SE
    - 新增/删除子系统矩阵行
- 角色分配规则
  - 主版本 SE：通过修改 `owner` 完成
  - 特性 SE / 普通成员：通过矩阵批量保存完成
  - `fm_admin`：当前页面不支持维护

### 4.8 任务管理页 `/failure-mode/tasks`

- 页面权限
  - `failure-mode:workflow-tasks:view`
- 主要 API
  - `GET /api/failure-mode/workflow/tasks`
  - `POST /api/failure-mode/workflow/tasks`
- 列表行为
  - Tab：我的待办 / 我发起的 / 全部任务
  - 进入详情按钮始终显示
- 按钮分配
  - “发起任务”当前前端默认显示
  - 真实权限在后端校验：只有 `fm_admin` 或该产品 `version_se` 可创建
- 当前差异
  - UI 没有在点击前做角色级隐藏
  - 实际是否能创建，以提交时后端 403 为准

### 4.9 任务详情页 `/failure-mode/tasks/detail/:id`

- 页面权限
  - `failure-mode:workflow-tasks:detail:view`
- 主要 API
  - `GET /api/failure-mode/workflow/tasks/{id}`
  - `GET /api/failure-mode/workflow/tasks/{id}/failure-modes`
  - `GET /api/failure-mode/workflow/tasks/{id}/logs`
  - `POST /accept`
  - `POST /submit`
  - `POST /recall`
  - `POST /reject`
  - `POST /close`
  - `POST /reassign`
  - `POST /failure-modes/bind`
  - `POST /failure-modes/quick-create`
  - `PUT /failure-modes/{failure_mode_id}`
  - `POST /failure-modes/{failure_mode_id}/draft`
  - `DELETE /failure-modes/{failure_mode_id}/draft`
- 顶部按钮分配
  - “接收任务”
    - 责任特性 SE
    - 且任务为 `CREATED`
  - “改派”
    - `fm_admin` 或该产品 `version_se`
    - 且任务为 `CREATED / PROCESSING`
  - “提交评审”
    - 责任特性 SE
    - 且任务为 `PROCESSING`
  - “撤回评审”
    - 责任特性 SE
    - 且任务为 `REVIEWING`
  - “驳回任务”
    - `fm_admin` 或该产品 `version_se`
    - 且任务为 `REVIEWING`
  - “评审关闭”
    - `fm_admin` 或该产品 `version_se`
    - 且任务为 `REVIEWING`
- 梳理工作台 Tab 按钮分配
  - CREATE 任务
    - “管理绑定”：责任特性 SE，`PROCESSING`
    - “快速新增故障模式”：责任特性 SE，`PROCESSING`
    - 行内“编辑”：只对“本任务快速新增”的故障模式开放
  - REVISE 任务
    - “绑定已有”：责任特性 SE，`PROCESSING`
    - “快速新增故障模式”：责任特性 SE，`PROCESSING`
    - 行内“编辑”：全部工作集条目可编辑，走草稿模式
    - 行内“撤销修订”：仅已有草稿的条目可见
  - DELETE 任务
    - “选择待删除条目”：责任特性 SE，`PROCESSING`
    - 不开放快速新增
    - 不开放行内编辑
- 流程记录 Tab
  - 只读查看，任何可见任务的人都可看
- 评审归档 Tab
  - 纪要和附件所有可见人可看
  - 实际可编辑关闭动作仍只属于 `fm_admin / version_se`

---

## 5. 任务流转与操作手册

### 5.1 谁来分配系统权限

- 系统管理员负责：
  - 给用户或 core role 分配菜单权限和 API 权限。
  - 赋予系统超级管理员能力。
  - 赋予 core role `fm_admin`。
- 如果一个人没有系统页面权限，即使有模块角色，也进不了对应页面。

### 5.2 谁来分配模块角色

- `fm_admin`
  - 建议由系统管理员通过 core role `fm_admin` 赋予。
  - 当前页面不支持配置。
- `version_se`
  - 由 `fm_admin` 或当前产品 `version_se` 在角色配置详情页设置产品 owner。
  - 对于新产品，通常应由 `fm_admin` 先完成首任 owner 设置。
- `feature_se`
  - 由 `fm_admin` 或产品 `version_se` 在角色配置详情页中，为指定“产品 + 子系统”添加。
- `member`
  - 由 `fm_admin` 或产品 `version_se` 在角色配置详情页中，为指定“产品 + 子系统”添加。

### 5.3 如何分配角色

- 步骤 1
  - 系统管理员先确认用户已有故障模式模块的菜单权限。
- 步骤 2
  - 进入“配置管理 > 角色配置”。
- 步骤 3
  - 选择产品并进入详情。
- 步骤 4
  - 如需指定主版本 SE，编辑产品 owner。
- 步骤 5
  - 在矩阵中为每个子系统配置 `feature_se` 和 `member`。
- 步骤 6
  - 保存后，相关人会自动获得该产品/子系统范围内的查看或处理资格。
- 关键约束
  - 任务责任人必须来自该产品该子系统下的 `feature_se`。
  - 当前页面不支持直接配置 `fm_admin`。

### 5.4 如何发起任务

- 发起人
  - `fm_admin`
  - 产品 `version_se`
- 页面入口
  - “任务管理 > 发起任务”
- 表单内容
  - 任务名称
  - 任务类型：`CREATE / REVISE / DELETE`
  - 关联产品
  - 子系统
  - 责任人
- 创建规则
  - `REVISE / DELETE` 必须存在当前产品 + 子系统的已生效基线。
  - 责任人必须是该产品该子系统的 `feature_se`。
- 创建完成后
  - 任务状态 = `CREATED`
  - 当前待办人 = 责任特性 SE

### 5.5 任务如何流转

- `CREATED`
  - 责任特性 SE 可“接收任务”
- `PROCESSING`
  - 特性 SE 在工作台梳理、修订、删除候选、快速新增
  - 完成后“提交评审”
- `REVIEWING`
  - 当前待办切到创建人
  - 特性 SE 可“撤回评审”
  - 版本 SE / 管理员可“驳回任务”或“评审关闭”
- `CLOSED`
  - 关闭后同步产品基线
  - 当前待办清空

### 5.6 三类任务怎么做

- CREATE
  - 从空工作集开始
  - 可绑定已有故障模式
  - 可快速新增故障模式
  - 仅“本任务新增”的故障模式可在任务内继续编辑
- REVISE
  - 自动带入当前基线作为工作集
  - 可新增已有全局故障模式
  - 可快速新增新故障模式
  - 可编辑已有条目，但修改先保存为任务草稿，关闭时再写回全局
  - 可通过移出工作集实现基线差量删除
- DELETE
  - 只能从当前基线里选择待删除条目
  - 不支持快速新增
  - 不支持编辑故障模式主数据

### 5.7 快速新增故障模式如何处理

- 操作人
  - 任务责任特性 SE
  - 仅限 `PROCESSING`
- 行为
  - 立即创建到全局故障模式库
  - 自动绑定当前任务
  - `source_type = task_quick_create`
  - 状态跟任务流转
- 状态映射
  - `CREATED -> 待梳理`
  - `PROCESSING -> 梳理中`
  - `REVIEWING -> 待评审`
  - `CLOSED -> 已基线`

### 5.8 关闭任务后怎么生效

- CREATE
  - 把任务工作集中的故障模式写入产品基线
- REVISE
  - 先应用任务草稿到全局故障模式
  - 再按差量同步产品基线
- DELETE
  - 从产品基线中移除选中条目
  - 不删除全局故障模式主数据

---

## 6. 当前实现差异与治理风险

### 6.1 按钮和系统 permission code 没有完全对齐

- 主数据页新增/编辑/删除按钮当前默认可见。
- 子系统配置页新增/编辑/删除按钮当前默认可见。
- 任务管理页“发起任务”按钮当前默认可见。
- 这些地方更多依赖后端 API 权限或业务 403，而不是前端先隐藏。

### 6.2 主数据页不是模块角色隔离页

- 故障模式数据页和各主数据 Tab 当前没有模块角色数据范围过滤。
- 如果系统侧给了对应页面和 API 权限，用户可能看到全局主数据。
- 因此这类权限应慎发，不应给普通协作者。

### 6.3 `fm_admin` 缺少配置入口

- 模型支持 `fm_admin`。
- 访问策略也支持 `fm_admin`。
- 但角色配置详情页没有分配 `fm_admin` 的 UI。
- 当前建议统一走系统 core role `fm_admin`。

### 6.4 工作流 API 权限过粗

- `/workflow/tasks*` 只用一个 permission code。
- `/workflow/products*` 只用一个 permission code。
- 当前真正的动作分流主要依赖 service 层业务校验。
- 如果未来要做精细审计，建议把 create/accept/submit/reject/close/reassign/owner/roles-save 分开。

### 6.5 统计选项接口缺少 permission seed

- 当前代码已经用到了子系统 options 接口。
- 初始化权限中还未登记这两个接口。
- 需要在权限初始化中补齐，否则会出现新接口无标准权限映射的问题。

---

## 7. 建议的系统角色分配策略

### 7.1 系统管理员

- 负责系统菜单、页面、接口权限分配。
- 负责给极少数人配置 core role `fm_admin`。
- 负责新产品首任 owner 建立。

### 7.2 模块管理员 `fm_admin`

- 负责跨产品治理。
- 负责处理没有主版本 SE 的产品。
- 负责兜底改派、驳回、关闭、异常数据处理。

### 7.3 产品主版本 SE

- 负责本产品角色配置。
- 负责发起任务、评审组织、驳回与关闭。
- 负责产品基线结果确认。

### 7.4 特性 SE

- 负责实际梳理、修订、删除候选确认。
- 负责在任务内快速新增故障模式并完善内容。
- 负责提交评审和必要时撤回。

### 7.5 普通成员

- 负责只读协同、查看基线、查看任务过程与归档。
- 不参与正式流转动作。

---

## 8. 验收与核对场景

- 场景 1
  - 系统管理员只给某用户“角色配置页面权限”，但不给模块角色。
  - 预期：能进页但看不到任何产品，或详情不可访问。
- 场景 2
  - 给某用户 core role `fm_admin`。
  - 预期：可见全部产品、全部任务、可编辑角色、可发起/驳回/关闭任务。
- 场景 3
  - 给某产品设置 owner。
  - 预期：该人立即具备该产品 version SE 能力。
- 场景 4
  - 给某子系统配置 feature SE。
  - 预期：该人可被选为该子系统任务责任人。
- 场景 5
  - feature SE 进入任务详情。
  - 预期：只看到自己该做的动作，不能看到关闭按钮。
- 场景 6
  - version SE 进入评审中任务。
  - 预期：可看到驳回和评审关闭。
- 场景 7
  - member 进入角色详情。
  - 预期：可只读查看，不可进入编辑模式。
- 场景 8
  - 用户只有主数据页权限，没有 workflow 产品/任务权限。
  - 预期：能维护主数据，但不能进入任务管理或产品基线。
- 场景 9
  - 新统计 options 接口走权限系统。
  - 预期：应有独立 permission seed，否则需要补初始化。

---

## Assumptions

- 本文基于当前仓库实现整理，时间口径为 `2026-04-03`。
- “系统角色”指系统超级管理员、core role、菜单/接口 permission 体系。
- “模块角色”指 `FailureModeRoleAssignment` 中的 `fm_admin / version_se / feature_se / member`。
- 本文的风险项不是未来建议，而是当前需要显式告知的实现差异。
