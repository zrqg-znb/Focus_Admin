<script lang="ts" setup>
import { useVbenDrawer } from '@vben/common-ui';
import { useVbenForm } from '#/adapter/form';
import { configModule } from '#/api/project-manager/quality';
import { getUserListApi } from '#/api/core';
import { ElMessage } from 'element-plus';
import { ref } from 'vue';

const emit = defineEmits(['success']);
const projectId = ref('');

const [Form, formApi] = useVbenForm({
  schema: [
    {
      fieldName: 'name',
      label: '模块名称',
      component: 'Input',
      rules: 'required',
    },
    {
      fieldName: 'owner_id',
      label: '责任人',
      component: 'Select',
      componentProps: {
        filterable: true,
        options: [], // 动态加载
      },
    },
  ],
  showDefaultActions: false,
});

const [Drawer, drawerApi] = useVbenDrawer({
  title: '配置模块',
  onConfirm: handleSubmit,
  onOpenChange: async (isOpen) => {
    if (isOpen) {
      // 加载用户
      const users = await getUserListApi({ page: 1, pageSize: 1000 });
      formApi.updateSchema({
        fieldName: 'owner_id',
        componentProps: {
          options: users.items.map(u => ({ label: u.name || u.username, value: u.id })),
        },
      });

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
    
    await configModule({
      ...values,
      project_id: projectId.value,
    });
    
    ElMessage.success('配置成功');
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
