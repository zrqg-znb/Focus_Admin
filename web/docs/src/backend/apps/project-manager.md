# 项目管理

项目管理模块是系统的核心业务模块，用于管理项目、迭代、里程碑等。

## 功能概述

- 项目管理
- 迭代管理
- 里程碑管理
- 代码质量分析
- DTS 缺陷跟踪

## 模块结构

```
apps/project_manager/
├── project/              # 项目管理
│   ├── api.py
│   ├── models.py
│   ├── schemas.py
│   └── services.py
├── iteration/            # 迭代管理
│   ├── api.py
│   ├── models.py
│   ├── schemas.py
│   └── services.py
├── milestone/            # 里程碑管理
│   ├── api.py
│   ├── models.py
│   └── schemas.py
├── code_quality/         # 代码质量
│   ├── api.py
│   ├── models.py
│   └── services.py
├── dts/                  # DTS 管理
│   ├── api.py
│   └── services.py
└── router.py             # 路由汇总
```

## 数据模型

### 项目

```python
class Project(CoreModel):
    """项目模型"""
    name = models.CharField(max_length=128, verbose_name="项目名称")
    code = models.CharField(max_length=64, unique=True, verbose_name="项目编码")
    status = models.IntegerField(choices=(
        (1, '进行中'),
        (2, '已完成'),
        (3, '已暂停'),
    ), default=1)
    start_date = models.DateField(null=True, verbose_name="开始日期")
    end_date = models.DateField(null=True, verbose_name="结束日期")
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'pm_project'
```

### 迭代

```python
class Iteration(CoreModel):
    """迭代模型"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = models.CharField(max_length=128, verbose_name="迭代名称")
    version = models.CharField(max_length=32, verbose_name="版本号")
    status = models.IntegerField(default=1)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    
    class Meta:
        db_table = 'pm_iteration'
```

## API 接口

### 项目列表

```
GET /api/project-manager/project/list
```

### 项目详情

```
GET /api/project-manager/project/{id}
```

### 迭代列表

```
GET /api/project-manager/iteration/list
```

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| project_id | int | 否 | 项目 ID |

### 代码质量统计

```
GET /api/project-manager/code-quality/statistics
```

返回代码质量相关的统计数据，包括代码行数、复杂度、重复率等指标。

## 外部系统集成

项目管理模块支持与外部系统集成，如：

- GitLab/GitHub 代码仓库
- Jira 项目管理
- SonarQube 代码质量
