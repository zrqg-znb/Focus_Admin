# 性能监控后端实现附录

性能监控后端位于 `backend-django/apps/performance/`，围绕指标定义、指标数据、风险记录和导入任务展开。

## 核心模型

主要模型位于 `models.py`：

- `PerformanceIndicator`
  指标定义、基线、阈值、责任边界
- `PerformanceIndicatorData`
  某日期下的指标值与波动值
- `PerformanceRiskRecord`
  异常识别后的风险记录
- `PerformanceIndicatorImportTask`
  指标导入任务

## 核心服务职责

主要服务位于 `services.py`，核心职责包括：

- 指标树和列表查询
- 指标批量导入
- 测试数据上传
- 趋势数据查询
- 风险识别与风险记录生成

## 后端 API

主要 API 位于 `api.py`，典型路由包括：

- `/api/performance/tree`
- `/api/performance/indicators`
- `/api/performance/indicators/import`
- `/api/performance/data/trend`
- `/api/performance/data/upload`
- `/api/performance/risks/query`

## 实现重点

- 风险记录不是前端手工创建，而是在数据上传时根据阈值自动识别
- 趋势看板读取的是时间序列数据，不是单条当前快照
- 导入任务独立建模，避免指标初始化动作阻塞页面

## 对应主线文档

- [性能监控](/modules/performance)
