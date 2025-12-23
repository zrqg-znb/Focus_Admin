<script lang="ts" setup>
import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';

import type { SystemPostApi } from '#/api/system/post';
import { useVbenForm } from '#/adapter/form';
import type { VbenFormSchema } from '#/adapter/form';

const emit = defineEmits<{
  success: [];
}>();

const userData = ref<SystemPostApi.SystemPost>();

const formSchema: VbenFormSchema[] = [
  {
    component: 'Input',
    fieldName: 'username',
    label: $t('system.user.account'),
    componentProps: {
      disabled: true,
    },
  },
  {
    component: 'Input',
    fieldName: 'name',
    label: $t('system.user.userName'),
    componentProps: {
      disabled: true,
    },
  },
  {
    component: 'Input',
    fieldName: 'email',
    label: $t('system.user.email'),
    componentProps: {
      disabled: true,
    },
  },
];

const [Form, formApi] = useVbenForm({
  layout: 'vertical',
  schema: formSchema,
  showDefaultActions: false,
});

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    // 这是一个只读的展示窗口，直接关闭
    modalApi.close();
    emit('success');
  },
  onOpenChange(isOpen) {
    if (isOpen) {
      const data = modalApi.getData<SystemPostApi.SystemPost>();
      if (data) {
        userData.value = data;
        formApi.setValues(userData.value);
      }
    }
  },
});

const getModalTitle = computed(() =>
  $t('ui.actionTitle.view', [$t('system.user.name')]),
);
</script>

<template>
  <Modal :title="getModalTitle">
    <Form class="mx-4" />
  </Modal>
</template>
