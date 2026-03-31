<script setup lang="ts">
import type {
  FailureModeDictOptions,
  FailureModeItem,
  FailureModeSubsystemConfigOptions,
} from '#/api/failure_mode';
import type {
  FailureModeTaskItem,
  FailureModeTaskLogItem,
} from '#/api/failure_mode_workflow';

import { computed, reactive, ref } from 'vue';

import { useUserStore } from '@vben/stores';

import {
  ElButton,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
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
  getTaskFailureModesApi,
  listProductRoleAssignmentsApi,
  listTaskLogsApi,
  quickCreateTaskFailureModeApi,
  reassignTaskApi,
  submitTaskApi,
} from '#/api/failure_mode_workflow';
import { ZqDrawer } from '#/components/zq-drawer';
import FileSelector from '#/components/zq-form/file-selector/file-selector.vue';
import { useZqTable } from '#/components/zq-table';

import FailureModeDrawer from '../../../components/FailureModeDrawer.vue';
import {
  createEmptyDictOptions,
  createEmptySubsystemConfigOptions,
  useFailureModeColumns,
} from '../../../data';
import FailureModeTransferDialog from './FailureModeTransferDialog.vue';

const emit = defineEmits(['success']);
const userStore = useUserStore();
const currentUserId = userStore.userInfo?.id;

const visible = ref(false);
const loading = ref(false);
const actionLoading = ref(false);
const currentTask = ref<FailureModeTaskItem | null>(null);
const boundFailureModes = ref<FailureModeItem[]>([]);
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

const statusLabelMap: Record<string, string> = {
  CLOSED: '已关闭',
  CREATED: '创建',
  PROCESSING: '梳理/修订中',
  REVIEWING: '评审中',
};

const taskTypeLabelMap: Record<string, string> = {
  CREATE: '创建',
  DELETE: '删除',
  REVISE: '修订',
};

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

async function loadTaskContext() {
  if (!currentTask.value) {
    return;
  }
  loading.value = true;
  try {
    const [
      failureModes,
      logs,
      taskDictOptions,
      taskSubsystemOptions,
      assignments,
    ] = await Promise.all([
      getTaskFailureModesApi(currentTask.value.id),
      listTaskLogsApi(currentTask.value.id),
      getFailureModeDictOptionsApi(),
      getFailureModeSubsystemConfigOptionsApi(),
      listProductRoleAssignmentsApi(currentTask.value.product_id),
    ]);
    boundFailureModes.value = failureModes as any;
    taskLogs.value = logs as any;
    roleAssignments.value = assignments as any;
    Object.assign(dictOptions, taskDictOptions);
    Object.assign(subsystemConfigOptions, taskSubsystemOptions);
    reassignUserId.value = currentTask.value.assignee_id || '';
    reviewForm.review_minutes_html =
      currentTask.value.review_minutes_html || '';
    reviewForm.review_attachment_ids = [
      ...(currentTask.value.review_attachment_ids || []),
    ];
    await failureModeGridApi.query();
  } finally {
    loading.value = false;
  }
}

async function open(task: FailureModeTaskItem) {
  currentTask.value = { ...task };
  visible.value = true;
  await loadTaskContext();
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
    ElMessage.success('任务故障模式绑定成功');
    await loadTaskContext();
  } catch (error: any) {
    ElMessage.error(error.message || '绑定失败');
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
    currentTask.value = await acceptTaskApi(currentTask.value.id);
    ElMessage.success('任务已接收');
    emit('success');
    await loadTaskContext();
  } catch (error: any) {
    ElMessage.error(error.message || '接收失败');
  } finally {
    actionLoading.value = false;
  }
}

function handleQuickCreateFailureMode() {
  failureModeDrawerRef.value?.openCreate();
}

async function handleQuickCreateSuccess() {
  ElMessage.success('故障模式已新增并自动绑定到当前任务');
  await loadTaskContext();
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
    currentTask.value = await submitTaskApi(currentTask.value.id);
    ElMessage.success('任务已提交评审');
    emit('success');
    await loadTaskContext();
  } catch (error: any) {
    ElMessage.error(error.message || '提交失败');
  } finally {
    actionLoading.value = false;
  }
}

async function handleReassignTask() {
  if (!currentTask.value) {
    return;
  }
  actionLoading.value = true;
  try {
    currentTask.value = await reassignTaskApi(
      currentTask.value.id,
      reassignUserId.value,
    );
    ElMessage.success('任务已改派');
    emit('success');
    await loadTaskContext();
  } catch (error: any) {
    ElMessage.error(error.message || '改派失败');
  } finally {
    actionLoading.value = false;
  }
}

