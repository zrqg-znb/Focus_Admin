---
title: 平台能力总览
description: Focus 平台底座与通用能力
---

# 平台能力总览

Focus 不只是业务模块堆叠而成。稳定运行这些模块的，是一组持续复用的平台能力。

## 权限与组织基座

- RBAC：用户、角色、权限、菜单、部门、岗位共同构成访问控制体系
- 认证：JWT Token、登录态续期、OAuth 回调与用户信息装载
- 菜单与路由：通过后端菜单配置驱动前端动态菜单和页面可访问性

相关入口：

- [核心模块概览](/backend/core/overview)
- [认证模块](/backend/core/auth)
- [权限管理](/backend/core/permission)

## 运维与可观测能力

- 任务调度：统一管理定时任务与执行状态，适合承载周期型平台作业
- 文件与日志：文件上传下载、登录日志、操作日志构成平台基础支撑
- 系统监控：服务器、Redis、数据库监控与管理能力帮助定位运行风险

相关入口：

- [任务调度](/backend/system/scheduler)
- [文件管理](/backend/system/file-manager)
- [日志管理](/backend/system/log)

## 技术实现模式

- 后端采用 Django + Django Ninja，按 `API / Service / Model` 分层组织
- 前端基于 Vue 3 + TypeScript + VbenAdmin 二开，页面与 API 按子域拆分
- docs 站本身使用 VitePress，模块主线与技术附录并存

继续阅读：

- [系统架构](/overview/architecture)
- [前端概览](/frontend/overview)
- [开发指南](/dev-guide/setup/backend)
