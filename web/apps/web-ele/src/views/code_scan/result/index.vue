<script setup lang="ts">
import type { ProjectOverviewTableRow } from './data';

import type {
  LatestResultsQueryParams,
  LatestScanResultItem,
  ProjectOverviewItem,
  ProjectOverviewQueryParams,
  ShieldApplyPayload,
  ShieldRecordItem,
  ShieldStatus,
} from '#/api/code_scan';

import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { Filter } from '@element-plus/icons-vue';
import {
  ElButton,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElPopover,
  ElRadio,
  ElRadioGroup,
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus';

import {
  applyShieldApi,
  listLatestResultsApi,
  listProjectOverviewApi,
  listResultShieldRecordsApi,
} from '#/api/code_scan';
import { UserSelector } from '#/components/zq-form/user-selector';
import { useZqTable } from '#/components/zq-table';

import {
  ALL_SCAN_TOOLS,
  SHIELD_STATUS_OPTIONS,
  useDetailColumns,
  useSummaryColumns,
} from './data';

defineOptions({ name: 'CodeScanResult' });

type TableSortOrder = 'ascending' | 'descending' | null;
type DetailKeywordColumnKey =
  | 'defect_type'
  | 'description'
  | 'file_path'
  | 'severity';
type DetailKeywordParamKey =
  | 'defect_type_keyword'
  | 'description_keyword'
  | 'file_path_keyword'
  | 'severity_keyword';
type DetailKeywordFilters = Record<DetailKeywordColumnKey, string>;
type DetailKeywordVisibleState = Record<DetailKeywordColumnKey, boolean>;

interface DetailKeywordFilterConfig {
  columnKey: DetailKeywordColumnKey;
  label: string;
  paramKey: DetailKeywordParamKey;
  placeholder: string;
  width: number;
}

const DETAIL_KEYWORD_FILTER_CONFIGS: DetailKeywordFilterConfig[] = [
  {
    columnKey: 'severity',
    label: '严重程度',
    paramKey: 'severity_keyword',
    placeholder: '输入关键词模糊搜索严重程度',
    width: 220,
  },
  {
    columnKey: 'defect_type',
    label: '缺陷类型',
    paramKey: 'defect_type_keyword',
    placeholder: '输入关键词模糊搜索缺陷类型',
    width: 240,
  },
  {
    columnKey: 'file_path',
    label: '文件路径',
    paramKey: 'file_path_keyword',
    placeholder: '输入关键词模糊搜索文件路径',
    width: 300,
  },
  {
    columnKey: 'description',
    label: '缺陷描述',
    paramKey: 'description_keyword',
    placeholder: '输入关键词模糊搜索缺陷描述',
    width: 320,
  },
];

function createDetailKeywordFilters(): DetailKeywordFilters {
  return {
    severity: '',
    defect_type: '',
    file_path: '',
    description: '',
  };
}

function createDetailKeywordVisibleState(): DetailKeywordVisibleState {
  return {
    severity: false,
    defect_type: false,
    file_path: false,
    description: false,
  };
}

const route = useRoute();
const router = useRouter();

const projectId = computed(() => route.query.projectId as string | undefined);
const isDetail = computed(() => Boolean(projectId.value));
const preferredTool = computed(() => {
  const tool =
    (route.query.tool as string | undefined) ||
    (route.query.tool_name as string | undefined) ||
    '';
  return String(tool).trim().toLowerCase();
});
const routeSubModules = computed(() => {
  const raw = route.query.sub_modules;
  if (Array.isArray(raw)) {
    return raw
      .map((item) => String(item).trim())
      .filter(Boolean)
      .join(',');
  }
  return String(raw || '').trim();
});

const shieldVisible = ref(false);
const shieldForm = ref<ShieldApplyPayload>({
  approver_id: '',
  reason: '',
  result_ids: [],
});

const projectMissing = ref(false);
const selectedResults = ref<LatestScanResultItem[]>([]);
const shieldStatusFilter = ref<'' | ShieldStatus>('');
const shieldStatusDraft = ref<'' | ShieldStatus>('');
const shieldStatusVisible = ref(false);
const tools = ref<string[]>([]);
const toolCountMap = ref<Record<string, null | number>>({});
const activeTool = ref('');
const summarySortState = ref<{ order: TableSortOrder; prop: string }>({
  prop: '',
  order: null,
});
const detailKeywordFilters = ref<DetailKeywordFilters>(
  createDetailKeywordFilters(),
);
const detailKeywordDrafts = ref<DetailKeywordFilters>(
  createDetailKeywordFilters(),
);
const detailKeywordVisible = ref<DetailKeywordVisibleState>(
  createDetailKeywordVisibleState(),
);

const expandTabMap = ref<Record<string, string>>({});
const shieldRecordsMap = ref<Record<string, ShieldRecordItem[]>>({});
const shieldRecordsLoadingMap = ref<Record<string, boolean>>({});

const [SummaryGrid, summaryGridApi] = useZqTable({
  gridOptions: {
    border: true,
    stripe: true,
    columns: useSummaryColumns([]),
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page }) => {
          const params: ProjectOverviewQueryParams = {
            page: page.currentPage,
            pageSize: page.pageSize,
          };
          const sortOrder = normalizeSummarySortOrder(
            summarySortState.value.order,
          );
          if (summarySortState.value.prop && sortOrder) {
            params.sort_field = summarySortState.value.prop;
            params.sort_order = sortOrder;
          }

          const res = await listProjectOverviewApi(params);
          const itemsData = res.items || [];
          const total = res.total || 0;

          const toolSet = new Set<string>(ALL_SCAN_TOOLS);
          for (const row of itemsData) {
            const keys = Object.keys(row.tool_counts || {});
            for (const key of keys) toolSet.add(key);
          }
          const extraTools = [...toolSet].filter(
            (tool) => !ALL_SCAN_TOOLS.includes(tool),
          );
          const toolNames = [...ALL_SCAN_TOOLS, ...extraTools];
          summaryGridApi.setGridOptions({
            columns: useSummaryColumns(toolNames),
          });

          const items: ProjectOverviewTableRow[] = itemsData.map(
            (row: ProjectOverviewItem) => {
              const normalizedCounts: Record<string, null | number> = {};
              for (const tool of toolNames) {
                const toolCounts = row.tool_counts || {};
                const hasValue = Object.prototype.hasOwnProperty.call(
                  toolCounts,
                  tool,
                );
                normalizedCounts[tool] = hasValue
                  ? Number(toolCounts[tool] || 0)
                  : null;
              }
              return { ...row, ...normalizedCounts };
            },
          );
          return { items, total };
        },
      },
    },
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [10, 20, 50, 100],
    },
    toolbarConfig: {
      custom: true,
      refresh: true,
      zoom: true,
    },
  },
});

