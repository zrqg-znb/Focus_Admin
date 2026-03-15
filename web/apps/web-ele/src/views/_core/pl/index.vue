<script lang="ts" setup>
import type { PlGroup } from '#/api/core/pl';

import { ref } from 'vue';

import { Page } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElButton, ElMessage, ElMessageBox } from 'element-plus';

import { addPlUsersApi, removePlUsersApi } from '#/api/core/pl';
import { UserListPanel } from '#/components/user-list-panel';
import { UserSelector } from '#/components/zq-form/user-selector';

import PlList from './modules/pl-list.vue';

defineOptions({ name: 'SystemPl' });

const currentPl = ref<PlGroup>();
const tempSelectedUsers = ref<Set<string>>(new Set());
const userListPanelRef = ref<InstanceType<typeof UserListPanel>>();
const plListRef = ref<InstanceType<typeof PlList>>();

function onPlSelect(plGroup: PlGroup | undefined) {
  currentPl.value = plGroup;
  tempSelectedUsers.value.clear();
}

function handleUserSelect(userId: string, _user: any) {
  if (tempSelectedUsers.value.has(userId)) {
    tempSelectedUsers.value.delete(userId);
  } else {
    tempSelectedUsers.value.add(userId);
  }
}

function handleRemoveUser(userId: string) {
  tempSelectedUsers.value.delete(userId);
}

async function refreshCurrentPl() {
  const currentId = currentPl.value?.id;
  await plListRef.value?.reload(currentId);
  userListPanelRef.value?.reload();
}

async function handleAddUsers(userIds: string | string[]) {
  if (!currentPl.value?.id) {
    ElMessage.warning($t('pl.selectGroupFirst'));
    throw new Error('请先选择资源组');
  }

  const userIdsArray = Array.isArray(userIds) ? userIds : [userIds];
  if (userIdsArray.length === 0) {
    ElMessage.warning($t('pl.selectUsersFirst'));
    throw new Error('请先选择用户');
  }

  await addPlUsersApi(currentPl.value.id, { user_ids: userIdsArray });
  ElMessage.success($t('pl.addUsersSuccess'));
  await refreshCurrentPl();
}

async function handleRemoveUsers() {
  if (!currentPl.value?.id) {
    ElMessage.warning($t('pl.selectGroupFirst'));
    return;
  }
  if (tempSelectedUsers.value.size === 0) {
    ElMessage.warning($t('pl.selectUsersFirst'));
    return;
  }

  const userIds = [...tempSelectedUsers.value];
  const confirmMessage =
    $t('pl.removeUsersConfirm', [tempSelectedUsers.value.size]) ||
    `确定要删除选中的 ${tempSelectedUsers.value.size} 个用户吗？`;

  try {
    await ElMessageBox.confirm(confirmMessage, $t('common.delete') || '删除', {
      confirmButtonText: $t('common.confirm') || '确定',
      cancelButtonText: $t('common.cancel') || '取消',
      type: 'warning',
    });

    await removePlUsersApi(currentPl.value.id, {
      user_ids: userIds,
    });
    ElMessage.success($t('pl.removeUsersSuccess'));
    tempSelectedUsers.value.clear();
    await refreshCurrentPl();
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to remove users:', error);
      ElMessage.error(error?.message || $t('pl.removeUsersFailed'));
    }
  }
}
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full">
      <div class="w-1/6 flex flex-col">
        <PlList ref="plListRef" @select="onPlSelect" />
      </div>

      <div class="w-5/6">
        <UserListPanel
          ref="userListPanelRef"
          :data-source="currentPl ? 'pl' : 'all'"
          :source-id="currentPl?.id"
          :temp-selected-users="tempSelectedUsers"
          :filterable="true"
          :multiple="true"
          :selectable="true"
          :show-selected-tags="false"
          :show-border="false"
          @user-select="handleUserSelect"
          @remove-user="handleRemoveUser"
        >
          <template #title>
            <div class="flex w-full flex-nowrap items-center gap-2">
              <UserSelector
                :multiple="true"
                :disabled="!currentPl"
                display-mode="button"
                :placeholder="$t('common.add') || '新增'"
                :on-confirm="handleAddUsers"
              />

              <ElButton
                type="danger"
                plain
                :disabled="!currentPl || tempSelectedUsers.size === 0"
                @click="handleRemoveUsers"
              >
                {{ $t('common.delete') || '删除' }}
              </ElButton>
            </div>
          </template>
        </UserListPanel>
      </div>
    </div>
  </Page>
</template>
