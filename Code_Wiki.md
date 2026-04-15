# Focus Admin Code Wiki

本文档是对 Focus Admin 项目的完整代码 Wiki，涵盖了项目的整体架构、主要模块职责、关键类与函数说明、依赖关系以及运行方式。

## 1. 项目整体架构

Focus Admin 是一个基于前后端分离架构的高性能企业级管理系统，支持多端接入、独立部署与独立迭代。

### 1.1 架构设计理念
- **前后端分离**：前端 UI 与后端 API 独立演进，后端专注提供 RESTful API。
- **模块化设计**：遵循高内聚、低耦合原则，按职责划分为 Core（核心）、Apps（业务）、Common（公共）和 Scheduler（调度）四层。
- **RBAC 权限模型**：实现“用户-角色-权限”的细粒度访问控制，后端通过接口装饰器拦截，前端通过动态路由与指令控制 UI。
- **Monorepo 工程化**：前端采用 pnpm workspace + Turborepo 架构，便于跨应用复用核心组件和逻辑。

### 1.2 系统架构全景
```text
┌─────────────────────────────────────────────────────────────┐
│                        前端应用 (Web)                         │
│  web/apps/web-ele (Vue3+Element) | web/apps/web-deepaudit   │
└─────────────────────────────────────────────────────────────┘
                               │
                      HTTP / WebSocket 
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      后端 API (Django)                        │
│   ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────┐  │
│   │    Core    │ │    Apps    │ │   Common   │ │Scheduler│  │
│   │  (基础核心)  │ │  (业务模块)  │ │  (公共组件)  │ │(异步调度)│  │
│   └────────────┘ └────────────┘ └────────────┘ └─────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
             ┌───────┐     ┌───────┐     ┌───────┐
             │ MySQL │     │ Redis │     │外部API │
             └───────┘     └───────┘     └───────┘
```

---

## 2. 主要模块职责

### 2.1 后端模块 (`backend-django/`)
后端采用 Django 5.2 + Django Ninja 框架，分为四大层级：

| 层级 | 目录路径 | 核心职责 | 典型子模块 |
| --- | --- | --- | --- |
| **Core** | `core/` | 提供系统的基础能力，包括权限、认证与组织架构。 | `auth` (认证), `user` (用户), `role` (角色), `permission` (权限), `dept` (部门), `menu` (菜单), 监控模块 |
| **Apps** | `apps/` | 承载具体业务逻辑，模块之间保持低耦合。 | `project_manager` (项目管理), `performance` (绩效), `code_compliance` (代码合规), `code_scan` (代码扫描), `failure_mode` (故障模式) |
| **Common** | `common/` | 抽象公共组件与基类，不依赖任何业务模块。 | `fu_crud` (CRUD操作), `fu_model` (ORM基类), `fu_schema` (数据验证) |
| **Scheduler**| `scheduler/` | 异步任务与定时调度模块。 | `tasks` (任务定义), `service` (调度逻辑) |

### 2.2 前端模块 (`web/`)
前端采用 Monorepo 架构管理：

| 目录路径 | 核心职责 | 说明 |
| --- | --- | --- |
| `apps/web-ele/` | 主后台应用 | 基于 Vue 3 + Element Plus 构建的管理端，`src/views/` 下与后端模块对应。 |
| `apps/web-deepaudit/`| DeepAudit 子应用 | 基于 React 编写的代码扫描独立应用。 |
| `packages/` | 共享包层 | 存放可复用的核心基础包 (`@core`)、图标 (`icons`)、工具函数 (`utils`) 等。 |
| `docs/` | 项目文档库 | 基于 VitePress 构建的系统技术文档。 |

---

## 3. 关键类与函数说明

### 3.1 后端核心基类与方法
为提高开发效率，系统抽象了大量复用类，位于 `backend-django/common/` 目录下：

#### `CoreModel` (位于 `fu_model.py`)
系统的 ORM 基类，所有业务 Model 都应继承该类，它默认提供了以下字段：
- `id`: 主键。
- `description`: 数据描述。
- `creator` / `modifier`: 自动记录数据的创建人和修改人。
- `create_datetime` / `update_datetime`: 自动记录创建和更新时间。

