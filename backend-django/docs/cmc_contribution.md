# CMC 贡献看板 v1

数据通过 `CMC_CONTRIBUTION_API_URL` 从数据湖按日同步到本地快照。固定部门为底层软件开发部；每日 01:00 同步前一日，管理员可在页面补数最多 31 天。

数据湖请求体固定为 `pageIndex`、`pageSize`、`params` 三个字段；业务筛选均放在 `params`，分页字段不再出现在其中。响应顶层 `result` 为成员列表，顶层 `total/pageIndex/pageSize` 控制翻页。每条成员数据必须满足 `merged_login == core.User.username` 且 `name == core.User.name`；成功后保存对应的 `core.User` 外键，并按该用户 ID 汇总。任一成员不匹配时，当日同步失败且不会覆盖已有快照。

- API：`/api/cmc-contribution/dashboard/summary`、`/dashboard/trend`、`/dashboard/person-ranking`、`/dashboard/comment-distribution`、`/persons`、`/sync-tasks`。
- 有效检视意见为四级检视意见和 Issue 的合计；密度以检视代码行为分母。
- 零检视 MR 数按人员、按日对 `cnt_total × 上游比例` 四舍五入后保存，再进行跨日聚合。
- 固定业务请求参数（部门、等级、排序等）维护在服务常量中；部署时仅配置数据湖 URL、Token、请求头及连接参数。
- 执行 `python manage.py init_cmc_contribution` 创建菜单、权限和每日任务。