const [DetailGrid, detailGridApi] = useZqTable({
  gridOptions: {
    border: true,
    stripe: true,
    columns: useDetailColumns(),
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({ page }) => {
          if (!projectId.value || !activeTool.value || projectMissing.value) {
            return { items: [], total: 0 };
          }
          const params: LatestResultsQueryParams = {
            tool_name: activeTool.value,
            page: page.currentPage,
            pageSize: page.pageSize,
          };
          if (shieldStatusFilter.value) {
            params.shield_status = shieldStatusFilter.value;
          }
          if (routeSubModules.value) {
            params.sub_modules = routeSubModules.value;
          }
          appendDetailKeywordParams(params);
          const res = await listLatestResultsApi(projectId.value, params);
          return {
            items: res.items || [],
            total: res.total || 0,
          };
        },
      },
    },
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [10, 20, 50, 100],
    },
    toolbarConfig: {
      custom: true,
      refresh: true,
      zoom: true,
    },
  },
});

function displayCount(value: null | number | undefined) {
  if (value === null || value === undefined) return '未扫描';
  return String(value);
}

function normalizeSummarySortOrder(
  order: TableSortOrder,
): 'asc' | 'desc' | undefined {
  if (order === 'ascending') return 'asc';
  if (order === 'descending') return 'desc';
  return undefined;
}

