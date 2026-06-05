<script lang="ts" setup>
import type { OrganizationItem, RepositoryItem } from '#/api/compliance/base';
import type {
  MissingMergeOperationLogItem,
  MissingMergeRecordItem,
  MissingMergeScanTaskItem,
  MissingMergeStatus,
} from '#/api/compliance/missing-merge';
import type { FormInstance, FormRules } from 'element-plus';

import { computed, nextTick, onMounted, reactive, ref } from 'vue';

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
  ElEmpty,
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
  ElTimeline,
  ElTimelineItem,
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

interface StatusFormState {
  handle_remark: string;
  id: string;
  status: MissingMergeStatus;
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
const statusFormRef = ref<FormInstance>();
const statusDialogVisible = ref(false);
const statusSubmitting = ref(false);
const scanDialogVisible = ref(false);
const scanning = ref(false);

const statusForm = reactive<StatusFormState>({
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

const remarkForbiddenPattern = /[\u0000-\u001F\u007F<>`{}]/;

const statusRules: FormRules<StatusFormState> = {
  handle_remark: [
    {
      validator: (
        _rule: unknown,
        value: string,
        callback: (error?: Error) => void,
      ) => {
        // 人工处理必须留下可追溯说明，同时拦截脚本风险字符。
        const remark = `${value || ''}`.trim();
        if (remark.length < 5) {
          callback(new Error('处理备注不能为空，且不少于 5 个字符'));
          return;
        }
        if (remarkForbiddenPattern.test(remark)) {
          callback(new Error('处理备注不能包含控制字符或 < > ` { } 等特殊字符'));
          return;
        }
        callback();
      },
      trigger: ['blur', 'change'],
    },
  ],
  status: [{ message: '请选择处理状态', required: true, trigger: 'change' }],
};

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

function getOperationLogColor(item: MissingMergeOperationLogItem) {
  // 时间轴颜色按操作语义区分，便于快速扫出人工处理和系统闭环。
  if (item.operation_type === 'auto_closed') return 'var(--el-color-success)';
  if (item.operation_type === 'reopened') return 'var(--el-color-warning)';
  if (item.operation_type === 'manual_handle') return 'var(--el-color-primary)';
  return 'var(--el-text-color-secondary)';
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
  // 每次人工处理都要求填写本次备注，避免复用历史备注形成空操作。
  statusForm.handle_remark = '';
  statusDialogVisible.value = true;
  nextTick(() => statusFormRef.value?.clearValidate());
}

