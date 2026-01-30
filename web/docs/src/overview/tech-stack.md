# 技术栈

## 后端技术栈

### 核心框架

| 技术 | 版本 | 说明 |
| --- | --- | --- |
| Python | 3.10+ | 编程语言 |
| Django | 4.x | Web 框架 |
| Django Ninja | 1.x | API 框架，高性能异步支持 |
| MySQL | 8.0+ | 关系型数据库 |
| Redis | 6.0+ | 缓存、消息队列 |

### 关键依赖

| 依赖 | 说明 |
| --- | --- |
| PyJWT | JWT Token 生成和验证 |
| APScheduler | 任务调度框架 |
| Celery | 异步任务队列（可选） |
| Pydantic | 数据验证 |

### 后端架构特点

```
backend-django/
├── application/        # Django 应用配置
│   ├── settings.py    # 主配置文件
│   ├── urls.py        # URL 路由
│   └── main.py        # Django Ninja API 入口
│
├── core/              # 核心模块（权限、用户等）
├── apps/              # 业务模块
├── common/            # 公共工具
│   ├── fu_crud.py     # CRUD 基类
│   ├── fu_model.py    # 模型基类
│   ├── fu_schema.py   # Schema 基类
│   └── fu_auth.py     # 认证工具
│
└── scheduler/         # 任务调度模块
```

## 前端技术栈

### 核心框架

| 技术 | 版本 | 说明 |
| --- | --- | --- |
| Vue | 3.4+ | 渐进式 JavaScript 框架 |
| TypeScript | 5.x | JavaScript 超集 |
| Vite | 5.x | 下一代前端构建工具 |
| Element Plus | 2.x | Vue 3 组件库 |
| Pinia | 2.x | Vue 状态管理 |

### 工程化工具

| 工具 | 说明 |
| --- | --- |
| pnpm | 高效的包管理器 |
| Turbo | Monorepo 构建系统 |
| ESLint | 代码质量检查 |
| Prettier | 代码格式化 |
| Stylelint | CSS 代码检查 |

### 前端架构特点

基于 **Vben Admin** 进行二次开发，采用 **Monorepo** 架构：

```
web/
├── apps/
│   └── web-ele/           # Element Plus 版本主应用
│       ├── src/
│       │   ├── api/       # API 请求
│       │   ├── components/# 业务组件
│       │   ├── router/    # 路由配置
│       │   ├── store/     # 状态管理
│       │   └── views/     # 页面视图
│       └── ...
│
├── packages/              # 共享包
│   ├── @core/            # 核心功能包
│   │   ├── base/         # 基础组件
│   │   ├── composables/  # 组合式函数
│   │   └── preferences/  # 偏好设置
│   │
│   ├── effects/          # 副作用包
│   ├── icons/            # 图标包
│   ├── locales/          # 国际化
│   ├── stores/           # 共享状态
│   └── utils/            # 工具函数
│
└── internal/             # 内部工具
    ├── lint-configs/     # Lint 配置
    ├── vite-config/      # Vite 配置
    └── tsconfig/         # TypeScript 配置
```

## 开发环境要求

### 后端

- Python 3.10+
- MySQL 8.0+
- Redis 6.0+
- pip 或 poetry

### 前端

- Node.js 18+
- pnpm 8+

## 推荐开发工具

- **IDE**: VS Code / PyCharm
- **数据库管理**: Navicat / DBeaver
- **API 测试**: Postman / Apifox
- **版本控制**: Git