function buildKeywordFilterButtonText(value: string) {
  const normalized = String(value || '').trim();
  if (!normalized) return '筛选';
  return normalized.length > 8 ? `${normalized.slice(0, 8)}...` : normalized;
}

function buildShieldStatusFilterButtonText(value: '' | ShieldStatus) {
  return value || '筛选';
}

function appendDetailKeywordParams(params: LatestResultsQueryParams) {
  const nextParams = params as LatestResultsQueryParams &
    Record<DetailKeywordParamKey, string>;
  for (const config of DETAIL_KEYWORD_FILTER_CONFIGS) {
    const keyword = detailKeywordFilters.value[config.columnKey].trim();
    if (!keyword) continue;
    nextParams[config.paramKey] = keyword;
  }
}

function resetDetailPage() {
  detailGridApi.pagination.currentPage = 1;
  detailGridApi.setGridOptions({
    pagerConfig: {
      currentPage: 1,
    },
  });
}

function resetDetailState() {
  selectedResults.value = [];
  expandTabMap.value = {};
  shieldRecordsMap.value = {};
  shieldRecordsLoadingMap.value = {};
}

function resetDetailFilters() {
  detailKeywordFilters.value = createDetailKeywordFilters();
  detailKeywordDrafts.value = createDetailKeywordFilters();
  detailKeywordVisible.value = createDetailKeywordVisibleState();
  shieldStatusFilter.value = '';
  shieldStatusDraft.value = '';
  shieldStatusVisible.value = false;
}

async function reloadDetailGrid() {
  resetDetailState();
  resetDetailPage();
  await detailGridApi.reload();
}

async function loadTools() {
  if (!projectId.value) return;

  projectMissing.value = false;
  tools.value = [...ALL_SCAN_TOOLS];
  toolCountMap.value = Object.fromEntries(
    ALL_SCAN_TOOLS.map((tool) => [tool, null]),
  );

  const params: ProjectOverviewQueryParams = {
    page: 1,
    pageSize: 1,
    project_id: projectId.value,
  };
  if (routeSubModules.value) {
    params.sub_modules = routeSubModules.value;
  }

  const res = await listProjectOverviewApi(params);
  const project = (res.items || []).find(
    (item) => item.project_id === projectId.value,
  );

  if (!project) {
    projectMissing.value = true;
    tools.value = [];
    toolCountMap.value = {};
    activeTool.value = '';
    resetDetailState();
    return;
  }

  if (project.tool_counts) {
    for (const tool of Object.keys(project.tool_counts)) {
      if (!tools.value.includes(tool)) {
        tools.value.push(tool);
      }
    }
    const merged: Record<string, null | number> = {};
    for (const tool of tools.value) {
      const toolCounts = project.tool_counts || {};
      const hasValue = Object.prototype.hasOwnProperty.call(toolCounts, tool);
      merged[tool] = hasValue ? Number(toolCounts[tool] || 0) : null;
    }
    toolCountMap.value = merged;
  }

  if (preferredTool.value && !tools.value.includes(preferredTool.value)) {
    tools.value.push(preferredTool.value);
    if (!(preferredTool.value in toolCountMap.value)) {
      toolCountMap.value[preferredTool.value] = null;
    }
  }
  if (preferredTool.value && tools.value.includes(preferredTool.value)) {
    activeTool.value = preferredTool.value;
    return;
  }
  if (!activeTool.value || !tools.value.includes(activeTool.value)) {
    activeTool.value = tools.value[0] || '';
  }
}

async function refreshCurrentView() {
  if (isDetail.value) {
    await loadTools();
    if (!projectMissing.value && activeTool.value) {
      detailGridApi.reload();
    }
    return;
  }
  summaryGridApi.reload();
}

