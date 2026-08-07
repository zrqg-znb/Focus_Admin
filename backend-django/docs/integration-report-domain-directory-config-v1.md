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

- 不新增领域字典；领域名称由配置维护人员直接填写。
- 不调整邮件指标展示结构。

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
- 历史页领域问题详情：
  - `GET /api/integration-report/history/domain-metric-details`
  - 参数：`config_id`、`record_date`、`metric_key`；仅支持 CodeCheck、DT_Bin、Cooddy Check、Bin Scope 四项问题数指标。
  - 当前项目启用“按领域获取”时，history 页点击该四项指标会打开领域详情弹窗；未启用时继续使用原有单 ID 详情链接。
  - 响应按领域分组，返回目录、task ID、文件和 fragment 展平后的真实问题明细；同一目录可在多个领域中分别展示。

## 历史页领域详情数据湖接入

- 每日采集由后端向 `INTEGRATION_REPORT_DOMAIN_ISSUE_API_URL` 发起 JSON `POST`，请求体为 `task_id`、`file_path`、`page`、`pageSize`；本地 `DEBUG=True` 未配置地址时使用稳定 Mock 数据。
- 上游 `result.total` 按 `info` 条目计数；采集服务按页拉全每个 task ID 与目录的全部 `info`，将 `fragment` 展平为问题明细，并以 `info` 总数写入每日指标汇总。
- 领域详情快照写入 Redis，缓存键按日期、项目配置、指标隔离，TTL 为 24 小时。history 详情接口只读取该快照，缓存过期后不回源数据湖。
- 任一 task ID 与目录请求失败时，主表当天该指标显示 `error`，Redis 保存失败原因，不混入部分结果。
- 弹窗任务 ID 使用 `http://codecheck.rnd.com/{任务id}` 新窗口跳转。

## 兼容策略

- 旧字段 `code_check_task_id`、`dt_bin_task_id`、`cooddy_check_task_id`、`bin_scope_task_id` 不删除、不改名。
- 新多 task id 字段为空时，服务层可从旧单 task id 字段回退为单元素列表。
- 项目未开启 `enable_domain_metrics` 时，现有采集配置和采集结果保持原行为。
- 前端开启 `enable_domain_metrics` 后隐藏旧单 task id 输入，只维护四个指标的多 task id 列表；关闭后只维护旧单 task id。
- Fetcher 中旧单 task id 采集和责任田目录采集分开实现：未开启按领域获取时走旧接口；开启后按 `task_id x 目录规则` 遍历请求目录接口，并对返回的问题数求和。
- 按领域获取的汇总记录不保存拼接后的多个详情 URL；目录与 task ID 的详情入口由领域详情接口返回，避免超出 `detail_url` 字段长度。

## 验收标准

- 可以创建、编辑、删除责任田目录配置集，且同一目录可出现在多个领域下。
- 项目配置可以开启“按领域获取”，绑定目录配置集，并为四个指标保存多个 task id。
- 旧项目配置查询、编辑和保存不丢失旧字段。
- 只有单 task id 且未开启按领域获取时，数据采集仍保持旧接口行为。
- 开启按领域获取时，四个问题数指标按绑定配置集里的目录逐个请求并累加。
- history 页中开启按领域获取的四个问题数指标可按领域 Tab 查看目录、task ID 与真实问题明细，并在展开行查看完整代码上下文。
- 后端测试覆盖目录配置 CRUD、多 task id 归一化、项目配置保存兼容。
