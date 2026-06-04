# 代码合规基础数据一期

## 背景

现有 `code_compliance` 模块承载旧 Excel 风险台账导入、岗位概览、用户详情和分支处理能力。一期升级需要保留旧能力，同时先补齐代码库系统联动前所需的组织、代码库、分支基础数据管理。

一期不实现漏合风险检测，只提供主数据维护、Excel 批量导入和代码库-分支绑定。

## 范围

本期新增两个前端入口：

- `代码库管理`：组织树与代码库列表合一，左侧维护组织，右侧维护当前组织直接挂载的代码库。
- `分支管理`：维护分支主数据，并从分支侧批量绑定代码库。

旧入口继续保留：

- `合规风险概览`
- `合规风险详情`
- 旧 Excel 风险台账上传 API
- 旧分支整改状态更新 API

## 数据模型

新增模型位于 `backend-django/apps/code_compliance/models.py`。

| 模型 | 说明 | 关键字段 |
| --- | --- | --- |
| `ComplianceOrganization` | 公司代码库系统组织主数据 | `group_id`、`name`、`parent`、`mode`、`domain`、`remark` |
| `ComplianceRepository` | 公司代码库系统代码库主数据 | `project_id`、`project_name`、`project_url`、`organization`、`mode`、`repo_type`、`responsibility_groups`、`domain` |
| `ComplianceManagedBranch` | 新分支主数据，区别于旧风险台账 `ComplianceBranch` | `branch_name`、`created_date`、`branch_type`、`alias`、`purpose`、`domain` |
| `ComplianceRepositoryBranch` | 代码库与分支绑定关系 | `repository`、`branch`，唯一约束 `repository + branch` |

`repo_type` 使用 core 字典，编码固定为 `code_compliance_repo_type`。责任领域绑定 core `PlGroup`，不再用自由文本。

## API

新接口统一挂在 `/api/code-compliance/base` 下。

| 资源 | 能力 |
| --- | --- |
| `/organizations/tree` | 返回组织树，节点输出 `repository_count` |
| `/organizations` | 组织 CRUD |
| `/organizations/template`、`/organizations/import` | 组织模板下载与 Excel 导入 |
| `/repositories` | 代码库分页列表和 CRUD，支持 `organization_id`、关键词、模式、领域、仓库类型过滤 |
| `/repositories/template`、`/repositories/import` | 代码库模板下载与 Excel 导入 |
| `/repositories/batch-bind-branches` | 从代码库侧批量绑定分支，支持 `append` / `replace` |
| `/branches` | 分支分页列表和 CRUD，输出关联代码库数 |
| `/branches/template`、`/branches/import` | 分支模板下载与 Excel 导入 |
| `/branches/batch-bind-repositories` | 从分支侧批量绑定代码库，支持 `append` / `replace` |

Excel 导入只导入基础字段，不导入代码库-分支绑定关系。

## 前端

新增 API wrapper：

- `web/apps/web-ele/src/api/compliance/base.ts`

新增页面：

- `web/apps/web-ele/src/views/compliance/repository/index.vue`
- `web/apps/web-ele/src/views/compliance/branch/index.vue`

代码库管理采用左右结构：

- 左侧组织树包含搜索、展开、收起、选中态和节点操作。
- “全部组织”为虚拟节点，进入页面默认选中并展示全量代码库。
- 组织新增/编辑使用 `ElDialog`。
- 代码库新增/编辑使用 `ElDrawer`。
- 右侧代码库列表显示当前组织路径、组织摘要、代码库数量和批量绑定入口。

分支管理采用 `zq-table`：

- 支持分支 CRUD、Excel 导入、模板下载。
- 支持选中多个分支后批量绑定代码库。

## 初始化

新增管理命令：

```bash
python manage.py init_code_compliance
```

命令会补齐：

- `代码合规` 菜单目录。
- 旧风险入口菜单。
- 新 `代码库管理` 和 `分支管理` 菜单。
- 新旧接口权限。
- `code_compliance_repo_type` 字典及默认仓库类型项。

命令不清理旧风险菜单和旧风险 API。

## 测试重点

- 组织树、组织防循环、组织删除约束。
- 代码库按组织过滤、外部 `project_id` 唯一性、PL 组绑定、仓库类型字典校验。
- 组织/代码库/分支导入的新增、更新、忽略和错误行反馈。
- 代码库侧绑定分支、分支侧绑定代码库的 `append` / `replace`。
- 旧 Excel 上传、旧风险概览、旧风险详情、旧分支状态更新不受影响。
