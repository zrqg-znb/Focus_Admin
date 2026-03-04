<script setup lang="ts">
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

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { listProjectsApi, listTasksApi } from '#/api/code_scan';

import { useColumns } from './data';

defineOptions({ name: 'CodeScanTaskLog' });

const TOOL_OPTIONS = [
  'tscan',
  'tsan',
  'cppcheck',
  'weggli',
  'cooddy',
  'binexplorer',
  'clang-tidy',
  'valgrind',
];

const STATUS_OPTIONS = [
  { label: '等待中', value: 'pending' },
  { label: '解析中', value: 'processing' },
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' },
];

const projectId = ref('');
const toolName = ref('');
const taskStatus = ref('');
const projectOptions = ref<Array<{ id: string; name: string }>>([]);
const projectNameMap = ref<Record<string, string>>({});
const detailVisible = ref(false);
const currentRow = ref<any>(null);

const gridOptions: any = {
  columns: useColumns(),
  height: '100%',
  pagerConfig: {
    enabled: true,
    pageSize: 20,
    pageSizes: [10, 20, 50, 100],
  },
  proxyConfig: {
    ajax: {
      query: async ({ page }) => {
        const res: any = await listTasksApi(projectId.value || undefined, {
          page: page.currentPage,
          pageSize: page.pageSize,
          tool_name: toolName.value || undefined,
          status: taskStatus.value || undefined,
        });
        const items = (res.items || []).map((item: any) => ({
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
  toolbarConfig: {
    refresh: true,
  },
};

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions,
});

function getStatusType(status?: string) {
  if (status === 'success') return 'success';
  if (status === 'processing') return 'warning';
  if (status === 'failed') return 'danger';
  return 'info';
}

async function loadProjects() {
  const res: any = await listProjectsApi({
    page: 1,
    pageSize: 500,
  });
  const rows = res.items || [];
  projectOptions.value = rows.map((item: any) => ({
    id: item.id,
    name: item.name,
  }));
  projectNameMap.value = Object.fromEntries(
    rows.map((item: any) => [item.id, item.name]),
  );
}

function openDetail(row: any) {
  currentRow.value = row;
  detailVisible.value = true;
}

watch(projectId, () => {
  gridApi.reload();
});

watch(toolName, () => {
  gridApi.reload();
});

watch(taskStatus, () => {
  gridApi.reload();
});

onMounted(async () => {
  await loadProjects();
  gridApi.reload();
});
</script>

<template>
  <Page title="任务解析历史日志" auto-content-height>
    <Grid>
      <template #table-title>
        <div class="flex items-center gap-3">
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
          <ElButton @click="gridApi.reload()">刷新</ElButton>
        </div>
      </template>

      <template #status="{ row }">
        <ElTag :type="getStatusType(row.status)">{{ row.status }}</ElTag>
      </template>

      <template #log="{ row }">
        <span class="line-clamp-2">{{ row.log || '-' }}</span>
      </template>

      <template #action="{ row }">
        <ElButton link type="primary" @click="openDetail(row)">详情</ElButton>
      </template>
    </Grid>

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
