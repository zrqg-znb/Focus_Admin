<script lang="ts" setup>
import type { FailureModeTaskItem } from '#/api/failure_mode_workflow';

import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { useUserStore } from '@vben/stores';

import {
  ElButton,
  ElInput,
  ElOption,
  ElSelect,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus';

import { listTasksApi } from '#/api/failure_mode_workflow';
import { useZqTable } from '#/components/zq-table';

import TaskCreateDrawer from '../workflow/tasks/components/TaskCreateDrawer.vue';
import {
  FM_TASK_STATUS_LABEL_MAP,
  FM_TASK_STATUS_OPTIONS,
  FM_TASK_TYPE_LABEL_MAP,
  getTaskStatusTagType,
  useTaskColumns,
} from './data';

defineOptions({ name: 'FailureModeTaskManagement' });

const router = useRouter();
const userStore = useUserStore();
const currentUserId = userStore.userInfo?.id;

const activeScope = ref<'all' | 'created' | 'todo'>('todo');
const keyword = ref('');
const statusFilter = ref('');
const productFilter = ref('');
const subsystemFilter = ref('');
const products = ref<string[]>([]);
const subsystems = ref<string[]>([]);
const taskRows = ref<FailureModeTaskItem[]>([]);
const taskCreateDrawerRef = ref<InstanceType<typeof TaskCreateDrawer>>();

function getUserNames(
  value?:
    | FailureModeTaskItem['assignee_info']
    | FailureModeTaskItem['creator_info'],
) {
  if (!value) {
    return [];
  }
  const items = Array.isArray(value) ? value : [value];
  return items
    .map((item) => item?.name || item?.username || item?.id || '')
    .filter(Boolean);
}

function formatUserNames(
  value?:
    | FailureModeTaskItem['assignee_info']
    | FailureModeTaskItem['creator_info'],
) {
  const labels = getUserNames(value);
  return labels.length > 0 ? labels.join(' / ') : '-';
}

const [TaskGrid, taskGridApi] = useZqTable<FailureModeTaskItem>({
  gridOptions: {
    border: true,
    columns: useTaskColumns(),
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async () => {
          const rows = await listTasksApi({
            status: statusFilter.value || undefined,
          });
          taskRows.value = rows;
          products.value = [
            ...new Set(rows.map((item) => item.product_name).filter(Boolean)),
          ];
          subsystems.value = [
            ...new Set(rows.map((item) => item.subsystem).filter(Boolean)),
          ];

          const normalizedKeyword = keyword.value.trim().toLowerCase();
          const filtered = rows.filter((item) => {
            if (
              activeScope.value === 'todo' &&
              (item.assignee_id !== currentUserId || item.status === 'CLOSED')
            ) {
              return false;
            }
            if (
              activeScope.value === 'created' &&
              item.creator_id !== currentUserId
            ) {
              return false;
            }
            if (
              productFilter.value &&
              item.product_name !== productFilter.value
            ) {
              return false;
            }
            if (
              subsystemFilter.value &&
              item.subsystem !== subsystemFilter.value
            ) {
              return false;
            }
            if (!normalizedKeyword) {
              return true;
            }
            return [
              item.task_no,
              item.name,
              item.product_name,
              item.subsystem,
              ...getUserNames(item.creator_info),
              ...getUserNames(item.assignee_info),
            ]
              .filter(Boolean)
              .some((value) =>
                String(value || '')
                  .toLowerCase()
                  .includes(normalizedKeyword),
              );
          });
          return { items: filtered as any, total: filtered.length };
        },
      },
    },
    rowKey: 'id',
    stripe: true,
    toolbarConfig: {
      custom: true,
      refresh: true,
      search: false,
      zoom: true,
    },
  },
});

const scopeCounts = computed(() => ({
  all: taskRows.value.length,
  created: taskRows.value.filter((item) => item.creator_id === currentUserId)
    .length,
  todo: taskRows.value.filter(
    (item) => item.assignee_id === currentUserId && item.status !== 'CLOSED',
  ).length,
}));

