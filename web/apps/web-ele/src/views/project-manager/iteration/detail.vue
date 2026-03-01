<script lang="ts" setup>
import type {
  IterationDetailItem,
  IterationRequirementItem,
} from '#/api/project-manager/iteration';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElInputNumber,
  ElMessage,
  ElOption,
  ElSelect,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus';
import * as XLSX from 'xlsx';

import {
  listIterationRequirementsApi,
  listProjectIterationsApi,
  listUnresolvedRequirementsApi,
  refreshProjectIterationApi,
  updateManualMetricApi,
} from '#/api/project-manager/iteration';
import { getProjectApi } from '#/api/project-manager/project';
import { useZqTable } from '#/components/zq-table';

defineOptions({ name: 'IterationDetail' });

type DetailTabKey = 'idpca' | 'metrics' | 'unresolved';
type EditableMetricField = 'test_automation_rate' | 'test_case_execution_rate';

interface IterationDetailRow extends IterationDetailItem {
  ar_set_a_rate: number;
  ar_set_c_rate: number;
  bug_fix_rate: number;
  code_coverage_rate: number;
  code_review_rate: number;
  dr_breakdown_rate: number;
  dr_set_a_rate: number;
  dr_set_c_rate: number;
  sr_breakdown_rate: number;
  test_automation_rate: number;
  test_case_execution_rate: number;
}

const route = useRoute();
const router = useRouter();
const projectId = route.params.id as string;
const projectInfo = ref<any>({});
const loading = ref(false);
const exportLoading = ref(false);
const activeTab = ref<DetailTabKey>('metrics');
const iterationRows = ref<IterationDetailRow[]>([]);
const selectedIterationId = ref('');
const selectedMetricIterationIds = ref<string[]>([]);

const idpcaStatusFilter = ref('');
const idpcaTypeFilter = ref('');
const unresolvedTypeFilter = ref('');

const editingCell = ref<null | { field: EditableMetricField; rowId: string }>(
  null,
);
const editingMetricValue = ref(0);

const iterationOptions = computed(() =>
  iterationRows.value.map((item) => ({
    label: `${item.name} (${item.code})`,
    value: item.id,
  })),
);
const currentIterationId = computed(
  () =>
    iterationRows.value.find((item) => item.is_current)?.id ||
    iterationRows.value[0]?.id ||
    '',
);
const effectiveIterationId = computed(
  () => selectedIterationId.value || currentIterationId.value,
);
const metricFilteredRows = computed(() => {
  const selectedIds = selectedMetricIterationIds.value;
  if (!Array.isArray(selectedIds) || selectedIds.length === 0) {
    return iterationRows.value;
  }
  const selectedIdSet = new Set(selectedIds);
  return iterationRows.value.filter((item) => selectedIdSet.has(item.id));
});

function formatRate(value: null | number | undefined) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return '-';
  }
  return `${(Number(value) * 100).toFixed(1)}%`;
}

const METRIC_THRESHOLD_RULES: Record<
  string,
  { comparator: 'gt' | 'lt'; threshold: number }
> = {
  ar_set_a_rate: { comparator: 'lt', threshold: 0.9 },
  ar_set_c_rate: { comparator: 'lt', threshold: 0.95 },
  bug_fix_rate: { comparator: 'lt', threshold: 0.9 },
  code_coverage_rate: { comparator: 'lt', threshold: 0.8 },
  code_review_rate: { comparator: 'lt', threshold: 0.9 },
  dr_breakdown_rate: { comparator: 'lt', threshold: 0.9 },
  dr_set_a_rate: { comparator: 'lt', threshold: 0.9 },
  dr_set_c_rate: { comparator: 'lt', threshold: 0.95 },
  sr_breakdown_rate: { comparator: 'lt', threshold: 0.9 },
  test_automation_rate: { comparator: 'lt', threshold: 0.75 },
  test_case_execution_rate: { comparator: 'lt', threshold: 0.9 },
};

function isOverThreshold(field: string, value: null | number | undefined) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return false;
  }
  const rule = METRIC_THRESHOLD_RULES[field];
  if (!rule) return false;
  return rule.comparator === 'lt'
    ? Number(value) < rule.threshold
    : Number(value) > rule.threshold;
}

function getMetricValueClass(field: string, value: null | number | undefined) {
  return isOverThreshold(field, value) ? 'metric-alert-value' : '';
}

function getMetricCellClasses(
  field: string,
  value: null | number | undefined,
  categoryClass: string,
) {
  const classes = ['metric-cell-value', categoryClass];
  const alertClass = getMetricValueClass(field, value);
  if (alertClass) {
    classes.push(alertClass);
  }
  return classes;
}

function formatBool(value: boolean | undefined) {
  return value ? '是' : '否';
}

function formatRequirementType(value: string | undefined) {
  return String(value || '').toUpperCase();
}

function getStatusTagType(value: string | undefined) {
  const status = String(value || '').toUpperCase();
  if (status === 'A') return 'success';
  if (status === 'C') return 'warning';
  if (status === 'P') return 'primary';
  if (status === 'D') return 'info';
  return 'danger';
}

function getStatusLabel(value: string | undefined) {
  const status = String(value || '').toUpperCase();
  if (status === 'A') return 'A';
  if (status === 'C') return 'C';
  if (status === 'P') return 'P';
  if (status === 'D') return 'D';
  return 'I';
}

function extractSingleFilterValue(filters: Record<string, any[]>, key: string) {
  const selected = filters[key];
  if (!Array.isArray(selected) || selected.length === 0) {
    return '';
  }
  return String(selected[0] || '');
}

