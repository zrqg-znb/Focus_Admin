<script setup lang="ts">
import type {
  ScanProjectItem,
  ScanProjectListParams,
  ScanProjectPayload,
} from '#/api/code_scan';

import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { useClipboard } from '@vueuse/core';
import {
  ElButton,
  ElDialog,
  ElInput,
  ElMessage,
  ElMessageBox,
} from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createProjectApi,
  deleteProjectApi,
  listProjectsApi,
  updateProjectApi,
} from '#/api/code_scan';
import { useZqTable } from '#/components/zq-table';

import { getFormSchema, useSearchFormSchema, useZqColumns } from './data';

defineOptions({ name: 'CodeScanProject' });

interface ProjectQueryParams {
  form?: ScanProjectListParams;
  page: {
    currentPage: number;
    pageSize: number;
  };
}

interface ScanProjectFormValues extends ScanProjectPayload {
  path_shield_prefixes_text?: string;
}

const router = useRouter();
const { copy } = useClipboard();

const [Grid, gridApi] = useZqTable({
  formOptions: {
    schema: useSearchFormSchema(),
    showCollapseButton: false,
  },
  gridOptions: {
    border: true,
    stripe: true,
    columns: useZqColumns(),
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page, form }: ProjectQueryParams) => {
          return await listProjectsApi({
            page: page.currentPage,
            pageSize: page.pageSize,
            ...form,
          });
        },
      },
    },
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [10, 20, 50, 100],
    },
    toolbarConfig: {
      custom: true,
      refresh: true,
      search: true,
      zoom: true,
    },
  },
});

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

function resetPreviewState() {
  previewPath.value = '';
  previewMatchedPrefix.value = '';
  previewChecked.value = false;
}

function handleCreate() {
  isEditMode.value = false;
  dialogTitle.value = '新建项目';
  currentId.value = '';
  resetPreviewState();
  formApi.setValues({
    name: '',
    repo_url: '',
    branch: 'master',
    description: '',
    caretaker_id: undefined,
    path_shield_prefixes_text: '',
  });
  dialogVisible.value = true;
}

function handleEdit(row: ScanProjectItem) {
  isEditMode.value = true;
  dialogTitle.value = '编辑项目';
  currentId.value = row.id;
  resetPreviewState();
  formApi.setValues({
    name: row.name,
    repo_url: row.repo_url,
    branch: row.branch,
    description: row.description || '',
    caretaker_id: row.caretaker || undefined,
    path_shield_prefixes_text: Array.isArray(row.path_shield_prefixes)
      ? row.path_shield_prefixes.join('\n')
      : '',
  });
  dialogVisible.value = true;
}

async function submitForm() {
  const { valid } = await formApi.validate();
  if (!valid) return;

  const values = await formApi.getValues<ScanProjectFormValues>();
  const payload: ScanProjectPayload = {
    branch: values.branch || 'master',
    caretaker_id: values.caretaker_id || null,
    description: values.description?.trim() || null,
    name: values.name,
    path_shield_prefixes: parsePathPrefixes(
      values.path_shield_prefixes_text || '',
    ),
    repo_url: values.repo_url,
  };

  try {
    if (isEditMode.value) {
      await updateProjectApi(currentId.value, payload);
      ElMessage.success('更新成功');
    } else {
      await createProjectApi(payload);
      ElMessage.success('创建成功');
    }
    dialogVisible.value = false;
    formApi.resetForm();
    gridApi.reload();
  } catch {
    // error handled by request interceptor
  }
}

async function handleDelete(row: ScanProjectItem) {
  try {
    await ElMessageBox.confirm(
      `确认删除项目「${row.name}」吗？删除后该项目及其扫描任务、结果、屏蔽申请都会隐藏。`,
      '删除项目',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning',
      },
    );
    await deleteProjectApi(row.id);
    ElMessage.success('删除成功');
    gridApi.reload();
  } catch {
    // 用户取消或请求失败时，由弹窗/拦截器处理
  }
}

function handleViewResults(row: ScanProjectItem) {
  router.push({
    path: '/code_scan/result',
    query: { projectId: row.id },
  });
}

function handleViewTaskLogs() {
  router.push({
    path: '/code_scan/task-log',
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

  const values = await formApi.getValues<ScanProjectFormValues>();
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
    <div class="flex h-full min-h-0 flex-col">
      <div class="min-h-0 flex-1">
        <Grid class="h-full">
          <template #toolbar-actions>
            <ElButton type="primary" @click="handleCreate">新建项目</ElButton>
            <ElButton @click="handleViewTaskLogs">解析日志</ElButton>
          </template>

          <template #cell-project_key="{ row }">
            <div class="flex items-center gap-2">
              <span class="truncate">{{ row.project_key }}</span>
              <ElButton
                size="small"
                link
                @click="copyProjectKey(row.project_key)"
              >
                复制
              </ElButton>
            </div>
          </template>

          <template #cell-actions="{ row }">
            <div class="flex items-center justify-center gap-2">
              <ElButton type="primary" link @click="handleViewResults(row)">
                查看结果
              </ElButton>
              <ElButton type="primary" link @click="handleEdit(row)">
                编辑
              </ElButton>
              <ElButton type="danger" link @click="handleDelete(row)">
                删除
              </ElButton>
            </div>
          </template>
        </Grid>
      </div>
    </div>

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
