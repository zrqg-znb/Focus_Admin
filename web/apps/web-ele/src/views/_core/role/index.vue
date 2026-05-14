<script lang="ts" setup>
import type { Role } from '#/api/core/role';

import { ref } from 'vue';

import { Page } from '@vben/common-ui';

import PermissionAssignPanel from './modules/permission-assign-panel.vue';
import RoleList from './modules/role-list.vue';

defineOptions({ name: 'SystemRole' });

const currentRole = ref<Role>();
const permissionPanelRef = ref();

/**
 * 角色选择事件
 */
function onRoleSelect(role: Role | undefined) {
  currentRole.value = role;
}

/**
 * 权限分配成功
 */
function onPermissionSuccess() {
  // 权限分配成功，可以在这里做其他操作
}
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full">
      <!-- 左侧：角色列表 -->
      <div class="w-1/6">
        <RoleList @select="onRoleSelect" />
      </div>

      <!-- 右侧：权限分配面板 -->
      <div class="w-5/6">
        <PermissionAssignPanel
          ref="permissionPanelRef"
          :role="currentRole"
          @success="onPermissionSuccess"
        />
      </div>
    </div>
  </Page>
</template>
