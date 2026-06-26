# Auto Test Report 座舱下游 CI 放行

## 背景

座舱自动化每日结果需要在质量满足条件时触发下游任务。当前真实 CI 接口暂未在代码中固化，本功能先提供统一的门禁判断、人工触发入口和定时任务入口，生产环境可替换占位调用实现。

## 规则

- 执行范围按 `execute_date` 的每日结果判定，只处理座舱领域。
- 定时任务自动触发要求所有活跃座舱车型的活跃用例当日都有最新结果，且结果全部为 `success`。
- 页面人工触发允许环境问题和用例问题存在，但必须满足：
  - 无缺失执行结果；
  - 所有 `failed`、`timeout`、`skip` 均已填写根因大类；
  - 不存在 `版本问题`。
- 根因大类固定为：
  - `version`：版本问题；
  - `environment`：环境问题；
  - `case`：用例问题。

## 接口

- `GET /api/auto-test-report/daily-results/overview`
  - 概览行与汇总增加非版本问题数、版本问题数、未分类非成功数、缺失执行数。
  - 汇总增加 `downstream_trigger_enabled` 和 `downstream_trigger_block_reasons`，供前端控制按钮状态。
- `PATCH /api/auto-test-report/daily-results/{result_id}/failure-reason`
  - 入参增加 `failure_category`，支持 `failed`、`timeout`、`skip`。
  - `success` 结果不允许维护异常原因和根因大类。
- `POST /api/auto-test-report/daily-results/downstream-trigger`
  - 入参：`execute_date`。
  - 后端会重新计算座舱全量门禁；不满足条件时返回 400。

## 定时任务

初始化命令 `python manage.py init_auto_test_report` 会创建默认禁用任务：

- code：`auto_test_report_cockpit_downstream_check`
- cron：`0 23 * * *`
- task：`apps.auto_test_report.auto_test_report_services.run_scheduled_cockpit_downstream_check`
- kwargs：`{"date_offset": 0}`

生产环境确认 CI 后，可在定时任务管理中启用任务并调整 cron 或 `date_offset`。

## 生产替换点

真实 CI 请求集中替换 `apps.auto_test_report.auto_test_report_services.invoke_cockpit_downstream_ci`。该函数当前只返回 dry-run 成功结果，不发起外部网络请求。

替换时建议补齐：

- CI URL 与鉴权配置；
- 请求体字段映射；
- 超时和错误重试；
- 失败日志与告警策略。
