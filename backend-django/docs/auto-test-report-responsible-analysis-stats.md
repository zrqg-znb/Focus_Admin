# Auto Test Report 车型责任人与失败分析统计

## 责任人

- 每个车型可绑定零到多个 `core_user` 用户作为责任人。
- 责任人仅通过车型配置页面维护；一站式 Excel 导入不会创建、覆盖或删除责任人绑定。
- 车型配置、用例管理和每日执行结果的全量车型概览均展示责任人姓名。用户未填写姓名时展示用户名。

## 第三方统计接口

`GET /api/auto-test-report/daily-results/analysis-stats`

该接口显式使用 `auth=None`，供受控内网第三方系统拉取并按车型责任人发送 IM 通知。

参数：

- `domain`：必填，`cockpit`、`cockpit_soc` 或 `vehicle`。
- `execute_date`：可选，`YYYY-MM-DD`；省略时按服务端当天统计。

返回 `summary`（领域总计）和 `items`（车型明细）。车型明细包含平台、车型、责任人及以下计数：

- `failed_count`：当日最新结果中未成功的用例数，包含 `failed`、`timeout` 和 `skip`。
- `need_analysis_count`：当日最新结果中状态为 `failed`、`timeout` 或 `skip` 的用例数。
- `pending_analysis_count`：需要分析的用例中尚未填写 `failure_category` 的数量。`items` 仅返回该值大于 0 的车型，`summary` 仍统计领域下所有活跃车型。

失败根因大类支持 `version`（版本问题）、`environment`（环境问题）、`case`（用例问题）和 `non_mcu`（非MCU问题）。其中环境问题、用例问题和非MCU问题均不阻塞座舱 MCU 下游任务放行。
- `version_failure_count`：需要分析的用例中根因分类为 `version` 的数量。

统计仅纳入当前启用的车型和用例，并按车型、执行日期、用例取最新一条上报结果。同日未执行用例不并入上述四项计数，但车型会保留在 `items` 中，责任人为空时返回空数组。

示例：

```bash
curl 'https://benefit.example.com/api/auto-test-report/daily-results/analysis-stats?domain=cockpit&execute_date=2026-08-11'
```
