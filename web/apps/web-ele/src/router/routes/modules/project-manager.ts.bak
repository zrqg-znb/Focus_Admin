import type { RouteRecordRaw } from 'vue-router';

import { BasicLayout } from '#/layouts';

const routes: RouteRecordRaw[] = [
  {
    component: BasicLayout,
    meta: {
      icon: 'lucide:folder-kanban',
      order: 1000,
      title: '项目管理',
    },
    name: 'ProjectManager',
    path: '/project-manager',
    children: [
      {
        name: 'ProjectList',
        path: 'project',
        component: () => import('#/views/project-manager/project/index.vue'),
        meta: {
          title: '项目列表',
          icon: 'lucide:list',
        },
      },
      {
        name: 'MilestoneBoard',
        path: 'milestone',
        component: () => import('#/views/project-manager/milestone/index.vue'),
        meta: {
          title: '里程碑看板',
          icon: 'lucide:flag',
        },
      },
      {
        name: 'IterationOverview',
        path: 'iteration',
        component: () => import('#/views/project-manager/iteration/overview.vue'),
        meta: {
          title: '健康迭代表',
          icon: 'lucide:activity',
        },
      },
      {
        name: 'IterationDetail',
        path: 'iteration/detail/:id',
        component: () => import('#/views/project-manager/iteration/detail.vue'),
        meta: {
          title: '迭代详情',
          hideInMenu: true,
          currentActiveMenu: '/project-manager/iteration',
        },
      },
      {
        name: 'QualityOverview',
        path: 'quality',
        component: () => import('#/views/project-manager/quality/overview.vue'),
        meta: {
          title: '代码质量',
          icon: 'lucide:code-2',
        },
      },
      {
        name: 'QualityDetail',
        path: 'quality/detail/:id',
        component: () => import('#/views/project-manager/quality/detail.vue'),
        meta: {
          title: '质量详情',
          hideInMenu: true,
          currentActiveMenu: '/project-manager/quality',
        },
      },
    ],
  },
];

export default routes;
