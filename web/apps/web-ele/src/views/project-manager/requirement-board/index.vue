<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type {
  RequirementBoardFilterPayload,
  RequirementBoardProjectOption,
  RequirementBoardSummary,
} from '#/api/project-manager/requirement_board';

import { computed, nextTick, onMounted, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

import {
  ElButton,
  ElCard,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElMessage,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus';

import {
  getRequirementBoardDataApi,
  getRequirementBoardFilterOptionsApi,
  getRequirementBoardSummaryApi,
} from '#/api/project-manager/requirement_board';
import { useZqTable } from '#/components/zq-table';

import {
  CATEGORY_OPTIONS,
  createEmptyRequirementSummary,
  DEFAULT_CATEGORIES,
  formatMetric,
  formatPercent,
  STATUS_META,
  useRequirementColumns,
} from './data';

defineOptions({ name: 'RequirementBoard' });

const activeTab = ref('data');
const optionsLoading = ref(false);
const summaryLoading = ref(false);
const projectOptions = ref<RequirementBoardProjectOption[]>([]);
const filters = ref<RequirementBoardFilterPayload>({
  project_ids: [],
  sub_teams: [],
  categories: [...DEFAULT_CATEGORIES],
});
const appliedFilters = ref<null | RequirementBoardFilterPayload>(null);
const summary = ref<RequirementBoardSummary>(createEmptyRequirementSummary());
const summaryFingerprint = ref('');
const statusChartRef = ref<EchartsUIType>();
const { renderEcharts } = useEcharts(statusChartRef);

function normalizeStringArray(values?: string[]) {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const item of values || []) {
    const text = String(item || '').trim();
    if (!text || seen.has(text)) {
      continue;
    }
    seen.add(text);
    result.push(text);
  }
  return result;
}

function cloneFilterPayload(source: RequirementBoardFilterPayload) {
  const categories = normalizeStringArray(source.categories);
  return {
    project_ids: normalizeStringArray(source.project_ids),
    sub_teams: normalizeStringArray(source.sub_teams),
    categories: categories.length > 0 ? categories : [...DEFAULT_CATEGORIES],
  };
}

function buildFingerprint(payload: null | RequirementBoardFilterPayload) {
  if (!payload) {
    return '';
  }
  return JSON.stringify({
    project_ids: [...(payload.project_ids || [])].sort(),
    sub_teams: [...(payload.sub_teams || [])].sort(),
    categories: [...(payload.categories || [])].sort(),
  });
}

const configuredProjectOptions = computed(() =>
  projectOptions.value.filter((item) => item.config_complete),
);

const selectedProjects = computed(() => {
  const projectMap = new Map(
    projectOptions.value.map((item) => [item.id, item]),
  );
  return normalizeStringArray(filters.value.project_ids)
    .map((item) => projectMap.get(item))
    .filter(
      (item): item is RequirementBoardProjectOption => item !== undefined,
    );
});

const teamOptions = computed(() => {
  const seen = new Set<string>();
  const result: Array<{ label: string; value: string }> = [];
  selectedProjects.value.forEach((project) => {
    (project.sub_teams || []).forEach((team) => {
      const text = String(team || '').trim();
      if (!text || seen.has(text)) {
        return;
      }
      seen.add(text);
      result.push({ label: text, value: text });
    });
  });
  return result;
});

const hasAppliedFilters = computed(() => Boolean(appliedFilters.value));
const dataResultCount = computed(() => Number(gridApi.total.value || 0));
const selectedCategoryCount = computed(() => {
  const categories = normalizeStringArray(filters.value.categories);
  return categories.length > 0 ? categories.length : DEFAULT_CATEGORIES.length;
});
const statusCards = computed(() => {
  const countMap = new Map(
    (summary.value.status_summary || []).map((item) => [
      item.status_code,
      item.count,
    ]),
  );
  return STATUS_META.map((item) => ({
    ...item,
    count: Number(countMap.get(item.status_code) || 0),
  }));
});

function getStatusValue(
  row: RequirementBoardSummary['team_summary'][number],
  code: string,
) {
  switch (code) {
    case 'A': {
      return row.a_count;
    }
    case 'C': {
      return row.c_count;
    }
    case 'D': {
      return row.d_count;
    }
    case 'I': {
      return row.i_count;
    }
    case 'P': {
      return row.p_count;
    }
    default: {
      return 0;
    }
  }
}

function getCategoryTagType(category: string) {
  if (category === 'AR') return 'danger';
  if (category === 'DR') return 'warning';
  if (category === 'SR') return 'success';
  return 'info';
}

function getStatusBadgeClass(statusCode: string) {
  return `requirement-status-badge requirement-status-badge--${String(
    statusCode || 'I',
  ).toLowerCase()}`;
}

function getTeamTagType(teamName: string) {
  const normalized = String(teamName || '').trim();
  if (!normalized || normalized === '未识别团队') {
    return 'info';
  }

  const palette = ['primary', 'success', 'warning', 'danger', 'info'];
  let hash = 0;
  for (const char of normalized) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  }
  return palette[hash % palette.length];
}