function isIterationEnded(row: IterationDetailRow) {
  if (!row.end_date) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const end = new Date(row.end_date);
  return end < today;
}

function toDetailRows(items: IterationDetailItem[]) {
  return items.map((item) => {
    const metric = item.latest_metric;
    return {
      ...item,
      ar_set_a_rate: Number(metric?.ar_set_a_rate || 0),
      ar_set_c_rate: Number(metric?.ar_set_c_rate || 0),
      bug_fix_rate: Number(metric?.bug_fix_rate || 0),
      code_coverage_rate: Number(metric?.code_coverage_rate || 0),
      code_review_rate: Number(metric?.code_review_rate || 0),
      dr_breakdown_rate: Number(metric?.dr_breakdown_rate || 0),
      dr_set_a_rate: Number(metric?.dr_set_a_rate || 0),
      dr_set_c_rate: Number(metric?.dr_set_c_rate || 0),
      sr_breakdown_rate: Number(metric?.sr_breakdown_rate || 0),
      test_automation_rate: Number(metric?.test_automation_rate || 0),
      test_case_execution_rate: Number(metric?.test_case_execution_rate || 0),
    } as IterationDetailRow;
  });
}

function syncSelectedIteration() {
  if (selectedIterationId.value) {
    const hit = iterationRows.value.find(
      (item) => item.id === selectedIterationId.value,
    );
    if (hit) return;
  }

  selectedIterationId.value = currentIterationId.value;
}

function syncMetricIterationSelection() {
  const allIds = new Set(iterationRows.value.map((item) => item.id));
  const selectedIds = selectedMetricIterationIds.value.filter((id) =>
    allIds.has(id),
  );

  if (selectedIds.length > 0) {
    selectedMetricIterationIds.value = selectedIds;
    return;
  }

  selectedMetricIterationIds.value = currentIterationId.value
    ? [currentIterationId.value]
    : [];
}

async function fetchProjectInfo() {
  try {
    projectInfo.value = await getProjectApi(projectId);
  } catch (error) {
    console.error(error);
  }
}

async function fetchIterationRows() {
  const data = await listProjectIterationsApi(projectId);
  iterationRows.value = toDetailRows(data);
  syncSelectedIteration();
  syncMetricIterationSelection();
}

