# 前端概览

Focus Admin 前端基于 Vben Admin 进行二次开发，采用 Vue 3 + TypeScript + Element Plus 技术栈。

## 技术栈

| 技术 | 版本 | 说明 |
| --- | --- | --- |
| Vue | 3.4+ | 渐进式 JavaScript 框架 |
| TypeScript | 5.x | JavaScript 超集 |
| Vite | 5.x | 下一代前端构建工具 |
| Element Plus | 2.x | Vue 3 组件库 |
| Pinia | 2.x | Vue 状态管理 |
| Vue Router | 4.x | 路由管理 |
| Axios | 1.x | HTTP 请求库 |
| Tailwind CSS | 3.x | 原子化 CSS 框架 |

## 项目特点

### 1. Monorepo 架构

采用 pnpm + Turbo 的 Monorepo 架构，支持多应用开发和代码复用。

### 2. 组件化开发

- 基础组件来自 Element Plus
- 业务组件按模块组织
- 公共组件通过 packages 共享

### 3. 状态管理

使用 Pinia 进行状态管理：

- `stores/modules/user.ts` - 用户状态
- `stores/modules/permission.ts` - 权限状态
- `stores/modules/app.ts` - 应用配置

### 4. 请求封装

统一的请求封装，支持：

- Token 自动携带
- 请求/响应拦截
- 错误统一处理
- 请求取消

## 开发流程

### 启动开发服务器

```bash
cd web
pnpm install
pnpm dev:ele
```

### 构建生产版本

```bash
pnpm build:ele
```

### 代码检查

```bash
pnpm lint
pnpm lint:fix
```

## 相关文档

- [目录结构](/frontend/project-structure)
- [路由管理](/frontend/router)
- [状态管理](/frontend/store)
- [组件开发](/frontend/components/overview)
