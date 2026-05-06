<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type {
  DtsBatchSaveResponse,
  DtsDictOptions,
  DtsExportTask,
  DtsMergedDefect,
  DtsSnapshotMeta,
  DtsStatisticsFilters,
  DtsPlGroupCompletionItem,
  DtsSummary,
} from '#/api/project-manager/dts-statistics';

import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

import { Filter } from '@element-plus/icons-vue';
import {
  ElButton,
  ElCard,
  ElCheckbox,
  ElCheckboxGroup,
  ElDatePicker,
  ElEmpty,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPopover,
  ElSegmented,
  ElSelect,
  ElTabPane,
  ElTabs,
  ElTag,
  ElTooltip,
} from 'element-plus';

import {
  downloadDtsExportTask,
  getDtsExportTask,
  getDtsFieldSets,
  getDtsList,
  getDtsSummary,
  prepareDtsExport,
} from '#/api/project-manager/dts-statistics';
import { useZqTable } from '#/components/zq-table';

import DtsHeaderPersonSelector from './components/DtsHeaderPersonSelector.vue';
import {
  fetchDtsDictOptionsCached,
  formatCycleIntegerDisplay,
  formatProjectDisplay,
  resolveDtsGovernanceTagList,
  resolveDtsGovernanceTagMeta,
  resolveSeverityMeta,
  useColumns,
} from './data';
import DtsBatchEditDrawer from './DtsBatchEditDrawer.vue';
import DtsEditDrawer from './DtsEditDrawer.vue';

defineOptions({ name: 'DtsStatistics' });

type TabKey = 'dashboard' | 'list';
type DtsFieldSetKey =
  | 'auto_pl_group_name'
  | 'auto_source_type'
  | 'projectName'
  | 'sConfigFlowType'
  | 'sDeptOneNoName'
  | 'sSubsystemNoName'
  | 'uQbiCloseTypeName';
type DtsFieldSetOptionsState = Record<DtsFieldSetKey, string[]>;
type DtsFieldSetLoadingState = Record<DtsFieldSetKey, boolean>;

const GOVERNANCE_SELECT_FILTER_CONFIGS = [
  {
    columnKey: 'is_downstream',
    dictKey: 'yes_no',
    filterKey: 'is_downstream_values',
    label: '是否下游问题',
    placeholder: '输入关键词筛选是否下游问题',
  },
  {
    columnKey: 'need_aar',
    dictKey: 'yes_no',
    filterKey: 'need_aar_values',
    label: '是否需要AAR',
    placeholder: '输入关键词筛选是否需要AAR',
  },
  {
    columnKey: 'need_dev_analyze',
    dictKey: 'yes_no',
    filterKey: 'need_dev_analyze_values',
    label: '需开发分析',
    placeholder: '输入关键词筛选需开发分析',
  },
  {
    columnKey: 'need_test_analyze',
    dictKey: 'yes_no',
    filterKey: 'need_test_analyze_values',
    label: '需测试分析',
    placeholder: '输入关键词筛选需测试分析',
  },
  {
    columnKey: 'issue_intro_stage',
    dictKey: 'issue_intro_stage',
    filterKey: 'issue_intro_stage_values',
    label: '问题引入阶段',
    placeholder: '输入关键词筛选问题引入阶段',
  },
  {
    columnKey: 'dev_sub_category',
    dictKey: 'dev_sub_category',
    filterKey: 'dev_sub_category_values',
    label: '问题小类',
    placeholder: '输入关键词筛选问题小类',
  },
  {
    columnKey: 'dev_issue_intro_point',
    dictKey: 'dev_issue_intro_point',
    filterKey: 'dev_issue_intro_point_values',
    label: '问题引入点',
    placeholder: '输入关键词筛选问题引入点',
  },
  {
    columnKey: 'dev_issue_probability',
    dictKey: 'dev_issue_probability',
    filterKey: 'dev_issue_probability_values',
    label: '问题概率',
    placeholder: '输入关键词筛选问题概率',
  },
  {
    columnKey: 'dev_common_issue_type',
    dictKey: 'dev_common_issue_type',
    filterKey: 'dev_common_issue_type_values',
    label: '是否共性问题',
    placeholder: '输入关键词筛选是否共性问题',
  },
  {
    columnKey: 'is_base_soft_issue',
    dictKey: 'yes_no',
    filterKey: 'is_base_soft_issue_values',
    label: '是否底软问题',
    placeholder: '输入关键词筛选是否底软问题',
  },
  {
    columnKey: 'is_duplicate_issue',
    dictKey: 'yes_no',
    filterKey: 'is_duplicate_issue_values',
    label: '是否重复问题',
    placeholder: '输入关键词筛选是否重复问题',
  },
  {
    columnKey: 'dev_control_points',
    dictKey: 'dev_control_points',
    filterKey: 'dev_control_points_values',
    label: '开发控制点',
    placeholder: '输入关键词筛选开发控制点',
  },
  {
    columnKey: 'dev_non_base_desc',
    dictKey: 'dev_non_base_desc',
    filterKey: 'dev_non_base_desc_values',
    label: '非底软说明',
    placeholder: '输入关键词筛选非底软说明',
  },
  {
    columnKey: 'dev_asset_type',
    dictKey: 'dev_asset_type',
    filterKey: 'dev_asset_type_values',
    label: '落地资产类型',
    placeholder: '输入关键词筛选落地资产类型',
  },
  {
    columnKey: 'dev_status',
    dictKey: 'action_status',
    filterKey: 'dev_status_values',
    label: '开发改进状态',
    placeholder: '输入关键词筛选开发改进状态',
  },
  {
    columnKey: 'test_miss_reason',
    dictKey: 'test_miss_reason',
    filterKey: 'test_miss_reason_values',
    label: '漏测原因',
    placeholder: '输入关键词筛选漏测原因',
  },
  {
    columnKey: 'test_status',
    dictKey: 'action_status',
    filterKey: 'test_status_values',
    label: '测试改进状态',
    placeholder: '输入关键词筛选测试改进状态',
  },
] as const;

const GOVERNANCE_KEYWORD_FILTER_CONFIGS = [
  {
    columnKey: 'process_quality_type',
    filterKey: 'process_quality_type_keyword',
    label: '过程质量分类',
    placeholder: '输入关键词模糊搜索过程质量分类',
  },
  {
    columnKey: 'qa_remark',
    filterKey: 'qa_remark_keyword',
    label: 'QA备注',
    placeholder: '输入关键词模糊搜索QA备注',
  },
  {
    columnKey: 'dev_feature',
    filterKey: 'dev_feature_keyword',
    label: '特性/功能',
    placeholder: '输入关键词模糊搜索特性/功能',
  },
  {
    columnKey: 'dev_reason',
    filterKey: 'dev_reason_keyword',
    label: '问题原因',
    placeholder: '输入关键词模糊搜索问题原因',
  },
  {
    columnKey: 'dev_intro_reason',
    filterKey: 'dev_intro_reason_keyword',
    label: '引入原因',
    placeholder: '输入关键词模糊搜索引入原因',
  },
  {
    columnKey: 'dev_intro_point_analysis',
    filterKey: 'dev_intro_point_analysis_keyword',
    label: '引入点分析',
    placeholder: '输入关键词模糊搜索引入点分析',
  },
  {
    columnKey: 'dev_improvements',
    filterKey: 'dev_improvements_keyword',
    label: '开发改进措施',
    placeholder: '输入关键词模糊搜索开发改进措施',
  },
  {
    columnKey: 'dev_aar_link',
    filterKey: 'dev_aar_link_keyword',
    label: 'AAR链接',
    placeholder: '输入关键词模糊搜索AAR链接',
  },
  {
    columnKey: 'dev_asset_link',
    filterKey: 'dev_asset_link_keyword',
    label: '开发落地资产链接',
    placeholder: '输入关键词模糊搜索开发落地资产链接',
  },
  {
    columnKey: 'dev_remark',
    filterKey: 'dev_remark_keyword',
    label: '开发备注',
    placeholder: '输入关键词模糊搜索开发备注',
  },
  {
    columnKey: 'duplicate_issue_no',
    filterKey: 'duplicate_issue_no_keyword',
    label: '重复问题单号',
    placeholder: '输入关键词模糊搜索重复问题单号',
  },
  {
    columnKey: 'test_standard_desc',
    filterKey: 'test_standard_desc_keyword',
    label: '规范问题描述',
    placeholder: '输入关键词模糊搜索规范问题描述',
  },
  {
    columnKey: 'test_improvements',
    filterKey: 'test_improvements_keyword',
    label: '测试改进措施',
    placeholder: '输入关键词模糊搜索测试改进措施',
  },
  {
    columnKey: 'test_non_test_desc',
    filterKey: 'test_non_test_desc_keyword',
    label: '非测试说明',
    placeholder: '输入关键词模糊搜索非测试说明',
  },
  {
    columnKey: 'test_asset_link',
    filterKey: 'test_asset_link_keyword',
    label: '测试落地资产链接',
    placeholder: '输入关键词模糊搜索测试落地资产链接',
  },
  {
    columnKey: 'test_remark',
    filterKey: 'test_remark_keyword',
    label: '测试备注',
    placeholder: '输入关键词模糊搜索测试备注',
  },
] as const;

type GovernanceSelectFilterConfig =
  (typeof GOVERNANCE_SELECT_FILTER_CONFIGS)[number];
type GovernanceSelectColumnKey = GovernanceSelectFilterConfig['columnKey'];
type GovernanceSelectFilterKey = GovernanceSelectFilterConfig['filterKey'];

type GovernanceKeywordFilterConfig =
  (typeof GOVERNANCE_KEYWORD_FILTER_CONFIGS)[number];
type GovernanceKeywordColumnKey = GovernanceKeywordFilterConfig['columnKey'];
type GovernanceKeywordFilterKey = GovernanceKeywordFilterConfig['filterKey'];

const PRODUCT_OPTIONS = [
  { label: '座舱', value: '250539396', disabled: false },
  { label: '车控', value: '250539397', disabled: false },
  { label: '全部（暂不支持）', value: 'ALL', disabled: true },
];

const FLOW_STATE_OPTIONS: Array<{ label: string; value: string }> = [
  { value: 'DTS001', label: '问题提交人填写' },
  { value: 'DTS002', label: '测试(项目)经理审核' },
  { value: 'DTS003', label: '项目经理审核' },
  { value: 'DTS004', label: '开发人员定位' },
  { value: 'DTS005', label: '项目经理审核定位' },
  { value: 'DTS006', label: '开发人员方案审计' },
  { value: 'DTS007', label: 'CCB方案审核' },
  { value: 'DTS008', label: '评审专家在线评审' },
  { value: 'DTS009', label: '开发人员审核修改' },
  { value: 'DTS010', label: '审核人员审核修改' },
  { value: 'DTS011', label: 'CMO归档' },
  { value: 'DTS012', label: '测试经理组织测试' },
  { value: 'DTS013', label: '测试人员回归测试' },
  { value: 'DTS014', label: '确认问题单' },
  { value: 'DTS015', label: '制定修补计划' },
  { value: 'FS99', label: '关闭' },
  { value: 'FS01', label: '撤销' },
];

const SEVERITY_OPTIONS: Array<{ label: string; value: string }> = [
  { value: 'Suggestion', label: '提示' },
  { value: 'Minor', label: '一般' },
  { value: 'Major', label: '严重' },
  { value: 'Critical', label: '关键' },
];

function createRecentTwoMonthRange(): [Date, Date] {
  const end = new Date();
  const start = new Date(end);
  start.setMonth(start.getMonth() - 2);
  return [start, end];
}

function createDefaultDateRange(): [Date, Date] {
  const end = new Date();
  const start = new Date(end);
  start.setMonth(start.getMonth() - 1);
  return [start, end];
}

function toTimestampMs(date: Date) {
  return Math.max(Math.floor(date.getTime()), 0);
}

function createDefaultFilters(): DtsStatisticsFilters {
  const [start, end] = createDefaultDateRange();
  return {
    productId: '250539396',
    flowStates: ['FS99'],
    severityNos: [],
    updateTimeBegin: toTimestampMs(start),
    updateTimeEnd: toTimestampMs(end),
    dtsBizNoKeyword: '',
    parentNoKeyword: '',
    projectNames: [],
    briefDescKeyword: '',
    iTestBackCountKeyword: '',
    iNumOfCloseDaysKeyword: '',
    iNumOfFirmDaysKeyword: '',
    iNumOfLocateDaysKeyword: '',
    iNumofModifyDaysKeyword: '',
    iNumofTestDaysKeyword: '',
    currentHandlerKeywords: [],
    creatorKeywords: [],
    sSubmitUserNameKeywords: [],
    last_dts009_handlerKeywords: [],
    last_dts010_handlerKeywords: [],
    last_dts013_handlerKeywords: [],
    createAtBegin: 0,
    createAtEnd: 0,
    dCloseTimeBegin: 0,
    dCloseTimeEnd: 0,
    uQbiCloseTypeNames: [],
    sDeptOneNoNames: [],
    sSubsystemNoNames: [],
    sConfigFlowTypes: [],
    auto_source_types: [],
    auto_pl_group_names: [],
    is_downstream_values: [],
    need_aar_values: [],
    need_dev_analyze_values: [],
    need_test_analyze_values: [],
    process_quality_type_keyword: '',
    qa_remark_keyword: '',
    dev_owner_name_keyword: [],
    issue_intro_stage_values: [],
    dev_feature_keyword: '',
    dev_sub_category_values: [],
    dev_reason_keyword: '',
    dev_intro_reason_keyword: '',
    dev_issue_intro_point_values: [],
    dev_issue_probability_values: [],
    dev_common_issue_type_values: [],
    is_base_soft_issue_values: [],
    is_duplicate_issue_values: [],
    duplicate_issue_no_keyword: '',
    dev_control_points_values: [],
    dev_intro_point_analysis_keyword: '',
    dev_improvements_keyword: '',
    dev_non_base_desc_values: [],
    dev_aar_link_keyword: '',
    dev_asset_link_keyword: '',
    dev_asset_type_values: [],
    dev_status_values: [],
    dev_remark_keyword: '',
    test_owner_name_keyword: [],
    test_miss_reason_values: [],
    test_standard_desc_keyword: '',
    test_improvements_keyword: '',
    test_non_test_desc_keyword: '',
    test_asset_link_keyword: '',
    test_status_values: [],
    test_remark_keyword: '',
  };
}

const activeTab = ref<TabKey>('list');

const editVisible = ref(false);
const batchEditVisible = ref(false);
const editingRow = ref<DtsMergedDefect | null>(null);
const selectedDtsBizNos = ref<string[]>([]);
const selectionFingerprint = ref('');
const selectionVersion = ref(0);
const syncingGridSelection = ref(false);

const dateRange = ref<[Date, Date] | null>(createDefaultDateRange());
const filters = ref<DtsStatisticsFilters>(createDefaultFilters());

const appliedFilters = ref<DtsStatisticsFilters | null>(null);
const summaryFingerprint = ref('');

function createEmptySummary(): DtsSummary {
  return {
    total_count: 0,
    open_count: 0,
    closed_count: 0,
    avg_process_days: 0,
    qa_filled_count: 0,
    qa_completion_rate: 0,
    dev_filled_count: 0,
    dev_completion_rate: 0,
    test_filled_count: 0,
    test_completion_rate: 0,
    severity_dist: [],
    status_dist: [],
    flow_type_dist: [],
    team_dist: [],
    close_type_dist: [],
    source_dist: [],
    auto_pl_group_dist: [],
    pl_group_dev_completion_dist: [],
    handler_dist: [],
    process_days_bucket_dist: [],
    issue_intro_stage_dist: [],
    dev_action_status_dist: [],
    test_action_status_dist: [],
    dev_sub_category_dist: [],
    test_miss_reason_dist: [],
    project_dist: [],
    action_status_dist: [],
    update_trend: null,
    pl_group_severity_matrix: null,
    snapshot: null,
  };
}

const summary = ref<DtsSummary>(createEmptySummary());
const summaryLoading = ref(false);
const queryLoading = ref(false);
const exportPreparing = ref(false);
const exportPrepareTask = ref<DtsExportTask | null>(null);
const dictOptions = ref<DtsDictOptions | null>(null);
const snapshotMeta = ref<DtsSnapshotMeta | null>(null);

function resolveGovTag(field: any, raw: unknown) {
  return resolveDtsGovernanceTagMeta(dictOptions.value, field, raw);
}

function resolveGovTagList(field: any, raw: unknown) {
  return resolveDtsGovernanceTagList(dictOptions.value, field, raw);
}

function openEdit(row: DtsMergedDefect) {
  editingRow.value = row;
  editVisible.value = true;
}

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

function bumpSelectionVersion() {
  selectionVersion.value += 1;
}

function setSelectedDtsBizNos(values?: string[]) {
  selectedDtsBizNos.value = normalizeStringArray(values);
  bumpSelectionVersion();
}

function clearBatchSelection({ silent = false }: { silent?: boolean } = {}) {
  if (selectedDtsBizNos.value.length === 0 && !selectionFingerprint.value) {
    return;
  }
  selectedDtsBizNos.value = [];
  selectionFingerprint.value = '';
  batchEditVisible.value = false;
  bumpSelectionVersion();
  if (!silent) {
    ElMessage.info('已清空当前批量选择');
  }
}

function syncCurrentPageSelection() {
  const rows = Array.isArray(gridApi.tableData.value)
    ? (gridApi.tableData.value as DtsMergedDefect[])
    : [];
  syncingGridSelection.value = true;
  gridApi.clearSelection();
  if (selectedDtsBizNos.value.length > 0) {
    const selectedSet = new Set(selectedDtsBizNos.value);
    rows.forEach((row) => {
      const defectNo = String(row?.dtsBizNo || '').trim();
      if (!defectNo || !selectedSet.has(defectNo)) {
        return;
      }
      gridApi.toggleRowSelection(row, true);
    });
  }
  void nextTick(() => {
    syncingGridSelection.value = false;
  });
}

function normalizeTimestampPair(left?: number, right?: number) {
  const begin = Math.max(Number(left || 0), 0);
  const end = Math.max(Number(right || 0), 0);
  if (begin > 0 && end > 0 && begin > end) {
    return { begin: end, end: begin };
  }
  return { begin, end };
}

function cloneFilters(source: DtsStatisticsFilters): DtsStatisticsFilters {
  let begin = Number(source.updateTimeBegin || 0);
  let end = Number(source.updateTimeEnd || 0);
  const createAtPair = normalizeTimestampPair(
    source.createAtBegin,
    source.createAtEnd,
  );
  const closeTimePair = normalizeTimestampPair(
    source.dCloseTimeBegin,
    source.dCloseTimeEnd,
  );
  if (begin > end) {
    const temp = begin;
    begin = end;
    end = temp;
  }
  return {
    productId: String(source.productId || '250539396'),
    flowStates: normalizeStringArray(source.flowStates),
    severityNos: normalizeStringArray(source.severityNos),
    updateTimeBegin: Math.max(begin, 0),
    updateTimeEnd: Math.max(end, 0),
    dtsBizNoKeyword: String(source.dtsBizNoKeyword || '').trim(),
    parentNoKeyword: String(source.parentNoKeyword || '').trim(),
    projectNames: normalizeStringArray(source.projectNames),
    briefDescKeyword: String(source.briefDescKeyword || '').trim(),
    iTestBackCountKeyword: String(source.iTestBackCountKeyword || '').trim(),
    iNumOfCloseDaysKeyword: String(source.iNumOfCloseDaysKeyword || '').trim(),
    iNumOfFirmDaysKeyword: String(source.iNumOfFirmDaysKeyword || '').trim(),
    iNumOfLocateDaysKeyword: String(
      source.iNumOfLocateDaysKeyword || '',
    ).trim(),
    iNumofModifyDaysKeyword: String(
      source.iNumofModifyDaysKeyword || '',
    ).trim(),
    iNumofTestDaysKeyword: String(source.iNumofTestDaysKeyword || '').trim(),
    currentHandlerKeywords: normalizeStringArray(source.currentHandlerKeywords),
    creatorKeywords: normalizeStringArray(source.creatorKeywords),
    sSubmitUserNameKeywords: normalizeStringArray(
      source.sSubmitUserNameKeywords,
    ),
    last_dts009_handlerKeywords: normalizeStringArray(
      source.last_dts009_handlerKeywords,
    ),
    last_dts010_handlerKeywords: normalizeStringArray(
      source.last_dts010_handlerKeywords,
    ),
    last_dts013_handlerKeywords: normalizeStringArray(
      source.last_dts013_handlerKeywords,
    ),
    createAtBegin: createAtPair.begin,
    createAtEnd: createAtPair.end,
    dCloseTimeBegin: closeTimePair.begin,
    dCloseTimeEnd: closeTimePair.end,
    uQbiCloseTypeNames: normalizeStringArray(source.uQbiCloseTypeNames),
    sDeptOneNoNames: normalizeStringArray(source.sDeptOneNoNames),
    sSubsystemNoNames: normalizeStringArray(source.sSubsystemNoNames),
    sConfigFlowTypes: normalizeStringArray(source.sConfigFlowTypes),
    auto_source_types: normalizeStringArray(source.auto_source_types),
    auto_pl_group_names: normalizeStringArray(source.auto_pl_group_names),
    is_downstream_values: normalizeStringArray(source.is_downstream_values),
    need_aar_values: normalizeStringArray(source.need_aar_values),
    need_dev_analyze_values: normalizeStringArray(
      source.need_dev_analyze_values,
    ),
    need_test_analyze_values: normalizeStringArray(
      source.need_test_analyze_values,
    ),
    process_quality_type_keyword: String(
      source.process_quality_type_keyword || '',
    ).trim(),
    qa_remark_keyword: String(source.qa_remark_keyword || '').trim(),
    dev_owner_name_keyword: normalizeStringArray(source.dev_owner_name_keyword),
    issue_intro_stage_values: normalizeStringArray(
      source.issue_intro_stage_values,
    ),
    dev_feature_keyword: String(source.dev_feature_keyword || '').trim(),
    dev_sub_category_values: normalizeStringArray(
      source.dev_sub_category_values,
    ),
    dev_reason_keyword: String(source.dev_reason_keyword || '').trim(),
    dev_intro_reason_keyword: String(
      source.dev_intro_reason_keyword || '',
    ).trim(),
    dev_issue_intro_point_values: normalizeStringArray(
      source.dev_issue_intro_point_values,
    ),
    dev_issue_probability_values: normalizeStringArray(
      source.dev_issue_probability_values,
    ),
    dev_common_issue_type_values: normalizeStringArray(
      source.dev_common_issue_type_values,
    ),
    is_base_soft_issue_values: normalizeStringArray(
      source.is_base_soft_issue_values,
    ),
    is_duplicate_issue_values: normalizeStringArray(
      source.is_duplicate_issue_values,
    ),
    duplicate_issue_no_keyword: String(
      source.duplicate_issue_no_keyword || '',
    ).trim(),
    dev_control_points_values: normalizeStringArray(
      source.dev_control_points_values,
    ),
    dev_intro_point_analysis_keyword: String(
      source.dev_intro_point_analysis_keyword || '',
    ).trim(),
    dev_improvements_keyword: String(
      source.dev_improvements_keyword || '',
    ).trim(),
    dev_non_base_desc_values: normalizeStringArray(
      source.dev_non_base_desc_values,
    ),
    dev_aar_link_keyword: String(source.dev_aar_link_keyword || '').trim(),
    dev_asset_link_keyword: String(source.dev_asset_link_keyword || '').trim(),
    dev_asset_type_values: normalizeStringArray(source.dev_asset_type_values),
    dev_status_values: normalizeStringArray(source.dev_status_values),
    dev_remark_keyword: String(source.dev_remark_keyword || '').trim(),
    test_owner_name_keyword: normalizeStringArray(
      source.test_owner_name_keyword,
    ),
    test_miss_reason_values: normalizeStringArray(
      source.test_miss_reason_values,
    ),
    test_standard_desc_keyword: String(
      source.test_standard_desc_keyword || '',
    ).trim(),
    test_improvements_keyword: String(
      source.test_improvements_keyword || '',
    ).trim(),
    test_non_test_desc_keyword: String(
      source.test_non_test_desc_keyword || '',
    ).trim(),
    test_asset_link_keyword: String(
      source.test_asset_link_keyword || '',
    ).trim(),
    test_status_values: normalizeStringArray(source.test_status_values),
    test_remark_keyword: String(source.test_remark_keyword || '').trim(),
  };
}

