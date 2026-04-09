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

import { computed, nextTick, reactive, ref, shallowRef, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElEmpty,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElSelect,
  ElStep,
  ElSteps,
  ElTabPane,
  ElTabs,
  ElTag,
  ElTimeline,
  ElTimelineItem,
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
  getTaskFailureModeLandingApi,
  getTaskFailureModesApi,
  listProductFailureModesApi,
  listProductRoleAssignmentsApi,
  listTaskLogsApi,
  quickCreateTaskFailureModeApi,
  reassignTaskApi,
  recallTaskApi,
  rejectTaskApi,
  saveTaskFailureModeDraftApi,
  saveTaskFailureModeLandingApi,
  submitTaskApi,
  updateTaskFailureModeApi,
} from '#/api/failure_mode_workflow';
import FileSelector from '#/components/zq-form/file-selector/file-selector.vue';
import { useZqTable } from '#/components/zq-table';

import FailureModeDrawer from '../components/FailureModeDrawer.vue';
import {
  createEmptyDictOptions,
  createEmptySubsystemConfigOptions,
  formatFailureModeSourceHint,
  formatFailureModeSourceLabel,
  formatTextList,
  useFailureModeColumns,
} from '../data';
import FailureModeTransferDialog from '../workflow/tasks/components/FailureModeTransferDialog.vue';
import LandingConfigDrawer from '../workflow/tasks/components/LandingConfigDrawer.vue';
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

const taskId = computed(() => String(route.params.id || ''));
const loading = ref(false);
const actionLoading = ref(false);
const activeTab = ref('workbench');

const currentTask = ref<FailureModeTaskItem | null>(null);
const boundFailureModes = shallowRef<FailureModeItem[]>([]);
const baselineFailureModes = shallowRef<ProductFailureModeItem[]>([]);
const taskLogs = ref<FailureModeTaskLogItem[]>([]);
const roleAssignments = ref<FailureModeRoleAssignmentItem[]>([]);
const reassignUserId = ref('');
const transferDialogRef = ref<InstanceType<typeof FailureModeTransferDialog>>();
const failureModeDrawerRef = ref<InstanceType<typeof FailureModeDrawer>>();
const landingConfigDrawerRef = ref<InstanceType<typeof LandingConfigDrawer>>();
const editingFailureModeRow = ref<FailureModeItem | null>(null);
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
const availableActions = computed(
  () => new Set(currentTask.value?.available_actions || []),
);

const canAccept = computed(() => availableActions.value.has('accept'));
const canEdit = computed(() => availableActions.value.has('bind'));
const canSubmit = computed(() => availableActions.value.has('submit'));
const canReassign = computed(() => availableActions.value.has('reassign'));
const canRecall = computed(() => availableActions.value.has('recall'));
const canReject = computed(() => availableActions.value.has('reject'));
const canClose = computed(() => availableActions.value.has('close'));
const isClosed = computed(() => currentTask.value?.status === 'CLOSED');

const canManageBinding = computed(() => canEdit.value && !isDeleteTask.value);
const canQuickCreate = computed(
  () => availableActions.value.has('quick_create') && !isDeleteTask.value,
);
const canSelectDelete = computed(() => canEdit.value && isDeleteTask.value);
const canMaintainLanding = computed(
  () =>
    canEdit.value &&
    currentTask.value?.status === 'PROCESSING' &&
    !isDeleteTask.value,
);

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

const latestReviewFeedback = computed(() => {
  const record = taskLogs.value.find((item) =>
    ['recall', 'reject'].includes(item.action),
  );
  if (!record) {
    return '-';
  }
  return record.extra_data?.reason || record.note || '-';
});

const workbenchColumns = ((useFailureModeColumns() || []).map((column) =>
  column?.key === 'actions'
    ? { ...column, cellSlotName: 'cell-actions', width: 320 }
    : column,
) || []) as ZqTableGridOptions<FailureModeItem>['columns'];

