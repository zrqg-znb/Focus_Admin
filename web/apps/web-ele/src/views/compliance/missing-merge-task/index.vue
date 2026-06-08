<script lang="ts" setup>
import type { OrganizationItem, RepositoryItem } from '#/api/compliance/base';
import type {
  MissingMergeScanStatus,
  MissingMergeScanTaskItem,
  MissingMergeTriggerType,
} from '#/api/compliance/missing-merge';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import dayjs from 'dayjs';
import {
  ElButton,
  ElDatePicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElDrawer,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElMessage,
  ElOption,
  ElSelect,
  ElTag,
} from 'element-plus';

import {
  getMissingMergeScanTaskApi,
  listMissingMergeOptionsApi,
  listMissingMergeScanTasksApi,
} from '#/api/compliance/missing-merge';
import { useZqTable } from '#/components/zq-table';

import {
  getTaskStatusTagType,
  TASK_STATUS_OPTIONS,
  TASK_TRIGGER_OPTIONS,
  useMissingMergeTaskColumns,
} from './data';

defineOptions({ name: 'ComplianceMissingMergeTask' });

const selectedStatus = ref('');
const selectedTriggerType = ref('');
const mergedRange = ref<string[]>([]);
const startedRange = ref<string[]>([]);
const detailVisible = ref(false);
const currentTask = ref<MissingMergeScanTaskItem>();
const organizationTree = ref<OrganizationItem[]>([]);
const repositoryOptions = ref<RepositoryItem[]>([]);

const organizationNameMap = computed(() => {
  const rows = flattenOrganizations(organizationTree.value);
  return new Map(rows.map((item) => [item.id, `${item.name}（${item.group_id}）`]));
});

const repositoryNameMap = computed(
  () =>
    new Map(
      repositoryOptions.value.map((item) => [
        item.id,
        `${item.project_name}（${item.project_id}）`,
      ]),
    ),
);

const [Grid, gridApi] = useZqTable<MissingMergeScanTaskItem>({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    border: true,
    columns: useMissingMergeTaskColumns(),
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [10, 20, 50, 100],
    },
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: ({
          page,
        }: {
          page: { currentPage: number; pageSize: number };
        }) =>
          listMissingMergeScanTasksApi({
            merged_after: mergedRange.value[0] || undefined,
            merged_before: mergedRange.value[1] || undefined,
            page: page.currentPage,
            pageSize: page.pageSize,
            started_after: startedRange.value[0] || undefined,
            started_before: startedRange.value[1] || undefined,
            status: (selectedStatus.value as MissingMergeScanStatus) || undefined,
            trigger_type:
              (selectedTriggerType.value as MissingMergeTriggerType) ||
              undefined,
          }),
      },
    },
    stripe: true,
    toolbarConfig: {
      custom: true,
      refresh: true,
      search: false,
      zoom: true,
    },
  },
});

function flattenOrganizations(items: OrganizationItem[]): OrganizationItem[] {
  // 详情抽屉只需要从组织 ID 映射到名称，扁平化即可避免重复递归查询。
  return items.flatMap((item) => [
    item,
    ...flattenOrganizations(item.children || []),
  ]);
}

function formatTime(value?: null | string) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
}

function formatDuration(item: MissingMergeScanTaskItem) {
  if (!item.started_at) return '-';
  const end = item.finished_at ? dayjs(item.finished_at) : dayjs();
  const seconds = Math.max(0, end.diff(dayjs(item.started_at), 'second'));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainSeconds = seconds % 60;
  return `${minutes}m ${remainSeconds}s`;
}

function normalizeRepositoryIds(item?: MissingMergeScanTaskItem) {
  const ids = item?.filter_payload?.repository_ids;
  return Array.isArray(ids) ? ids.filter((id) => `${id || ''}`.trim()) : [];
}

function getOrganizationLabel(item?: MissingMergeScanTaskItem) {
  const orgId = `${item?.filter_payload?.organization_id || ''}`.trim();
  if (!orgId) return '';
  return organizationNameMap.value.get(orgId) || orgId;
}

function getRepositoryLabels(item?: MissingMergeScanTaskItem) {
  return normalizeRepositoryIds(item).map(
    (id) => repositoryNameMap.value.get(id) || id,
  );
}

function getScopeSummary(item: MissingMergeScanTaskItem) {
  const repositoryIds = normalizeRepositoryIds(item);
  if (repositoryIds.length > 0) return `已选 ${repositoryIds.length} 个代码库`;
  const organizationLabel = getOrganizationLabel(item);
  if (organizationLabel) return `组织：${organizationLabel}`;
  return '全部组织';
}