async function handleRefresh() {
  try {
    loading.value = true;
    await refreshProjectIterationApi(projectId);
    ElMessage.success('刷新任务已提交，请稍后查看同步日志或刷新页面');
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

async function handleReloadList() {
  await fetchIterationRows();
  await reloadActiveTabGrid();
}

function handleBack() {
  router.back();
}

async function onManualMetricChange(
  row: IterationDetailRow,
  field: EditableMetricField,
  value: null | number | undefined,
) {
  if (value === null || value === undefined || !row.id) return;
  if (isIterationEnded(row)) {
    ElMessage.warning('该迭代已结束，无法修改指标');
    return;
  }

  const prev = row[field];
  row[field] = Number(value);
  row.latest_metric = {
    ...row.latest_metric,
    [field]: row[field],
  } as NonNullable<IterationDetailItem['latest_metric']>;

  try {
    await updateManualMetricApi(row.id, {
      [field]: row[field],
    });
    ElMessage.success('更新成功');
  } catch {
    row[field] = prev;
    row.latest_metric = {
      ...row.latest_metric,
      [field]: prev,
    } as NonNullable<IterationDetailItem['latest_metric']>;
    ElMessage.error('更新失败');
  }
}

function isEditingMetric(row: IterationDetailRow, field: EditableMetricField) {
  return (
    editingCell.value?.rowId === row.id && editingCell.value?.field === field
  );
}

function beginMetricEdit(row: IterationDetailRow, field: EditableMetricField) {
  if (!row.id || isIterationEnded(row)) {
    return;
  }
  editingCell.value = { rowId: row.id, field };
  editingMetricValue.value = Number(row[field] || 0);
}

async function commitMetricEdit(
  row: IterationDetailRow,
  field: EditableMetricField,
) {
  if (!isEditingMetric(row, field)) return;
  const nextValue = Number(editingMetricValue.value || 0);
  editingCell.value = null;
  await onManualMetricChange(row, field, nextValue);
}

function useEntryColumns(): ZqTableGridOptions<IterationDetailRow>['columns'] {
  const columns: NonNullable<
    ZqTableGridOptions<IterationDetailRow>['columns']
  > = [
    {
      key: 'name',
      dataKey: 'name',
      title: '迭代名称',
      width: 180,
      fixed: true,
      headerHelp: {
        definition: '迭代周期的展示名称，用于区分不同迭代。',
      },
    },
    {
      key: 'code',
      dataKey: 'code',
      title: '编码',
      width: 120,
      headerHelp: {
        definition: '迭代编码，通常用于系统内唯一识别。',
      },
    },
    {
      key: 'start_date',
      dataKey: 'start_date',
      title: '开始时间',
      width: 120,
      headerHelp: {
        definition: '迭代计划开始日期。',
      },
    },
    {
      key: 'end_date',
      dataKey: 'end_date',
      title: '结束时间',
      width: 120,
      headerHelp: {
        definition: '迭代计划结束日期。',
      },
    },
    {
      key: 'is_current',
      dataKey: 'is_current',
      title: '当前迭代',
      width: 110,
      headerHelp: {
        definition: '标识该迭代是否为当前进行中的迭代。',
      },
    },
    {
      key: 'is_healthy',
      dataKey: 'is_healthy',
      title: '健康状态',
      width: 110,
      headerHelp: {
        definition: '基于迭代过程和结果指标综合判断的状态。',
      },
    },
    {
      key: 'dr_breakdown_rate',
      dataKey: 'dr_breakdown_rate',
      title: 'DR分解率',
      width: 120,
      headerHelp: {
        definition: 'DR需求已完成分解的比例。',
        formula: 'DR分解率 = 已分解DR数 ÷ DR总数',
      },
    },
    {
      key: 'sr_breakdown_rate',
      dataKey: 'sr_breakdown_rate',
      title: 'SR分解率',
      width: 120,
      headerHelp: {
        definition: 'SR需求已完成分解的比例。',
        formula: 'SR分解率 = 已分解SR数 ÷ SR总数',
      },
    },
  ];
  return columns.map((column) => ({
    ...column,
    align: 'center',
    headerAlign: 'center',
  }));
}

function useExitColumns(): ZqTableGridOptions<IterationDetailRow>['columns'] {
  const columns: NonNullable<
    ZqTableGridOptions<IterationDetailRow>['columns']
  > = [
    {
      key: 'name',
      dataKey: 'name',
      title: '迭代名称',
      width: 180,
      fixed: true,
    },
    {
      key: 'code',
      dataKey: 'code',
      title: '编码',
      width: 120,
    },
    {
      key: 'a_rate_group',
      dataKey: 'a_rate_group',
      title: '置A率（考核指标）',
      labelClassName: 'metric-group-kpi',
      headerHelp: {
        definition: '考核型质量指标，关注需求达成的正向结果。',
      },
      children: [
        {
          key: 'dr_set_a_rate',
          dataKey: 'dr_set_a_rate',
          title: 'DR',
          width: 120,
          className: 'metric-cell-kpi',
          labelClassName: 'metric-head-kpi',
          headerHelp: {
            definition: 'DR需求置A占比。',
            formula: 'DR置A率 = DR置A数量 ÷ DR总数量',
          },
        },
        {
          key: 'ar_set_a_rate',
          dataKey: 'ar_set_a_rate',
          title: 'AR',
          width: 120,
          className: 'metric-cell-kpi',
          labelClassName: 'metric-head-kpi',
          headerHelp: {
            definition: 'AR需求置A占比。',
            formula: 'AR置A率 = AR置A数量 ÷ AR总数量',
          },
        },
      ],
    },
    {
      key: 'c_rate_group',
      dataKey: 'c_rate_group',
      title: '置C率（度量指标）',
      labelClassName: 'metric-group-measure',
      headerHelp: {
        definition: '度量型质量指标，关注需求质量稳定性。',
      },
      children: [
        {
          key: 'dr_set_c_rate',
          dataKey: 'dr_set_c_rate',
          title: 'DR',
          width: 120,
          className: 'metric-cell-measure',
          labelClassName: 'metric-head-measure',
          headerHelp: {
            definition: 'DR需求置C占比。',
            formula: 'DR置C率 = DR置C数量 ÷ DR总数量',
          },
        },
        {
          key: 'ar_set_c_rate',
          dataKey: 'ar_set_c_rate',
          title: 'AR',
          width: 120,
          className: 'metric-cell-measure',
          labelClassName: 'metric-head-measure',
          headerHelp: {
            definition: 'AR需求置C占比。',
            formula: 'AR置C率 = AR置C数量 ÷ AR总数量',
          },
        },
      ],
    },
    {
      key: 'process_rate_group',
      dataKey: 'process_rate_group',
      title: '过程指标',
      labelClassName: 'metric-group-process',
      headerHelp: {
        definition: '过程执行质量类指标，用于衡量迭代执行稳定性。',
      },
      children: [
        {
          key: 'test_automation_rate',
          dataKey: 'test_automation_rate',
          title: '测试自动化率',
          width: 150,
          className: 'metric-cell-process',
          labelClassName: 'metric-head-process',
          headerHelp: {
            definition: '自动化测试覆盖的比例。',
            formula: '测试自动化率 = 自动化测试项 ÷ 测试总项',
            editableHint: '双击单元格可编辑，输入范围 0 ~ 1。',
          },
        },
        {
          key: 'test_case_execution_rate',
          dataKey: 'test_case_execution_rate',
          title: '用例执行率',
          width: 140,
          className: 'metric-cell-process',
          labelClassName: 'metric-head-process',
          headerHelp: {
            definition: '测试用例执行完成比例。',
            formula: '用例执行率 = 已执行用例数 ÷ 计划用例总数',
            editableHint: '双击单元格可编辑，输入范围 0 ~ 1。',
          },
        },
        {
          key: 'bug_fix_rate',
          dataKey: 'bug_fix_rate',
          title: '缺陷修复率',
          width: 120,
          className: 'metric-cell-process',
          labelClassName: 'metric-head-process',
          headerHelp: {
            definition: '已关闭缺陷在全部缺陷中的占比。',
            formula: '缺陷修复率 = 已修复缺陷数 ÷ 缺陷总数',
          },
        },
        {
          key: 'code_review_rate',
          dataKey: 'code_review_rate',
          title: '代码评审率',
          width: 120,
          className: 'metric-cell-process',
          labelClassName: 'metric-head-process',
          headerHelp: {
            definition: '已完成评审代码占比。',
            formula: '代码评审率 = 完成评审代码量 ÷ 提交代码量',
          },
        },
      ],
    },
    {
      key: 'reference_group',
      dataKey: 'reference_group',
      title: '参考指标',
      labelClassName: 'metric-group-reference',
      headerHelp: {
        definition: '参考观测类指标，用于辅助评估整体质量趋势。',
      },
      children: [
        {
          key: 'code_coverage_rate',
          dataKey: 'code_coverage_rate',
          title: '代码覆盖率',
          width: 120,
          className: 'metric-cell-reference',
          labelClassName: 'metric-head-reference',
          headerHelp: {
            definition: '单元测试覆盖率。',
            formula: '代码覆盖率 = 被覆盖代码行数 ÷ 代码总行数',
          },
        },
      ],
    },
  ];
  return columns.map((column) => ({
    ...column,
    align: 'center',
    headerAlign: 'center',
  }));
}

function useIdpcaColumns(): ZqTableGridOptions<IterationRequirementItem>['columns'] {
  const columns: NonNullable<
    ZqTableGridOptions<IterationRequirementItem>['columns']
  > = [
    {
      key: 'requirement_id',
      dataKey: 'requirement_id',
      title: '需求ID',
      width: 200,
    },
    {
      key: 'title',
      dataKey: 'title',
      title: '需求标题',
      width: 220,
    },
    {
      key: 'requirement_type',
      dataKey: 'requirement_type',
      title: '需求类型',
      width: 100,
      columnKey: 'requirement_type',
      filterMultiple: false,
      filters: [
        { text: 'SR', value: 'sr' },
        { text: 'DR', value: 'dr' },
        { text: 'AR', value: 'ar' },
      ],
    },
    {
      key: 'idpca_status',
      dataKey: 'idpca_status',
      title: 'IDPCA状态',
      width: 120,
      columnKey: 'idpca_status',
      filterMultiple: false,
      filters: [
        { text: 'I', value: 'I' },
        { text: 'D', value: 'D' },
        { text: 'P', value: 'P' },
        { text: 'C', value: 'C' },
        { text: 'A', value: 'A' },
      ],
    },
    {
      key: 'owner_team',
      dataKey: 'owner_team',
      title: '责任团队',
      width: 140,
    },
    {
      key: 'need_breakdown',
      dataKey: 'need_breakdown',
      title: '需分解',
      width: 100,
    },
    {
      key: 'is_decomposed',
      dataKey: 'is_decomposed',
      title: '已分解',
      width: 100,
    },
  ];

  return columns.map((column) => ({
    ...column,
    align: 'center',
    headerAlign: 'center',
  }));
}

function useUnresolvedColumns(): ZqTableGridOptions<IterationRequirementItem>['columns'] {
  const columns: NonNullable<
    ZqTableGridOptions<IterationRequirementItem>['columns']
  > = [
    {
      key: 'requirement_id',
      dataKey: 'requirement_id',
      title: '需求ID',
      width: 200,
    },
    {
      key: 'title',
      dataKey: 'title',
      title: '需求标题',
      width: 220,
    },
    {
      key: 'requirement_type',
      dataKey: 'requirement_type',
      title: '需求类型',
      width: 100,
      columnKey: 'requirement_type',
      filterMultiple: false,
      filters: [
        { text: 'SR', value: 'sr' },
        { text: 'DR', value: 'dr' },
        { text: 'AR', value: 'ar' },
      ],
    },
    {
      key: 'idpca_status',
      dataKey: 'idpca_status',
      title: 'IDPCA状态',
      width: 120,
    },
    {
      key: 'owner_team',
      dataKey: 'owner_team',
      title: '责任团队',
      width: 140,
    },
    {
      key: 'need_breakdown',
      dataKey: 'need_breakdown',
      title: '需分解',
      width: 100,
    },
  ];

  return columns.map((column) => ({
    ...column,
    align: 'center',
    headerAlign: 'center',
  }));
}

const [EntryGrid, entryGridApi] = useZqTable({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    columns: useEntryColumns(),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async () => {
          const rows = metricFilteredRows.value;
          return {
            items: rows,
            total: rows.length,
          };
        },
      },
    },
    pagerConfig: { enabled: false },
    toolbarConfig: {
      custom: true,
      refresh: true,
      zoom: true,
    },
  } as ZqTableGridOptions<IterationDetailRow>,
});

