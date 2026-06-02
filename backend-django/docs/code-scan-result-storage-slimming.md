# code_scan 结果表瘦身落地说明

## 背景

`scan_result` 原模型按“每次扫描任务的一条缺陷结果”完整保存明细。生产环境中同一项目、同一工具每天上报大量重复缺陷时，`file_path / defect_type / severity / description / help_info / code_snippet / fingerprint` 会被反复存储，导致单表膨胀。

本次改造采用“身份去重 + 明细去重 + 扫描命中快照”的结构，保留现有接口语义，不直接删除旧生产数据。

## 新存储结构

- `scan_finding`：项目级缺陷身份，按 `project + fingerprint` 唯一，承接跨任务屏蔽继承。
- `scan_result_detail`：缺陷明细内容，按内容 hash 去重保存大文本字段。
- `scan_result_occurrence`：每次扫描命中，只保存 `task / finding / detail / line_number / shield_status` 等轻字段。
- `scan_shield_application.occurrence_id`：新屏蔽申请关联 occurrence；旧 `result_id` 保留兼容历史审批记录。

## 兼容策略

- 新上传任务写入规范化三表，不再继续写入旧 `scan_result`。
- 查询最新结果、项目概览、屏蔽记录、审批列表、集成日报时优先读 occurrence。
- 未回填或部分回填的数据自动从旧 `scan_result` fallback，避免切换期间页面空洞。
- 旧 `scan_result` 保持只读保留，真正释放空间需要回填校验和观察期后再单独归档/清理。

## 运维命令

只读评估重复度：

```bash
python manage.py audit_code_scan_storage
```

回填旧结果：

```bash
python manage.py backfill_code_scan_occurrences --batch-size 1000
```

校验回填一致性：

```bash
python manage.py verify_code_scan_occurrences --strict
```

建议先对 1-2 个项目带 `--project-id` 灰度执行，确认结果页与集成日报一致后再扩大范围。

## 验收点

- `latest-results` 返回字段不变，结果数量与旧逻辑一致。
- `projects/overview` 各工具计数与旧逻辑一致。
- 已屏蔽 fingerprint 在新扫描中继续继承为 `Shielded`。
- 路径前缀屏蔽规则仍生效。
- 审批通过后 occurrence、finding、旧 result 映射状态同步。
