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
  ElCard,
  ElDescriptions,
  ElDescriptionsItem,
  ElEmpty,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
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
const activeTab = ref('overview');
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

const taskTimelineSummary = computed(() => {
  if (!currentTask.value) {
    return [];
  }
  return [
    { label: '创建时间', value: currentTask.value.sys_create_datetime || '-' },
    { label: '接收时间', value: currentTask.value.accepted_at || '-' },
    { label: '提交评审', value: currentTask.value.submitted_at || '-' },
    { label: '关闭时间', value: currentTask.value.closed_at || '-' },
  ];
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
  if (!currentTask.value || !reviewForm.review_minutes_html.trim()) {
    return;
  }
  actionLoading.value = true;
  try {
    await closeTaskApi(currentTask.value.id, {
      review_minutes_html: reviewForm.review_minutes_html,
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
      <div class="rounded-xl bg-white p-5 shadow-sm">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div class="flex flex-wrap items-center gap-3">
            <ElButton plain @click="handleBack">返回任务列表</ElButton>
            <span class="text-xl font-semibold text-gray-900">
              {{ currentTask?.name || '任务详情' }}
            </span>
            <ElTag v-if="currentTask" type="info">
              {{ currentTask.task_no }}
            </ElTag>
            <ElTag
              v-if="currentTask"
              :type="getTaskStatusTagType(currentTask.status)"
            >
              {{
                FM_TASK_STATUS_LABEL_MAP[currentTask.status] ||
                currentTask.status
              }}
            </ElTag>
            <ElTag v-if="currentTask" type="warning">
              {{
                FM_TASK_TYPE_LABEL_MAP[currentTask.task_type] ||
                currentTask.task_type
              }}
            </ElTag>
          </div>

          <div class="flex flex-wrap items-center gap-2">
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

        <ElDescriptions v-if="currentTask" :column="4" border>
          <ElDescriptionsItem label="产品">
            {{ currentTask.product_name }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="子系统">
            {{ currentTask.subsystem }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="创建人">
            {{
              currentTask.creator_info?.name ||
              currentTask.creator_info?.username ||
              '-'
            }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="责任人">
            {{
              currentTask.assignee_info?.name ||
              currentTask.assignee_info?.username ||
              '-'
            }}
          </ElDescriptionsItem>
        </ElDescriptions>
      </div>

      <div
        class="flex min-h-0 flex-1 flex-col rounded-xl bg-white p-4 shadow-sm"
      >
        <ElTabs v-model="activeTab" class="failure-mode-task-detail__tabs">
          <ElTabPane label="概览" name="overview">
            <div
              class="grid h-full min-h-0 gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]"
            >
              <ElCard shadow="never">
                <template #header>
                  <span class="font-medium">任务摘要</span>
                </template>
                <div class="space-y-3 text-sm text-gray-600">
                  <div
                    v-for="item in taskTimelineSummary"
                    :key="item.label"
                    class="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2"
                  >
                    <span>{{ item.label }}</span>
                    <span class="font-medium text-gray-900">{{
                      item.value
                    }}</span>
                  </div>
                </div>
              </ElCard>

              <ElCard shadow="never">
                <template #header>
                  <span class="font-medium">职责说明</span>
                </template>
                <div class="space-y-3 text-sm text-gray-600">
                  <div>特性SE 在“梳理工作台”完成故障模式绑定与快速新增。</div>
                  <div>版本SE 在“评审归档”完成纪要沉淀与关闭动作。</div>
                  <div>普通成员可在“流程记录”与“评审归档”中只读查看。</div>
                </div>
              </ElCard>
            </div>
          </ElTabPane>

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
                <FailureModeGrid />
              </div>
            </div>
          </ElTabPane>

          <ElTabPane label="流程记录" name="flow">
            <div v-if="taskLogs.length === 0" class="py-12">
              <ElEmpty description="暂无流程记录" />
            </div>
            <div v-else class="space-y-3">
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
          </ElTabPane>

          <ElTabPane label="评审归档" name="review">
            <div class="flex h-full min-h-0 flex-col gap-4">
              <div class="rounded-xl border bg-white p-4">
                <div class="mb-3 text-base font-medium text-gray-800">
                  评审纪要
                </div>
                <div class="space-y-4">
                  <ElInput
                    v-model="reviewForm.review_minutes_html"
                    :autosize="{ minRows: 4, maxRows: 8 }"
                    :disabled="isClosed"
                    placeholder="请录入评审纪要"
                    type="textarea"
                  />
                  <FileSelector
                    v-model="reviewForm.review_attachment_ids"
                    :disabled="isClosed"
                    display-mode="list"
                    multiple
                    placeholder="上传评审附件"
                  />
                </div>
              </div>

              <div class="min-h-0 flex-1 rounded-xl border bg-white p-2">
                <div class="px-2 pb-3 pt-2 text-base font-medium text-gray-800">
                  当前生效基线
                </div>
                <BaselineGrid />
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
</style>
