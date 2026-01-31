# 集成报告

集成报告模块（`integration_report`）用于生成每日集成报告，汇总项目的代码检测、构建检测等指标数据，并支持邮件订阅推送。

## 架构概览

### 模块关系图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  IntegrationProjectConfig (项目配置)                      │
│  - 关联项目（Project）                                                    │
│  - 配置名称（邮件显示名）                                                  │
│  - 外部任务ID（代码检测、二进制范围、构建检测、编译检测）                     │
└─────────────────────────────────────────────────────────────────────────┘
          │                        │                        │
          │ 1:N                    │ 1:N                    │ 1:N
          ▼                        ▼                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  MetricValue    │     │  Subscription   │     │  EmailDelivery  │
│   指标值         │     │   邮件订阅       │     │   邮件投递       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
          │
          │ N:1
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  IntegrationMetricDefinition (指标定义)                   │
│  - 分组（code/dt）                                                       │
│  - 指标名称、Key、单位                                                    │
│  - 预警规则（操作符、阈值）                                                │
└─────────────────────────────────────────────────────────────────────────┘
```

### 领域模型关系

| 聚合根 | 关联实体 | 关系类型 | 说明 |
| --- | --- | --- | --- |
| IntegrationProjectConfig | Project | N:1 | 配置关联到项目 |
| IntegrationProjectConfig | User | M:N | 项目负责人 |
| IntegrationProjectConfig | IntegrationProjectMetricValue | 1:N | 每日指标数据 |
| IntegrationProjectConfig | IntegrationEmailSubscription | 1:N | 邮件订阅 |
| IntegrationMetricDefinition | IntegrationProjectMetricValue | 1:N | 指标定义关联值 |
| IntegrationEmailSubscription | User | N:1 | 订阅人 |

## 核心概念

### 指标分组

| 分组 | 代码 | 说明 |
| --- | --- | --- |
| 代码检测 | code | 代码静态检查相关指标 |
| DT检测 | dt | 动态测试相关指标 |

### 值类型

| 类型 | 代码 | 说明 |
| --- | --- | --- |
| 数值 | number | 数字类型，支持预警规则 |
| 文本 | string | 文本类型 |
| 百分比 | percent | 百分比类型 |

### 预警规则

通过 `warn_operator` 和 `warn_value` 定义预警规则：

| 操作符 | 说明 | 示例 |
| --- | --- | --- |
| `>` | 大于 | 值 > 100 时预警 |
| `<` | 小于 | 值 < 0 时预警 |
| `>=` | 大于等于 | 值 >= 90 时预警 |
| `<=` | 小于等于 | 值 <= 10 时预警 |
| `!=` | 不等于 | 值 != 0 时预警 |
| `==` | 等于 | 值 == 0 时预警 |

### 邮件投递状态

| 状态 | 代码 | 说明 |
| --- | --- | --- |
| 待发送 | pending | 邮件已创建，等待发送 |
| 已发送 | sent | 邮件发送成功 |
| 失败 | failed | 邮件发送失败 |

## 数据模型

### IntegrationProjectConfig（项目配置）

```python
class IntegrationProjectConfig(RootModel):
    project = models.ForeignKey(Project, related_name="integration_configs")
    name = models.CharField(max_length=128)                # 配置名称
    managers = models.ManyToManyField("core.User")         # 项目负责人
    enabled = models.BooleanField(default=True)            # 是否启用
    
    # 外部任务ID配置
    code_check_task_id = models.CharField(max_length=128)      # 代码检测任务
    bin_scope_task_id = models.CharField(max_length=128)       # 二进制范围任务
    build_check_task_id = models.CharField(max_length=128)     # 构建检测任务
    compile_check_task_id = models.CharField(max_length=128)   # 编译检测任务
    dt_project_id = models.CharField(max_length=128)           # DT项目ID
```

### IntegrationMetricDefinition（指标定义）

```python
class IntegrationMetricDefinition(RootModel):
    group = models.CharField(max_length=64)                # 分组：code | dt
    key = models.CharField(max_length=128, unique=True)    # 指标Key
    name = models.CharField(max_length=128)                # 指标名称
    value_type = models.CharField(max_length=32)           # 值类型
    unit = models.CharField(max_length=16)                 # 单位
    
    warn_operator = models.CharField(max_length=8)         # 预警操作符
    warn_value = models.FloatField(null=True)              # 预警阈值
    enabled = models.BooleanField(default=True)
