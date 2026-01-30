---
name: crud_template
description: 编写前后端的 crud 接口
---

### 技术栈要求

#### 后端开发技能
- **核心框架**：熟练使用 Django  框架开发
- **API 工具**：掌握 Django Ninja 实现高性能 API 路由与 OpenAPI 文档生成
- **数据库**：精通 MySQL 8.0 特性（窗口函数/CTE）及 Django ORM 优化技巧
- **分层架构**：
  - Models 层：实现符合业务逻辑的数据关系与约束
  - Schemas 层：使用 Pydantic 进行严格的数据验证与序列化
  - Service 层：封装核心业务逻辑与事务管理
  - API 层：处理请求/响应与权限控制

#### 前端开发技能
- **Vue3 生态**：
  - 熟练使用 Composition API 和 `<script setup>` 语法
  - 掌握 VbenAdmin 5.x 的布局系统与权限集成方案
- **组件规范**：
  - 标准化 VXETable 高级功能（服务端分页/列动态渲染）
  - 严格遵循组件目录结构：
    ```
    /views/对应业务模块
    ├── data.ts    # 类型定义与API配置
    ├── index.vue  # 主视图逻辑
    └── components # 子组件集合
    