# 集成报告页面

集成报告 (`integration-report`) 模块页面用于管理多项目、多工具链产生的持续集成（CI）报告的汇总、订阅与推送记录。

## 页面结构

### 1. 报告配置 (Config)
位于 `views/integration-report/config/`：
- 配置项目构建产物、测试覆盖率、安全扫描结果等数据源的接入信息。
- 设置生成周期和触发规则。

### 2. 邮件日志 (Email Logs)
位于 `views/integration-report/email-logs/`：
- 展示生成的报告推送至特定订阅人的记录。
- 列出发送状态（成功、失败）和时间，支持按状态筛选和重新发送。

### 3. 报告历史 (History)
位于 `views/integration-report/history/`：
- 汇总展示历史生成的所有集成报告快照。
- 允许用户下载或在线预览具体的测试和扫描详情。

### 4. 订阅管理 (Subscription)
位于 `views/integration-report/subscription/`：
- 管理集成报告的订阅人（通过邮箱或企业通讯工具通知）。
- 允许按不同项目或标签订阅特定周期的报告。

## 核心交互

- **在线预览**：历史报告页面可加载后端渲染的报告 HTML 或 Markdown，并在弹窗或新标签页中展示。
- **动态配置表单**：订阅和配置页面利用封装好的表单生成器，快速收集用户的订阅偏好和触发规则。
