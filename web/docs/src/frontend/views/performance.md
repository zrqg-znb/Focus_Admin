# 性能监控页面

前端 `performance` 页面对应的是性能监控场景，而不是绩效管理。当前页面已经按“配置 -> 观测 -> 风险处置”三段拆分。

## 页面结构

| 页面 | 路由 | 页面职责 |
| --- | --- | --- |
| 指标配置 | `/performance/config` | 维护指标定义、导入任务、树状筛选和批量操作 |
| 趋势看板 | `/performance/dashboard` | 展示当前值、基线值、波动值和覆盖情况 |
| 风险管理 | `/performance/risk` | 查看风险记录、确认异常和解决问题 |

## 设计思路

### 1. 配置与展示分离

指标定义页不承担趋势展示职责，避免将“配置动作”和“运行观察”混在同一界面里。

### 2. 风险独立为单独页面

异常记录不只是在图表里标红，而是作为独立风险对象进入待处理列表，这样责任人可以持续跟踪。

### 3. 强依赖树状筛选

由于性能指标天然带有 `分类 / 项目 / 模块 / 芯片` 多级上下文，配置页通过树状结构组织比传统扁平表格更容易定位目标指标。

## 主要交互

- 左侧树筛选分类、项目与模块
- 顶部筛选芯片类型和关键字
- 支持导入指标、批量删除和批量字段更新
- 趋势页支持按维度切换和排序
- 风险页支持确认、标记解决和查看详情

## 主要依赖 API

- `GET /api/performance/tree`
- `GET /api/performance/indicators`
- `POST /api/performance/indicators/import`
- `POST /api/performance/data/upload`
- `GET /api/performance/data/trend`
- `POST /api/performance/risks/query`

## 相关文档

- [模块主线说明](/modules/performance)
- [后端技术参考](/backend/apps/performance)