function buildFingerprint(payload: DtsStatisticsFilters | null) {
  if (!payload) {
    return '';
  }
  return JSON.stringify({
    productId: payload.productId || '',
    flowStates: [...(payload.flowStates || [])].sort(),
    severityNos: [...(payload.severityNos || [])].sort(),
    updateTimeBegin: payload.updateTimeBegin || 0,
    updateTimeEnd: payload.updateTimeEnd || 0,
    dtsBizNoKeyword: payload.dtsBizNoKeyword || '',
    parentNoKeyword: payload.parentNoKeyword || '',
    projectNames: [...(payload.projectNames || [])].sort(),
    briefDescKeyword: payload.briefDescKeyword || '',
    iTestBackCountKeyword: payload.iTestBackCountKeyword || '',
    iNumOfCloseDaysKeyword: payload.iNumOfCloseDaysKeyword || '',
    iNumOfFirmDaysKeyword: payload.iNumOfFirmDaysKeyword || '',
    iNumOfLocateDaysKeyword: payload.iNumOfLocateDaysKeyword || '',
    iNumofModifyDaysKeyword: payload.iNumofModifyDaysKeyword || '',
    iNumofTestDaysKeyword: payload.iNumofTestDaysKeyword || '',
    currentHandlerKeywords: [...(payload.currentHandlerKeywords || [])].sort(),
    creatorKeywords: [...(payload.creatorKeywords || [])].sort(),
    sSubmitUserNameKeywords: [
      ...(payload.sSubmitUserNameKeywords || []),
    ].sort(),
    last_dts009_handlerKeywords: [
      ...(payload.last_dts009_handlerKeywords || []),
    ].sort(),
    last_dts010_handlerKeywords: [
      ...(payload.last_dts010_handlerKeywords || []),
    ].sort(),
    last_dts013_handlerKeywords: [
      ...(payload.last_dts013_handlerKeywords || []),
    ].sort(),
    createAtBegin: payload.createAtBegin || 0,
    createAtEnd: payload.createAtEnd || 0,
    dCloseTimeBegin: payload.dCloseTimeBegin || 0,
    dCloseTimeEnd: payload.dCloseTimeEnd || 0,
    uQbiCloseTypeNames: [...(payload.uQbiCloseTypeNames || [])].sort(),
    sDeptOneNoNames: [...(payload.sDeptOneNoNames || [])].sort(),
    sSubsystemNoNames: [...(payload.sSubsystemNoNames || [])].sort(),
    sConfigFlowTypes: [...(payload.sConfigFlowTypes || [])].sort(),
    auto_source_types: [...(payload.auto_source_types || [])].sort(),
    auto_pl_group_names: [...(payload.auto_pl_group_names || [])].sort(),
    is_downstream_values: [...(payload.is_downstream_values || [])].sort(),
    need_aar_values: [...(payload.need_aar_values || [])].sort(),
    need_dev_analyze_values: [
      ...(payload.need_dev_analyze_values || []),
    ].sort(),
    need_test_analyze_values: [
      ...(payload.need_test_analyze_values || []),
    ].sort(),
    process_quality_type_keyword: payload.process_quality_type_keyword || '',
    qa_remark_keyword: payload.qa_remark_keyword || '',
    dev_owner_name_keyword: [...(payload.dev_owner_name_keyword || [])].sort(),
    issue_intro_stage_values: [
      ...(payload.issue_intro_stage_values || []),
    ].sort(),
    dev_feature_keyword: payload.dev_feature_keyword || '',
    dev_sub_category_values: [
      ...(payload.dev_sub_category_values || []),
    ].sort(),
    dev_reason_keyword: payload.dev_reason_keyword || '',
    dev_intro_reason_keyword: payload.dev_intro_reason_keyword || '',
    dev_issue_intro_point_values: [
      ...(payload.dev_issue_intro_point_values || []),
    ].sort(),
    dev_issue_probability_values: [
      ...(payload.dev_issue_probability_values || []),
    ].sort(),
    dev_common_issue_type_values: [
      ...(payload.dev_common_issue_type_values || []),
    ].sort(),
    is_base_soft_issue_values: [
      ...(payload.is_base_soft_issue_values || []),
    ].sort(),
    is_duplicate_issue_values: [
      ...(payload.is_duplicate_issue_values || []),
    ].sort(),
    duplicate_issue_no_keyword: payload.duplicate_issue_no_keyword || '',
    dev_control_points_values: [
      ...(payload.dev_control_points_values || []),
    ].sort(),
    dev_intro_point_analysis_keyword:
      payload.dev_intro_point_analysis_keyword || '',
    dev_improvements_keyword: payload.dev_improvements_keyword || '',
    dev_non_base_desc_values: [
      ...(payload.dev_non_base_desc_values || []),
    ].sort(),
    dev_aar_link_keyword: payload.dev_aar_link_keyword || '',
    dev_asset_link_keyword: payload.dev_asset_link_keyword || '',
    dev_asset_type_values: [...(payload.dev_asset_type_values || [])].sort(),
    dev_status_values: [...(payload.dev_status_values || [])].sort(),
    dev_remark_keyword: payload.dev_remark_keyword || '',
    test_owner_name_keyword: [
      ...(payload.test_owner_name_keyword || []),
    ].sort(),
    test_miss_reason_values: [
      ...(payload.test_miss_reason_values || []),
    ].sort(),
    test_standard_desc_keyword: payload.test_standard_desc_keyword || '',
    test_improvements_keyword: payload.test_improvements_keyword || '',
    test_non_test_desc_keyword: payload.test_non_test_desc_keyword || '',
    test_asset_link_keyword: payload.test_asset_link_keyword || '',
    test_status_values: [...(payload.test_status_values || [])].sort(),
    test_remark_keyword: payload.test_remark_keyword || '',
  });
}

async function loadDictOptions() {
  try {
    dictOptions.value = await fetchDtsDictOptionsCached();
  } catch (error) {
    console.error(error);
    dictOptions.value = null;
  }
}

function restoreDateValue(value?: number) {
  const normalized = Math.max(Number(value || 0), 0);
  if (normalized <= 0) {
    return null;
  }
  return new Date(normalized);
}

function syncSnapshotMeta(next?: DtsSnapshotMeta | null) {
  if (!next) {
    return;
  }
  snapshotMeta.value = { ...next };
}

function resolveAllowedUpdateWindowBegin() {
  const snapshotBegin = Number(snapshotMeta.value?.windowBegin || 0);
  if (snapshotBegin > 0) {
    return snapshotBegin;
  }
  const [start] = createRecentTwoMonthRange();
  return toTimestampMs(start);
}

function validateUpdateTimeRange(payload: DtsStatisticsFilters) {
  const begin = Math.max(Number(payload.updateTimeBegin || 0), 0);
  const end = Math.max(Number(payload.updateTimeEnd || 0), 0);
  const allowedBegin = resolveAllowedUpdateWindowBegin();
  if (begin > 0 && begin < allowedBegin) {
    return '当前仅支持最近 2 个月更新时间数据';
  }
  if (end > 0 && end < allowedBegin) {
    return '当前筛选时间早于缓存窗口，请调整到最近 2 个月内';
  }
  return '';
}

function disableOutOfWindowDate(date: Date) {
  return toTimestampMs(date) < resolveAllowedUpdateWindowBegin();
}

async function loadFieldSetOptions(fields: DtsFieldSetKey[]) {
  if (!appliedFilters.value || queryLoading.value) {
    return;
  }
  const requestPayload = {
    ...cloneFilters(filters.value),
    fields,
  };
  for (const field of fields) {
    fieldSetLoading.value[field] = true;
  }
  fieldSetLoading.value = { ...fieldSetLoading.value };
  try {
    const response = await getDtsFieldSets(requestPayload);
    const nextOptions = { ...fieldSetOptions.value };
    for (const field of fields) {
      nextOptions[field] = [...(response.fieldSets?.[field] || [])];
    }
    fieldSetOptions.value = nextOptions;
  } catch (error) {
    console.error(error);
    ElMessage.error(resolveErrorMessage(error, '加载筛选候选值失败'));
  } finally {
    const nextLoading = { ...fieldSetLoading.value };
    for (const field of fields) {
      nextLoading[field] = false;
    }
    fieldSetLoading.value = nextLoading;
  }
}

watch(
  dateRange,
  (value) => {
    if (value && value.length === 2) {
      filters.value.updateTimeBegin = toTimestampMs(value[0]);
      filters.value.updateTimeEnd = toTimestampMs(value[1]);
      return;
    }
    const [start, end] = createDefaultDateRange();
    filters.value.updateTimeBegin = toTimestampMs(start);
    filters.value.updateTimeEnd = toTimestampMs(end);
  },
  { immediate: true },
);

const hasAppliedFilters = computed(() => Boolean(appliedFilters.value));

async function fetchSummary(force = false) {
  if (!appliedFilters.value) {
    summary.value = createEmptySummary();
    summaryFingerprint.value = '';
    snapshotMeta.value = null;
    return;
  }

  const currentFingerprint = buildFingerprint(appliedFilters.value);
  if (!force && summaryFingerprint.value === currentFingerprint) {
    return;
  }
  summaryLoading.value = true;
  try {
    summary.value = await getDtsSummary(appliedFilters.value);
    syncSnapshotMeta(summary.value.snapshot || null);
    summaryFingerprint.value = currentFingerprint;
  } catch (error) {
    console.error(error);
    ElMessage.error(resolveErrorMessage(error, '加载总结看板失败'));
  } finally {
    summaryLoading.value = false;
  }
}

const [Grid, gridApi] = useZqTable({
  gridOptions: {
    columns: useColumns(),
    showSelection: true,
    border: true,
    stripe: true,
    rowKey: 'dtsBizNo',
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
          const response = await getDtsList({
            ...appliedFilters.value,
            pageIndex: page.currentPage,
            pageSize: page.pageSize,
          });
          syncSnapshotMeta(response.snapshot || null);
          return { items: response.items || [], total: response.total || 0 };
        },
      },
    },
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [20, 50, 100, 200, 500],
    },
    toolbarConfig: {
      custom: true,
      refresh: true,
      zoom: true,
    },
  },
});

function handleGridSelectionChange(selection: DtsMergedDefect[]) {
  if (syncingGridSelection.value) {
    return;
  }
  const currentPageIds = (
    Array.isArray(gridApi.tableData.value) ? gridApi.tableData.value : []
  )
    .map((row) => String(row?.dtsBizNo || '').trim())
    .filter(Boolean);
  const selectedPageIds = (selection || [])
    .map((row) => String(row?.dtsBizNo || '').trim())
    .filter(Boolean);

  const next = new Set(selectedDtsBizNos.value);
  currentPageIds.forEach((id) => next.delete(id));
  selectedPageIds.forEach((id) => next.add(id));
  selectedDtsBizNos.value = [...next];
  selectionFingerprint.value = buildFingerprint(appliedFilters.value);
}

watch(
  [() => gridApi.tableData.value, selectionVersion],
  async () => {
    await nextTick();
    syncCurrentPageSelection();
  },
  { deep: true },
);

const dataResultCount = computed(() => Number(gridApi.total.value || 0));
const selectedDtsCount = computed(() => selectedDtsBizNos.value.length);
const canExport = computed(
  () =>
    hasAppliedFilters.value &&
    dataResultCount.value > 0 &&
    !queryLoading.value &&
    !exportPreparing.value,
);
const canBatchEdit = computed(
  () =>
    hasAppliedFilters.value &&
    selectedDtsCount.value > 0 &&
    !queryLoading.value &&
    !exportPreparing.value,
);
const queryStatusText = computed(() =>
  queryLoading.value ? '正在从 DTS 快照缓存加载数据' : '',
);
const exportPrepareStatusText = computed(() => {
  if (!exportPreparing.value && !exportPrepareTask.value) {
    return '';
  }
  const task = exportPrepareTask.value;
  const progress = Number(task?.progress || 0);
  const baseMessage = task?.message || '导出准备中';
  return progress > 0 ? `${baseMessage}（${progress}%）` : baseMessage;
});
const selectedFlowStateLabel = computed(() => {
  const count = filters.value.flowStates.length;
  if (count === 0) {
    return '全部状态';
  }
  return `状态（${count}）`;
});
const selectedSeverityLabel = computed(() => {
  const count = filters.value.severityNos.length;
  if (count === 0) {
    return '全部级别';
  }
  return `级别（${count}）`;
});
function hasTimeRange(begin: number, end: number) {
  return Number(begin || 0) > 0 || Number(end || 0) > 0;
}
function buildTimeFilterButtonText(begin: number, end: number) {
  if (!hasTimeRange(begin, end)) {
    return '全部';
  }
  if (Number(begin || 0) > 0 && Number(end || 0) > 0) {
    return '已设定';
  }
  return '部分';
}
function buildKeywordFilterButtonText(value: string) {
  return String(value || '').trim() ? '已设定' : '全部';
}
const selectedDtsBizNoKeywordLabel = computed(() =>
  buildKeywordFilterButtonText(filters.value.dtsBizNoKeyword),
);
const selectedParentNoKeywordLabel = computed(() =>
  buildKeywordFilterButtonText(filters.value.parentNoKeyword),
);
const selectedProjectLabel = computed(() => {
  const count = filters.value.projectNames.length;
  return count > 0 ? `${count} 项` : '全部';
});
const selectedBriefDescKeywordLabel = computed(() =>
  buildKeywordFilterButtonText(filters.value.briefDescKeyword),
);
const selectedITestBackCountKeywordLabel = computed(() =>
  buildKeywordFilterButtonText(filters.value.iTestBackCountKeyword),
);
const selectedINumOfCloseDaysKeywordLabel = computed(() =>
  buildKeywordFilterButtonText(filters.value.iNumOfCloseDaysKeyword),
);
const selectedINumOfFirmDaysKeywordLabel = computed(() =>
  buildKeywordFilterButtonText(filters.value.iNumOfFirmDaysKeyword),
);
const selectedINumOfLocateDaysKeywordLabel = computed(() =>
  buildKeywordFilterButtonText(filters.value.iNumOfLocateDaysKeyword),
);
const selectedINumofModifyDaysKeywordLabel = computed(() =>
  buildKeywordFilterButtonText(filters.value.iNumofModifyDaysKeyword),
);
const selectedINumofTestDaysKeywordLabel = computed(() =>
  buildKeywordFilterButtonText(filters.value.iNumofTestDaysKeyword),
);
const selectedCurrentHandlerLabel = computed(() => {
  const count = filters.value.currentHandlerKeywords.length;
  return count > 0 ? `${count} 项` : '全部';
});
const selectedCreatorLabel = computed(() => {
  const count = filters.value.creatorKeywords.length;
  return count > 0 ? `${count} 项` : '全部';
});
const selectedSubmitUserNameLabel = computed(() => {
  const count = filters.value.sSubmitUserNameKeywords.length;
  return count > 0 ? `${count} 项` : '全部';
});
const selectedLastDts009HandlerLabel = computed(() => {
  const count = filters.value.last_dts009_handlerKeywords.length;
  return count > 0 ? `${count} 项` : '全部';
});
const selectedLastDts010HandlerLabel = computed(() => {
  const count = filters.value.last_dts010_handlerKeywords.length;
  return count > 0 ? `${count} 项` : '全部';
});
const selectedLastDts013HandlerLabel = computed(() => {
  const count = filters.value.last_dts013_handlerKeywords.length;
  return count > 0 ? `${count} 项` : '全部';
});
const selectedDevOwnerNameLabel = computed(() => {
  const count = filters.value.dev_owner_name_keyword.length;
  return count > 0 ? `${count} 项` : '全部';
});
const selectedTestOwnerNameLabel = computed(() => {
  const count = filters.value.test_owner_name_keyword.length;
  return count > 0 ? `${count} 项` : '全部';
});
const selectedCreateAtLabel = computed(() =>
  buildTimeFilterButtonText(
    filters.value.createAtBegin,
    filters.value.createAtEnd,
  ),
);
const selectedCloseTimeLabel = computed(() =>
  buildTimeFilterButtonText(
    filters.value.dCloseTimeBegin,
    filters.value.dCloseTimeEnd,
  ),
);
const selectedCloseTypeLabel = computed(() => {
  const count = filters.value.uQbiCloseTypeNames.length;
  return count > 0 ? `${count} 项` : '全部';
});
const selectedConfigFlowTypeLabel = computed(() => {
  const count = filters.value.sConfigFlowTypes.length;
  return count > 0 ? `${count} 项` : '全部';
});
const selectedAutoSourceLabel = computed(() => {
  const count = filters.value.auto_source_types.length;
  return count > 0 ? `${count} 项` : '全部';
});
const selectedDeptLabel = computed(() => {
  const count = filters.value.sDeptOneNoNames.length;
  return count > 0 ? `${count} 项` : '全部';
});
const selectedSubsystemLabel = computed(() => {
  const count = filters.value.sSubsystemNoNames.length;
  return count > 0 ? `${count} 项` : '全部';
});
const selectedAutoPlGroupLabel = computed(() => {
  const count = filters.value.auto_pl_group_names.length;
  return count > 0 ? `${count} 项` : '全部';
});
function filterFieldOptions(options: string[], keyword: string) {
  const normalizedKeyword = String(keyword || '')
    .trim()
    .toLowerCase();
  if (!normalizedKeyword) {
    return options;
  }
  return options.filter((item) =>
    String(item || '')
      .toLowerCase()
      .includes(normalizedKeyword),
  );
}

function resolveErrorMessage(error: any, fallback: string) {
  const candidates = [
    error?.response?.data?.detail,
    error?.response?.data?.message,
    error?.response?._data?.detail,
    error?.response?._data?.message,
    error?.message,
  ];
  const matched = candidates.find(
    (item) => typeof item === 'string' && item.trim().length > 0,
  );
  return matched || fallback;
}

const selectedProductLabel = computed(() => {
  return (
    PRODUCT_OPTIONS.find((item) => item.value === filters.value.productId)
      ?.label || '座舱'
  );
});

