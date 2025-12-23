<script setup lang="ts">
import { ref, watch } from 'vue';
import { ElDialog, ElInput, ElForm, ElFormItem, ElButton, ElMessage } from 'element-plus';
import { renameItem } from '#/api/core/file';
import { useFileManager } from '../composables/useFileManager';

const props = defineProps<{
  visible: boolean;
  item: { id: string; name: string; type: string } | null;
}>();

const emit = defineEmits(['update:visible', 'success']);

const { fetchFiles } = useFileManager();
const loading = ref(false);
const form = ref({
  name: '',
});
const formRef = ref<any>(null);

watch(
  () => props.visible,
  (val) => {
    if (val && props.item) {
      form.value.name = props.item.name;
    }
  },
);

const handleClose = () => {
  emit('update:visible', false);
};

const handleSubmit = async () => {
  if (!props.item) return;
  if (!form.value.name) {
    ElMessage.warning('请输入名称');
    return;
  }

  loading.value = true;
  try {
    await renameItem(props.item.id, {
      name: form.value.name,
    });
    ElMessage.success('重命名成功');
    emit('update:visible', false);
    emit('success');
    fetchFiles();
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <ElDialog
    :model-value="visible"
    title="重命名"
    width="400px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <ElForm ref="formRef" :model="form" @submit.prevent="handleSubmit">
      <ElFormItem label="名称">
        <ElInput 
          v-model="form.name" 
          placeholder="请输入名称" 
          autofocus
          @keyup.enter="handleSubmit"
        />
      </ElFormItem>
    </ElForm>
    <template #footer>
      <div class="dialog-footer">
        <ElButton @click="handleClose">取消</ElButton>
        <ElButton type="primary" :loading="loading" @click="handleSubmit">
          确定
        </ElButton>
      </div>
    </template>
  </ElDialog>
</template>
