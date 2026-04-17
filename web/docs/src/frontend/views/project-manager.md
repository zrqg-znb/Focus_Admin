# 项目管理前端附录

项目管理前端主要位于 `web/apps/web-ele/src/views/project-manager/`，采用“项目主数据 + 多子域页面”结构，每个子域围绕同一个项目上下文展开。

## 页面层级

主要页面包括：

- `project/`
  项目主数据与能力开关
- `milestone/`
  里程碑节点、风险与日志
- `iteration/`
  迭代推进与指标
- `code-quality/`
  代码质量模块与指标
- `hardware/`
  硬件与典配相关页面
- `requirement_workspace/`
  需求工作区面板

## API 分层

API 主要位于：

- `src/api/project-manager/*.ts`

特点：

- 每个子域一个独立 API 文件
- 列表页普遍配合 `zq-table`
- `data.ts` 负责列定义、过滤项和表单 schema

## 交互特征

- 项目页负责承接子域能力开关
- 里程碑和迭代页依赖项目上下文
- 代码质量和 DTS 更偏指标展示与趋势表格

## 对应主线文档

- [项目管理](/modules/project-manager)
