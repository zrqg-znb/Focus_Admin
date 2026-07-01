# Auto Test Report 下游 Commit ID 链路

## 背景

座舱下游 CI 触发需要携带 `commit-id`。CI 构建产品包时会把本次构建使用的 commit-id 上报到本系统，测试人员完成取包和自动化验证后，在执行看板选择对应 commit-id 触发下游任务。

## 数据规则

- `commit_id` 按 trim 后的精确字符串去重，空值拒绝。
- 重复上传同一个 commit-id 不新增记录，只更新最近上传时间和上传次数。
- 每次人工或定时触发尝试都会写入使用记录，包含执行日期、触发方式、触发人、结果、消息和 dry-run 状态。

## 接口规则

- CI 上传：`POST /api/auto-test-report/report/commit-ids`
- 后台查询：`GET /api/auto-test-report/downstream-commits`
- 使用记录：`GET /api/auto-test-report/downstream-commits/{id}/usages`
- 人工触发：`POST /api/auto-test-report/daily-results/downstream-trigger`，请求体必须包含 `execute_date` 和 `commit_id`。

### CI 上传示例

```bash
curl -X POST 'http://127.0.0.1:8000/api/auto-test-report/report/commit-ids' \
  -H 'Content-Type: application/json' \
  -d '{
    "commit_id": "mock-cockpit-20260701-001"
  }'
```

重复上传同一个 `commit_id` 时会返回同一条记录，并累加 `upload_count`。

## 触发规则

- 人工触发仍沿用座舱门禁：无缺失执行、无未分类非成功、无版本问题。
- 人工触发时 commit-id 必须已由 CI 上报；门禁失败也记录一次失败使用记录。
- 定时任务仅在全部座舱用例成功时触发，并自动选择最近上传且未使用过的 commit-id。
- 当前 CI 调用仍是 dry-run 占位实现，生产环境替换 `invoke_cockpit_downstream_ci` 时必须把 `commit_id` 放入真实请求体。
