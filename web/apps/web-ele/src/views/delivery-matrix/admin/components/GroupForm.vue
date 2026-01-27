<script lang="ts" setup>
import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { useVbenForm } from '#/adapter/form';
import { createGroup, updateGroup } from '#/api/delivery-matrix';

import { useGroupFormSchema } from '../../data';

const emit = defineEmits<{ success: [] }>();
const formData = ref<any>();

const [Form, formApi] = useVbenForm({
  commonConfig: { colon: true, componentProps: { class: 'w-full' } },
  schema: useGroupFormSchema(),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-1 gap-x-4',
});

const [Drawer, drawerApi] = useVbenDrawer({
  onConfirm: onSubmit,
  onOpenChange(isOpen) {
    if (isOpen) {
      const data = drawerApi.getData<any>();
      if (data && data.id) {
        formData.value = data;
        formApi.setValues(data);
      } else {
        formData.value = {};
        formApi.resetForm();
      }
    }
  },
});

const getDrawerTitle = computed(() =>
  formData.value?.id ? '编辑项目群' : '创建项目群',
);

async function onSubmit() {
  const { valid } = await formApi.validate();
  if (valid) {
    drawerApi.lock();
    const data = await formApi.getValues();
    try {
      await (formData.value?.id
        ? updateGroup(formData.value.id, data)
        : createGroup(data));
      drawerApi.close();
      emit('success');
    } finally {
      drawerApi.unlock();
    }
  }
}
</script>
<template>
  <Drawer class="w-full max-w-[600px]" :title="getDrawerTitle">
    <Form class="mx-4" />
  </Drawer>
</template>