function handleSummarySortChange(data: {
  order: TableSortOrder;
  prop?: string;
}) {
  summarySortState.value = {
    prop: String(data.prop || ''),
    order: data.order ?? null,
  };
  summaryGridApi.reload();
}

function handleTabChange() {
  void reloadDetailGrid();
}

function handleKeywordFilterShow(columnKey: DetailKeywordColumnKey) {
  detailKeywordDrafts.value = {
    ...detailKeywordDrafts.value,
    [columnKey]: detailKeywordFilters.value[columnKey],
  };
}

function resetKeywordFilterDraft(columnKey: DetailKeywordColumnKey) {
  detailKeywordDrafts.value = {
    ...detailKeywordDrafts.value,
    [columnKey]: '',
  };
}

async function confirmKeywordFilter(columnKey: DetailKeywordColumnKey) {
  detailKeywordFilters.value = {
    ...detailKeywordFilters.value,
    [columnKey]: detailKeywordDrafts.value[columnKey].trim(),
  };
  detailKeywordVisible.value = {
    ...detailKeywordVisible.value,
    [columnKey]: false,
  };
  await reloadDetailGrid();
}

function handleShieldStatusFilterShow() {
  shieldStatusDraft.value = shieldStatusFilter.value;
}

function resetShieldStatusDraft() {
  shieldStatusDraft.value = '';
}

async function confirmShieldStatusFilter() {
  shieldStatusFilter.value = shieldStatusDraft.value;
  shieldStatusVisible.value = false;
  await reloadDetailGrid();
}

function openProject(row: ProjectOverviewTableRow) {
  router.push({ path: route.path, query: { projectId: row.project_id } });
}

function backToSummary() {
  resetDetailFilters();
  resetDetailState();
  router.push({ path: route.path, query: {} });
}

function handleResultSelectionChange(rows: LatestScanResultItem[]) {
  selectedResults.value = rows;
}

function handleApplyShield() {
  if (selectedResults.value.length === 0) {
    ElMessage.warning('请选择要屏蔽的缺陷');
    return;
  }
  shieldForm.value = {
    approver_id: '',
    reason: '',
    result_ids: selectedResults.value.map((item) => item.id),
  };
  shieldVisible.value = true;
}

async function submitShield() {
  try {
    if (!shieldForm.value.approver_id) {
      ElMessage.warning('请选择审批人');
      return;
    }
    if (!shieldForm.value.reason.trim()) {
      ElMessage.warning('请输入屏蔽理由');
      return;
    }
    await applyShieldApi(shieldForm.value);
    ElMessage.success('申请已提交');
    shieldVisible.value = false;
    selectedResults.value = [];
    shieldForm.value = {
      approver_id: '',
      reason: '',
      result_ids: [],
    };
    detailGridApi.reload();
  } catch {
    ElMessage.error('提交失败');
  }
}

function getSeverityType(severity: string) {
  if (severity === 'High') return 'danger';
  if (severity === 'Medium') return 'warning';
  return 'info';
}

function getStatusType(status: string) {
  if (status === 'Shielded') return 'success';
  if (status === 'Pending') return 'warning';
  if (status === 'Rejected') return 'danger';
  return 'info';
}

function getShieldRecordStatusType(status: string) {
  if (status === 'Approved') return 'success';
  if (status === 'Pending') return 'warning';
  if (status === 'Rejected') return 'danger';
  return 'info';
}

function getExpandTab(resultId: string) {
  return expandTabMap.value[resultId] || 'detail';
}

function isShieldRecordsLoading(resultId: string) {
  return Boolean(shieldRecordsLoadingMap.value[resultId]);
}

async function ensureShieldRecordsLoaded(resultId: string) {
  if (shieldRecordsMap.value[resultId]) return;
  shieldRecordsLoadingMap.value[resultId] = true;
  try {
    const res = await listResultShieldRecordsApi(resultId);
    shieldRecordsMap.value[resultId] = Array.isArray(res) ? res : [];
  } catch {
    shieldRecordsMap.value[resultId] = [];
  } finally {
    shieldRecordsLoadingMap.value[resultId] = false;
  }
}

