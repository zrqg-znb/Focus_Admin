<script setup lang="ts">
import type { CodeScanTaskLogRow } from './data';

import type { ScanProjectItem } from '#/api/code_scan';

import { onMounted, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElDialog,
  ElEmpty,
  ElInput,
  ElOption,
  ElSelect,
  ElTag,
} from 'element-plus';

import { listProjectsApi, listTasksApi } from '#/api/code_scan';
import { useZqTable } from '#/components/zq-table';

import { STATUS_OPTIONS, TOOL_OPTIONS, useColumns } from './data';

defineOptions({ name: 'CodeScanTaskLog' });

const projectId = ref('');
const toolName = ref('');
const taskStatus = ref('');
const projectOptions = ref<Array<{ id: string; name: string }>>([]);
const projectNameMap = ref<Record<string, string>>({});
const detailVisible = ref(false);
const currentRow = ref<CodeScanTaskLogRow | null>(null);

const [Grid, gridApi] = useZqTable({
  gridOptions: {
    border: true,
    stripe: true,
    columns: useColumns(),
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({ page }) => {
          const res = await listTasksApi(projectId.value || undefined, {
            page: page.currentPage,
            pageSize: page.pageSize,
            tool_name: toolName.value || undefined,
            status: taskStatus.value || undefined,
          });
          const items: CodeScanTaskLogRow[] = (res.items || []).map((item) => ({
            ...item,
            project_name: projectNameMap.value[item.project] || item.project,
          }));
          return {
            items,
            total: res.total || 0,
          };
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
      zoom: true,
    },
  },
});

function getStatusType(status?: string) {
  if (status === 'success') return 'success';
  if (status === 'processing') return 'warning';
  if (status === 'failed') return 'danger';
  return 'info';
}

async function loadProjects() {
  const res = await listProjectsApi({
    page: 1,
    pageSize: 500,
  });
  const rows = res.items || [];
  projectOptions.value = rows.map((item: ScanProjectItem) => ({
    id: item.id,
    name: item.name,
  }));
  projectNameMap.value = Object.fromEntries(
    rows.map((item: ScanProjectItem) => [item.id, item.name]),
  );
}

function openDetail(row: CodeScanTaskLogRow) {
  currentRow.value = row;
  detailVisible.value = true;
}

watch([projectId, toolName, taskStatus], () => {
  gridApi.reload();
});

onMounted(async () => {
  await loadProjects();
  gridApi.reload();
});
</script>

<template>
  <Page title="任务解析历史日志" auto-content-height>
    <div class="flex h-full min-h-0 flex-col">
      <div class="min-h-0 flex-1">
        <Grid class="h-full">
          <template #toolbar-actions>
            <div class="flex flex-wrap items-center gap-3">
              <ElSelect
                v-model="projectId"
                clearable
                filterable
                placeholder="项目（默认全部）"
                style="width: 260px"
              >
                <ElOption
                  v-for="item in projectOptions"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id"
                />
              </ElSelect>
              <ElSelect
                v-model="toolName"
                clearable
                filterable
                placeholder="工具（默认全部）"
                style="width: 200px"
              >
                <ElOption
                  v-for="item in TOOL_OPTIONS"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </ElSelect>
              <ElSelect
                v-model="taskStatus"
                clearable
                placeholder="状态（默认全部）"
                style="width: 180px"
              >
                <ElOption
                  v-for="item in STATUS_OPTIONS"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </ElSelect>
            </div>
          </template>

          <template #cell-status="{ row }">
            <ElTag :type="getStatusType(row.status)">{{ row.status }}</ElTag>
          </template>

          <template #cell-log="{ row }">
            <span class="line-clamp-2">{{ row.log || '-' }}</span>
          </template>

          <template #cell-actions="{ row }">
            <ElButton link type="primary" @click="openDetail(row)">
              详情
            </ElButton>
          </template>
        </Grid>
      </div>
    </div>

    <ElDialog v-model="detailVisible" title="任务解析详情" width="760px">
      <template v-if="currentRow">
        <div class="space-y-3">
          <div class="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span class="text-gray-500">任务ID：</span>
              <span>{{ currentRow.id }}</span>
            </div>
            <div>
              <span class="text-gray-500">项目：</span>
              <span>{{ currentRow.project_name }}</span>
            </div>
            <div>
              <span class="text-gray-500">工具：</span>
              <span>{{ currentRow.tool_name }}</span>
            </div>
            <div>
              <span class="text-gray-500">状态：</span>
              <ElTag :type="getStatusType(currentRow.status)">
                {{ currentRow.status }}
              </ElTag>
            </div>
            <div>
              <span class="text-gray-500">扫描时间：</span>
              <span>{{ currentRow.scan_time || '-' }}</span>
            </div>
            <div>
              <span class="text-gray-500">完成时间：</span>
              <span>{{ currentRow.processed_time || '-' }}</span>
            </div>
          </div>

          <div>
            <div class="mb-1 text-sm text-gray-500">报告文件</div>
            <ElInput :model-value="currentRow.report_file || '-'" readonly />
          </div>

          <div>
            <div class="mb-1 text-sm text-gray-500">解析日志</div>
            <ElInput
              :autosize="{ minRows: 6, maxRows: 16 }"
              :model-value="currentRow.log || '-'"
              readonly
              type="textarea"
            />
          </div>
        </div>
      </template>
      <ElEmpty v-else description="暂无任务详情" />
      <template #footer>
        <ElButton @click="detailVisible = false">关闭</ElButton>
      </template>
    </ElDialog>
  </Page>
</template>
