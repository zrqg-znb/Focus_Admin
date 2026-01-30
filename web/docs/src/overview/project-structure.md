# 项目结构

## 整体结构

```
Focus_Admin/
├── backend-django/          # 后端代码
├── web/                     # 前端代码 (Monorepo)
└── README.md                # 项目说明
```

## 后端结构

```
backend-django/
├── application/              # Django 应用配置
│   ├── settings.py          # 主配置文件
│   ├── urls.py              # URL 路由总入口
│   ├── main.py              # Django Ninja API 入口
│   ├── celery.py            # Celery 配置
│   └── wsgi.py              # WSGI 配置
│
├── apps/                     # 业务应用模块
│   ├── router.py            # 业务模块路由汇总
│   ├── project_manager/     # 项目管理模块
│   │   ├── project/         # 项目管理
│   │   ├── iteration/       # 迭代管理
│   │   ├── milestone/       # 里程碑
│   │   ├── code_quality/    # 代码质量
│   │   └── dts/             # DTS 管理
│   ├── performance/         # 绩效管理模块
│   ├── code_compliance/     # 代码合规模块
│   ├── delivery_matrix/     # 交付矩阵模块
│   ├── integration_report/  # 集成报告模块
│   └── dashboard/           # 仪表盘模块
│
├── core/                     # 核心功能模块
│   ├── router.py            # 核心模块路由汇总
│   ├── auth/                # 认证模块
│   ├── user/                # 用户管理
│   ├── role/                # 角色管理
│   ├── permission/          # 权限管理
│   ├── menu/                # 菜单管理
│   ├── dept/                # 部门管理
│   ├── dict/                # 字典管理
│   ├── dict_item/           # 字典项管理
│   ├── post/                # 岗位管理
│   ├── file_manager/        # 文件管理
│   ├── operation_log/       # 操作日志
│   ├── login_log/           # 登录日志
│   ├── server_monitor/      # 服务器监控
│   ├── database_manager/    # 数据库管理
│   ├── database_monitor/    # 数据库监控
│   ├── redis_manager/       # Redis 管理
│   ├── redis_monitor/       # Redis 监控
│   ├── oauth/               # OAuth 登录
│   └── websocket/           # WebSocket
│
├── common/                   # 公共模块
│   ├── fu_crud.py           # CRUD 基类
│   ├── fu_model.py          # Model 基类
│   ├── fu_schema.py         # Schema 基类
│   ├── fu_auth.py           # 认证装饰器
│   ├── fu_pagination.py     # 分页工具
│   ├── fu_cache.py          # 缓存工具
│   └── utils/               # 工具函数
│       ├── common.py        # 通用工具
│       ├── excel_utils.py   # Excel 工具
│       └── request_util.py  # 请求工具
│
├── scheduler/                # 任务调度模块
│   ├── service.py           # 调度服务
│   ├── tasks.py             # 任务定义
│   └── models.py            # 任务模型
│
├── env/                      # 环境配置
│   ├── dev_env.py           # 开发环境
│   ├── uat_env.py           # 测试环境
│   └── prd_env.py           # 生产环境
│
├── logs/                     # 日志目录
├── media/                    # 媒体文件目录
├── .env                      # 环境变量
├── manage.py                 # Django 管理脚本
├── requirements.txt          # Python 依赖
└── start_scheduler.py        # 调度器启动脚本
```

## 前端结构

```
web/
├── apps/                     # 应用目录
│   └── web-ele/             # Element Plus 版本应用
│       ├── src/
│       │   ├── adapter/     # 适配器层
│       │   ├── api/         # API 接口定义
│       │   │   ├── core/    # 核心模块 API
│       │   │   └── ...
│       │   ├── components/  # 业务组件
│       │   ├── layouts/     # 布局组件
│       │   ├── locales/     # 国际化文件
│       │   ├── router/      # 路由配置
│       │   │   ├── routes/  # 路由定义
│       │   │   └── index.ts # 路由入口
│       │   ├── store/       # Pinia Store
│       │   ├── utils/       # 工具函数
│       │   ├── views/       # 页面视图
│       │   │   ├── core/    # 核心功能页面
│       │   │   ├── demos/   # 示例页面
│       │   │   └── ...
│       │   ├── app.vue      # 根组件
│       │   ├── main.ts      # 应用入口
│       │   └── bootstrap.ts # 启动配置
│       ├── .env.*           # 环境配置
│       ├── index.html       # HTML 入口
│       └── vite.config.mts  # Vite 配置
│
├── packages/                 # 共享包
│   ├── @core/               # 核心功能包
│   │   ├── base/            # 基础组件
│   │   ├── composables/     # 组合式函数
│   │   ├── preferences/     # 偏好设置
│   │   └── shadcn-ui/       # UI 组件
│   ├── constants/           # 常量定义
│   ├── effects/             # 副作用
│   │   ├── access/          # 权限控制
│   │   ├── layouts/         # 布局效果
│   │   └── request/         # 请求封装
│   ├── icons/               # 图标
│   ├── locales/             # 国际化
│   ├── preferences/         # 偏好配置
│   ├── stores/              # 共享状态
│   │   └── src/modules/     # Store 模块
│   ├── styles/              # 样式
│   ├── types/               # 类型定义
│   └── utils/               # 工具函数
│
├── internal/                 # 内部工具
│   ├── lint-configs/        # Lint 配置
│   │   ├── eslint-config/   # ESLint
│   │   ├── prettier-config/ # Prettier
│   │   └── stylelint-config/# Stylelint
│   ├── node-utils/          # Node 工具
│   ├── tailwind-config/     # Tailwind 配置
│   ├── tsconfig/            # TypeScript 配置
│   └── vite-config/         # Vite 配置
│
├── docs/                     # 项目文档
│   ├── src/                 # 文档源文件
│   └── .vitepress/          # VitePress 配置
│
├── scripts/                  # 脚本
│   ├── deploy/              # 部署脚本
│   └── vsh/                 # VSH 脚本
│
├── package.json             # 根 package.json
├── pnpm-workspace.yaml      # pnpm 工作区配置
├── turbo.json               # Turbo 配置
└── eslint.config.mjs        # ESLint 配置
```

## 模块命名规范

### 后端模块

每个功能模块通常包含以下文件：

```
module/
├── api.py          # API 接口定义
├── models.py       # 数据模型
├── schemas.py      # Pydantic Schema
├── services.py     # 业务服务（可选）
└── apps.py         # Django App 配置
```

### 前端模块

页面模块结构：

```
views/module/
├── index.vue       # 列表页面
├── detail.vue      # 详情页面（可选）
├── components/     # 局部组件
└── api.ts          # API 定义
```
