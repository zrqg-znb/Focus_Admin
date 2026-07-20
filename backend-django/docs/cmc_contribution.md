# CMC 贡献看板 v1

数据通过 `CMC_CONTRIBUTION_API_URL` 从数据湖按日同步到本地快照。固定部门为底层软件开发部；每日 01:00 同步前一日，管理员可在页面补数最多 31 天。

- API：`/api/cmc-contribution/dashboard/summary`、`/persons`、`/sync-tasks`。
- 有效检视意见为四级检视意见和 Issue 的合计；密度以检视代码行为分母。
- 零检视 MR 数按人员、按日对 `cnt_total × 上游比例` 四舍五入后保存，再进行跨日聚合。
- 执行 `python manage.py init_cmc_contribution` 创建菜单、权限和每日任务；部署时配置数据湖 URL、Token 与请求头。
