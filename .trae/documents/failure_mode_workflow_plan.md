# 故障模式 (Failure Mode) 新需求实施方案

## 1. 需求摘要 (Summary)
在现有的故障模式应用中，新增以下三大核心能力：
1. **项目关联**：将故障模式数据与 `project_manager` 模块中的 `Project`（产品）进行关联，并为产品指定归属人。
2. **角色与数据权限过滤**：引入四种业务角色（管理员、版本 SE、特性 SE、普通用户）。为了降低维护成本并实现灵活的数据隔离，采用**基于数据关系动态推导**的方案，而非独立的显式角色表。
3. **工作流管理**：实现任务的生命周期管理（创建/修订/删除任务）。支持从任务发起到特性 SE 梳理（绑定故障模式），再到版本 SE 评审关闭，并最终形成产品基线的完整闭环。

## 2. 现状分析 (Current State Analysis)
- 当前 `FailureMode` 模型作为全局字典存在，包含子系统、模块等字段，但未与 `Project`（产品）直接绑定，缺乏产品维度的基线管理。
- 缺少任务管理和工作流引擎相关模型。
- 系统核心 (`core`) 具有基于 RBAC 的 `Role` 模型，但其 `data_scope` 主要基于部门或个人层级，无法完全满足“版本 SE（产品归属人）”和“特性 SE（任务责任人）”这种基于实例级属性的细粒度数据过滤需求。

## 3. 提议更改 (Proposed Changes)

### 3.1 数据库模型新增 (Database Models)
修改文件：`backend-django/apps/project_manager/failure_mode/failure_mode_model.py`

- **`FailureModeProduct` (产品故障模式配置)**
  - **What**: 记录产品与归属人的映射。
  - **字段**: `project` (OneToOneField -> `Project`), `owner` (ForeignKey -> `User`，即版本 SE)。
  - **Why**: 满足“每个产品关联故障模式，且有独立归属人”的需求。

- **`ProductFailureMode` (产品故障模式基线)**
  - **What**: 记录某个产品下某个子系统最终确认绑定的故障模式。
  - **字段**: `product` (ForeignKey -> `FailureModeProduct`), `subsystem` (CharField), `failure_mode` (ForeignKey -> `FailureMode`)。
  - **Why**: 隔离任务过程数据与最终生效的基线数据。

- **`FailureModeTask` (故障模式梳理任务)**
  - **What**: 工作流任务实体。
  - **字段**:
    - `name` (任务名称)
    - `task_type` (任务类型：`CREATE` 创建, `REVISE` 修订, `DELETE` 删除)
    - `status` (状态：`ANALYZING` 梳理中, `REVIEWING` 评审中, `CLOSED` 已关闭)
    - `product` (关联的产品 -> `FailureModeProduct`)
    - `subsystem` (子系统名称)
    - `creator` (创建人，通常为版本 SE)
    - `assignee` (责任人 -> `User`，即特性 SE)
    - `review_minutes` (TextField，评审会议纪要)
  - **Why**: 支撑工作流流转。根据确认，任务创建后直接进入“梳理中”状态。

- **`TaskFailureMode` (任务关联的故障模式)**
  - **What**: 记录在特定任务中，特性 SE 正在梳理绑定的故障模式列表。
  - **字段**: `task` (ForeignKey -> `FailureModeTask`), `failure_mode` (ForeignKey -> `FailureMode`)。
  - **Why**: 在任务未关闭前，所绑定的故障模式仅属于该任务；评审通过后才同步到基线。

### 3.2 角色与权限逻辑实现 (Roles & Permissions)
修改文件：`backend-django/apps/project_manager/failure_mode/service/` 和 `api/` 相关文件。

- **What & How**:
  - **管理员 (Admin)**: 拥有 `fm_admin` 角色或 `is_superuser=True`，拥有所有数据的读写权限。
  - **版本 SE (Version SE)**: 通过判断 `request.user == FailureModeProduct.owner` 动态识别。可以发起其名下产品的任务，并在任务流转到“评审中”时组织评审和关闭任务。API 层针对列表查询进行 `owner_id=request.user.id` 过滤。
  - **特性 SE (Feature SE)**: 通过判断 `request.user == FailureModeTask.assignee` 动态识别。在任务列表中只能看到自己作为责任人的任务，并能对这些处于“梳理中”的任务进行故障模式绑定/解绑。
  - **普通用户 (Normal User)**: 仅具备基线数据（`FailureModeProduct`, `ProductFailureMode`）和公开字典（`FailureMode`）的只读权限。
- **Why**: 基于数据关系的推导无需额外维护用户角色关系表，减少数据不一致风险，符合最小权限原则。

### 3.3 工作流核心逻辑实现 (Workflow Logic)
修改文件：`backend-django/apps/project_manager/failure_mode/service/task_service.py` (新建)

- **What & How**:
  1. **发起任务**: 版本 SE 调用接口创建任务，指定产品、子系统、责任人（特性 SE）。系统自动将 `status` 设为 `ANALYZING`（梳理中）。
  2. **梳理与绑定**:
     - 特性 SE 在前端通过组件选择现有的 `FailureMode`，调用接口将其绑定到当前任务（写入 `TaskFailureMode`）。
     - **快速添加**: 若无所需故障模式，前端提供表单复用现有创建接口生成新的 `FailureMode`，并自动将其 ID 关联至当前任务。
  3. **提交评审**: 梳理完成后，特性 SE 调用提交流转接口，将任务状态从 `ANALYZING` 更新为 `REVIEWING`。
  4. **评审与基线化 (闭环)**: 
     - 版本 SE 组织线下评审后，调用评审关闭接口，填写 `review_minutes`，任务状态更新为 `CLOSED`。
     - **基线同步逻辑**: 任务关闭时，触发同步事件。根据 `task_type` 将 `TaskFailureMode` 中的记录合并/更新/移除到 `ProductFailureMode` 表中，完成产品基线的更新。
- **Why**: 明确的职责边界和状态机流转，保证数据的可追溯性和严谨性。

## 4. 假设与决策 (Assumptions & Decisions)
1. **假设**: 工作流流转采用简单的线性状态机（梳理中 -> 评审中 -> 已关闭），暂不需要复杂的退回重审机制（如果评审不通过，可通过重新激活任务或新建修订任务处理，当前按线性流转设计）。
2. **决策**: 角色管理放弃独立创建 `FailureModeRole` 表，而是基于 `Product.owner` 和 `Task.assignee` 隐式判定，降低架构复杂度。
3. **决策**: 任务一旦创建就自动进入 `ANALYZING`（梳理中）状态，特性 SE 登录后直接看到并开始工作，省去“接收”步骤。

## 5. 验证步骤 (Verification Steps)
1. **模型迁移**: 运行 `makemigrations` 和 `migrate`，验证新表 `FailureModeProduct`, `FailureModeTask` 等是否成功创建。
2. **权限隔离测试**: 
   - 登录版本 SE 账号，验证只能看到自己归属的产品并创建任务。
   - 登录特性 SE 账号，验证只能看到指派给自己的任务。
3. **工作流测试**: 
   - 创建一个 `CREATE` 类型的任务。
   - 特性 SE 绑定若干故障模式并提交。
   - 版本 SE 填写纪要并关闭任务。
   - 检查 `ProductFailureMode` 表，确认故障模式已成功同步至基线。
