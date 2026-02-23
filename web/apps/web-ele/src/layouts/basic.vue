<script lang="ts" setup>
import type { NotificationItem } from '@vben/layouts';
import type { WebSocketManager } from '#/api/core/websocket';
import type { UserMessage } from '#/api/core/message';

import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import { AuthenticationLoginExpiredModal } from '@vben/common-ui';
import { VBEN_DOC_URL, VBEN_GITHUB_URL } from '@vben/constants';
import { useWatermark } from '@vben/hooks';
import { BookOpenText, CircleHelp, SvgGithubIcon } from '@vben/icons';
import {
  BasicLayout,
  LockScreen,
  Notification,
  UserDropdown,
} from '@vben/layouts';
import { preferences } from '@vben/preferences';
import { useAccessStore, useUserStore } from '@vben/stores';
import { openWindow } from '@vben/utils';
import dayjs from 'dayjs';
import { ElMessage } from 'element-plus';

import {
  clearInboxMessageApi,
  getInboxMessageListApi,
  getUnreadMessageCountApi,
  markAllMessagesReadApi,
  markMessageReadApi,
} from '#/api/core/message';
import { getFileStreamUrl } from '#/api/core/file';
import { createNotificationWebSocket } from '#/api/core/websocket';
import { $t } from '#/locales';
import { useAuthStore } from '#/store';
import LoginForm from '#/views/_core/authentication/login.vue';

interface HeaderNotification extends NotificationItem {
  id: string;
  link?: string;
}

const userStore = useUserStore();
const authStore = useAuthStore();
const accessStore = useAccessStore();
const router = useRouter();
const { destroyWatermark, updateWatermark } = useWatermark();
const notifications = ref<HeaderNotification[]>([]);
const unreadCount = ref(0);
const wsManager = ref<null | WebSocketManager>(null);

const showDot = computed(() => unreadCount.value > 0);

const menus = computed(() => [
  {
    handler: () => {
      openWindow(VBEN_DOC_URL, {
        target: '_blank',
      });
    },
    icon: BookOpenText,
    text: $t('ui.widgets.document'),
  },
  {
    handler: () => {
      openWindow(VBEN_GITHUB_URL, {
        target: '_blank',
      });
    },
    icon: SvgGithubIcon,
    text: 'GitHub',
  },
  {
    handler: () => {
      openWindow(`${VBEN_GITHUB_URL}/issues`, {
        target: '_blank',
      });
    },
    icon: CircleHelp,
    text: $t('ui.widgets.qa'),
  },
]);

const avatar = computed(() => {
  return userStore.userInfo?.avatar ?? preferences.app.defaultAvatar;
});

async function handleLogout() {
  await authStore.logout(false);
}

function formatNoticeDate(value?: null | string) {
  if (!value) {
    return '';
  }
  const current = dayjs(value);
  if (!current.isValid()) {
    return value;
  }
  return current.format('YYYY-MM-DD HH:mm');
}

function mapMessageToNotice(message: UserMessage): HeaderNotification {
  const senderAvatar = message.sender_avatar
    ? getFileStreamUrl(message.sender_avatar)
    : preferences.app.defaultAvatar;
  return {
    id: message.id,
    avatar: senderAvatar,
    date: formatNoticeDate(message.sys_create_datetime),
    isRead: message.is_read,
    link: message.link || undefined,
    message: message.content,
    title: message.title,
  };
}

async function refreshUnreadCount() {
  try {
    const result = await getUnreadMessageCountApi();
    unreadCount.value = result.unread_count ?? 0;
  } catch (error) {
    console.error('获取未读消息数失败:', error);
  }
}

async function loadHeaderNotifications() {
  try {
    const result = await getInboxMessageListApi({
      page: 1,
      pageSize: 8,
    });
    notifications.value = (result.items || []).map(mapMessageToNotice);
  } catch (error) {
    console.error('加载通知列表失败:', error);
  }
}

