import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    children: [
      {
        component: () => import('#/views/_core/message-center/index.vue'),
        meta: {
          keepAlive: true,
          title: '站内信中心',
        },
        name: 'MessageCenter',
        path: '/message/center',
      },
      {
        component: () =>
          import('#/views/_core/announcement-settings/index.vue'),
        meta: {
          title: '公告设置',
        },
        name: 'AnnouncementSettings',
        path: '/message/announcement',
      },
    ],
    meta: {
      icon: 'lucide:bell-ring',
      order: 98,
      title: '消息通知',
    },
    name: 'MessageNotice',
    path: '/message',
    redirect: '/message/center',
  },
];

export default routes;

