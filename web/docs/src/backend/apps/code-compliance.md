# 代码合规

代码合规模块（`code_compliance`）用于追踪代码变更的合规性风险，确保代码变更在所有必要的分支上进行了同步。

当前模块是双轨形态：

- 旧风险台账：继续保留 Excel 上传、岗位概览、用户详情和旧分支整改能力。
- 一期基础数据：新增组织、代码库、分支和代码库-分支绑定，为后续联动公司代码库系统做准备。

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
| ComplianceOrganization | ComplianceRepository | 1:N | 组织下直接挂载代码库 |
| ComplianceRepository | ComplianceManagedBranch | M:N | 通过 ComplianceRepositoryBranch 维护绑定 |

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

### ComplianceOrganization（基础数据组织）

```python
class ComplianceOrganization(RootModel):
    group_id = models.CharField(unique=True)  # 公司代码库系统组织ID
    name = models.CharField(max_length=255)
    parent = models.ForeignKey("self", null=True, related_name="children")
    mode = models.CharField(choices=(("CR", "CR"), ("MR", "MR")))
    domain = models.CharField(choices=(("cockpit", "座舱"), ("vehicle", "车控")))
    remark = models.TextField(null=True, blank=True)
```

### ComplianceRepository（基础数据代码库）

```python
class ComplianceRepository(RootModel):
    project_id = models.CharField(unique=True)  # 公司代码库系统代码库ID
    project_name = models.CharField(max_length=255)
    project_url = models.CharField(max_length=1024, blank=True)
    organization = models.ForeignKey(ComplianceOrganization)
    repo_type = models.CharField(max_length=100)  # core 字典 code_compliance_repo_type
    responsibility_groups = models.ManyToManyField("core.PlGroup")
    mode = models.CharField(choices=(("CR", "CR"), ("MR", "MR")))
    domain = models.CharField(choices=(("cockpit", "座舱"), ("vehicle", "车控")))
```

### ComplianceManagedBranch（基础数据分支）

`ComplianceManagedBranch` 是新分支主数据，命名上刻意避开旧风险台账的 `ComplianceBranch`，避免旧功能下线前发生语义冲突。

```python
class ComplianceManagedBranch(RootModel):
    branch_name = models.CharField(max_length=255)
    created_date = models.DateField(null=True, blank=True)
    branch_type = models.CharField(choices=(("development", "开发"), ("trunk", "主干"), ("release", "发布"), ("other", "其他")))
    alias = models.CharField(max_length=255, blank=True)
    purpose = models.TextField(blank=True)
    domain = models.CharField(choices=(("cockpit", "座舱"), ("vehicle", "车控")))
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

### 一期基础数据

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/code-compliance/base/organizations/tree` | 获取组织树，节点包含直接代码库数量 |
| POST/PUT/DELETE | `/api/code-compliance/base/organizations` | 组织新增、编辑、删除 |
| GET/POST | `/api/code-compliance/base/organizations/template`、`/import` | 组织模板下载和 Excel 导入 |
| GET | `/api/code-compliance/base/repositories` | 代码库分页列表，支持组织、关键词、模式、领域、仓库类型过滤 |
| POST/PUT/DELETE | `/api/code-compliance/base/repositories` | 代码库新增、编辑、删除 |
| POST | `/api/code-compliance/base/repositories/batch-bind-branches` | 从代码库侧批量绑定分支，支持 `append` / `replace` |
| GET | `/api/code-compliance/base/branches` | 分支分页列表，输出关联代码库数量 |
| POST/PUT/DELETE | `/api/code-compliance/base/branches` | 分支新增、编辑、删除 |
| POST | `/api/code-compliance/base/branches/batch-bind-repositories` | 从分支侧批量绑定代码库，支持 `append` / `replace` |

## 目录结构

```
apps/code_compliance/
├── api.py             # API 接口定义
├── base_api.py        # 一期基础数据 API
├── base_schemas.py    # 一期基础数据 Schema
├── base_services.py   # 一期基础数据服务
├── models.py          # 数据模型 (Record, Branch)
├── schemas.py         # Pydantic Schema
├── services.py        # 业务服务
├── apps.py            # Django App 配置
├── management/        # 管理命令
│   └── commands/      # 自定义命令（如同步命令）
└── migrations/        # 数据库迁移
```

## 初始化

一期新增命令：

```bash
python manage.py init_code_compliance
```

命令补齐菜单、权限和 `code_compliance_repo_type` 字典。旧风险入口保持可见，后续等新检测能力稳定后再做日落。

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
