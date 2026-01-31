# 交付矩阵

交付矩阵模块（`delivery_matrix`）用于管理组织的交付领域、项目群和项目组件的层级结构，提供项目组织视图。

## 架构概览

### 模块关系图

```
┌─────────────────────────────────────────────────────────────┐
│                  DeliveryDomain (交付领域)                    │
│  - 领域名称、编码                                             │
│  - 领域接口人（多对多关联 User）                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ 1:N
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   ProjectGroup (项目群)                       │
│  - 项目群名称                                                 │
│  - 项目群经理（多对多关联 User）                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ 1:N
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 ProjectComponent (项目组件)                   │
│  - 组件名称                                                   │
│  - 项目经理（多对多关联 User）                                 │
│  - 关联项目（可选，关联到 project_manager.Project）            │
└─────────────────────────────────────────────────────────────┘
```

### 树形层级结构

```
DeliveryDomain (交付领域)
├── ProjectGroup (项目群)
│   ├── ProjectComponent (项目组件) ──▶ Project
│   ├── ProjectComponent (项目组件) ──▶ Project
│   └── ...
├── ProjectGroup (项目群)
│   └── ...
└── ...
```

### 领域模型关系

| 聚合根 | 关联实体 | 关系类型 | 说明 |
| --- | --- | --- | --- |
| DeliveryDomain | User | M:N | 领域接口人 |
| DeliveryDomain | ProjectGroup | 1:N | 一个领域包含多个项目群 |
| ProjectGroup | User | M:N | 项目群经理 |
| ProjectGroup | ProjectComponent | 1:N | 一个项目群包含多个组件 |
| ProjectComponent | User | M:N | 项目经理 |
| ProjectComponent | Project | N:1 | 组件可关联到项目管理中的项目 |

### 与项目管理模块的关系

```
┌──────────────────────────┐         ┌──────────────────────────┐
│     delivery_matrix      │         │     project_manager      │
│                          │         │                          │
│  ┌────────────────────┐  │         │  ┌────────────────────┐  │
│  │ ProjectComponent   │──┼────────▶│  │      Project       │  │
│  │                    │  │ linked  │  │                    │  │
│  │ - linked_project   │  │ project │  │  - iterations      │  │
│  └────────────────────┘  │         │  │  - milestones      │  │
│                          │         │  │  - code_quality    │  │
└──────────────────────────┘         └──────────────────────────┘
```

## 核心概念

### 层级说明

| 层级 | 模型 | 说明 | 示例 |
| --- | --- | --- | --- |
| L1 | DeliveryDomain | 交付领域，最高层级组织单元 | 智能驾驶、智能座舱 |
| L2 | ProjectGroup | 项目群，领域下的项目集合 | 高速领航、泊车系统 |
| L3 | ProjectComponent | 项目组件，最小管理单元 | 感知模块、规控模块 |

### 职责分配

| 角色 | 职责 | 关联模型 |
| --- | --- | --- |
| 领域接口人 | 领域整体规划和跨项目群协调 | DeliveryDomain.interface_people |
| 项目群经理 | 项目群内项目协调和资源管理 | ProjectGroup.managers |
| 项目经理 | 具体项目组件的执行和交付 | ProjectComponent.managers |

## 数据模型

### DeliveryDomain（交付领域）

```python
class DeliveryDomain(RootModel):
    name = models.CharField(max_length=255, verbose_name="领域名称")
    code = models.CharField(max_length=255, unique=True, verbose_name="领域编码")
    interface_people = models.ManyToManyField(
        'core.User', 
        related_name='delivery_domains',
        verbose_name="领域接口人"
    )
    remark = models.TextField(blank=True, null=True, verbose_name="备注")
    
    class Meta:
        db_table = 'dm_delivery_domain'
```

### ProjectGroup（项目群）

```python
class ProjectGroup(RootModel):
    name = models.CharField(max_length=255, verbose_name="项目群名称")
    domain = models.ForeignKey(
        DeliveryDomain, 
        on_delete=models.CASCADE,
        related_name='groups',
        verbose_name="所属领域"
    )
    managers = models.ManyToManyField(
        'core.User',
        related_name='delivery_project_groups',
        verbose_name="项目群经理"
    )
    remark = models.TextField(blank=True, null=True, verbose_name="备注")
    
    class Meta:
        db_table = 'dm_project_group'
```

### ProjectComponent（项目组件）

```python
class ProjectComponent(RootModel):
    name = models.CharField(max_length=255, verbose_name="组件名称")
    group = models.ForeignKey(
        ProjectGroup,
        on_delete=models.CASCADE,
        related_name='components',
        verbose_name="所属项目群"
    )
    managers = models.ManyToManyField(
        'core.User',
        related_name='delivery_components',
        verbose_name="项目经理"
    )
    linked_project = models.ForeignKey(
        'project_manager.Project',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='delivery_component',
        verbose_name="关联项目"
    )
    remark = models.TextField(blank=True, null=True, verbose_name="备注")
    
    class Meta:
        db_table = 'dm_project_component'
```

## 业务场景

### 组织架构视图

交付矩阵提供项目的组织架构视图，便于：

1. **层级管理**：按领域 → 项目群 → 组件的层级管理项目
2. **职责明确**：明确各层级的责任人
3. **关联项目数据**：通过 `linked_project` 关联到项目管理模块，获取项目详细数据

### 数据聚合

通过交付矩阵可以实现数据的层级聚合：

```
组件级数据（来自 linked_project）
        │
        ▼ 聚合
项目群级汇总
        │
        ▼ 聚合
领域级汇总
```

## API 接口

### 领域管理

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/delivery-matrix/domains` | 获取领域列表 |
| GET | `/api/delivery-matrix/domains/{id}` | 获取领域详情 |
| POST | `/api/delivery-matrix/domains` | 创建领域 |
| PUT | `/api/delivery-matrix/domains/{id}` | 更新领域 |
| DELETE | `/api/delivery-matrix/domains/{id}` | 删除领域 |

### 项目群管理

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/delivery-matrix/groups` | 获取项目群列表 |
| GET | `/api/delivery-matrix/groups/{id}` | 获取项目群详情 |
| POST | `/api/delivery-matrix/groups` | 创建项目群 |
| PUT | `/api/delivery-matrix/groups/{id}` | 更新项目群 |
| DELETE | `/api/delivery-matrix/groups/{id}` | 删除项目群 |

### 组件管理

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/delivery-matrix/components` | 获取组件列表 |
| GET | `/api/delivery-matrix/components/{id}` | 获取组件详情 |
| POST | `/api/delivery-matrix/components` | 创建组件 |
| PUT | `/api/delivery-matrix/components/{id}` | 更新组件 |
| DELETE | `/api/delivery-matrix/components/{id}` | 删除组件 |
| POST | `/api/delivery-matrix/components/{id}/link` | 关联项目 |

### 树形数据

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/delivery-matrix/tree` | 获取完整树形结构 |

## 目录结构

```
apps/delivery_matrix/
├── api.py             # API 接口定义
├── models.py          # 数据模型 (Domain, Group, Component)
├── schemas.py         # Pydantic Schema
├── services.py        # 业务服务
├── apps.py            # Django App 配置
└── migrations/        # 数据库迁移
```

## 扩展指南

### 添加新的层级

如需添加第四层级（如子组件）：

1. 创建新的模型，关联到 `ProjectComponent`
2. 更新 API 和 Service
3. 更新前端树形组件

### 添加数据聚合功能

1. 在 `services.py` 添加聚合计算逻辑
2. 通过 `linked_project` 获取关联项目的指标数据
3. 按层级进行汇总计算
