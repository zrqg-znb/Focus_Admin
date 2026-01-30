---
# https://vitepress.dev/reference/default-theme-home-page
layout: home
sidebar: false

hero:
  name: Focus Admin
  text: 企业级全栈管理系统
  tagline: 基于 Django + Vue 3 + Element Plus 的现代化管理平台
  image:
    src: /logo.svg
    alt: Focus Admin
  actions:
    - theme: brand
      text: 快速开始 ->
      link: /overview/quick-start
    - theme: alt
      text: 项目介绍
      link: /overview/introduction
    - theme: alt
      text: 在 GitHub 查看
      link: https://github.com/jiangzhikj/zq-platform

features:
  - icon: 🚀
    title: 前后端分离架构
    details: 采用 Django + Vue 3 前后端分离架构，后端使用 Django Ninja 构建高性能 API，前端基于 Vben Admin 二次开发。
    link: /overview/architecture
    linkText: 查看架构
  - icon: 🎯
    title: 项目管理模块
    details: 完整的项目管理功能，包括项目、迭代、里程碑、代码质量分析等，支持与外部系统集成。
    link: /backend/apps/project-manager
    linkText: 了解更多
  - icon: 📊
    title: 绩效管理
    details: 支持绩效指标定义、数据导入、统计分析等功能，帮助团队进行绩效评估和管理。
    link: /backend/apps/performance
    linkText: 查看详情
  - icon: 🔐
    title: 完善的权限管理
    details: 基于 RBAC 的权限管理系统，支持用户、角色、权限、菜单、部门等完整的权限控制体系。
    link: /backend/core/permission
    linkText: 权限文档
  - icon: ⏰
    title: 任务调度
    details: 内置任务调度模块，支持定时任务、周期任务的配置和管理，基于 APScheduler 实现。
    link: /backend/system/scheduler
    linkText: 调度文档
  - title: Django
    icon:
      src: /logos/django.svg
    details: 后端基于 Django 4.x + Django Ninja 构建，提供高性能的 RESTful API 服务。
    link: /backend/core/overview
    linkText: 后端文档
  - title: Vue 3
    icon:
      src: /logos/vue.svg
    details: 前端采用 Vue 3 + TypeScript + Element Plus，基于 Vben Admin 框架进行二次开发。
    link: /frontend/overview
    linkText: 前端文档
  - title: Monorepo
    icon:
      src: /logos/turborepo.svg
    details: 前端采用 pnpm + Monorepo + Turbo 工程管理模式，支持多应用开发和共享组件库。
    link: /frontend/project-structure
    linkText: 工程结构
---

## 项目模块

<div class="module-grid">

### 核心模块 (Core)
- **认证模块** - 用户登录、JWT Token 管理
- **用户管理** - 用户增删改查、状态管理
- **角色管理** - 角色定义、权限分配
- **权限管理** - 细粒度权限控制
- **菜单管理** - 动态菜单配置
- **部门管理** - 组织架构管理
- **字典管理** - 数据字典维护

### 业务模块 (Apps)
- **项目管理** - 项目、迭代、里程碑管理
- **绩效管理** - 绩效指标、统计分析
- **代码合规** - 代码规范检查
- **交付矩阵** - 交付进度管理
- **集成报告** - 外部系统数据集成

### 系统功能
- **任务调度** - 定时任务管理
- **文件管理** - 文件上传下载
- **日志管理** - 操作日志、登录日志
- **系统监控** - 服务器状态监控

</div>