const flowFilterVisible = ref(false);
const severityFilterVisible = ref(false);
const dtsBizNoFilterVisible = ref(false);
const parentNoFilterVisible = ref(false);
const projectFilterVisible = ref(false);
const briefDescFilterVisible = ref(false);
const iTestBackCountFilterVisible = ref(false);
const iNumOfCloseDaysFilterVisible = ref(false);
const iNumOfFirmDaysFilterVisible = ref(false);
const iNumOfLocateDaysFilterVisible = ref(false);
const iNumofModifyDaysFilterVisible = ref(false);
const iNumofTestDaysFilterVisible = ref(false);
const currentHandlerFilterVisible = ref(false);
const creatorFilterVisible = ref(false);
const submitUserNameFilterVisible = ref(false);
const lastDts009HandlerFilterVisible = ref(false);
const lastDts010HandlerFilterVisible = ref(false);
const lastDts013HandlerFilterVisible = ref(false);
const devOwnerNameFilterVisible = ref(false);
const testOwnerNameFilterVisible = ref(false);
const createAtFilterVisible = ref(false);
const closeTimeFilterVisible = ref(false);
const closeTypeFilterVisible = ref(false);
const configFlowTypeFilterVisible = ref(false);
const autoSourceFilterVisible = ref(false);
const deptFilterVisible = ref(false);
const subsystemFilterVisible = ref(false);
const autoPlGroupFilterVisible = ref(false);
const draftFlowStates = ref<string[]>([]);
const draftSeverityNos = ref<string[]>([]);
const draftDtsBizNoKeyword = ref('');
const draftParentNoKeyword = ref('');
const draftProjectNames = ref<string[]>([]);
const draftBriefDescKeyword = ref('');
const draftITestBackCountKeyword = ref('');
const draftINumOfCloseDaysKeyword = ref('');
const draftINumOfFirmDaysKeyword = ref('');
const draftINumOfLocateDaysKeyword = ref('');
const draftINumofModifyDaysKeyword = ref('');
const draftINumofTestDaysKeyword = ref('');
const draftCurrentHandlerKeywords = ref<string[]>([]);
const draftCreatorKeywords = ref<string[]>([]);
const draftSubmitUserNameKeywords = ref<string[]>([]);
const draftLastDts009HandlerKeywords = ref<string[]>([]);
const draftLastDts010HandlerKeywords = ref<string[]>([]);
const draftLastDts013HandlerKeywords = ref<string[]>([]);
const draftDevOwnerNameKeywords = ref<string[]>([]);
const draftTestOwnerNameKeywords = ref<string[]>([]);
const draftCreateAtBegin = ref<Date | null>(null);
const draftCreateAtEnd = ref<Date | null>(null);
const draftCloseTimeBegin = ref<Date | null>(null);
const draftCloseTimeEnd = ref<Date | null>(null);
const draftCloseTypeNames = ref<string[]>([]);
const draftConfigFlowTypes = ref<string[]>([]);
const draftAutoSourceTypes = ref<string[]>([]);
const draftDeptNames = ref<string[]>([]);
const draftSubsystemNames = ref<string[]>([]);
const draftAutoPlGroupNames = ref<string[]>([]);
const draftCloseTypeKeyword = ref('');
const draftConfigFlowTypeKeyword = ref('');
const draftAutoSourceKeyword = ref('');
const draftProjectKeyword = ref('');
const draftDeptKeyword = ref('');
const draftSubsystemKeyword = ref('');
const draftAutoPlGroupKeyword = ref('');
const fieldSetOptions = ref<DtsFieldSetOptionsState>({
  uQbiCloseTypeName: [],
  sConfigFlowType: [],
  auto_source_type: [],
  projectName: [],
  sDeptOneNoName: [],
  sSubsystemNoName: [],
  auto_pl_group_name: [],
});
const fieldSetLoading = ref<DtsFieldSetLoadingState>({
  uQbiCloseTypeName: false,
  sConfigFlowType: false,
  auto_source_type: false,
  projectName: false,
  sDeptOneNoName: false,
  sSubsystemNoName: false,
  auto_pl_group_name: false,
});
const filteredCloseTypeOptions = computed(() =>
  filterFieldOptions(
    fieldSetOptions.value.uQbiCloseTypeName || [],
    draftCloseTypeKeyword.value,
  ),
);
const filteredConfigFlowTypeOptions = computed(() =>
  filterFieldOptions(
    fieldSetOptions.value.sConfigFlowType || [],
    draftConfigFlowTypeKeyword.value,
  ),
);
const filteredAutoSourceOptions = computed(() =>
  filterFieldOptions(
    fieldSetOptions.value.auto_source_type || [],
    draftAutoSourceKeyword.value,
  ),
);
const filteredProjectOptions = computed(() =>
  filterFieldOptions(
    fieldSetOptions.value.projectName || [],
    draftProjectKeyword.value,
  ),
);
const filteredDeptOptions = computed(() =>
  filterFieldOptions(
    fieldSetOptions.value.sDeptOneNoName || [],
    draftDeptKeyword.value,
  ),
);
const filteredSubsystemOptions = computed(() =>
  filterFieldOptions(
    fieldSetOptions.value.sSubsystemNoName || [],
    draftSubsystemKeyword.value,
  ),
);
const filteredAutoPlGroupOptions = computed(() =>
  filterFieldOptions(
    fieldSetOptions.value.auto_pl_group_name || [],
    draftAutoPlGroupKeyword.value,
  ),
);

function createGovernanceSelectRecord<T>(
  factory: (config: GovernanceSelectFilterConfig) => T,
) {
  const record = {} as Record<GovernanceSelectColumnKey, T>;
  for (const config of GOVERNANCE_SELECT_FILTER_CONFIGS) {
    record[config.columnKey] = factory(config);
  }
  return record;
}

function createGovernanceKeywordRecord<T>(
  factory: (config: GovernanceKeywordFilterConfig) => T,
) {
  const record = {} as Record<GovernanceKeywordColumnKey, T>;
  for (const config of GOVERNANCE_KEYWORD_FILTER_CONFIGS) {
    record[config.columnKey] = factory(config);
  }
  return record;
}

const governanceSelectVisible = ref<Record<GovernanceSelectColumnKey, boolean>>(
  createGovernanceSelectRecord(() => false),
);
const governanceSelectDraft = ref<Record<GovernanceSelectColumnKey, string[]>>(
  createGovernanceSelectRecord(() => []),
);
const governanceSelectKeyword = ref<Record<GovernanceSelectColumnKey, string>>(
  createGovernanceSelectRecord(() => ''),
);

const governanceKeywordVisible = ref<
  Record<GovernanceKeywordColumnKey, boolean>
>(createGovernanceKeywordRecord(() => false));
const governanceKeywordDraft = ref<Record<GovernanceKeywordColumnKey, string>>(
  createGovernanceKeywordRecord(() => ''),
);

function getFilterArrayValue(key: GovernanceSelectFilterKey): string[] {
  return normalizeStringArray((filters.value as Record<string, any>)[key]);
}

function setFilterArrayValue(key: GovernanceSelectFilterKey, value: string[]) {
  (filters.value as Record<string, any>)[key] = normalizeStringArray(value);
}

function getFilterKeywordValue(key: GovernanceKeywordFilterKey): string {
  return String((filters.value as Record<string, any>)[key] || '').trim();
}

function setFilterKeywordValue(key: GovernanceKeywordFilterKey, value: string) {
  (filters.value as Record<string, any>)[key] = String(value || '').trim();
}

function resolveDictCandidateValues(config: GovernanceSelectFilterConfig) {
  const options = (dictOptions.value?.[config.dictKey] || []) as Array<{
    label?: string;
    value?: string;
  }>;
  const seen = new Set<string>();
  const result: string[] = [];
  options.forEach((item) => {
    const text = String(item.label || item.value || '').trim();
    if (!text || seen.has(text)) {
      return;
    }
    seen.add(text);
    result.push(text);
  });
  return result;
}

function getGovernanceSelectOptions(config: GovernanceSelectFilterConfig) {
  const keyword = governanceSelectKeyword.value[config.columnKey] || '';
  return filterFieldOptions(resolveDictCandidateValues(config), keyword);
}

function buildMultiFilterLabel(values: string[]) {
  const count = normalizeStringArray(values).length;
  return count > 0 ? `${count} 项` : '全部';
}

function handleGovernanceSelectPopoverShow(
  config: GovernanceSelectFilterConfig,
) {
  governanceSelectDraft.value[config.columnKey] = getFilterArrayValue(
    config.filterKey,
  );
  governanceSelectKeyword.value[config.columnKey] = '';
  if (!dictOptions.value) {
    void loadDictOptions();
  }
}

function resetGovernanceSelectFilterDraft(
  config: GovernanceSelectFilterConfig,
) {
  governanceSelectDraft.value[config.columnKey] = [];
  governanceSelectKeyword.value[config.columnKey] = '';
}

async function confirmGovernanceSelectFilter(
  config: GovernanceSelectFilterConfig,
) {
  setFilterArrayValue(
    config.filterKey,
    governanceSelectDraft.value[config.columnKey] || [],
  );
  governanceSelectVisible.value[config.columnKey] = false;
  await handleSearch(true);
}

function handleGovernanceKeywordPopoverShow(
  config: GovernanceKeywordFilterConfig,
) {
  governanceKeywordDraft.value[config.columnKey] = getFilterKeywordValue(
    config.filterKey,
  );
}

function resetGovernanceKeywordFilterDraft(
  config: GovernanceKeywordFilterConfig,
) {
  governanceKeywordDraft.value[config.columnKey] = '';
}

async function confirmGovernanceKeywordFilter(
  config: GovernanceKeywordFilterConfig,
) {
  setFilterKeywordValue(
    config.filterKey,
    governanceKeywordDraft.value[config.columnKey] || '',
  );
  governanceKeywordVisible.value[config.columnKey] = false;
  await handleSearch(true);
}

let autoReloadTimer: null | number = null;
let exportPrepareTimer: null | number = null;
let exportPollingSerial = 0;
let suspendAutoReload = false;
const pollMaxWaitMs = 10 * 60 * 1000;

watch(
  () => gridApi.tableData.value.length,
  async () => {
    await nextTick();
    updateDataGridHeight();
  },
);

const dataGridWrapRef = ref<HTMLDivElement>();
const dataGridHeight = ref<null | number>(null);

const dataGridWrapStyle = computed(() => {
  if (!dataGridHeight.value) {
    return undefined;
  }
  return { height: `${dataGridHeight.value}px` };
});

let resizeTimer: null | number = null;

function updateDataGridHeight() {
  if (!dataGridWrapRef.value || activeTab.value !== 'list') {
    dataGridHeight.value = null;
    return;
  }
  const rect = dataGridWrapRef.value.getBoundingClientRect();
  const bottomOffset = 24;
  const available = window.innerHeight - rect.top - bottomOffset;
  dataGridHeight.value = Math.max(320, Math.floor(available));
}

function handleResize() {
  if (resizeTimer) {
    window.clearTimeout(resizeTimer);
  }
  resizeTimer = window.setTimeout(() => {
    updateDataGridHeight();
  }, 120);
}

function scheduleAutoReload() {
  if (autoReloadTimer) {
    window.clearTimeout(autoReloadTimer);
  }
  autoReloadTimer = window.setTimeout(() => {
    void handleSearch(true);
  }, 260);
}

watch(
  () => ({
    productId: filters.value.productId,
    updateTimeBegin: filters.value.updateTimeBegin,
    updateTimeEnd: filters.value.updateTimeEnd,
  }),
  () => {
    if (
      suspendAutoReload ||
      !filters.value.productId ||
      filters.value.productId === 'ALL'
    ) {
      return;
    }
    scheduleAutoReload();
  },
  { deep: true },
);

watch(
  () => flowFilterVisible.value,
  (visible) => {
    if (visible) {
      draftFlowStates.value = [...filters.value.flowStates];
    }
  },
);

watch(
  () => severityFilterVisible.value,
  (visible) => {
    if (visible) {
      draftSeverityNos.value = [...filters.value.severityNos];
    }
  },
);

watch(
  () => dtsBizNoFilterVisible.value,
  (visible) => {
    if (visible) {
      draftDtsBizNoKeyword.value = filters.value.dtsBizNoKeyword || '';
    }
  },
);

watch(
  () => parentNoFilterVisible.value,
  (visible) => {
    if (visible) {
      draftParentNoKeyword.value = filters.value.parentNoKeyword || '';
    }
  },
);

watch(
  () => projectFilterVisible.value,
  (visible) => {
    if (visible) {
      if (!appliedFilters.value || queryLoading.value) {
        projectFilterVisible.value = false;
        ElMessage.warning('请先完成当前查询，再打开候选值筛选');
        return;
      }
      draftProjectNames.value = [...filters.value.projectNames];
      draftProjectKeyword.value = '';
      void loadFieldSetOptions(['projectName']);
    }
  },
);

watch(
  () => briefDescFilterVisible.value,
  (visible) => {
    if (visible) {
      draftBriefDescKeyword.value = filters.value.briefDescKeyword || '';
    }
  },
);

watch(
  () => iTestBackCountFilterVisible.value,
  (visible) => {
    if (visible) {
      draftITestBackCountKeyword.value =
        filters.value.iTestBackCountKeyword || '';
    }
  },
);

watch(
  () => iNumOfCloseDaysFilterVisible.value,
  (visible) => {
    if (visible) {
      draftINumOfCloseDaysKeyword.value =
        filters.value.iNumOfCloseDaysKeyword || '';
    }
  },
);

watch(
  () => iNumOfFirmDaysFilterVisible.value,
  (visible) => {
    if (visible) {
      draftINumOfFirmDaysKeyword.value =
        filters.value.iNumOfFirmDaysKeyword || '';
    }
  },
);

watch(
  () => iNumOfLocateDaysFilterVisible.value,
  (visible) => {
    if (visible) {
      draftINumOfLocateDaysKeyword.value =
        filters.value.iNumOfLocateDaysKeyword || '';
    }
  },
);

watch(
  () => iNumofModifyDaysFilterVisible.value,
  (visible) => {
    if (visible) {
      draftINumofModifyDaysKeyword.value =
        filters.value.iNumofModifyDaysKeyword || '';
    }
  },
);

watch(
  () => iNumofTestDaysFilterVisible.value,
  (visible) => {
    if (visible) {
      draftINumofTestDaysKeyword.value =
        filters.value.iNumofTestDaysKeyword || '';
    }
  },
);

watch(
  () => currentHandlerFilterVisible.value,
  (visible) => {
    if (visible) {
      draftCurrentHandlerKeywords.value = [
        ...filters.value.currentHandlerKeywords,
      ];
    }
  },
);

watch(
  () => creatorFilterVisible.value,
  (visible) => {
    if (visible) {
      draftCreatorKeywords.value = [...filters.value.creatorKeywords];
    }
  },
);

watch(
  () => submitUserNameFilterVisible.value,
  (visible) => {
    if (visible) {
      draftSubmitUserNameKeywords.value = [
        ...filters.value.sSubmitUserNameKeywords,
      ];
    }
  },
);

watch(
  () => lastDts009HandlerFilterVisible.value,
  (visible) => {
    if (visible) {
      draftLastDts009HandlerKeywords.value = [
        ...filters.value.last_dts009_handlerKeywords,
      ];
    }
  },
);

watch(
  () => lastDts010HandlerFilterVisible.value,
  (visible) => {
    if (visible) {
      draftLastDts010HandlerKeywords.value = [
        ...filters.value.last_dts010_handlerKeywords,
      ];
    }
  },
);

watch(
  () => lastDts013HandlerFilterVisible.value,
  (visible) => {
    if (visible) {
      draftLastDts013HandlerKeywords.value = [
        ...filters.value.last_dts013_handlerKeywords,
      ];
    }
  },
);

watch(
  () => devOwnerNameFilterVisible.value,
  (visible) => {
    if (visible) {
      draftDevOwnerNameKeywords.value = [
        ...filters.value.dev_owner_name_keyword,
      ];
    }
  },
);

watch(
  () => testOwnerNameFilterVisible.value,
  (visible) => {
    if (visible) {
      draftTestOwnerNameKeywords.value = [
        ...filters.value.test_owner_name_keyword,
      ];
    }
  },
);

watch(
  () => createAtFilterVisible.value,
  (visible) => {
    if (visible) {
      draftCreateAtBegin.value = restoreDateValue(filters.value.createAtBegin);
      draftCreateAtEnd.value = restoreDateValue(filters.value.createAtEnd);
    }
  },
);

watch(
  () => closeTimeFilterVisible.value,
  (visible) => {
    if (visible) {
      draftCloseTimeBegin.value = restoreDateValue(
        filters.value.dCloseTimeBegin,
      );
      draftCloseTimeEnd.value = restoreDateValue(filters.value.dCloseTimeEnd);
    }
  },
);

watch(
  () => closeTypeFilterVisible.value,
  (visible) => {
    if (visible) {
      if (!appliedFilters.value || queryLoading.value) {
        closeTypeFilterVisible.value = false;
        ElMessage.warning('请先完成当前查询，再打开候选值筛选');
        return;
      }
      draftCloseTypeNames.value = [...filters.value.uQbiCloseTypeNames];
      draftCloseTypeKeyword.value = '';
      void loadFieldSetOptions(['uQbiCloseTypeName']);
    }
  },
);

watch(
  () => configFlowTypeFilterVisible.value,
  (visible) => {
    if (visible) {
      if (!appliedFilters.value || queryLoading.value) {
        configFlowTypeFilterVisible.value = false;
        ElMessage.warning('请先完成当前查询，再打开候选值筛选');
        return;
      }
      draftConfigFlowTypes.value = [...filters.value.sConfigFlowTypes];
      draftConfigFlowTypeKeyword.value = '';
      void loadFieldSetOptions(['sConfigFlowType']);
    }
  },
);

watch(
  () => autoSourceFilterVisible.value,
  (visible) => {
    if (visible) {
      if (!appliedFilters.value || queryLoading.value) {
        autoSourceFilterVisible.value = false;
        ElMessage.warning('请先完成当前查询，再打开候选值筛选');
        return;
      }
      draftAutoSourceTypes.value = [...filters.value.auto_source_types];
      draftAutoSourceKeyword.value = '';
      void loadFieldSetOptions(['auto_source_type']);
    }
  },
);

watch(
  () => deptFilterVisible.value,
  (visible) => {
    if (visible) {
      if (!appliedFilters.value || queryLoading.value) {
        deptFilterVisible.value = false;
        ElMessage.warning('请先完成当前查询，再打开候选值筛选');
        return;
      }
      draftDeptNames.value = [...filters.value.sDeptOneNoNames];
      draftDeptKeyword.value = '';
      void loadFieldSetOptions(['sDeptOneNoName']);
    }
  },
);

watch(
  () => subsystemFilterVisible.value,
  (visible) => {
    if (visible) {
      if (!appliedFilters.value || queryLoading.value) {
        subsystemFilterVisible.value = false;
        ElMessage.warning('请先完成当前查询，再打开候选值筛选');
        return;
      }
      draftSubsystemNames.value = [...filters.value.sSubsystemNoNames];
      draftSubsystemKeyword.value = '';
      void loadFieldSetOptions(['sSubsystemNoName']);
    }
  },
);

watch(
  () => autoPlGroupFilterVisible.value,
  (visible) => {
    if (visible) {
      if (!appliedFilters.value || queryLoading.value) {
        autoPlGroupFilterVisible.value = false;
        ElMessage.warning('请先完成当前查询，再打开候选值筛选');
        return;
      }
      draftAutoPlGroupNames.value = [...filters.value.auto_pl_group_names];
      draftAutoPlGroupKeyword.value = '';
      void loadFieldSetOptions(['auto_pl_group_name']);
    }
  },
);

watch(
  () => activeTab.value,
  (tab) => {
    if (tab === 'dashboard') {
      void fetchSummary();
    }
    void nextTick().then(() => updateDataGridHeight());
  },
);

async function handleSearch(resetPage = true) {
  if (queryLoading.value) {
    return;
  }
  if (autoReloadTimer) {
    window.clearTimeout(autoReloadTimer);
    autoReloadTimer = null;
  }
  const payload = cloneFilters(filters.value);
  await runSearch(payload, { resetPage });
}

function stopExportPreparePolling() {
  exportPollingSerial += 1;
  if (exportPrepareTimer) {
    window.clearInterval(exportPrepareTimer);
    exportPrepareTimer = null;
  }
}

async function runSearch(
  payload: DtsStatisticsFilters,
  { resetPage = true }: { resetPage?: boolean } = {},
) {
  if (!payload.productId || payload.productId === 'ALL') {
    ElMessage.warning('“全部”产品暂不支持查询，请选择座舱或车控');
    return;
  }
  const invalidMessage = validateUpdateTimeRange(payload);
  if (invalidMessage) {
    ElMessage.warning(invalidMessage);
    return;
  }
  const nextFingerprint = buildFingerprint(payload);
  if (
    selectedDtsBizNos.value.length > 0 &&
    selectionFingerprint.value &&
    selectionFingerprint.value !== nextFingerprint
  ) {
    clearBatchSelection({ silent: true });
    ElMessage.info('筛选条件已变更，已清空之前的批量选择');
  }
  const previousApplied = appliedFilters.value
    ? cloneFilters(appliedFilters.value)
    : null;
  const previousFingerprint = summaryFingerprint.value;
  const previousSummary = { ...summary.value };
  const previousSnapshot = snapshotMeta.value
    ? { ...snapshotMeta.value }
    : null;
  queryLoading.value = true;
  appliedFilters.value = cloneFilters(payload);
  summaryFingerprint.value = '';
  gridApi.setLoading(true);
  try {
    if (resetPage) {
      gridApi.pagination.currentPage = 1;
    }
    await nextTick();
    await Promise.all([gridApi.reload(), fetchSummary(true)]);
    selectionFingerprint.value = nextFingerprint;
    await nextTick();
    updateDataGridHeight();
  } catch (error) {
    console.error(error);
    appliedFilters.value = previousApplied;
    summaryFingerprint.value = previousFingerprint;
    summary.value = previousSummary;
    snapshotMeta.value = previousSnapshot;
    ElMessage.error(resolveErrorMessage(error, '查询失败，请稍后重试'));
  } finally {
    queryLoading.value = false;
    gridApi.setLoading(false);
  }
}

async function handleReset() {
  if (autoReloadTimer) {
    window.clearTimeout(autoReloadTimer);
    autoReloadTimer = null;
  }
  queryLoading.value = false;
  gridApi.setLoading(false);
  stopExportPreparePolling();
  exportPreparing.value = false;
  exportPrepareTask.value = null;
  clearBatchSelection({ silent: true });
  const nextFilters = createDefaultFilters();
  suspendAutoReload = true;
  filters.value = nextFilters;
  dateRange.value = [
    new Date(nextFilters.updateTimeBegin),
    new Date(nextFilters.updateTimeEnd),
  ];
  suspendAutoReload = false;
  await handleSearch(true);
}

async function confirmFlowFilter() {
  filters.value.flowStates = normalizeStringArray(draftFlowStates.value);
  flowFilterVisible.value = false;
  await handleSearch(true);
}

function resetFlowFilterDraft() {
  draftFlowStates.value = [];
}

async function confirmSeverityFilter() {
  filters.value.severityNos = normalizeStringArray(draftSeverityNos.value);
  severityFilterVisible.value = false;
  await handleSearch(true);
}

function resetSeverityFilterDraft() {
  draftSeverityNos.value = [];
}

async function confirmDtsBizNoFilter() {
  filters.value.dtsBizNoKeyword = String(
    draftDtsBizNoKeyword.value || '',
  ).trim();
  dtsBizNoFilterVisible.value = false;
  await handleSearch(true);
}

function resetDtsBizNoFilterDraft() {
  draftDtsBizNoKeyword.value = '';
}

async function confirmParentNoFilter() {
  filters.value.parentNoKeyword = String(
    draftParentNoKeyword.value || '',
  ).trim();
  parentNoFilterVisible.value = false;
  await handleSearch(true);
}

function resetParentNoFilterDraft() {
  draftParentNoKeyword.value = '';
}

async function confirmProjectFilter() {
  filters.value.projectNames = normalizeStringArray(draftProjectNames.value);
  projectFilterVisible.value = false;
  await handleSearch(true);
}

function resetProjectFilterDraft() {
  draftProjectNames.value = [];
  draftProjectKeyword.value = '';
}

async function confirmBriefDescFilter() {
  filters.value.briefDescKeyword = String(
    draftBriefDescKeyword.value || '',
  ).trim();
  briefDescFilterVisible.value = false;
  await handleSearch(true);
}

