<script setup lang="ts">
import { ref } from 'vue';
import { Page } from '@vben/common-ui';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { listProjectsApi, createProjectApi, updateProjectApi } from '#/api/code_scan';
import { useColumns, getFormSchema, useSearchFormSchema } from './data';
import { ElButton, ElMessage, ElDialog, ElForm, ElFormItem, ElInput } from 'element-plus';
import { useRouter } from 'vue-router';
import { useClipboard } from '@vueuse/core';
import { useVbenForm } from '#/adapter/form';

const router = useRouter();
const { copy } = useClipboard();

const gridOptions: any = {
  columns: useColumns(),
  height: '100%', // 强制撑满父容器
  proxyConfig: {
    ajax: {
      query: async ({ page }, formValues) => {
        const res = await listProjectsApi(formValues);
        return { items: res };
      },
    },
  },
  toolbarConfig: {
      search: true,
      refresh: true,
  }
};

const [Grid, gridApi] = useVbenVxeGrid({
    gridOptions,
    formOptions: {
        schema: useSearchFormSchema(),
    }
});

// 创建/编辑项目弹窗逻辑
const dialogVisible = ref(false);
const dialogTitle = ref('新建项目');
const isEditMode = ref(false);
const currentId = ref('');

const [Form, formApi] = useVbenForm({
  schema: getFormSchema(),
  showDefaultActions: false,
});

function handleCreate() {
  isEditMode.value = false;
  dialogTitle.value = '新建项目';
  formApi.setValues({
    name: '',
    repo_url: '',
    branch: 'master',
    description: '',
    caretaker_id: '',
  });
  dialogVisible.value = true;
}

function handleEdit(row: any) {
  isEditMode.value = true;
  dialogTitle.value = '编辑项目';
  currentId.value = row.id;
  // 回显数据
  formApi.setValues({
    name: row.name,
    repo_url: row.repo_url,
    branch: row.branch,
    description: row.description,
    caretaker_id: row.caretaker,
  });
  dialogVisible.value = true;
}

async function submitForm() {
  const { valid } = await formApi.validate();
  if (!valid) return;

  const values = await formApi.getValues();
  try {
    if (isEditMode.value) {
      await updateProjectApi(currentId.value, values);
      ElMessage.success('更新成功');
    } else {
      await createProjectApi(values);
      ElMessage.success('创建成功');
    }
    dialogVisible.value = false;
    gridApi.reload();
    formApi.resetForm();
  } catch (error) {
    // error handled by request interceptor
  }
}

function handleViewResults(row: any) {
  router.push({
    name: 'CodeScanResults',
    query: { projectId: row.id }
  });
}

function copyProjectKey(key: string) {
    copy(key);
    ElMessage.success('Project Key 已复制');
}
</script>

<template>
  <Page title="Code Scan 项目管理" auto-content-height>
    <template #extra>
      <ElButton type="primary" @click="handleCreate">新建项目</ElButton>
    </template>

    <Grid>
      <template #project_key="{ row }">
            <div class="flex items-center gap-2">
                <span>{{ row.project_key }}</span>
                <ElButton size="small" link @click="copyProjectKey(row.project_key)">复制</ElButton>
            </div>
      </template>
      <template #action="{ row }">
        <ElButton type="primary" link @click="handleViewResults(row)">查看结果</ElButton>
        <ElButton type="primary" link @click="handleEdit(row)">编辑</ElButton>
      </template>
    </Grid>

    <ElDialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <Form />
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" @click="submitForm">确定</ElButton>
      </template>
    </ElDialog>
  </Page>
</template>