async function handleSearch() {
  taskGridApi.pagination.currentPage = 1;
  await taskGridApi.query();
}

function handleReset() {
  activeScope.value = 'todo';
  keyword.value = '';
  statusFilter.value = '';
  productFilter.value = '';
  subsystemFilter.value = '';
  handleSearch();
}

function handleCreateTask() {
  taskCreateDrawerRef.value?.open();
}

function handleOpenTask(row: FailureModeTaskItem) {
  router.push(`/failure-mode/tasks/detail/${row.id}`);
}
</script>

<template>
  <Page content-class="flex h-full min-h-0 flex-col" auto-content-height>
    <div class="flex min-h-0 flex-1 flex-col gap-4">
      <div class="rounded-xl bg-white p-4 shadow-sm">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <ElTabs v-model="activeScope" @tab-change="handleSearch">
            <ElTabPane :label="`我的待办 (${scopeCounts.todo})`" name="todo" />
            <ElTabPane
              :label="`我发起的 (${scopeCounts.created})`"
              name="created"
            />
            <ElTabPane :label="`全部任务 (${scopeCounts.all})`" name="all" />
          </ElTabs>
          <ElButton type="primary" @click="handleCreateTask">发起任务</ElButton>
        </div>

        <div
          class="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1.2fr)_180px_180px_180px_140px]"
        >
          <ElInput
            v-model="keyword"
            clearable
            placeholder="搜索任务编号、任务名称、产品、责任人"
            @keyup.enter="handleSearch"
          />
          <ElSelect
            v-model="statusFilter"
            clearable
            placeholder="任务状态"
            @change="handleSearch"
          >
            <ElOption
              v-for="item in FM_TASK_STATUS_OPTIONS"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
          <ElSelect
            v-model="productFilter"
            clearable
            filterable
            placeholder="产品"
            @change="handleSearch"
          >
            <ElOption
              v-for="item in products"
              :key="item"
              :label="item"
              :value="item"
            />
          </ElSelect>
          <ElSelect
            v-model="subsystemFilter"
            clearable
            filterable
            placeholder="子系统"
            @change="handleSearch"
          >
            <ElOption
              v-for="item in subsystems"
              :key="item"
              :label="item"
              :value="item"
            />
          </ElSelect>
          <div class="flex items-center justify-end gap-2">
            <ElButton @click="handleReset">重置</ElButton>
            <ElButton type="primary" plain @click="handleSearch">查询</ElButton>
          </div>
        </div>
      </div>

      <div
        class="min-h-0 flex-1 overflow-hidden rounded-xl bg-white p-4 shadow-sm"
      >
        <TaskGrid>
          <template #cell-task-type="{ row }">
            <span>{{
              FM_TASK_TYPE_LABEL_MAP[row.task_type] || row.task_type
            }}</span>
          </template>
          <template #cell-status="{ row }">
            <ElTag :type="getTaskStatusTagType(row.status)">
              {{ FM_TASK_STATUS_LABEL_MAP[row.status] || row.status }}
            </ElTag>
          </template>
          <template #cell-creator="{ row }">
            <span>{{ formatUserNames(row.creator_info) }}</span>
          </template>
          <template #cell-assignee="{ row }">
            <span>{{ formatUserNames(row.assignee_info) }}</span>
          </template>
          <template #cell-actions="{ row }">
            <ElButton
              link
              size="small"
              type="primary"
              @click="handleOpenTask(row)"
            >
              {{
                row.status === 'CREATED'
                  ? '进入详情'
                  : row.status === 'PROCESSING'
                    ? '进入工作台'
                    : row.status === 'REVIEWING'
                      ? '进入评审'
                      : '查看归档'
              }}
            </ElButton>
          </template>
        </TaskGrid>
      </div>
    </div>

    <TaskCreateDrawer ref="taskCreateDrawerRef" @success="handleSearch" />
  </Page>
</template>
