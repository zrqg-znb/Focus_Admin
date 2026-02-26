<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { useClipboard } from '@vueuse/core';
import { ElButton, ElDialog, ElInput, ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  createProjectApi,
  listProjectsApi,
  updateProjectApi,
} from '#/api/code_scan';

import { getFormSchema, useColumns, useSearchFormSchema } from './data';

const router = useRouter();
const { copy } = useClipboard();

const gridOptions: any = {
  columns: useColumns(),
  height: '100%', // 强制撑满父容器
  pagerConfig: {
    enabled: true,
    pageSize: 20,
    pageSizes: [10, 20, 50, 100],
  },
  proxyConfig: {
    ajax: {
      query: async ({ page }, formValues) => {
        const res = await listProjectsApi({
          ...formValues,
          page: page.currentPage,
          pageSize: page.pageSize,
        });
        return { items: res.items, total: res.total };
      },
    },
  },
  toolbarConfig: {
    search: true,
    refresh: true,
  },
};

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions,
  formOptions: {
    schema: useSearchFormSchema(),
  },
});

// 创建/编辑项目弹窗逻辑
const dialogVisible = ref(false);
const dialogTitle = ref('新建项目');
const isEditMode = ref(false);
const currentId = ref('');
const previewPath = ref('');
const previewMatchedPrefix = ref('');
const previewChecked = ref(false);

const [Form, formApi] = useVbenForm({
  schema: getFormSchema(),
  showDefaultActions: false,
});

function normalizePath(value: string) {
  return value.trim().replaceAll('\\', '/');
}

function parsePathPrefixes(rawText: string) {
  const values = String(rawText || '')
    .split('\n')
    .map((item) => normalizePath(item))
    .filter(Boolean);
  return [...new Set(values)];
}

function handleCreate() {
  isEditMode.value = false;
  dialogTitle.value = '新建项目';
  previewPath.value = '';
  previewMatchedPrefix.value = '';
  previewChecked.value = false;
  formApi.setValues({
    name: '',
    repo_url: '',
    branch: 'master',
    description: '',
    caretaker_id: '',
    path_shield_prefixes_text: '',
  });
  dialogVisible.value = true;
}

function handleEdit(row: any) {
  isEditMode.value = true;
  dialogTitle.value = '编辑项目';
  currentId.value = row.id;
  previewPath.value = '';
  previewMatchedPrefix.value = '';
  previewChecked.value = false;
  // 回显数据
  formApi.setValues({
    name: row.name,
    repo_url: row.repo_url,
    branch: row.branch,
    description: row.description,
    caretaker_id: row.caretaker,
    path_shield_prefixes_text: Array.isArray(row.path_shield_prefixes)
      ? row.path_shield_prefixes.join('\n')
      : '',
  });
  dialogVisible.value = true;
}

async function submitForm() {
  const { valid } = await formApi.validate();
  if (!valid) return;

  const values = await formApi.getValues<any>();
  const path_shield_prefixes = parsePathPrefixes(
    values.path_shield_prefixes_text || '',
  );
  const payload = {
    ...values,
    path_shield_prefixes,
  };
  delete payload.path_shield_prefixes_text;
  try {
    if (isEditMode.value) {
      await updateProjectApi(currentId.value, payload);
      ElMessage.success('更新成功');
    } else {
      await createProjectApi(payload);
      ElMessage.success('创建成功');
    }
    dialogVisible.value = false;
    gridApi.reload();
    formApi.resetForm();
  } catch {
    // error handled by request interceptor
  }
}

function handleViewResults(row: any) {
  router.push({
    path: '/code_scan/result',
    query: { projectId: row.id },
  });
}

function handleViewTaskLogs() {
  router.push({
    path: '/code_scan/report_log',
  });
}

function copyProjectKey(key: string) {
  copy(key);
  ElMessage.success('Project Key 已复制');
}

async function handlePreviewPathRule() {
  const path = normalizePath(previewPath.value);
  previewChecked.value = true;
  previewMatchedPrefix.value = '';
  if (!path) {
    ElMessage.warning('请输入要预览的文件路径');
    return;
  }

  const values = await formApi.getValues<any>();
  const prefixes = parsePathPrefixes(values.path_shield_prefixes_text || '');
  const matched = [...prefixes]
    .sort((left, right) => right.length - left.length)
    .find((prefix) => path.startsWith(prefix));

  if (matched) {
    previewMatchedPrefix.value = matched;
    ElMessage.success(`命中前缀规则: ${matched}`);
    return;
  }
  ElMessage.info('未命中任何路径前缀规则');
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
          <ElButton size="small" link @click="copyProjectKey(row.project_key)">
            复制
          </ElButton>
        </div>
      </template>
      <template #action="{ row }">
        <ElButton type="primary" link @click="handleViewResults(row)">
          查看结果
        </ElButton>
        <ElButton type="primary" link @click="handleViewTaskLogs">
          解析日志
        </ElButton>
        <ElButton type="primary" link @click="handleEdit(row)">编辑</ElButton>
      </template>
    </Grid>

    <ElDialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <Form />
      <div class="mt-3 rounded border border-dashed border-gray-300 p-3">
        <div class="mb-2 text-sm font-medium">规则命中预览</div>
        <div class="flex items-center gap-2">
          <ElInput
            v-model="previewPath"
            placeholder="输入文件路径预览，例如：/src/generated/demo.c"
          />
          <ElButton @click="handlePreviewPathRule">预览</ElButton>
        </div>
        <div v-if="previewChecked" class="mt-2 text-xs">
          <span v-if="previewMatchedPrefix" class="text-green-600">
            命中规则：{{ previewMatchedPrefix }}
          </span>
          <span v-else class="text-gray-500">未命中任何规则</span>
        </div>
      </div>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" @click="submitForm">确定</ElButton>
      </template>
    </ElDialog>
  </Page>
</template>
