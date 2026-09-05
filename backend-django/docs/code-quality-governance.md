# 独立代码问题治理模块

模块位于 `apps.agent_tools.code_quality_governance`，与现有 `apps.code_scan` 完全隔离。

## 接入

机器接入使用 `POST /api/agent-tools/code-quality-governance/reports/ingest`，请求包含 `project_id`、`responsibility_id`、`tool_name` 和第三方 JSON 报文；页面上传使用同一路由前缀下的 `/reports/upload`。

问题身份按 `identity.issue_key`、`legacy_fingerprints[0]`、`fingerprint` 和平台回退身份依次归并。原始报告、finding、identity、evidence 均保留。

## 屏蔽审批

责任田维护审批人员范围，申请人提交时选择审批人。申请、通过、驳回都会同步更新稳定问题状态并写入审计日志；同一稳定问题存在待审批申请时不能重复提交。

## 菜单初始化

执行现有 `init_agent_tools` 管理命令后，会创建“代码问题治理”菜单和独立权限。
