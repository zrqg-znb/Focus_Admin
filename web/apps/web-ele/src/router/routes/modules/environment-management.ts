import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    children: [
      {
        component: () => import('#/views/environment-management/user/index.vue'),
        meta: {
          keepAlive: true,
          title: '环境使用',
        },
        name: 'EnvironmentManagementUser',
        path: '/environment-management/user',
      },
      {
        component: () =>
          import('#/views/environment-management/admin/index.vue'),
        meta: {
          keepAlive: true,
          title: '环境配置',
        },
        name: 'EnvironmentManagementAdmin',
        path: '/environment-management/admin',
      },
    ],
    meta: {
      icon: 'lucide:server-cog',
      order: 38,
      title: '环境管理',
    },
    name: 'EnvironmentManagement',
    path: '/environment-management',
    redirect: '/environment-management/user',
  },
];

export default routes;
