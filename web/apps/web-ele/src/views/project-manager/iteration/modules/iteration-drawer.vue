<script lang="ts" setup>
import { useVbenDrawer } from '@vben/common-ui';
import { useVbenForm } from '#/adapter/form';
import { createIteration } from '#/api/project-manager/iteration';
import { ElMessage } from 'element-plus';
import { ref } from 'vue';

const emit = defineEmits(['success']);
const projectId = ref('');

const [Form, formApi] = useVbenForm({
  schema: [
    {
      fieldName: 'name',
      label: '迭代名称',
      component: 'Input',
      rules: 'required',
    },
    {
      fieldName: 'code',
      label: '迭代编码',
      component: 'Input',
      rules: 'required',
    },
    {
      fieldName: 'start_date',
      label: '开始时间',
      component: 'DatePicker',
      componentProps: {
        type: 'date',
        valueFormat: 'YYYY-MM-DD',
      },
      rules: 'required',
    },
    {
      fieldName: 'end_date',
      label: '结束时间',
      component: 'DatePicker',
      componentProps: {
        type: 'date',
        valueFormat: 'YYYY-MM-DD',
      },
      rules: 'required',
    },
    {
      fieldName: 'is_current',
      label: '设为当前迭代',
      component: 'Switch',
      help: '开启后，该项目下的其他迭代将自动取消当前状态',
    },
  ],
  showDefaultActions: false,
});

const [Drawer, drawerApi] = useVbenDrawer({
  title: '新建迭代',
  onConfirm: handleSubmit,
  onOpenChange: (isOpen) => {
    if (isOpen) {
      const data = drawerApi.getData();
      projectId.value = data.project_id;
      formApi.resetValues();
    }
  },
});

async function handleSubmit() {
  try {
    const { valid } = await formApi.validate();
    if (!valid) return;

    drawerApi.setState({ loading: true });
    const values = await formApi.getValues();
    
    await createIteration({
      ...values,
      project_id: projectId.value,
    });
    
    ElMessage.success('创建成功');
    drawerApi.close();
    emit('success');
  } catch (error) {
    console.error(error);
  } finally {
    drawerApi.setState({ loading: false });
  }
}
</script>

<template>
  <Drawer>
    <Form />
  </Drawer>
</template>
