<script lang="ts" setup>
import type {
  FailureModeDictOptions,
  FailureModeItem,
  FailureModeSubsystemConfigOptions,
} from '#/api/failure_mode';
import type {
  FailureModeTaskItem,
  FailureModeTaskLogItem,
  ProductFailureModeItem,
} from '#/api/failure_mode_workflow';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { computed, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { useUserStore } from '@vben/stores';

import {
  ElButton,
  ElEmpty,
  ElMessage,
  ElOption,
  ElSelect,
  ElStep,
  ElSteps,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus';

import {
  getFailureModeDictOptionsApi,
  getFailureModeSubsystemConfigOptionsApi,
} from '#/api/failure_mode';
import {
  acceptTaskApi,
  bindTaskFailureModesApi,
  closeTaskApi,
  getTaskApi,
  getTaskFailureModesApi,
  listProductFailureModesApi,
  listProductRoleAssignmentsApi,
  listTaskLogsApi,
  quickCreateTaskFailureModeApi,
  reassignTaskApi,
  submitTaskApi,
} from '#/api/failure_mode_workflow';
import FileSelector from '#/components/zq-form/file-selector/file-selector.vue';
import { useZqTable } from '#/components/zq-table';

import FailureModeDrawer from '../components/FailureModeDrawer.vue';
import {
  createEmptyDictOptions,
  createEmptySubsystemConfigOptions,
  formatFailureModeSourceHint,
  formatFailureModeSourceLabel,
  useFailureModeColumns,
} from '../data';
import FailureModeTransferDialog from '../workflow/tasks/components/FailureModeTransferDialog.vue';
import {
  FM_TASK_STATUS_LABEL_MAP,
  FM_TASK_TYPE_LABEL_MAP,
  getTaskStatusTagType,
} from './data';

defineOptions({ name: 'FailureModeTaskDetail' });

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const currentUserId = userStore.userInfo?.id;

const taskId = computed(() => String(route.params.id || ''));
const loading = ref(false);
const actionLoading = ref(false);
const activeTab = ref('workbench');

const activeStep = computed(() => {
  const status = currentTask.value?.status;
  if (status === 'CREATED') return 0;
  if (status === 'PROCESSING') return 1;
  if (status === 'REVIEWING') return 2;
  if (status === 'CLOSED') return 3;
  return 0;
});

const currentTask = ref<FailureModeTaskItem | null>(null);
const boundFailureModes = ref<FailureModeItem[]>([]);
const baselineFailureModes = ref<ProductFailureModeItem[]>([]);
const taskLogs = ref<FailureModeTaskLogItem[]>([]);
const roleAssignments = ref<any[]>([]);
const reassignUserId = ref('');
const transferDialogRef = ref<InstanceType<typeof FailureModeTransferDialog>>();
const failureModeDrawerRef = ref<InstanceType<typeof FailureModeDrawer>>();
const dictOptions = reactive<FailureModeDictOptions>(createEmptyDictOptions());
const subsystemConfigOptions = reactive<FailureModeSubsystemConfigOptions>(
  createEmptySubsystemConfigOptions(),
);

const reviewForm = reactive({
  review_attachment_ids: [] as string[],
  review_minutes_html: '',
});

const [FailureModeGrid, failureModeGridApi] = useZqTable<FailureModeItem>({
  gridOptions: {
    border: true,
    columns: useFailureModeColumns(),
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async () => ({
          items: boundFailureModes.value,
          total: boundFailureModes.value.length,
        }),
      },
    },
  },
});

const [BaselineGrid, baselineGridApi] = useZqTable<ProductFailureModeItem>({
  gridOptions: {
    border: true,
    columns: [
      {
        align: 'center',
        dataKey: 'subsystem',
        headerAlign: 'center',
        key: 'subsystem',
        title: '子系统',
        width: 160,
      },
      {
        align: 'center',
        dataKey: 'failure_mode_brief',
        headerAlign: 'center',
        key: 'failure_mode_brief',
        title: '当前生效故障模式',
        width: 420,
      },
      {
        align: 'center',
        dataKey: 'sys_create_datetime',
        headerAlign: 'center',
        key: 'sys_create_datetime',
        title: '生效时间',
        width: 200,
      },
    ] as ZqTableGridOptions<ProductFailureModeItem>['columns'],
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async () => ({
          items: baselineFailureModes.value,
          total: baselineFailureModes.value.length,
        }),
      },
    },
  },
});