function cloneFailureModeRows(items: FailureModeItem[]) {
  return items.map((item) => ({
    ...item,
    chips: [...(item.chips || [])],
    fault_categories: [...(item.fault_categories || [])],
    symptoms: [...(item.symptoms || [])],
    author_ids: [...(item.author_ids || [])],
    author_info: [...(item.author_info || [])],
    related_dts_nos: [...(item.related_dts_nos || [])],
    required_handling_measure_categories: [
      ...(item.required_handling_measure_categories || []),
    ],
    required_observation_method_types: [
      ...(item.required_observation_method_types || []),
    ],
    interception_strategy_ids: [...(item.interception_strategy_ids || [])],
    interception_strategy_items: [...(item.interception_strategy_items || [])],
    handling_measure_ids: [...(item.handling_measure_ids || [])],
    handling_measure_items: [...(item.handling_measure_items || [])],
    observation_method_ids: [...(item.observation_method_ids || [])],
    observation_method_items: [...(item.observation_method_items || [])],
    huatuo_diagnosis_ids: [...(item.huatuo_diagnosis_ids || [])],
    huatuo_diagnosis_items: [...(item.huatuo_diagnosis_items || [])],
  }));
}

function cloneBaselineRows(items: ProductFailureModeItem[]) {
  return items.map((item) => ({ ...item }));
}

function paginateRows<T extends Record<string, any>>(
  rows: T[],
  page?: { currentPage?: number; pageSize?: number },
) {
  const currentPage = Math.max(1, Number(page?.currentPage || 1));
  const pageSize = Math.max(1, Number(page?.pageSize || 20));
  const start = (currentPage - 1) * pageSize;
  return rows.slice(start, start + pageSize);
}