async function handleExpandTabChange(resultId: string, name: number | string) {
  const tabName = String(name);
  expandTabMap.value[resultId] = tabName;
  if (tabName === 'shield') {
    await ensureShieldRecordsLoaded(resultId);
  }
}

onMounted(async () => {
  await refreshCurrentView();
});

watch(
  () => [
    route.query.projectId,
    route.query.tool,
    route.query.tool_name,
    route.query.sub_modules,
  ],
  async (newValues, oldValues) => {
    const newProjectId = String(newValues[0] || '');
    const oldProjectId = String(oldValues?.[0] || '');
    if (newProjectId !== oldProjectId) {
      resetDetailFilters();
      resetDetailState();
    }
    await refreshCurrentView();
  },
);
</script>

<template>
  <Page title="扫描结果" auto-content-height>
    <template #extra>
      <div v-if="isDetail" class="flex items-center gap-3">
        <ElButton @click="backToSummary">返回</ElButton>
        <ElButton
          type="warning"
          :disabled="projectMissing"
          @click="handleApplyShield"
        >
          申请屏蔽
        </ElButton>
      </div>
    </template>

    <div class="flex h-full min-h-0 flex-col">
      <SummaryGrid
        v-if="!isDetail"
        class="code-scan-data-grid h-full"
        @sort-change="handleSummarySortChange"
      >
        <template #cell-project_name="{ row }">
          <ElButton link type="primary" @click="openProject(row)">
            {{ row.project_name }}
          </ElButton>
        </template>
      </SummaryGrid>

      <div v-else class="flex h-full min-h-0 flex-col">
        <template v-if="projectMissing">
          <div class="flex flex-1 items-center justify-center">
            <ElEmpty description="项目不存在或已删除">
              <ElButton type="primary" @click="backToSummary">
                返回汇总
              </ElButton>
            </ElEmpty>
          </div>
        </template>
        <template v-else>
          <ElTabs
            v-model="activeTool"
            class="mb-2"
            @tab-change="handleTabChange"
          >
            <ElTabPane
              v-for="tool in tools"
              :key="tool"
              :label="`${tool} (${displayCount(toolCountMap[tool])})`"
              :name="tool"
            />
          </ElTabs>
          <div class="min-h-0 flex-1 overflow-hidden">
            <DetailGrid
              :key="projectId || 'detail-grid'"
              class="code-scan-data-grid h-full"
              @selection-change="handleResultSelectionChange"
            >
              <template
                v-for="config in DETAIL_KEYWORD_FILTER_CONFIGS"
                :key="`header-${config.columnKey}`"
                #[`header-${config.columnKey}`]
              >
                <div class="code-scan-header-filter" @click.stop>
                  <span class="code-scan-header-filter__label">
                    {{ config.label }}
                  </span>
                  <ElPopover
                    v-model:visible="detailKeywordVisible[config.columnKey]"
                    placement="bottom-start"
                    trigger="click"
                    :width="config.width"
                    popper-class="code-scan-header-filter-popper"
                    @show="handleKeywordFilterShow(config.columnKey)"
                  >
                    <template #reference>
                      <button
                        type="button"
                        class="code-scan-header-filter-trigger"
                        :class="{
                          'is-active': Boolean(
                            detailKeywordFilters[config.columnKey].trim(),
                          ),
                        }"
                      >
                        <Filter class="code-scan-header-filter-trigger__icon" />
                        <span class="code-scan-header-filter-trigger__text">
                          {{
                            buildKeywordFilterButtonText(
                              detailKeywordFilters[config.columnKey],
                            )
                          }}
                        </span>
                      </button>
                    </template>
                    <div class="code-scan-header-filter-panel" @click.stop>
                      <div class="code-scan-header-filter-panel__body">
                        <ElInput
                          v-model="detailKeywordDrafts[config.columnKey]"
                          size="small"
                          clearable
                          class="code-scan-header-filter-panel__search"
                          :placeholder="config.placeholder"
                        />
                      </div>
                      <div class="code-scan-header-filter-panel__actions">
                        <ElButton
                          size="small"
                          @click="resetKeywordFilterDraft(config.columnKey)"
                        >
                          重置
                        </ElButton>
                        <ElButton
                          type="primary"
                          size="small"
                          @click="confirmKeywordFilter(config.columnKey)"
                        >
                          确认
                        </ElButton>
                      </div>
                    </div>
                  </ElPopover>
                </div>
              </template>

              <template #header-shield_status>
                <div class="code-scan-header-filter" @click.stop>
                  <span class="code-scan-header-filter__label">状态</span>
                  <ElPopover
                    v-model:visible="shieldStatusVisible"
                    placement="bottom-start"
                    trigger="click"
                    :width="220"
                    popper-class="code-scan-header-filter-popper"
                    @show="handleShieldStatusFilterShow"
                  >
                    <template #reference>
                      <button
                        type="button"
                        class="code-scan-header-filter-trigger"
                        :class="{ 'is-active': Boolean(shieldStatusFilter) }"
                      >
                        <Filter class="code-scan-header-filter-trigger__icon" />
                        <span class="code-scan-header-filter-trigger__text">
                          {{
                            buildShieldStatusFilterButtonText(
                              shieldStatusFilter,
                            )
                          }}
                        </span>
                      </button>
                    </template>
                    <div class="code-scan-header-filter-panel" @click.stop>
                      <div class="code-scan-header-filter-panel__body">
                        <ElRadioGroup
                          v-model="shieldStatusDraft"
                          class="code-scan-header-filter-radio-group"
                        >
                          <ElRadio
                            v-for="status in SHIELD_STATUS_OPTIONS"
                            :key="status"
                            :value="status"
                          >
                            {{ status }}
                          </ElRadio>
                        </ElRadioGroup>
                      </div>
                      <div class="code-scan-header-filter-panel__actions">
                        <ElButton size="small" @click="resetShieldStatusDraft">
                          重置
                        </ElButton>
                        <ElButton
                          type="primary"
                          size="small"
                          @click="confirmShieldStatusFilter"
                        >
                          确认
                        </ElButton>
                      </div>
                    </div>
                  </ElPopover>
                </div>
              </template>

              <template #expand_content="{ row }">
                <div class="bg-gray-50 p-4">
                  <ElTabs
                    :model-value="getExpandTab(row.id)"
                    @tab-change="(name) => handleExpandTabChange(row.id, name)"
                  >
                    <ElTabPane label="缺陷详情" name="detail">
                      <ElDescriptions title="详细信息" :column="1" border>
                        <ElDescriptionsItem label="缺陷描述">
                          {{ row.description }}
                        </ElDescriptionsItem>
                        <ElDescriptionsItem label="文件路径">
                          {{ row.file_path }} : {{ row.line_number }}
                        </ElDescriptionsItem>
                        <ElDescriptionsItem
                          v-if="row.help_info"
                          label="修复建议"
                        >
                          {{ row.help_info }}
                        </ElDescriptionsItem>
                        <ElDescriptionsItem
                          v-if="row.code_snippet"
                          label="代码片段"
                        >
                          <pre
                            class="overflow-x-auto rounded bg-gray-800 p-2 text-xs text-white"
                          >
                            {{ row.code_snippet }}
                          </pre>
                        </ElDescriptionsItem>
                      </ElDescriptions>
                    </ElTabPane>
                    <ElTabPane label="屏蔽记录" name="shield">
                      <ElTable
                        v-loading="isShieldRecordsLoading(row.id)"
                        :data="shieldRecordsMap[row.id] || []"
                        border
                        size="small"
                        style="width: 100%"
                      >
                        <ElTableColumn
                          prop="sys_create_datetime"
                          label="时间"
                          width="180"
                        />
                        <ElTableColumn label="状态" width="120">
                          <template #default="{ row: shieldRow }">
                            <ElTag
                              :type="
                                getShieldRecordStatusType(shieldRow.status)
                              "
                            >
                              {{ shieldRow.status }}
                            </ElTag>
                          </template>
                        </ElTableColumn>
                        <ElTableColumn
                          prop="applicant_name"
                          label="申请人"
                          width="120"
                        />
                        <ElTableColumn
                          prop="approver_name"
                          label="审批人"
                          width="120"
                        />
                        <ElTableColumn
                          prop="reason"
                          label="理由"
                          min-width="220"
                        />
                        <ElTableColumn
                          prop="audit_comment"
                          label="审批意见"
                          min-width="220"
                        />
                      </ElTable>
                      <div
                        v-if="
                          !isShieldRecordsLoading(row.id) &&
                          (shieldRecordsMap[row.id]?.length || 0) === 0
                        "
                        class="py-3 text-center text-gray-400"
                      >
                        暂无屏蔽记录
                      </div>
                    </ElTabPane>
                  </ElTabs>
                </div>
              </template>

              <template #cell-severity="{ row }">
                <ElTag :type="getSeverityType(row.severity)">
                  {{ row.severity }}
                </ElTag>
              </template>

              <template #cell-shield_status="{ row }">
                <ElTag :type="getStatusType(row.shield_status)">
                  {{ row.shield_status }}
                </ElTag>
              </template>
            </DetailGrid>
          </div>
        </template>
      </div>
    </div>

    <ElDialog v-model="shieldVisible" title="申请屏蔽" width="500px">
      <ElForm :model="shieldForm" label-width="100px">
        <ElFormItem label="审批人" required>
          <UserSelector
            v-model="shieldForm.approver_id"
            placeholder="请选择审批人"
          />
        </ElFormItem>
        <ElFormItem label="屏蔽理由" required>
          <ElInput
            v-model="shieldForm.reason"
            placeholder="请输入理由"
            type="textarea"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="shieldVisible = false">取消</ElButton>
        <ElButton type="primary" @click="submitShield">提交</ElButton>
      </template>
    </ElDialog>
  </Page>
