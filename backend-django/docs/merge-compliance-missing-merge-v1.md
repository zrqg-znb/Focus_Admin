# merge_compliance 模块漏合检测能力设计文档

## 背景

仓库实现模块以 `apps.code_compliance` 为准，业务命名继续沿用 `merge_compliance`。旧 Excel 风险台账、岗位概览、用户详情和旧分支整改接口继续保留；新能力基于一期已维护的组织、代码库、分支绑定关系，自动从公司数据湖拉取 CR 明细并识别漏合风险。

本期不新增显式主干-发布配对配置，按同一代码库下绑定的 `trunk` 分支与 `release` 分支自动组合。该策略配置成本低，但可能带来误报，后续稳定后可升级为显式监测关系。

## 数据湖对接

专用 client 位于 `apps.code_compliance.missing_merge_client`，使用 `GET + 查询串`。数据湖 URL 固定为 `http://apig.yinwang.com/api/v4/groups/{group_id}/change_requests`，其中 `{group_id}` 由同步服务按当前组织动态替换。开发环境打开 `CODE_COMPLIANCE_CR_FORCE_MOCK` 时会返回同结构 mock 数据。

配置项：

固定 URL、超时、分页大小、SSL 校验和定时扫描窗口统一写在 client/service 模块常量中，避免把不会变化的值散落到 `.env` 或 settings。`application/settings.py` 和本地 `.env` 只保留鉴权、额外 header 和 mock 开关；测试和部署环境可用同名系统环境变量覆盖这些环境相关项。

| 配置 | 说明 |
| --- | --- |
| `CODE_COMPLIANCE_CR_API_TOKEN` | Bearer Token，可为空 |
| `CODE_COMPLIANCE_CR_API_HEADERS_JSON` | 额外请求头 JSON 对象 |
| `CODE_COMPLIANCE_CR_FORCE_MOCK` | 是否强制 mock |
| `CODE_COMPLIANCE_DTS_RELATION_API_URL_TEMPLATE` | CR 关联 DTS 的 GET URL 模板，默认 GitLab 风格项目级路径 |
| `CODE_COMPLIANCE_DTS_STATUS_API_URL` | DTS 批量状态查询 POST URL |
| `CODE_COMPLIANCE_DTS_FORCE_MOCK` | DTS 关联与状态接口是否使用开发期 mock |

请求参数由 client 统一校验和格式化：

- `page`、`per_page`
- `state=merged`
- `target_branch`
- `projects`：当前组织下扫描范围内代码库 `project_id` 数组，GET 查询串按多值参数编码
- `merged_after`、`merged_before`：格式为 `2026-06-11T16:20:20.000+08:00`，并进行 URL 编码
- `only_count=True/False`

client 先以 `only_count=True` 获取统计数量，再以 `only_count=False` 分页拉取明细。CR 明细会归一出 `change_request_iid`、`change_key`、`title`、`description`、`web_url`、`added_lines`、`removed_lines`、`merged_at`、`target_branch`、`author.username` 和 `project_id`。

## 存储设计

新增模型位于 `apps.code_compliance.models`。

| 模型 | 说明 |
| --- | --- |
| `ComplianceMissingMergeRecord` | 漏合风险记录，保存组织/代码库快照、主干/发布分支、CR 核心字段和处理状态 |
| `ComplianceMissingMergeScanTask` | 漏合检测任务记录，保存触发方式、时间范围、扫描计数、识别/新增/补合数量和错误信息 |

`ComplianceMissingMergeRecord` 会在扫描落库时同步写入作者归属：

