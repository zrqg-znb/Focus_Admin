# 性能监控

性能监控模块（`performance`）用于维护性能指标定义、上传测试数据、识别异常风险并对外输出趋势看板。  
这里的 `performance` 指系统性能监控，不是绩效管理。

## 模块职责

后端的主要职责分为 4 块：

- 指标定义管理：维护指标编码、基线、波动范围、方向和责任人
- 数据上传与查询：接收某个项目 / 模块 / 芯片维度的测试数据
- 风险识别：在数据越界时生成风险记录
- 导入任务：支持通过 Excel / CSV 批量导入指标定义

## 核心对象

| 对象 | 说明 |
| --- | --- |
| `PerformanceIndicator` | 指标定义，包含分类、项目、模块、芯片类型、基线与责任人 |
| `PerformanceIndicatorData` | 具体某次日期下的测试值 |
| `PerformanceRiskRecord` | 数据异常后生成的风险记录 |
| `PerformanceIndicatorImportTask` | 指标导入异步任务 |

## 路由结构

模块路由集中在 `backend-django/apps/performance/api.py`，当前可归纳为以下几组：

### 指标定义

| Method | Path | 说明 |
| --- | --- | --- |
| `GET` | `/api/performance/indicators` | 分页查询指标定义 |
| `POST` | `/api/performance/indicators` | 创建指标 |
| `PUT` | `/api/performance/indicators/{id}` | 更新指标 |
| `DELETE` | `/api/performance/indicators/{id}` | 删除指标 |
| `POST` | `/api/performance/indicators/batch-delete` | 批量删除指标 |
| `POST` | `/api/performance/indicators/batch-update` | 批量更新字段 |

### 筛选与辅助结构

| Method | Path | 说明 |
| --- | --- | --- |
| `GET` | `/api/performance/tree` | 获取分类 / 项目 / 模块树 |
| `GET` | `/api/performance/chip-types` | 获取芯片类型列表 |

### 导入与上传

| Method | Path | 说明 |
| --- | --- | --- |
| `POST` | `/api/performance/indicators/import` | 创建指标导入任务 |
| `GET` | `/api/performance/indicators/import/{task_id}` | 查询导入任务状态 |
| `POST` | `/api/performance/data/upload` | 上传测试数据 |

### 趋势与风险

| Method | Path | 说明 |
| --- | --- | --- |
| `GET` | `/api/performance/data/trend` | 获取趋势看板数据 |
| `POST` | `/api/performance/risks/query` | 分页查询风险记录 |
| `GET` | `/api/performance/risks/{id}` | 获取风险详情 |
| `POST` | `/api/performance/risks/{id}/ack` | 确认风险 |
| `POST` | `/api/performance/risks/{id}/confirm` | 确认异常有效性 |
| `POST` | `/api/performance/risks/{id}/resolve` | 标记风险已解决 |

## 实现逻辑

### 指标管理逻辑

- 指标按 `category + project + module + chip_type + name` 形成业务唯一约束
- 指标定义中同时保存基线值、单位、波动范围与波动方向
- 这些配置决定了后续数据上传时如何判定异常

### 数据上传逻辑

- 上传接口接收某个日期下的一批指标值
- 系统根据指标配置定位对应的 `PerformanceIndicator`
- 写入 `PerformanceIndicatorData` 后计算偏差值

### 风险识别逻辑

- 当数据超出允许波动范围时，生成或更新 `PerformanceRiskRecord`
- 风险对象独立存在，便于后续确认、解决和审计留痕

### 导入逻辑

- 文件上传后先创建 `PerformanceIndicatorImportTask`
- 后台线程异步处理 Excel / CSV
- 任务记录保存进度、成功数、失败数和错误信息

## 与前端对应关系

后端接口主要被以下页面使用：

| 前端页面 | 路由 | 主要依赖接口 |
| --- | --- | --- |
| 指标配置 | `/performance/config` | tree、indicators、chip-types、import |
| 趋势看板 | `/performance/dashboard` | data/trend |
| 风险管理 | `/performance/risk` | risks/query、ack、confirm、resolve |

## 相关文档

- [模块主线说明](/modules/performance)
- [前端页面参考](/frontend/views/performance)
