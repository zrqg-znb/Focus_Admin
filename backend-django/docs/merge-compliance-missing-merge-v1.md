# merge_compliance 模块漏合检测能力设计文档

## 背景

仓库实现模块以 `apps.code_compliance` 为准，业务命名继续沿用 `merge_compliance`。旧 Excel 风险台账、岗位概览、用户详情和旧分支整改接口继续保留；新能力基于一期已维护的组织、代码库、分支绑定关系，自动从公司数据湖拉取 CR 明细并识别漏合风险。

本期不新增显式主干-发布配对配置，按同一代码库下绑定的 `trunk` 分支与 `release` 分支自动组合。该策略配置成本低，但可能带来误报，后续稳定后可升级为显式监测关系。

## 数据湖对接

专用 client 位于 `apps.code_compliance.missing_merge_client`，使用 `GET + 查询串`。开发环境若未配置真实地址或打开 `CODE_COMPLIANCE_CR_FORCE_MOCK`，会返回同结构 mock 数据。

配置项：

本地开发默认值写在 `backend-django/.env`，Django 侧统一在 `application/settings.py` 暴露为同名 setting；测试和部署环境可直接用同名系统环境变量覆盖。

| 配置 | 说明 |
| --- | --- |
| `CODE_COMPLIANCE_CR_API_URL` | 公司数据湖 CR 查询地址；为空时走 mock |
| `CODE_COMPLIANCE_CR_API_TOKEN` | Bearer Token，可为空 |
| `CODE_COMPLIANCE_CR_API_HEADERS_JSON` | 额外请求头 JSON 对象 |
| `CODE_COMPLIANCE_CR_FORCE_MOCK` | 是否强制 mock |
| `CODE_COMPLIANCE_CR_API_TIMEOUT` | 请求超时，默认 15 秒 |
| `CODE_COMPLIANCE_CR_API_VERIFY_SSL` | 是否校验证书 |
| `CODE_COMPLIANCE_CR_PAGE_SIZE` | 明细分页大小，默认 100 |
| `CODE_COMPLIANCE_CR_SCHEDULE_WINDOW_DAYS` | 定时任务默认扫描窗口，默认 1 天 |

请求参数由 client 统一校验和格式化：

- `page`、`per_page`
- `state=merged`
- `target_branch`
- `projects`：当前组织下扫描范围内代码库 `project_id` 的逗号分隔集合
- `merged_after`、`merged_before`：格式为 `2026-06-11T16:20:20.000+08:00`，并进行 URL 编码
- `only_count=True/False`

client 先以 `only_count=True` 获取统计数量，再以 `only_count=False` 分页拉取明细。CR 明细会归一出 `change_request_iid`、`change_key`、`title`、`description`、`web_url`、`added_lines`、`removed_lines`、`merged_at`、`target_branch`、`author.username` 和 `project_id`。

## 存储设计

新增模型位于 `apps.code_compliance.models`。

| 模型 | 说明 |
| --- | --- |
| `ComplianceMissingMergeRecord` | 漏合风险记录，保存组织/代码库快照、主干/发布分支、CR 核心字段和处理状态 |
| `ComplianceMissingMergeScanTask` | 漏合检测任务记录，保存触发方式、时间范围、扫描计数、识别/新增/补合数量和错误信息 |

漏合风险唯一键为 `repository + trunk_branch + release_branch + change_key`。风险状态为：

- `open`：未处理
- `fixed`：已补合
- `ignored`：已忽略

历史 `open` 记录如果本轮在发布分支 CR 集合中出现，会自动标记为 `fixed`。`ignored` 记录只刷新 CR 信息，不自动覆盖处理状态。

## 检测流程

1. 加载未删除的组织、代码库和代码库-分支绑定。
2. 过滤至少同时绑定一个 `trunk` 和一个 `release` 分支的代码库。
3. 按组织分组，使用该组织下扫描范围内所有 `project_id` 作为 `projects` 参数。
4. 对每个目标分支拉取已合入 CR 明细，并按 `branch/project_id/change_key` 建索引。
5. 对每个代码库的主干-发布组合执行集合差异：`trunk_change_keys - release_change_keys`。
6. 差集写入或更新 `ComplianceMissingMergeRecord`。
7. 发布分支已出现的历史 `open` 风险自动标记为 `fixed`。
8. 扫描结果写入 `ComplianceMissingMergeScanTask`。

## API

接口统一挂在 `/api/code-compliance/missing-merges`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/records` | 分页查询漏合风险，支持组织、代码库、分支、状态、创建人、时间范围筛选 |
| GET | `/records/{id}` | 查询漏合风险详情 |
| PUT | `/records/{id}/status` | 更新处理状态和备注 |
| GET | `/scan-tasks` | 查询扫描任务历史 |
| POST | `/scan-tasks/run` | 手动触发扫描 |

定时任务入口为 `apps.code_compliance.missing_merge_services.run_scheduled_missing_merge_scan`。`init_code_compliance` 会创建默认禁用的定时任务 `code_compliance_missing_merge_scan`，Cron 为每天 02:00。

## 前端

新增页面 `web/apps/web-ele/src/views/compliance/missing-merge/index.vue`，菜单名为 `漏合风险`。

页面能力：

- 顶部展示最近一次同步任务摘要。
- 支持按关键词、状态、组织、代码库、创建人、主干分支、发布分支、合入时间、识别时间筛选。
- 表格展示漏合 CR、状态、代码库、组织、分支配对、创建人、合入时间、识别时间和代码行变化。
- 详情抽屉展示 CR 描述、链接、分支配对和处理备注。
- 状态弹窗支持 `未处理/已补合/已忽略` 更新。
- 手动同步弹窗支持选择时间范围、组织和代码库。

## 验收标准

- 开发环境未配置数据湖 URL 时，手动同步可通过 mock 生成稳定漏合风险。
- URL 编码、时间格式、`only_count` 两种模式有单元测试覆盖。
- 重复扫描不会重复新增同一 `change_key` 风险。
- 发布分支已包含的历史 `open` 风险会自动标记为 `fixed`。
- 人工 `ignored` 风险不会被扫描自动改回 `open` 或 `fixed`。
- 旧 Excel 风险台账、代码库管理和分支管理能力不受影响。
