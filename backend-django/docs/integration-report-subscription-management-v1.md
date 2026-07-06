# 集成报告邮件订阅管理页

## 背景

每日集成报告邮件停发较久后，项目配置和订阅关系已经与实际使用人群产生偏差。现有个人订阅页只能让当前用户管理自己的订阅，无法支撑管理员按项目集中治理“哪些项目被哪些人订阅”。

## 目标

- 在集成报告模块内新增管理员视角的邮件订阅管理页。
- 以项目/配置为主线，快速查看每个配置的订阅人数、无邮箱订阅人数和启用状态。
- 支持管理员在单个项目配置下批量追加、移除和全量保存订阅人。
- 支持管理员勾选多个项目配置后批量追加订阅人。
- 保持邮件发送逻辑不变，继续以 `IntegrationEmailSubscription.enabled=True` 作为发送依据。

## 非目标

- 不恢复或调整邮件发送任务调度。
- 不启用遗留 `apps/mail_subscription` 模块。
- 首次上线不自动补项目负责人或全量活跃用户订阅。
- OAuth 新用户创建后不再默认订阅全部集成报告项目。

## 接口与页面

- 页面路径：`/integration-report/subscription-management`
- 页面形态：主表查询项目配置，右侧抽屉维护订阅人。
- 接口：
  - `GET /api/integration-report/subscription-management/projects`
  - `GET /api/integration-report/subscription-management/projects/{config_id}/subscribers`
  - `PUT /api/integration-report/subscription-management/projects/{config_id}/subscribers`
  - `POST /api/integration-report/subscription-management/projects/{config_id}/subscribers/batch-add`
  - `POST /api/integration-report/subscription-management/projects/{config_id}/subscribers/batch-remove`
  - `POST /api/integration-report/subscription-management/projects/subscribers/batch-add`

## 验收标准

- 管理员可以按配置名/项目名、启用状态、是否有订阅人、是否存在无邮箱订阅人筛选项目配置。
- 管理员可以打开项目配置抽屉，查看订阅人、邮箱、启用状态和更新时间。
- 批量追加用户不会产生重复订阅；已软删或已禁用订阅会重新启用。
- 勾选多个项目配置批量追加用户时，只追加管理员明确选择的项目配置。
- 全量保存只影响当前项目配置，不会自动改动其他项目配置。
- 批量移除将订阅置为禁用并软删除，邮件发送不再包含这些关系。