const [ExitGrid, exitGridApi] = useZqTable({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    columns: useExitColumns(),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async () => {
          const rows = metricFilteredRows.value;
          return {
            items: rows,
            total: rows.length,
          };
        },
      },
    },
    pagerConfig: { enabled: false },
    toolbarConfig: {
      custom: true,
      refresh: true,
      zoom: true,
    },
  } as ZqTableGridOptions<IterationDetailRow>,
});

const [IdpcaGrid, idpcaGridApi] = useZqTable({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    columns: useIdpcaColumns(),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({ page }) => {
          if (!effectiveIterationId.value) {
            return { items: [], total: 0 };
          }
          const res = await listIterationRequirementsApi(
            effectiveIterationId.value,
            {
              idpca_status: idpcaStatusFilter.value || undefined,
              page: page.currentPage,
              page_size: page.pageSize,
              requirement_type: idpcaTypeFilter.value || undefined,
            },
          );
          return { items: res.items || [], total: res.total || 0 };
        },
      },
    },
    pagerConfig: { enabled: true, pageSize: 20 },
    toolbarConfig: {
      custom: true,
      refresh: true,
      zoom: true,
    },
  } as ZqTableGridOptions<IterationRequirementItem>,
});

const [UnresolvedGrid, unresolvedGridApi] = useZqTable({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    columns: useUnresolvedColumns(),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({ page }) => {
          if (!effectiveIterationId.value) {
            return { items: [], total: 0 };
          }
          const res = await listUnresolvedRequirementsApi(
            effectiveIterationId.value,
            {
              page: page.currentPage,
              page_size: page.pageSize,
              requirement_type: unresolvedTypeFilter.value || undefined,
            },
          );
          return { items: res.items || [], total: res.total || 0 };
        },
      },
    },
    pagerConfig: { enabled: true, pageSize: 20 },
    toolbarConfig: {
      custom: true,
      refresh: true,
      zoom: true,
    },
  } as ZqTableGridOptions<IterationRequirementItem>,
});

