<script lang="ts" setup>
import type {
  FailureModeDictOptions,
  FailureModeItem,
  FailureModePayload,
  FailureModeSubsystemConfigOptions,
} from '#/api/failure_mode';
import type {
  FailureModeRoleAssignmentItem,
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
  ElInput,
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
  deleteTaskFailureModeDraftApi,
  getTaskApi,
  getTaskFailureModesApi,
  listProductFailureModesApi,
  listProductRoleAssignmentsApi,
  listTaskLogsApi,
  quickCreateTaskFailureModeApi,
  reassignTaskApi,
  saveTaskFailureModeDraftApi,
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

const TASK_CHANGE_TYPE_LABEL_MAP: Record<string, string> = {
  baseline: '当前基线',
  delete_candidate: '待删除',
  edited: '已有条目已修订',
  new: '本任务新增',
};

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const currentUserId = userStore.userInfo?.id;

const taskId = computed(() => String(route.params.id || ''));
const loading = ref(false);
const actionLoading = ref(false);
const activeTab = ref('workbench');

const currentTask = ref<FailureModeTaskItem | null>(null);
const boundFailureModes = ref<FailureModeItem[]>([]);
const baselineFailureModes = ref<ProductFailureModeItem[]>([]);
const taskLogs = ref<FailureModeTaskLogItem[]>([]);
const roleAssignments = ref<FailureModeRoleAssignmentItem[]>([]);
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

const activeStep = computed(() => {
  const status = currentTask.value?.status;
  if (status === 'CREATED') return 0;
  if (status === 'PROCESSING') return 1;
  if (status === 'REVIEWING') return 2;
  if (status === 'CLOSED') return 4;
  return 0;
});

const isReviseTask = computed(() => currentTask.value?.task_type === 'REVISE');
const isDeleteTask = computed(() => currentTask.value?.task_type === 'DELETE');

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

const canManageBinding = computed(() => canEdit.value && !isDeleteTask.value);
const canQuickCreate = computed(() => canEdit.value && !isDeleteTask.value);
const canSelectDelete = computed(() => canEdit.value && isDeleteTask.value);

const selectedDeleteRows = computed(() =>
  boundFailureModes.value.filter(
    (item) => item.task_change_type === 'delete_candidate',
  ),
);

const assigneeOptions = computed(() => {
  const task = currentTask.value;
  if (!task) {
    return [];
  }
  const seen = new Set<string>();
  return roleAssignments.value
    .filter(
      (item) => item.role === 'feature_se' && item.subsystem === task.subsystem,
    )
    .filter((item) => {
      if (seen.has(item.user_id)) {
        return false;
      }
      seen.add(item.user_id);
      return true;
    })
    .map((item) => ({
      label: formatUserName(item.user_info),
      value: item.user_id,
    }));
});

const workbenchSummary = computed(() => {
  if (isDeleteTask.value) {
    return `当前基线 ${boundFailureModes.value.length} 条，已选择待删除 ${selectedDeleteRows.value.length} 条`;
  }
  if (isReviseTask.value) {
    const editedCount = boundFailureModes.value.filter(
      (item) => item.has_task_draft,
    ).length;
    return `当前工作集 ${boundFailureModes.value.length} 条，其中已修订 ${editedCount} 条`;
  }
  return `当前工作集 ${boundFailureModes.value.length} 条，可继续绑定已有故障模式或快速新增`;
});

const workbenchColumns = useFailureModeColumns().map((column) =>
  column.key === 'actions'
    ? { ...column, cellSlotName: 'cell-actions', width: 180 }
    : column,
) as ZqTableGridOptions<FailureModeItem>['columns'];

const [FailureModeGrid, failureModeGridApi] = useZqTable<FailureModeItem>({
  gridOptions: {
    border: true,
    columns: workbenchColumns,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async () => ({
          items: boundFailureModes.value,
          total: boundFailureModes.value.length,
        }),
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

function formatUserName(
  user?: null | {
    id?: null | string;
    name?: null | string;
    username?: null | string;
  },
) {
  return user?.name || user?.username || user?.id || '-';
}

function getTaskChangeLabel(row: FailureModeItem) {
  return row.task_change_type
    ? TASK_CHANGE_TYPE_LABEL_MAP[row.task_change_type] || row.task_change_type
    : '';
}

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
    boundFailureModes.value = failureModes as FailureModeItem[];
    taskLogs.value = logs as FailureModeTaskLogItem[];
    roleAssignments.value = assignments as FailureModeRoleAssignmentItem[];
    baselineFailureModes.value = baselineItems as ProductFailureModeItem[];
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
  const task = currentTask.value;
  if (!task) {
    return;
  }

  if (isDeleteTask.value) {
    transferDialogRef.value?.open({
      title: '选择待删除故障模式',
      sourceTitle: '当前生效基线',
      confirmButtonText: '保存删除集合',
      localRows: [...boundFailureModes.value],
      selectedIds: selectedDeleteRows.value.map((item) => item.id),
      selectedItems: [...selectedDeleteRows.value],
    });
    return;
  }

  transferDialogRef.value?.open({
    title: isReviseTask.value ? '绑定已有故障模式' : '选择故障模式',
    sourceTitle: '全局故障模式库',
    confirmButtonText: '确定保存',
    selectedIds: boundFailureModes.value.map((item) => item.id),
    selectedItems: [...boundFailureModes.value],
    extraFilters: { subsystem: task.subsystem },
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
    ElMessage.success(
      isDeleteTask.value ? '待删除集合已更新' : '任务工作集已更新',
    );
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

function quickCreateHandler(payload: FailureModePayload) {
  if (!currentTask.value) {
    return Promise.reject(new Error('当前任务不存在'));
  }
  return quickCreateTaskFailureModeApi(currentTask.value.id, payload);
}

function draftUpdateHandler(id: string, payload: FailureModePayload) {
  if (!currentTask.value) {
    return Promise.reject(new Error('当前任务不存在'));
  }
  return saveTaskFailureModeDraftApi(currentTask.value.id, id, payload);
}

function handleEditFailureMode(row: FailureModeItem) {
  failureModeDrawerRef.value?.openEdit(row);
}

async function handleDeleteDraft(row: FailureModeItem) {
  if (!currentTask.value) {
    return;
  }
  actionLoading.value = true;
  try {
    await deleteTaskFailureModeDraftApi(currentTask.value.id, row.id);
    ElMessage.success('已撤销该条目的修订草稿');
    await loadTaskContext();
  } finally {
    actionLoading.value = false;
  }
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
      review_minutes_html:
        reviewForm.review_minutes_html.trim() || '<p>评审通过</p>',
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
          <div class="min-w-0 flex-1">
            <div
              class="mb-2 flex flex-col justify-between gap-4 lg:flex-row lg:items-center"
            >
              <div class="flex flex-wrap items-center gap-3">
                <ElButton plain size="small" @click="handleBack">返回</ElButton>
                <span
                  class="max-w-[300px] truncate text-xl font-bold text-gray-900 sm:max-w-[400px]"
                >
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

              <div class="flex flex-wrap gap-3">
                <ElButton
                  v-if="canAccept"
                  type="primary"
                  :loading="actionLoading"
                  @click="handleAcceptTask"
                >
                  接收任务
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
              <div
                class="col-span-1 flex items-center sm:col-span-2 md:col-span-3 xl:col-span-2"
              >
                <span class="w-20 shrink-0 text-gray-400">任务编号：</span>
                <span
                  class="truncate font-medium text-gray-900"
                  :title="currentTask?.task_no || '-'"
                >
                  {{ currentTask?.task_no || '-' }}
                </span>
              </div>
              <div class="flex items-center">
                <span class="w-20 shrink-0 text-gray-400">任务类型：</span>
                <span class="truncate font-medium text-gray-900">
                  {{
                    currentTask?.task_type
                      ? FM_TASK_TYPE_LABEL_MAP[currentTask.task_type] ||
                        currentTask.task_type
                      : '-'
                  }}
                </span>
              </div>
              <div class="flex items-center">
                <span class="w-20 shrink-0 text-gray-400">产品：</span>
                <span class="truncate font-medium text-gray-900">
                  {{ currentTask?.product_name || '-' }}
                </span>
              </div>
              <div class="flex items-center">
                <span class="w-20 shrink-0 text-gray-400">子系统：</span>
                <span class="truncate font-medium text-gray-900">
                  {{ currentTask?.subsystem || '-' }}
                </span>
              </div>
              <div class="flex items-center">
                <span class="w-20 shrink-0 text-gray-400">创建人：</span>
                <span class="truncate font-medium text-gray-900">
                  {{ formatUserName(currentTask?.creator_info) }}
                </span>
              </div>
              <div class="flex items-center">
                <span class="w-20 shrink-0 text-gray-400">责任人：</span>
                <span class="truncate font-medium text-gray-900">
                  {{ formatUserName(currentTask?.assignee_info) }}
                </span>
              </div>
            </div>

            <div class="flex w-full justify-center">
              <ElSteps
                :active="activeStep"
                align-center
                class="mx-auto w-full max-w-2xl pt-1"
                finish-status="success"
                style="--el-step-icon-size: 24px"
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
              <div class="min-h-0 flex-1 rounded-xl border bg-white p-2">
                <FailureModeGrid>
                  <template #table-title>
                    <div class="min-w-0">
                      <div class="text-sm font-semibold text-gray-900">
                        梳理工作台
                      </div>
                      <div class="mt-1 text-xs text-gray-500">
                        {{ workbenchSummary }}
                      </div>
                    </div>
                  </template>

                  <template #toolbar-actions>
                    <div class="flex flex-1 flex-wrap items-center gap-2">
                      <div class="flex-1"></div>

                      <template v-if="canReassign">
                        <ElSelect
                          v-model="reassignUserId"
                          class="w-[220px]"
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
                          plain
                          type="warning"
                          :loading="actionLoading"
                          @click="handleReassignTask"
                        >
                          改派责任人
                        </ElButton>
                      </template>

                      <ElButton
                        v-if="canManageBinding"
                        plain
                        type="primary"
                        @click="handleManageFailureModes"
                      >
                        {{ isReviseTask ? '绑定已有' : '管理绑定' }}
                      </ElButton>
                      <ElButton
                        v-if="canSelectDelete"
                        plain
                        type="danger"
                        @click="handleManageFailureModes"
                      >
                        选择待删除条目
                      </ElButton>
                      <ElButton
                        v-if="canQuickCreate"
                        plain
                        type="success"
                        @click="handleQuickCreateFailureMode"
                      >
                        快速新增故障模式
                      </ElButton>
                      <ElButton
                        v-if="canSubmit"
                        type="success"
                        :loading="actionLoading"
                        @click="handleSubmitTask"
                      >
                        提交评审
                      </ElButton>
                    </div>
                  </template>

                  <template #cell-status="{ row }">
                    <div class="text-sm text-gray-700">
                      {{ row.status || '-' }}
                    </div>
                    <div
                      v-if="getTaskChangeLabel(row)"
                      class="mt-1 text-xs text-gray-500"
                    >
                      {{ getTaskChangeLabel(row) }}
                    </div>
                  </template>

                  <template #cell-source-task-no="{ row }">
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
                        ?.map((item) => formatUserName(item))
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
                        {{ item.label }}
                      </div>
                    </div>
                    <span v-else class="text-gray-400">-</span>
                  </template>

                  <template #cell-actions="{ row }">
                    <div
                      v-if="isReviseTask && canEdit"
                      class="flex items-center justify-center gap-2"
                    >
                      <ElButton
                        link
                        type="primary"
                        @click="handleEditFailureMode(row)"
                      >
                        编辑
                      </ElButton>
                      <ElButton
                        v-if="row.has_task_draft"
                        link
                        type="warning"
                        @click="handleDeleteDraft(row)"
                      >
                        撤销修订
                      </ElButton>
                    </div>
                    <span v-else class="text-gray-400">-</span>
                  </template>
                </FailureModeGrid>
              </div>
            </div>
          </ElTabPane>

          <ElTabPane label="流程记录" name="flow">
            <div class="flex h-full min-h-0 flex-col">
              <div v-if="taskLogs.length === 0" class="py-12">
                <ElEmpty description="暂无流程记录" />
              </div>
              <div v-else class="flex-1 space-y-3 overflow-y-auto pb-2 pr-2">
                <div
                  v-for="item in taskLogs"
                  :key="item.id"
                  class="rounded-xl border bg-gray-50 p-4"
                >
                  <div
                    class="flex flex-wrap items-center justify-between gap-2"
                  >
                    <div class="font-medium text-gray-900">
                      {{ item.note || item.action }}
                    </div>
                    <div class="text-sm text-gray-500">
                      {{ item.sys_create_datetime || '-' }}
                    </div>
                  </div>
                  <div class="mt-2 text-sm text-gray-600">
                    操作人：{{ formatUserName(item.operator_info) }}
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
            <div class="flex h-full min-h-0 flex-col gap-4">
              <div class="rounded-xl border border-gray-100 bg-gray-50/50 p-4">
                <div class="mb-3 text-base font-semibold text-gray-800">
                  评审纪要
                </div>
                <ElInput
                  v-model="reviewForm.review_minutes_html"
                  :autosize="{ minRows: 5, maxRows: 10 }"
                  :disabled="isClosed"
                  placeholder="请输入评审结论、会议纪要与基线说明"
                  type="textarea"
                />
              </div>

              <div
                class="shrink-0 rounded-xl border border-gray-100 bg-gray-50/50 p-4"
              >
                <div class="mb-3 text-base font-semibold text-gray-800">
                  评审附件
                </div>
                <div
                  class="max-h-[160px] overflow-y-auto rounded-lg bg-white p-2 shadow-sm"
                >
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
      :update-handler="isReviseTask && canEdit ? draftUpdateHandler : undefined"
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
  margin-top: 2px;
  padding-right: 10%;
  font-size: 12px;
}
</style>
