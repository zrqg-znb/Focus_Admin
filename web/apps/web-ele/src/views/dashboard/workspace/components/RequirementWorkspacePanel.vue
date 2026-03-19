<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type {
  RequirementWorkspaceFieldKey,
  RequirementWorkspaceLatest,
  RequirementWorkspaceProjectFieldStat,
  RequirementWorkspaceProjectRow,
  RequirementWorkspaceScope,
} from '#/api/project-manager/requirement_workspace';

import { computed, nextTick, onMounted, ref, watch } from 'vue';

import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

import {
  ElButton,
  ElCard,
  ElEmpty,
  ElMessage,
  ElOption,
  ElSelect,
  ElSkeleton,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import {
  getRequirementWorkspaceLatestApi,
  refreshRequirementWorkspaceApi,
} from '#/api/project-manager/requirement_workspace';

const props = withDefaults(
  defineProps<{
    scope?: RequirementWorkspaceScope;
  }>(),
  {
    scope: 'all',
  },
);

type RequirementWorkspaceSortValue =
  | 'acceptance_delay'
  | 'completion_score'
  | 'delay_total'
  | 'development_delay'
  | 'selected_missing'
  | `field:${RequirementWorkspaceFieldKey}`;

interface FieldOption {
  accent: string;
  label: string;
  value: RequirementWorkspaceFieldKey;
}

interface EnrichedProjectRow extends RequirementWorkspaceProjectRow {
  delayTotal: number;
  selectedApplicableCount: number;
  selectedMissingCount: number;
  selectedMissingRate: number;
}

const FIELD_OPTIONS: FieldOption[] = [
  {
    value: 'planned_test_time',
    label: '计划转测时间',
    accent: '#2563eb',
  },
  {
    value: 'due_date',
    label: '计划完成时间',
    accent: '#0f766e',
  },
  {
    value: 'develop_users',
    label: '开发责任人',
    accent: '#7c3aed',
  },
  {
    value: 'test_users',
    label: '测试责任人',
    accent: '#0369a1',
  },
  {
    value: 'workload_man_day',
    label: '工作量(人天)',
    accent: '#ea580c',
  },
  {
    value: 'workload_kloc',
    label: '代码量(KLOC)',
    accent: '#dc2626',
  },
];

const EMPTY_SNAPSHOT: RequirementWorkspaceLatest = {
  generated_at: null,
  scope: '',
  project_count: 0,
  requirement_count: 0,
  field_overview: [],
  project_rows: [],
  missing_previews: {
    planned_test_time: [],
    due_date: [],
    develop_users: [],
    test_users: [],
    workload_man_day: [],
    workload_kloc: [],
  },
  delay_previews: {
    development: [],
    acceptance: [],
  },
};

const SORT_OPTIONS: Array<{
  label: string;
  value: RequirementWorkspaceSortValue;
}> = [
  { label: '按合规分数', value: 'completion_score' },
  { label: '按选中字段缺失数', value: 'selected_missing' },
  { label: '按开发延期数', value: 'development_delay' },
  { label: '按测试延期数', value: 'acceptance_delay' },
  { label: '按总延期数', value: 'delay_total' },
  ...FIELD_OPTIONS.map((item) => ({
    label: `按${item.label}缺失数`,
    value: `field:${item.value}` as const,
  })),
];

const snapshot = ref<RequirementWorkspaceLatest>({ ...EMPTY_SNAPSHOT });
const loading = ref(true);
const refreshing = ref(false);
const selectedFields = ref<RequirementWorkspaceFieldKey[]>(
  FIELD_OPTIONS.map((item) => item.value),
);
const selectedSort = ref<RequirementWorkspaceSortValue>('completion_score');

const fieldOverviewChartRef = ref<EchartsUIType>();
const { renderEcharts: renderFieldOverviewChart } = useEcharts(
  fieldOverviewChartRef,
);
const missingProjectChartRef = ref<EchartsUIType>();
const { renderEcharts: renderMissingProjectChart } = useEcharts(
  missingProjectChartRef,
);
const delayProjectChartRef = ref<EchartsUIType>();
const { renderEcharts: renderDelayProjectChart } =
  useEcharts(delayProjectChartRef);

function getFieldMeta(fieldKey: RequirementWorkspaceFieldKey): FieldOption {
  return (
    FIELD_OPTIONS.find((item) => item.value === fieldKey) || FIELD_OPTIONS[0]!
  );
}

function createErrorMessage(error: unknown) {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return '请求失败，请稍后重试';
}

function createEmptyChartOption(message: string) {
  return {
    graphic: {
      type: 'text',
      left: 'center',
      top: 'middle',
      style: {
        fill: '#94a3b8',
        fontSize: 14,
        text: message,
      },
    },
    xAxis: {
      show: false,
    },
    yAxis: {
      show: false,
    },
    series: [],
  };
}

function formatPercent(value?: null | number) {
  const numeric = Number(value || 0);
  return `${(numeric * 100).toFixed(1)}%`;
}

function formatGeneratedAt(value?: null | string) {
  if (!value) {
    return '--';
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  const pad = (item: number) => String(item).padStart(2, '0');
  return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())} ${pad(parsed.getHours())}:${pad(parsed.getMinutes())}`;
}

function resolveDataIndex(params: unknown) {
  if (!Array.isArray(params) || params.length === 0) {
    return 0;
  }
  const [firstItem] = params as Array<{ dataIndex?: number }>;
  return Number(firstItem?.dataIndex || 0);
}

function getFieldStat(
  row: RequirementWorkspaceProjectRow,
  fieldKey: RequirementWorkspaceFieldKey,
): RequirementWorkspaceProjectFieldStat {
  return row.fields[fieldKey];
}

const panelTitle = computed(() =>
  props.scope === 'favorites' ? '收藏项目交付合规看板' : '需求交付合规看板',
);
const panelDescription = computed(() =>
  props.scope === 'favorites'
    ? '聚焦当前收藏项目的计划字段、责任人、工作量填写率与延期情况。'
    : '基于每日快照展示项目计划字段、责任人、工作量填写率与延期情况。',
);
const projectTagLabel = computed(() =>
  props.scope === 'favorites' ? '收藏项目' : '配置项目',
);
const emptyProjectDescription = computed(() =>
  props.scope === 'favorites' ? '暂无已配置收藏项目' : '暂无已配置项目',
);
const emptySnapshotDescription = computed(() =>
  props.scope === 'favorites'
    ? '尚未生成收藏项目交付合规快照'
    : '尚未生成需求交付合规快照',
);

const hasConfiguredProjects = computed(
  () => Number(snapshot.value.project_count || 0) > 0,
);
const hasSnapshot = computed(() => Boolean(snapshot.value.generated_at));
const effectiveSelectedFields = computed<RequirementWorkspaceFieldKey[]>(() =>
  selectedFields.value.length > 0
    ? [...selectedFields.value]
    : FIELD_OPTIONS.map((item) => item.value),
);
const visibleFieldOverview = computed(() => {
  const selected = new Set(effectiveSelectedFields.value);
  return snapshot.value.field_overview.filter((item) =>
    selected.has(item.field_key),
  );
});
const delayIssueCount = computed(() =>
  snapshot.value.project_rows.reduce(
    (total, row) =>
      total +
      Number(row.delay.development_count || 0) +
      Number(row.delay.acceptance_count || 0),
    0,
  ),
);
const averageFilledRate = computed(() => {
  const rows = visibleFieldOverview.value;
  if (rows.length === 0) {
    return 0;
  }
  return (
    rows.reduce((total, row) => total + Number(row.filled_rate || 0), 0) /
    rows.length
  );
});

const projectRows = computed<EnrichedProjectRow[]>(() => {
  const selected = effectiveSelectedFields.value;
  return snapshot.value.project_rows.map((row) => {
    const selectedApplicableCount = selected.reduce(
      (total, fieldKey) =>
        total + Number(getFieldStat(row, fieldKey).applicable_count || 0),
      0,
    );
    const selectedMissingCount = selected.reduce(
      (total, fieldKey) =>
        total + Number(getFieldStat(row, fieldKey).missing_count || 0),
      0,
    );
    const delayTotal =
      Number(row.delay.development_count || 0) +
      Number(row.delay.acceptance_count || 0);
    return {
      ...row,
      delayTotal,
      selectedApplicableCount,
      selectedMissingCount,
      selectedMissingRate: selectedApplicableCount
        ? selectedMissingCount / selectedApplicableCount
        : 0,
    };
  });
});

const missingTopProjects = computed(() =>
  [...projectRows.value]
    .filter((row) => row.selectedMissingCount > 0)
    .sort(
      (left, right) =>
        right.selectedMissingCount - left.selectedMissingCount ||
        right.total_count - left.total_count ||
        left.project_name.localeCompare(right.project_name, 'zh-CN'),
    )
    .slice(0, 10),
);

const delayTopProjects = computed(() =>
  [...projectRows.value]
    .filter((row) => row.delayTotal > 0)
    .sort(
      (left, right) =>
        right.delayTotal - left.delayTotal ||
        right.total_count - left.total_count ||
        left.project_name.localeCompare(right.project_name, 'zh-CN'),
    )
    .slice(0, 10),
);

const selectedMissingLabel = computed(() => {
  if (effectiveSelectedFields.value.length === 1) {
    return `${getFieldMeta(effectiveSelectedFields.value[0]!).label}缺失`;
  }
  return '选中字段缺失';
});

const sortedTableRows = computed(() => {
  const rows = [...projectRows.value];
  const sortMode = selectedSort.value;

  rows.sort((left, right) => {
    if (sortMode === 'completion_score') {
      return (
        right.completion_score - left.completion_score ||
        right.total_count - left.total_count ||
        left.project_name.localeCompare(right.project_name, 'zh-CN')
      );
    }
    if (sortMode === 'selected_missing') {
      return (
        right.selectedMissingCount - left.selectedMissingCount ||
        right.selectedMissingRate - left.selectedMissingRate ||
        left.project_name.localeCompare(right.project_name, 'zh-CN')
      );
    }
    if (sortMode === 'development_delay') {
      return (
        right.delay.development_count - left.delay.development_count ||
        right.total_count - left.total_count ||
        left.project_name.localeCompare(right.project_name, 'zh-CN')
      );
    }
    if (sortMode === 'acceptance_delay') {
      return (
        right.delay.acceptance_count - left.delay.acceptance_count ||
        right.total_count - left.total_count ||
        left.project_name.localeCompare(right.project_name, 'zh-CN')
      );
    }
    if (sortMode === 'delay_total') {
      return (
        right.delayTotal - left.delayTotal ||
        right.total_count - left.total_count ||
        left.project_name.localeCompare(right.project_name, 'zh-CN')
      );
    }

    const [, fieldKey] = sortMode.split(':') as [
      string,
      RequirementWorkspaceFieldKey,
    ];
    return (
      getFieldStat(right, fieldKey).missing_count -
        getFieldStat(left, fieldKey).missing_count ||
      getFieldStat(left, fieldKey).filled_rate -
        getFieldStat(right, fieldKey).filled_rate ||
      left.project_name.localeCompare(right.project_name, 'zh-CN')
    );
  });

  return rows;
});

async function loadSnapshot() {
  loading.value = true;
  try {
    snapshot.value = await getRequirementWorkspaceLatestApi(props.scope);
  } catch (error) {
    console.error('Failed to load requirement workspace snapshot', error);
    ElMessage.error(`加载需求交付合规看板失败：${createErrorMessage(error)}`);
    snapshot.value = { ...EMPTY_SNAPSHOT };
  } finally {
    loading.value = false;
  }
}

async function refreshSnapshot() {
  refreshing.value = true;
  try {
    snapshot.value = await refreshRequirementWorkspaceApi(props.scope);
    ElMessage.success('需求交付合规快照已刷新');
  } catch (error) {
    console.error('Failed to refresh requirement workspace snapshot', error);
    ElMessage.error(`刷新失败：${createErrorMessage(error)}`);
  } finally {
    refreshing.value = false;
  }
}

async function renderFieldOverviewChartView() {
  await nextTick();
  const rows = visibleFieldOverview.value;
  if (rows.length === 0) {
    await renderFieldOverviewChart(createEmptyChartOption('暂无字段统计数据'));
    return;
  }

  await renderFieldOverviewChart({
    color: rows.map((item) => getFieldMeta(item.field_key).accent),
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const current = rows[resolveDataIndex(params)];
        if (!current) {
          return '';
        }
        return [
          current.field_label,
          `填写率：${formatPercent(current.filled_rate)}`,
          `已填：${current.filled_count}`,
          `缺失：${current.missing_count}`,
          `适用：${current.applicable_count}`,
        ].join('<br/>');
      },
    },
    grid: {
      left: '4%',
      right: '4%',
      bottom: '8%',
      top: '12%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: rows.map((item) => item.field_label),
      axisLabel: {
        interval: 0,
        rotate: rows.length > 4 ? 18 : 0,
      },
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: {
        formatter: '{value}%',
      },
    },
    series: [
      {
        type: 'bar',
        barWidth: 26,
        label: {
          show: true,
          position: 'top',
          formatter: ({ value }: { value: number }) =>
            `${Number(value || 0).toFixed(1)}%`,
        },
        itemStyle: {
          borderRadius: [8, 8, 0, 0],
        },
        data: rows.map((item) => Number((item.filled_rate * 100).toFixed(1))),
      },
    ],
  });
}

async function renderMissingProjectChartView() {
  await nextTick();
  const rows = missingTopProjects.value;
  if (rows.length === 0) {
    await renderMissingProjectChart(
      createEmptyChartOption('当前筛选字段没有缺失项目'),
    );
    return;
  }

  await renderMissingProjectChart({
    color: ['#ef4444'],
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow',
      },
      formatter: (params: unknown) => {
        const current = rows[resolveDataIndex(params)];
        if (!current) {
          return '';
        }
        const details = effectiveSelectedFields.value.map((fieldKey) => {
          const fieldStat = getFieldStat(current, fieldKey);
          return `${getFieldMeta(fieldKey).label}：${fieldStat.missing_count}`;
        });
        return [
          current.project_name,
          `缺失数：${current.selectedMissingCount}`,
          `缺失率：${formatPercent(current.selectedMissingRate)}`,
          ...details,
        ].join('<br/>');
      },
    },
    grid: {
      left: '4%',
      right: '5%',
      bottom: '4%',
      top: '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'value',
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: rows.map((item) => item.project_name),
    },
    series: [
      {
        type: 'bar',
        barWidth: 18,
        data: rows.map((item) => item.selectedMissingCount),
        label: {
          show: true,
          position: 'right',
        },
        itemStyle: {
          borderRadius: [0, 8, 8, 0],
        },
      },
    ],
  });
}

async function renderDelayProjectChartView() {
  await nextTick();
  const rows = delayTopProjects.value;
  if (rows.length === 0) {
    await renderDelayProjectChart(
      createEmptyChartOption('当前项目暂无延期需求'),
    );
    return;
  }

  await renderDelayProjectChart({
    color: ['#ea580c', '#dc2626'],
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow',
      },
    },
    legend: {
      top: 0,
    },
    grid: {
      left: '4%',
      right: '4%',
      bottom: '8%',
      top: '12%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: rows.map((item) => item.project_name),
      axisLabel: {
        interval: 0,
        rotate: rows.length > 4 ? 18 : 0,
      },
    },
    yAxis: {
      type: 'value',
    },
    series: [
      {
        name: '开发延期',
        type: 'bar',
        barWidth: 16,
        data: rows.map((item) => item.delay.development_count),
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
        },
      },
      {
        name: '测试延期',
        type: 'bar',
        barWidth: 16,
        data: rows.map((item) => item.delay.acceptance_count),
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
        },
      },
    ],
  });
}

async function renderAllCharts() {
  if (!hasSnapshot.value || !hasConfiguredProjects.value) {
    return;
  }
  await Promise.all([
    renderFieldOverviewChartView(),
    renderMissingProjectChartView(),
    renderDelayProjectChartView(),
  ]);
}

watch(
  visibleFieldOverview,
  () => {
    if (!loading.value && hasSnapshot.value) {
      renderFieldOverviewChartView();
    }
  },
  { deep: true, flush: 'post' },
);

watch(
  missingTopProjects,
  () => {
    if (!loading.value && hasSnapshot.value) {
      renderMissingProjectChartView();
    }
  },
  { deep: true, flush: 'post' },
);

watch(
  delayTopProjects,
  () => {
    if (!loading.value && hasSnapshot.value) {
      renderDelayProjectChartView();
    }
  },
  { deep: true, flush: 'post' },
);

watch(
  () => loading.value,
  (isLoading) => {
    if (!isLoading) {
      renderAllCharts();
    }
  },
  { flush: 'post' },
);

onMounted(() => {
  loadSnapshot();
});

watch(
  () => props.scope,
  () => {
    loadSnapshot();
  },
);
</script>

<template>
  <div class="space-y-6">
    <div
      class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between"
    >
      <div>
        <div class="text-lg font-bold text-slate-900 dark:text-slate-100">
          {{ panelTitle }}
        </div>
        <div class="mt-1 text-sm text-slate-500">
          {{ panelDescription }}
        </div>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <ElTag type="info" effect="light">
          {{ projectTagLabel }} {{ snapshot.project_count }}
        </ElTag>
        <ElTag type="primary" effect="light">
          需求 {{ snapshot.requirement_count }}
        </ElTag>
        <ElTag type="warning" effect="light">
          平均填写率 {{ formatPercent(averageFilledRate) }}
        </ElTag>
        <ElTag type="danger" effect="light"> 延期 {{ delayIssueCount }} </ElTag>
        <span class="text-xs text-slate-500">
          最后更新：{{ formatGeneratedAt(snapshot.generated_at) }}
        </span>
        <ElButton type="primary" :loading="refreshing" @click="refreshSnapshot">
          {{ hasSnapshot ? '手动刷新' : '立即生成' }}
        </ElButton>
      </div>
    </div>

    <ElSkeleton v-if="loading" :rows="8" animated />

    <ElCard
      v-else-if="!hasConfiguredProjects"
      shadow="never"
      class="rounded-xl border border-dashed border-slate-200 dark:border-slate-700"
    >
      <ElEmpty :description="emptyProjectDescription" />
    </ElCard>

    <ElCard
      v-else-if="!hasSnapshot"
      shadow="never"
      class="rounded-xl border border-dashed border-slate-200 dark:border-slate-700"
    >
      <ElEmpty :description="emptySnapshotDescription">
        <template #default>
          <ElButton
            type="primary"
            :loading="refreshing"
            @click="refreshSnapshot"
          >
            立即生成
          </ElButton>
        </template>
      </ElEmpty>
    </ElCard>

    <template v-else>
      <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <ElCard
          shadow="never"
          class="rounded-xl border border-slate-100 dark:border-slate-800"
        >
          <template #header>
            <div class="flex items-center justify-between gap-3">
              <div>
                <div class="text-base font-semibold">字段填写率总览</div>
                <div class="mt-1 text-xs text-slate-500">
                  按字段分口径统计填写率，帮助快速识别共性薄弱项。
                </div>
              </div>
              <ElTag type="primary" effect="plain">
                {{ visibleFieldOverview.length }} 个字段
              </ElTag>
            </div>
          </template>
          <div class="h-[320px] w-full">
            <EchartsUI ref="fieldOverviewChartRef" />
          </div>
        </ElCard>

        <ElCard
          shadow="never"
          class="rounded-xl border border-slate-100 dark:border-slate-800"
        >
          <template #header>
            <div
              class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between"
            >
              <div>
                <div class="text-base font-semibold">项目缺失 TopN</div>
                <div class="mt-1 text-xs text-slate-500">
                  聚合当前选中字段的缺失数，优先暴露最需要补齐的项目。
                </div>
              </div>
              <div class="w-full lg:w-[320px]">
                <ElSelect
                  v-model="selectedFields"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  placeholder="选择统计字段"
                >
                  <ElOption
                    v-for="item in FIELD_OPTIONS"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </ElSelect>
              </div>
            </div>
          </template>
          <div class="mb-2 text-xs text-slate-500">
            当前口径：{{ selectedMissingLabel }}
          </div>
          <div class="h-[320px] w-full">
            <EchartsUI ref="missingProjectChartRef" />
          </div>
        </ElCard>
      </div>

      <ElCard
        shadow="never"
        class="rounded-xl border border-slate-100 dark:border-slate-800"
      >
        <template #header>
          <div class="flex items-center justify-between gap-3">
            <div>
              <div class="text-base font-semibold">项目延期对比图</div>
              <div class="mt-1 text-xs text-slate-500">
                对比各项目开发延期与测试延期数量，判断交付风险集中区域。
              </div>
            </div>
            <ElTag type="danger" effect="plain">
              Top {{ Math.min(delayTopProjects.length, 10) }}
            </ElTag>
          </div>
        </template>
        <div class="h-[320px] w-full">
          <EchartsUI ref="delayProjectChartRef" />
        </div>
      </ElCard>

      <ElCard
        shadow="never"
        class="rounded-xl border border-slate-100 dark:border-slate-800"
      >
        <template #header>
          <div
            class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between"
          >
            <div>
              <div class="text-base font-semibold">项目合规表格</div>
              <div class="mt-1 text-xs text-slate-500">
                默认按合规分数排序，也支持切换为缺失字段或延期数排序。
              </div>
            </div>
            <div class="w-full lg:w-[240px]">
              <ElSelect v-model="selectedSort" placeholder="选择排序方式">
                <ElOption
                  v-for="item in SORT_OPTIONS"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </ElSelect>
            </div>
          </div>
        </template>
        <ElTable
          :data="sortedTableRows"
          size="small"
          max-height="460"
          class="requirement-workspace-table"
        >
          <ElTableColumn label="项目" min-width="160" prop="project_name" />
          <ElTableColumn label="需求数" min-width="88" align="center">
            <template #default="{ row }">
              <span class="font-medium text-slate-700 dark:text-slate-200">
                {{ row.total_count }}
              </span>
            </template>
          </ElTableColumn>
          <ElTableColumn label="合规分数" min-width="110" align="center">
            <template #default="{ row }">
              <ElTag
                :type="
                  row.completion_score >= 0.8
                    ? 'success'
                    : row.completion_score >= 0.6
                      ? 'warning'
                      : 'danger'
                "
                effect="light"
              >
                {{ formatPercent(row.completion_score) }}
              </ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn
            :label="selectedMissingLabel"
            min-width="120"
            align="center"
          >
            <template #default="{ row }">
              <div class="font-medium text-rose-500">
                {{ row.selectedMissingCount }}
              </div>
              <div class="text-xs text-slate-400">
                {{ formatPercent(row.selectedMissingRate) }}
              </div>
            </template>
          </ElTableColumn>
          <ElTableColumn label="开发延期" min-width="100" align="center">
            <template #default="{ row }">
              <div>{{ row.delay.development_count }}</div>
              <div class="text-xs text-slate-400">
                {{ formatPercent(row.delay.development_rate) }}
              </div>
            </template>
          </ElTableColumn>
          <ElTableColumn label="测试延期" min-width="100" align="center">
            <template #default="{ row }">
              <div>{{ row.delay.acceptance_count }}</div>
              <div class="text-xs text-slate-400">
                {{ formatPercent(row.delay.acceptance_rate) }}
              </div>
            </template>
          </ElTableColumn>
          <ElTableColumn label="计划转测" min-width="112" align="center">
            <template #default="{ row }">
              {{ formatPercent(row.fields.planned_test_time.filled_rate) }}
            </template>
          </ElTableColumn>
          <ElTableColumn label="计划完成" min-width="112" align="center">
            <template #default="{ row }">
              {{ formatPercent(row.fields.due_date.filled_rate) }}
            </template>
          </ElTableColumn>
          <ElTableColumn label="开发责任人" min-width="118" align="center">
            <template #default="{ row }">
              {{ formatPercent(row.fields.develop_users.filled_rate) }}
            </template>
          </ElTableColumn>
          <ElTableColumn label="测试责任人" min-width="118" align="center">
            <template #default="{ row }">
              {{ formatPercent(row.fields.test_users.filled_rate) }}
            </template>
          </ElTableColumn>
          <ElTableColumn label="工作量(人天)" min-width="128" align="center">
            <template #default="{ row }">
              {{ formatPercent(row.fields.workload_man_day.filled_rate) }}
            </template>
          </ElTableColumn>
          <ElTableColumn label="代码量(KLOC)" min-width="128" align="center">
            <template #default="{ row }">
              {{ formatPercent(row.fields.workload_kloc.filled_rate) }}
            </template>
          </ElTableColumn>
        </ElTable>
      </ElCard>
    </template>
  </div>
</template>