async function submitStatus() {
  if (!statusForm.id) return;
  const valid = await statusFormRef.value?.validate().catch(() => false);
  if (!valid) return;
  statusSubmitting.value = true;
  try {
    const updatedRecord = await updateMissingMergeRecordStatusApi(statusForm.id, {
      handle_remark: statusForm.handle_remark.trim(),
      status: statusForm.status,
    });
    ElMessage.success('状态已更新');
    statusDialogVisible.value = false;
    if (currentRecord.value?.id === updatedRecord.id) {
      currentRecord.value = updatedRecord;
    }
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
          <!-- 统一筛选表单用固定宽度和显式 label，避免多段工具栏割裂。 -->
          <ElForm
            class="missing-merge-toolbar"
            inline
            label-position="left"
            label-width="72px"
          >
            <ElFormItem class="toolbar-filter toolbar-filter-keyword" label="关键词">
              <ElInput
                v-model="keyword"
                clearable
                placeholder="标题 / Change Key / 代码库"
                :prefix-icon="Search"
                @clear="reloadRecords(true)"
                @keyup.enter="reloadRecords(true)"
              />
            </ElFormItem>
            <ElFormItem class="toolbar-filter" label="状态">
              <ElSelect
                v-model="selectedStatus"
                clearable
                placeholder="全部状态"
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
            </ElFormItem>
            <ElFormItem class="toolbar-filter" label="组织">
              <ElSelect
                v-model="selectedOrganizationId"
                clearable
                filterable
                placeholder="选择组织"
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
            </ElFormItem>
            <ElFormItem class="toolbar-filter" label="代码库">
              <ElSelect
                v-model="selectedRepositoryId"
                clearable
                filterable
                placeholder="选择代码库"
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
            </ElFormItem>
            <ElFormItem class="toolbar-filter" label="创建人">
              <ElInput
                v-model="authorUsername"
                clearable
                placeholder="Focus 用户名"
                @clear="reloadRecords(true)"
                @keyup.enter="reloadRecords(true)"
              />
            </ElFormItem>
            <ElFormItem class="toolbar-filter" label="主干分支">
              <ElInput
                v-model="trunkBranch"
                clearable
                placeholder="分支名"
                @clear="reloadRecords(true)"
                @keyup.enter="reloadRecords(true)"
              />
            </ElFormItem>
            <ElFormItem class="toolbar-filter" label="发布分支">
              <ElInput
                v-model="releaseBranch"
                clearable
                placeholder="分支名"
                @clear="reloadRecords(true)"
                @keyup.enter="reloadRecords(true)"
              />
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
                @change="reloadRecords(true)"
              />
            </ElFormItem>
            <ElFormItem class="toolbar-filter toolbar-filter-range" label="识别时间">
              <ElDatePicker
                v-model="detectedRange"
                clearable
                end-placeholder="识别结束"
                range-separator="至"
                start-placeholder="识别开始"
                type="datetimerange"
                value-format="YYYY-MM-DDTHH:mm:ssZ"
                @change="reloadRecords(true)"
              />
            </ElFormItem>
            <ElFormItem class="toolbar-actions-item">
              <div class="toolbar-actions-content">
                <ElButton @click="reloadRecords(true)">查询</ElButton>
                <ElButton @click="loadLatestTasks(true)">刷新任务</ElButton>
                <ElButton
                  type="primary"
                  :loading="optionsLoading"
                  @click="openScanDialog"
                >
                  手动同步
                </ElButton>
              </div>
            </ElFormItem>
          </ElForm>
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
      size="720px"
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

        <div class="detail-section">
          <div class="detail-section-title">操作历史</div>
          <ElEmpty
            v-if="!currentRecord.operation_logs?.length"
            description="暂无操作历史"
          />
          <ElTimeline v-else class="missing-merge-history">
            <ElTimelineItem
              v-for="item in currentRecord.operation_logs"
              :key="item.id"
              :color="getOperationLogColor(item)"
              :timestamp="formatTime(item.operated_at)"
              placement="top"
            >
              <div class="history-card">
                <div class="history-card-header">
                  <div class="history-title">
                    {{ item.operation_type_label }}
                  </div>
                  <ElTag
                    size="small"
                    :type="item.source === 'system' ? 'info' : 'primary'"
                  >
                    {{ item.source_label }}
                  </ElTag>
                </div>
                <div class="history-meta">
                  <span>操作人：{{ item.operator_name || '-' }}</span>
                  <span v-if="item.from_status_label || item.to_status_label">
                    状态：{{ item.from_status_label || '-' }} ->
                    {{ item.to_status_label || '-' }}
                  </span>
                </div>
                <div class="history-remark">
                  {{ item.remark || '-' }}
                </div>
              </div>
            </ElTimelineItem>
          </ElTimeline>
        </div>
      </template>
    </ElDrawer>

    <ElDialog
      v-model="statusDialogVisible"
      title="更新漏合风险状态"
      width="520px"
      destroy-on-close
    >
      <ElForm
        ref="statusFormRef"
        label-width="92px"
        :model="statusForm"
        :rules="statusRules"
      >
        <ElFormItem label="处理状态" prop="status">
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
        <ElFormItem label="处理备注" prop="handle_remark">
          <ElInput
            v-model="statusForm.handle_remark"
            maxlength="500"
            :rows="4"
            show-word-limit
            placeholder="至少 5 个字符，不能包含 < > ` { } 等特殊字符"
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

.missing-merge-toolbar {
  // 固定宽度筛选项按自然顺序换行，避免搜索栏出现无规律断行。
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  width: 100%;
  min-width: 0;
  gap: 10px 12px;
  margin: 0;
}

.missing-merge-toolbar :deep(.el-form-item) {
  margin: 0;
}

.missing-merge-toolbar :deep(.el-form-item__label) {
  height: 32px;
  justify-content: flex-end;
  padding-right: 8px;
  font-size: 12px;
  line-height: 32px;
  color: var(--el-text-color-regular);
}

.missing-merge-toolbar :deep(.el-form-item__content) {
  flex: 1;
  min-width: 0;
}

.missing-merge-toolbar :deep(.el-input),
.missing-merge-toolbar :deep(.el-select),
.missing-merge-toolbar :deep(.el-date-editor) {
  width: 100%;
}

.toolbar-filter {
  width: 260px;
}

.toolbar-filter-keyword {
  width: 320px;
}

.toolbar-filter-range {
  width: 430px;
}

.toolbar-actions-item {
  width: auto;
}

.toolbar-actions-content {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-section {
  margin-top: 18px;
}

.detail-section-title {
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.missing-merge-history {
  padding: 4px 0 0 2px;
}

.history-card {
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-extra-light);
}

.history-card-header,
.history-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.history-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.history-meta {
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.history-remark {
  margin-top: 8px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
}

@media (max-width: 768px) {
  .summary-bar {
    align-items: flex-start;
    flex-direction: column;
  }

  .toolbar-filter,
  .toolbar-filter-keyword,
  .toolbar-filter-range,
  .toolbar-actions-item {
    width: 100%;
  }

  .toolbar-actions-content {
    width: 100%;
  }
}
</style>