async function loadFilterOptions() {
  optionsLoading.value = true;
  try {
    const result = await getRequirementBoardFilterOptionsApi();
    projectOptions.value = result.projects || [];
  } catch (error) {
    console.error(error);
    ElMessage.error('加载需求看板筛选项失败');
  } finally {
    optionsLoading.value = false;
  }
}

const [Grid, gridApi] = useZqTable({
  gridOptions: {
    columns: useRequirementColumns(),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({
          page,
        }: {
          page: { currentPage: number; pageSize: number };
        }) => {
          if (!appliedFilters.value) {
            return { items: [], total: 0 };
          }
          const response = await getRequirementBoardDataApi({
            ...appliedFilters.value,
            page_no: page.currentPage,
            page_size: page.pageSize,
          });
          return { items: response.items || [], total: response.total || 0 };
        },
      },
    },
    pagerConfig: {
      enabled: true,
      pageSize: 20,
    },
    toolbarConfig: {
      custom: true,
      refresh: true,
      zoom: true,
    },
  },
});

async function fetchSummary(force = false) {
  if (!appliedFilters.value) {
    summary.value = createEmptyRequirementSummary();
    summaryFingerprint.value = '';
    return;
  }

  const currentFingerprint = buildFingerprint(appliedFilters.value);
  if (!force && summaryFingerprint.value === currentFingerprint) {
    return;
  }

  summaryLoading.value = true;
  try {
    summary.value = await getRequirementBoardSummaryApi(appliedFilters.value);
    summaryFingerprint.value = currentFingerprint;
  } catch (error) {
    console.error(error);
    ElMessage.error('加载需求总结失败');
  } finally {
    summaryLoading.value = false;
  }
}

async function handleSearch() {
  const payload = cloneFilterPayload(filters.value);
  if (payload.project_ids.length === 0) {
    ElMessage.warning('请至少选择一个项目');
    return;
  }

  appliedFilters.value = payload;
  summaryFingerprint.value = '';
  gridApi.pagination.currentPage = 1;
  await nextTick();
  await gridApi.reload();
  if (activeTab.value === 'summary') {
    await fetchSummary(true);
  }
}

function clearGridData() {
  gridApi.tableData.value = [];
  gridApi.total.value = 0;
  gridApi.pagination.total = 0;
}

async function handleReset() {
  filters.value = {
    project_ids: [],
    sub_teams: [],
    categories: [...DEFAULT_CATEGORIES],
  };
  appliedFilters.value = null;
  summary.value = createEmptyRequirementSummary();
  summaryFingerprint.value = '';
  gridApi.pagination.currentPage = 1;
  clearGridData();
}

watch(
  () => filters.value.project_ids,
  () => {
    const available = new Set(teamOptions.value.map((item) => item.value));
    filters.value.sub_teams = normalizeStringArray(
      filters.value.sub_teams,
    ).filter((item) => available.has(item));
  },
  { deep: true },
);

watch(
  () => activeTab.value,
  async (value) => {
    if (value === 'summary' && appliedFilters.value) {
      await fetchSummary();
    }
  },
);

watch(
  () => summary.value.team_summary,
  (rows) => {
    if (rows.length === 0) {
      renderEcharts({
        title: {
          text: '暂无团队分布数据',
          left: 'center',
          top: 'middle',
          textStyle: {
            color: '#94a3b8',
            fontSize: 14,
            fontWeight: 400,
          },
        },
        xAxis: { show: false },
        yAxis: { show: false },
        series: [],
      });
      return;
    }

    const colors: Record<string, string> = {
      I: '#ef4444',
      D: '#38bdf8',
      P: '#6366f1',
      C: '#f59e0b',
      A: '#22c55e',
    };

    renderEcharts({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { type: 'scroll', bottom: 0 },
      grid: { left: '3%', right: '4%', bottom: '14%', containLabel: true },
      xAxis: { type: 'value' },
      yAxis: {
        type: 'category',
        data: rows.map((item) => item.team_name),
      },
      series: STATUS_META.map((item) => ({
        name: `${item.status_code} · ${item.status_label}`,
        type: 'bar',
        stack: 'total',
        emphasis: { focus: 'series' },
        itemStyle: { color: colors[item.status_code] },
        data: rows.map((row) => getStatusValue(row, item.status_code)),
      })),
    });
  },
  { deep: true, immediate: true },
);