function handleSocketMessage(message: {
  data?: any;
  message?: string;
  type: string;
}) {
  if (message.type !== 'notification') {
    return;
  }
  const payload = (message.data?.notification || null) as UserMessage | null;
  if (payload?.id) {
    const notice = mapMessageToNotice(payload);
    notifications.value = [
      notice,
      ...notifications.value.filter((item) => item.id !== notice.id),
    ].slice(0, 8);
  } else {
    notifications.value = [
      {
        id: `${Date.now()}`,
        avatar: preferences.app.defaultAvatar,
        date: dayjs().format('YYYY-MM-DD HH:mm'),
        isRead: false,
        message: message.message || '您有新的消息',
        title: '新消息提醒',
      },
      ...notifications.value,
    ].slice(0, 8);
  }
  unreadCount.value += 1;
}

async function connectNotificationSocket() {
  if (!accessStore.accessToken) {
    return;
  }
  if (wsManager.value?.isConnected) {
    return;
  }
  wsManager.value?.close();
  const manager = createNotificationWebSocket({
    onMessage: handleSocketMessage,
  });
  wsManager.value = manager;
  try {
    await manager.connect();
  } catch (error) {
    console.error('通知WebSocket连接失败:', error);
  }
}

function closeNotificationSocket() {
  wsManager.value?.close(1000, 'layout unmount');
  wsManager.value = null;
}

async function handleNoticeClear() {
  if (notifications.value.length === 0) {
    return;
  }
  try {
    await clearInboxMessageApi();
    notifications.value = [];
    unreadCount.value = 0;
    ElMessage.success('通知已清空');
  } catch (error) {
    console.error('清空通知失败:', error);
  }
}

async function handleMakeAll() {
  if (notifications.value.length === 0) {
    return;
  }
  try {
    await markAllMessagesReadApi();
    notifications.value = notifications.value.map((item) => ({
      ...item,
      isRead: true,
    }));
    unreadCount.value = 0;
  } catch (error) {
    console.error('全部已读操作失败:', error);
  }
}

async function handleReadNotice(item: NotificationItem) {
  const target = item as HeaderNotification;
  if (!target.id) {
    router.push('/message/center');
    return;
  }
  if (!target.isRead) {
    try {
      await markMessageReadApi(target.id);
      target.isRead = true;
      unreadCount.value = Math.max(0, unreadCount.value - 1);
    } catch (error) {
      console.error('标记已读失败:', error);
    }
  }
  if (target.link) {
    router.push(target.link);
    return;
  }
  router.push('/message/center');
}

function handleViewAll() {
  router.push('/message/center');
}

watch(
  () => ({
    enable: preferences.app.watermark,
    content: preferences.app.watermarkContent,
  }),
  async ({ enable, content }) => {
    if (enable) {
      await updateWatermark({
        content:
          content ||
          `${userStore.userInfo?.username} - ${userStore.userInfo?.realName}`,
      });
    } else {
      destroyWatermark();
    }
  },
  {
    immediate: true,
  },
);

watch(
  () => accessStore.accessToken,
  async (token) => {
    if (!token) {
      notifications.value = [];
      unreadCount.value = 0;
      closeNotificationSocket();
      return;
    }
    await Promise.all([loadHeaderNotifications(), refreshUnreadCount()]);
    await connectNotificationSocket();
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  closeNotificationSocket();
});
</script>

<template>
  <BasicLayout @clear-preferences-and-logout="handleLogout">
    <template #user-dropdown>
      <UserDropdown
        :avatar
        :menus
        :text="userStore.userInfo?.realName"
        description="jiangzhikj@outlook.com"
        tag-text="Pro"
        @logout="handleLogout"
      />
    </template>
    <template #notification>
      <Notification
        :dot="showDot"
        :notifications="notifications"
        @clear="handleNoticeClear"
        @make-all="handleMakeAll"
        @read="handleReadNotice"
        @view-all="handleViewAll"
      />
    </template>
    <template #extra>
      <AuthenticationLoginExpiredModal
        v-model:open="accessStore.loginExpired"
        :avatar
      >
        <LoginForm />
      </AuthenticationLoginExpiredModal>
    </template>
    <template #lock-screen>
      <LockScreen :avatar @to-login="handleLogout" />
    </template>
  </BasicLayout>
</template>