const canAccept = computed(() => {
  return (
    currentTask.value?.status === 'CREATED' &&
    currentTask.value.assignee_id === currentUserId
  );
});

const canEdit = computed(() => {
  return (
    currentTask.value?.status === 'PROCESSING' &&
    currentTask.value.assignee_id === currentUserId
  );
});

const canSubmit = computed(() => canEdit.value);

const canReassign = computed(() => {
  return (
    currentTask.value?.status === 'CREATED' ||
    currentTask.value?.status === 'PROCESSING'
  );
});

const canClose = computed(() => currentTask.value?.status === 'REVIEWING');
const isClosed = computed(() => currentTask.value?.status === 'CLOSED');

const assigneeOptions = computed(() => {
  const task = currentTask.value;
  if (!task) {
    return [];
  }
  const seen = new Set<string>();
  return roleAssignments.value
    .filter(
      (item: any) =>
        item.role === 'feature_se' && item.subsystem === task.subsystem,
    )
    .filter((item: any) => {
      if (seen.has(item.user_id)) {
        return false;
      }
      seen.add(item.user_id);
      return true;
    })
    .map((item: any) => ({
      label: item.user_info?.name || item.user_info?.username || item.user_id,
      value: item.user_id,
    }));
});

async function loadTaskContext() {
  if (!taskId.value) {
    return;
  }
  loading.value = true;
  try {
    const detail = await getTaskApi(taskId.value);
    currentTask.value = detail;
    const [
      failureModes,
      logs,
      taskDictOptions,
      taskSubsystemOptions,
      assignments,
      baselineItems,
    ] = await Promise.all([
      getTaskFailureModesApi(taskId.value),
      listTaskLogsApi(taskId.value),
      getFailureModeDictOptionsApi(),
      getFailureModeSubsystemConfigOptionsApi(),
      listProductRoleAssignmentsApi(detail.product_id),
      listProductFailureModesApi(detail.product_id, {
        subsystem: detail.subsystem,
      }),
    ]);
    boundFailureModes.value = failureModes as any;
    taskLogs.value = logs as any;
    roleAssignments.value = assignments as any;
    baselineFailureModes.value = baselineItems as any;
    Object.assign(dictOptions, taskDictOptions);
    Object.assign(subsystemConfigOptions, taskSubsystemOptions);
    reassignUserId.value = detail.assignee_id || '';
    reviewForm.review_minutes_html = detail.review_minutes_html || '';
    reviewForm.review_attachment_ids = [
      ...(detail.review_attachment_ids || []),
    ];
    await failureModeGridApi.query();
    await baselineGridApi.query();
  } finally {
    loading.value = false;
  }
}

function handleBack() {
  router.push('/failure-mode/tasks');
}

function handleManageFailureModes() {
  if (!currentTask.value) {
    return;
  }
  transferDialogRef.value?.open({
    selectedIds: boundFailureModes.value.map((item) => item.id),
    selectedItems: [...boundFailureModes.value],
    extraFilters: { subsystem: currentTask.value.subsystem },
  });
}

async function handleTransferConfirm(payload: {
  ids: string[];
  items: FailureModeItem[];
}) {
  if (!currentTask.value) {
    return;
  }
  actionLoading.value = true;
  try {
    await bindTaskFailureModesApi(currentTask.value.id, payload.ids);
    ElMessage.success('任务绑定已更新');
    activeTab.value = 'workbench';
    await loadTaskContext();
  } finally {
    actionLoading.value = false;
  }
}

async function handleAcceptTask() {
  if (!currentTask.value) {
    return;
  }
  actionLoading.value = true;
  try {
    await acceptTaskApi(currentTask.value.id);
    ElMessage.success('任务已接收');
    await loadTaskContext();
  } finally {
    actionLoading.value = false;
  }
}

function handleQuickCreateFailureMode() {
  failureModeDrawerRef.value?.openCreate();
}