async function reloadActiveTabGrid() {
  if (activeTab.value === 'metrics') {
    await entryGridApi.reload();
    await exitGridApi.reload();
    return;
  }
  if (activeTab.value === 'idpca') {
    await idpcaGridApi.reload();
    return;
  }
  await unresolvedGridApi.reload();
}

async function handleIdpcaHeaderFilterChange(filters: Record<string, any[]>) {
  idpcaStatusFilter.value = extractSingleFilterValue(filters, 'idpca_status');
  idpcaTypeFilter.value = extractSingleFilterValue(filters, 'requirement_type');
  await idpcaGridApi.reload();
}

async function handleUnresolvedHeaderFilterChange(
  filters: Record<string, any[]>,
) {
  unresolvedTypeFilter.value = extractSingleFilterValue(
    filters,
    'requirement_type',
  );
  await unresolvedGridApi.reload();
}

watch(
  () => activeTab.value,
  async () => {
    await reloadActiveTabGrid();
  },
);

watch(
  () => selectedIterationId.value,
  async () => {
    if (activeTab.value === 'idpca') {
      await idpcaGridApi.reload();
      return;
    }
    if (activeTab.value === 'unresolved') {
      await unresolvedGridApi.reload();
    }
  },
);

watch(
  () => selectedMetricIterationIds.value,
  async () => {
    if (activeTab.value === 'metrics') {
      await entryGridApi.reload();
      await exitGridApi.reload();
    }
  },
  { deep: true },
);

async function fetchAllRequirementItems(
  fetchPage: (
    page: number,
    pageSize: number,
  ) => Promise<{ items: IterationRequirementItem[]; total: number }>,
) {
  const allItems: IterationRequirementItem[] = [];
  const pageSize = 200;
  let page = 1;
  let total = 0;

  while (true) {
    const result = await fetchPage(page, pageSize);
    const currentItems = result.items || [];
    total = Number(result.total || 0);
    allItems.push(...currentItems);
    if (allItems.length >= total || currentItems.length === 0) {
      break;
    }
    page += 1;
  }

  return allItems;
}

async function handleExportAll() {
  if (exportLoading.value) return;
  exportLoading.value = true;
  try {
    const xlsx = (XLSX as any)?.utils ? (XLSX as any) : (XLSX as any)?.default;
    if (!xlsx?.utils) {
      throw new TypeError('xlsx utils unavailable');
    }
    const writeFile = xlsx.writeFileXLSX || xlsx.writeFile;
    if (typeof writeFile !== 'function') {
      throw new TypeError('xlsx writeFile unavailable');
    }

    const workbook = xlsx.utils.book_new();

    const entryRows = metricFilteredRows.value.map((row) => ({
      迭代名称: row.name,
      编码: row.code,
      开始时间: row.start_date,
      结束时间: row.end_date,
      当前迭代: row.is_current ? '是' : '否',
      健康状态: row.is_healthy ? '健康' : '风险',
      DR分解率: formatRate(row.dr_breakdown_rate),
      SR分解率: formatRate(row.sr_breakdown_rate),
    }));

    const exitRows = metricFilteredRows.value.map((row) => ({
      迭代名称: row.name,
      编码: row.code,
      DR置A率: formatRate(row.dr_set_a_rate),
      AR置A率: formatRate(row.ar_set_a_rate),
      DR置C率: formatRate(row.dr_set_c_rate),
      AR置C率: formatRate(row.ar_set_c_rate),
      测试自动化率: formatRate(row.test_automation_rate),
      用例执行率: formatRate(row.test_case_execution_rate),
      缺陷修复率: formatRate(row.bug_fix_rate),
      代码评审率: formatRate(row.code_review_rate),
      代码覆盖率: formatRate(row.code_coverage_rate),
    }));

    const metricSheetData: any[][] = [
      ['迭代入口指标'],
      [
        '迭代名称',
        '编码',
        '开始时间',
        '结束时间',
        '当前迭代',
        '健康状态',
        'DR分解率',
        'SR分解率',
      ],
      ...entryRows.map((row) => [
        row.迭代名称,
        row.编码,
        row.开始时间,
        row.结束时间,
        row.当前迭代,
        row.健康状态,
        row.DR分解率,
        row.SR分解率,
      ]),
      [],
      ['迭代出口指标'],
      [
        '迭代名称',
        '编码',
        'DR置A率',
        'AR置A率',
        'DR置C率',
        'AR置C率',
        '测试自动化率',
        '用例执行率',
        '缺陷修复率',
        '代码评审率',
        '代码覆盖率',
      ],
      ...exitRows.map((row) => [
        row.迭代名称,
        row.编码,
        row.DR置A率,
        row.AR置A率,
        row.DR置C率,
        row.AR置C率,
        row.测试自动化率,
        row.用例执行率,
        row.缺陷修复率,
        row.代码评审率,
        row.代码覆盖率,
      ]),
    ];
    const metricsSheet = xlsx.utils.aoa_to_sheet(metricSheetData);
    xlsx.utils.book_append_sheet(workbook, metricsSheet, '迭代指标');

    let idpcaItems: IterationRequirementItem[] = [];
    let unresolvedItems: IterationRequirementItem[] = [];
    if (effectiveIterationId.value) {
      idpcaItems = await fetchAllRequirementItems((page, pageSize) =>
        listIterationRequirementsApi(effectiveIterationId.value, {
          idpca_status: idpcaStatusFilter.value || undefined,
          requirement_type: idpcaTypeFilter.value || undefined,
          page,
          page_size: pageSize,
        }),
      );
      unresolvedItems = await fetchAllRequirementItems((page, pageSize) =>
        listUnresolvedRequirementsApi(effectiveIterationId.value, {
          requirement_type: unresolvedTypeFilter.value || undefined,
          page,
          page_size: pageSize,
        }),
      );
    }

    const idpcaRows = idpcaItems.map((item) => ({
      需求ID: item.requirement_id,
      需求标题: item.title,
      需求类型: formatRequirementType(item.requirement_type),
      IDPCA状态: item.idpca_status,
      责任团队: item.owner_team || '-',
      需分解: formatBool(item.need_breakdown),
      已分解: formatBool(item.is_decomposed),
    }));
    const idpcaSheet = xlsx.utils.json_to_sheet(idpcaRows);
    xlsx.utils.book_append_sheet(workbook, idpcaSheet, '需求IDPCA状态');

    const unresolvedRows = unresolvedItems.map((item) => ({
      需求ID: item.requirement_id,
      需求标题: item.title,
      需求类型: formatRequirementType(item.requirement_type),
      IDPCA状态: item.idpca_status,
      责任团队: item.owner_team || '-',
      需分解: formatBool(item.need_breakdown),
      已分解: formatBool(item.is_decomposed),
    }));
    const unresolvedSheet = xlsx.utils.json_to_sheet(unresolvedRows);
    xlsx.utils.book_append_sheet(workbook, unresolvedSheet, '未分解需求');

    const dateText = new Date().toISOString().slice(0, 10);
    const filename = `${projectInfo.value?.name || '项目'}-迭代详情-${dateText}.xlsx`;
    writeFile(workbook, filename);
    ElMessage.success('导出成功');
  } catch (error) {
    console.error('[iteration detail export failed]', error);
    ElMessage.error('导出失败，请检查数据或依赖');
  } finally {
    exportLoading.value = false;
  }
}

