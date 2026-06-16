# 代码量看板 v1 设计文档

## 背景与目标

代码合规模块已经具备组织、代码库、分支绑定、漏合检测和数据湖 CR 采集能力。`代码量看板` 基于这些基础数据，面向生产环境回答两个问题：

- 当前某个代码库、某条分支的存量代码量是多少。
- 在选定时间范围内，代码合入量趋势和仓库/人员/PL 组分布如何变化。

本页面不是 CR 台账。CR 详情继续在公司代码库系统中查看，平台只保留 CR 事实表用于增量计算、聚合统计和排障。

## 一期边界

- 不做综合贡献分，不输出绩效结论。
- 不展示 CR 明细列表，不提供页面上的 CR 明细导出。
- 不声称数据湖 CR 可天然还原真实总代码量；存量代码量以人工基线和后续 CR 净增滚动计算。
- 不纳入评审人、合入人等参与人，只按 CR 创建人统计合入贡献。

## 数据来源与统计口径

数据来源包括两类：

- 代码量基线：人工维护或 Excel 批量导入，按 `代码库 x 分支` 记录某个时间点的真实代码量。
- CR 增量：复用数据湖 CR API 的 `added_lines`、`removed_lines`，按活跃绑定分支采集。

核心公式：

| 指标 | 口径 |
| --- | --- |
| 当前存量代码量 | `最新生效基线代码量 + 基线时间之后 sum(net_lines)` |
| 本期新增 | 时间范围内 `sum(added_lines)` |
| 本期删除 | 时间范围内 `sum(removed_lines)` |
| 本期净增 | 时间范围内 `sum(added_lines - removed_lines)` |
| 本期总变更 | 时间范围内 `sum(added_lines + removed_lines)` |
| 缺失基线 | 当前筛选范围内活跃绑定仓库分支数 - 已维护当前基线的仓库分支数 |

时间筛选只影响本期合入趋势和本期变更指标，不影响当前存量代码量。当前存量始终表达“截至当前已采集数据的估算存量”。

## 本地存储模型

- `ComplianceContributionRecord`：CR 贡献事实表，唯一键为 `repository + branch_name + change_key`，保留内部排障和聚合计算能力。
- `ComplianceContributionDailyAggregate`：日聚合表，按日期、代码库、分支、创建人聚合。
- `ComplianceContributionCodeBaseline`：代码量基线表，按代码库和分支保留历次校准记录；同一仓库分支只有一条 `is_current=True` 生效基线。
- `ComplianceContributionCollectTask`：贡献数据采集任务，记录定时、回补、手动任务。
- `ComplianceContributionExportTask`：代码量看板异步导出任务。

基线覆盖校准时，系统会把同一 `repository + branch_name` 的旧生效基线置为历史，再插入新基线。历史记录不删除，便于追溯。

## 页面与交互

顶部筛选采用组织/代码库级联多选：

- 组织节点和代码库节点均可搜索。
- 选择父组织时，前端展开为该组织下全部子孙代码库 ID 后提交。
- 支持全选和清空全部，避免生产环境大量代码库时依赖普通下拉框翻找。

页面主体：

- 指标卡：当前存量代码量、已覆盖仓库、已覆盖分支、缺失基线、本期新增、本期删除、本期净增、本期总变更。
- 合入趋势图：展示时间范围内新增、删除、净增趋势。
- 仓库/分支代码量表：展示当前存量、基线时间、本期净增、本期总变更，可直接补维护基线。
- 人员与 PL 组分布：保留工程贡献观察能力，但不作为绩效排行结论。
- 基线维护弹窗：支持单条维护、模板下载、Excel 批量导入。

## API 设计

统一前缀：`/api/code-compliance/contributions`

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/dashboard/summary` | 代码量核心指标 |
| GET | `/dashboard/trend` | 合入代码量日趋势 |
| GET | `/dashboard/repository-ranking` | 仓库/分支存量与本期变更排行 |
| GET | `/dashboard/person-ranking` | 创建人合入贡献排行 |
| GET | `/dashboard/category-distribution` | 仓库类型、领域、PL 组分布 |
| GET | `/records` | CR 明细兼容接口，仅用于排障和后续复用 |
| GET | `/code-baselines` | 代码量基线列表 |
| POST | `/code-baselines` | 新增一次基线覆盖校准 |
| GET | `/code-baselines/template` | 下载基线导入模板 |
| POST | `/code-baselines/import` | 批量导入基线 |
| GET | `/collect-tasks` | 采集任务历史 |
| POST | `/collect-tasks/run` | 管理员手动触发采集 |
| POST | `/export-tasks` | 创建看板导出任务 |
| GET | `/export-tasks/{id}/download` | 下载导出文件 |

## 验收标准

- 无基线的仓库分支显示为缺失基线，不误算为 0 存量。
- 有基线时，当前存量等于基线值加基线时间之后的 CR 净增。
- 多次覆盖校准只让最新基线生效，旧基线保留历史。
- 时间筛选不影响当前存量，只影响合入趋势和本期指标。
- 基线单条维护、模板下载、Excel 导入、看板导出均可用。
- 页面不再展示 CR 明细区域和 CR 明细导出。
- 级联选择器可搜索组织/代码库，选择父组织可覆盖全部子孙代码库，并支持清空全部。