function resetBriefDescFilterDraft() {
  draftBriefDescKeyword.value = '';
}

async function confirmITestBackCountFilter() {
  filters.value.iTestBackCountKeyword = String(
    draftITestBackCountKeyword.value || '',
  ).trim();
  iTestBackCountFilterVisible.value = false;
  await handleSearch(true);
}

function resetITestBackCountFilterDraft() {
  draftITestBackCountKeyword.value = '';
}

async function confirmINumOfCloseDaysFilter() {
  filters.value.iNumOfCloseDaysKeyword = String(
    draftINumOfCloseDaysKeyword.value || '',
  ).trim();
  iNumOfCloseDaysFilterVisible.value = false;
  await handleSearch(true);
}

function resetINumOfCloseDaysFilterDraft() {
  draftINumOfCloseDaysKeyword.value = '';
}

async function confirmINumOfFirmDaysFilter() {
  filters.value.iNumOfFirmDaysKeyword = String(
    draftINumOfFirmDaysKeyword.value || '',
  ).trim();
  iNumOfFirmDaysFilterVisible.value = false;
  await handleSearch(true);
}

function resetINumOfFirmDaysFilterDraft() {
  draftINumOfFirmDaysKeyword.value = '';
}

async function confirmINumOfLocateDaysFilter() {
  filters.value.iNumOfLocateDaysKeyword = String(
    draftINumOfLocateDaysKeyword.value || '',
  ).trim();
  iNumOfLocateDaysFilterVisible.value = false;
  await handleSearch(true);
}

function resetINumOfLocateDaysFilterDraft() {
  draftINumOfLocateDaysKeyword.value = '';
}

async function confirmINumofModifyDaysFilter() {
  filters.value.iNumofModifyDaysKeyword = String(
    draftINumofModifyDaysKeyword.value || '',
  ).trim();
  iNumofModifyDaysFilterVisible.value = false;
  await handleSearch(true);
}

function resetINumofModifyDaysFilterDraft() {
  draftINumofModifyDaysKeyword.value = '';
}

async function confirmINumofTestDaysFilter() {
  filters.value.iNumofTestDaysKeyword = String(
    draftINumofTestDaysKeyword.value || '',
  ).trim();
  iNumofTestDaysFilterVisible.value = false;
  await handleSearch(true);
}

function resetINumofTestDaysFilterDraft() {
  draftINumofTestDaysKeyword.value = '';
}

async function confirmCurrentHandlerFilter() {
  filters.value.currentHandlerKeywords = normalizeStringArray(
    draftCurrentHandlerKeywords.value,
  );
  currentHandlerFilterVisible.value = false;
  await handleSearch(true);
}

function resetCurrentHandlerFilterDraft() {
  draftCurrentHandlerKeywords.value = [];
}

async function confirmCreatorFilter() {
  filters.value.creatorKeywords = normalizeStringArray(
    draftCreatorKeywords.value,
  );
  creatorFilterVisible.value = false;
  await handleSearch(true);
}

function resetCreatorFilterDraft() {
  draftCreatorKeywords.value = [];
}

async function confirmSubmitUserNameFilter() {
  filters.value.sSubmitUserNameKeywords = normalizeStringArray(
    draftSubmitUserNameKeywords.value,
  );
  submitUserNameFilterVisible.value = false;
  await handleSearch(true);
}

function resetSubmitUserNameFilterDraft() {
  draftSubmitUserNameKeywords.value = [];
}

async function confirmLastDts009HandlerFilter() {
  filters.value.last_dts009_handlerKeywords = normalizeStringArray(
    draftLastDts009HandlerKeywords.value,
  );
  lastDts009HandlerFilterVisible.value = false;
  await handleSearch(true);
}

function resetLastDts009HandlerFilterDraft() {
  draftLastDts009HandlerKeywords.value = [];
}

async function confirmLastDts010HandlerFilter() {
  filters.value.last_dts010_handlerKeywords = normalizeStringArray(
    draftLastDts010HandlerKeywords.value,
  );
  lastDts010HandlerFilterVisible.value = false;
  await handleSearch(true);
}

function resetLastDts010HandlerFilterDraft() {
  draftLastDts010HandlerKeywords.value = [];
}

async function confirmLastDts013HandlerFilter() {
  filters.value.last_dts013_handlerKeywords = normalizeStringArray(
    draftLastDts013HandlerKeywords.value,
  );
  lastDts013HandlerFilterVisible.value = false;
  await handleSearch(true);
}

function resetLastDts013HandlerFilterDraft() {
  draftLastDts013HandlerKeywords.value = [];
}

async function confirmDevOwnerNameFilter() {
  filters.value.dev_owner_name_keyword = normalizeStringArray(
    draftDevOwnerNameKeywords.value,
  );
  devOwnerNameFilterVisible.value = false;
  await handleSearch(true);
}

function resetDevOwnerNameFilterDraft() {
  draftDevOwnerNameKeywords.value = [];
}

async function confirmTestOwnerNameFilter() {
  filters.value.test_owner_name_keyword = normalizeStringArray(
    draftTestOwnerNameKeywords.value,
  );
  testOwnerNameFilterVisible.value = false;
  await handleSearch(true);
}

function resetTestOwnerNameFilterDraft() {
  draftTestOwnerNameKeywords.value = [];
}

async function confirmCreateAtFilter() {
  const normalized = normalizeTimestampPair(
    draftCreateAtBegin.value ? toTimestampMs(draftCreateAtBegin.value) : 0,
    draftCreateAtEnd.value ? toTimestampMs(draftCreateAtEnd.value) : 0,
  );
  filters.value.createAtBegin = normalized.begin;
  filters.value.createAtEnd = normalized.end;
  createAtFilterVisible.value = false;
  await handleSearch(true);
}

function resetCreateAtFilterDraft() {
  draftCreateAtBegin.value = null;
  draftCreateAtEnd.value = null;
}

async function confirmCloseTimeFilter() {
  const normalized = normalizeTimestampPair(
    draftCloseTimeBegin.value ? toTimestampMs(draftCloseTimeBegin.value) : 0,
    draftCloseTimeEnd.value ? toTimestampMs(draftCloseTimeEnd.value) : 0,
  );
  filters.value.dCloseTimeBegin = normalized.begin;
  filters.value.dCloseTimeEnd = normalized.end;
  closeTimeFilterVisible.value = false;
  await handleSearch(true);
}

function resetCloseTimeFilterDraft() {
  draftCloseTimeBegin.value = null;
  draftCloseTimeEnd.value = null;
}

async function confirmCloseTypeFilter() {
  filters.value.uQbiCloseTypeNames = normalizeStringArray(
    draftCloseTypeNames.value,
  );
  closeTypeFilterVisible.value = false;
  await handleSearch(true);
}

function resetCloseTypeFilterDraft() {
  draftCloseTypeNames.value = [];
  draftCloseTypeKeyword.value = '';
}

async function confirmConfigFlowTypeFilter() {
  filters.value.sConfigFlowTypes = normalizeStringArray(
    draftConfigFlowTypes.value,
  );
  configFlowTypeFilterVisible.value = false;
  await handleSearch(true);
}

function resetConfigFlowTypeFilterDraft() {
  draftConfigFlowTypes.value = [];
  draftConfigFlowTypeKeyword.value = '';
}

async function confirmAutoSourceFilter() {
  filters.value.auto_source_types = normalizeStringArray(
    draftAutoSourceTypes.value,
  );
  autoSourceFilterVisible.value = false;
  await handleSearch(true);
}

function resetAutoSourceFilterDraft() {
  draftAutoSourceTypes.value = [];
  draftAutoSourceKeyword.value = '';
}

async function confirmDeptFilter() {
  filters.value.sDeptOneNoNames = normalizeStringArray(draftDeptNames.value);
  deptFilterVisible.value = false;
  await handleSearch(true);
}

function resetDeptFilterDraft() {
  draftDeptNames.value = [];
  draftDeptKeyword.value = '';
}

async function confirmSubsystemFilter() {
  filters.value.sSubsystemNoNames = normalizeStringArray(
    draftSubsystemNames.value,
  );
  subsystemFilterVisible.value = false;
  await handleSearch(true);
}

function resetSubsystemFilterDraft() {
  draftSubsystemNames.value = [];
  draftSubsystemKeyword.value = '';
}

async function confirmAutoPlGroupFilter() {
  filters.value.auto_pl_group_names = normalizeStringArray(
    draftAutoPlGroupNames.value,
  );
  autoPlGroupFilterVisible.value = false;
  await handleSearch(true);
}

function resetAutoPlGroupFilterDraft() {
  draftAutoPlGroupNames.value = [];
  draftAutoPlGroupKeyword.value = '';
}

function buildExportFilename() {
  const current = new Date();
  const pad = (value: number) => String(value).padStart(2, '0');
  return `DTS统计明细-${current.getFullYear()}${pad(current.getMonth() + 1)}${pad(current.getDate())}-${pad(current.getHours())}${pad(current.getMinutes())}${pad(current.getSeconds())}.xlsx`;
}

function triggerBlobDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(new Blob([blob]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.append(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

async function downloadExportTaskFile(task: DtsExportTask | null) {
  if (!task?.id) {
    throw new Error('missing export task id');
  }
  const blob = await downloadDtsExportTask(task.id);
  triggerBlobDownload(
    blob as Blob,
    String(task.file_name || '').trim() || buildExportFilename(),
  );
}

function startExportPreparePolling(taskId: string) {
  stopExportPreparePolling();
  exportPreparing.value = true;
  const pollingSerial = exportPollingSerial + 1;
  exportPollingSerial = pollingSerial;
  let polling = false;
  const startedAt = Date.now();

  exportPrepareTimer = window.setInterval(async () => {
    if (pollingSerial !== exportPollingSerial) {
      return;
    }
    if (polling) {
      return;
    }
    if (Date.now() - startedAt > pollMaxWaitMs) {
      stopExportPreparePolling();
      exportPreparing.value = false;
      exportPrepareTask.value = null;
      ElMessage.error('导出任务超时，请稍后重试');
      return;
    }
    polling = true;
    try {
      const task = await getDtsExportTask(taskId);
      if (pollingSerial !== exportPollingSerial) {
        return;
      }
      exportPrepareTask.value = task;
      if (task.status === 'success') {
        stopExportPreparePolling();
        exportPreparing.value = false;
        await downloadExportTaskFile(task);
        exportPrepareTask.value = null;
        ElMessage.success('导出成功');
        return;
      }
      if (task.status === 'failed') {
        stopExportPreparePolling();
        exportPreparing.value = false;
        exportPrepareTask.value = null;
        ElMessage.error(task.error_message || task.message || '导出任务失败');
      }
    } catch (error) {
      console.error(error);
      stopExportPreparePolling();
      exportPreparing.value = false;
      exportPrepareTask.value = null;
      ElMessage.error(resolveErrorMessage(error, '导出任务状态获取失败'));
    } finally {
      polling = false;
    }
  }, 1000);
}

async function handleExport() {
  if (!appliedFilters.value) {
    ElMessage.warning('请先查询明细数据');
    return;
  }
  if (dataResultCount.value <= 0) {
    ElMessage.warning('当前没有可导出的数据');
    return;
  }

  stopExportPreparePolling();
  exportPreparing.value = true;
  exportPrepareTask.value = null;
  try {
    const payload = cloneFilters(appliedFilters.value);
    const prepareResponse = await prepareDtsExport(payload);
    if (prepareResponse.mode === 'ready') {
      exportPreparing.value = false;
      exportPrepareTask.value = prepareResponse.task;
      await downloadExportTaskFile(prepareResponse.task);
      exportPrepareTask.value = null;
      ElMessage.success('导出成功');
      return;
    }

    exportPrepareTask.value = prepareResponse.task;
    if (!prepareResponse.task?.id) {
      exportPreparing.value = false;
      exportPrepareTask.value = null;
      ElMessage.error('导出任务创建失败');
      return;
    }
    startExportPreparePolling(prepareResponse.task.id);
  } catch (error) {
    console.error(error);
    exportPreparing.value = false;
    exportPrepareTask.value = null;
    ElMessage.error(
      resolveErrorMessage(error, '导出失败，请检查筛选条件后重试'),
    );
  }
}

async function refreshCurrentView() {
  await Promise.all([gridApi.reload(), fetchSummary(true)]);
  await nextTick();
  updateDataGridHeight();
}

function formatBatchFailedItems(response: DtsBatchSaveResponse) {
  return response.failedItems
    .map((item) => `${item.defectNo}: ${item.errorMessage || '保存失败'}`)
    .join('\n');
}

async function showBatchFailureDetails(
  response: DtsBatchSaveResponse,
  title: string,
) {
  if (response.failedItems.length <= 0) {
    return;
  }
  await ElMessageBox.alert(formatBatchFailedItems(response), title, {
    confirmButtonText: '知道了',
  });
}

function openBatchEdit() {
  if (selectedDtsCount.value <= 0) {
    ElMessage.warning('请先勾选要批量填报的 DTS');
    return;
  }
  batchEditVisible.value = true;
}

async function handleBatchSaved(response: DtsBatchSaveResponse) {
  const failedIds = normalizeStringArray(
    response.failedItems.map((item) => item.defectNo),
  );

  if (response.successCount > 0 && response.failedCount <= 0) {
    batchEditVisible.value = false;
    clearBatchSelection({ silent: true });
    await refreshCurrentView();
    ElMessage.success(`批量保存成功，已更新 ${response.successCount} 条 DTS`);
    return;
  }

  if (response.successCount > 0) {
    batchEditVisible.value = false;
    setSelectedDtsBizNos(failedIds);
    selectionFingerprint.value = buildFingerprint(appliedFilters.value);
    await refreshCurrentView();
    ElMessage.warning(
      `批量保存已完成，成功 ${response.successCount} 条，失败 ${response.failedCount} 条`,
    );
    await showBatchFailureDetails(response, '部分 DTS 保存失败');
    return;
  }

  setSelectedDtsBizNos(
    failedIds.length > 0 ? failedIds : selectedDtsBizNos.value,
  );
  selectionFingerprint.value = buildFingerprint(appliedFilters.value);
  ElMessage.error('批量保存失败，未成功更新任何 DTS');
  await showBatchFailureDetails(response, '批量保存失败');
}

async function handleSaved() {
  await refreshCurrentView();
}

function formatArrayCell(value: unknown) {
  const items = Array.isArray(value) ? value : [];
  const normalized = items
    .map((item) => String(item || '').trim())
    .filter(Boolean);
  return {
    text: normalized.join(', '),
    tooltip: normalized.join('\n'),
  };
}

function formatArrayTooltip(value: unknown) {
  return formatArrayCell(value).tooltip;
}

function takeFirstTwo(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.slice(0, 2).map((item) => String(item || '').trim());
}

type SummaryDistributionRow = {
  label: string;
  value: number;
};

type SummaryTrend = NonNullable<DtsSummary['update_trend']>;
type SummaryHeatmapMatrix = NonNullable<DtsSummary['pl_group_severity_matrix']>;
type SummaryPlGroupCompletionRow = DtsPlGroupCompletionItem;
type SummaryRankMode = 'handler' | 'pl_group' | 'project';
type SummaryTreemapMode = 'dev_sub_category' | 'test_miss_reason';

const SUMMARY_RANK_MODE_OPTIONS = ['PL领域', '项目', '处理人'];

const SUMMARY_TREEMAP_MODE_OPTIONS = ['开发问题小类', '漏测原因'];

const TREEMAP_PALETTE = [
  '#2563eb',
  '#16a34a',
  '#f59e0b',
  '#ef4444',
  '#06b6d4',
  '#8b5cf6',
  '#14b8a6',
  '#ec4899',
];

const trendChartRef = ref<EchartsUIType>();
const { renderEcharts: renderTrendChart } = useEcharts(trendChartRef);
const processDaysChartRef = ref<EchartsUIType>();
const { renderEcharts: renderProcessDaysChart } = useEcharts(processDaysChartRef);
const completionRadarChartRef = ref<EchartsUIType>();
const { renderEcharts: renderCompletionRadarChart } =
  useEcharts(completionRadarChartRef);
const severityChartRef = ref<EchartsUIType>();
const { renderEcharts: renderSeverityChart } = useEcharts(severityChartRef);
const statusChartRef = ref<EchartsUIType>();
const { renderEcharts: renderStatusChart } = useEcharts(statusChartRef);
const flowTypeChartRef = ref<EchartsUIType>();
const { renderEcharts: renderFlowTypeChart } = useEcharts(flowTypeChartRef);
const closeTypeChartRef = ref<EchartsUIType>();
const { renderEcharts: renderCloseTypeChart } = useEcharts(closeTypeChartRef);
const sourceChartRef = ref<EchartsUIType>();
const { renderEcharts: renderSourceChart } = useEcharts(sourceChartRef);
const plGroupChartRef = ref<EchartsUIType>();
const { renderEcharts: renderPlGroupChart } = useEcharts(plGroupChartRef);
const plGroupCompletionChartRef = ref<EchartsUIType>();
const { renderEcharts: renderPlGroupCompletionChart } = useEcharts(
  plGroupCompletionChartRef,
);
const actionStatusChartRef = ref<EchartsUIType>();
const { renderEcharts: renderActionStatusChart } =
  useEcharts(actionStatusChartRef);
const issueIntroStageChartRef = ref<EchartsUIType>();
const { renderEcharts: renderIssueIntroStageChart } =
  useEcharts(issueIntroStageChartRef);
const governanceTreemapChartRef = ref<EchartsUIType>();
const { renderEcharts: renderGovernanceTreemapChart } =
  useEcharts(governanceTreemapChartRef);
const organizationHeatmapChartRef = ref<EchartsUIType>();
const { renderEcharts: renderOrganizationHeatmapChart } =
  useEcharts(organizationHeatmapChartRef);
const organizationRankChartRef = ref<EchartsUIType>();
const { renderEcharts: renderOrganizationRankChart } =
  useEcharts(organizationRankChartRef);

const governanceTreemapMode = ref<SummaryTreemapMode>('dev_sub_category');
const organizationRankMode = ref<SummaryRankMode>('pl_group');

const organizationRankSegmentValue = computed<string>({
  get: () => {
    switch (organizationRankMode.value) {
      case 'handler':
        return '处理人';
      case 'pl_group':
        return 'PL领域';
      case 'project':
      default:
        return '项目';
    }
  },
  set: (value) => {
    switch (value) {
      case '处理人':
        organizationRankMode.value = 'handler';
        break;
      case 'PL领域':
        organizationRankMode.value = 'pl_group';
        break;
      case '项目':
      default:
        organizationRankMode.value = 'project';
        break;
    }
  },
});

const governanceTreemapSegmentValue = computed<string>({
  get: () =>
    governanceTreemapMode.value === 'test_miss_reason'
      ? '漏测原因'
      : '开发问题小类',
  set: (value) => {
    governanceTreemapMode.value =
      value === '漏测原因' ? 'test_miss_reason' : 'dev_sub_category';
  },
});

const dashboardReady = computed(
  () =>
    activeTab.value === 'dashboard' &&
    hasAppliedFilters.value &&
    summary.value.total_count > 0,
);

function resolveCssVar(name: string, fallback: string) {
  if (typeof window === 'undefined') {
    return fallback;
  }
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return value || fallback;
}

function getChartTheme() {
  return {
    primary: resolveCssVar('--el-color-primary', '#2563eb'),
    primaryLight: resolveCssVar('--el-color-primary-light-3', '#93c5fd'),
    primaryLighter: resolveCssVar('--el-color-primary-light-5', '#bfdbfe'),
    success: resolveCssVar('--el-color-success', '#16a34a'),
    successLight: resolveCssVar('--el-color-success-light-3', '#86efac'),
    warning: resolveCssVar('--el-color-warning', '#f59e0b'),
    warningLight: resolveCssVar('--el-color-warning-light-3', '#fcd34d'),
    danger: resolveCssVar('--el-color-danger', '#ef4444'),
    dangerLight: resolveCssVar('--el-color-danger-light-3', '#fca5a5'),
    info: resolveCssVar('--el-color-info', '#64748b'),
    text: '#475569',
    muted: '#94a3b8',
    border: '#e2e8f0',
    background: '#f8fafc',
  };
}

function createVerticalGradient(top: string, bottom: string) {
  return {
    type: 'linear',
    x: 0,
    y: 0,
    x2: 0,
    y2: 1,
    colorStops: [
      { offset: 0, color: top },
      { offset: 1, color: bottom },
    ],
  };
}

function normalizeChartRows(
  rows?: null | SummaryDistributionRow[],
): SummaryDistributionRow[] {
  return (rows || [])
    .map((item) => ({
      label: String(item?.label || '').trim(),
      value: Number(item?.value || 0),
    }))
    .filter((item) => item.label);
}

function normalizePlGroupCompletionRows(
  rows?: null | SummaryPlGroupCompletionRow[],
): SummaryPlGroupCompletionRow[] {
  return (rows || [])
    .map((item) => ({
      label: String(item?.label || '').trim(),
      filled_count: Number(item?.filled_count || 0),
      total_count: Number(item?.total_count || 0),
      filled_rate: Number(item?.filled_rate || 0),
    }))
    .filter((item) => item.label);
}

function formatShare(value: number, total: number) {
  if (!total) {
    return String(value);
  }
  const share = ((value / total) * 100).toFixed(1);
  return `${value} (${share}%)`;
}

function renderEmptyChart(
  render: (options: Record<string, any>) => void,
  title: string,
) {
  render({
    title: {
      text: title,
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
}

function renderTrendCombo(
  render: (options: Record<string, any>) => void,
  trend: SummaryTrend | null,
) {
  if (!trend || trend.labels.length === 0) {
    renderEmptyChart(render, '暂无更新时间趋势');
    return;
  }
  const theme = getChartTheme();
  const rotateLabel = trend.labels.some((label) => label.length > 10);
  render({
    color: [theme.primary, theme.success, theme.warning, theme.danger],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    legend: {
      top: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: theme.text, fontSize: 12 },
    },
    grid: {
      left: 16,
      right: 16,
      top: 48,
      bottom: trend.labels.length > 12 ? 56 : 24,
      containLabel: true,
    },
    dataZoom: trend.labels.length > 12
      ? [
          {
            type: 'slider',
            xAxisIndex: 0,
            bottom: 10,
            height: 10,
            start: 0,
            end: 100,
          },
          {
            type: 'inside',
            xAxisIndex: 0,
            start: 0,
            end: 100,
          },
        ]
      : [],
    xAxis: {
      type: 'category',
      data: trend.labels,
      axisLabel: {
        color: theme.muted,
        fontSize: 11,
        rotate: rotateLabel ? 20 : 0,
      },
      axisLine: { lineStyle: { color: theme.border } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: theme.muted, fontSize: 11 },
      axisLine: { lineStyle: { color: theme.border } },
      splitLine: { lineStyle: { color: theme.border } },
    },
    series: [
      {
        name: '总量',
        type: 'bar',
        barMaxWidth: 20,
        data: trend.total_values,
        itemStyle: {
          borderRadius: [8, 8, 0, 0],
          color: createVerticalGradient(theme.primaryLight, theme.primary),
        },
      },
      {
        name: '已关闭',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        data: trend.closed_values,
        lineStyle: { color: theme.success, width: 3 },
        itemStyle: { color: theme.success },
        areaStyle: { color: 'rgba(34, 197, 94, 0.08)' },
        z: 3,
      },
      {
        name: '严重问题',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        data: trend.major_values,
        lineStyle: { color: theme.warning, width: 3 },
        itemStyle: { color: theme.warning },
        areaStyle: { color: 'rgba(245, 158, 11, 0.08)' },
        z: 4,
      },
      {
        name: '关键问题',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        data: trend.critical_values,
        lineStyle: { color: theme.danger, width: 3, type: 'dashed' },
        itemStyle: { color: theme.danger },
        z: 5,
      },
    ],
  });
}

function renderCompletionRadar(
  render: (options: Record<string, any>) => void,
) {
  const theme = getChartTheme();
  const qaRate = Math.round((summary.value.qa_completion_rate || 0) * 100);
  const devRate = Math.round((summary.value.dev_completion_rate || 0) * 100);
  const testRate = Math.round((summary.value.test_completion_rate || 0) * 100);
  render({
    color: [theme.primary],
    tooltip: {
      trigger: 'item',
      formatter: () => [
        `QA：${qaRate}%`,
        `开发：${devRate}%`,
        `测试：${testRate}%`,
      ].join('<br/>'),
    },
    radar: {
      center: ['50%', '50%'],
      radius: '64%',
      splitNumber: 5,
      axisName: { color: theme.text, fontSize: 12 },
      splitLine: { lineStyle: { color: theme.border } },
      splitArea: {
        areaStyle: {
          color: ['rgba(248, 250, 252, 0.9)', 'rgba(255, 255, 255, 1)'],
        },
      },
      indicator: [
        { name: 'QA', max: 100 },
        { name: '开发', max: 100 },
        { name: '测试', max: 100 },
      ],
    },
    series: [
      {
        name: '填报完成度',
        type: 'radar',
        symbol: 'circle',
        symbolSize: 7,
        data: [
          {
            value: [qaRate, devRate, testRate],
            name: '完成率',
            areaStyle: { color: 'rgba(37, 99, 235, 0.18)' },
            lineStyle: { color: theme.primary, width: 3 },
            itemStyle: { color: theme.primary },
          },
        ],
      },
    ],
  });
}

function renderRosePie(
  render: (options: Record<string, any>) => void,
  rows: SummaryDistributionRow[],
  title: string,
) {
  const chartRows = normalizeChartRows(rows);
  if (chartRows.length === 0) {
    renderEmptyChart(render, `暂无${title}`);
    return;
  }
  const theme = getChartTheme();
  render({
    color: [
      theme.danger,
      theme.warning,
      theme.primary,
      theme.success,
      theme.info,
      theme.primaryLight,
      theme.successLight,
    ],
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const name = String(params?.name ?? '');
        const value = Number(params?.value ?? 0);
        const percent = Number(params?.percent ?? 0);
        return `${name}<br/>${value} (${percent.toFixed(1)}%)`;
      },
    },
    legend: {
      type: 'scroll',
      bottom: 0,
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      textStyle: { color: theme.text, fontSize: 11 },
    },
    series: [
      {
        type: 'pie',
        roseType: 'radius',
        radius: ['28%', '70%'],
        center: ['50%', '44%'],
        label: {
          show: true,
          color: theme.text,
          fontSize: 11,
          formatter: '{b}\n{c} ({d}%)',
        },
        labelLine: {
          length: 10,
          length2: 12,
        },
        itemStyle: {
          borderColor: '#fff',
          borderWidth: 2,
        },
        data: chartRows.map((item) => ({
          name: item.label,
          value: item.value,
        })),
      },
    ],
  });
}

function renderVerticalBar(
  render: (options: Record<string, any>) => void,
  rows: SummaryDistributionRow[],
  title: string,
  color: string,
) {
  const chartRows = normalizeChartRows(rows);
  if (chartRows.length === 0) {
    renderEmptyChart(render, `暂无${title}`);
    return;
  }
  const theme = getChartTheme();
  const total = chartRows.reduce((sum, item) => sum + item.value, 0);
  const rotateLabel = chartRows.some((item) => item.label.length > 6);
  render({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const first = Array.isArray(params) ? params[0] : params;
        const value = Number(first?.value ?? 0);
        const name = String(first?.axisValue ?? first?.name ?? '');
        return `${name}<br/>${formatShare(value, total)}`;
      },
    },
    grid: {
      left: 16,
      right: 16,
      top: 12,
      bottom: 20,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: chartRows.map((item) => item.label),
      axisLabel: {
        color: theme.muted,
        fontSize: 11,
        interval: 0,
        rotate: rotateLabel ? 20 : 0,
      },
      axisLine: { lineStyle: { color: theme.border } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: theme.muted, fontSize: 11 },
      axisLine: { lineStyle: { color: theme.border } },
      splitLine: { lineStyle: { color: theme.border } },
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 28,
        data: chartRows.map((item) => item.value),
        itemStyle: {
          borderRadius: [8, 8, 0, 0],
          color: createVerticalGradient(color, theme.primaryLight),
        },
        label: {
          show: true,
          position: 'top',
          color: theme.text,
          fontSize: 11,
          formatter: (params: any) => {
            const value = Number(params?.value ?? 0);
            return formatShare(value, total);
          },
        },
      },
    ],
  });
}