onMounted(async () => {
  await fetchProjectInfo();
  await fetchIterationRows();
  await entryGridApi.reload();
  await exitGridApi.reload();
});
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full min-h-0 flex-col">
      <div class="mb-4 flex items-center justify-between px-4">
        <div class="flex items-center gap-4">
          <ElButton @click="handleBack">返回</ElButton>
          <div class="text-lg font-bold">{{ projectInfo.name }} - 迭代详情</div>
        </div>
        <div class="flex items-center gap-2">
          <ElButton @click="handleReloadList">刷新列表</ElButton>
          <ElButton :loading="exportLoading" @click="handleExportAll">
            导出详情
          </ElButton>
          <ElButton type="primary" :loading="loading" @click="handleRefresh">
            刷新数据
          </ElButton>
        </div>
      </div>

      <div class="min-h-0 flex-1 px-4 pb-4">
        <div class="flex h-full min-h-0 flex-col">
          <ElTabs v-model="activeTab">
            <ElTabPane label="迭代指标数据表格" name="metrics" />
            <ElTabPane label="需求IDPCA状态列表" name="idpca" />
            <ElTabPane label="未分解需求" name="unresolved" />
          </ElTabs>

          <div class="min-h-0 flex-1">
            <div v-if="activeTab === 'metrics'" class="h-full">
              <div class="flex h-full min-h-0 flex-col gap-3">
                <div class="flex items-center gap-2">
                  <ElSelect
                    v-model="selectedMetricIterationIds"
                    class="!w-[360px] shrink-0"
                    style="width: 360px"
                    filterable
                    multiple
                    collapse-tags
                    collapse-tags-tooltip
                    placeholder="选择迭代（可多选）"
                  >
                    <ElOption
                      v-for="item in iterationOptions"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                    />
                  </ElSelect>
                </div>
                <div class="grid min-h-0 flex-1 grid-rows-2 gap-3">
                  <div class="min-h-0">
                    <EntryGrid class="h-full">
                      <template #table-title>
                        <div class="text-sm font-medium">迭代入口指标</div>
                      </template>
                      <template #cell-is_current="{ row }">
                        <ElTag
                          :type="row.is_current ? 'success' : 'info'"
                          size="small"
                        >
                          {{ row.is_current ? '是' : '否' }}
                        </ElTag>
                      </template>
                      <template #cell-is_healthy="{ row }">
                        <ElTag
                          :type="row.is_healthy ? 'success' : 'danger'"
                          size="small"
                        >
                          {{ row.is_healthy ? '健康' : '风险' }}
                        </ElTag>
                      </template>
                      <template #cell-dr_breakdown_rate="{ row }">
                        <span
                          :class="
                            getMetricValueClass(
                              'dr_breakdown_rate',
                              row.dr_breakdown_rate,
                            )
                          "
                        >
                          {{ formatRate(row.dr_breakdown_rate) }}
                        </span>
                      </template>
                      <template #cell-sr_breakdown_rate="{ row }">
                        <span
                          :class="
                            getMetricValueClass(
                              'sr_breakdown_rate',
                              row.sr_breakdown_rate,
                            )
                          "
                        >
                          {{ formatRate(row.sr_breakdown_rate) }}
                        </span>
                      </template>
                    </EntryGrid>
                  </div>

                  <div class="min-h-0">
                    <ExitGrid class="h-full">
                      <template #table-title>
                        <div class="flex items-center gap-3">
                          <div class="text-sm font-medium">迭代出口指标</div>
                          <span
                            class="metric-group-chip metric-group-chip--kpi"
                          >
                            考核
                          </span>
                          <span
                            class="metric-group-chip metric-group-chip--measure"
                          >
                            度量
                          </span>
                          <span
                            class="metric-group-chip metric-group-chip--reference"
                          >
                            参考
                          </span>
                          <div class="metric-threshold-note">
                            红色表示超阈值
                          </div>
                        </div>
                      </template>

                      <template #cell-dr_set_a_rate="{ row }">
                        <span
                          :class="
                            getMetricCellClasses(
                              'dr_set_a_rate',
                              row.dr_set_a_rate,
                              'metric-cell-value--kpi',
                            )
                          "
                        >
                          {{ formatRate(row.dr_set_a_rate) }}
                        </span>
                      </template>
                      <template #cell-ar_set_a_rate="{ row }">
                        <span
                          :class="
                            getMetricCellClasses(
                              'ar_set_a_rate',
                              row.ar_set_a_rate,
                              'metric-cell-value--kpi',
                            )
                          "
                        >
                          {{ formatRate(row.ar_set_a_rate) }}
                        </span>
                      </template>
                      <template #cell-dr_set_c_rate="{ row }">
                        <span
                          :class="
                            getMetricCellClasses(
                              'dr_set_c_rate',
                              row.dr_set_c_rate,
                              'metric-cell-value--measure',
                            )
                          "
                        >
                          {{ formatRate(row.dr_set_c_rate) }}
                        </span>
                      </template>
                      <template #cell-ar_set_c_rate="{ row }">
                        <span
                          :class="
                            getMetricCellClasses(
                              'ar_set_c_rate',
                              row.ar_set_c_rate,
                              'metric-cell-value--measure',
                            )
                          "
                        >
                          {{ formatRate(row.ar_set_c_rate) }}
                        </span>
                      </template>
                      <template #cell-bug_fix_rate="{ row }">
                        <span
                          :class="
                            getMetricCellClasses(
                              'bug_fix_rate',
                              row.bug_fix_rate,
                              'metric-cell-value--process',
                            )
                          "
                        >
                          {{ formatRate(row.bug_fix_rate) }}
                        </span>
                      </template>
                      <template #cell-code_review_rate="{ row }">
                        <span
                          :class="
                            getMetricCellClasses(
                              'code_review_rate',
                              row.code_review_rate,
                              'metric-cell-value--process',
                            )
                          "
                        >
                          {{ formatRate(row.code_review_rate) }}
                        </span>
                      </template>
                      <template #cell-code_coverage_rate="{ row }">
                        <span
                          :class="
                            getMetricCellClasses(
                              'code_coverage_rate',
                              row.code_coverage_rate,
                              'metric-cell-value--reference',
                            )
                          "
                        >
                          {{ formatRate(row.code_coverage_rate) }}
                        </span>
                      </template>

                      <template #cell-test_automation_rate="{ row }">
                        <ElInputNumber
                          v-if="isEditingMetric(row, 'test_automation_rate')"
                          :model-value="editingMetricValue"
                          size="small"
                          :controls="false"
                          :step="0.01"
                          :min="0"
                          :max="1"
                          @update:model-value="
                            (value) => (editingMetricValue = Number(value || 0))
                          "
                          @blur="commitMetricEdit(row, 'test_automation_rate')"
                          @change="
                            (value) => {
                              editingMetricValue = Number(value || 0);
                              void commitMetricEdit(
                                row,
                                'test_automation_rate',
                              );
                            }
                          "
                        />
                        <span
                          :class="[
                            ...getMetricCellClasses(
                              'test_automation_rate',
                              row.test_automation_rate,
                              'metric-cell-value--process',
                            ),
                            isIterationEnded(row) ? '' : 'cursor-pointer',
                          ]"
                          v-else
                          @dblclick="
                            beginMetricEdit(row, 'test_automation_rate')
                          "
                        >
                          {{ formatRate(row.test_automation_rate) }}
                        </span>
                      </template>
                      <template #cell-test_case_execution_rate="{ row }">
                        <ElInputNumber
                          v-if="
                            isEditingMetric(row, 'test_case_execution_rate')
                          "
                          :model-value="editingMetricValue"
                          size="small"
                          :controls="false"
                          :step="0.01"
                          :min="0"
                          :max="1"
                          @update:model-value="
                            (value) => (editingMetricValue = Number(value || 0))
                          "
                          @blur="
                            commitMetricEdit(row, 'test_case_execution_rate')
                          "
                          @change="
                            (value) => {
                              editingMetricValue = Number(value || 0);
                              void commitMetricEdit(
                                row,
                                'test_case_execution_rate',
                              );
                            }
                          "
                        />
                        <span
                          :class="[
                            ...getMetricCellClasses(
                              'test_case_execution_rate',
                              row.test_case_execution_rate,
                              'metric-cell-value--process',
                            ),
                            isIterationEnded(row) ? '' : 'cursor-pointer',
                          ]"
                          v-else
                          @dblclick="
                            beginMetricEdit(row, 'test_case_execution_rate')
                          "
                        >
                          {{ formatRate(row.test_case_execution_rate) }}
                        </span>
                      </template>
                    </ExitGrid>
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="activeTab === 'idpca'" class="h-full">
              <IdpcaGrid
                class="h-full"
                @filter-change="handleIdpcaHeaderFilterChange"
              >
                <template #table-title>
                  <div class="flex items-center gap-2">
                    <ElSelect
                      v-model="selectedIterationId"
                      class="!w-[280px] shrink-0"
                      style="width: 280px"
                      filterable
                      placeholder="选择迭代"
                    >
                      <ElOption
                        v-for="item in iterationOptions"
                        :key="item.value"
                        :label="item.label"
                        :value="item.value"
                      />
                    </ElSelect>
                  </div>
                </template>

                <template #cell-requirement_type="{ row }">
                  {{ formatRequirementType(row.requirement_type) }}
                </template>
                <template #cell-idpca_status="{ row }">
                  <ElTag
                    :type="getStatusTagType(row.idpca_status)"
                    size="small"
                  >
                    {{ getStatusLabel(row.idpca_status) }}
                  </ElTag>
                </template>
                <template #cell-need_breakdown="{ row }">
                  {{ row.need_breakdown ? '是' : '否' }}
                </template>
                <template #cell-is_decomposed="{ row }">
                  {{ row.is_decomposed ? '是' : '否' }}
                </template>
              </IdpcaGrid>
            </div>

            <div v-else class="h-full">
              <UnresolvedGrid
                class="h-full"
                @filter-change="handleUnresolvedHeaderFilterChange"
              >
                <template #table-title>
                  <div class="flex items-center gap-2">
                    <ElSelect
                      v-model="selectedIterationId"
                      class="!w-[280px] shrink-0"
                      style="width: 280px"
                      filterable
                      placeholder="选择迭代"
                    >
                      <ElOption
                        v-for="item in iterationOptions"
                        :key="item.value"
                        :label="item.label"
                        :value="item.value"
                      />
                    </ElSelect>
                  </div>
                </template>

                <template #cell-requirement_type="{ row }">
                  {{ formatRequirementType(row.requirement_type) }}
                </template>
                <template #cell-idpca_status="{ row }">
                  <ElTag
                    :type="getStatusTagType(row.idpca_status)"
                    size="small"
                  >
                    {{ getStatusLabel(row.idpca_status) }}
                  </ElTag>
                </template>
                <template #cell-need_breakdown="{ row }">
                  {{ row.need_breakdown ? '是' : '否' }}
                </template>
              </UnresolvedGrid>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Page>