- `author_username` 来自数据湖 CR 明细中的 `author.username`。
- `author_user`、`author_user_name` 按 `core.User.username` 精确匹配。
- `author_pl_group`、`author_pl_group_name` 按启用的 `core.PlGroup.members` 匹配。
- 作者不存在、作者未加入启用 PL 组、PL 组被禁用时统一归为 `非底软领域`，此时 `author_pl_group=NULL`。
- 同一用户命中多个启用 PL 组时，按 PL 组现有排序 `-sort, name, id` 取第一个，确保单条 CR 只计入一个 PL 组。
- 前端创建人展示口径为：匹配 Focus 用户且存在姓名时显示 `姓名（工号）`，未匹配 Focus 用户时显示数据湖返回的原始工号；创建人筛选支持姓名和工号双字段命中。

漏合风险唯一键为 `repository + trunk_branch + release_branch + change_key`。风险状态为：

- `open`：未处理
- `fixed`：已补合
- `ignored`：已忽略

历史 `open` 记录如果本轮在发布分支 CR 集合中出现，会自动标记为 `fixed`。`ignored` 记录只刷新 CR 信息，不自动覆盖处理状态。

## 检测流程

1. 加载未删除的组织、代码库和代码库-分支绑定，并在配对前排除已归档的非活跃分支。
2. 过滤至少同时绑定一个活跃 `trunk` 和一个活跃 `release` 分支的代码库。
3. 按组织分组，使用该组织下扫描范围内所有 `project_id` 作为 `projects` 参数。
4. 对每个目标分支拉取已合入 CR 明细，并按 `branch/project_id/change_key` 建索引。
5. 对同批 CR 创建人批量加载 Focus 用户和启用 PL 组映射，避免逐条查询。
6. 对每个代码库的主干-发布组合执行集合差异：`trunk_change_keys - release_change_keys`。
7. 差集写入或更新 `ComplianceMissingMergeRecord`，同步刷新作者用户与 PL 组归属快照。
8. 对待入库 CR 按 `project_id + change_request_iid` 查询关联项，只使用首项且仅接受 `DTS` 前缀单号；优先从 DTS 统计快照读取状态，未命中才批量请求 DTS 状态接口。
9. 发布分支已出现的历史 `open` 风险自动标记为 `fixed`。
10. 扫描结果写入 `ComplianceMissingMergeScanTask`。

漏合记录保存 `dts_no`、`dts_title`、`dts_status_name` 快照。CR 没有关联、关联首项不是 DTS 时会清空旧快照；关联单号存在但快照和上游状态接口均未返回时保留单号，前端显示“未查询到”。历史记录可通过 `POST /dts-backfill-tasks/run` 异步回填，任务运行中重复提交会复用已有任务。

手动同步采用进程内 daemon thread 异步执行：接口只创建 `pending` 任务并立即返回，后台线程负责把任务流转为 `running/success/failed`。如果服务进程重启，正在执行的线程不做跨进程恢复；这是本期不引入 Celery/RQ 的约束。手动提交前会检查是否已有 `pending/running` 漏合同步任务，存在时不创建新任务，直接返回当前任务用于页面提示。

跨天自动闭环按同一配对维度判断：`repository + trunk_branch + release_branch + change_key`。当前扫描窗口内发布分支出现某个历史 `open` 风险的 `change_key` 时，只闭环同一代码库、同一主干-发布配对下的旧记录；其他配对即使 `change_key` 相同也不受影响。当前扫描窗口内主干新增、发布缺失的新 `change_key` 会继续新增为新的 `open` 风险。

## API

