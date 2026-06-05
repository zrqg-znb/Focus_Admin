<script lang="ts" setup>
import type { OrganizationItem, RepositoryItem } from '#/api/compliance/base';
import type {
  MissingMergeRecordItem,
  MissingMergeScanTaskItem,
  MissingMergeStatus,
} from '#/api/compliance/missing-merge';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { Search } from '@vben/icons';

import dayjs from 'dayjs';
import {
  ElButton,
  ElDatePicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElDrawer,
  ElForm,
  ElFormItem,
  ElInput,
  ElLink,
  ElMessage,
  ElOption,
  ElRadioButton,
  ElRadioGroup,
  ElSelect,
  ElTag,
} from 'element-plus';

import {
  getMissingMergeRecordApi,
  listMissingMergeOptionsApi,
  listMissingMergeRecordsApi,
  listMissingMergeScanTasksApi,
  runMissingMergeScanApi,
  updateMissingMergeRecordStatusApi,
} from '#/api/compliance/missing-merge';
import { useZqTable } from '#/components/zq-table';

import {
  getStatusTagType,
  STATUS_OPTIONS,
  useMissingMergeColumns,
} from './data';

defineOptions({ name: 'ComplianceMissingMerge' });

interface OrganizationOption {
  id: string;
  label: string;
}

const keyword = ref('');
const selectedOrganizationId = ref('');
const selectedRepositoryId = ref('');
const selectedStatus = ref('');
const authorUsername = ref('');
const trunkBranch = ref('');
const releaseBranch = ref('');
const mergedRange = ref<string[]>([]);
const detectedRange = ref<string[]>([]);

const organizationOptions = ref<OrganizationOption[]>([]);
const repositoryOptions = ref<RepositoryItem[]>([]);
const latestTasks = ref<MissingMergeScanTaskItem[]>([]);
const optionsLoading = ref(false);

const detailDrawerVisible = ref(false);
const currentRecord = ref<MissingMergeRecordItem>();
const statusDialogVisible = ref(false);
const statusSubmitting = ref(false);
const scanDialogVisible = ref(false);
const scanning = ref(false);

const statusForm = reactive<{
  handle_remark: string;
  id: string;
  status: MissingMergeStatus;
}>({
  handle_remark: '',
  id: '',
  status: 'open',
});

const scanForm = reactive<{
  organization_id: string;
  repository_id: string;
  timeRange: string[];
}>({
  organization_id: '',
  repository_id: '',
  timeRange: [],
});

const filteredRepositoryOptions = computed(() => {
  if (!selectedOrganizationId.value) return repositoryOptions.value;
  return repositoryOptions.value.filter(
    (item) => item.organization_id === selectedOrganizationId.value,
  );
});

const scanRepositoryOptions = computed(() => {
  if (!scanForm.organization_id) return repositoryOptions.value;
  return repositoryOptions.value.filter(
    (item) => item.organization_id === scanForm.organization_id,
  );
});

const latestTask = computed(() => latestTasks.value[0]);

const [Grid, gridApi] = useZqTable<MissingMergeRecordItem>({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    border: true,
    columns: useMissingMergeColumns(),
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
        }) => {
          return listMissingMergeRecordsApi({
            author_username: authorUsername.value || undefined,
            detected_after: detectedRange.value[0] || undefined,
            detected_before: detectedRange.value[1] || undefined,
            keyword: keyword.value || undefined,
            merged_after: mergedRange.value[0] || undefined,
            merged_before: mergedRange.value[1] || undefined,
            organization_id: selectedOrganizationId.value || undefined,
            page: page.currentPage,
            pageSize: page.pageSize,
            release_branch: releaseBranch.value || undefined,
            repository_id: selectedRepositoryId.value || undefined,
            status: (selectedStatus.value as MissingMergeStatus) || undefined,
            trunk_branch: trunkBranch.value || undefined,
          });
        },
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

function formatTime(value?: null | string) {
  // 表格和详情统一时间格式，空值显示短横线。
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
}