</template>

<style scoped>
.metric-threshold-note {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.metric-alert-value {
  color: var(--el-color-danger);
  font-weight: 600;
}

.metric-group-chip {
  border: 1px solid var(--el-border-color);
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 12px;
  line-height: 1;
}

.metric-group-chip--kpi {
  color: #1f6feb;
  border-color: rgb(31 111 235 / 45%);
  background: rgb(31 111 235 / 8%);
}

.metric-group-chip--measure {
  color: #0f766e;
  border-color: rgb(15 118 110 / 45%);
  background: rgb(15 118 110 / 8%);
}

.metric-group-chip--reference {
  color: #6b7280;
  border-color: rgb(107 114 128 / 45%);
  background: rgb(107 114 128 / 8%);
}

:deep(th.metric-group-kpi) {
  background: rgb(31 111 235 / 5%) !important;
}

:deep(.metric-group-kpi) .cell {
  color: #1f6feb !important;
  font-weight: 600;
}

:deep(th.metric-head-kpi) {
  background: rgb(31 111 235 / 7%) !important;
}

:deep(.metric-head-kpi) .cell {
  color: #1f6feb !important;
  font-weight: 700;
}

:deep(th.metric-group-measure) {
  background: rgb(15 118 110 / 5%) !important;
}

:deep(.metric-group-measure) .cell {
  color: #0f766e !important;
  font-weight: 600;
}

:deep(th.metric-head-measure) {
  background: rgb(15 118 110 / 7%) !important;
}

:deep(.metric-head-measure) .cell {
  color: #0f766e !important;
  font-weight: 700;
}

:deep(th.metric-group-process) {
  background: rgb(100 116 139 / 6%) !important;
}

:deep(.metric-group-process) .cell {
  color: #64748b !important;
  font-weight: 600;
}

:deep(th.metric-head-process) {
  background: rgb(100 116 139 / 8%) !important;
}

:deep(.metric-head-process) .cell {
  color: #64748b !important;
  font-weight: 700;
}

:deep(th.metric-group-reference) {
  background: rgb(107 114 128 / 8%) !important;
}

:deep(.metric-group-reference) .cell {
  color: #6b7280 !important;
  font-weight: 600;
}

:deep(th.metric-head-reference) {
  background: rgb(107 114 128 / 10%) !important;
}

:deep(.metric-head-reference) .cell {
  color: #6b7280 !important;
  font-weight: 700;
}

:deep(td.metric-cell-kpi) {
  background: rgb(31 111 235 / 4%);
}

:deep(td.metric-cell-kpi) .cell {
  border-left: 2px solid rgb(31 111 235 / 30%);
}

:deep(td.metric-cell-measure) {
  background: rgb(15 118 110 / 4%);
}

:deep(td.metric-cell-measure) .cell {
  border-left: 2px solid rgb(15 118 110 / 30%);
}

:deep(td.metric-cell-process) {
  background: rgb(100 116 139 / 4%);
}

:deep(td.metric-cell-process) .cell {
  border-left: 2px solid rgb(100 116 139 / 26%);
}

:deep(td.metric-cell-reference) {
  background: rgb(107 114 128 / 5%);
}

:deep(td.metric-cell-reference) .cell {
  border-left: 2px solid rgb(107 114 128 / 30%);
}

.metric-cell-value {
  display: inline-block;
}
</style>
