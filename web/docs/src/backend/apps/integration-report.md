# 集成报告

集成报告模块用于外部系统数据的集成和报告生成。

## 功能概述

- 外部数据源配置
- 数据同步
- 报告生成
- 邮件订阅

## 模块结构

```
apps/integration_report/
├── integration_api.py        # API 接口
├── integration_models.py     # 数据模型
├── integration_schema.py     # Schema 定义
├── integration_service.py    # 业务服务
├── integration_email.py      # 邮件服务
└── integration_mock.py       # Mock 数据
```

## 数据源配置

支持配置多种外部数据源：

- REST API
- 数据库直连
- 文件导入

## API 接口

### 数据源列表

```
GET /api/integration/datasource/list
```

### 触发同步

```
POST /api/integration/sync/{datasource_id}
```

### 生成报告

```
POST /api/integration/report/generate
```
