import type { DefaultTheme } from 'vitepress';

import { defineConfig } from 'vitepress';

import { version } from '../../../package.json';

export const zh = defineConfig({
  description: 'Focus Admin - 企业级全栈管理系统',
  lang: 'zh-Hans',
  themeConfig: {
    darkModeSwitchLabel: '主题',
    darkModeSwitchTitle: '切换到深色模式',
    docFooter: {
      next: '下一页',
      prev: '上一页',
    },
    editLink: {
      pattern:
        'https://github.com/jiangzhikj/zq-platform/edit/main/web/docs/src/:path',
      text: '在 GitHub 上编辑此页面',
    },
    footer: {
      copyright: `Copyright © 2024-${new Date().getFullYear()} Focus Admin`,
      message: '内部项目文档',
    },
    langMenuLabel: '多语言',
    lastUpdated: {
      formatOptions: {
        dateStyle: 'short',
        timeStyle: 'medium',
      },
      text: '最后更新于',
    },
    lightModeSwitchTitle: '切换到浅色模式',
    nav: nav(),

    outline: {
      label: '页面导航',
    },
    returnToTopLabel: '回到顶部',

    sidebar: {
      '/overview/': { base: '/overview/', items: sidebarOverview() },
      '/backend/': { base: '/backend/', items: sidebarBackend() },
      '/frontend/': { base: '/frontend/', items: sidebarFrontend() },
      '/dev-guide/': { base: '/dev-guide/', items: sidebarDevGuide() },
    },
    sidebarMenuLabel: '菜单',
  },
});

// 项目概览侧边栏
function sidebarOverview(): DefaultTheme.SidebarItem[] {
  return [
    {
      collapsed: false,
      text: '项目简介',
      items: [
        { link: 'introduction', text: '项目介绍' },
        { link: 'tech-stack', text: '技术栈' },
        { link: 'architecture', text: '系统架构' },
      ],
    },
    {
      collapsed: false,
      text: '快速开始',
      items: [
        { link: 'quick-start', text: '快速开始' },
        { link: 'project-structure', text: '项目结构' },
      ],
    },
  ];
}

// 后端文档侧边栏
function sidebarBackend(): DefaultTheme.SidebarItem[] {
  return [
    {
      collapsed: false,
      text: '核心模块',
      items: [
        { link: 'core/overview', text: '模块概览' },
        { link: 'core/auth', text: '认证模块' },
        { link: 'core/user', text: '用户管理' },
        { link: 'core/role', text: '角色管理' },
        { link: 'core/permission', text: '权限管理' },
        { link: 'core/menu', text: '菜单管理' },
        { link: 'core/dept', text: '部门管理' },
      ],
    },
    {
      collapsed: false,
      text: '业务模块',
      items: [
        { link: 'apps/project-manager', text: '项目管理' },
        { link: 'apps/performance', text: '绩效管理' },
        { link: 'apps/code-compliance', text: '代码合规' },
        { link: 'apps/delivery-matrix', text: '交付矩阵' },
        { link: 'apps/integration-report', text: '集成报告' },
      ],
    },
    {
      collapsed: false,
      text: '系统功能',
      items: [
        { link: 'system/scheduler', text: '任务调度' },
        { link: 'system/file-manager', text: '文件管理' },
        { link: 'system/dict', text: '数据字典' },
        { link: 'system/log', text: '日志管理' },
      ],
    },
  ];
}

// 前端文档侧边栏
function sidebarFrontend(): DefaultTheme.SidebarItem[] {
  return [
    {
      collapsed: false,
      text: '基础',
      items: [
        { link: 'overview', text: '前端概览' },
        { link: 'project-structure', text: '目录结构' },
        { link: 'router', text: '路由管理' },
        { link: 'store', text: '状态管理' },
      ],
    },
    {
      collapsed: false,
      text: '功能页面',
      items: [
        { link: 'views/project-manager', text: '项目管理页面' },
        { link: 'views/performance', text: '绩效管理页面' },
        { link: 'views/system', text: '系统管理页面' },
      ],
    },
    {
      collapsed: false,
      text: '组件',
      items: [
        { link: 'components/overview', text: '组件概览' },
        { link: 'components/common', text: '通用组件' },
      ],
    },
  ];
}

// 开发指南侧边栏
function sidebarDevGuide(): DefaultTheme.SidebarItem[] {
  return [
    {
      collapsed: false,
      text: '环境搭建',
      items: [
        { link: 'setup/backend', text: '后端环境' },
        { link: 'setup/frontend', text: '前端环境' },
        { link: 'setup/database', text: '数据库配置' },
      ],
    },
    {
      collapsed: false,
      text: '开发规范',
      items: [
        { link: 'standard/code-style', text: '代码规范' },
        { link: 'standard/git', text: 'Git 规范' },
        { link: 'standard/api', text: 'API 规范' },
      ],
    },
    {
      collapsed: false,
      text: '部署',
      items: [
        { link: 'deploy/docker', text: 'Docker 部署' },
        { link: 'deploy/nginx', text: 'Nginx 配置' },
      ],
    },
  ];
}

function nav(): DefaultTheme.NavItem[] {
  return [
    {
      activeMatch: '^/overview/',
      text: '项目概览',
      link: '/overview/introduction',
    },
    {
      activeMatch: '^/backend/',
      text: '后端文档',
      items: [
        {
          text: '核心模块',
          link: '/backend/core/overview',
        },
        {
          text: '业务模块',
          link: '/backend/apps/project-manager',
        },
        {
          text: '系统功能',
          link: '/backend/system/scheduler',
        },
      ],
    },
    {
      activeMatch: '^/frontend/',
      text: '前端文档',
      link: '/frontend/overview',
    },
    {
      activeMatch: '^/dev-guide/',
      text: '开发指南',
      items: [
        {
          text: '环境搭建',
          link: '/dev-guide/setup/backend',
        },
        {
          text: '开发规范',
          link: '/dev-guide/standard/code-style',
        },
        {
          text: '部署文档',
          link: '/dev-guide/deploy/docker',
        },
      ],
    },
    {
      text: version,
      items: [
        {
          link: 'https://github.com/jiangzhikj/zq-platform/releases',
          text: '更新日志',
        },
      ],
    },
  ];
}

export const search: DefaultTheme.AlgoliaSearchOptions['locales'] = {
  root: {
    placeholder: '搜索文档',
    translations: {
      button: {
        buttonAriaLabel: '搜索文档',
        buttonText: '搜索文档',
      },
      modal: {
        errorScreen: {
          helpText: '你可能需要检查你的网络连接',
          titleText: '无法获取结果',
        },
        footer: {
          closeText: '关闭',
          navigateText: '切换',
          searchByText: '搜索提供者',
          selectText: '选择',
        },
        noResultsScreen: {
          noResultsText: '无法找到相关结果',
          reportMissingResultsLinkText: '点击反馈',
          reportMissingResultsText: '你认为该查询应该有结果？',
          suggestedQueryText: '你可以尝试查询',
        },
        searchBox: {
          cancelButtonAriaLabel: '取消',
          cancelButtonText: '取消',
          resetButtonAriaLabel: '清除查询条件',
          resetButtonTitle: '清除查询条件',
        },
        startScreen: {
          favoriteSearchesTitle: '收藏',
          noRecentSearchesText: '没有搜索历史',
          recentSearchesTitle: '搜索历史',
          removeFavoriteSearchButtonTitle: '从收藏中移除',
          removeRecentSearchButtonTitle: '从搜索历史中移除',
          saveRecentSearchButtonTitle: '保存至搜索历史',
        },
      },
    },
  },
};
