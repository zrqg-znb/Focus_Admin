# 需求看板责任 PL 组映射

## 问题

需求看板从数据湖拿到的 `service_name / servioce_name` 是虚拟责任团队，不等同于系统组织管理中的实际 PL 组。用户需要在需求明细中看到可落到 PL 管理口径的责任 PL 组，并按 PL 组筛选。

## 目标

- 根据需求开发责任人自动映射责任 PL 组。
- 新增独立的责任 PL 组列和筛选，不影响开发责任人列与筛选。
- 筛选项复用核心 PL 组 API：`GET /api/core/pl/all`。
- 不新增数据库字段、表或需求看板 API 路径。

## 后端口径

需求标准化时新增：

- `responsible_pl_group_id`
- `responsible_pl_group_name`

映射规则：

1. 标准化数据湖的 `develop_owner / develop_user` 得到 `develop_users`。
2. 如果存在多个开发责任人，只取 `develop_users[0]`。
3. 只匹配启用状态的 `core.PlGroup.members`。
4. 同一用户命中多个 PL 组时，按 `-sort, name, id` 取第一个。
5. 未命中、无开发责任人、仅命中禁用 PL 组时，输出 `responsible_pl_group_id = null`、`responsible_pl_group_name = 未识别PL领域`。

筛选字段：

```json
{
  "responsible_pl_group_ids": ["pl-group-id", "unknown"]
}
```

`unknown` 表示筛选未识别 PL 领域。该字段为本地过滤条件，不下推数据湖，并纳入 prepared cache、summary cache、filtered cache 和全量缓存过滤。

## 前端口径

- 明细表在“团队”后新增“责任PL组”列。
- 表头筛选使用多选 PL 组下拉，选项来自 `/api/core/pl/all`，末尾追加“未识别PL领域”。
- 默认筛选、保存偏好、恢复偏好、导出都携带 `responsible_pl_group_ids`。

## 验收标准

- 单开发责任人能映射到正确启用 PL 组。
- 多开发责任人只按第一个人映射。
- 多 PL 组命中时排序第一生效。
- 未命中可展示并筛选“未识别PL领域”。
- 责任 PL 组筛选不影响开发责任人字段和开发责任人筛选。