function formatApiTime(value = dayjs()) {
  // 后端和数据湖均接受带时区的 ISO-like 字符串。
  return dayjs(value).format('YYYY-MM-DDTHH:mm:ssZ');
}

function flattenOrganizations(
  items: OrganizationItem[],
  parents: string[] = [],
): OrganizationOption[] {
  // 组织树在筛选下拉中展开为路径文案，避免同名组织难以区分。
  return items.flatMap((item) => {
    const path = [...parents, item.name];
    return [
      { id: item.id, label: `${path.join(' / ')}（${item.group_id}）` },
      ...flattenOrganizations(item.children || [], path),
    ];
  });
}

async function loadOptions() {
  // 选项接口挂在漏合风险权限下，避免依赖代码库管理页的 API 权限。
  optionsLoading.value = true;
  try {
    const result = await listMissingMergeOptionsApi();
    organizationOptions.value = flattenOrganizations(
      result.organizations || [],
    );
    repositoryOptions.value = result.repositories || [];
  } finally {
    optionsLoading.value = false;
  }
}

async function loadLatestTasks(showMessage = false) {
  // 最近任务摘要独立于表格，手动同步后即时刷新。
  const result = await listMissingMergeScanTasksApi({ page: 1, pageSize: 5 });
  latestTasks.value = result.items || [];
  if (showMessage) {
    ElMessage.success(
      latestTasks.value.length ? '任务记录已刷新' : '暂无任务记录',
    );
  }
}

function reloadRecords(resetPage = false) {
  if (resetPage) gridApi.pagination.currentPage = 1;
  gridApi.query();
}

function handleOrganizationChange() {
  if (
    selectedRepositoryId.value &&
    !filteredRepositoryOptions.value.some(
      (item) => item.id === selectedRepositoryId.value,
    )
  ) {
    selectedRepositoryId.value = '';
  }
  reloadRecords(true);
}

async function openDetail(row: MissingMergeRecordItem) {
  currentRecord.value = await getMissingMergeRecordApi(row.id);
  detailDrawerVisible.value = true;
}

function openStatusDialog(row: MissingMergeRecordItem) {
  statusForm.id = row.id;
  statusForm.status = row.status;
  statusForm.handle_remark = row.handle_remark || '';
  statusDialogVisible.value = true;
}

async function submitStatus() {
  if (!statusForm.id) return;
  statusSubmitting.value = true;
  try {
    await updateMissingMergeRecordStatusApi(statusForm.id, {
      handle_remark: statusForm.handle_remark,
      status: statusForm.status,
    });
    ElMessage.success('状态已更新');
    statusDialogVisible.value = false;
    reloadRecords();
  } finally {
    statusSubmitting.value = false;
  }
}

async function openScanDialog() {
  await loadOptions();
  const now = dayjs();
  scanForm.timeRange = [
    formatApiTime(now.subtract(1, 'day')),
    formatApiTime(now),
  ];
  scanForm.organization_id = selectedOrganizationId.value;
  scanForm.repository_id = selectedRepositoryId.value;
  scanDialogVisible.value = true;
}

function handleScanOrganizationChange() {
  // 扫描范围切换组织时，清掉不属于该组织的代码库。
  if (
    scanForm.repository_id &&
    !scanRepositoryOptions.value.some(
      (item) => item.id === scanForm.repository_id,
    )
  ) {
    scanForm.repository_id = '';
  }
}

async function submitScan() {
  if (scanForm.timeRange.length !== 2) {
    ElMessage.warning('请选择扫描时间范围');
    return;
  }
  scanning.value = true;
  try {
    const [mergedAfter, mergedBefore] = scanForm.timeRange;
    const task = await runMissingMergeScanApi({
      merged_after: mergedAfter!,
      merged_before: mergedBefore!,
      organization_id: scanForm.organization_id || undefined,
      repository_id: scanForm.repository_id || undefined,
    });
    if (task.status === 'failed') {
      ElMessage.warning(`扫描失败：${task.error_message || '请查看任务记录'}`);
    } else {
      ElMessage.success(`扫描完成，识别 ${task.detected_count} 条漏合风险`);
    }
    scanDialogVisible.value = false;
    await loadLatestTasks();
    reloadRecords(true);
  } finally {
    scanning.value = false;
  }
}

