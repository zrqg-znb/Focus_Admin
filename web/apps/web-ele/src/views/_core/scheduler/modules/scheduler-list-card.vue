<script lang="ts" setup>
import type { SchedulerJob } from '#/api/core/scheduler';

import { onMounted, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';
import { $t } from '@vben/locales';

import {
  ElButton,
  ElMessage,
  ElMessageBox,
  ElPopover,
  ElTooltip,
} from 'element-plus';

import { deleteSchedulerJobApi, getSchedulerJobListApi } from '#/api/core/scheduler';
import { CardList } from '#/components/card-list';
import type { CardListOptions } from '#/components/card-list';
import { getStatusName } from '../data';

import SchedulerFormModal from './scheduler-form-modal.vue';

const emit = defineEmits<{
  select: [jobId: string | undefined];
  refresh: [];
}>();

const jobList = ref<SchedulerJob[]>([]);
const loading = ref(false);
const selectedJobId = ref<string>();
const searchKeyword = ref<string>('');
const hoveredJobId = ref<string>();

// 注册表单 Modal
const [SchedulerFormModalComponent, schedulerFormModalApi] = useVbenModal({
  connectedComponent: SchedulerFormModal,
  destroyOnClose: true,
});

// 卡片列表配置
const cardListOptions: CardListOptions<SchedulerJob> = {
  searchFields: [
    { field: 'name' },
    { field: 'code' },
  ],
  titleField: 'name',
};

async function fetchJobList() {
  try {
    loading.value = true;
    const response = await getSchedulerJobListApi({
      page: 1,
      pageSize: 1000,
    });
    jobList.value = response.items || [];
  } finally {
    loading.value = false;
  }
}

/**
 * 处理任务选择
 */
function onJobSelect(jobId: string | undefined) {
  selectedJobId.value = jobId;
  emit('select', jobId);
}

/**
 * 打开添加任务对话框
 */
function onAddJob() {
  schedulerFormModalApi.setData(null).open();
}

/**
 * 打开编辑任务对话框
 */
function onEditJob(job: SchedulerJob, e?: Event) {
  e?.stopPropagation();
  schedulerFormModalApi.setData(job).open();
}

/**
 * 删除任务
 */
async function onDeleteJob(job: SchedulerJob, e?: Event) {
  e?.stopPropagation();

  ElMessageBox.confirm(
    `确定要删除任务 "${job.name}" 吗？`,
    $t('common.delete'),
    {
      confirmButtonText: $t('common.confirm'),
      cancelButtonText: $t('common.cancel'),
      type: 'warning',
      showClose: false,
    },
  )
    .then(async () => {
      try {
        await deleteSchedulerJobApi(job.id);
        ElMessage.success($t('ui.actionMessage.deleteSuccess', [job.name]));

        // 如果删除的是当前选中的任务，清除选中状态
        if (selectedJobId.value === job.id) {
          selectedJobId.value = undefined;
          emit('select', undefined);
        }

        await fetchJobList();
      } catch {
        ElMessage.error($t('ui.actionMessage.deleteError'));
      }
    })
    .catch(() => {
      // 用户取消了操作
    });
}

/**
 * 添加/编辑任务成功后的回调
 */
async function onFormSuccess() {
  ElMessage.success('操作成功');
  await fetchJobList();
  emit('refresh');
}

onMounted(() => {
  fetchJobList();
});
</script>

<template>
  <CardList
    :items="jobList"
    :loading="loading"
    :selected-id="selectedJobId"
    :hovered-id="hoveredJobId"
    :search-keyword="searchKeyword"
    :options="cardListOptions"
    @select="onJobSelect"
    @update:search-keyword="(v) => searchKeyword = v"
    @update:hovered-id="(v) => hoveredJobId = v"
    @add="onAddJob"
    @edit="onEditJob"
    @delete="onDeleteJob"
  >
    <!-- 自定义项目渲染（标题行） -->
    <template #item="{ item }">
      <div class="truncate text-sm font-medium" :title="item.name">
        {{ item.name }}
      </div>
    </template>

    <!-- 详细信息（第二行） -->
    <template #details="{ item }">
      <div class="flex items-center gap-2 text-xs opacity-70">
        <!-- 任务编码 -->
        <span class="truncate" :title="item.code">
          {{ item.code }}
        </span>

        <!-- 分隔符 -->
        <span class="text-gray-400">|</span>

        <!-- 触发器类型 -->
        <span class="flex-shrink-0">
          {{ item.trigger_type === 'cron' ? 'Cron' : item.trigger_type === 'interval' ? '间隔' : '一次性' }}
        </span>

        <!-- 分隔符 -->
        <span class="text-gray-400">|</span>

        <!-- 任务状态 -->
        <span class="flex-shrink-0">
          {{ getStatusName(item.status) }}
        </span>

        <!-- 执行次数 -->
        <span v-if="item.total_run_count" class="flex-shrink-0">
          执行: {{ item.total_run_count }}
        </span>
      </div>
    </template>

    <!-- 操作按钮（第一行最右侧） -->
    <template #actions="{ item }">
      <div class="flex flex-shrink-0" @click.stop>
        <!-- 编辑按钮 -->
        <ElTooltip content="编辑" placement="top">
          <ElButton
            type="primary"
            text
            size="small"
            circle
            @click="onEditJob(item, $event)"
          >
            <IconifyIcon icon="ep:edit" class="size-4" />
          </ElButton>
        </ElTooltip>

        <!-- 删除按钮 -->
        <ElButton
          type="danger"
          text
          size="small"
          circle
          style="margin-left: 0"
          title="删除"
          @click="onDeleteJob(item, $event)"
        >
          <IconifyIcon icon="ep:delete" class="size-4" />
        </ElButton>

        <!-- 详情按钮 -->
        <ElPopover placement="right" :width="400">
          <template #reference>
            <ElButton type="info" text size="small" style="margin-left: 0" circle>
              <IconifyIcon icon="ep:info-filled" class="size-4" />
            </ElButton>
          </template>

          <!-- Popover 内容：详细信息 -->
          <div class="space-y-2 p-3 text-sm">
            <div class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">任务名称:</span>
              <span class="font-medium">{{ item.name || '-' }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">任务编码:</span>
              <span class="font-medium">{{ item.code || '-' }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">任务组:</span>
              <span class="font-medium">{{ item.group || '-' }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">触发器类型:</span>
              <span class="font-medium">
                {{ item.trigger_type === 'cron' ? 'Cron' : item.trigger_type === 'interval' ? '间隔' : '一次性' }}
              </span>
            </div>
            <div v-if="item.cron_expression" class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">Cron 表达式:</span>
              <span class="font-mono text-xs">{{ item.cron_expression }}</span>
            </div>
            <div v-if="item.interval_seconds" class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">间隔时间:</span>
              <span class="font-medium">{{ item.interval_seconds }}秒</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">状态:</span>
              <span class="font-medium">{{ getStatusName(item.status) }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">优先级:</span>
              <span class="font-medium">{{ item.priority }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">最大实例数:</span>
              <span class="font-medium">{{ item.max_instances }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">最大重试次数:</span>
              <span class="font-medium">{{ item.max_retries }}</span>
            </div>
            <div v-if="item.timeout" class="flex justify-between">
              <span class="text-gray-600 dark:text-gray-400">超时时间:</span>
              <span class="font-medium">{{ item.timeout }}秒</span>
            </div>
            <div class="border-t border-gray-200 pt-2 dark:border-gray-700">
              <div class="flex justify-between">
                <span class="text-gray-600 dark:text-gray-400">总执行次数:</span>
                <span class="font-medium">{{ item.total_run_count }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600 dark:text-gray-400">成功次数:</span>
                <span class="font-medium text-green-600">{{ item.success_count }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600 dark:text-gray-400">失败次数:</span>
                <span class="font-medium text-red-600">{{ item.failure_count }}</span>
              </div>
            </div>
            <div v-if="item.last_run_time" class="border-t border-gray-200 pt-2 dark:border-gray-700">
              <div class="flex justify-between">
                <span class="text-gray-600 dark:text-gray-400">上次执行:</span>
                <span class="text-xs">{{ item.last_run_time }}</span>
              </div>
              <div v-if="item.next_run_time" class="flex justify-between">
                <span class="text-gray-600 dark:text-gray-400">下次执行:</span>
                <span class="text-xs">{{ item.next_run_time }}</span>
              </div>
            </div>
            <div v-if="item.description" class="border-t border-gray-200 pt-2 dark:border-gray-700">
              <span class="text-gray-600 dark:text-gray-400">描述:</span>
              <div class="mt-1 max-h-32 overflow-y-auto break-words rounded bg-gray-100 p-2 text-xs dark:bg-gray-800">
                {{ item.description }}
              </div>
            </div>
          </div>
        </ElPopover>
      </div>
    </template>

    <!-- Modal 组件 -->
    <template #modal>
      <SchedulerFormModalComponent @success="onFormSuccess" />
    </template>
  </CardList>
</template>

<style scoped>
/* 输入框前置图标样式 */
:deep(.el-input__icon) {
  cursor: pointer;
}

/* 文本按钮样式 */
:deep(.el-button--text) {
  padding: 0 4px;
}

/* Popover reference 样式 */
:deep(.el-popover__reference) {
  padding: 0;
}
</style>