function getRiskSummary(item: MissingMergeScanTaskItem) {
  return `识别 ${item.detected_count} / 新增 ${item.created_count} / 更新 ${item.updated_count} / 补合 ${item.fixed_count}`;
}

function reloadTasks(resetPage = false) {
  if (resetPage) gridApi.pagination.currentPage = 1;
  gridApi.query();
}

async function loadOptions() {
  const result = await listMissingMergeOptionsApi();
  organizationTree.value = result.organizations || [];
  repositoryOptions.value = result.repositories || [];
}

async function openDetail(row: MissingMergeScanTaskItem) {
  currentTask.value = await getMissingMergeScanTaskApi(row.id);
  detailVisible.value = true;
}

async function refreshCurrentTask() {
  if (!currentTask.value?.id) return;
  currentTask.value = await getMissingMergeScanTaskApi(currentTask.value.id);
  ElMessage.success('任务详情已刷新');
}

onMounted(() => {
  loadOptions();
});
</script>

<template>
  <Page auto-content-height>
    <div
      class="flex h-full min-h-0 flex-col gap-3 rounded border border-[var(--el-border-color-light)] bg-[var(--el-bg-color)] p-3"
    >
      <div class="task-summary-bar">
        <div>
          <div class="text-sm font-semibold text-[var(--el-text-color-primary)]">
            同步任务历史
          </div>
          <div class="mt-1 text-xs text-[var(--el-text-color-secondary)]">
            查看手动同步和定时扫描的执行状态、扫描范围、风险计数和失败原因。
          </div>
        </div>
        <ElButton @click="reloadTasks()">刷新</ElButton>
      </div>

      <Grid class="min-h-0 flex-1">
        <template #toolbar-actions>
          <!-- 任务历史筛选项保持稳定宽度，便于值班排障时快速扫视。 -->
          <ElForm
            class="task-toolbar"
            inline
            label-position="left"
            label-width="72px"
          >
            <ElFormItem class="toolbar-filter" label="状态">
              <ElSelect
                v-model="selectedStatus"
                clearable
                placeholder="全部状态"
                @change="reloadTasks(true)"
                @clear="reloadTasks(true)"
              >
                <ElOption
                  v-for="item in TASK_STATUS_OPTIONS"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </ElSelect>
            </ElFormItem>
            <ElFormItem class="toolbar-filter" label="触发方式">
              <ElSelect
                v-model="selectedTriggerType"
                clearable
                placeholder="全部方式"
                @change="reloadTasks(true)"
                @clear="reloadTasks(true)"
              >
                <ElOption
                  v-for="item in TASK_TRIGGER_OPTIONS"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </ElSelect>
            </ElFormItem>
            <ElFormItem class="toolbar-filter toolbar-filter-range" label="合入时间">
              <ElDatePicker
                v-model="mergedRange"
                clearable
                end-placeholder="合入结束"
                range-separator="至"
                start-placeholder="合入开始"
                type="datetimerange"
                value-format="YYYY-MM-DDTHH:mm:ssZ"
                @change="reloadTasks(true)"
              />
            </ElFormItem>
            <ElFormItem class="toolbar-filter toolbar-filter-range" label="开始时间">
              <ElDatePicker
                v-model="startedRange"
                clearable
                end-placeholder="开始结束"
                range-separator="至"
                start-placeholder="开始起始"
                type="datetimerange"
                value-format="YYYY-MM-DDTHH:mm:ssZ"
                @change="reloadTasks(true)"
              />
            </ElFormItem>
            <ElFormItem class="toolbar-actions-item">
              <div class="toolbar-actions-content">
                <ElButton @click="reloadTasks(true)">查询</ElButton>
                <ElButton @click="reloadTasks()">刷新</ElButton>
              </div>
            </ElFormItem>
          </ElForm>
        </template>

        <template #cell-status_label="{ row }">
          <ElTag :type="getTaskStatusTagType(row.status)">
            {{ row.status_label }}
          </ElTag>
        </template>
        <template #cell-trigger_type_label="{ row }">
          <ElTag effect="plain">
            {{ row.trigger_type_label }}
          </ElTag>
        </template>
        <template #cell-merged_range="{ row }">
          <div class="task-range">
            <span>{{ formatTime(row.merged_after) }}</span>
            <span>至</span>
            <span>{{ formatTime(row.merged_before) }}</span>
          </div>
        </template>
        <template #cell-started_at="{ row }">
          {{ formatTime(row.started_at) }}
        </template>
        <template #cell-finished_at="{ row }">
          {{ formatTime(row.finished_at) }}
        </template>
        <template #cell-duration="{ row }">
          {{ formatDuration(row) }}
        </template>
        <template #cell-scan_counts="{ row }">
          <div class="task-counts">
            <span>组织 {{ row.scanned_organization_count }}</span>
            <span>仓库 {{ row.scanned_repository_count }}</span>
            <span>分支对 {{ row.scanned_branch_pair_count }}</span>
          </div>
        </template>
        <template #cell-risk_counts="{ row }">
          <div class="task-counts">
            <span>识别 {{ row.detected_count }}</span>
            <span>新增 {{ row.created_count }}</span>
            <span>更新 {{ row.updated_count }}</span>
            <span>补合 {{ row.fixed_count }}</span>
          </div>
        </template>
        <template #cell-error_message="{ row }">
          <span class="error-summary" :title="row.error_message">
            {{ row.error_message || '-' }}
          </span>
        </template>
        <template #cell-actions="{ row }">
          <ElButton link type="primary" @click="openDetail(row)">
            详情
          </ElButton>
        </template>
      </Grid>
    </div>

    <ElDrawer
      v-model="detailVisible"
      title="同步任务详情"
      size="720px"
      destroy-on-close
    >
      <template v-if="currentTask">
        <div class="detail-actions">
          <ElButton @click="refreshCurrentTask">刷新详情</ElButton>
        </div>
        <ElDescriptions :column="1" border>
          <ElDescriptionsItem label="任务状态">
            <ElTag :type="getTaskStatusTagType(currentTask.status)">
              {{ currentTask.status_label }}
            </ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="触发方式">
            {{ currentTask.trigger_type_label }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="合入时间">
            {{ formatTime(currentTask.merged_after) }} 至
            {{ formatTime(currentTask.merged_before) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="执行时间">
            {{ formatTime(currentTask.started_at) }} 至
            {{ formatTime(currentTask.finished_at) }}（{{
              formatDuration(currentTask)
            }}）
          </ElDescriptionsItem>
          <ElDescriptionsItem label="扫描范围">
            {{ getScopeSummary(currentTask) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="扫描计数">
            组织 {{ currentTask.scanned_organization_count }} / 仓库
            {{ currentTask.scanned_repository_count }} / 分支对
            {{ currentTask.scanned_branch_pair_count }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="风险计数">
            {{ getRiskSummary(currentTask) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="代码库明细">
            <div v-if="getRepositoryLabels(currentTask).length" class="repo-list">
              <ElTag
                v-for="item in getRepositoryLabels(currentTask)"
                :key="item"
                effect="plain"
              >
                {{ item }}
              </ElTag>
            </div>
            <span v-else>-</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="错误信息">
            <pre v-if="currentTask.error_message" class="error-block">{{
              currentTask.error_message
            }}</pre>
            <span v-else>-</span>
          </ElDescriptionsItem>
        </ElDescriptions>
      </template>
      <ElEmpty v-else description="暂无任务详情" />
    </ElDrawer>
  </Page>
</template>

<style scoped lang="less">
.task-summary-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-extra-light);
}

.task-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  width: 100%;
  min-width: 0;
  gap: 10px 12px;
  margin: 0;
}

.task-toolbar :deep(.el-form-item) {
  margin: 0;
}

.task-toolbar :deep(.el-form-item__label) {
  height: 32px;
  justify-content: flex-end;
  padding-right: 8px;
  font-size: 12px;
  line-height: 32px;
  color: var(--el-text-color-regular);
}

.task-toolbar :deep(.el-form-item__content) {
  flex: 1;
  min-width: 0;
}

.task-toolbar :deep(.el-select),
.task-toolbar :deep(.el-date-editor) {
  width: 100%;
}

.toolbar-filter {
  width: 260px;
}

.toolbar-filter-range {
  width: 430px;
}

.toolbar-actions-item {
  width: auto;
}

.toolbar-actions-content,
.task-counts,
.task-range,
.repo-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.task-counts,
.task-range {
  justify-content: center;
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.error-summary {
  display: inline-block;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--el-color-danger);
  vertical-align: middle;
}

.detail-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.error-block {
  max-height: 260px;
  padding: 10px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  color: var(--el-color-danger);
  background: var(--el-fill-color-extra-light);
}

@media (max-width: 768px) {
  .task-summary-bar {
    align-items: flex-start;
    flex-direction: column;
  }

  .toolbar-filter,
  .toolbar-filter-range,
  .toolbar-actions-item {
    width: 100%;
  }
}
</style>