function renderRankBar(
  render: (options: Record<string, any>) => void,
  rows: SummaryDistributionRow[],
  title: string,
  color: string,
) {
  const chartRows = normalizeChartRows(rows).slice(0, 10);
  if (chartRows.length === 0) {
    renderEmptyChart(render, `暂无${title}`);
    return;
  }
  const theme = getChartTheme();
  const total = chartRows.reduce((sum, item) => sum + item.value, 0);
  render({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const first = Array.isArray(params) ? params[0] : params;
        const name = String(first?.axisValue ?? first?.name ?? '');
        const value = Number(first?.value ?? 0);
        return `${name}<br/>${formatShare(value, total)}`;
      },
    },
    grid: {
      left: 18,
      right: 18,
      top: 12,
      bottom: 16,
      containLabel: true,
    },
    xAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: theme.muted, fontSize: 11 },
      axisLine: { lineStyle: { color: theme.border } },
      splitLine: { lineStyle: { color: theme.border } },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: chartRows.map((item) => item.label),
      axisLabel: {
        color: theme.text,
        fontSize: 11,
        width: 120,
        overflow: 'truncate',
      },
      axisLine: { lineStyle: { color: theme.border } },
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 18,
        data: chartRows.map((item) => item.value),
        itemStyle: {
          borderRadius: [0, 8, 8, 0],
          color: createVerticalGradient(theme.primaryLight, color),
        },
        label: {
          show: true,
          position: 'right',
          color: theme.text,
          fontSize: 11,
          formatter: (params: any) => {
            const value = Number(params?.value ?? 0);
            return formatShare(value, total);
          },
        },
      },
    ],
  });
}

function renderPlGroupCompletionBar(
  render: (options: Record<string, any>) => void,
  rows?: null | SummaryPlGroupCompletionRow[],
  title: string,
) {
  const chartRows = normalizePlGroupCompletionRows(rows).sort((left, right) => {
    if (right.filled_rate !== left.filled_rate) {
      return right.filled_rate - left.filled_rate;
    }
    if (right.filled_count !== left.filled_count) {
      return right.filled_count - left.filled_count;
    }
    if (right.total_count !== left.total_count) {
      return right.total_count - left.total_count;
    }
    return left.label.localeCompare(right.label);
  });
  if (chartRows.length === 0) {
    renderEmptyChart(render, `暂无${title}`);
    return;
  }
  const theme = getChartTheme();
  const rotateLabel = chartRows.some((item) => item.label.length > 8);
  const rateValues = chartRows.map((item) =>
    Number((item.filled_rate * 100).toFixed(1)),
  );
  render({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const first = Array.isArray(params) ? params[0] : params;
        const row = chartRows[Number(first?.dataIndex ?? 0)];
        if (!row) {
          return '';
        }
        return `${row.label}<br/>已填报 ${row.filled_count} / ${row.total_count}<br/>完成率 ${(row.filled_rate * 100).toFixed(1)}%`;
      },
    },
    grid: {
      left: 16,
      right: 16,
      top: 16,
      bottom: chartRows.length > 12 ? 48 : 24,
      containLabel: true,
    },
    dataZoom:
      chartRows.length > 12
        ? [
            {
              type: 'slider',
              xAxisIndex: 0,
              bottom: 10,
              height: 10,
              start: 0,
              end: 100,
            },
            {
              type: 'inside',
              xAxisIndex: 0,
              start: 0,
              end: 100,
            },
          ]
        : [],
    xAxis: {
      type: 'category',
      data: chartRows.map((item) => item.label),
      axisLabel: {
        color: theme.muted,
        fontSize: 11,
        interval: 0,
        rotate: rotateLabel ? 20 : 0,
      },
      axisLine: { lineStyle: { color: theme.border } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      splitNumber: 5,
      axisLabel: {
        color: theme.muted,
        fontSize: 11,
        formatter: (value: number) => `${value}%`,
      },
      axisLine: { lineStyle: { color: theme.border } },
      splitLine: { lineStyle: { color: theme.border } },
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 28,
        data: rateValues,
        itemStyle: {
          borderRadius: [8, 8, 0, 0],
          color: createVerticalGradient(theme.successLight, theme.success),
        },
        label: {
          show: true,
          position: 'top',
          color: theme.text,
          fontSize: 11,
          formatter: (params: any) => {
            const value = Number(params?.value ?? 0);
            return `${value.toFixed(1)}%`;
          },
        },
      },
    ],
  });
}

function renderGroupedBar(
  render: (options: Record<string, any>) => void,
  leftRows: SummaryDistributionRow[],
  rightRows: SummaryDistributionRow[],
  leftLabel: string,
  rightLabel: string,
  leftColor: string,
  rightColor: string,
) {
  const theme = getChartTheme();
  const left = normalizeChartRows(leftRows);
  const right = normalizeChartRows(rightRows);
  const labels = Array.from(
    new Set([...left.map((item) => item.label), ...right.map((item) => item.label)]),
  ).sort((a, b) => {
    const leftTotal =
      (left.find((item) => item.label === b)?.value || 0) +
      (right.find((item) => item.label === b)?.value || 0);
    const rightTotal =
      (left.find((item) => item.label === a)?.value || 0) +
      (right.find((item) => item.label === a)?.value || 0);
    return rightTotal - leftTotal;
  });
  if (labels.length === 0) {
    renderEmptyChart(render, '暂无措施状态对比');
    return;
  }
  render({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    legend: {
      top: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: theme.text, fontSize: 12 },
    },
    grid: {
      left: 16,
      right: 16,
      top: 44,
      bottom: 16,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: {
        color: theme.muted,
        fontSize: 11,
        interval: 0,
        rotate: labels.some((label) => label.length > 6) ? 20 : 0,
      },
      axisLine: { lineStyle: { color: theme.border } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: theme.muted, fontSize: 11 },
      axisLine: { lineStyle: { color: theme.border } },
      splitLine: { lineStyle: { color: theme.border } },
    },
    series: [
      {
        name: leftLabel,
        type: 'bar',
        barMaxWidth: 18,
        data: labels.map(
          (label) => left.find((item) => item.label === label)?.value || 0,
        ),
        itemStyle: {
          borderRadius: [8, 8, 0, 0],
          color: createVerticalGradient(leftColor, theme.primaryLight),
        },
      },
      {
        name: rightLabel,
        type: 'bar',
        barMaxWidth: 18,
        data: labels.map(
          (label) => right.find((item) => item.label === label)?.value || 0,
        ),
        itemStyle: {
          borderRadius: [8, 8, 0, 0],
          color: createVerticalGradient(rightColor, theme.successLight),
        },
      },
    ],
  });
}

function renderHeatmap(
  render: (options: Record<string, any>) => void,
  matrix: SummaryHeatmapMatrix | null,
  title: string,
) {
  const safeMatrix = matrix;
  const columns = safeMatrix?.columns || [];
  const rows = safeMatrix?.rows || [];
  if (columns.length === 0 || rows.length === 0) {
    renderEmptyChart(render, `暂无${title}`);
    return;
  }
  const theme = getChartTheme();
  const data = rows.flatMap((row, rowIndex) =>
    columns.map((_column, columnIndex) => [
      columnIndex,
      rowIndex,
      Number(row.values[columnIndex] || 0),
    ]),
  );
  const maxValue = Math.max(...data.map((item) => Number(item[2] || 0)), 1);
  render({
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        const row = rows[Number(params?.data?.[1] ?? 0)];
        const column = columns[Number(params?.data?.[0] ?? 0)];
        const value = Number(params?.data?.[2] ?? 0);
        return `${row?.label || ''}<br/>${column || ''}：${value}`;
      },
    },
    grid: {
      left: 12,
      right: 12,
      top: 12,
      bottom: 28,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: columns,
      splitArea: { show: true },
      axisLabel: { color: theme.text, fontSize: 11 },
      axisLine: { lineStyle: { color: theme.border } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'category',
      data: rows.map((row) => row.label),
      splitArea: { show: true },
      axisLabel: {
        color: theme.text,
        fontSize: 11,
        width: 96,
        overflow: 'truncate',
      },
      axisLine: { lineStyle: { color: theme.border } },
      axisTick: { show: false },
    },
    visualMap: {
      min: 0,
      max: maxValue,
      calculable: false,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      textStyle: { color: theme.text },
      inRange: {
        color: [theme.primaryLighter, theme.primary],
      },
    },
    series: [
      {
        type: 'heatmap',
        data,
        label: {
          show: true,
          color: '#0f172a',
          fontSize: 11,
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(15, 23, 42, 0.2)',
          },
        },
      },
    ],
  });
}

function renderTreemap(
  render: (options: Record<string, any>) => void,
  rows: SummaryDistributionRow[],
  title: string,
) {
  const chartRows = normalizeChartRows(rows).slice(0, 12);
  if (chartRows.length === 0) {
    renderEmptyChart(render, `暂无${title}`);
    return;
  }
  render({
    color: TREEMAP_PALETTE,
    tooltip: {
      formatter: (params: any) => {
        const name = String(params?.name ?? '');
        const value = Number(params?.value ?? 0);
        return `${name}<br/>${value}`;
      },
    },
    series: [
      {
        type: 'treemap',
        data: chartRows.map((item, index) => ({
          name: item.label,
          value: item.value,
          itemStyle: {
            borderColor: '#fff',
            borderWidth: 2,
            borderRadius: 8,
            color: TREEMAP_PALETTE[index % TREEMAP_PALETTE.length],
          },
        })),
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        upperLabel: { show: false },
        label: {
          show: true,
          color: '#fff',
          fontSize: 11,
          fontWeight: 700,
          formatter: '{b}\n{c}',
          overflow: 'truncate',
        },
        itemStyle: {
          gapWidth: 2,
          borderWidth: 2,
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(15, 23, 42, 0.18)',
          },
        },
      },
    ],
  });
}

function watchDashboardChart(source: () => unknown, render: () => void) {
  watch(
    [dashboardReady, source] as const,
    ([ready]) => {
      if (!ready) {
        return;
      }
      render();
    },
    { deep: true, immediate: true },
  );
}

function getRankRows(mode: SummaryRankMode): SummaryDistributionRow[] {
  switch (mode) {
    case 'handler':
      return normalizeChartRows(summary.value.handler_dist);
    case 'pl_group':
      return normalizeChartRows(summary.value.auto_pl_group_dist);
    case 'project':
    default:
      return normalizeChartRows(summary.value.project_dist);
  }
}

function getTreemapRows(mode: SummaryTreemapMode): SummaryDistributionRow[] {
  switch (mode) {
    case 'test_miss_reason':
      return normalizeChartRows(summary.value.test_miss_reason_dist);
    case 'dev_sub_category':
    default:
      return normalizeChartRows(summary.value.dev_sub_category_dist);
  }
}

const organizationRankTitle = computed(() => {
  switch (organizationRankMode.value) {
    case 'handler':
      return '处理人 Top';
    case 'pl_group':
      return 'PL领域排名';
    case 'project':
    default:
      return '项目分布';
  }
});

const governanceTreemapTitle = computed(() => {
  switch (governanceTreemapMode.value) {
    case 'test_miss_reason':
      return '漏测原因 Top';
    case 'dev_sub_category':
    default:
      return '开发问题小类 Top';
  }
});

watchDashboardChart(
  () => summary.value.update_trend,
  () => renderTrendCombo(renderTrendChart, summary.value.update_trend),
);
watchDashboardChart(
  () => summary.value.process_days_bucket_dist,
  () =>
    renderVerticalBar(
      renderProcessDaysChart,
      summary.value.process_days_bucket_dist,
      '处理时长分布',
      getChartTheme().warning,
    ),
);
watchDashboardChart(
  () => [
    summary.value.qa_completion_rate,
    summary.value.dev_completion_rate,
    summary.value.test_completion_rate,
  ],
  () => renderCompletionRadar(renderCompletionRadarChart),
);
watchDashboardChart(
  () => summary.value.severity_dist,
  () =>
    renderRosePie(
      renderSeverityChart,
      summary.value.severity_dist,
      '严重程度分布',
    ),
);
watchDashboardChart(
  () => summary.value.status_dist,
  () =>
    renderVerticalBar(
      renderStatusChart,
      summary.value.status_dist,
      '状态分布',
      getChartTheme().primary,
    ),
);
watchDashboardChart(
  () => summary.value.flow_type_dist,
  () =>
    renderVerticalBar(
      renderFlowTypeChart,
      summary.value.flow_type_dist,
      '流程类型分布',
      getChartTheme().info,
    ),
);
watchDashboardChart(
  () => summary.value.close_type_dist,
  () =>
    renderVerticalBar(
      renderCloseTypeChart,
      summary.value.close_type_dist,
      '关闭类型分布',
      getChartTheme().warning,
    ),
);
watchDashboardChart(
  () => summary.value.source_dist,
  () =>
    renderRosePie(
      renderSourceChart,
      summary.value.source_dist,
      '提单来源分布',
    ),
);
watchDashboardChart(
  () => summary.value.auto_pl_group_dist,
  () =>
    renderRankBar(
      renderPlGroupChart,
      summary.value.auto_pl_group_dist,
      'PL领域排名',
      getChartTheme().success,
    ),
);
watchDashboardChart(
  () => summary.value.pl_group_dev_completion_dist,
  () =>
    renderPlGroupCompletionBar(
      renderPlGroupCompletionChart,
      summary.value.pl_group_dev_completion_dist,
      'PL 组开发填报完成率',
    ),
);
watchDashboardChart(
  () => [summary.value.dev_action_status_dist, summary.value.test_action_status_dist],
  () =>
    renderGroupedBar(
      renderActionStatusChart,
      summary.value.dev_action_status_dist,
      summary.value.test_action_status_dist,
      '开发',
      '测试',
      getChartTheme().primary,
      getChartTheme().success,
    ),
);
watchDashboardChart(
  () => summary.value.issue_intro_stage_dist,
  () =>
    renderVerticalBar(
      renderIssueIntroStageChart,
      summary.value.issue_intro_stage_dist,
      '问题引入阶段分布',
      getChartTheme().info,
    ),
);
watchDashboardChart(
  () => summary.value.pl_group_severity_matrix,
  () =>
    renderHeatmap(
      renderOrganizationHeatmapChart,
      summary.value.pl_group_severity_matrix,
      'PL领域 × 严重度热点',
    ),
);
watchDashboardChart(
  () => [
    organizationRankMode.value,
    summary.value.project_dist,
    summary.value.handler_dist,
    summary.value.auto_pl_group_dist,
  ],
  () =>
    renderRankBar(
      renderOrganizationRankChart,
      getRankRows(organizationRankMode.value),
      organizationRankTitle.value,
      getChartTheme().primary,
    ),
);
watchDashboardChart(
  () => [
    governanceTreemapMode.value,
    summary.value.dev_sub_category_dist,
    summary.value.test_miss_reason_dist,
  ],
  () =>
    renderTreemap(
      renderGovernanceTreemapChart,
      getTreemapRows(governanceTreemapMode.value),
      governanceTreemapTitle.value,
    ),
);

onMounted(() => {
  void loadDictOptions();
  void handleSearch(true);
  updateDataGridHeight();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (resizeTimer) {
    window.clearTimeout(resizeTimer);
  }
  if (autoReloadTimer) {
    window.clearTimeout(autoReloadTimer);
  }
  stopExportPreparePolling();
});
</script>