</template>

<style scoped>
.code-scan-header-filter {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  min-width: 0;
}

.code-scan-header-filter__label {
  font-size: 12px;
  font-weight: 600;
  line-height: 1.3;
  color: #475569;
  white-space: nowrap;
}

.code-scan-header-filter-trigger {
  display: inline-flex;
  gap: 4px;
  align-items: center;
  height: 24px;
  padding: 0 8px;
  font-size: 12px;
  line-height: 1;
  color: #606266;
  cursor: pointer;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  transition:
    color 0.2s ease,
    border-color 0.2s ease,
    background-color 0.2s ease;
}

.code-scan-header-filter-trigger:hover {
  border-color: #c0c4cc;
}

.code-scan-header-filter-trigger.is-active {
  color: #409eff;
  background: #ecf5ff;
  border-color: #a0cfff;
}

.code-scan-header-filter-trigger__icon {
  width: 12px;
  height: 12px;
}

.code-scan-header-filter-trigger__text {
  white-space: nowrap;
}

.code-scan-header-filter-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.code-scan-header-filter-panel__body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 260px;
  padding-right: 4px;
  overflow: auto;
}

.code-scan-header-filter-panel__search {
  position: sticky;
  top: 0;
  z-index: 1;
  padding-bottom: 2px;
  background: #fff;
}

.code-scan-header-filter-radio-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.code-scan-header-filter-panel__actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}

.code-scan-data-grid :deep(.zq-table-header th.el-table__cell) {
  vertical-align: middle;
}

:deep(.code-scan-header-filter-popper.el-popper) {
  padding: 10px 12px;
}

:deep(.code-scan-header-filter-radio-group .el-radio) {
  margin-right: 0;
}
</style>
