<script lang="ts" setup>
import { ref } from 'vue';

import { saveDtsExtension } from '#/api/project-manager/dts-statistics';
import { BasicDrawer, useDrawerInner } from '#/components/drawer';
import { useZqForm, ZqForm } from '#/components/zq-form';

import { qaFormSchema } from './data';

const emit = defineEmits(['success']);
const defectNo = ref('');
const [registerForm, { setFieldsValue, validate }] = useZqForm();

const [registerDrawer, { setDrawerProps, closeDrawer }] = useDrawerInner(
  async (data) => {
    defectNo.value = data.row.defectNo;
    setFieldsValue(data.row);
  },
);

async function handleSubmit() {
  const values = await validate();
  setDrawerProps({ confirmLoading: true });
  await saveDtsExtension(defectNo.value, values);
  setDrawerProps({ confirmLoading: false });
  closeDrawer();
  emit('success');
}
const formProps = {
  ...qaFormSchema,
  register: registerForm,
};
</script>
<template>
  <BasicDrawer v-bind="registerDrawer" title="编辑拓展信息" @ok="handleSubmit">
    <ZqForm v-bind="formProps" />
  </BasicDrawer>
</template>
