<script lang="ts" setup>
import { focusModules, getFocusModulesByGroup } from '../../src/data/modules';

const commandModules = getFocusModulesByGroup('command');
const qualityModules = getFocusModulesByGroup('quality');
const deliveryModules = getFocusModulesByGroup('delivery');
const intelligenceModules = getFocusModulesByGroup('intelligence');

const metrics = [
  { label: '核心模块', value: `${focusModules.length}` },
  { label: '文档主线', value: '模块优先' },
  { label: '适用人群', value: '研发 / 测试 / 管理' },
  { label: '内容形态', value: '设计 + 实现 + API' },
];

const platformCapabilities = [
  {
    description: '用户、角色、权限、菜单、部门、岗位等模块提供完整 RBAC 基座。',
    link: '/backend/core/overview',
    title: '认证与权限平台',
  },
  {
    description: '服务器、Redis、数据库监控以及日志、文件、消息等能力组成平台底座。',
    link: '/platform/capabilities',
    title: '系统能力与运维底座',
  },
  {
    description: '前端采用 VbenAdmin 二开与 Monorepo 结构，后端使用 Django + Ninja 分层设计。',
    link: '/overview/architecture',
    title: '前后端分离架构',
  },
];

const narrativePanels = [
  {
    body: '以项目、需求、性能、质量、故障和智能审计为核心业务域，强调跨模块协作，而不是孤立功能页。',
    title: '产品地图',
  },
  {
    body: '每个模块页都同时解释模块定位、对象结构、关键流程、前后端实现路径和核心 API。',
    title: '工程说明书',
  },
  {
    body: '保留 backend / frontend 附录作为深入参考，但不再让实现目录决定你的理解顺序。',
    title: '技术附录',
  },
];
</script>

<template>
  <div class="focus-home">
    <section class="focus-home-hero">
      <div class="focus-home-hero__content">
        <p class="focus-kicker">Focus Project Docs</p>
        <p class="focus-home-hero__eyebrow">Focus 平台文档重构版</p>
        <h1>让 Focus 的模块设计、实现逻辑和真实接口，像一张系统蓝图一样被读懂。</h1>
        <p class="focus-home-hero__summary">
          这个文档站先解释 Focus 的业务模块如何分工、如何协作、由哪些对象和流程组成，
          再继续下钻到后端 API、前端页面和技术附录。你看到的不只是功能列表，而是项目本身的设计结构。
        </p>
        <div class="focus-home-hero__actions">
          <a class="focus-button is-primary" href="/modules/index">查看产品模块</a>
          <a class="focus-button" href="/overview/architecture">阅读系统架构</a>
          <a class="focus-button" href="/platform/capabilities">查看平台能力</a>
        </div>

        <div class="focus-home-hero__narrative">
          <article
            v-for="panel in narrativePanels"
            :key="panel.title"
            class="focus-home-hero__narrative-card"
          >
            <span>{{ panel.title }}</span>
            <p>{{ panel.body }}</p>
          </article>
        </div>
      </div>

      <div class="focus-home-hero__panel">
        <div class="focus-home-hero__poster">
          <div class="focus-home-hero__poster-grid">
            <span>项目管理</span>
            <span>性能监控</span>
            <span>需求中心</span>
            <span>代码合规</span>
            <span>代码扫描</span>
            <span>交付矩阵</span>
            <span>集成报告</span>
            <span>自动化测试</span>
            <span>故障模式</span>
            <span>DeepAudit</span>
          </div>
          <div class="focus-home-hero__poster-note">
            <strong>MODULE-DRIVEN</strong>
            <span>把系统理解顺序从“代码目录”切换成“业务模块协同图”。</span>
          </div>
        </div>

        <div class="focus-home-hero__metrics">
          <div v-for="metric in metrics" :key="metric.label" class="focus-home-hero__metric">
            <strong>{{ metric.value }}</strong>
            <span>{{ metric.label }}</span>
          </div>
        </div>

        <div class="focus-home-hero__map">
          <div>
            <span>统筹与协同</span>
            <strong>{{ commandModules.map((item) => item.title).join(' / ') }}</strong>
          </div>
          <div>
            <span>质量与性能</span>
            <strong>{{ qualityModules.map((item) => item.title).join(' / ') }}</strong>
          </div>
          <div>
            <span>交付与验证</span>
            <strong>{{ deliveryModules.map((item) => item.title).join(' / ') }}</strong>
          </div>
          <div>
            <span>智能审计</span>
            <strong>{{ intelligenceModules.map((item) => item.title).join(' / ') }}</strong>
          </div>
        </div>
      </div>
    </section>

    <section class="focus-home-section">
      <div class="focus-section-heading">
        <p class="focus-kicker">Product Modules</p>
        <h2>先看模块设计，再看代码实现。</h2>
        <p>
          每个模块页都会明确模块职责、设计目标、关键对象、数据流、前后端结构、核心 API 和典型场景。
        </p>
      </div>
      <FocusModuleGrid />
    </section>

    <section class="focus-home-section focus-home-section--split">
      <div>
        <div class="focus-section-heading">
          <p class="focus-kicker">Architecture Brief</p>
          <h2>Focus 不是模块拼盘，而是一套有分层边界的协作系统。</h2>
        </div>
        <ol class="focus-stage-list">
          <li>
            <strong>产品模块层</strong>
            <span>项目管理、需求中心、性能监控、故障模式等模块面向不同角色承接实际业务协作。</span>
          </li>
          <li>
            <strong>平台能力层</strong>
            <span>RBAC、监控、调度、文件、日志与消息等底座保证业务模块可以持续运转和治理。</span>
          </li>
          <li>
            <strong>技术实现层</strong>
            <span>Django + Ninja 负责统一 API 出口，Vue 3 + VbenAdmin 二开前端负责复杂工作台和业务视图。</span>
          </li>
        </ol>
      </div>

      <div class="focus-capability-list">
        <a
          v-for="capability in platformCapabilities"
          :key="capability.title"
          :href="capability.link"
          class="focus-capability-card"
        >
          <span>{{ capability.title }}</span>
          <p>{{ capability.description }}</p>
        </a>
      </div>
    </section>

    <section class="focus-home-section focus-home-section--media">
      <div class="focus-section-heading">
        <p class="focus-kicker">Real Screens</p>
        <h2>文档优先展示真实项目界面，而不是装饰性示意图。</h2>
        <p>
          下面两张图来自现有 DeepAudit 应用。新的首页视觉会继续沿用“真实系统截图 + 结构化说明”的方式，而不是泛用展示卡片。
        </p>
      </div>

      <div class="focus-media-strip">
        <figure>
          <img
            alt="DeepAudit 首页"
            src="/showcase/deepaudit-home.png"
          />
          <figcaption>DeepAudit 首页入口，突出任务入口和分析工作台。</figcaption>
        </figure>
        <figure>
          <img
            alt="DeepAudit 审计报告"
            src="/showcase/deepaudit-report.png"
          />
          <figcaption>结构化审计报告展示风险、上下文和修复建议。</figcaption>
        </figure>
      </div>
    </section>
  </div>
</template>
