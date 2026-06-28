# 需求看板全量缓存预热

## 问题

需求看板原有查询链路会在用户提交筛选时实时请求数据湖。项目选择较多时，后端需要按分页扫描大量需求明细，用户白天打开看板会等待较久。

## 目标

- 夜间提前拉取所有未删除且已配置 `design_id` 和责任团队的项目需求。
- 把标准化后的需求明细写入 Django cache，通常对应 Redis。
- 白天 `data`、`summary`、`export` 优先复用全量缓存，并按用户筛选条件本地过滤。
- 缓存中的明细包含责任 PL 组映射结果，支持白天按责任 PL 组筛选。
- 不新增前端页面、不新增 API、不把需求明细落 MySQL。

## 调度入口

系统定时任务可配置函数：

```text
apps.project_manager.requirement_board.requirement_board_services.run_scheduled_requirement_board_cache_refresh
```

推荐配置：

| 字段 | 示例 |
| --- | --- |
| `trigger_type` | `cron` |
| `cron_expression` | `0 3 * * *` |
| `max_instances` | `1` |
| `coalesce` | `true` |
| `allow_concurrent` | `false` |

## 缓存策略

全量缓存覆盖范围为所有 `Project.is_deleted = False` 且完成需求数据源配置的项目，包含已关闭但未删除项目。缓存写入时会使用刷新锁，避免多个调度任务同时扫描数据湖。

查询读取顺序：

1. 用户级 prepared cache。
2. 全量预热缓存。
3. 原有实时数据湖查询。

`/query-prepare` 会先做轻量 full cache 覆盖判断。只要缓存存在且当前项目集合是缓存项目集合子集，就直接返回 `ready`，避免白天查询被后台准备任务拦住。

如果用户选择了缓存快照中不存在的新项目，后端会自动回退实时查询，避免返回不完整数据。

排障提示：

- 当前 full cache key 为 `pm:requirement-board:full:v2:all-configured`。
- 发布责任 PL 组字段后，旧 `v1` 缓存不会命中新查询，需要重新预热。
- 若 `/query-prepare` 仍返回 `async`，优先检查 full cache 是否存在、是否过期、是否覆盖当前项目。

责任 PL 组口径：

- 取需求第一个开发责任人 username。
- 只匹配启用状态的 PL 组成员关系。
- 同一用户命中多个 PL 组时，按 `-sort, name, id` 取第一个。
- 未命中统一为 `未识别PL领域`，筛选值为 `unknown`。

## 配置项

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `REQUIREMENT_BOARD_FULL_CACHE_TTL_SECONDS` | `57600` | 全量缓存有效期，默认 16 小时 |
| `REQUIREMENT_BOARD_FULL_CACHE_PAGE_SIZE` | `500` | 预热扫描页大小 |
| `REQUIREMENT_BOARD_FULL_CACHE_MAX_PAGES` | `200` | 预热最多扫描页数 |
| `REQUIREMENT_BOARD_FULL_CACHE_LOCK_TTL_SECONDS` | `1800` | 防并发刷新锁时长 |

## 验收标准

- 调度函数返回项目数、团队数、需求数、扫描页数、生成时间和缓存键。
- 缓存命中后，明细、汇总和导出不再访问数据湖。
- 项目、团队、类型、状态、验证策略、标题、责任人和时间筛选仍保持现有口径。
- 未配置 `design_id` 或责任团队的项目不会进入预热范围。
