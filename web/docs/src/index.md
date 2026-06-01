---
layout: home

hero:
  name: "Focus Project Docs"
  text: "Focus 平台文档重构版"
  tagline: "让 Focus 的模块设计、实现逻辑和真实接口，像一张系统蓝图一样被读懂。"
  actions:
    - theme: brand
      text: 查看产品模块
      link: /modules/index
    - theme: alt
      text: 阅读系统架构
      link: /overview/architecture
    - theme: alt
      text: 查看平台能力
      link: /platform/capabilities
  image:
    src: /showcase/deepaudit-home.png
    alt: Focus Admin

features:
  - title: 产品地图
    details: 以项目、需求、性能、质量、故障和智能审计为核心业务域，强调跨模块协作，而不是孤立功能页。
  - title: 工程说明书
    details: 每个模块页都同时解释模块定位、对象结构、关键流程、前后端实现路径和核心 API。
  - title: 技术附录
    details: 保留 backend / frontend 附录作为深入参考，但不再让实现目录决定你的理解顺序。
---

<div class="vp-doc">
  <h2 style="text-align: center; margin-top: 60px; margin-bottom: 20px;">Product Modules</h2>
  <p style="text-align: center; color: var(--vp-c-text-2); margin-bottom: 40px;">
    先看模块设计，再看代码实现。<br>
    每个模块页都会明确模块职责、设计目标、关键对象、数据流、前后端结构、核心 API 和典型场景。
  </p>
  <FocusModuleGrid />

  <h2 style="text-align: center; margin-top: 80px; margin-bottom: 20px;">Architecture Brief</h2>
  <p style="text-align: center; color: var(--vp-c-text-2); margin-bottom: 40px;">
    Focus 不是模块拼盘，而是一套有分层边界的协作系统。
  </p>

  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 60px;">
    <div style="padding: 24px; border-radius: 12px; background: var(--vp-c-bg-soft);">
      <h3 style="margin-top: 0; margin-bottom: 12px; font-size: 1.1rem;">1. 产品模块层</h3>
      <p style="margin: 0; color: var(--vp-c-text-2); font-size: 0.95rem;">项目管理、性能监控、故障模式等模块面向不同角色承接实际业务协作。</p>
    </div>
    <div style="padding: 24px; border-radius: 12px; background: var(--vp-c-bg-soft);">
      <h3 style="margin-top: 0; margin-bottom: 12px; font-size: 1.1rem;">2. 平台能力层</h3>
      <p style="margin: 0; color: var(--vp-c-text-2); font-size: 0.95rem;">RBAC、监控、调度、文件、日志与消息等底座保证业务模块可以持续运转和治理。</p>
    </div>
    <div style="padding: 24px; border-radius: 12px; background: var(--vp-c-bg-soft);">
      <h3 style="margin-top: 0; margin-bottom: 12px; font-size: 1.1rem;">3. 技术实现层</h3>
      <p style="margin: 0; color: var(--vp-c-text-2); font-size: 0.95rem;">Django + Ninja 负责统一 API 出口，Vue 3 + VbenAdmin 二开前端负责复杂工作台和业务视图。</p>
    </div>
  </div>

  <h2 style="text-align: center; margin-top: 80px; margin-bottom: 20px;">Real Screens</h2>
  <p style="text-align: center; color: var(--vp-c-text-2); margin-bottom: 40px;">
    文档优先展示真实项目界面，而不是装饰性示意图。
  </p>

  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; margin-bottom: 60px;">
    <div style="border-radius: 12px; overflow: hidden; border: 1px solid var(--vp-c-border);">
      <img src="/showcase/deepaudit-home.png" alt="DeepAudit 首页" style="width: 100%; display: block;" />
      <div style="padding: 16px; background: var(--vp-c-bg-soft);">
        <p style="margin: 0; font-size: 0.9rem; color: var(--vp-c-text-2);">DeepAudit 首页入口，突出任务入口和分析工作台。</p>
      </div>
    </div>
    <div style="border-radius: 12px; overflow: hidden; border: 1px solid var(--vp-c-border);">
      <img src="/showcase/deepaudit-report.png" alt="DeepAudit 审计报告" style="width: 100%; display: block;" />
      <div style="padding: 16px; background: var(--vp-c-bg-soft);">
        <p style="margin: 0; font-size: 0.9rem; color: var(--vp-c-text-2);">结构化审计报告展示风险、上下文和修复建议。</p>
      </div>
    </div>
  </div>
</div>
