<script lang="ts" setup>
import { ref } from 'vue';
import { ElMessage } from 'element-plus';
import { useVbenModal, Page } from '@vben/common-ui';
import { $t } from '@vben/locales';

defineOptions({ name: 'SystemPermission' });

import PermissionLeftPanel from './modules/permission-left-panel.vue';
import PermissionTable from './modules/permission-table.vue';
import PermissionFormModal from './modules/permission-form-modal.vue';

const selectedMenuId = ref<string>();
const selectedMenuName = ref<string>();
const permissionTableRef = ref();

const [PermissionFormModalComponent, permissionFormModalApi] = useVbenModal({
  connectedComponent: PermissionFormModal,
  destroyOnClose: true,
});

function onAddPermission(permission?: any) {
  if (!selectedMenuId.value) {
    ElMessage.warning($t('permission.selectMenuFirst'));
    return;
  }

  // 如果是编辑操作，传递权限对象；否则只传递 menu_id
  const data = permission ? permission : { menu_id: selectedMenuId.value };
  permissionFormModalApi.setData(data).open();
}

function onMenuSelect(menuId: string, menuName?: string) {
  selectedMenuId.value = menuId;
  selectedMenuName.value = menuName;
}

function onFormSuccess() {
  // 刷新表格
  permissionTableRef.value?.loadPermissions?.();
}
</script>

<template>
  <Page auto-content-height>
    <PermissionFormModalComponent @success="onFormSuccess" />

    <div class="flex h-full">
      <!-- 左侧：菜单树 -->
      <div class="w-1/6">
        <PermissionLeftPanel @select="onMenuSelect" />
      </div>

      <!-- 右侧：权限管理 -->
      <div class="w-5/6">
        <PermissionTable
          ref="permissionTableRef"
          :menu-id="selectedMenuId"
          :menu-name="selectedMenuName"
          @add="onAddPermission"
        />
      </div>
    </div>
  </Page>
</template>

