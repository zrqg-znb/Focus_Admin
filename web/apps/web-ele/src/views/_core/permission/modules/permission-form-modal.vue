<script lang="ts" setup>
import type { Permission, PermissionCreateInput } from '#/api/core/permission';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElButton } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createPermissionApi,
  updatePermissionApi,
} from '#/api/core/permission';

import { getFormSchema } from '../data';

const emit = defineEmits(['success']);
const permissionData = ref<Permission>();
const currentMenuId = ref<string>('');

const [Form, formApi] = useVbenForm({
  layout: 'vertical',
  schema: getFormSchema(),
  showDefaultActions: false,
});

const getTitle = computed(() => {
  return permissionData.value?.id
    ? $t('permission.edit')
    : $t('permission.add');
});

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (valid) {
      modalApi.lock();
      try {
        const formData = await formApi.getValues<any>();

        // 构建提交数据，确保包含 menu_id
        const submitData: PermissionCreateInput = {
          ...formData,
          menu_id: currentMenuId.value,
        };

        await (permissionData.value?.id
          ? updatePermissionApi(permissionData.value.id, submitData)
          : createPermissionApi(submitData));

        modalApi.close();
        emit('success');
      } finally {
        modalApi.lock(false);
      }
    }
  },
  onOpenChange(isOpen) {
    if (isOpen) {
      const data = modalApi.getData<Permission>();
      if (data) {
        permissionData.value = data;
        currentMenuId.value = data.menu_id;
        formApi.setValues(data);
      } else {
        permissionData.value = undefined;
        formApi.resetForm();
      }
    }
  },
});
</script>

<template>
  <Modal :title="getTitle">
    <Form class="mx-4" />
    <template #prepend-footer>
      <div class="flex-auto">
        <ElButton type="default" @click="() => formApi.resetForm()">
          {{ $t('common.reset') }}
        </ElButton>
      </div>
    </template>
  </Modal>
</template>
