# 自动化测试报告后端实现附录

自动化测试报告后端位于 `backend-django/apps/auto_test_report/`，按平台、车型、用例、每日明细、每日汇总五层对象组织，并在平台 / 车型 / 用例层补入座舱与车控双领域能力。

## 核心模型

模型位于 `auto_test_report_model.py`：

- `McuPlatform`
- `VehicleModel`
- `TestCase`
- `DailyExecutionBatch`
- `DailyExecutionResult`

其中：

- `McuPlatform.domain`
  区分 `cockpit` / `vehicle`，旧数据默认归为座舱领域
- `VehicleModel.viu_codes`
  车控车型可用的 VIU 编号子集，按车型保存
- `TestCase.viu_code`
  车控领域与 `vehicle + case_no` 共同组成唯一键，座舱领域保持空值

## 核心服务职责

服务位于 `auto_test_report_services.py`，负责：

- 平台与车型 CRUD
- 用例增删改查、导入、导出，支持按领域和 VIU 编号过滤
- 测试结果上报，座舱按 `vehicle_code + case_no` 解析，车控按 `vehicle_code + viu_code + case_no` 解析
- 每日汇总重算
- 全量概览与单车型明细查询，车控视图下明细会带出 VIU 编号
- 异常原因补录与历史建议

## 核心 API

接口位于 `auto_test_report_api.py`，典型路由包括：

- `/api/auto-test-report/platforms`
- `/api/auto-test-report/vehicles`
- `/api/auto-test-report/test-cases`
- `/api/auto-test-report/daily-results/summary`
- `/api/auto-test-report/daily-results/overview`
- `/api/auto-test-report/daily-results/list`
- `/api/auto-test-report/report/daily-results`

## 实现重点

- 每日汇总不是外部直接上传，而是由 `recalculate_daily_batch` 从明细重算
- `skip_count` 通过“总用例数 - 有结果用例数”推导
- 失败 / 超时结果支持回看历史 `failure_reason` 给出建议值
- 前端和导入模板通过 `domain` 统一切换座舱 / 车控视图，后端按同一字段集返回对应结构

## 对应主线文档

- [自动化测试报告](/modules/auto-test-report)
