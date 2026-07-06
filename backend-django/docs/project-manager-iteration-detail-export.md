# 迭代详情导出

## 问题和目标

健康迭代详情页需要一键导出当前迭代的各类数据，供项目经理和质量运营人员离线核对指标与需求明细。导出文件由后端统一生成，避免前端分页、筛选状态或浏览器内存影响数据完整性。

## 范围

- 页面：`web/apps/web-ele/src/views/project-manager/iteration/detail.vue`
- 接口：`GET /api/project-manager/iterations/iteration/{iteration_id}/export-detail`
- 导出范围：当前选中的单个迭代。
- 不新增菜单、权限码、字典、迁移或初始化数据。

## Sheet 口径

导出文件为 XLSX，每一类数据独立 sheet：

- `迭代基础信息`：项目、迭代、周期、当前迭代、健康状态、最新指标日期。
- `入口指标`：DR/SR 分解率等入口指标。
- `出口指标`：置 A/C 率、测试自动化率、用例执行率、缺陷修复率、代码评审率、代码覆盖率。
- `需求IDPCA状态`：当前迭代全部需求明细。
- `未分解需求`：`need_breakdown=True` 且 `is_decomposed=False` 的需求。

## 开发责任人口径

需求类 sheet 和前端需求表格新增“开发责任人”。字段优先级为：

1. `develop_owner`
2. `develop_user`
3. `develop_users`
4. `owner`

`owner` 仅作为历史缓存数据的兼容回退，不再作为面向用户的“责任人”主口径。

## 验收标准

- 点击详情页“导出详情”按钮，下载 `{项目名}-{迭代名称}-迭代详情-{YYYY-MM-DD}.xlsx`。
- 导出文件可被 Excel 或 openpyxl 正常打开，并包含 5 个预期 sheet。
- 需求类 sheet 均包含“开发责任人”，且未分解需求 sheet 只包含未分解需求。
- 导出接口不存在分页依赖，当前迭代缓存中的需求明细会完整写入文件。