<template>
  <Page content-class="flex h-full min-h-0 flex-col" auto-content-height>
    <div class="dts-statistics-shell flex h-full min-h-0 flex-col gap-4">
      <ElTabs v-model="activeTab" class="dts-statistics-tabs flex flex-col">
        <ElTabPane label="数据明细" name="list">
          <ElCard shadow="never" class="dts-data-card">
            <template #header>
              <div class="dts-data-card__header">
                <div>
                  <div class="dts-data-card__title">DTS 明细表</div>
                  <div class="dts-data-card__desc">
                    筛选入口已集成到表头与标题栏；查询后明细表与统计看板复用同一组条件。
                  </div>
                </div>
                <div class="dts-data-card__actions">
                  <ElButton
                    type="primary"
                    :disabled="!canBatchEdit"
                    @click="openBatchEdit"
                  >
                    批量填报
                  </ElButton>
                  <ElButton
                    type="primary"
                    plain
                    :disabled="!canExport"
                    :loading="exportPreparing"
                    @click="handleExport"
                  >
                    导出当前查询结果
                  </ElButton>
                  <ElTag
                    class="dts-data-card__status"
                    :effect="hasAppliedFilters ? 'light' : 'plain'"
                    :type="hasAppliedFilters ? 'success' : 'info'"
                  >
                    {{
                      hasAppliedFilters
                        ? `已加载 ${dataResultCount} 条结果`
                        : '等待查询'
                    }}
                  </ElTag>
                  <ElTag
                    class="dts-data-card__status"
                    :effect="selectedDtsCount > 0 ? 'light' : 'plain'"
                    :type="selectedDtsCount > 0 ? 'warning' : 'info'"
                  >
                    {{
                      selectedDtsCount > 0
                        ? `已选 ${selectedDtsCount} 条`
                        : '未选择批量对象'
                    }}
                  </ElTag>
                  <ElTag
                    v-if="queryLoading"
                    class="dts-data-card__status"
                    type="warning"
                    effect="light"
                  >
                    {{ queryStatusText }}
                  </ElTag>
                  <ElTag
                    v-if="exportPreparing"
                    class="dts-data-card__status"
                    type="warning"
                    effect="light"
                  >
                    {{ exportPrepareStatusText }}
                  </ElTag>
                </div>
              </div>
            </template>

            <div class="dts-data-card__body">
              <div
                ref="dataGridWrapRef"
                class="dts-data-grid-wrap"
                :style="dataGridWrapStyle"
              >
                <Grid
                  class="dts-data-grid h-full min-h-0"
                  @selection-change="handleGridSelectionChange"
                >
                  <template #table-title>
                    <div class="dts-table-title">
                      <div class="dts-table-title__filters">
                        <div class="dts-table-title__field">
                          <span class="dts-table-title__label">产品线</span>
                          <ElSelect
                            v-model="filters.productId"
                            size="small"
                            class="dts-table-title__select"
                            placeholder="选择产品线"
                            :disabled="queryLoading || exportPreparing"
                          >
                            <ElOption
                              v-for="item in PRODUCT_OPTIONS"
                              :key="item.value"
                              :label="item.label"
                              :value="item.value"
                              :disabled="item.disabled"
                            />
                          </ElSelect>
                        </div>
                        <div class="dts-table-title__field">
                          <span class="dts-table-title__label">时间区间</span>
                          <ElDatePicker
                            v-model="dateRange"
                            type="datetimerange"
                            unlink-panels
                            size="small"
                            class="dts-table-title__date"
                            start-placeholder="开始时间"
                            end-placeholder="结束时间"
                            range-separator="-"
                            format="YYYY-MM-DD HH:mm:ss"
                            :disabled="queryLoading || exportPreparing"
                            :disabled-date="disableOutOfWindowDate"
                          />
                        </div>
                        <div class="dts-table-title__actions">
                          <ElButton
                            type="primary"
                            size="small"
                            :loading="queryLoading"
                            :disabled="exportPreparing"
                            @click="handleSearch(true)"
                          >
                            {{ queryLoading ? '查询中' : '立即刷新' }}
                          </ElButton>
                          <ElButton
                            size="small"
                            :disabled="queryLoading || exportPreparing"
                            @click="handleReset"
                          >
                            重置
                          </ElButton>
                        </div>
                      </div>
                      <div class="dts-table-title__meta">
                        <ElTag type="info" effect="plain">
                          当前产品：{{ selectedProductLabel }}
                        </ElTag>
                        <ElTag type="success" effect="plain">
                          状态：{{ selectedFlowStateLabel }}
                        </ElTag>
                        <ElTag type="warning" effect="plain">
                          严重程度：{{ selectedSeverityLabel }}
                        </ElTag>
                      </div>
                    </div>
                  </template>

                  <template #header-dtsStatusName>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">状态</span>
                      <ElPopover
                        v-model:visible="flowFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="280"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': filters.flowStates.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{
                                filters.flowStates.length > 0
                                  ? `${filters.flowStates.length} 项`
                                  : '全部'
                              }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElCheckboxGroup
                              v-model="draftFlowStates"
                              class="dts-header-filter-check-group"
                            >
                              <ElCheckbox
                                v-for="item in FLOW_STATE_OPTIONS"
                                :key="item.value"
                                :label="item.value"
                                :value="item.value"
                              >
                                {{ item.label }}
                              </ElCheckbox>
                            </ElCheckboxGroup>
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetFlowFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmFlowFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-serverityNoName>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">严重程度</span>
                      <ElPopover
                        v-model:visible="severityFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="240"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': filters.severityNos.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{
                                filters.severityNos.length > 0
                                  ? `${filters.severityNos.length} 项`
                                  : '全部'
                              }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElCheckboxGroup
                              v-model="draftSeverityNos"
                              class="dts-header-filter-check-group"
                            >
                              <ElCheckbox
                                v-for="item in SEVERITY_OPTIONS"
                                :key="item.value"
                                :label="item.value"
                                :value="item.value"
                              >
                                {{ item.label }}
                              </ElCheckbox>
                            </ElCheckboxGroup>
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetSeverityFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmSeverityFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #cell-serverityNoName="{ row }">
                    <ElTooltip
                      :content="resolveSeverityMeta(row.serverityNoName).tip"
                      placement="top"
                    >
                      <ElTag
                        :type="resolveSeverityMeta(row.serverityNoName).type"
                        effect="light"
                      >
                        {{ resolveSeverityMeta(row.serverityNoName).label }}
                      </ElTag>
                    </ElTooltip>
                  </template>

                  <template #cell-iNumOfCloseDays="{ row }">
                    {{ formatCycleIntegerDisplay(row.iNumOfCloseDays) }}
                  </template>

                  <template #cell-iNumOfFirmDays="{ row }">
                    {{ formatCycleIntegerDisplay(row.iNumOfFirmDays) }}
                  </template>

                  <template #cell-iNumOfLocateDays="{ row }">
                    {{ formatCycleIntegerDisplay(row.iNumOfLocateDays) }}
                  </template>

                  <template #cell-iNumofModifyDays="{ row }">
                    {{ formatCycleIntegerDisplay(row.iNumofModifyDays) }}
                  </template>

                  <template #cell-iNumofTestDays="{ row }">
                    {{ formatCycleIntegerDisplay(row.iNumofTestDays) }}
                  </template>

                  <template #header-dtsBizNo>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">问题单号</span>
                      <ElPopover
                        v-model:visible="dtsBizNoFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="280"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': Boolean(filters.dtsBizNoKeyword),
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedDtsBizNoKeywordLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-model="draftDtsBizNoKeyword"
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              placeholder="输入关键词模糊搜索问题单号"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetDtsBizNoFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmDtsBizNoFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-parentNo>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">父单单号</span>
                      <ElPopover
                        v-model:visible="parentNoFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="280"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': Boolean(filters.parentNoKeyword),
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedParentNoKeywordLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-model="draftParentNoKeyword"
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              placeholder="输入关键词模糊搜索父单单号"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetParentNoFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmParentNoFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-briefDesc>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">简要描述</span>
                      <ElPopover
                        v-model:visible="briefDescFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="280"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': Boolean(filters.briefDescKeyword),
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedBriefDescKeywordLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-model="draftBriefDescKeyword"
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              placeholder="输入关键词模糊搜索简要描述"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetBriefDescFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmBriefDescFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-iTestBackCount>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">测试返回次数</span>
                      <ElPopover
                        v-model:visible="iTestBackCountFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="300"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': Boolean(
                                filters.iTestBackCountKeyword,
                              ),
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedITestBackCountKeywordLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-model="draftITestBackCountKeyword"
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              placeholder="输入关键词模糊搜索测试返回次数"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetITestBackCountFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmITestBackCountFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-iNumOfCloseDays>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">关闭周期</span>
                      <ElPopover
                        v-model:visible="iNumOfCloseDaysFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="300"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': Boolean(
                                filters.iNumOfCloseDaysKeyword,
                              ),
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedINumOfCloseDaysKeywordLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-model="draftINumOfCloseDaysKeyword"
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              placeholder="输入关键词模糊搜索关闭周期"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetINumOfCloseDaysFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmINumOfCloseDaysFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-iNumOfFirmDays>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">确认周期</span>
                      <ElPopover
                        v-model:visible="iNumOfFirmDaysFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="300"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': Boolean(
                                filters.iNumOfFirmDaysKeyword,
                              ),
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedINumOfFirmDaysKeywordLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-model="draftINumOfFirmDaysKeyword"
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              placeholder="输入关键词模糊搜索确认周期"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetINumOfFirmDaysFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmINumOfFirmDaysFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-iNumOfLocateDays>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">定位周期</span>
                      <ElPopover
                        v-model:visible="iNumOfLocateDaysFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="300"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': Boolean(
                                filters.iNumOfLocateDaysKeyword,
                              ),
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedINumOfLocateDaysKeywordLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-model="draftINumOfLocateDaysKeyword"
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              placeholder="输入关键词模糊搜索定位周期"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetINumOfLocateDaysFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmINumOfLocateDaysFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-iNumofModifyDays>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">修改周期</span>
                      <ElPopover
                        v-model:visible="iNumofModifyDaysFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="300"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': Boolean(
                                filters.iNumofModifyDaysKeyword,
                              ),
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedINumofModifyDaysKeywordLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-model="draftINumofModifyDaysKeyword"
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              placeholder="输入关键词模糊搜索修改周期"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetINumofModifyDaysFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmINumofModifyDaysFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-iNumofTestDays>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">回归测试周期</span>
                      <ElPopover
                        v-model:visible="iNumofTestDaysFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="300"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': Boolean(
                                filters.iNumofTestDaysKeyword,
                              ),
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedINumofTestDaysKeywordLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-model="draftINumofTestDaysKeyword"
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              placeholder="输入关键词模糊搜索回归测试周期"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetINumofTestDaysFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmINumofTestDaysFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-projectName>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">项目</span>
                      <ElPopover
                        v-model:visible="projectFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="280"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': filters.projectNames.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedProjectLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-if="!fieldSetLoading.projectName"
                              v-model="draftProjectKeyword"
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              placeholder="输入关键词筛选项目"
                            />
                            <div
                              v-if="fieldSetLoading.projectName"
                              class="dts-header-filter-panel__tip"
                            >
                              正在加载候选值...
                            </div>
                            <ElEmpty
                              v-else-if="
                                fieldSetOptions.projectName.length === 0
                              "
                              :image-size="56"
                              description="暂无候选值"
                            />
                            <ElEmpty
                              v-else-if="filteredProjectOptions.length === 0"
                              :image-size="56"
                              description="暂无匹配项"
                            />
                            <ElCheckboxGroup
                              v-else
                              v-model="draftProjectNames"
                              class="dts-header-filter-check-group"
                            >
                              <ElCheckbox
                                v-for="item in filteredProjectOptions"
                                :key="item"
                                :label="item"
                                :value="item"
                              >
                                {{ item }}
                              </ElCheckbox>
                            </ElCheckboxGroup>
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetProjectFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmProjectFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-currentHandler>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">当前处理人</span>
                      <ElPopover
                        v-model:visible="currentHandlerFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="620"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active':
                                filters.currentHandlerKeywords.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedCurrentHandlerLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <DtsHeaderPersonSelector
                              v-model="draftCurrentHandlerKeywords"
                              :visible="currentHandlerFilterVisible"
                              value-mode="username"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetCurrentHandlerFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmCurrentHandlerFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-creator>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">提单人工号</span>
                      <ElPopover
                        v-model:visible="creatorFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="620"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': filters.creatorKeywords.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedCreatorLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <DtsHeaderPersonSelector
                              v-model="draftCreatorKeywords"
                              :visible="creatorFilterVisible"
                              value-mode="username"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetCreatorFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmCreatorFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-sSubmitUserName>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">提单人姓名</span>
                      <ElPopover
                        v-model:visible="submitUserNameFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="620"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active':
                                filters.sSubmitUserNameKeywords.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedSubmitUserNameLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <DtsHeaderPersonSelector
                              v-model="draftSubmitUserNameKeywords"
                              :visible="submitUserNameFilterVisible"
                              value-mode="name"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetSubmitUserNameFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmSubmitUserNameFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-createAt>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">提单时间</span>
                      <ElPopover
                        v-model:visible="createAtFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="360"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': hasTimeRange(
                                filters.createAtBegin,
                                filters.createAtEnd,
                              ),
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedCreateAtLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <div class="dts-header-filter-panel__time-stack">
                              <div class="dts-header-filter-panel__time-field">
                                <div
                                  class="dts-header-filter-panel__time-label"
                                >
                                  开始时间
                                </div>
                                <ElDatePicker
                                  v-model="draftCreateAtBegin"
                                  type="datetime"
                                  size="small"
                                  clearable
                                  :teleported="false"
                                  class="dts-header-filter-panel__date"
                                  placeholder="选择开始时间"
                                  format="YYYY-MM-DD HH:mm:ss"
                                />
                              </div>
                              <div class="dts-header-filter-panel__time-field">
                                <div
                                  class="dts-header-filter-panel__time-label"
                                >
                                  结束时间
                                </div>
                                <ElDatePicker
                                  v-model="draftCreateAtEnd"
                                  type="datetime"
                                  size="small"
                                  clearable
                                  :teleported="false"
                                  class="dts-header-filter-panel__date"
                                  placeholder="选择结束时间"
                                  format="YYYY-MM-DD HH:mm:ss"
                                />
                              </div>
                            </div>
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetCreateAtFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmCreateAtFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-dCloseTime>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">关闭时间</span>
                      <ElPopover
                        v-model:visible="closeTimeFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="360"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': hasTimeRange(
                                filters.dCloseTimeBegin,
                                filters.dCloseTimeEnd,
                              ),
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedCloseTimeLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <div class="dts-header-filter-panel__time-stack">
                              <div class="dts-header-filter-panel__time-field">
                                <div
                                  class="dts-header-filter-panel__time-label"
                                >
                                  开始时间
                                </div>
                                <ElDatePicker
                                  v-model="draftCloseTimeBegin"
                                  type="datetime"
                                  size="small"
                                  clearable
                                  :teleported="false"
                                  class="dts-header-filter-panel__date"
                                  placeholder="选择开始时间"
                                  format="YYYY-MM-DD HH:mm:ss"
                                />
                              </div>
                              <div class="dts-header-filter-panel__time-field">
                                <div
                                  class="dts-header-filter-panel__time-label"
                                >
                                  结束时间
                                </div>
                                <ElDatePicker
                                  v-model="draftCloseTimeEnd"
                                  type="datetime"
                                  size="small"
                                  clearable
                                  :teleported="false"
                                  class="dts-header-filter-panel__date"
                                  placeholder="选择结束时间"
                                  format="YYYY-MM-DD HH:mm:ss"
                                />
                              </div>
                            </div>
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetCloseTimeFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmCloseTimeFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-uQbiCloseTypeName>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">关闭类型</span>
                      <ElPopover
                        v-model:visible="closeTypeFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="260"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active':
                                filters.uQbiCloseTypeNames.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedCloseTypeLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-if="!fieldSetLoading.uQbiCloseTypeName"
                              v-model="draftCloseTypeKeyword"
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              placeholder="输入关键词筛选关闭类型"
                            />
                            <div
                              v-if="fieldSetLoading.uQbiCloseTypeName"
                              class="dts-header-filter-panel__tip"
                            >
                              正在加载候选值...
                            </div>
                            <ElEmpty
                              v-else-if="
                                fieldSetOptions.uQbiCloseTypeName.length === 0
                              "
                              :image-size="56"
                              description="暂无候选值"
                            />
                            <ElEmpty
                              v-else-if="filteredCloseTypeOptions.length === 0"
                              :image-size="56"
                              description="暂无匹配项"
                            />
                            <ElCheckboxGroup
                              v-else
                              v-model="draftCloseTypeNames"
                              class="dts-header-filter-check-group"
                            >
                              <ElCheckbox
                                v-for="item in filteredCloseTypeOptions"
                                :key="item"
                                :label="item"
                                :value="item"
                              >
                                {{ item }}
                              </ElCheckbox>
                            </ElCheckboxGroup>
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetCloseTypeFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmCloseTypeFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-sConfigFlowType>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">流程类型</span>
                      <ElPopover
                        v-model:visible="configFlowTypeFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="260"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': filters.sConfigFlowTypes.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedConfigFlowTypeLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-if="!fieldSetLoading.sConfigFlowType"
                              v-model="draftConfigFlowTypeKeyword"
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              placeholder="输入关键词筛选流程类型"
                            />
                            <div
                              v-if="fieldSetLoading.sConfigFlowType"
                              class="dts-header-filter-panel__tip"
                            >
                              正在加载候选值...
                            </div>
                            <ElEmpty
                              v-else-if="
                                fieldSetOptions.sConfigFlowType.length === 0
                              "
                              :image-size="56"
                              description="暂无候选值"
                            />
                            <ElEmpty
                              v-else-if="
                                filteredConfigFlowTypeOptions.length === 0
                              "
                              :image-size="56"
                              description="暂无匹配项"
                            />
                            <ElCheckboxGroup
                              v-else
                              v-model="draftConfigFlowTypes"
                              class="dts-header-filter-check-group"
                            >
                              <ElCheckbox
                                v-for="item in filteredConfigFlowTypeOptions"
                                :key="item"
                                :label="item"
                                :value="item"
                              >
                                {{ item }}
                              </ElCheckbox>
                            </ElCheckboxGroup>
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetConfigFlowTypeFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmConfigFlowTypeFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-auto_source_type>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">提单来源</span>
                      <ElPopover
                        v-model:visible="autoSourceFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="260"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': filters.auto_source_types.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedAutoSourceLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-if="!fieldSetLoading.auto_source_type"
                              v-model="draftAutoSourceKeyword"
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              placeholder="输入关键词筛选提单来源"
                            />
                            <div
                              v-if="fieldSetLoading.auto_source_type"
                              class="dts-header-filter-panel__tip"
                            >
                              正在加载候选值...
                            </div>
                            <ElEmpty
                              v-else-if="
                                fieldSetOptions.auto_source_type.length === 0
                              "
                              :image-size="56"
                              description="暂无候选值"
                            />
                            <ElEmpty
                              v-else-if="filteredAutoSourceOptions.length === 0"
                              :image-size="56"
                              description="暂无匹配项"
                            />
                            <ElCheckboxGroup
                              v-else
                              v-model="draftAutoSourceTypes"
                              class="dts-header-filter-check-group"
                            >
                              <ElCheckbox
                                v-for="item in filteredAutoSourceOptions"
                                :key="item"
                                :label="item"
                                :value="item"
                              >
                                {{ item }}
                              </ElCheckbox>
                            </ElCheckboxGroup>
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetAutoSourceFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmAutoSourceFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-sDeptOneNoName>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">提出方部门</span>
                      <ElPopover
                        v-model:visible="deptFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="260"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': filters.sDeptOneNoNames.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedDeptLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-if="!fieldSetLoading.sDeptOneNoName"
                              v-model="draftDeptKeyword"
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              placeholder="输入关键词筛选部门"
                            />
                            <div
                              v-if="fieldSetLoading.sDeptOneNoName"
                              class="dts-header-filter-panel__tip"
                            >
                              正在加载候选值...
                            </div>
                            <ElEmpty
                              v-else-if="
                                fieldSetOptions.sDeptOneNoName.length === 0
                              "
                              :image-size="56"
                              description="暂无候选值"
                            />
                            <ElEmpty
                              v-else-if="filteredDeptOptions.length === 0"
                              :image-size="56"
                              description="暂无匹配项"
                            />
                            <ElCheckboxGroup
                              v-else
                              v-model="draftDeptNames"
                              class="dts-header-filter-check-group"
                            >
                              <ElCheckbox
                                v-for="item in filteredDeptOptions"
                                :key="item"
                                :label="item"
                                :value="item"
                              >
                                {{ item }}
                              </ElCheckbox>
                            </ElCheckboxGroup>
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetDeptFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmDeptFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-sSubsystemNoName>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">子系统</span>
                      <ElPopover
                        v-model:visible="subsystemFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="260"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': filters.sSubsystemNoNames.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedSubsystemLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-if="!fieldSetLoading.sSubsystemNoName"
                              v-model="draftSubsystemKeyword"
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              placeholder="输入关键词筛选子系统"
                            />
                            <div
                              v-if="fieldSetLoading.sSubsystemNoName"
                              class="dts-header-filter-panel__tip"
                            >
                              正在加载候选值...
                            </div>
                            <ElEmpty
                              v-else-if="
                                fieldSetOptions.sSubsystemNoName.length === 0
                              "
                              :image-size="56"
                              description="暂无候选值"
                            />
                            <ElEmpty
                              v-else-if="filteredSubsystemOptions.length === 0"
                              :image-size="56"
                              description="暂无匹配项"
                            />
                            <ElCheckboxGroup
                              v-else
                              v-model="draftSubsystemNames"
                              class="dts-header-filter-check-group"
                            >
                              <ElCheckbox
                                v-for="item in filteredSubsystemOptions"
                                :key="item"
                                :label="item"
                                :value="item"
                              >
                                {{ item }}
                              </ElCheckbox>
                            </ElCheckboxGroup>
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetSubsystemFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmSubsystemFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-auto_pl_group_name>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">自动责任PL组</span>
                      <ElPopover
                        v-model:visible="autoPlGroupFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="260"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active':
                                filters.auto_pl_group_names.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedAutoPlGroupLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-if="!fieldSetLoading.auto_pl_group_name"
                              v-model="draftAutoPlGroupKeyword"
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              placeholder="输入关键词筛选自动责任PL组"
                            />
                            <div
                              v-if="fieldSetLoading.auto_pl_group_name"
                              class="dts-header-filter-panel__tip"
                            >
                              正在加载候选值...
                            </div>
                            <ElEmpty
                              v-else-if="
                                fieldSetOptions.auto_pl_group_name.length === 0
                              "
                              :image-size="56"
                              description="暂无候选值"
                            />
                            <ElEmpty
                              v-else-if="
                                filteredAutoPlGroupOptions.length === 0
                              "
                              :image-size="56"
                              description="暂无匹配项"
                            />
                            <ElCheckboxGroup
                              v-else
                              v-model="draftAutoPlGroupNames"
                              class="dts-header-filter-check-group"
                            >
                              <ElCheckbox
                                v-for="item in filteredAutoPlGroupOptions"
                                :key="item"
                                :label="item"
                                :value="item"
                              >
                                {{ item }}
                              </ElCheckbox>
                            </ElCheckboxGroup>
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetAutoPlGroupFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmAutoPlGroupFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-last_dts009_handler>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">
                        最后开发修改人
                      </span>
                      <ElPopover
                        v-model:visible="lastDts009HandlerFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="620"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active':
                                filters.last_dts009_handlerKeywords.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedLastDts009HandlerLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <DtsHeaderPersonSelector
                              v-model="draftLastDts009HandlerKeywords"
                              :visible="lastDts009HandlerFilterVisible"
                              value-mode="username"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetLastDts009HandlerFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmLastDts009HandlerFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-last_dts010_handler>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">
                        最后审核修改人
                      </span>
                      <ElPopover
                        v-model:visible="lastDts010HandlerFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="620"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active':
                                filters.last_dts010_handlerKeywords.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedLastDts010HandlerLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <DtsHeaderPersonSelector
                              v-model="draftLastDts010HandlerKeywords"
                              :visible="lastDts010HandlerFilterVisible"
                              value-mode="username"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetLastDts010HandlerFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmLastDts010HandlerFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-last_dts013_handler>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">
                        最后测试回归人
                      </span>
                      <ElPopover
                        v-model:visible="lastDts013HandlerFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="620"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active':
                                filters.last_dts013_handlerKeywords.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedLastDts013HandlerLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <DtsHeaderPersonSelector
                              v-model="draftLastDts013HandlerKeywords"
                              :visible="lastDts013HandlerFilterVisible"
                              value-mode="username"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetLastDts013HandlerFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmLastDts013HandlerFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-dev_owner_name>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">开发责任人</span>
                      <ElPopover
                        v-model:visible="devOwnerNameFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="620"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active':
                                filters.dev_owner_name_keyword.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedDevOwnerNameLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <DtsHeaderPersonSelector
                              v-model="draftDevOwnerNameKeywords"
                              :visible="devOwnerNameFilterVisible"
                              value-mode="name"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetDevOwnerNameFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmDevOwnerNameFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #header-test_owner_name>
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">测试责任人</span>
                      <ElPopover
                        v-model:visible="testOwnerNameFilterVisible"
                        placement="bottom-start"
                        trigger="click"
                        :width="620"
                        popper-class="dts-header-filter-popper"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active':
                                filters.test_owner_name_keyword.length > 0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{ selectedTestOwnerNameLabel }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <DtsHeaderPersonSelector
                              v-model="draftTestOwnerNameKeywords"
                              :visible="testOwnerNameFilterVisible"
                              value-mode="name"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetTestOwnerNameFilterDraft"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmTestOwnerNameFilter"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template
                    v-for="config in GOVERNANCE_SELECT_FILTER_CONFIGS"
                    :key="`header-${config.columnKey}`"
                    #[`header-${config.columnKey}`]
                  >
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">
                        {{ config.label }}
                      </span>
                      <ElPopover
                        v-model:visible="
                          governanceSelectVisible[config.columnKey]
                        "
                        placement="bottom-start"
                        trigger="click"
                        :width="280"
                        popper-class="dts-header-filter-popper"
                        @show="handleGovernanceSelectPopoverShow(config)"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active':
                                getFilterArrayValue(config.filterKey).length >
                                0,
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{
                                buildMultiFilterLabel(
                                  getFilterArrayValue(config.filterKey),
                                )
                              }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-model="
                                governanceSelectKeyword[config.columnKey]
                              "
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              :placeholder="config.placeholder"
                            />
                            <ElEmpty
                              v-if="
                                getGovernanceSelectOptions(config).length === 0
                              "
                              :image-size="56"
                              description="暂无候选值"
                            />
                            <ElCheckboxGroup
                              v-else
                              v-model="governanceSelectDraft[config.columnKey]"
                              class="dts-header-filter-check-group"
                            >
                              <ElCheckbox
                                v-for="item in getGovernanceSelectOptions(
                                  config,
                                )"
                                :key="item"
                                :label="item"
                                :value="item"
                              >
                                {{ item }}
                              </ElCheckbox>
                            </ElCheckboxGroup>
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetGovernanceSelectFilterDraft(config)"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmGovernanceSelectFilter(config)"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template
                    v-for="config in GOVERNANCE_KEYWORD_FILTER_CONFIGS"
                    :key="`header-${config.columnKey}`"
                    #[`header-${config.columnKey}`]
                  >
                    <div class="dts-header-filter" @click.stop>
                      <span class="dts-header-filter__label">
                        {{ config.label }}
                      </span>
                      <ElPopover
                        v-model:visible="
                          governanceKeywordVisible[config.columnKey]
                        "
                        placement="bottom-start"
                        trigger="click"
                        :width="300"
                        popper-class="dts-header-filter-popper"
                        @show="handleGovernanceKeywordPopoverShow(config)"
                      >
                        <template #reference>
                          <button
                            type="button"
                            class="dts-header-filter-trigger"
                            :class="{
                              'is-active': Boolean(
                                getFilterKeywordValue(config.filterKey),
                              ),
                            }"
                          >
                            <Filter class="dts-header-filter-trigger__icon" />
                            <span class="dts-header-filter-trigger__text">
                              {{
                                buildKeywordFilterButtonText(
                                  getFilterKeywordValue(config.filterKey),
                                )
                              }}
                            </span>
                          </button>
                        </template>
                        <div class="dts-header-filter-panel" @click.stop>
                          <div class="dts-header-filter-panel__body">
                            <ElInput
                              v-model="governanceKeywordDraft[config.columnKey]"
                              size="small"
                              clearable
                              class="dts-header-filter-panel__search"
                              :placeholder="config.placeholder"
                            />
                          </div>
                          <div class="dts-header-filter-panel__actions">
                            <ElButton
                              size="small"
                              @click="resetGovernanceKeywordFilterDraft(config)"
                            >
                              重置
                            </ElButton>
                            <ElButton
                              type="primary"
                              size="small"
                              @click="confirmGovernanceKeywordFilter(config)"
                            >
                              确认
                            </ElButton>
                          </div>
                        </div>
                      </ElPopover>
                    </div>
                  </template>

                  <template #cell-projectName="{ row }">
                    <div class="dts-project-cell">
                      <span>{{ formatProjectDisplay(row) }}</span>
                      <span
                        v-if="!row.projectName && row.sProdCName"
                        class="dts-project-cell__hint"
                      >
                        未匹配项目
                      </span>
                    </div>
                  </template>

                  <template #cell-is_downstream="{ row }">
                    <span v-if="!row.is_downstream" class="text-slate-400">
                      -
                    </span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag('is_downstream', row.is_downstream)
                          ?.type || 'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag('is_downstream', row.is_downstream)
                          ?.label || row.is_downstream
                      }}
                    </ElTag>
                  </template>

                  <template #cell-process_quality_type="{ row }">
                    <span
                      v-if="!row.process_quality_type"
                      class="text-slate-400"
                    >
                      -
                    </span>
                    <ElTooltip
                      v-else
                      :content="row.process_quality_type"
                      placement="top-start"
                    >
                      <span class="cursor-help">{{
                        row.process_quality_type
                      }}</span>
                    </ElTooltip>
                  </template>

                  <template #cell-issue_intro_stage="{ row }">
                    <span v-if="!row.issue_intro_stage" class="text-slate-400">
                      -
                    </span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag(
                          'issue_intro_stage',
                          row.issue_intro_stage,
                        )?.type || 'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag(
                          'issue_intro_stage',
                          row.issue_intro_stage,
                        )?.label || row.issue_intro_stage
                      }}
                    </ElTag>
                  </template>

                  <template #cell-need_aar="{ row }">
                    <span v-if="!row.need_aar" class="text-slate-400">-</span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag('need_aar', row.need_aar)?.type || 'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag('need_aar', row.need_aar)?.label ||
                        row.need_aar
                      }}
                    </ElTag>
                  </template>

                  <template #cell-need_dev_analyze="{ row }">
                    <span v-if="!row.need_dev_analyze" class="text-slate-400">
                      -
                    </span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag('need_dev_analyze', row.need_dev_analyze)
                          ?.type || 'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag('need_dev_analyze', row.need_dev_analyze)
                          ?.label || row.need_dev_analyze
                      }}
                    </ElTag>
                  </template>

                  <template #cell-need_test_analyze="{ row }">
                    <span v-if="!row.need_test_analyze" class="text-slate-400">
                      -
                    </span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag(
                          'need_test_analyze',
                          row.need_test_analyze,
                        )?.type || 'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag(
                          'need_test_analyze',
                          row.need_test_analyze,
                        )?.label || row.need_test_analyze
                      }}
                    </ElTag>
                  </template>

                  <template #cell-dev_status="{ row }">
                    <span v-if="!row.dev_status" class="text-slate-400">-</span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag('dev_status', row.dev_status)?.type ||
                        'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag('dev_status', row.dev_status)?.label ||
                        row.dev_status
                      }}
                    </ElTag>
                  </template>

                  <template #cell-dev_common_issue_type="{ row }">
                    <span
                      v-if="!row.dev_common_issue_type"
                      class="text-slate-400"
                    >
                      -
                    </span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag(
                          'dev_common_issue_type',
                          row.dev_common_issue_type,
                        )?.type || 'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag(
                          'dev_common_issue_type',
                          row.dev_common_issue_type,
                        )?.label || row.dev_common_issue_type
                      }}
                    </ElTag>
                  </template>

                  <template #cell-is_base_soft_issue="{ row }">
                    <span v-if="!row.is_base_soft_issue" class="text-slate-400">
                      -
                    </span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag(
                          'is_base_soft_issue',
                          row.is_base_soft_issue,
                        )?.type || 'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag(
                          'is_base_soft_issue',
                          row.is_base_soft_issue,
                        )?.label || row.is_base_soft_issue
                      }}
                    </ElTag>
                  </template>

                  <template #cell-is_duplicate_issue="{ row }">
                    <span v-if="!row.is_duplicate_issue" class="text-slate-400">
                      -
                    </span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag(
                          'is_duplicate_issue',
                          row.is_duplicate_issue,
                        )?.type || 'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag(
                          'is_duplicate_issue',
                          row.is_duplicate_issue,
                        )?.label || row.is_duplicate_issue
                      }}
                    </ElTag>
                  </template>

                  <template #cell-duplicate_issue_no="{ row }">
                    <span v-if="!row.duplicate_issue_no" class="text-slate-400">
                      -
                    </span>
                    <ElTooltip
                      v-else
                      :content="row.duplicate_issue_no"
                      placement="top-start"
                    >
                      <span class="cursor-help">{{
                        row.duplicate_issue_no
                      }}</span>
                    </ElTooltip>
                  </template>

                  <template #cell-test_status="{ row }">
                    <span v-if="!row.test_status" class="text-slate-400">
                      -
                    </span>
                    <ElTag
                      v-else
                      :type="
                        resolveGovTag('test_status', row.test_status)?.type ||
                        'info'
                      "
                      effect="light"
                      size="small"
                    >
                      {{
                        resolveGovTag('test_status', row.test_status)?.label ||
                        row.test_status
                      }}
                    </ElTag>
                  </template>

                  <template #cell-dev_sub_category="{ row }">
                    <span
                      v-if="(row.dev_sub_category || []).length === 0"
                      class="text-slate-400"
                    >
                      -
                    </span>
                    <div v-else class="dts-cell-tags">
                      <template
                        v-for="item in (row.dev_sub_category || []).slice(0, 2)"
                        :key="item"
                      >
                        <ElTag
                          :type="
                            resolveGovTag('dev_sub_category', item)?.type ||
                            'info'
                          "
                          effect="light"
                          size="small"
                        >
                          {{
                            resolveGovTag('dev_sub_category', item)?.label ||
                            item
                          }}
                        </ElTag>
                      </template>

                      <ElTooltip
                        v-if="(row.dev_sub_category || []).length > 2"
                        :content="formatArrayCell(row.dev_sub_category).tooltip"
                        placement="top-start"
                      >
                        <ElTag type="info" effect="plain" size="small">
                          +{{ (row.dev_sub_category || []).length - 2 }}
                        </ElTag>
                      </ElTooltip>
                    </div>
                  </template>

                  <template #cell-dev_improvements="{ row }">
                    <span
                      v-if="(row.dev_improvements || []).length === 0"
                      class="text-slate-400"
                    >
                      -
                    </span>
                    <ElTooltip
                      v-else
                      :content="formatArrayCell(row.dev_improvements).tooltip"
                      placement="top-start"
                    >
                      <span class="cursor-help">
                        {{ formatArrayCell(row.dev_improvements).text }}
                      </span>
                    </ElTooltip>
                  </template>

                  <template #cell-dev_non_base_desc="{ row }">
                    <span
                      v-if="(row.dev_non_base_desc || []).length === 0"
                      class="text-slate-400"
                    >
                      -
                    </span>
                    <div v-else class="dts-cell-tags">
                      <template
                        v-for="item in takeFirstTwo(row.dev_non_base_desc)"
                        :key="item"
                      >
                        <ElTag
                          :type="
                            resolveGovTag('dev_non_base_desc', item)?.type ||
                            'info'
                          "
                          effect="light"
                          size="small"
                        >
                          {{
                            resolveGovTag('dev_non_base_desc', item)?.label ||
                            item
                          }}
                        </ElTag>
                      </template>

                      <ElTooltip
                        v-if="(row.dev_non_base_desc || []).length > 2"
                        :content="formatArrayTooltip(row.dev_non_base_desc)"
                        placement="top-start"
                      >
                        <ElTag type="info" effect="plain" size="small">
                          +{{ (row.dev_non_base_desc || []).length - 2 }}
                        </ElTag>
                      </ElTooltip>
                    </div>
                  </template>

                  <template #cell-dev_asset_type="{ row }">
                    <span
                      v-if="(row.dev_asset_type || []).length === 0"
                      class="text-slate-400"
                    >
                      -
                    </span>
                    <div v-else class="dts-cell-tags">
                      <template
                        v-for="item in resolveGovTagList(
                          'dev_asset_type',
                          row.dev_asset_type,
                        ).slice(0, 2)"
                        :key="item.label"
                      >
                        <ElTag :type="item.type" effect="light" size="small">
                          {{ item.label }}
                        </ElTag>
                      </template>

                      <ElTooltip
                        v-if="(row.dev_asset_type || []).length > 2"
                        :content="formatArrayTooltip(row.dev_asset_type)"
                        placement="top-start"
                      >
                        <ElTag type="info" effect="plain" size="small">
                          +{{ (row.dev_asset_type || []).length - 2 }}
                        </ElTag>
                      </ElTooltip>
                    </div>
                  </template>

                  <template #cell-dev_control_points="{ row }">
                    <span
                      v-if="(row.dev_control_points || []).length === 0"
                      class="text-slate-400"
                    >
                      -
                    </span>
                    <div v-else class="dts-cell-tags">
                      <template
                        v-for="item in takeFirstTwo(row.dev_control_points)"
                        :key="item"
                      >
                        <ElTag
                          :type="
                            resolveGovTag('dev_control_points', item)?.type ||
                            'info'
                          "
                          effect="light"
                          size="small"
                        >
                          {{
                            resolveGovTag('dev_control_points', item)?.label ||
                            item
                          }}
                        </ElTag>
                      </template>

                      <ElTooltip
                        v-if="(row.dev_control_points || []).length > 2"
                        :content="formatArrayTooltip(row.dev_control_points)"
                        placement="top-start"
                      >
                        <ElTag type="info" effect="plain" size="small">
                          +{{ (row.dev_control_points || []).length - 2 }}
                        </ElTag>
                      </ElTooltip>
                    </div>
                  </template>

                  <template #cell-test_miss_reason="{ row }">
                    <span
                      v-if="(row.test_miss_reason || []).length === 0"
                      class="text-slate-400"
                    >
                      -
                    </span>
                    <div v-else class="dts-cell-tags">
                      <template
                        v-for="item in (row.test_miss_reason || []).slice(0, 2)"
                        :key="item"
                      >
                        <ElTag
                          :type="
                            resolveGovTag('test_miss_reason', item)?.type ||
                            'info'
                          "
                          effect="light"
                          size="small"
                        >
                          {{
                            resolveGovTag('test_miss_reason', item)?.label ||
                            item
                          }}
                        </ElTag>
                      </template>

                      <ElTooltip
                        v-if="(row.test_miss_reason || []).length > 2"
                        :content="formatArrayCell(row.test_miss_reason).tooltip"
                        placement="top-start"
                      >
                        <ElTag type="info" effect="plain" size="small">
                          +{{ (row.test_miss_reason || []).length - 2 }}
                        </ElTag>
                      </ElTooltip>
                    </div>
                  </template>

                  <template #cell-test_improvements="{ row }">
                    <span
                      v-if="(row.test_improvements || []).length === 0"
                      class="text-slate-400"
                    >
                      -
                    </span>
                    <ElTooltip
                      v-else
                      :content="formatArrayCell(row.test_improvements).tooltip"
                      placement="top-start"
                    >
                      <span class="cursor-help">
                        {{ formatArrayCell(row.test_improvements).text }}
                      </span>
                    </ElTooltip>
                  </template>

                  <template #cell-dev_remark="{ row }">
                    <span v-if="!row.dev_remark" class="text-slate-400">-</span>
                    <ElTooltip
                      v-else
                      :content="row.dev_remark"
                      placement="top-start"
                    >
                      <span class="cursor-help">{{ row.dev_remark }}</span>
                    </ElTooltip>
                  </template>

                  <template #cell-test_remark="{ row }">
                    <span v-if="!row.test_remark" class="text-slate-400">
                      -
                    </span>
                    <ElTooltip
                      v-else
                      :content="row.test_remark"
                      placement="top-start"
                    >
                      <span class="cursor-help">{{ row.test_remark }}</span>
                    </ElTooltip>
                  </template>

                  <template #cell-actions="{ row }">
                    <ElButton
                      type="primary"
                      link
                      size="small"
                      @click="openEdit(row)"
                    >
                      填报/编辑
                    </ElButton>
                  </template>

                  <template #empty>
                    <div v-if="!hasAppliedFilters" class="dts-data-guide">
                      <div class="dts-data-guide__panel">
                        <div class="dts-data-guide__title">先设置筛选条件</div>
                        <div class="dts-data-guide__desc">
                          默认已按最近一个月和关闭状态自动查询，可继续通过产品线、状态和严重程度收窄范围。
                        </div>
                        <div class="dts-data-guide__actions">
                          <ElButton
                            type="primary"
                            size="small"
                            @click="handleSearch(true)"
                          >
                            开始查询明细
                          </ElButton>
                        </div>
                      </div>
                    </div>
                    <div v-else class="dts-data-empty">
                      <ElEmpty description="当前筛选条件下暂无 DTS 数据" />
                    </div>
                  </template>
                </Grid>
              </div>
            </div>
          </ElCard>
        </ElTabPane>

        <ElTabPane label="统计看板" name="dashboard">
          <div
            v-loading="summaryLoading"
            class="dts-summary-panel space-y-4 pb-4"
          >
            <ElEmpty
              v-if="!hasAppliedFilters"
              description="正在加载默认筛选数据..."
            />
            <ElEmpty
              v-else-if="summary.total_count === 0"
              description="当前筛选无数据"
            />
            <div v-else class="flex flex-col gap-4">
              <div class="summary-overview-grid">
                <ElCard
                  shadow="never"
                  class="dense-overview-card dense-overview-card--hero"
                >
                  <div class="dense-overview-card__title-row">
                    <div class="dense-overview-card__title">缺陷总览</div>
                    <ElTag type="primary" effect="light">
                      {{ summary.total_count }} 条
                    </ElTag>
                  </div>
                  <div class="dense-overview-card__hero-value">
                    {{ summary.total_count }}
                  </div>
                  <div class="dense-overview-card__hero-label">
                    当前筛选范围内的 DTS 问题单总数
                  </div>
                  <div
                    class="dense-overview-card__metric-grid dense-overview-card__metric-grid--three"
                  >
                    <div class="dense-metric-block dense-metric-block--danger">
                      <div class="dense-metric-block__label">未关闭</div>
                      <div class="dense-metric-block__value">
                        {{ summary.open_count }}
                      </div>
                      <div class="dense-metric-block__subtext">
                        占比
                        {{
                          summary.total_count
                            ? Math.round(
                                (summary.open_count / summary.total_count) *
                                  100,
                              )
                            : 0
                        }}%
                      </div>
                    </div>
                    <div class="dense-metric-block dense-metric-block--success">
                      <div class="dense-metric-block__label">已关闭</div>
                      <div class="dense-metric-block__value">
                        {{ summary.closed_count }}
                      </div>
                      <div class="dense-metric-block__subtext">
                        占比
                        {{
                          summary.total_count
                            ? Math.round(
                                (summary.closed_count / summary.total_count) *
                                  100,
                              )
                            : 0
                        }}%
                      </div>
                    </div>
                    <div class="dense-metric-block">
                      <div class="dense-metric-block__label">平均处理天数</div>
                      <div class="dense-metric-block__value">
                        {{ summary.avg_process_days }}
                      </div>
                      <div class="dense-metric-block__subtext">近似口径</div>
                    </div>
                  </div>
                  <div class="dense-overview-card__meta">
                    填报完成度：QA
                    {{ Math.round((summary.qa_completion_rate || 0) * 100) }}% ·
                    开发
                    {{ Math.round((summary.dev_completion_rate || 0) * 100) }}%
                    · 测试
                    {{ Math.round((summary.test_completion_rate || 0) * 100) }}%
                  </div>
                </ElCard>

                <ElCard shadow="never" class="dense-overview-card">
                  <div class="dense-overview-card__title-row">
                    <div class="dense-overview-card__title">填报完成度</div>
                    <ElTag type="info" effect="plain">
                      共 {{ summary.total_count }} 条
                    </ElTag>
                  </div>

                  <div class="completion-radar-panel">
                    <div class="completion-radar-panel__chart">
                      <EchartsUI ref="completionRadarChartRef" height="260px" />
                    </div>
                    <div class="completion-kpi-grid">
                      <div class="completion-kpi-card completion-kpi-card--qa">
                        <div class="completion-kpi-card__label">QA 填报率</div>
                        <div class="completion-kpi-card__value">
                          {{ Math.round((summary.qa_completion_rate || 0) * 100) }}%
                        </div>
                        <div class="completion-kpi-card__meta">
                          {{ summary.qa_filled_count }} / {{ summary.total_count }}
                        </div>
                      </div>
                      <div class="completion-kpi-card completion-kpi-card--dev">
                        <div class="completion-kpi-card__label">开发填报率</div>
                        <div class="completion-kpi-card__value">
                          {{ Math.round((summary.dev_completion_rate || 0) * 100) }}%
                        </div>
                        <div class="completion-kpi-card__meta">
                          {{ summary.dev_filled_count }} / {{ summary.total_count }}
                        </div>
                      </div>
                      <div class="completion-kpi-card completion-kpi-card--test">
                        <div class="completion-kpi-card__label">测试填报率</div>
                        <div class="completion-kpi-card__value">
                          {{ Math.round((summary.test_completion_rate || 0) * 100) }}%
                        </div>
                        <div class="completion-kpi-card__meta">
                          {{ summary.test_filled_count }} / {{ summary.total_count }}
                        </div>
                      </div>
                    </div>
                  </div>
                </ElCard>
              </div>

              <ElCard
                shadow="never"
                class="dts-chart-card dts-chart-card--wide"
              >
                <template #header>
                  <div class="dts-chart-card__header dts-chart-card__header--stacked">
                    <div>
                      <div class="dts-chart-card__title">PL 组开发填报完成率</div>
                      <div class="dts-chart-card__desc">
                        有开发责任人即视为已填报，按完成率从高到低展示各 PL 组的填报情况。
                      </div>
                    </div>
                    <ElTag type="success" effect="plain">
                      {{ summary.pl_group_dev_completion_dist.length }} 个PL组
                    </ElTag>
                  </div>
                </template>
                <EchartsUI ref="plGroupCompletionChartRef" height="360px" />
              </ElCard>

              <ElCard shadow="never" class="summary-section-card summary-section-card--trend">
                <template #header>
                  <div class="summary-section-card__header">
                    <div>
                      <div class="summary-section-card__title">趋势与效率</div>
                      <div class="summary-section-card__desc">
                        观察当前筛选下的更新时间走势与处理时长分桶，快速判断问题波动和处理效率。
                      </div>
                    </div>
                    <ElTag
                      class="summary-section-card__tag"
                      type="primary"
                      effect="plain"
                    >
                      {{ summary.update_trend?.granularity === 'week' ? '按周聚合' : '按天聚合' }}
                    </ElTag>
                  </div>
                </template>
                <div class="dts-trend-grid">
                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">更新时间趋势</div>
                        <ElTag type="primary" effect="plain">
                          {{ summary.update_trend?.labels.length || 0 }} 个区间
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="trendChartRef" height="320px" />
                  </ElCard>

                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">处理时长分布</div>
                        <ElTag type="warning" effect="plain">
                          6 个分桶
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="processDaysChartRef" height="320px" />
                  </ElCard>
                </div>
              </ElCard>

              <ElCard shadow="never" class="summary-section-card">
                <template #header>
                  <div class="summary-section-card__header">
                    <div>
                      <div class="summary-section-card__title">缺陷结构</div>
                      <div class="summary-section-card__desc">
                        从严重程度、状态、流程类型与关闭类型维度观察当前筛选下的结构特征。
                      </div>
                    </div>
                    <ElTag
                      class="summary-section-card__tag"
                      type="danger"
                      effect="plain"
                    >
                      {{ summary.severity_dist.length }} 类严重程度
                    </ElTag>
                  </div>
                </template>
                <div class="dts-charts-grid">
                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">严重程度分布</div>
                        <ElTag type="danger" effect="plain">
                          {{ summary.severity_dist.length }} 类
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="severityChartRef" height="320px" />
                  </ElCard>

                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">状态分布</div>
                        <ElTag type="primary" effect="plain">
                          {{ summary.status_dist.length }} 类
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="statusChartRef" height="320px" />
                  </ElCard>

                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">流程类型分布</div>
                        <ElTag type="info" effect="plain">
                          {{ summary.flow_type_dist.length }} 类
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="flowTypeChartRef" height="320px" />
                  </ElCard>

                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">关闭类型分布</div>
                        <ElTag type="warning" effect="plain">
                          {{ summary.close_type_dist.length }} 类
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="closeTypeChartRef" height="320px" />
                  </ElCard>
                </div>
              </ElCard>

              <ElCard shadow="never" class="summary-section-card">
                <template #header>
                  <div class="summary-section-card__header">
                    <div>
                      <div class="summary-section-card__title">组织热点</div>
                      <div class="summary-section-card__desc">
                        聚焦各 PL 领域的严重度热点与归属排名，辅助识别高压领域和高频责任区。
                      </div>
                    </div>
                    <ElTag
                      class="summary-section-card__tag"
                      type="success"
                      effect="plain"
                    >
                      {{ summary.pl_group_severity_matrix?.rows.length || 0 }} 个PL领域
                    </ElTag>
                  </div>
                </template>
                <div class="dts-hotspot-grid">
                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">PL领域 × 严重度热点</div>
                        <ElTag type="danger" effect="plain">
                          {{ summary.pl_group_severity_matrix?.columns.length || 0 }} 个严重度维度
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="organizationHeatmapChartRef" height="360px" />
                  </ElCard>

                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header dts-chart-card__header--stacked">
                        <div>
                          <div class="dts-chart-card__title">{{ organizationRankTitle }}</div>
                          <div class="dts-chart-card__desc">
                            使用分段切换 PL 领域、项目与处理人视角。
                          </div>
                        </div>
                        <ElSegmented
                          v-model="organizationRankSegmentValue"
                          class="dts-segmented"
                          :options="SUMMARY_RANK_MODE_OPTIONS"
                          size="small"
                        />
                      </div>
                    </template>
                    <EchartsUI ref="organizationRankChartRef" height="360px" />
                  </ElCard>
                </div>
              </ElCard>

              <ElCard shadow="never" class="summary-section-card">
                <template #header>
                  <div class="summary-section-card__header">
                    <div>
                      <div class="summary-section-card__title">来源与归属</div>
                      <div class="summary-section-card__desc">
                        观察提单来源与责任 PL 领域归属，辅助判断问题如何进入系统以及主要落在哪个责任领域。
                      </div>
                    </div>
                    <ElTag
                      class="summary-section-card__tag"
                      type="warning"
                      effect="plain"
                    >
                      {{ summary.source_dist.length }} 类来源
                    </ElTag>
                  </div>
                </template>
                <div class="dts-attribution-grid">
                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">提单来源分布</div>
                        <ElTag type="warning" effect="plain">
                          {{ summary.source_dist.length }} 类
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="sourceChartRef" height="320px" />
                  </ElCard>

                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">PL领域排名</div>
                        <ElTag type="success" effect="plain">
                          {{ summary.auto_pl_group_dist.length }} 个PL领域
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="plGroupChartRef" height="340px" />
                  </ElCard>
                </div>
              </ElCard>

              <ElCard shadow="never" class="summary-section-card">
                <template #header>
                  <div class="summary-section-card__header">
                    <div>
                      <div class="summary-section-card__title">治理质量</div>
                      <div class="summary-section-card__desc">
                        将开发、测试和引入阶段拆开观察，同时保留问题分类的切换入口，方便做治理复盘。
                      </div>
                    </div>
                    <ElTag
                      class="summary-section-card__tag"
                      type="primary"
                      effect="plain"
                    >
                      {{ summary.action_status_dist.length }} 类措施状态
                    </ElTag>
                  </div>
                </template>

                <div class="dts-governance-grid">
                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">开发 / 测试措施状态对比</div>
                        <ElTag type="danger" effect="plain">
                          {{ summary.dev_action_status_dist.length + summary.test_action_status_dist.length }} 个状态项
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="actionStatusChartRef" height="320px" />
                  </ElCard>

                  <ElCard shadow="never" class="dts-chart-card">
                    <template #header>
                      <div class="dts-chart-card__header">
                        <div class="dts-chart-card__title">问题引入阶段分布</div>
                        <ElTag type="info" effect="plain">
                          {{ summary.issue_intro_stage_dist.length }} 类
                        </ElTag>
                      </div>
                    </template>
                    <EchartsUI ref="issueIntroStageChartRef" height="320px" />
                  </ElCard>

                  <ElCard
                    shadow="never"
                    class="dts-chart-card dts-chart-card--wide"
                  >
                    <template #header>
                      <div class="dts-chart-card__header dts-chart-card__header--stacked">
                        <div>
                          <div class="dts-chart-card__title">{{ governanceTreemapTitle }}</div>
                          <div class="dts-chart-card__desc">
                            在开发问题小类和漏测原因之间切换，查看高频治理分类。
                          </div>
                        </div>
                        <ElSegmented
                          v-model="governanceTreemapSegmentValue"
                          class="dts-segmented"
                          :options="SUMMARY_TREEMAP_MODE_OPTIONS"
                          size="small"
                        />
                      </div>
                    </template>
                    <EchartsUI ref="governanceTreemapChartRef" height="340px" />
                  </ElCard>
                </div>
              </ElCard>
            </div>
          </div>
        </ElTabPane>
      </ElTabs>

      <DtsBatchEditDrawer
        v-model="batchEditVisible"
        :selected-dts-biz-nos="selectedDtsBizNos"
        @success="handleBatchSaved"
      />

      <DtsEditDrawer
        v-model="editVisible"
        :row="editingRow"
        @success="handleSaved"
      />
    </div>
  </Page>