#### CRUD 基础函数 (位于 `fu_crud.py`)
封装了基于 Django ORM 的基础操作，避免重复编写模板代码：
- `create(request, data, model)`: 插入数据，并自动解析 `request.auth` 绑定创建人信息。
- `update(request, id, data, model)`: 根据 ID 更新单条数据。
- `retrieve(request, model, filters)`: 支持复杂条件的查询与分页返回。
- `delete(id, model)` / `batch_delete(ids, model)`: 单条与批量删除操作。

#### API 与 Schema (基于 Django Ninja)
- **Schema 定义**：基于 Pydantic 的 `Schema` 类进行请求与响应的数据校验，例如 `UserSchemaIn`, `UserSchemaOut`。
- **分页包装**：使用 `@paginate(MyPagination)` 装饰器自动对 QuerySet 进行分页处理。

### 3.2 前端架构约定
- **组件划分**：在 `web/apps/web-ele/src/views/` 中，每个业务模块标准结构包括：
  - `index.vue`: 列表展示页。
  - `data.ts`: 表格列(Columns)和表单(Form)的配置定义。
  - `modules/`: 存放当前页面独有的弹窗、抽屉等子组件。
- **API 封装**：`src/api/` 下按业务模块定义请求函数，通过 Axios 拦截器统一处理 Token 注入与错误拦截。

---

## 4. 依赖关系

### 4.1 后端核心依赖 (`requirements.txt`)
- **核心 Web 框架**: `Django` (5.2.x), `django-ninja` (RESTful API 快速开发)
- **数据库驱动**: `pymysql` (MySQL), `psycopg2-binary` (PostgreSQL), `pyodbc` (SQL Server)
- **缓存与实时通信**: `redis`, `django-redis`, `channels` (WebSocket 支持)
- **异步与调度**: `celery`, `django-celery-beat`, `APScheduler`
- **安全与认证**: `PyJWT`, `cryptography`

### 4.2 前端核心依赖 (`package.json`)
- **包管理与工程化**: `pnpm` (10.x), `turbo` (构建缓存与任务编排)
- **核心框架**: `vue` (3.x), `react` (子应用)
- **UI 组件库**: `element-plus`
- **构建与样式**: `vite` (5.x), `tailwindcss`
- **状态与路由**: `pinia`, `vue-router`

---

## 5. 项目运行方式

### 5.1 环境准备
- **后端**: Python >= 3.10, MySQL/PostgreSQL/SQLite, Redis >= 5.0
- **前端**: Node.js >= 20.10.0, pnpm >= 9.12.0

### 5.2 后端启动指南
1. **安装依赖**
   ```bash
   cd backend-django
   python -m venv venv
   source venv/bin/activate  # Windows 下使用 venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **配置环境变量**
   复制 `env` 目录下的示例或直接创建 `.env` 文件，配置数据库连接 (如 `DATABASE_TYPE=MYSQL`, `DATABASE_HOST` 等) 和 Redis 连接信息。
3. **数据库初始化**
   ```bash
   python manage.py makemigrations core scheduler system
   python manage.py migrate
   python manage.py loaddata db_init.json  # 导入初始数据
   ```
4. **启动服务**
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
5. **启动定时调度器**（可选）
   ```bash
   python start_scheduler.py
   ```

### 5.3 前端启动指南
1. **安装依赖**
   ```bash
   cd web
   pnpm install
   ```
2. **环境配置**
   ```bash
   cd apps/web-ele
   cp .env.development .env
   # 按需修改 .env 中的 API 代理地址 (VITE_GLOB_API_URL)
   ```
3. **启动开发服务**
   回到 `web/` 根目录执行：
   ```bash
   pnpm dev
   ```
4. **生产构建**
   ```bash
   pnpm build:ele
   ```

### 5.4 默认登录信息
- **初始化账号**: `superadmin`
- **初始化密码**: `123456`
- **API 接口文档**: 启动后端后访问 `http://localhost:8000/api/docs`
