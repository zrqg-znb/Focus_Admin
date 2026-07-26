# CMC 贡献看板 v1

数据通过 `CMC_CONTRIBUTION_API_URL` 从数据湖按日同步到本地快照。固定部门为底层软件开发部；每日 01:00 同步前一日，管理员可在页面补数最多 31 天。

数据湖请求体固定为 `pageIndex`、`pageSize`、`params` 三个字段；业务筛选均放在 `params`，分页字段不再出现在其中。响应从 `result.list` 读取，使用 `result.total/pageIndex/pageSize` 控制翻页。数据湖的 `name` 与 `merged_login` 分别保存为显示姓名和登录名，并按登录名关联 `core.User`。

- API：`/api/cmc-contribution/dashboard/summary`、`/dashboard/trend`、`/dashboard/person-ranking`、`/dashboard/comment-distribution`、`/persons`、`/sync-tasks`。
- 有效检视意见为四级检视意见和 Issue 的合计；密度以检视代码行为分母。
- 零检视 MR 数按人员、按日对 `cnt_total × 上游比例` 四舍五入后保存，再进行跨日聚合。
- 固定业务请求参数（部门、等级、排序等）维护在服务常量中；部署时仅配置数据湖 URL、Token、请求头及连接参数。
- 执行 `python manage.py init_cmc_contribution` 创建菜单、权限和每日任务。