接口统一挂在 `/api/code-compliance/missing-merges`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/records` | 分页查询漏合风险，支持组织、代码库、分支、状态、创建人、时间范围筛选 |
| GET | `/records/{id}` | 查询漏合风险详情 |
| PUT | `/records/{id}/status` | 更新处理状态和备注 |
| GET | `/pl-dashboard` | 查询 PL 组漏合看板，按主干合入周聚合趋势和状态分布 |
| GET | `/scan-tasks` | 分页查询扫描任务历史，支持状态、触发方式和时间范围筛选 |
| GET | `/scan-tasks/{id}` | 查询单条扫描任务详情 |
| POST | `/scan-tasks/run` | 手动提交扫描任务，立即返回 `{ accepted, message, task }` |
| POST | `/dts-backfill-tasks/run` | 异步提交历史漏合风险 DTS 回填任务 |
| GET | `/dts-backfill-tasks/{id}` | 查询 DTS 回填任务进度和诊断 |

`/records` 和 `/pl-dashboard` 均支持 `pl_group_ids` 筛选，多个 ID 使用逗号分隔。特殊值 `unknown` 表示 `非底软领域`，与真实 PL 组多选时按并集命中，随后再与状态、时间、组织/代码库等筛选条件取交集。

定时任务入口为 `apps.code_compliance.missing_merge_services.run_scheduled_missing_merge_scan`。`init_code_compliance` 会创建默认禁用的定时任务 `code_compliance_missing_merge_scan`，Cron 为每天 02:00。

## 前端

新增页面：

- `web/apps/web-ele/src/views/compliance/missing-merge/index.vue`，菜单名为 `漏合风险`。
- `web/apps/web-ele/src/views/compliance/missing-merge-task/index.vue`，菜单名为 `同步任务历史`。

漏合风险页面能力：

- 顶部展示最近一次同步任务摘要。
- 顶部通过 `风险列表 / PL组看板` 分段切换，两个视图共用同一组筛选条件。
- 支持按关键词、状态、组织/代码库级联、创建人、PL 组、主干分支、发布分支、合入时间、识别时间筛选；PL 组选项直接复用核心 PL 组列表接口，并追加 `非底软领域`。
- 表格展示漏合 CR、状态、PL 组、代码库、组织、分支配对、创建人、关联 DTS、DTS 状态、合入时间、识别时间和代码行变化。
- 详情抽屉展示 CR 描述、链接、分支配对、Focus 用户、PL 组归属、关联 DTS 和处理备注。
- 状态弹窗支持 `未处理/已补合/已忽略` 更新。
- 手动同步弹窗支持选择时间范围、组织和代码库；提交后只等待任务创建结果，不等待完整扫描。
- PL 组看板按 `merged_at` 所属 ISO 自然周展示各 PL 组漏合趋势；未传合入时间范围时默认展示最近 12 个自然周。`merged_at` 为空的记录进入汇总和 PL 组明细，但不进入周趋势，并通过 `missing_merged_at_count` 标识。

同步任务历史页面能力：

- 展示手动同步和定时扫描任务。
- 支持按状态、触发方式、合入时间范围、任务开始时间范围筛选。
- 详情抽屉展示筛选范围、扫描计数、风险计数、耗时和失败错误信息。
- 任务详情返回 `scan_diagnostics`，用于排查零结果任务：包含组织 `group_id`、项目数量、分支 only_count/detail_count、每个配对的 trunk/release/missing/fixed 计数。

## 验收标准

- 开发环境未配置数据湖 URL 时，手动同步可通过 mock 生成稳定漏合风险。
- URL 编码、时间格式、`only_count` 两种模式有单元测试覆盖。
- 重复扫描不会重复新增同一 `change_key` 风险。
- 扫描新增和重复更新都会刷新作者 Focus 用户与 PL 组归属；未知归属统一显示为 `非底软领域`。
- 风险列表支持真实 PL 组和 `unknown` 混合筛选。
- PL 组看板按 `merged_at` 周统计趋势，状态计数、未知归属和空合入时间均有覆盖。
- 手动同步接口在已有 `pending/running` 任务时返回 `accepted=false`，不创建重复任务。
- 发布分支已包含的历史 `open` 风险会自动标记为 `fixed`。
- 自动闭环只影响同一代码库、同一主干-发布配对、同一 `change_key` 的历史 `open` 记录；同 key 不同配对不会互相闭环。
- 人工 `ignored` 风险不会被扫描自动改回 `open` 或 `fixed`。
- 旧 Excel 风险台账、代码库管理和分支管理能力不受影响。
