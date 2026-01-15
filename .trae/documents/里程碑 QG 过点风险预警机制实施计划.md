# 里程碑 QG 过点风险预警机制实施计划

根据您的需求，我将设计并实现一套针对自定义 QG 点的风险预警机制。

## 1. 数据库模型设计

在 `backend-django/apps/project_manager/milestone/milestone_model.py` 中新增以下模型：

### 1.1 `MilestoneQGConfig` (QG 配置表)
用于存储哪些 QG 点需要进行预警扫描。
- `milestone`: 关联到 `Milestone` (外键)
- `qg_name`: 字符型 (如 "QG1", "QG2")
- `target_di`: 目标 DI 值 (Float, 可空)
- `enabled`: 是否启用 (Boolean, 默认 True)

### 1.2 `MilestoneRiskItem` (QG 风险记录表)
每日扫描生成的风险项。
- `config`: 关联到 `MilestoneQGConfig` (外键)
- `record_date`: 记录日期 (Date)
- `risk_type`: 风险类型 (Choice: "dts", "di")
- `description`: 风险描述 (Text)
- `status`: 状态 (Choice: "pending", "confirmed", "closed")
- `manager_confirm_note`: 项目经理确认备注 (Text)
- `manager_confirm_at`: 确认时间 (Datetime)
- `manager`: 确认人 (User 外键)

### 1.3 `MilestoneRiskLog` (处理日志表)
记录风险项的状态变更和处理历史。
- `risk_item`: 关联到 `MilestoneRiskItem` (外键)
- `action`: 操作类型 (Create, Update, Confirm, Close)
- `operator`: 操作人 (User 外键)
- `note`: 操作备注 (Text)
- `created_at`: 创建时间 (Datetime)

## 2. 后端 API 设计

在 `backend-django/apps/project_manager/milestone/milestone_api.py` 中新增接口：

### 2.1 配置管理
- `POST /milestone/qg-config`: 创建/更新 QG 配置
- `GET /milestone/qg-config/{milestone_id}`: 获取某里程碑的 QG 配置

### 2.2 风险管理
- `GET /milestone/risks/pending`: 获取当前所有待处理风险 (用于工作台)
- `GET /milestone/risks/{config_id}`: 获取某 QG 配置的历史风险
- `POST /milestone/risks/{risk_id}/confirm`: 项目经理确认/关闭风险 (填写备注)

### 2.3 定时任务逻辑 (在 `milestone_service.py` 实现)
- `check_qg_risks_daily()`: 每日运行的 Celery 任务或手动触发函数
    - 遍历所有启用的 `MilestoneQGConfig`
    - 计算当前日期与 QG 日期的差值，如果在 2 周内 (<= 14 days)
    - 调用 DTS/DI 查询接口 (Mock 或实际逻辑)
    - **DTS 检查**: 是否有未关闭问题单
    - **DI 检查**: 当前 DI 是否 > `target_di`
    - **风险生成**:
        - 如果发现风险：检查昨日是否有相同未关闭风险。
        - 如果有，更新状态/描述；如果无 (或昨日已关闭)，创建新风险 `MilestoneRiskItem`。
    - **自动恢复**: 如果风险消失，自动将未确认/未关闭的风险标记为已解决 (可选，或保留由人工关闭)。*根据需求"重新预警"，倾向于只要存在就生成/保持 Open 状态。*

## 3. 前端页面变更

### 3.1 里程碑看板页面 (`project-manager/milestone`)
- **配置入口**: 在里程碑看板或列表项中增加 "QG 预警配置" 按钮。
- **配置弹窗**: 允许用户为 QG1-QG8 开启/关闭预警，并设置目标 DI。
- **风险展示**: 在看板的 QG 节点上增加 "风险" 图标/标记，点击查看详情。

### 3.2 工作台页面 (`dashboard/workspace`)
- **风险卡片**: 新增 "QG 过点风险预警" 卡片 (Risk Card)。
- **展示内容**: 列表展示当前 `pending` 状态的风险项 (项目名, QG点, 风险类型, 描述)。
- **操作**: 提供 "确认/处理" 按钮，弹出对话框输入备注并闭环。

## 4. 实施步骤

1.  **后端模型开发**: 创建 `MilestoneQGConfig`, `MilestoneRiskItem`, `MilestoneRiskLog`。
2.  **后端逻辑开发**: 实现 `check_qg_risks_daily` 核心扫描逻辑。
3.  **后端 API 开发**: 实现配置和风险管理的 CRUD 接口。
4.  **前端配置开发**: 实现里程碑 QG 配置弹窗。
5.  **前端工作台开发**: 实现风险预警卡片及处理交互。
6.  **联调与测试**: 模拟数据测试 2 周内预警触发、风险生成、确认闭环流程。

此方案满足了自定义配置、两周预警、每日 Check、重复风险再预警以及操作留痕的核心需求。