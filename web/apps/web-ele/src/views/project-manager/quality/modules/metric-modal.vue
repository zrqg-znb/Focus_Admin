<script lang="ts" setup>
import { useVbenModal } from '@vben/common-ui';
import { useVbenForm } from '#/adapter/form';
import { recordModuleMetric } from '#/api/project-manager/quality';
import { ElMessage } from 'element-plus';
import { ref } from 'vue';

const emit = defineEmits(['success']);
const moduleId = ref('');

const [Form, formApi] = useVbenForm({
  schema: [
    {
      fieldName: 'record_date',
      label: '记录日期',
      component: 'DatePicker',
      componentProps: {
        type: 'date',
        valueFormat: 'YYYY-MM-DD',
      },
      defaultValue: new Date().toISOString().split('T')[0],
      rules: 'required',
    },
    {
      fieldName: 'loc',
      label: '代码行数',
      component: 'InputNumber',
      componentProps: { min: 0 },
      rules: 'required',
    },
    {
      fieldName: 'function_count',
      label: '函数个数',
      component: 'InputNumber',
      componentProps: { min: 0 },
      rules: 'required',
    },
    {
      fieldName: 'dangerous_func_count',
      label: '危险函数个数',
      component: 'InputNumber',
      componentProps: { min: 0 },
      rules: 'required',
    },
    {
      fieldName: 'duplication_rate',
      label: '代码重复率(%)',
      component: 'InputNumber',
      componentProps: { min: 0, max: 100, precision: 2 },
      rules: 'required',
    },
  ],
  showDefaultActions: false,
});

const [Modal, modalApi] = useVbenModal({
  title: '录入Mock数据',
  onConfirm: handleSubmit,
  onOpenChange: (isOpen) => {
    if (isOpen) {
      const data = modalApi.getData();
      moduleId.value = data.module_id;
      formApi.resetValues();
      formApi.setValues({
        record_date: new Date().toISOString().split('T')[0],
      });
    }
  },
});

async function handleSubmit() {
  try {
    const { valid } = await formApi.validate();
    if (!valid) return;

    modalApi.setState({ loading: true });
    const values = await formApi.getValues();
    
    await recordModuleMetric(moduleId.value, values);
    ElMessage.success('录入成功');
    
    modalApi.close();
    emit('success');
  } catch (error) {
    console.error(error);
  } finally {
    modalApi.setState({ loading: false });
  }
}
</script>

<template>
  <Modal>
    <Form />
  </Modal>
</template>
