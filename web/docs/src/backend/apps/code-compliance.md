# 代码合规

代码合规模块（`code_compliance`）用于追踪代码变更的合规性风险，确保代码变更在所有必要的分支上进行了同步。

## 架构概览

### 模块关系图

```
┌─────────────────────────────────────────────────────────────┐
│                   ComplianceRecord (合规记录)                 │
│  - 关联用户（提交人）                                          │
│  - 变更信息（ChangeId, Title, URL）                           │
│  - 聚合状态（待处理/无风险/已修复）                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ 1:N
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   ComplianceBranch (合规分支)                 │
│  - 分支名称                                                   │
│  - 分支级别状态                                               │
│  - 处理备注                                                   │
└─────────────────────────────────────────────────────────────┘
```

### 领域模型关系

| 聚合根 | 关联实体 | 关系类型 | 说明 |
| --- | --- | --- | --- |
| ComplianceRecord | User | N:1 | 记录关联到提交变更的用户 |
| ComplianceRecord | ComplianceBranch | 1:N | 一条记录可能缺失多个分支的同步 |

## 核心概念

### 状态定义

| 状态值 | 状态名 | 说明 |
| --- | --- | --- |
| 0 | 待处理 | 变更未在目标分支同步，需要处理 |
| 1 | 无风险 | 经评估确认无需同步或不存在风险 |
| 2 | 已修复 | 已完成分支同步 |

### 业务场景

代码合规检查主要解决以下问题：

1. **分支同步遗漏**：开发人员在主分支提交代码后，忘记同步到其他需要的分支
2. **版本一致性**：确保关键修复在所有活跃版本分支都已应用
3. **合规审计**：提供变更追踪和处理记录

## 数据模型

### ComplianceRecord（合规记录）

```python
class ComplianceRecord(RootModel):
    STATUS_CHOICES = (
        (0, '待处理'),  # Unresolved
        (1, '无风险'),  # No Risk
        (2, '已修复'),  # Fixed
    )
    
    user = models.ForeignKey(User, related_name='compliance_records')  # 提交用户
    change_id = models.CharField(max_length=255)                        # 变更ID
    title = models.CharField(max_length=500)                            # 变更标题
    update_time = models.DateTimeField()                                # 更新时间
    url = models.CharField(max_length=500)                              # 变更链接
    
    status = models.IntegerField(choices=STATUS_CHOICES, default=0)     # 聚合状态
    remark = models.TextField()                                          # 备注
```

### ComplianceBranch（合规分支）

```python
class ComplianceBranch(RootModel):
    STATUS_CHOICES = (
        (0, '待处理'),
        (1, '无风险'),
        (2, '已修复'),
    )
    
    record = models.ForeignKey(ComplianceRecord, related_name='branches')
    branch_name = models.CharField(max_length=255)  # 分支名称
    status = models.IntegerField(default=0)          # 分支状态
    remark = models.TextField()                      # 备注
```

## 业务流程

### 合规检查流程

```
外部系统推送变更数据
        │
        ▼
┌─────────────────────────┐
│  解析变更信息            │
│  (ChangeId, 缺失分支)    │
└─────────────┬───────────┘
              │
              ▼
┌─────────────────────────┐
│  创建/更新 Record        │
│  关联 User              │
└─────────────┬───────────┘
              │
              ▼
┌─────────────────────────┐
│  创建 Branch 记录        │
│  (每个缺失分支一条)       │
└─────────────────────────┘
```

### 风险处理流程

```
┌─────────────────────────┐
│     待处理状态           │
│   status = 0            │
└─────────────┬───────────┘
              │
    ┌─────────┴─────────┐
    │                   │
    ▼                   ▼
┌─────────────┐   ┌─────────────┐
│ 确认无风险   │   │  完成修复   │
│ status = 1  │   │ status = 2  │
└─────────────┘   └─────────────┘
```

## API 接口

### 记录管理

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/code-compliance/records` | 获取合规记录列表 |
| GET | `/api/code-compliance/records/{id}` | 获取记录详情 |
| PUT | `/api/code-compliance/records/{id}` | 更新记录状态 |

### 分支管理

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| PUT | `/api/code-compliance/branches/{id}` | 更新分支状态 |
| POST | `/api/code-compliance/branches/{id}/no-risk` | 标记为无风险 |
| POST | `/api/code-compliance/branches/{id}/fixed` | 标记为已修复 |

### 数据同步

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/code-compliance/sync` | 手动触发数据同步 |

## 目录结构

```
apps/code_compliance/
├── api.py             # API 接口定义
├── models.py          # 数据模型 (Record, Branch)
├── schemas.py         # Pydantic Schema
├── services.py        # 业务服务
├── apps.py            # Django App 配置
├── management/        # 管理命令
│   └── commands/      # 自定义命令（如同步命令）
└── migrations/        # 数据库迁移
```

## 数据同步

### 外部数据源

合规数据通过定时任务从外部代码审查系统同步：

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   APScheduler    │      │  Sync Service   │      │  External API   │
│   定时触发        │ ──▶ │   同步服务       │ ──▶ │  代码审查系统    │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │     MySQL       │
                         │  Record/Branch  │
                         └─────────────────┘
```

## 扩展指南

### 添加新的状态

1. 在模型的 `STATUS_CHOICES` 添加新状态
2. 创建数据库迁移
3. 更新 Service 层的状态流转逻辑
4. 更新前端状态展示

### 集成新的代码审查系统

1. 在 `services.py` 添加新的同步方法
2. 实现数据格式转换逻辑
3. 在定时任务中注册新的同步任务
