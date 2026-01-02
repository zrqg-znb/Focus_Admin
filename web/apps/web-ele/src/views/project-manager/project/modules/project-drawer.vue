<script lang="ts" setup>
import { ref } from 'vue';
import { useVbenDrawer } from '@vben/common-ui';
import { useVbenForm } from '#/adapter/form';
import { createProject, updateProject } from '#/api/project-manager/project';
import { getUserListApi } from '#/api/core';
import { useFormSchema } from '../data';
import { ElMessage } from 'element-plus';

const emit = defineEmits(['success']);

const isUpdate = ref(false);
const recordId = ref<string>('');

const [Form, formApi] = useVbenForm({
  ...useFormSchema(),
  showDefaultActions: false,
});

const [Drawer, drawerApi] = useVbenDrawer({
  onConfirm: handleSubmit,
  onOpenChange: async (isOpen) => {
    if (isOpen) {
      // 加载用户列表供选择
      const users = await getUserListApi({ page: 1, pageSize: 1000 });
      formApi.updateSchema({
        fieldName: 'manager_ids',
        componentProps: {
          options: users.items.map(u => ({ label: u.name || u.username, value: u.id })),
        },
      });

      const data = drawerApi.getData();
      isUpdate.value = !!data?.id;
      recordId.value = data?.id || '';
      
      if (isUpdate.value) {
        drawerApi.setState({ title: '编辑项目' });
        // 转换 managers 对象数组为 ids 数组
        const formData = {
          ...data,
          manager_ids: data.managers?.map((m: any) => m.id) || [],
        };
        formApi.setValues(formData);
      } else {
        drawerApi.setState({ title: '新增项目' });
        formApi.setValues({
          enable_milestone: true,
          enable_iteration: true,
          enable_quality: true,
        });
      }
    } else {
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
    
    if (isUpdate.value) {
      await updateProject(recordId.value, values);
      ElMessage.success('更新成功');
    } else {
      await createProject(values);
      ElMessage.success('创建成功');
    }
    
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