```

### IntegrationProjectMetricValue（指标值）

```python
class IntegrationProjectMetricValue(RootModel):
    config = models.ForeignKey(IntegrationProjectConfig, related_name="metric_values")
    record_date = models.DateField()                       # 记录日期
    metric = models.ForeignKey(IntegrationMetricDefinition, related_name="values")
    value_number = models.FloatField(null=True)            # 数值
    value_text = models.CharField(max_length=255)          # 文本值
    detail_url = models.CharField(max_length=512)          # 详情URL
    
    class Meta:
        unique_together = ("config", "record_date", "metric")
```

### IntegrationEmailSubscription（邮件订阅）

```python
class IntegrationEmailSubscription(RootModel):
    user = models.ForeignKey("core.User", related_name="integration_subscriptions")
    config = models.ForeignKey(IntegrationProjectConfig, related_name="subscriptions")
    enabled = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ("user", "config")
```

### IntegrationEmailDelivery（邮件投递）

```python
class IntegrationEmailDelivery(RootModel):
    record_date = models.DateField()                       # 数据日期
    user = models.ForeignKey("core.User", related_name="integration_deliveries")
    to_email = models.EmailField()                         # 收件邮箱
    subject = models.CharField(max_length=255)             # 邮件主题
    status = models.CharField(max_length=16)               # 状态
    error_message = models.TextField()                     # 错误信息
```

## 业务流程

### 数据采集流程

```
定时任务触发（每日）
        │
        ▼
┌─────────────────────────┐
│  获取启用的项目配置      │
└─────────────┬───────────┘
              │
              ▼
┌─────────────────────────┐
│  根据任务ID调用外部API   │
│  获取各项检测数据        │
└─────────────┬───────────┘
              │
              ▼
┌─────────────────────────┐
│  解析数据并存储          │
│  IntegrationProjectMetric│
│  Value                  │
└─────────────────────────┘
```

### 邮件发送流程

```
数据采集完成
        │
        ▼
┌─────────────────────────┐
│  获取订阅该配置的用户    │
└─────────────┬───────────┘
              │
              ▼
┌─────────────────────────┐
│  生成邮件内容            │
│  - 汇总指标数据          │
│  - 标记预警项            │
└─────────────┬───────────┘
              │
              ▼
┌─────────────────────────┐
│  创建 EmailDelivery     │
│  status = pending       │
└─────────────┬───────────┘
              │
              ▼
┌─────────────────────────┐
│  调用邮件服务发送        │
└─────────────┬───────────┘
              │
    ┌─────────┴─────────┐
    │ Success           │ Failed
    ▼                   ▼
┌─────────────┐   ┌─────────────┐
│ status=sent │   │status=failed│
└─────────────┘   │记录错误信息  │
                  └─────────────┘
```

## API 接口

### 项目配置

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/integration-report/configs` | 获取配置列表 |
| GET | `/api/integration-report/configs/{id}` | 获取配置详情 |
| POST | `/api/integration-report/configs` | 创建配置 |
| PUT | `/api/integration-report/configs/{id}` | 更新配置 |
| DELETE | `/api/integration-report/configs/{id}` | 删除配置 |

### 指标定义

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/integration-report/metrics` | 获取指标定义列表 |
| POST | `/api/integration-report/metrics` | 创建指标定义 |
| PUT | `/api/integration-report/metrics/{id}` | 更新指标定义 |

### 指标数据

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/integration-report/values` | 获取指标数据 |
| POST | `/api/integration-report/sync` | 手动触发数据同步 |

### 邮件订阅

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/integration-report/subscriptions` | 获取订阅列表 |
| POST | `/api/integration-report/subscriptions` | 创建订阅 |
| DELETE | `/api/integration-report/subscriptions/{id}` | 取消订阅 |

## 目录结构

```
apps/integration_report/
├── integration_api.py        # API 接口定义
├── integration_models.py     # 数据模型
├── integration_schema.py     # Pydantic Schema
├── integration_service.py    # 业务服务
├── integration_email.py      # 邮件发送服务
├── integration_mock.py       # Mock 数据（开发用）
├── apps.py                   # Django App 配置
└── migrations/               # 数据库迁移
```

## 扩展指南

### 添加新的指标分组

1. 创建新的指标定义记录，指定 `group`
2. 在数据采集服务中添加对应的获取逻辑
3. 更新邮件模板展示

### 集成新的外部检测系统

1. 在 `IntegrationProjectConfig` 添加新的任务ID字段
2. 创建数据库迁移
3. 在 `integration_service.py` 添加数据获取逻辑
4. 定义对应的指标定义

### 自定义邮件模板

1. 修改 `integration_email.py` 中的邮件生成逻辑
2. 支持 HTML 模板渲染
3. 可配置化预警样式
