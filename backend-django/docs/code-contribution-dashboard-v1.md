# 代码贡献看板 v1 设计文档

## 背景与目标

代码合规模块已经具备组织、代码库、分支、绑定关系和漏合检测能力。基于同一套基础数据，本期新增 `代码贡献看板`，用于从代码仓、分支、人员、PL 组和时间维度观察研发代码变更贡献。

第一版只统计数据湖 CR 列表中的 `added_lines` 和 `removed_lines`，表达“统计期内代码变更量”，不表达当前分支总代码行数。

## 一期边界

- 不做综合贡献分，避免绩效化和口径争议。
- 不做异常波动识别或告警。
- 不统计当前分支总代码行数。
- 不纳入评审人、合入人等参与人，只按 CR 创建人统计。
- 与漏合风险共享组织、代码库、分支、人员等筛选口径，但不做 CR 漏合状态联动。

## 数据来源与统计口径

数据来源复用现有数据湖 CR API：

- `group_id` 来自组织主数据。
- `projects` 来自当前组织下被采集代码库的 `project_id` 集合。
- `target_branch` 来自活跃绑定分支。
- `merged_after`、`merged_before` 为采集时间范围。

核心指标：

| 指标 | 口径 |
| --- | --- |
| 新增行数 | `sum(added_lines)` |
| 删除行数 | `sum(removed_lines)` |
| 净增行数 | `sum(added_lines - removed_lines)` |
| 总变更行数 | `sum(added_lines + removed_lines)` |
| CR 数 | 贡献明细 CR 数 |
| 贡献人数 | CR 创建人去重数 |
| 活跃代码库数 | 当前筛选范围内有贡献记录的代码库去重数 |
| 活跃分支数 | 当前筛选范围内有贡献记录的分支去重数 |

## 本地存储模型

新增四类数据表：

- `ComplianceContributionRecord`：CR 贡献明细事实表，唯一键为 `repository + branch_name + change_key`。
- `ComplianceContributionDailyAggregate`：日聚合表，按日期、代码库、分支、创建人聚合。
- `ComplianceContributionCollectTask`：贡献数据采集任务，记录定时、回补、手动任务。
- `ComplianceContributionExportTask`：贡献看板异步导出任务。

明细表保存组织、代码库、分支、仓库类型、领域、责任 PL 组、作者、Focus 用户、PL 组等快照字段，确保基础数据改名后历史看板仍稳定展示。

## 采集任务与回补策略

采集范围为所有活跃代码库-分支绑定关系。

- 上线默认回补近 12 个月，按月拆分任务。
- 日常定时任务每日凌晨采集前一天。
- 手动同步仅管理员可用，支持选择时间范围、组织、代码库和分支。
- 每次采集后根据受影响日期和采集范围重算日聚合，避免重复采集造成累加误差。

采集任务诊断记录：

- 组织 `group_id`
- 项目数、分支数
- 每个分支的 `only_count`、明细数量
- 新增、更新、跳过数量

## 看板信息架构

页面采用“总览 + 明细一页式工作台”。

顶部筛选：

- 组织/代码库
- 分支
- 分支类型
- 仓库类型
- 领域
- PL 组
- 创建人
- 时间范围
- 关键词

首屏指标卡：

- 活跃仓库
- 活跃分支
- CR 数
- 贡献人数
- 新增行数
- 删除行数
- 净增行数
- 总变更行数

图表与列表：

- 日趋势：新增、删除、净增。
- 仓库/分支排行：默认按总变更行数排序。
- 类别分布：仓库类型、领域、PL 组。
- 人员排行：姓名（工号）、PL 组、参与仓库数、参与分支数、CR 数和代码变更量。
- CR 明细：标题、链接、仓库、分支、作者、PL 组、合入时间和代码行变化。

## API 设计

统一前缀：`/api/code-compliance/contributions`

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/dashboard/summary` | 核心指标 |
| GET | `/dashboard/trend` | 日趋势 |
| GET | `/dashboard/repository-ranking` | 仓库/分支排行 |
| GET | `/dashboard/person-ranking` | 人员排行 |
| GET | `/dashboard/category-distribution` | 类别分布 |
| GET | `/records` | CR 明细 |
| GET | `/collect-tasks` | 采集任务历史 |
| GET | `/collect-tasks/{id}` | 采集任务详情 |
| POST | `/collect-tasks/run` | 管理员手动触发采集 |
| POST | `/export-tasks` | 创建导出任务 |
| GET | `/export-tasks/{id}` | 查询导出任务 |
| GET | `/export-tasks/{id}/download` | 下载导出文件 |

## 权限与导出

- 查看权限采用菜单权限控制。
- 手动同步仅超级管理员可用。
- 导出采用异步任务，支持导出聚合排行和 CR 明细。

## 验收标准

- CR 明细按 `repository + branch_name + change_key` 幂等入库。
- 代码行指标计算正确。
- 作者可匹配 Focus 用户和启用 PL 组；未匹配时保留原始工号并归入 `非底软领域`。
- 日聚合重算不会重复累加。
- 看板筛选、趋势、排行、类别分布和明细下钻可用。
- 定时采集、手动采集、回补任务和导出任务均可追踪。
- 代码库管理、分支管理、漏合风险和旧 Excel 风险台账不受影响。

## 后续扩展

- 接入当前分支总代码行数数据源。
- 增加异常波动识别和告警。
- 引入评审人、合入人等参与贡献维度。
- 增加任务取消、重试、队列化和分布式执行。
- 按组织或 PL 组做更细粒度的数据权限。