onMounted(async () => {
  await loadFilterOptions();
});
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full min-h-0 flex-col gap-4">
      <ElCard shadow="never">
        <ElForm inline :model="filters" class="requirement-filter-form">
          <ElFormItem label="项目">
            <ElSelect
              v-model="filters.project_ids"
              class="!w-[320px]"
              collapse-tags
              collapse-tags-tooltip
              filterable
              multiple
              clearable
              :loading="optionsLoading"
              placeholder="请选择项目"
            >
              <ElOption
                v-for="item in projectOptions"
                :key="item.id"
                :label="
                  item.config_complete
                    ? item.name
                    : `${item.name}（未完成配置）`
                "
                :value="item.id"
                :disabled="!item.config_complete"
              />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="责任团队">
            <ElSelect
              v-model="filters.sub_teams"
              class="!w-[260px]"
              collapse-tags
              collapse-tags-tooltip
              filterable
              multiple
              clearable
              :disabled="selectedProjects.length === 0"
              placeholder="按所选项目动态生成"
            >
              <ElOption
                v-for="item in teamOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="需求类型">
            <ElSelect
              v-model="filters.categories"
              class="!w-[220px]"
              collapse-tags
              collapse-tags-tooltip
              filterable
              multiple
              clearable
              placeholder="默认全选"
            >
              <ElOption
                v-for="item in CATEGORY_OPTIONS"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </ElSelect>
          </ElFormItem>
          <ElFormItem>
            <ElButton type="primary" @click="handleSearch">查询</ElButton>
            <ElButton @click="handleReset">重置</ElButton>
          </ElFormItem>
        </ElForm>
        <div class="mt-3 text-xs text-slate-500">
          当前可查询项目
          {{ configuredProjectOptions.length }}
          个；需求数据源配置不完整的项目会自动禁用。
        </div>
      </ElCard>

      <ElTabs
        v-model="activeTab"
        class="requirement-board-tabs flex h-full min-h-0 flex-1 flex-col"
      >
        <ElTabPane label="需求数据看板" name="data">
          <div class="flex h-full min-h-0 flex-col">
            <ElCard shadow="never" class="requirement-data-card h-full min-h-0">
              <template #header>
                <div class="requirement-data-card__header">
                  <div>
                    <div class="requirement-data-card__title">需求明细表</div>
                    <div class="requirement-data-card__desc">
                      按当前筛选条件展示分页后的需求明细，支持横向滚动查看项目、团队、状态与工作量字段。
                    </div>
                  </div>
                  <ElTag
                    class="requirement-data-card__status"
                    :effect="hasAppliedFilters ? 'light' : 'plain'"
                    :type="hasAppliedFilters ? 'success' : 'info'"
                  >
                    {{
                      hasAppliedFilters
                        ? `已加载 ${dataResultCount} 条结果`
                        : '等待查询'
                    }}
                  </ElTag>
                </div>
              </template>

              <div v-if="hasAppliedFilters" class="requirement-data-card__body">
                <Grid class="h-full">
                  <template #cell-team_name="{ row }">
                    <ElTag
                      :type="getTeamTagType(row.team_name)"
                      effect="light"
                      class="requirement-team-badge"
                    >
                      <span class="requirement-team-badge__text">
                        {{ row.team_name || '未识别团队' }}
                      </span>
                    </ElTag>
                  </template>
                  <template #cell-category="{ row }">
                    <ElTag
                      :type="getCategoryTagType(row.category)"
                      effect="plain"
                      class="requirement-category-badge"
                    >
                      {{ row.category }}
                    </ElTag>
                  </template>
                  <template #cell-status_code="{ row }">
                    <ElTag
                      :class="getStatusBadgeClass(row.status_code)"
                      effect="plain"
                    >
                      <span class="requirement-status-dot" />
                      {{ row.status_code }} · {{ row.status_label }}
                    </ElTag>
                  </template>
                  <template #cell-workload_kloc="{ row }">
                    {{ formatMetric(row.workload_kloc) }}
                  </template>
                  <template #cell-workload_man_day="{ row }">
                    {{ formatMetric(row.workload_man_day) }}
                  </template>
                </Grid>
              </div>

              <div v-else class="requirement-data-guide">
                <div class="requirement-data-guide__panel">
                  <div class="requirement-data-guide__eyebrow">需求数据看板</div>
                  <div class="requirement-data-guide__title">
                    先选择筛选条件，再拉取需求明细数据
                  </div>
                  <div class="requirement-data-guide__desc">
                    数据看板不会预加载全量需求。请选择项目，可按项目动态筛选责任团队，并按需求类型组合查询。
                  </div>

                  <div class="requirement-guide-steps">
                    <div class="requirement-guide-step">
                      <div class="requirement-guide-step__index">1</div>
                      <div class="requirement-guide-step__title">选择项目</div>
                      <div class="requirement-guide-step__desc">
                        当前已选 {{ filters.project_ids.length }} 个项目；未完成配置的项目已自动禁用。
                      </div>
                    </div>
                    <div class="requirement-guide-step">
                      <div class="requirement-guide-step__index">2</div>
                      <div class="requirement-guide-step__title">选择责任团队</div>
                      <div class="requirement-guide-step__desc">
                        团队选项会随项目自动去重生成；当前已选 {{ filters.sub_teams?.length || 0 }} 个团队。
                      </div>
                    </div>
                    <div class="requirement-guide-step">
                      <div class="requirement-guide-step__index">3</div>
                      <div class="requirement-guide-step__title">点击查询</div>
                      <div class="requirement-guide-step__desc">
                        需求类型默认全选；当前生效 {{ selectedCategoryCount }} 种类型。
                      </div>
                    </div>
                  </div>

                  <div class="mt-6 flex flex-wrap items-center gap-3">
                    <ElButton type="primary" @click="handleSearch">
                      开始查询明细
                    </ElButton>
                    <span class="text-xs text-slate-500">
                      查询后将保留筛选条件，可直接切换到总结看板查看团队汇总。
                    </span>
                  </div>
                </div>
              </div>
            </ElCard>
          </div>
        </ElTabPane>

        <ElTabPane label="需求总结看板" name="summary">
          <div
            v-loading="summaryLoading"
            class="requirement-summary-panel h-full space-y-4 overflow-auto pb-4"
          >
            <ElEmpty
              v-if="!hasAppliedFilters"
              description="请选择项目并点击查询后查看总结"
            />
            <template v-else>
              <div class="summary-grid">
                <ElCard
                  shadow="never"
                  class="summary-card summary-card--primary"
                >
                  <div class="summary-card__label">总需求数</div>
                  <div class="summary-card__value">
                    {{ summary.total_count }}
                  </div>
                </ElCard>
                <ElCard shadow="never" class="summary-card">
                  <div class="summary-card__label">总工作量(人天)</div>
                  <div class="summary-card__value">
                    {{ formatMetric(summary.total_workload_man_day) }}
                  </div>
                </ElCard>
                <ElCard shadow="never" class="summary-card">
                  <div class="summary-card__label">总代码量(KLOC)</div>
                  <div class="summary-card__value">
                    {{ formatMetric(summary.total_workload_kloc) }}
                  </div>
                </ElCard>
                <ElCard
                  v-for="item in statusCards"
                  :key="item.status_code"
                  shadow="never"
                  class="summary-card"
                >
                  <div class="summary-card__label">
                    {{ item.status_code }} · {{ item.status_label }}
                  </div>
                  <div class="summary-card__value">{{ item.count }}</div>
                </ElCard>
              </div>

              <div class="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
                <ElCard shadow="never" header="团队状态堆叠图">
                  <div class="h-[420px] w-full">
                    <EchartsUI ref="statusChartRef" />
                  </div>
                </ElCard>
                <ElCard shadow="never" header="类型分布">
                  <ElTable :data="summary.type_summary" size="small">
                    <ElTableColumn
                      prop="category"
                      label="需求类型"
                      min-width="110"
                    />
                    <ElTableColumn
                      prop="total_count"
                      label="数量"
                      min-width="90"
                    />
                    <ElTableColumn label="工作量(人天)" min-width="120">
                      <template #default="{ row }">
                        {{ formatMetric(row.total_workload_man_day) }}
                      </template>
                    </ElTableColumn>
                    <ElTableColumn label="代码量(KLOC)" min-width="120">
                      <template #default="{ row }">
                        {{ formatMetric(row.total_workload_kloc) }}
                      </template>
                    </ElTableColumn>
                  </ElTable>
                </ElCard>
              </div>

              <ElCard shadow="never" header="团队完成统计">
                <ElTable :data="summary.team_summary" size="small">
                  <ElTableColumn
                    prop="team_name"
                    label="团队"
                    min-width="150"
                    fixed="left"
                  />
                  <ElTableColumn
                    prop="total_count"
                    label="总需求数"
                    min-width="100"
                  />
                  <ElTableColumn label="总工作量(人天)" min-width="130">
                    <template #default="{ row }">
                      {{ formatMetric(row.total_workload_man_day) }}
                    </template>
                  </ElTableColumn>
                  <ElTableColumn label="总代码量(KLOC)" min-width="130">
                    <template #default="{ row }">
                      {{ formatMetric(row.total_workload_kloc) }}
                    </template>
                  </ElTableColumn>
                  <ElTableColumn prop="i_count" label="I" min-width="80" />
                  <ElTableColumn prop="d_count" label="D" min-width="80" />
                  <ElTableColumn prop="p_count" label="P" min-width="80" />
                  <ElTableColumn prop="c_count" label="C" min-width="80" />
                  <ElTableColumn prop="a_count" label="A" min-width="80" />
                  <ElTableColumn label="开发完成 数量/占比" min-width="150">
                    <template #default="{ row }">
                      {{ row.dev_done.count }} /
                      {{ formatPercent(row.dev_done.count_rate) }}
                    </template>
                  </ElTableColumn>
                  <ElTableColumn label="开发完成 人天/占比" min-width="170">
                    <template #default="{ row }">
                      {{ formatMetric(row.dev_done.workload_man_day) }} /
                      {{ formatPercent(row.dev_done.workload_man_day_rate) }}
                    </template>
                  </ElTableColumn>
                  <ElTableColumn label="开发完成 KLOC/占比" min-width="170">
                    <template #default="{ row }">
                      {{ formatMetric(row.dev_done.workload_kloc) }} /
                      {{ formatPercent(row.dev_done.workload_kloc_rate) }}
                    </template>
                  </ElTableColumn>
                  <ElTableColumn label="验收完成 数量/占比" min-width="150">
                    <template #default="{ row }">
                      {{ row.acceptance_done.count }} /
                      {{ formatPercent(row.acceptance_done.count_rate) }}
                    </template>
                  </ElTableColumn>
                  <ElTableColumn label="验收完成 人天/占比" min-width="170">
                    <template #default="{ row }">
                      {{ formatMetric(row.acceptance_done.workload_man_day) }} /
                      {{
                        formatPercent(row.acceptance_done.workload_man_day_rate)
                      }}
                    </template>
                  </ElTableColumn>
                  <ElTableColumn label="验收完成 KLOC/占比" min-width="170">
                    <template #default="{ row }">
                      {{ formatMetric(row.acceptance_done.workload_kloc) }} /
                      {{
                        formatPercent(row.acceptance_done.workload_kloc_rate)
                      }}
                    </template>
                  </ElTableColumn>
                </ElTable>
              </ElCard>

              <ElCard shadow="never" header="项目分布">
                <ElTable :data="summary.project_summary" size="small">
                  <ElTableColumn
                    prop="project_name"
                    label="项目"
                    min-width="180"
                  />
                  <ElTableColumn
                    prop="total_count"
                    label="需求数量"
                    min-width="100"
                  />
                  <ElTableColumn label="工作量(人天)" min-width="120">
                    <template #default="{ row }">
                      {{ formatMetric(row.total_workload_man_day) }}
                    </template>
                  </ElTableColumn>
                  <ElTableColumn label="代码量(KLOC)" min-width="120">
                    <template #default="{ row }">
                      {{ formatMetric(row.total_workload_kloc) }}
                    </template>
                  </ElTableColumn>
                </ElTable>
              </ElCard>
            </template>
          </div>
        </ElTabPane>
      </ElTabs>
    </div>
  </Page>
</template>

<style scoped>
.requirement-filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.summary-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.summary-card {
  border-radius: 16px;
}

.summary-card--primary {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
}

.summary-card__label {
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.summary-card__value {
  color: #0f172a;
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
  margin-top: 10px;
}

.requirement-board-tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}

.requirement-board-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.requirement-board-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
}

.requirement-board-tabs :deep(.el-tab-pane) {
  height: 100%;
  min-height: 0;
}

.requirement-summary-panel {
  padding-right: 4px;
}
</style>
