# 集成报告责任田目录配置 V1

## 背景

集成报告中的部分项目指标来自数据湖任务。实际项目里同一个指标可能被拆成多个任务，例如一个项目的 CodeCheck 结果对应三个 task id，需要分别请求后累加。同时后续需要按责任田领域和目录统计问题数，因此需要先补齐“领域 x 目录”的配置能力，并让项目配置可以绑定一套目录配置。

## 目标

- 新增可复用的“责任田领域 x 目录配置集”，一个配置集下可以维护多个领域，每个领域可以维护多个目录字符串。
- 同一个目录字符串允许出现在同一配置集的多个领域中，不做唯一约束。
- 项目配置新增“按领域获取”开关；开启后可绑定一套目录配置集，并为四个指标配置多个 task id。
- 四个支持多 task id 的指标为：CodeCheck 错误数、DT_Bin错误数、Cooddy Check错误数、Bin Scope 错误数。
- 保留现有单 task id 字段和旧采集行为，已配置项目不失效。

## 非目标

- V1 不实现最终的数据湖按领域目录请求逻辑；后续会重写数据湖请求与按领域统计。
- V1 不新增领域字典；领域名称由配置维护人员直接填写。
- V1 不改变历史页和邮件中的指标展示结构。

## 接口与页面

- 新增页面：`/integration-report/domain-directory-sets`
  - 主表使用 zq-table，分页展示配置集名称、启用状态、领域数、目录数、更新时间、操作。
  - 抽屉维护配置集基础信息和领域目录规则，支持批量粘贴目录。
- 新增接口：
  - `GET /api/integration-report/domain-directory-sets`
  - `GET /api/integration-report/domain-directory-sets/options`
  - `GET /api/integration-report/domain-directory-sets/{set_id}`
  - `POST /api/integration-report/domain-directory-sets`
  - `PUT /api/integration-report/domain-directory-sets/{set_id}`
  - `DELETE /api/integration-report/domain-directory-sets/{set_id}`
- 扩展项目配置接口：
  - `enable_domain_metrics`
  - `domain_directory_set_id`
  - `code_check_task_ids`
  - `dt_bin_task_ids`
  - `cooddy_check_task_ids`
  - `bin_scope_task_ids`

## 兼容策略

- 旧字段 `code_check_task_id`、`dt_bin_task_id`、`cooddy_check_task_id`、`bin_scope_task_id` 不删除、不改名。
- 新多 task id 字段为空时，服务层可从旧单 task id 字段回退为单元素列表。
- 项目未开启 `enable_domain_metrics` 时，现有采集配置和采集结果保持原行为。

## 验收标准

- 可以创建、编辑、删除责任田目录配置集，且同一目录可出现在多个领域下。
- 项目配置可以开启“按领域获取”，绑定目录配置集，并为四个指标保存多个 task id。
- 旧项目配置查询、编辑和保存不丢失旧字段。
- 后端测试覆盖目录配置 CRUD、多 task id 归一化、项目配置保存兼容。