function quickCreateHandler(payload: any) {
  if (!currentTask.value) {
    return Promise.reject(new Error('当前任务不存在'));
  }
  return quickCreateTaskFailureModeApi(currentTask.value.id, payload);
}

function handleViewFailureMode(row: FailureModeItem) {
  // router.push({ name: 'FailureModeDetail', params: { id: row.id } }); // If there is a detail page
  // Actually, wait, maybe we should open FailureModeDrawer in edit/view mode.
  failureModeDrawerRef.value?.openEdit(row);
}

async function handleSubmitTask() {
  if (!currentTask.value) {
    return;
  }
  actionLoading.value = true;
  try {
    await submitTaskApi(currentTask.value.id);
    ElMessage.success('任务已提交评审');
    activeTab.value = 'review';
    await loadTaskContext();
  } finally {
    actionLoading.value = false;
  }
}

async function handleReassignTask() {
  if (!currentTask.value || !reassignUserId.value) {
    return;
  }
  actionLoading.value = true;
  try {
    await reassignTaskApi(currentTask.value.id, reassignUserId.value);
    ElMessage.success('责任人已改派');
    await loadTaskContext();
  } finally {
    actionLoading.value = false;
  }
}

async function handleCloseTask() {
  if (!currentTask.value) {
    return;
  }
  actionLoading.value = true;
  try {
    await closeTaskApi(currentTask.value.id, {
      review_minutes_html: reviewForm.review_minutes_html || '<p>评审通过</p>',
      review_attachment_ids: reviewForm.review_attachment_ids,
    });
    ElMessage.success('任务已关闭并同步基线');
    await loadTaskContext();
  } finally {
    actionLoading.value = false;
  }
}

watch(
  taskId,
  () => {
    void loadTaskContext();
  },
  { immediate: true },
);
</script>

