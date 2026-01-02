<script lang="ts" setup>
import { useVbenModal } from '@vben/common-ui';
import { useVbenForm } from '#/adapter/form';
import { recordIterationMetric } from '#/api/project-manager/iteration';
import { ElMessage } from 'element-plus';
import { ref } from 'vue';

const emit = defineEmits(['success']);
const iterationId = ref('');

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
      fieldName: 'req_completion_rate',
      label: '需求完成率(%)',
      component: 'InputNumber',
      componentProps: { min: 0, max: 100 },
      rules: 'required',
    },
    {
      fieldName: 'req_drift_rate',
      label: '需求游离率(%)',
      component: 'InputNumber',
      componentProps: { min: 0, max: 100 },
      rules: 'required',
    },
    {
      fieldName: 'req_decomposition_rate',
      label: '需求分解率(%)',
      component: 'InputNumber',
      componentProps: { min: 0, max: 100 },
      rules: 'required',
    },
    {
      fieldName: 'req_workload',
      label: '需求工作量',
      component: 'InputNumber',
      componentProps: { min: 0 },
      rules: 'required',
    },
    {
      fieldName: 'completed_workload',
      label: '已完成工作量',
      component: 'InputNumber',
      componentProps: { min: 0 },
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
      iterationId.value = data.iteration_id;
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
    
    await recordIterationMetric(iterationId.value, values);
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