</template>

<style scoped>
.dts-statistics-shell {
  flex: 1;
  min-height: 0;
}

.dts-statistics-tabs {
  flex: 1;
  min-height: 0;
  padding: 14px;
  background: linear-gradient(
    180deg,
    rgb(255 255 255 / 96%) 0%,
    rgb(248 250 252 / 92%) 100%
  );
  border: 1px solid #dbe5f1;
  border-radius: 24px;
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 96%),
    0 12px 30px rgb(15 23 42 / 4%);
}

.dts-statistics-tabs :deep(.el-tabs__content) {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

.dts-statistics-tabs :deep(.el-tab-pane) {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

.dts-statistics-tabs :deep(.el-tabs__header) {
  padding: 8px;
  margin-bottom: 18px;
  background: linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%);
  border: 1px solid #dde6f2;
  border-radius: 18px;
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 92%);
}

.dts-statistics-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.dts-statistics-tabs :deep(.el-tabs__nav-wrap) {
  padding: 0;
}

.dts-statistics-tabs :deep(.el-tabs__nav) {
  gap: 8px;
}

.dts-statistics-tabs :deep(.el-tabs__active-bar) {
  display: none;
}

.dts-statistics-tabs :deep(.el-tabs__item) {
  height: 40px;
  padding: 0 18px !important;
  font-size: 13px;
  font-weight: 700;
  color: #64748b;
  border-radius: 12px;
  transition:
    background-color 0.2s ease,
    box-shadow 0.2s ease,
    color 0.2s ease,
    transform 0.2s ease;
}

