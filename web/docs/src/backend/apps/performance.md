# 绩效管理

绩效管理模块（`performance`）用于性能指标的定义、数据采集、风险监控和统计分析。

## 架构概览

### 模块关系图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PerformanceIndicator (性能指标)                        │
│  - 指标定义（名称、模块、项目、芯片类型）                                    │
│  - 基线配置（基线值、单位、浮动范围、浮动方向）                              │
│  - 责任人关联（owner -> User）                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
     ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
     │ IndicatorData   │   │   RiskRecord    │   │   ImportTask    │
     │    指标数据      │   │    风险记录      │   │    导入任务      │
     └─────────────────┘   └─────────────────┘   └─────────────────┘
             │                     │
             │                     │
             ▼                     ▼
     ┌─────────────────────────────────────────┐
     │              RiskRecord                  │
     │  风险记录 (当数据超出浮动范围时自动生成)    │
     └─────────────────────────────────────────┘
```

### 领域模型关系

| 聚合根 | 关联实体 | 关系类型 | 说明 |
| --- | --- | --- | --- |
| PerformanceIndicator | PerformanceIndicatorData | 1:N | 一个指标有多条数据记录（按日期） |
| PerformanceIndicator | PerformanceRiskRecord | 1:N | 一个指标可能有多条风险记录 |
| PerformanceIndicatorData | PerformanceRiskRecord | 1:1 | 每条异常数据对应一条风险记录 |

## 核心概念

### 指标分类

| 分类 | 代码 | 说明 |
| --- | --- | --- |
| 车控 | vehicle | 车辆控制相关性能指标 |
| 座舱 | cockpit | 智能座舱相关性能指标 |

### 值类型

| 类型 | 代码 | 说明 |
| --- | --- | --- |
| 平均值 | avg | 取测试结果的平均值 |
| 最小值 | min | 取测试结果的最小值 |
| 最大值 | max | 取测试结果的最大值 |

### 浮动方向

| 方向 | 代码 | 说明 |
| --- | --- | --- |
| 越大越好 | up | 如启动速度，值越大表示性能越好 |
| 越小越好 | down | 如响应时间，值越小表示性能越好 |
| 无方向 | none | 无明确优劣方向 |

## 数据模型

### PerformanceIndicator（性能指标）

```python
class PerformanceIndicator(RootModel):
    code = models.CharField(max_length=100, unique=True)          # 业务唯一标识
    category = models.CharField(max_length=20)                     # 分类：vehicle/cockpit
    name = models.CharField(max_length=255)                        # 指标名称
    module = models.CharField(max_length=100)                      # 所属模块
    project = models.CharField(max_length=100)                     # 所属项目
    chip_type = models.CharField(max_length=100)                   # 芯片类型
    
    value_type = models.CharField(max_length=20)                   # 值类型：avg/min/max
    baseline_value = models.FloatField()                           # 基线值
    baseline_unit = models.CharField(max_length=50)                # 单位
    fluctuation_range = models.FloatField()                        # 允许浮动范围
    fluctuation_direction = models.CharField(max_length=20)        # 浮动方向
    
    owner = models.ForeignKey(User, on_delete=models.SET_NULL)     # 责任人
    
    class Meta:
        unique_together = ('category', 'project', 'module', 'chip_type', 'name')
```

### PerformanceIndicatorData（指标数据）

```python
class PerformanceIndicatorData(RootModel):
    indicator = models.ForeignKey(PerformanceIndicator, related_name='data')
    date = models.DateField()                 # 测试日期
    value = models.FloatField()               # 具体测试值
    fluctuation_value = models.FloatField()   # 浮动差值
    
    class Meta:
        unique_together = ('indicator', 'date')
```

### PerformanceRiskRecord（风险记录）

```python
class PerformanceRiskRecord(RootModel):
    STATUS_CHOICES = (
        ('open', '未处理'),
        ('ack', '已确认'),
        ('resolved', '已解决'),
    )
    
    indicator = models.ForeignKey(PerformanceIndicator, related_name='risks')
    data = models.ForeignKey(PerformanceIndicatorData, related_name='risks')
    occur_date = models.DateField()           # 发生日期
    status = models.CharField(max_length=20)  # 状态
    owner = models.ForeignKey(User)           # 责任人
    
    baseline_value = models.FloatField()      # 基线值（快照）
    measured_value = models.FloatField()      # 测量值
    deviation_value = models.FloatField()     # 偏差值
    allowed_range = models.FloatField()       # 允许浮动范围
    message = models.CharField(max_length=500) # 说明
```

### PerformanceIndicatorImportTask（导入任务）

```python
class PerformanceIndicatorImportTask(RootModel):
    STATUS_CHOICES = (
        ('pending', '等待中'),
        ('running', '执行中'),
        ('success', '成功'),
        ('failed', '失败'),
    )
    
    status = models.CharField(max_length=20)
    progress = models.IntegerField(default=0)  # 进度 0-100
    
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    
    total_rows = models.IntegerField()
    processed_rows = models.IntegerField()
    success_count = models.IntegerField()
    error_count = models.IntegerField()
```

## 业务流程

### 指标数据采集流程

```
上传 CSV/Excel 文件
        │
        ▼
┌─────────────────────┐
│  创建 ImportTask    │
│  status = pending   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│    异步处理任务      │
│  status = running   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  逐行解析并存储      │◀─────┐
│  更新 progress      │      │
└─────────┬───────────┘      │
          │                   │ 循环处理
          │                   │
          ├───────────────────┘
          │
          ▼
┌─────────────────────┐
│  完成任务           │
│  status = success   │
└─────────────────────┘
```

### 风险检测流程

```
写入 IndicatorData
        │
        ▼
┌─────────────────────────────────────┐
│      计算浮动差值                    │
│  fluctuation_value = value - baseline│
└─────────────────┬───────────────────┘
                  │
                  ▼
        ┌─────────────────┐
        │  是否超出阈值?   │
        └────────┬────────┘
                 │
         ┌───────┴───────┐
         │ Yes           │ No
         ▼               ▼
┌─────────────────┐   ┌──────────┐
│ 创建 RiskRecord │   │  正常结束 │
│ status = open   │   └──────────┘
└─────────────────┘
```

## API 接口

### 指标管理

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/performance/indicator/list` | 指标列表 |
| POST | `/api/performance/indicator/create` | 创建指标 |
| PUT | `/api/performance/indicator/{id}` | 更新指标 |
| DELETE | `/api/performance/indicator/{id}` | 删除指标 |

### 数据管理

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/performance/data/list` | 数据列表 |
| POST | `/api/performance/data/import` | 数据导入 |
| GET | `/api/performance/data/export` | 数据导出 |

### 风险管理

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/performance/risk/list` | 风险列表 |
| POST | `/api/performance/risk/{id}/ack` | 确认风险 |
| POST | `/api/performance/risk/{id}/resolve` | 解决风险 |

## 目录结构

```
apps/performance/
├── api.py             # API 接口定义
├── models.py          # 数据模型（Indicator, Data, Risk, ImportTask）
├── schemas.py         # Pydantic Schema
├── services.py        # 业务服务
├── apps.py            # Django App 配置
└── migrations/        # 数据库迁移
```

## 扩展指南

### 添加新的指标分类

1. 在 `PerformanceIndicator.CATEGORY_CHOICES` 添加选项
2. 创建数据库迁移
3. 更新前端下拉选项

### 添加新的浮动方向

1. 在 `PerformanceIndicator.DIRECTION_CHOICES` 添加选项
2. 在风险检测逻辑中添加对应判断逻辑
3. 创建数据库迁移