const [FailureModeGrid, failureModeGridApi] = useZqTable<FailureModeItem>({
  gridOptions: {
    border: true,
    columns: workbenchColumns,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({
          page,
        }: {
          page?: { currentPage?: number; pageSize?: number };
        }) => {
          const rows = cloneFailureModeRows(boundFailureModes.value);
          return {
            items: paginateRows(rows, page),
            total: rows.length,
          };
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
        query: async ({
          page,
        }: {
          page?: { currentPage?: number; pageSize?: number };
        }) => {
          const rows = cloneBaselineRows(baselineFailureModes.value);
          return {
            items: paginateRows(rows, page),
            total: rows.length,
          };
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

const TASK_LOG_ACTION_LABEL_MAP: Record<string, string> = {
  accept: '接收任务',
  bind_failure_modes: '维护任务工作集',
  close: '评审关闭',
  create: '创建任务',
  delete_draft: '撤销修订草稿',
  edit_failure_mode: '编辑任务内故障模式',
  quick_create_failure_mode: '任务内快速新增故障模式',
  recall: '撤回评审',
  reassign: '改派责任人',
  reject: '评审驳回',
  save_landing: '保存落地配置',
  save_draft: '保存修订草稿',
  submit: '提交评审',
};

function formatUserName(
  user?:
    | null
    | {
        id?: null | string;
        name?: null | string;
        username?: null | string;
      }
    | {
        id?: null | string;
        name?: null | string;
        username?: null | string;
      }[],
) {
  if (!user) {
    return '-';
  }
  const items = Array.isArray(user) ? user : [user];
  const labels = items
    .map((item) => item?.name || item?.username || item?.id || '')
    .filter(Boolean);
  return labels.length > 0 ? labels.join(' / ') : '-';
}

function getTaskLogColor(item: FailureModeTaskLogItem) {
  if (item.to_status === 'CLOSED') {
    return '#16a34a';
  }
  if (item.to_status === 'REVIEWING') {
    return '#d97706';
  }
  if (item.to_status === 'PROCESSING') {
    return '#2563eb';
  }
  return '#94a3b8';
}

function getTaskLogTitle(item: FailureModeTaskLogItem) {
  return TASK_LOG_ACTION_LABEL_MAP[item.action] || item.note || item.action;
}

function getTaskChangeLabel(row: FailureModeItem) {
  return row.task_change_type
    ? TASK_CHANGE_TYPE_LABEL_MAP[row.task_change_type] || row.task_change_type
    : '';
}

function formatDate(dateStr?: null | string) {
  if (!dateStr) return '-';
  try {
    const date = new Date(dateStr);
    if (Number.isNaN(date.getTime())) return dateStr;
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}\n${pad(date.getHours())}:${pad(date.getMinutes())}`;
  } catch {
    return dateStr;
  }
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
    await nextTick();
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
  editingFailureModeRow.value = null;
  failureModeDrawerRef.value?.openCreate();
}

function quickCreateHandler(payload: FailureModePayload) {
  if (!currentTask.value) {
    return Promise.reject(new Error('当前任务不存在'));
  }
  return quickCreateTaskFailureModeApi(currentTask.value.id, payload);
}

function taskFailureModeUpdateHandler(id: string, payload: FailureModePayload) {
  if (!currentTask.value) {
    return Promise.reject(new Error('当前任务不存在'));
  }
  const taskEditMode = editingFailureModeRow.value?.task_edit_mode;
  if (taskEditMode === 'draft') {
    return saveTaskFailureModeDraftApi(currentTask.value.id, id, payload);
  }
  if (taskEditMode === 'direct_update') {
    return updateTaskFailureModeApi(currentTask.value.id, id, payload);
  }
  return Promise.reject(new Error('当前故障模式不支持编辑'));
}

function handleEditFailureMode(row: FailureModeItem) {
  editingFailureModeRow.value = row;
  failureModeDrawerRef.value?.openEdit(row);
}

function handleViewFailureMode(row: FailureModeItem) {
  editingFailureModeRow.value = null;
  failureModeDrawerRef.value?.openView(row);
}

async function handleFailureModeSaved() {
  editingFailureModeRow.value = null;
  await loadTaskContext();
}

function handleOpenLandingConfig(row: FailureModeItem) {
  if (!currentTask.value) {
    return;
  }
  landingConfigDrawerRef.value?.open({
    taskId: currentTask.value.id,
    failureModeId: row.id,
    failureModeBrief: row.brief,
    productName: currentTask.value.product_name,
    subsystem: currentTask.value.subsystem,
    taskType:
      FM_TASK_TYPE_LABEL_MAP[currentTask.value.task_type] ||
      currentTask.value.task_type,
    taskStatus:
      FM_TASK_STATUS_LABEL_MAP[currentTask.value.status] ||
      currentTask.value.status,
  });
}

function loadTaskFailureModeLanding(taskId: string, failureModeId: string) {
  return getTaskFailureModeLandingApi(taskId, failureModeId);
}

async function saveTaskFailureModeLanding(
  taskId: string,
  failureModeId: string,
  payload: Record<string, any>,
) {
  const result = await saveTaskFailureModeLandingApi(
    taskId,
    failureModeId,
    payload,
  );
  await loadTaskContext();
  return result;
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

async function handleRecallTask() {
  if (!currentTask.value) {
    return;
  }
  try {
    const { value } = await ElMessageBox.prompt(
      '如有需要可补充撤回说明，留空也可继续撤回。',
      '撤回评审',
      {
        confirmButtonText: '确认撤回',
        inputPlaceholder: '请输入撤回说明（选填）',
      },
    );
    actionLoading.value = true;
    await recallTaskApi(currentTask.value.id, { reason: value || '' });
    ElMessage.success('任务已撤回到梳理阶段');
    activeTab.value = 'workbench';
    await loadTaskContext();
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      throw error;
    }
  } finally {
    actionLoading.value = false;
  }
}

async function handleRejectTask() {
  if (!currentTask.value) {
    return;
  }
  try {
    const { value } = await ElMessageBox.prompt(
      '请输入驳回原因，任务会退回给特性 SE 继续修订。',
      '驳回任务',
      {
        confirmButtonText: '确认驳回',
        inputPlaceholder: '请输入驳回原因',
        inputValidator: (value) => (value.trim() ? true : '驳回原因不能为空'),
      },
    );
    actionLoading.value = true;
    await rejectTaskApi(currentTask.value.id, { reason: value.trim() });
    ElMessage.success('任务已驳回');
    activeTab.value = 'flow';
    await loadTaskContext();
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      throw error;
    }
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
      <div class="rounded-xl bg-white shadow-sm">
        <!-- Header -->
        <div
          class="flex flex-col gap-4 border-b border-gray-100 p-4 lg:flex-row lg:items-center lg:justify-between"
        >
          <div class="flex flex-wrap items-center gap-3">
            <ElButton plain size="small" @click="handleBack">返回</ElButton>
            <div class="hidden h-4 w-[1px] bg-gray-300 sm:block"></div>
            <span
              class="max-w-[300px] truncate text-lg font-bold text-gray-900 sm:max-w-[400px]"
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

          <!-- Actions -->
          <div class="flex flex-wrap items-center gap-2">
            <template v-if="canReassign">
              <ElSelect
                v-model="reassignUserId"
                class="w-[136px]"
                filterable
                placeholder="选择责任人"
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
                改派
              </ElButton>
            </template>

            <ElButton
              v-if="canAccept"
              type="primary"
              :loading="actionLoading"
              @click="handleAcceptTask"
            >
              接收任务
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
              v-if="canRecall"
              plain
              type="warning"
              :loading="actionLoading"
              @click="handleRecallTask"
            >
              撤回评审
            </ElButton>
            <ElButton
              v-if="canReject"
              plain
              type="danger"
              :loading="actionLoading"
              @click="handleRejectTask"
            >
              驳回任务
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

        <!-- Hint Area (if any actions available) -->
        <div
          v-if="
            canAccept ||
            canReassign ||
            canSubmit ||
            canRecall ||
            canReject ||
            canClose
          "
          class="border-b border-blue-100 bg-blue-50/50 px-4 py-2.5"
        >
          <div class="flex items-center gap-2 text-sm text-blue-600">
            <span
              class="flex h-4 w-4 items-center justify-center rounded-full bg-blue-500 text-xs font-bold text-white"
            >
              i
            </span>
            <span>
              {{
                canClose
                  ? '填写评审纪要并完成关闭。'
                  : canReject
                    ? '版本 SE 组织评审后，可驳回任务继续修订或直接关闭。'
                    : canRecall
                      ? '提交评审后如发现问题，可撤回到梳理阶段继续完善。'
                      : canSubmit
                        ? '完成工作集确认后提交版本 SE 进入评审。'
                        : canAccept
                          ? '责任人接收任务后进入梳理工作台。'
                          : '需要时可在这里改派责任人。'
              }}
            </span>
          </div>
        </div>

        <!-- Body -->
        <div class="flex flex-col gap-6 p-4 xl:flex-row xl:items-start">
          <!-- Info Grid -->
          <div
            class="grid min-w-0 flex-1 grid-cols-2 gap-x-4 gap-y-5 sm:grid-cols-4"
          >
            <div class="flex flex-col gap-1.5">
              <span class="text-xs text-gray-500">任务编号</span>
              <span
                class="truncate text-sm font-medium text-gray-900"
                :title="currentTask?.task_no || '-'"
              >
                {{ currentTask?.task_no || '-' }}
              </span>
            </div>
            <div class="flex flex-col gap-1.5">
              <span class="text-xs text-gray-500">任务类型</span>
              <span class="truncate text-sm font-medium text-gray-900">
                {{
                  currentTask?.task_type
                    ? FM_TASK_TYPE_LABEL_MAP[currentTask.task_type] ||
                      currentTask.task_type
                    : '-'
                }}
              </span>
            </div>
            <div class="flex flex-col gap-1.5">
              <span class="text-xs text-gray-500">产品</span>
              <span
                class="truncate text-sm font-medium text-gray-900"
                :title="currentTask?.product_name || '-'"
              >
                {{ currentTask?.product_name || '-' }}
              </span>
            </div>
            <div class="flex flex-col gap-1.5">
              <span class="text-xs text-gray-500">子系统</span>
              <span
                class="truncate text-sm font-medium text-gray-900"
                :title="currentTask?.subsystem || '-'"
              >
                {{ currentTask?.subsystem || '-' }}
              </span>
            </div>
            <div class="flex flex-col gap-1.5">
              <span class="text-xs text-gray-500">创建人</span>
              <span class="truncate text-sm font-medium text-gray-900">
                {{ formatUserName(currentTask?.creator_info) }}
              </span>
            </div>
            <div class="flex flex-col gap-1.5">
              <span class="text-xs text-gray-500">责任人</span>
              <span class="truncate text-sm font-medium text-gray-900">
                {{ formatUserName(currentTask?.assignee_info) }}
              </span>
            </div>
            <div class="flex flex-col gap-1.5">
              <span class="text-xs text-gray-500">当前待办</span>
              <span class="truncate text-sm font-medium text-gray-900">
                {{ formatUserName(currentTask?.current_processor_info) }}
              </span>
            </div>
            <div class="flex flex-col gap-1.5">
              <span class="text-xs text-gray-500">最近反馈</span>
              <span
                class="truncate text-sm font-medium text-gray-900"
                :title="latestReviewFeedback"
              >
                {{ latestReviewFeedback }}
              </span>
            </div>
          </div>

          <!-- Vertical Divider for Desktop -->
          <div class="hidden h-24 w-[1px] bg-gray-100 xl:block"></div>

          <!-- Steps -->
          <div class="w-full shrink-0 pt-4 xl:w-[450px]">
            <ElSteps
              :active="activeStep"
              align-center
              class="w-full"
              finish-status="success"
              style="--el-step-icon-size: 24px"
            >
              <ElStep title="已创建">
                <template #description>
                  <div class="-ml-[10%] mt-1 flex w-[120%] justify-center">
                    <div
                      class="whitespace-pre-wrap text-center font-mono text-[11px] leading-tight tracking-tighter text-gray-500"
                    >
                      {{ formatDate(currentTask?.sys_create_datetime) }}
                    </div>
                  </div>
                </template>
              </ElStep>
              <ElStep title="梳理中">
                <template #description>
                  <div class="-ml-[10%] mt-1 flex w-[120%] justify-center">
                    <div
                      class="whitespace-pre-wrap text-center font-mono text-[11px] leading-tight tracking-tighter text-gray-500"
                    >
                      {{ formatDate(currentTask?.accepted_at) }}
                    </div>
                  </div>
                </template>
              </ElStep>
              <ElStep title="评审中">
                <template #description>
                  <div class="-ml-[10%] mt-1 flex w-[120%] justify-center">
                    <div
                      class="whitespace-pre-wrap text-center font-mono text-[11px] leading-tight tracking-tighter text-gray-500"
                    >
                      {{ formatDate(currentTask?.submitted_at) }}
                    </div>
                  </div>
                </template>
              </ElStep>
              <ElStep title="已关闭">
                <template #description>
                  <div class="-ml-[10%] mt-1 flex w-[120%] justify-center">
                    <div
                      class="whitespace-pre-wrap text-center font-mono text-[11px] leading-tight tracking-tighter text-gray-500"
                    >
                      {{ formatDate(currentTask?.closed_at) }}
                    </div>
                  </div>
                </template>
              </ElStep>
            </ElSteps>
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
                    <div class="flex items-center gap-3">
                      <span class="text-base font-semibold text-gray-900">
                        梳理工作台
                      </span>
                      <span class="text-sm text-gray-500">
                        {{ workbenchSummary }}
                      </span>
                    </div>
                  </template>

                  <template #toolbar-actions>
                    <div class="flex flex-wrap items-center gap-2">
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
                    <div
                      v-if="!isDeleteTask"
                      class="mt-1 text-xs"
                      :class="
                        row.landing_completed
                          ? 'text-emerald-600'
                          : 'text-amber-600'
                      "
                    >
                      {{
                        row.landing_completed
                          ? `落地已补齐 · ${row.landing_resource_landed_count}/${row.landing_resource_total}`
                          : `落地待补齐 · ${row.landing_resource_landed_count}/${row.landing_resource_total}`
                      }}
                    </div>
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

                  <template #cell-chips="{ row }">
                    {{ formatTextList(row.chips) || '-' }}
                  </template>

                  <template #cell-fault_categories="{ row }">
                    {{ formatTextList(row.fault_categories) || '-' }}
                  </template>

                  <template #cell-symptoms="{ row }">
                    {{ formatTextList(row.symptoms) || '-' }}
                  </template>

                  <template #cell-related_dts_nos="{ row }">
                    {{ formatTextList(row.related_dts_nos) || '-' }}
                  </template>

                  <template #cell-author_info="{ row }">
                    <span>{{
                      row.author_info
                        ?.map((item: FailureModeItem['author_info'][number]) =>
                          formatUserName(item),
                        )
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
                    <div class="flex items-center justify-center gap-2">
                      <ElButton
                        link
                        type="primary"
                        @click="handleViewFailureMode(row)"
                      >
                        查看
                      </ElButton>
                      <ElButton
                        v-if="canMaintainLanding"
                        link
                        type="success"
                        @click="handleOpenLandingConfig(row)"
                      >
                        落地配置
                      </ElButton>
                      <ElButton
                        v-if="row.editable_in_task"
                        link
                        type="primary"
                        @click="handleEditFailureMode(row)"
                      >
                        编辑
                      </ElButton>
                      <ElButton
                        v-if="
                          row.task_edit_mode === 'draft' && row.has_task_draft
                        "
                        link
                        type="warning"
                        @click="handleDeleteDraft(row)"
                      >
                        撤销修订
                      </ElButton>
                    </div>
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
              <div v-else class="flex-1 overflow-y-auto pr-2">
                <ElTimeline class="failure-mode-task-detail__timeline">
                  <ElTimelineItem
                    v-for="item in taskLogs"
                    :key="item.id"
                    :color="getTaskLogColor(item)"
                    :timestamp="item.sys_create_datetime || '-'"
                    placement="top"
                  >
                    <div
                      class="rounded-2xl border border-gray-200 bg-gradient-to-br from-white to-gray-50 p-4 shadow-sm"
                    >
                      <div class="flex flex-wrap items-center gap-2">
                        <div class="font-medium text-gray-900">
                          {{ getTaskLogTitle(item) }}
                        </div>
                        <div class="text-xs text-gray-400">
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
                      <div class="mt-2 text-sm text-gray-600">
                        操作人：{{ formatUserName(item.operator_info) }}
                      </div>
                      <div
                        v-if="item.extra_data?.reason"
                        class="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800"
                      >
                        说明：{{ item.extra_data.reason }}
                      </div>
                      <div
                        v-if="
                          item.extra_data?.from_processor_info ||
                          item.extra_data?.to_processor_info
                        "
                        class="mt-2 text-sm text-gray-500"
                      >
                        待办流转：
                        {{
                          formatUserName(item.extra_data?.from_processor_info)
                        }}
                        ->
                        {{ formatUserName(item.extra_data?.to_processor_info) }}
                      </div>
                    </div>
                  </ElTimelineItem>
                </ElTimeline>
              </div>
            </div>
          </ElTabPane>

          <ElTabPane label="评审归档" name="review">
            <div class="flex h-full min-h-0 flex-col gap-4">
              <div
                class="grid shrink-0 gap-4 xl:grid-cols-[minmax(0,1.1fr)_380px]"
              >
                <div
                  class="rounded-xl border border-gray-100 bg-gray-50/50 p-4"
                >
                  <div class="mb-3 text-base font-semibold text-gray-800">
                    评审纪要
                  </div>
                  <ElInput
                    v-model="reviewForm.review_minutes_html"
                    :autosize="{ minRows: 7, maxRows: 10 }"
                    :disabled="isClosed"
                    placeholder="请输入评审结论、会议纪要与基线说明"
                    type="textarea"
                  />
                </div>

                <div
                  class="rounded-xl border border-gray-100 bg-gray-50/50 p-4"
                >
                  <div class="mb-3 text-base font-semibold text-gray-800">
                    评审附件
                  </div>
                  <div
                    class="max-h-[220px] overflow-y-auto rounded-lg bg-white p-2 shadow-sm"
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
      :update-handler="taskFailureModeUpdateHandler"
      @success="handleFailureModeSaved"
    />
    <LandingConfigDrawer
      ref="landingConfigDrawerRef"
      :load-handler="loadTaskFailureModeLanding"
      :save-handler="saveTaskFailureModeLanding"
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

:deep(.failure-mode-task-detail__timeline) {
  padding-left: 8px;
}

:deep(.failure-mode-task-detail__timeline .el-timeline-item__wrapper) {
  top: -4px;
  padding-left: 20px;
}

:deep(.el-step__title) {
  font-size: 13px;
  line-height: 1.2;
}

:deep(.el-step__description) {
  margin-top: 4px;
  padding-right: 0 !important;
  display: flex;
  justify-content: center;
}

:deep(.el-step__main) {
  width: 100%;
}
</style>
