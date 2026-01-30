# 绩效管理

绩效管理模块用于团队绩效的指标管理和统计分析。

## 功能概述

- 绩效指标定义
- 绩效数据导入
- 绩效统计分析
- 绩效报表导出

## 模块结构

```
apps/performance/
├── api.py             # API 接口
├── models.py          # 数据模型
├── schemas.py         # Schema 定义
├── services.py        # 业务服务
└── migrations/        # 数据库迁移
```

## 数据模型

```python
class PerformanceIndicator(CoreModel):
    """绩效指标"""
    name = models.CharField(max_length=128, verbose_name="指标名称")
    code = models.CharField(max_length=64, unique=True, verbose_name="指标编码")
    category = models.CharField(max_length=64, verbose_name="指标分类")
    unit = models.CharField(max_length=32, blank=True, verbose_name="单位")
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    
    class Meta:
        db_table = 'perf_indicator'

class PerformanceRecord(CoreModel):
    """绩效记录"""
    indicator = models.ForeignKey(PerformanceIndicator, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    period = models.CharField(max_length=32, verbose_name="统计周期")
    value = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'perf_record'
```

## API 接口

### 指标列表

```
GET /api/performance/indicator/list
```

### 数据导入

```
POST /api/performance/import
```

支持 CSV/Excel 格式的绩效数据批量导入。

### 统计分析

```
GET /api/performance/statistics
```

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| period | string | 是 | 统计周期 (如: 2024-01) |
| dept_id | int | 否 | 部门 ID |

**响应示例：**

```json
{
  "code": 200,
  "data": {
    "summary": {
      "total_score": 85.5,
      "rank": 3
    },
    "details": [
      {
        "indicator_name": "代码提交量",
        "value": 120,
        "score": 90
      }
    ]
  }
}
```
