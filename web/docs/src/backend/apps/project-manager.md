# 项目管理模块

项目管理模块 (`project_manager`) 是系统的核心业务模块，采用模块化设计，以 **Project（项目）** 为核心聚合根，关联多个子领域模块，实现项目全生命周期的管理与数据追踪。

## 架构概览

### 模块关系图

```
                           ┌─────────────────────────────────────────────────────────┐
                           │                    Project (项目)                        │
                           │  - 项目基础信息（名称、编码、领域、类型）                    │
                           │  - 功能开关（里程碑、迭代、代码质量、DTS）                  │
                           │  - 项目经理关联                                          │
                           └─────────────────────────────────────────────────────────┘
                                          │
          ┌───────────────┬───────────────┼───────────────┬───────────────┐
          │               │               │               │               │
          ▼               ▼               ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ Milestone│    │ Iteration│    │CodeModule│    │ DtsTeam  │    │  Report  │
    │  里程碑   │    │   迭代    │    │ 代码模块  │    │ DTS团队  │    │   报告   │
    └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
         │               │               │               │
         │               │               │               │
         ▼               ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ QGConfig │    │Iteration │    │CodeMetric│    │ DtsData  │
    │ QG点配置  │    │  Metric  │    │ 代码指标  │    │ DTS数据  │
    └──────────┘    │ 迭代指标  │    └──────────┘    └──────────┘
         │          └──────────┘
         ▼
    ┌──────────┐
    │ RiskItem │
    │  风险项   │
    └──────────┘
         │
         ▼
    ┌──────────┐
    │ RiskLog  │
    │ 风险日志  │
    └──────────┘
```

### 领域模型关系

| 聚合根 | 关联实体 | 关系类型 | 说明 |
| --- | --- | --- | --- |
| Project | Milestone | 1:1 | 每个项目有一个里程碑配置 |
| Project | Iteration | 1:N | 一个项目可以有多个迭代 |
| Project | CodeModule | 1:N | 一个项目可以有多个代码模块 |
| Project | DtsTeam | 1:N | 一个项目可以有多个DTS团队 |
| Milestone | MilestoneQGConfig | 1:N | 一个里程碑有多个QG点配置 |
| MilestoneQGConfig | MilestoneRiskItem | 1:N | 每个QG点可以有多个风险项 |
| Iteration | IterationMetric | 1:N | 每个迭代有多条指标记录（按日期） |
| CodeModule | CodeMetric | 1:N | 每个模块有多条指标记录（按日期） |
| DtsTeam | DtsData | 1:N | 每个团队有多条DTS数据（按日期） |

## 子模块详解

### 1. Project（项目）

项目是整个模块的聚合根，所有子模块都通过外键关联到项目。

**核心字段：**

```python
class Project(RootModel):
    name = models.CharField(max_length=255, verbose_name="项目名")
    code = models.CharField(max_length=255, unique=True, verbose_name="项目编码")
    domain = models.CharField(max_length=255, verbose_name="项目领域")
    type = models.CharField(max_length=255, verbose_name="项目类型")
    managers = models.ManyToManyField('core.User', verbose_name="项目经理")
    is_closed = models.BooleanField(default=False, verbose_name="是否结项")
    
    # 功能开关 - 控制子模块启用
    enable_milestone = models.BooleanField(default=True)   # 里程碑
    enable_iteration = models.BooleanField(default=True)   # 迭代
    enable_quality = models.BooleanField(default=False)    # 代码质量
    enable_dts = models.BooleanField(default=False)        # DTS问题单
```

**功能开关设计：**

项目通过功能开关控制各子模块的启用状态，实现灵活的项目配置：

- `enable_milestone`: 启用里程碑管理
- `enable_iteration`: 启用迭代数据统计
- `enable_quality`: 启用代码质量分析
- `enable_dts`: 启用DTS问题单追踪

### 2. Milestone（里程碑）

里程碑模块负责项目关键节点（QG点）的管理和风险追踪。

**模型层级：**

```
Milestone (里程碑)
├── MilestoneQGConfig (QG点配置)
│   └── MilestoneRiskItem (风险项)
│       └── MilestoneRiskLog (风险日志)
```

**核心概念：**

- **QG点（Quality Gate）**: 质量门禁点，如 QG1-QG8，代表项目不同阶段的质量检查点
- **目标DI值**: 每个QG点的缺陷密度目标值
- **风险项**: 当DI值超标或存在DTS问题时自动/手动创建的风险记录

**业务流程：**

```
项目配置QG点 → 每日同步DI数据 → 超标自动生成风险项 → 项目经理确认处理 → 记录操作日志
```

### 3. Iteration（迭代）

迭代模块负责敏捷开发迭代周期的管理和指标追踪。

**模型层级：**

```
Iteration (迭代)
└── IterationMetric (迭代指标)
```

**核心字段：**

```python
class Iteration(RootModel):
    project = models.ForeignKey(Project, related_name='iterations')
    name = models.CharField(max_length=255, verbose_name="迭代名称")
    code = models.CharField(max_length=255, verbose_name="迭代编号")
    start_date = models.DateField(verbose_name="开始时间")
    end_date = models.DateField(verbose_name="结束时间")
    is_current = models.BooleanField(default=False, verbose_name="是否当前迭代")
```

**迭代指标：**

`IterationMetric` 记录每日的迭代指标数据：

