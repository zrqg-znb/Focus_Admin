<script lang="ts" setup>
import { useVbenModal } from '@vben/common-ui';
import { useVbenForm } from '#/adapter/form';
import { updateMilestone } from '#/api/project-manager/milestone';
import { useFormSchema } from '../data';
import { ElMessage } from 'element-plus';
import { ref } from 'vue';

const emit = defineEmits(['success']);
const projectId = ref('');

const [Form, formApi] = useVbenForm({
  ...useFormSchema(),
  showDefaultActions: false,
});

const [Modal, modalApi] = useVbenModal({
  title: '配置里程碑',
  onConfirm: handleSubmit,
  onOpenChange: (isOpen) => {
    if (isOpen) {
      const data = modalApi.getData();
      projectId.value = data.project_id;
      formApi.setValues(data);
    }
  },
});

async function handleSubmit() {
  try {
    modalApi.setState({ loading: true });
    const values = await formApi.getValues();
    
    await updateMilestone(projectId.value, values);
    ElMessage.success('更新成功');
    
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