<template>
  <Page content-class="flex h-full min-h-0 flex-col" auto-content-height>
    <div class="flex min-h-0 flex-1 flex-col gap-4">
      <div class="rounded-xl bg-white p-4 shadow-sm">
        <div
          class="flex flex-col justify-between gap-4 lg:flex-row lg:items-start"
        >
          <div class="flex-1 min-w-0">
            <div class="mb-2 flex flex-col gap-4 lg:flex-row lg:items-center justify-between">
              <div class="flex items-center gap-3 flex-wrap">
                <ElButton plain @click="handleBack" size="small">返回</ElButton>
                <span class="text-xl font-bold text-gray-900 truncate max-w-[300px] sm:max-w-[400px]">
                  {{ currentTask?.name || '任务详情' }}
                </span>
                <ElTag
                  v-if="currentTask"
                  :type="getTaskStatusTagType(currentTask.status)"
                  effect="light"
                  round
                >
                  {{
                    FM_TASK_STATUS_LABEL_MAP[currentTask.status] ||
                    currentTask.status
                  }}
                </ElTag>
              </div>
              
              <div class="flex gap-3 flex-wrap">
                <ElButton
                  v-if="canAccept"
                  type="primary"
                  :loading="actionLoading"
                  @click="handleAcceptTask"
                >
                  接收任务
                </ElButton>
                <ElButton
                  v-if="canEdit"
                  type="primary"
                  plain
                  @click="handleManageFailureModes"
                >
                  管理绑定
                </ElButton>
                <ElButton
                  v-if="canEdit"
                  type="success"
                  plain
                  @click="handleQuickCreateFailureMode"
                >
                  快速新增模式
                </ElButton>
                <ElButton
                  v-if="canSubmit"
                  type="success"
                  :loading="actionLoading"
                  @click="handleSubmitTask"
                >
                  提交评审
                </ElButton>
                <ElButton
                  v-if="canClose"
                  type="success"
                  :loading="actionLoading"
                  @click="handleCloseTask"
                >
                  评审关闭
                </ElButton>
              </div>
            </div>

            <div
              class="mb-3 grid grid-cols-1 gap-x-4 gap-y-2 text-sm text-gray-600 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-5"
            >
              <div class="flex items-center col-span-1 sm:col-span-2 md:col-span-3 xl:col-span-2">
                <span class="w-20 shrink-0 text-gray-400">任务编号：</span>
                <span class="font-medium text-gray-900 truncate" :title="currentTask?.task_no || '-'">{{
                  currentTask?.task_no || '-'
                }}</span>
              </div>
              <div class="flex items-center">
                <span class="w-20 shrink-0 text-gray-400">任务类型：</span>
                <span class="font-medium text-gray-900 truncate">{{
                  currentTask?.task_type
                    ? FM_TASK_TYPE_LABEL_MAP[currentTask.task_type] ||
                      currentTask.task_type
                    : '-'
                }}</span>
              </div>
              <div class="flex items-center">
                <span class="w-20 shrink-0 text-gray-400">产品：</span>
                <span class="font-medium text-gray-900 truncate">{{
                  currentTask?.product_name || '-'
                }}</span>
              </div>
              <div class="flex items-center">
                <span class="w-20 shrink-0 text-gray-400">子系统：</span>
                <span class="font-medium text-gray-900 truncate">{{
                  currentTask?.subsystem || '-'
                }}</span>
              </div>
              <div class="flex items-center">
                <span class="w-20 shrink-0 text-gray-400">创建人：</span>
                <span class="font-medium text-gray-900 truncate">{{
                  currentTask?.creator_info?.name ||
                  currentTask?.creator_info?.username ||
                  '-'
                }}</span>
              </div>
              <div class="flex items-center">
                <span class="w-20 shrink-0 text-gray-400">责任人：</span>
                <span class="font-medium text-gray-900 truncate">{{
                  currentTask?.assignee_info?.name ||
                  currentTask?.assignee_info?.username ||
                  '-'
                }}</span>
              </div>
            </div>

            <div class="flex justify-center w-full">
              <ElSteps
                :active="activeStep"
                finish-status="success"
                align-center
                class="w-full max-w-2xl pt-1 mx-auto"
                style="--el-step-icon-size: 24px;"
              >
                <ElStep
                  title="已创建"
                  :description="currentTask?.sys_create_datetime || '-'"
                />
                <ElStep
                  title="梳理中"
                  :description="currentTask?.accepted_at || '-'"
                />
                <ElStep
                  title="评审中"
                  :description="currentTask?.submitted_at || '-'"
                />
                <ElStep
                  title="已关闭"
                  :description="currentTask?.closed_at || '-'"
                />
              </ElSteps>
            </div>
          </div>
        </div>
      </div>

      <div
        class="flex min-h-0 flex-1 flex-col rounded-xl bg-white p-4 shadow-sm"
      >
        <ElTabs v-model="activeTab" class="failure-mode-task-detail__tabs">
          <ElTabPane label="梳理工作台" name="workbench">
            <div class="flex h-full min-h-0 flex-col gap-4">
              <div
                v-if="canReassign"
                class="grid gap-3 rounded-xl border p-4 lg:grid-cols-[200px_minmax(0,1fr)_120px]"
              >
                <div
                  class="flex items-center text-sm font-medium text-gray-700"
                >
                  改派责任人
                </div>
                <ElSelect
                  v-model="reassignUserId"
                  filterable
                  placeholder="请选择新的特性SE"
                >
                  <ElOption
                    v-for="item in assigneeOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </ElSelect>
                <ElButton
                  type="warning"
                  plain
                  :loading="actionLoading"
                  @click="handleReassignTask"
                >
                  改派
                </ElButton>
              </div>

              <div class="min-h-0 flex-1 rounded-xl border bg-white p-2">
                <FailureModeGrid>
                  <template #cell-status="{ row }">
                    <span>{{ row.status || '-' }}</span>
                  </template>
                  <template #cell-source_task_no="{ row }">
                    <div class="text-sm text-gray-700">
                      {{ formatFailureModeSourceLabel(row) }}
                    </div>
                    <div
                      v-if="formatFailureModeSourceHint(row)"
                      class="mt-1 text-xs text-gray-500"
                    >
                      {{ formatFailureModeSourceHint(row) }}
                    </div>
                  </template>
                  <template #cell-author_info="{ row }">
                    <span>{{
                      row.author_info
                        ?.map((item) => item.name || item.username)
                        .join(' / ') || '-'
                    }}</span>
                  </template>
                  <template #cell-handling_measure_items="{ row }">
                    <div
                      v-if="row.handling_measure_items?.length"
                      class="space-y-1"
                    >
                      <div
                        v-for="item in row.handling_measure_items"
                        :key="item.id"
                        class="truncate text-sm text-gray-700"
                        :title="item.label"
                      >
                        • {{ item.label }}
                      </div>
                    </div>
                    <span v-else class="text-gray-400">-</span>
                  </template>
                  <template #cell-actions="{ row }">
                    <ElButton
                      link
                      type="primary"
                      @click="handleViewFailureMode(row)"
                    >
                      查看详情
                    </ElButton>
                  </template>
                </FailureModeGrid>
              </div>
            </div>
          </ElTabPane>

          <ElTabPane label="流程记录" name="flow">
            <div class="flex h-full flex-col min-h-0">
              <div v-if="taskLogs.length === 0" class="py-12">
                <ElEmpty description="暂无流程记录" />
              </div>
              <div v-else class="flex-1 overflow-y-auto space-y-3 pr-2 pb-2">
                <div
                  v-for="item in taskLogs"
                  :key="item.id"
                  class="rounded-xl border bg-gray-50 p-4"
                >
                  <div class="flex flex-wrap items-center justify-between gap-2">
                    <div class="font-medium text-gray-900">
                      {{ item.note || item.action }}
                    </div>
                    <div class="text-sm text-gray-500">
                      {{ item.sys_create_datetime || '-' }}
                    </div>
                  </div>
                  <div class="mt-2 text-sm text-gray-600">
                    操作人：{{
                      item.operator_info?.name ||
                      item.operator_info?.username ||
                      '-'
                    }}
                  </div>
                  <div class="mt-1 text-sm text-gray-600">
                    状态：
                    {{
                      FM_TASK_STATUS_LABEL_MAP[item.from_status] ||
                      item.from_status ||
                      '-'
                    }}
                    ->
                    {{
                      FM_TASK_STATUS_LABEL_MAP[item.to_status] ||
                      item.to_status ||
                      '-'
                    }}
                  </div>
                </div>
              </div>
            </div>
          </ElTabPane>

          <ElTabPane label="评审归档" name="review">
            <div class="flex h-full flex-col min-h-0 gap-4">
              <div class="shrink-0 rounded-xl border border-gray-100 bg-gray-50/50 p-4">
                <div class="mb-3 text-base font-semibold text-gray-800">
                  评审附件
                </div>
                <div class="rounded-lg bg-white p-2 shadow-sm max-h-[160px] overflow-y-auto">
                  <FileSelector
                    v-model="reviewForm.review_attachment_ids"
                    :disabled="isClosed"
                    display-mode="list"
                    multiple
                    placeholder="点击或拖拽上传评审附件"
                  />
                </div>
              </div>

              <div
                class="flex min-h-0 flex-1 flex-col rounded-xl border border-gray-100 bg-white p-2 shadow-sm"
              >
                <div
                  class="px-3 pb-3 pt-2 text-base font-semibold text-gray-800"
                >
                  当前生效基线预览
                </div>
                <div class="min-h-0 flex-1">
                  <BaselineGrid />
                </div>
              </div>
            </div>
          </ElTabPane>
        </ElTabs>
      </div>
    </div>

    <FailureModeTransferDialog
      ref="transferDialogRef"
      @confirm="handleTransferConfirm"
    />
    <FailureModeDrawer
      ref="failureModeDrawerRef"
      :create-handler="quickCreateHandler"
      :dict-options="dictOptions"
      hide-status-field
      :subsystem-config-options="subsystemConfigOptions"
      @success="loadTaskContext"
    />
  </Page>
</template>

<style scoped>
:deep(.failure-mode-task-detail__tabs) {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
}

:deep(.failure-mode-task-detail__tabs > .el-tabs__content) {
  flex: 1;
  min-height: 0;
}

:deep(.failure-mode-task-detail__tabs .el-tab-pane) {
  height: 100%;
}

:deep(.el-step__title) {
  font-size: 13px;
  line-height: 1.2;
}

:deep(.el-step__description) {
  font-size: 12px;
  padding-right: 10%;
  margin-top: 2px;
}
</style>
