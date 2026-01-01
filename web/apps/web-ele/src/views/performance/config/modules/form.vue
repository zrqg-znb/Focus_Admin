<script lang="ts" setup>
import type { PerformanceIndicator } from '#/api/core/performance';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { useVbenForm } from '#/adapter/form';
import { createIndicatorApi, updateIndicatorApi } from '#/api/core/performance';

import { getFormSchema } from '../data';

const emit = defineEmits<{
  success: [];
}>();

const formData = ref<PerformanceIndicator>();

const [Form, formApi] = useVbenForm({
  commonConfig: {
    colon: true,
    componentProps: {
      class: 'w-full',
    },
    labelWidth: 100,
  },
  schema: getFormSchema(),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-1 gap-x-4',
});

const [Drawer, drawerApi] = useVbenDrawer({
  onConfirm: onSubmit,
  onOpenChange(isOpen) {
    if (isOpen) {
      const data = drawerApi.getData<PerformanceIndicator>();
      if (data) {
        formData.value = data;
        const values = { ...data };
        if (!values.owner_id && data.owner) {
          values.owner_id = data.owner.id;
        }
        formApi.setValues(values);
      } else {
        formData.value = undefined;
        formApi.resetForm();
      }
    }
  },
});

const getDrawerTitle = computed(() =>
  formData.value?.id ? '编辑指标' : '新增指标',
);

async function onSubmit() {
  const { valid } = await formApi.validate();
  if (valid) {
    drawerApi.lock();
    const data = await formApi.getValues<PerformanceIndicator>();
    try {
      await (formData.value?.id
        ? updateIndicatorApi(formData.value.id, data)
        : createIndicatorApi(data));
      await drawerApi.close();
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
