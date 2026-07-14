# 代码贡献看板 v1 设计文档

## 背景与目标

代码合规模块已经具备组织、代码库、分支绑定、漏合检测和数据湖 CR 采集能力。`代码贡献看板` 在此基础上面向生产环境回答三个问题：

- 选定统计期内，哪些代码库和分支新增代码贡献最高。
- 各 PL 组、创建人、仓库类型和领域的新增贡献分布如何。
- 合入代码量在时间维度上是否持续、集中或波动。

本页面不是 CR 台账，也不做个人绩效结论。CR 详情继续在公司代码库系统中查看，平台保留 CR 事实表用于聚合统计、采集诊断和后续扩展。

## 一期边界

- 不做代码量基线统计，不表达代码库当前真实总代码行数。
- 不展示 CR 明细列表，不在页面提供 CR 明细导出入口。
- 不做综合贡献分，不做异常波动识别，不输出绩效排序结论。
- 不纳入评审人、合入人等参与人，只按 CR 创建人统计新增贡献。
- 旧版 `code-baselines` 模型和 API 暂保留兼容，但当前看板、导出和主口径不再使用。

## 数据来源与统计口径

数据来源为数据湖中已合入的 CR、MR 的 `added_lines`、`removed_lines` 字段，采集范围来自代码合规模块中启用的组织、代码库和活跃绑定分支。

### CR / MR 接入边界

- CR 仍使用组织级接口 `GET /api/v4/groups/{group_id}/change_requests`，可按组织批量携带多个 `projects`。
- MR 使用项目级接口 `GET /api/v4/projects/{project_id}/merge_requests`，数据湖不支持组织级 MR 查询，因此按“项目 x 活跃绑定分支”请求。
- MR 与 CR 都使用 `only_count`、目标分支、合入时间范围和分页参数；MR 单个采集任务最多 5 个请求并发，项目失败会写入任务诊断，不会被静默视为零数据。
- CR 的幂等标识为 `change_key`；MR 没有 `change_key`，使用上游全局 `id` 作为 `source_change_id`。事实表唯一键为 `repository + branch_name + source_mode + source_change_id`。
- MR 首次接入不做历史回补，仅从上线后的定时增量和管理员手动同步开始积累。MR 不参与漏合检测、漏合风险和漏合任务历史。
- 组织树按模式隔离：CR 父组织下只允许 CR 子组织和代码库，MR 同理；代码库模式必须与所属组织一致。

核心指标：

| 指标 | 口径 | 看板定位 |
| --- | --- | --- |
| 新增行数贡献 | 时间范围内 `sum(added_lines)` | 主指标、主排行口径 |
| 删除行数 | 时间范围内 `sum(removed_lines)` | 辅助观察 |
| 总变更行数 | 时间范围内 `sum(added_lines + removed_lines)` | 辅助观察 |
| CR 数 | 时间范围内 CR 明细数量 | 辅助观察 |
| 贡献人数 | 时间范围内 distinct `author_username` | 辅助观察 |
| 参与代码库 / 分支 | 时间范围内有 CR 贡献的代码库、分支数量 | 辅助观察 |

`net_lines = added_lines - removed_lines` 仍保留在事实表和兼容接口中，但不作为看板主指标、主排序或重点展示字段。

## 本地存储模型

- `ComplianceContributionRecord`：CR/MR 贡献事实表，保留 `source_mode`、`source_change_id` 以及新增、删除、净增、总变更等明细字段。
- `ComplianceContributionDailyAggregate`：日聚合表，按日期、代码库、分支、创建人等维度聚合。
- `ComplianceContributionCollectTask`：贡献数据采集任务，记录定时、回补、手动任务和诊断信息。
- `ComplianceContributionExportTask`：代码贡献看板异步导出任务。
- `ComplianceContributionCodeBaseline`：历史兼容表，当前看板不再读取或展示。

## 页面与交互

顶部筛选采用组织/代码库级联多选：

- 组织节点和代码库节点均可搜索。
- 选择父组织时，前端展开为该组织下全部子孙代码库 ID 后提交。
- 支持全选和清空全部，避免生产环境大量代码库时依赖普通下拉框翻找。
- 来源模式提供 `全部 / CR / MR` 分段筛选，默认汇总两类数据；切换后会清空不匹配的组织、代码库和分支范围。

页面主体：

- 指标卡：新增行数贡献、参与代码库、参与分支、CR 数、贡献人数、删除行数、总变更行数。
- 趋势图：展示新增行数、删除行数、总变更行数趋势，其中新增行数为主口径。
- PL 组趋势图：展示新增贡献最高的 PL 组在日期维度上的贡献变化，用于观察团队贡献节奏和集中度。
- 仓库 / 分支新增贡献表：按 `added_lines DESC, cr_count DESC` 排序，展示新增行数、删除行数、总变更、CR 数和贡献人数。
- 人员合入贡献表：按创建人聚合，重点展示新增行数和 CR 数。
- PL 组新增贡献表：按作者 PL 组聚合，重点展示新增行数和 CR 数。
- 仓库/分支 Top、PL 组 Top、人员 Top 图表：均按新增行数贡献展示。

## API 设计

统一前缀：`/api/code-compliance/contributions`

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/dashboard/summary` | 代码贡献核心指标 |
| GET | `/dashboard/trend` | 新增、删除、总变更趋势 |
| GET | `/dashboard/pl-group-trend` | PL 组新增贡献趋势 |
| GET | `/dashboard/repository-ranking` | 仓库 / 分支新增贡献排行 |
| GET | `/dashboard/person-ranking` | 创建人新增贡献排行 |
| GET | `/dashboard/category-distribution` | 仓库类型、领域、PL 组新增贡献分布 |
| GET | `/records` | CR 明细兼容接口，仅用于排障和后续复用 |
| GET | `/collect-tasks` | 采集任务历史 |
| POST | `/collect-tasks/run` | 管理员手动触发采集 |
| POST | `/export-tasks` | 创建看板导出任务 |
| GET | `/export-tasks/{id}/download` | 下载导出文件 |

所有看板、排行、趋势、明细与导出接口支持可选 `source_mode=CR|MR`。未传时默认汇总两类来源；手动采集任务也可传该字段限定采集范围。

兼容保留：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/code-baselines` | 旧版代码量基线列表，当前看板不使用 |
| POST | `/code-baselines` | 旧版代码量基线维护，当前看板不使用 |
| GET | `/code-baselines/template` | 旧版基线导入模板，当前看板不使用 |
| POST | `/code-baselines/import` | 旧版基线导入，当前看板不使用 |

## 验收标准

- 页面不再出现基线、存量、缺失基线、补基线、维护基线等看板入口或文案。
- Summary、仓库 / 分支排行、人员排行、PL 组分布和导出均不依赖 `ComplianceContributionCodeBaseline`。
- 仓库 / 分支、人员、PL 组、类别分布默认按 `added_lines` 降序展示。
- 总览看板展示 PL 组贡献趋势、仓库/分支 Top、PL 组 Top 和人员 Top。
- 趋势图以新增行数为主，删除和总变更只作为辅助观察。
- 导出文件不包含当前存量、基线代码量、基线时间、是否有基线、净增重点列。
- 旧基线 API 仍可兼容访问，但不影响当前看板展示和统计口径。