async function handleCloseTask() {
  if (!currentTask.value) {
    return;
  }
  if (!reviewForm.review_minutes_html.trim()) {
    ElMessage.warning('请填写评审纪要');
    return;
  }
  actionLoading.value = true;
  try {
    currentTask.value = await closeTaskApi(currentTask.value.id, {
      review_minutes_html: reviewForm.review_minutes_html,
      review_attachment_ids: reviewForm.review_attachment_ids,
    });
    ElMessage.success('任务已评审关闭并同步基线');
    emit('success');
    await loadTaskContext();
  } catch (error: any) {
    ElMessage.error(error.message || '关闭失败');
  } finally {
    actionLoading.value = false;
  }
}

defineExpose({ open });
</script>

<template>
  <ZqDrawer
    v-model="visible"
    :loading="loading"
    :show-footer="false"
    size="86%"
    title="处理梳理任务"
  >
    <div class="flex h-full flex-col space-y-4">
      <div class="rounded-xl border bg-gray-50 p-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex flex-wrap items-center gap-3">
            <span class="text-lg font-semibold">{{ currentTask?.name }}</span>
            <ElTag type="info">{{ currentTask?.task_no }}</ElTag>
            <ElTag size="small" type="warning">
              {{
                taskTypeLabelMap[currentTask?.task_type || ''] ||
                currentTask?.task_type
              }}
            </ElTag>
            <ElTag
              size="small"
              :type="
                currentTask?.status === 'CLOSED'
                  ? 'success'
                  : currentTask?.status === 'REVIEWING'
                    ? 'warning'
                    : 'primary'
              "
            >
              {{
                statusLabelMap[currentTask?.status || ''] || currentTask?.status
              }}
            </ElTag>
          </div>

          <div class="flex flex-wrap gap-2">
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
              管理/绑定故障模式
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

        <div
          class="mt-4 grid grid-cols-2 gap-4 text-sm text-gray-600 xl:grid-cols-4"
        >
          <div>
            产品：<span class="font-medium text-gray-900">{{
              currentTask?.product_name
            }}</span>
          </div>
          <div>
            子系统：<span class="font-medium text-gray-900">{{
              currentTask?.subsystem
            }}</span>
          </div>
          <div>
            创建人：<span class="font-medium text-gray-900">{{
              currentTask?.creator_info?.name ||
              currentTask?.creator_info?.username ||
              '-'
            }}</span>
          </div>
          <div>
            责任人：<span class="font-medium text-gray-900">{{
              currentTask?.assignee_info?.name ||
              currentTask?.assignee_info?.username ||
              '-'
            }}</span>
          </div>
        </div>
      </div>

      <div
        v-if="canReassign"
        class="grid grid-cols-[220px_minmax(0,1fr)_120px] items-center gap-3 rounded-xl border bg-white p-4"
      >
        <div class="text-sm font-medium text-gray-700">改派责任人</div>
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

      <div class="flex-1 overflow-hidden rounded-xl border bg-white p-2">
        <FailureModeGrid />
      </div>

      <div class="rounded-xl border bg-white p-4">
        <div class="mb-3 text-base font-medium text-gray-800">评审纪要</div>
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

      <div class="rounded-xl border bg-white p-4">
        <div class="mb-3 text-base font-medium text-gray-800">任务日志</div>
        <div
          v-if="taskLogs.length === 0"
          class="py-6 text-center text-sm text-gray-500"
        >
          暂无任务日志
        </div>
        <div v-else class="space-y-3">
          <div
            v-for="item in taskLogs"
            :key="item.id"
            class="rounded-lg border border-gray-100 bg-gray-50 p-3"
          >
            <div
              class="flex flex-wrap items-center justify-between gap-3 text-sm"
            >
              <div class="font-medium text-gray-900">
                {{ item.note || item.action }}
              </div>
              <div class="text-gray-500">
                {{ item.sys_create_datetime || '-' }}
              </div>
            </div>
            <div class="mt-2 text-xs text-gray-500">
              操作人：{{
                item.operator_info?.name || item.operator_info?.username || '-'
              }}
              <span v-if="item.from_status || item.to_status" class="ml-3">
                状态：{{
                  statusLabelMap[item.from_status] || item.from_status || '-'
                }}
                ->
                {{ statusLabelMap[item.to_status] || item.to_status || '-' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </ZqDrawer>

  <FailureModeTransferDialog
    ref="transferDialogRef"
    @confirm="handleTransferConfirm"
  />
  <FailureModeDrawer
    ref="failureModeDrawerRef"
    :create-handler="quickCreateHandler"
    :dict-options="dictOptions"
    :subsystem-config-options="subsystemConfigOptions"
    @success="handleQuickCreateSuccess"
  />
</template>