.dts-statistics-tabs :deep(.el-tabs__item:hover) {
  color: #1e293b;
}

.dts-statistics-tabs :deep(.el-tabs__item.is-active) {
  color: #0f172a;
  background: linear-gradient(180deg, #fff 0%, #f8fbff 100%);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 90%),
    0 8px 18px rgb(37 99 235 / 12%);
  transform: translateY(-1px);
}

.dts-data-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.dts-data-card {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  background: linear-gradient(180deg, #fff 0%, #fbfdff 100%);
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  box-shadow: 0 14px 32px rgb(15 23 42 / 4%);
}

.dts-data-card :deep(.el-card__header) {
  padding: 18px 20px 16px;
  border-bottom-color: #e2e8f0;
}

.dts-data-card :deep(.el-card__body) {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  padding: 0 0 16px;
}

.dts-data-card__header {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}

.dts-data-card__title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.dts-data-card__desc {
  max-width: 720px;
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.6;
  color: #64748b;
}

.dts-data-card__status {
  flex-shrink: 0;
  margin-top: 2px;
}

.dts-data-card__body {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.dts-data-grid-wrap {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

.dts-data-grid {
  min-height: 0;
}

.dts-table-title {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  gap: 10px 16px;
  align-items: flex-start;
  min-width: 0;
  padding: 6px 0 10px;
}

.dts-table-title__filters {
  display: flex;
  flex: 1 1 720px;
  flex-wrap: wrap;
  gap: 10px 12px;
  align-items: center;
  min-width: 0;
}

.dts-table-title__field {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.dts-table-title__label,
.dts-header-filter__label {
  font-size: 12px;
  font-weight: 600;
  line-height: 1.3;
  color: #475569;
  white-space: nowrap;
}

.dts-table-title__select {
  width: 180px;
}

.dts-table-title__date {
  width: 320px;
}

.dts-table-title__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.dts-table-title__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.dts-header-filter {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  min-width: 0;
}

.dts-header-filter-trigger {
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

.dts-header-filter-trigger:hover {
  border-color: #c0c4cc;
}

.dts-header-filter-trigger.is-active {
  color: #409eff;
  background: #ecf5ff;
  border-color: #a0cfff;
}

.dts-header-filter-trigger__icon {
  width: 12px;
  height: 12px;
}

.dts-header-filter-trigger__text {
  white-space: nowrap;
}

.dts-header-filter-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dts-header-filter-panel__body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 260px;
  padding-right: 4px;
  overflow: auto;
}

.dts-header-filter-panel__search {
  position: sticky;
  top: 0;
  z-index: 1;
  padding-bottom: 2px;
  background: #fff;
}

.dts-header-filter-panel__date {
  width: 100%;
}

.dts-header-filter-panel__time-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dts-header-filter-panel__time-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dts-header-filter-panel__time-label {
  font-size: 12px;
  font-weight: 600;
  line-height: 1.4;
  color: #606266;
}

.dts-header-filter-check-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dts-header-filter-panel__tip {
  padding: 8px 2px;
  font-size: 12px;
  line-height: 1.6;
  color: #64748b;
}

.dts-header-filter-panel__actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}

:deep(.dts-header-filter-popper.el-popper) {
  padding: 10px 12px;
}

.dts-data-grid :deep(.flex.items-center.justify-between.px-4.pb-4.pt-2) {
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-start;
}

.dts-data-grid
  :deep(.flex.items-center.justify-between.px-4.pb-4.pt-2 > div:first-child) {
  display: flex;
  flex: 1 1 760px;
  min-width: 0;
}

.dts-data-grid
  :deep(.flex.items-center.justify-between.px-4.pb-4.pt-2 > div:last-child) {
  flex-shrink: 0;
}

.dts-data-grid :deep(.zq-table-header th.el-table__cell) {
  vertical-align: middle;
}

.dts-data-grid :deep(.zq-table-header .cell) {
  overflow: visible;
  white-space: normal;
}

.dts-cell-tags {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  justify-content: center;
}

.dts-project-cell {
  display: inline-flex;
  flex-direction: column;
  gap: 2px;
  align-items: center;
  line-height: 1.4;
}

.dts-project-cell__hint {
  color: #94a3b8;
  font-size: 12px;
}

.dts-data-guide {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  padding: 16px 20px;
}

.dts-data-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 280px;
}

.dts-data-guide__panel {
  width: min(100%, 420px);
  padding: 20px 22px;
  text-align: center;
  background: #fff;
  border: 1px dashed #cbd5e1;
  border-radius: 16px;
}

.dts-data-guide__title {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.4;
  color: #0f172a;
}

.dts-data-guide__desc {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.7;
  color: #475569;
}

.dts-data-guide__meta {
  margin-top: 8px;
  font-size: 12px;
  color: #94a3b8;
}

.dts-data-guide__actions {
  display: flex;
  justify-content: center;
  margin-top: 14px;
}

.dts-summary-panel {
  flex: 1;
  min-height: 0;
  padding-right: 4px;
  overflow-y: auto;
}

.summary-overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}

.dense-overview-card {
  min-height: 216px;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  box-shadow: 0 12px 28px rgb(15 23 42 / 4%);
}

.dense-overview-card--hero {
  background:
    radial-gradient(circle at top right, rgb(37 99 235 / 14%), transparent 42%),
    linear-gradient(135deg, #eff6ff 0%, #fff 100%);
}

.dense-overview-card__title-row {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}

.dense-overview-card__title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.dense-overview-card__hero-value {
  margin-top: 18px;
  font-size: 40px;
  font-weight: 800;
  line-height: 1;
  color: #0f172a;
}

.dense-overview-card__hero-label {
  margin-top: 6px;
  font-size: 13px;
  color: #475569;
}

.dense-overview-card__metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 18px;
}

.dense-overview-card__meta {
  margin-top: 10px;
  font-size: 12px;
  color: #64748b;
}

.dense-overview-card__metric-grid--three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.dense-metric-block {
  padding: 14px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
}

.dense-metric-block--warning {
  background: linear-gradient(180deg, #fff7ed 0%, #fff 100%);
  border-color: #fdba74;
}

.dense-metric-block--danger {
  background: linear-gradient(180deg, #fef2f2 0%, #fff 100%);
  border-color: #fca5a5;
}

.dense-metric-block--success {
  background: linear-gradient(180deg, #f0fdf4 0%, #fff 100%);
  border-color: #86efac;
}

.dense-metric-block__label {
  font-size: 12px;
  color: #64748b;
}

.dense-metric-block__value {
  margin-top: 10px;
  font-size: 24px;
  font-weight: 800;
  line-height: 1.1;
  color: #0f172a;
}

.dense-metric-block__subtext {
  margin-top: 6px;
  font-size: 12px;
  color: #475569;
}

.dense-completion-grid {
  display: grid;
  gap: 12px;
  margin-top: 18px;
}

.dense-completion-panel {
  padding: 16px;
  border-radius: 18px;
}

.dense-completion-panel--qa {
  background: linear-gradient(180deg, #eff6ff 0%, #fff 100%);
  border: 1px solid #bfdbfe;
}

.dense-completion-panel--dev {
  background: linear-gradient(180deg, #fff7ed 0%, #fff 100%);
  border: 1px solid #fdba74;
}

.dense-completion-panel--test {
  background: linear-gradient(180deg, #f0fdf4 0%, #fff 100%);
  border: 1px solid #86efac;
}

.dense-completion-panel__title {
  font-size: 12px;
  font-weight: 700;
  color: #334155;
}

.dense-completion-panel__headline {
  margin: 10px 0 12px;
  font-size: 24px;
  font-weight: 800;
  line-height: 1.2;
  color: #0f172a;
}

.dense-completion-panel__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.6;
  color: #475569;
}

.summary-section-card {
  border-radius: 18px;
}

.summary-section-card :deep(.el-card__header) {
  padding: 18px 20px 16px;
  border-bottom-color: #e2e8f0;
}

.summary-section-card__header {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}

.summary-section-card__title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.summary-section-card__desc {
  max-width: 720px;
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.6;
  color: #64748b;
}

.summary-section-card__tag {
  flex-shrink: 0;
  margin-top: 2px;
}

.dts-charts-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.dts-chart-card {
  border-radius: 18px;
}

.dts-chart-card :deep(.el-card__header) {
  padding: 14px 18px 12px;
  border-bottom-color: #e2e8f0;
}

.dts-chart-card__header {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}

.dts-chart-card__title {
  font-size: 13px;
  font-weight: 600;
  line-height: 18px;
  color: #0f172a;
}

.dts-chart-card--wide {
  grid-column: 1 / -1;
}

.completion-radar-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 18px;
}

.completion-radar-panel__chart {
  min-height: 240px;
}

.completion-kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.completion-kpi-card {
  padding: 14px 16px;
  background: linear-gradient(180deg, #fff 0%, #f8fafc 100%);
  border: 1px solid #e2e8f0;
  border-radius: 16px;
}

.completion-kpi-card--qa {
  background: linear-gradient(180deg, #eff6ff 0%, #fff 100%);
  border-color: #bfdbfe;
}

.completion-kpi-card--dev {
  background: linear-gradient(180deg, #f0fdf4 0%, #fff 100%);
  border-color: #86efac;
}

.completion-kpi-card--test {
  background: linear-gradient(180deg, #fff7ed 0%, #fff 100%);
  border-color: #fdba74;
}

.completion-kpi-card__label {
  font-size: 12px;
  color: #64748b;
}

.completion-kpi-card__value {
  margin-top: 8px;
  font-size: 24px;
  font-weight: 800;
  line-height: 1.1;
  color: #0f172a;
}

.completion-kpi-card__meta {
  margin-top: 6px;
  font-size: 12px;
  color: #475569;
}

.dts-trend-grid,
.dts-attribution-grid,
.dts-governance-grid,
.dts-hotspot-grid {
  display: grid;
  gap: 12px;
}

.dts-trend-grid {
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 0.9fr);
}

.dts-attribution-grid {
  grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
}

.dts-governance-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.dts-hotspot-grid {
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
}

.dts-chart-card__header--stacked {
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
}

.dts-chart-card__desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.6;
  color: #64748b;
}

.dts-segmented {
  align-self: flex-start;
}

.summary-section-card--trend {
  background: linear-gradient(180deg, #fff 0%, #f8fbff 100%);
}

@media (max-width: 1024px) {
  .dense-overview-card__metric-grid--three {
    grid-template-columns: repeat(1, minmax(0, 1fr));
  }

  .dts-data-grid-wrap,
  .dts-data-grid {
    min-height: 0;
  }

  .dts-table-title__filters {
    flex-basis: 100%;
  }

  .dts-table-title__date {
    width: 260px;
  }

  .dts-data-grid :deep(.p-4) {
    position: sticky;
    bottom: 0;
    z-index: 3;
    background: #fff;
    box-shadow: 0 -6px 16px rgb(15 23 42 / 8%);
  }

  .dts-data-grid :deep(.el-table__body-wrapper) {
    padding-bottom: 64px;
  }

  .dts-charts-grid {
    grid-template-columns: 1fr;
  }

  .completion-kpi-grid,
  .dts-trend-grid,
  .dts-attribution-grid,
  .dts-governance-grid,
  .dts-hotspot-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .dts-statistics-tabs {
    padding: 10px;
    border-radius: 18px;
  }

  .dts-data-card__header,
  .summary-section-card__header,
  .dense-overview-card__title-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
