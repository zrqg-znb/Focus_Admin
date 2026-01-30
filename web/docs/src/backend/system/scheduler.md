# 任务调度

任务调度模块基于 APScheduler 实现，用于管理定时任务和周期任务。

## 功能概述

- 定时任务配置
- 周期任务管理
- 任务执行日志
- 任务暂停/恢复

## 模块结构

```
scheduler/
├── api.py             # API 接口
├── models.py          # 任务模型
├── schema.py          # Schema 定义
├── service.py         # 调度服务
├── tasks.py           # 任务定义
├── router.py          # 路由
└── module/            # 任务模块
    └── sync_tasks.py  # 同步任务
```

## 数据模型

```python
class SchedulerTask(CoreModel):
    """调度任务"""
    name = models.CharField(max_length=128, verbose_name="任务名称")
    job_id = models.CharField(max_length=64, unique=True, verbose_name="任务ID")
    func = models.CharField(max_length=255, verbose_name="执行函数")
    trigger = models.CharField(max_length=32, verbose_name="触发器类型")
    trigger_args = models.JSONField(default=dict, verbose_name="触发器参数")
    status = models.IntegerField(default=1, verbose_name="状态")
    last_run = models.DateTimeField(null=True, verbose_name="上次执行时间")
    next_run = models.DateTimeField(null=True, verbose_name="下次执行时间")
    
    class Meta:
        db_table = 'sys_scheduler_task'
```

## 触发器类型

| 类型 | 说明 | 示例 |
| --- | --- | --- |
| cron | Cron 表达式 | `{"hour": "8", "minute": "0"}` |
| interval | 固定间隔 | `{"seconds": 60}` |
| date | 指定时间 | `{"run_date": "2024-12-31"}` |

## API 接口

### 任务列表

```
GET /api/scheduler/task/list
```

### 新增任务

```
POST /api/scheduler/task/add
```

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| name | string | 是 | 任务名称 |
| func | string | 是 | 执行函数路径 |
| trigger | string | 是 | 触发器类型 |
| trigger_args | object | 是 | 触发器参数 |

### 暂停任务

```
POST /api/scheduler/task/pause/{id}
```

### 恢复任务

```
POST /api/scheduler/task/resume/{id}
```

### 立即执行

```
POST /api/scheduler/task/run/{id}
```

## 使用示例

### 定义任务函数

```python
# scheduler/module/sync_tasks.py

def sync_project_data():
    """同步项目数据"""
    # 任务逻辑
    pass

def daily_report():
    """生成日报"""
    # 任务逻辑
    pass
```

### 配置定时任务

通过 API 或管理界面配置：

```json
{
  "name": "每日数据同步",
  "func": "scheduler.module.sync_tasks:sync_project_data",
  "trigger": "cron",
  "trigger_args": {
    "hour": "2",
    "minute": "0"
  }
}
```

## 启动调度器

```bash
python start_scheduler.py
```

或集成到 Django 启动：

```python
# application/celery.py or wsgi.py
from scheduler.service import start_scheduler
start_scheduler()
```