| 指标 | 说明 |
| --- | --- |
| sr_num / dr_num / ar_num | SR/DR/AR 需求数量 |
| need_break_sr_num | 需要分解的SR数 |
| workload_man_dr_count | 填写了工作量的DR数 |
| i/d/p/c/a_state_*_num | 各状态需求数量 |

### 4. CodeQuality（代码质量）

代码质量模块负责代码模块的质量指标追踪。

**模型层级：**

```
CodeModule (代码模块)
└── CodeMetric (代码指标)
```

**核心指标：**

| 指标 | 说明 |
| --- | --- |
| loc | 代码行数 |
| function_count | 函数个数 |
| dangerous_func_count | 危险函数个数 |
| duplication_rate | 代码重复率 |
| is_clean_code | 是否符合CleanCode标准 |

### 5. DTS（问题单追踪）

DTS模块负责问题单/缺陷的团队级统计和追踪。

**模型层级：**

```
DtsTeam (责任团队) - 支持树形结构
└── DtsData (问题单数据)
```

**核心指标：**

| 指标 | 说明 |
| --- | --- |
| di / target_di | 当前DI值 / 目标DI值 |
| today_in_di / today_out_di | 今日流入/流出DI |
| solve_rate | 问题单解决率 |
| critical_solve_rate | 严重问题单解决率 |
| suggestion_num / minor_num / major_num / fatal_num | 各级别问题单数量 |

### 6. Report（报告）

报告模块负责汇总各子模块数据，生成项目报告。

**主要功能：**

- 项目整体状态汇总
- 迭代进度分析
- 质量趋势图表
- DI值对比分析

## 数据同步机制

### SyncLog（同步日志）

系统通过定时任务从外部数据源同步数据，`SyncLog` 记录每次同步操作：

```python
class SyncLog(RootModel):
    project_id = models.CharField(max_length=64)
    sync_type = models.CharField(choices=[
        ('iteration', '迭代数据'),
        ('dts', 'DTS问题单'),
        ('code_quality', '代码质量'),
        ('milestone', '里程碑'),
        ('project', '项目信息'),
    ])
    status = models.CharField(choices=[
        ('pending', '进行中'),
        ('success', '成功'),
        ('failed', '失败'),
    ])
    result_summary = models.TextField()  # 结果摘要
    detail_log = models.TextField()      # 详细日志
    duration = models.FloatField()       # 耗时(秒)
```

### 同步流程

```
定时任务触发
    │
    ▼
创建 SyncLog (status=pending)
    │
    ▼
调用外部 API 获取数据
    │
    ├── 成功 → 解析并存储数据 → 更新 SyncLog (status=success)
    │
    └── 失败 → 记录错误信息 → 更新 SyncLog (status=failed)
```

## 目录结构

```
apps/project_manager/
├── models/                  # 共享模型导出
│   ├── __init__.py         # 模型汇总导出
│   └── sync_log_model.py   # 同步日志模型
│
├── project/                 # 项目管理
│   ├── project_api.py      # API 接口
│   ├── project_model.py    # 数据模型
│   ├── project_schema.py   # Pydantic Schema
│   └── project_service.py  # 业务服务
│
├── milestone/               # 里程碑管理
│   ├── milestone_api.py
│   ├── milestone_model.py   # Milestone, QGConfig, RiskItem, RiskLog
│   ├── milestone_schema.py
│   └── milestone_service.py
│
├── iteration/               # 迭代管理
│   ├── iteration_api.py
│   ├── iteration_model.py   # Iteration, IterationMetric
│   ├── iteration_schema.py
│   ├── iteration_service.py
│   └── iteration_sync.py    # 迭代数据同步
│
├── code_quality/            # 代码质量
│   ├── code_quality_api.py
│   ├── code_quality_model.py # CodeModule, CodeMetric
│   ├── code_quality_schema.py
│   └── code_quality_service.py
│
├── dts/                     # DTS问题单
│   ├── dts_api.py
│   ├── dts_model.py         # DtsTeam, DtsData
│   ├── dts_schema.py
│   └── dts_service.py
│
├── report/                  # 报告生成
│   ├── report_api.py
│   ├── report_schema.py
│   └── report_service.py
│
├── utils/                   # 工具函数
├── router.py                # 路由汇总
└── sync_log_api.py          # 同步日志 API
```

## API 路由

| 路径 | 模块 | 说明 |
| --- | --- | --- |
| `/api/project-manager/projects` | project | 项目管理 |
| `/api/project-manager/milestones` | milestone | 里程碑管理 |
| `/api/project-manager/iterations` | iteration | 迭代管理 |
| `/api/project-manager/code_quality` | code_quality | 代码质量 |
| `/api/project-manager/dts` | dts | DTS问题单 |
| `/api/project-manager/report` | report | 报告生成 |

## 扩展指南

### 添加新的子模块

1. 在 `project_manager/` 下创建新目录
2. 创建 `*_model.py` 定义模型，关联到 Project
3. 创建 `*_api.py`, `*_schema.py`, `*_service.py`
4. 在 `router.py` 注册路由
5. 如需同步，添加 `SyncLog` 类型枚举

### 添加新指标

1. 在对应的 Metric 模型中添加字段
2. 创建数据库迁移
3. 更新 Schema 和 Service
4. 更新同步逻辑（如适用）