onMounted(async () => {
  await loadOptions();
  await loadLatestTasks();
});
</script>

<template>
  <Page auto-content-height>
    <div
      class="flex h-full min-h-0 flex-col gap-3 rounded border border-[var(--el-border-color-light)] bg-[var(--el-bg-color)] p-3"
    >
      <div class="summary-bar">
        <div>
          <div
            class="text-sm font-semibold text-[var(--el-text-color-primary)]"
          >
            漏合风险
          </div>
          <div class="mt-1 text-xs text-[var(--el-text-color-secondary)]">
            基于组织、代码库和分支绑定关系自动比对主干与发布分支 CR。
          </div>
        </div>
        <div class="summary-task" v-if="latestTask">
          <ElTag
            :type="
              latestTask.status === 'success'
                ? 'success'
                : latestTask.status === 'failed'
                  ? 'danger'
                  : 'warning'
            "
          >
            {{ latestTask.status_label }}
          </ElTag>
          <span
            >最近同步：{{
              formatTime(latestTask.finished_at || latestTask.started_at)
            }}</span
          >
          <span>识别 {{ latestTask.detected_count }} 条</span>
          <span>补合 {{ latestTask.fixed_count }} 条</span>
        </div>
        <div v-else class="text-xs text-[var(--el-text-color-secondary)]">
          暂无同步任务
        </div>
      </div>

      <Grid class="min-h-0 flex-1">
        <template #toolbar-actions>
          <div class="toolbar-stack">
            <!-- 筛选条件和业务操作分行展示，避免内部治理页横向拥挤。 -->
            <div class="toolbar-row">
              <ElInput
                v-model="keyword"
                class="toolbar-keyword"
                clearable
                placeholder="搜索标题/Change Key/代码库"
                :prefix-icon="Search"
                @clear="reloadRecords(true)"
                @keyup.enter="reloadRecords(true)"
              />
              <ElSelect
                v-model="selectedStatus"
                class="toolbar-select-sm"
                clearable
                placeholder="状态"
                @change="reloadRecords(true)"
                @clear="reloadRecords(true)"
              >
                <ElOption
                  v-for="item in STATUS_OPTIONS"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </ElSelect>
              <ElSelect
                v-model="selectedOrganizationId"
                class="toolbar-select-lg"
                clearable
                filterable
                placeholder="组织"
                @change="handleOrganizationChange"
                @clear="handleOrganizationChange"
              >
                <ElOption
                  v-for="item in organizationOptions"
                  :key="item.id"
                  :label="item.label"
                  :value="item.id"
                />
              </ElSelect>
              <ElSelect
                v-model="selectedRepositoryId"
                class="toolbar-select-lg"
                clearable
                filterable
                placeholder="代码库"
                @change="reloadRecords(true)"
                @clear="reloadRecords(true)"
              >
                <ElOption
                  v-for="item in filteredRepositoryOptions"
                  :key="item.id"
                  :label="`${item.project_name}（${item.project_id}）`"
                  :value="item.id"
                />
              </ElSelect>
              <ElInput
                v-model="authorUsername"
                class="toolbar-select-md"
                clearable
                placeholder="创建人"
                @clear="reloadRecords(true)"
                @keyup.enter="reloadRecords(true)"
              />
              <ElButton @click="reloadRecords(true)">查询</ElButton>
            </div>
            <div class="toolbar-row">
              <ElInput
                v-model="trunkBranch"
                class="toolbar-select-md"
                clearable
                placeholder="主干分支"
                @clear="reloadRecords(true)"
                @keyup.enter="reloadRecords(true)"
              />
              <ElInput
                v-model="releaseBranch"
                class="toolbar-select-md"
                clearable
                placeholder="发布分支"
                @clear="reloadRecords(true)"
                @keyup.enter="reloadRecords(true)"
              />
              <ElDatePicker
                v-model="mergedRange"
                class="toolbar-date-range"
                clearable
                end-placeholder="合入结束"
                range-separator="至"
                start-placeholder="合入开始"
                type="datetimerange"
                value-format="YYYY-MM-DDTHH:mm:ssZ"
                @change="reloadRecords(true)"
              />
              <ElDatePicker
                v-model="detectedRange"
                class="toolbar-date-range"
                clearable
                end-placeholder="识别结束"
                range-separator="至"
                start-placeholder="识别开始"
                type="datetimerange"
                value-format="YYYY-MM-DDTHH:mm:ssZ"
                @change="reloadRecords(true)"
              />
            </div>
            <div class="toolbar-row toolbar-row-actions">
              <ElButton @click="loadLatestTasks(true)">刷新任务</ElButton>
              <ElButton
                type="primary"
                :loading="optionsLoading"
                @click="openScanDialog"
              >
                手动同步
              </ElButton>
            </div>
          </div>
        </template>

        <template #cell-title="{ row }">
          <div class="min-w-0 text-left">
            <div class="truncate font-medium" :title="row.title">
              {{ row.title || row.change_key }}
            </div>
            <div class="truncate text-xs text-[var(--el-text-color-secondary)]">
              {{ row.change_request_iid || '-' }} / {{ row.change_key }}
            </div>
          </div>
        </template>

        <template #cell-status_label="{ row }">
          <ElTag :type="getStatusTagType(row.status)">
            {{ row.status_label }}
          </ElTag>
        </template>

        <template #cell-merged_at="{ row }">
          {{ formatTime(row.merged_at) }}
        </template>

        <template #cell-detected_at="{ row }">
          {{ formatTime(row.detected_at) }}
        </template>

        <template #cell-line_changes="{ row }">
          <span class="text-[var(--el-color-success)]"
            >+{{ row.added_lines }}</span
          >
          <span class="mx-1 text-[var(--el-text-color-secondary)]">/</span>
          <span class="text-[var(--el-color-danger)]"
            >-{{ row.removed_lines }}</span
          >
        </template>

        <template #cell-actions="{ row }">
          <div class="flex items-center justify-center gap-1">
            <ElButton link type="primary" @click="openDetail(row)"
              >详情</ElButton
            >
            <ElButton link type="primary" @click="openStatusDialog(row)"
              >处理</ElButton
            >
          </div>
        </template>
      </Grid>
    </div>

    <ElDrawer
      v-model="detailDrawerVisible"
      title="漏合 CR 详情"
      size="640px"
      destroy-on-close
    >
      <template v-if="currentRecord">
        <ElDescriptions :column="1" border>
          <ElDescriptionsItem label="标题">
            {{ currentRecord.title || '-' }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="Change Key">
            {{ currentRecord.change_key }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="代码库">
            {{ currentRecord.repository_name }}（{{
              currentRecord.repository_project_id
            }}）
          </ElDescriptionsItem>
          <ElDescriptionsItem label="组织">
            {{ currentRecord.organization_name }}（{{
              currentRecord.organization_group_id
            }}）
          </ElDescriptionsItem>
          <ElDescriptionsItem label="分支配对">
            {{ currentRecord.trunk_branch }} ->
            {{ currentRecord.release_branch }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="创建人">
            {{ currentRecord.author_username || '-' }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="主干合入时间">
            {{ formatTime(currentRecord.merged_at) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="代码行变化">
            +{{ currentRecord.added_lines }} / -{{
              currentRecord.removed_lines
            }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="CR链接">
            <ElLink
              v-if="currentRecord.web_url"
              :href="currentRecord.web_url"
              target="_blank"
              type="primary"
            >
              {{ currentRecord.web_url }}
            </ElLink>
            <span v-else>-</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="描述">
            <div class="whitespace-pre-wrap leading-6">
              {{ currentRecord.description || '-' }}
            </div>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="处理备注">
            <div class="whitespace-pre-wrap leading-6">
              {{ currentRecord.handle_remark || '-' }}
            </div>
          </ElDescriptionsItem>
        </ElDescriptions>
      </template>
    </ElDrawer>

    <ElDialog
      v-model="statusDialogVisible"
      title="更新漏合风险状态"
      width="520px"
      destroy-on-close
    >
      <ElForm label-width="92px">
        <ElFormItem label="处理状态">
          <ElRadioGroup v-model="statusForm.status">
            <ElRadioButton
              v-for="item in STATUS_OPTIONS"
              :key="item.value"
              :label="item.value"
            >
              {{ item.label }}
            </ElRadioButton>
          </ElRadioGroup>
        </ElFormItem>
        <ElFormItem label="处理备注">
          <ElInput
            v-model="statusForm.handle_remark"
            :rows="4"
            placeholder="记录本次处理说明"
            type="textarea"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="statusDialogVisible = false">取消</ElButton>
        <ElButton
          type="primary"
          :loading="statusSubmitting"
          @click="submitStatus"
        >
          保存
        </ElButton>
      </template>
    </ElDialog>

    <ElDialog
      v-model="scanDialogVisible"
      title="手动同步漏合数据"
      width="620px"
      destroy-on-close
    >
      <ElForm label-width="92px">
        <ElFormItem label="时间范围" required>
          <ElDatePicker
            v-model="scanForm.timeRange"
            class="w-full"
            end-placeholder="合入结束"
            range-separator="至"
            start-placeholder="合入开始"
            type="datetimerange"
            value-format="YYYY-MM-DDTHH:mm:ssZ"
          />
        </ElFormItem>
        <ElFormItem label="组织">
          <ElSelect
            v-model="scanForm.organization_id"
            class="w-full"
            clearable
            filterable
            :loading="optionsLoading"
            placeholder="不选则扫描全部组织"
            @change="handleScanOrganizationChange"
            @clear="handleScanOrganizationChange"
          >
            <ElOption
              v-for="item in organizationOptions"
              :key="item.id"
              :label="item.label"
              :value="item.id"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="代码库">
          <ElSelect
            v-model="scanForm.repository_id"
            class="w-full"
            clearable
            filterable
            :loading="optionsLoading"
            placeholder="不选则扫描组织下全部代码库"
          >
            <ElOption
              v-for="item in scanRepositoryOptions"
              :key="item.id"
              :label="`${item.project_name}（${item.project_id}）`"
              :value="item.id"
            />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="scanDialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="scanning" @click="submitScan">
          开始同步
        </ElButton>
      </template>
    </ElDialog>
  </Page>
</template>

<style scoped lang="less">
.summary-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-extra-light);
}

.summary-task {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.toolbar-stack {
  flex: 1;
  width: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toolbar-row {
  // 三段式工具栏让高频筛选、时间筛选和业务动作各自保持可读宽度。
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  width: 100%;
  min-width: 0;
  gap: 8px;
}

.toolbar-row-actions {
  justify-content: flex-end;
}

.toolbar-keyword {
  width: 280px;
  max-width: 100%;
}

.toolbar-select-sm {
  width: 120px;
}

.toolbar-select-md {
  width: 160px;
}

.toolbar-select-lg {
  width: 240px;
}

.toolbar-date-range {
  width: 330px;
  max-width: 100%;
}

@media (max-width: 768px) {
  .summary-bar {
    align-items: flex-start;
    flex-direction: column;
  }

  .toolbar-keyword,
  .toolbar-select-sm,
  .toolbar-select-md,
  .toolbar-select-lg,
  .toolbar-date-range {
    width: 100%;
  }

  .toolbar-row-actions {
    justify-content: flex-start;
  }
}
</style>
