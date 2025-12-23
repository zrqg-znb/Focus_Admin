<script setup lang="ts">
import { ref, watch } from 'vue';
import { ElDialog, ElInput, ElForm, ElFormItem, ElButton, ElMessage } from 'element-plus';
import { createFolder } from '#/api/core/file';
import { useFileManager } from '../composables/useFileManager';

const { createFolderDialogVisible, currentFolderId, fetchFiles } = useFileManager();

const form = ref({
  name: '',
});

const formRef = ref<any>(null);
const loading = ref(false);

// 监听对话框打开，重置表单
watch(createFolderDialogVisible, (val) => {
  if (val) {
    form.value.name = '';
  }
});

const handleClose = () => {
  createFolderDialogVisible.value = false;
};

const handleSubmit = async () => {
  if (!form.value.name) {
    ElMessage.warning('请输入文件夹名称');
    return;
  }

  loading.value = true;
  try {
    await createFolder({
      name: form.value.name,
      parent_id: currentFolderId.value || undefined,
    });
    ElMessage.success('创建成功');
    createFolderDialogVisible.value = false;
    // 刷新列表
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
    v-model="createFolderDialogVisible"
    title="新建文件夹"
    width="400px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <ElForm ref="formRef" :model="form" @submit.prevent="handleSubmit">
      <ElFormItem label="文件夹名称">
        <ElInput 
          v-model="form.name" 
          placeholder="请输入文件夹名称" 
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
