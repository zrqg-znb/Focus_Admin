import type { VbenFormSchema } from '#/adapter/form';
import type {
  DtsDictOptions,
  DtsMergedDefect,
} from '#/api/project-manager/dts-statistics';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { getDtsDictOptions } from '#/api/project-manager/dts-statistics';

type Columns = ZqTableGridOptions<DtsMergedDefect>['columns'];

const YES_NO_OPTIONS = [
  { label: '是', value: '是' },
  { label: '否', value: '否' },
];

export type SelectOption = { label: string; value: string };

export type DtsFormFieldComponent =
  | 'ApiSelect'
  | 'Input'
  | 'Textarea'
  | 'UserSelector';

export interface DtsFormFieldConfig {
  component: DtsFormFieldComponent;
  fieldName: string;
  label: string;
  placeholder: string;
  dictKey?: keyof DtsDictOptions;
  multiple?: boolean;
  rows?: number;
}

function normalizeSelectOptions(
  items: Array<Partial<SelectOption>> | null | undefined,
): SelectOption[] {
  const seen = new Set<string>();
  const options: SelectOption[] = [];
  (items || []).forEach((item) => {
    const label = String(item.label ?? item.value ?? '').trim();
    const value = String(item.value ?? item.label ?? '').trim();
    const resolvedLabel = label || value;
    // Store label into DB so list/export/summary remain human-readable.
    const resolvedValue = resolvedLabel;
    if (!resolvedLabel || !resolvedValue || seen.has(resolvedValue)) {
      return;
    }
    seen.add(resolvedValue);
    options.push({ label: resolvedLabel, value: resolvedValue });
  });
  return options;
}

function normalizeDtsDictOptions(
  bundle: null | Partial<DtsDictOptions> | undefined,
): DtsDictOptions {
  const safeBundle = bundle || {};
  const normalized: DtsDictOptions = {
    yes_no: normalizeSelectOptions(safeBundle.yes_no),
    issue_intro_stage: normalizeSelectOptions(safeBundle.issue_intro_stage),
    dev_sub_category: normalizeSelectOptions(safeBundle.dev_sub_category),
    dev_issue_intro_point: normalizeSelectOptions(
      safeBundle.dev_issue_intro_point,
    ),
    dev_issue_probability: normalizeSelectOptions(
      safeBundle.dev_issue_probability,
    ),
    dev_common_issue_type: normalizeSelectOptions(
      safeBundle.dev_common_issue_type,
    ),
    dev_control_points: normalizeSelectOptions(safeBundle.dev_control_points),
    dev_non_base_desc: normalizeSelectOptions(safeBundle.dev_non_base_desc),
    test_miss_reason: normalizeSelectOptions(safeBundle.test_miss_reason),
    action_status: normalizeSelectOptions(safeBundle.action_status),
  };
  if (normalized.yes_no.length === 0) {
    normalized.yes_no = [...YES_NO_OPTIONS];
  }
  return normalized;
}

let dtsDictOptionsPromise: null | Promise<DtsDictOptions> = null;

export async function fetchDtsDictOptionsCached(
  force = false,
): Promise<DtsDictOptions> {
  if (force || !dtsDictOptionsPromise) {
    dtsDictOptionsPromise = getDtsDictOptions()
      .then((bundle) => normalizeDtsDictOptions(bundle))
      .catch(() => normalizeDtsDictOptions(null));
  }
  return dtsDictOptionsPromise;
}

function createDtsDictApiSelectProps(
  key: keyof DtsDictOptions,
  fallbackOptions: SelectOption[] = [],
) {
  return {
    api: async () => {
      const bundle = await fetchDtsDictOptionsCached();
      return (bundle as any)[key] || [];
    },
    afterFetch: (items: SelectOption[]) => {
      const options = normalizeSelectOptions(items);
      return options.length > 0 ? options : fallbackOptions;
    },
    filterable: true,
    clearable: true,
  };
}

export type DtsTagType = 'danger' | 'info' | 'primary' | 'success' | 'warning';

export interface DtsDictTagMeta {
  label: string;
  type: DtsTagType;
}

export type DtsGovernanceField =
  | 'action_status'
  | 'dev_common_issue_type'
  | 'dev_control_points'
  | 'dev_issue_intro_point'
  | 'dev_issue_probability'
  | 'dev_non_base_desc'
  | 'dev_status'
  | 'dev_sub_category'
  | 'is_base_soft_issue'
  | 'is_downstream'
  | 'is_duplicate_issue'
  | 'issue_intro_stage'
  | 'need_aar'
  | 'need_dev_analyze'
  | 'need_test_analyze'
  | 'test_miss_reason'
  | 'test_status';

const TAG_PALETTE: DtsTagType[] = [
  'primary',
  'success',
  'warning',
  'danger',
  'info',
];

function resolveOptionsForField(
  dictOptions: DtsDictOptions | null | undefined,
  field: DtsGovernanceField,
): SelectOption[] {
  const safeOptions = dictOptions || normalizeDtsDictOptions(null);
  switch (field) {
    case 'action_status': {
      return safeOptions.action_status;
    }
    case 'dev_common_issue_type': {
      return safeOptions.dev_common_issue_type;
    }
    case 'dev_control_points': {
      return safeOptions.dev_control_points;
    }
    case 'dev_issue_intro_point': {
      return safeOptions.dev_issue_intro_point;
    }
    case 'dev_issue_probability': {
      return safeOptions.dev_issue_probability;
    }
    case 'dev_non_base_desc': {
      return safeOptions.dev_non_base_desc;
    }
    case 'dev_status': {
      return safeOptions.action_status;
    }
    case 'dev_sub_category': {
      return safeOptions.dev_sub_category;
    }
    case 'is_base_soft_issue':
    case 'is_downstream':
    case 'is_duplicate_issue':
    case 'need_aar':
    case 'need_dev_analyze':
    case 'need_test_analyze': {
      return safeOptions.yes_no.length > 0
        ? safeOptions.yes_no
        : YES_NO_OPTIONS;
    }
    case 'issue_intro_stage': {
      return safeOptions.issue_intro_stage;
    }
    case 'test_miss_reason': {
      return safeOptions.test_miss_reason;
    }
    case 'test_status': {
      return safeOptions.action_status;
    }
    default: {
      return [];
    }
  }
}

function resolveOptionLabel(raw: unknown, options: SelectOption[]): string {
  const text = String(raw || '').trim();
  if (!text) {
    return '';
  }
  const matched = options.find((item) => {
    const value = String(item.value || '').trim();
    const label = String(item.label || '').trim();
    return value === text || label === text;
  });
  return String(matched?.label || matched?.value || text).trim() || text;
}

function resolvePaletteTagType(
  raw: unknown,
  options: SelectOption[],
): DtsTagType {
  const text = String(raw || '').trim();
  if (!text || options.length === 0) {
    return 'info';
  }
  const index = options.findIndex((item) => {
    const value = String(item.value || '').trim();
    const label = String(item.label || '').trim();
    return value === text || label === text;
  });
  if (index === -1) {
    return 'info';
  }
  return TAG_PALETTE[index % TAG_PALETTE.length] || 'info';
}

function resolveYesNoTagType(label: string): DtsTagType {
  const text = String(label || '').trim();
  if (text === '是' || text.toLowerCase() === 'yes') {
    return 'success';
  }
  if (text === '否' || text.toLowerCase() === 'no') {
    return 'info';
  }
  return 'info';
}

function resolveActionStatusTagType(label: string): DtsTagType {
  const text = String(label || '').trim();
  if (!text) {
    return 'info';
  }
  const normalized = text.toLowerCase();
  if (normalized === 'open' || text.includes('未关闭')) {
    return 'warning';
  }
  if (
    normalized === 'close' ||
    text.includes('已关闭') ||
    text.includes('关闭')
  ) {
    return 'success';
  }
  return 'info';
}

export function resolveDtsGovernanceTagMeta(
  dictOptions: DtsDictOptions | null | undefined,
  field: DtsGovernanceField,
  raw: unknown,
): DtsDictTagMeta | null {
  const text = String(raw || '').trim();
  if (!text) {
    return null;
  }
  const options = resolveOptionsForField(dictOptions, field);
  const label = resolveOptionLabel(text, options) || text;
  if (!label) {
    return null;
  }

  if (
    field === 'is_base_soft_issue' ||
    field === 'is_downstream' ||
    field === 'is_duplicate_issue' ||
    field === 'need_aar' ||
    field === 'need_dev_analyze' ||
    field === 'need_test_analyze'
  ) {
    return { label, type: resolveYesNoTagType(label) };
  }

  if (field === 'dev_status' || field === 'test_status') {
    const semanticType = resolveActionStatusTagType(label);
    if (semanticType !== 'info') {
      return { label, type: semanticType };
    }
    return { label, type: resolvePaletteTagType(label, options) };
  }

  return { label, type: resolvePaletteTagType(label, options) };
}

export function resolveDtsGovernanceTagList(
  dictOptions: DtsDictOptions | null | undefined,
  field:
    | 'dev_control_points'
    | 'dev_non_base_desc'
    | 'dev_sub_category'
    | 'test_miss_reason',
  raw: unknown,
): DtsDictTagMeta[] {
  const values = Array.isArray(raw) ? raw : [];
  const options = resolveOptionsForField(dictOptions, field);
  const seen = new Set<string>();
  const result: DtsDictTagMeta[] = [];

  values.forEach((value) => {
    const text = String(value || '').trim();
    if (!text) {
      return;
    }
    const label = resolveOptionLabel(text, options) || text;
    if (!label || seen.has(label)) {
      return;
    }
    seen.add(label);
    result.push({
      label,
      type: resolvePaletteTagType(label, options),
    });
  });

  return result;
}

export interface SeverityMeta {
  label: string;
  type: 'danger' | 'info' | 'success' | 'warning';
  tip: string;
}

function withCenterAlign(columns: Record<string, any>[]) {
  return columns.map((column) => {
    const nextColumn: Record<string, any> = {
      ...column,
      align: column.align ?? 'center',
      headerAlign: column.headerAlign ?? 'center',
    };
    if (Array.isArray(column.children)) {
      nextColumn.children = withCenterAlign(column.children);
    }
    return nextColumn;
  });
}

function pad2(value: number) {
  return String(value).padStart(2, '0');
}

export function formatDateTime(date: Date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(
    date.getDate(),
  )} ${pad2(date.getHours())}:${pad2(date.getMinutes())}:${pad2(
    date.getSeconds(),
  )}`;
}

export function formatCycleIntegerDisplay(value: unknown) {
  const text = String(value ?? '').trim();
  if (!text) {
    return '-';
  }
  const numeric = Number(text);
  if (Number.isFinite(numeric)) {
    return String(Math.round(numeric));
  }
  return text;
}

export function formatProjectDisplay(row?: null | Partial<DtsMergedDefect>) {
  const projectName = String(row?.projectName || '').trim();
  const projectCode = String(row?.sProdCName || '').trim();
  if (projectName && projectCode && projectName !== projectCode) {
    return `${projectName} (${projectCode})`;
  }
  return projectName || projectCode || '-';
}

export function getTodayDateRange(): [Date, Date] {
  const now = new Date();
  const start = new Date(now);
  start.setHours(0, 0, 0, 0);
  const end = new Date(now);
  end.setHours(23, 59, 59, 0);
  return [start, end];
}

export function useColumns(): Columns {
  return withCenterAlign([
    {
      key: 'dtsBizNo',
      dataKey: 'dtsBizNo',
      title: '问题单号',
      width: 180,
      fixed: 'left',
    },
    {
      key: 'briefDesc',
      dataKey: 'briefDesc',
      title: '简要描述',
      minWidth: 240,
      fixed: 'left',
      showOverflowTooltip: true,
    },
    {
      key: 'dtsStatusName',
      dataKey: 'dtsStatusName',
      title: '当前状态',
      width: 140,
      fixed: 'left',
    },
    {
      key: 'serverityNoName',
      dataKey: 'serverityNoName',
      title: '严重程度',
      width: 110,
    },
    {
      key: 'parentNo',
      dataKey: 'parentNo',
      title: '父单单号',
      width: 140,
    },
    {
      key: 'createAt',
      dataKey: 'createAt',
      title: '提单时间',
      width: 170,
    },
    {
      key: 'dCloseTime',
      dataKey: 'dCloseTime',
      title: '关闭时间',
      width: 170,
    },
    {
      key: 'uQbiCloseTypeName',
      dataKey: 'uQbiCloseTypeName',
      title: '关闭类型',
      width: 140,
    },
    {
      key: 'sConfigFlowType',
      dataKey: 'sConfigFlowType',
      title: '流程类型',
      width: 120,
    },
    {
      key: 'sDeptOneNoName',
      dataKey: 'sDeptOneNoName',
      title: '提出方部门',
      width: 140,
    },
    {
      key: 'auto_source_type',
      dataKey: 'auto_source_type',
      title: '提单来源',
      width: 140,
    },
    {
      key: 'currentHandler',
      dataKey: 'currentHandler',
      title: '当前处理人',
      width: 130,
    },
    {
      key: 'creator',
      dataKey: 'creator',
      title: '提单人工号',
      width: 130,
    },
    {
      key: 'sSubmitUserName',
      dataKey: 'sSubmitUserName',
      title: '提单人姓名',
      width: 130,
    },
    {
      key: 'projectName',
      dataKey: 'projectName',
      title: '项目',
      minWidth: 180,
    },
    {
      key: 'sSubsystemNoName',
      dataKey: 'sSubsystemNoName',
      title: '子系统',
      width: 140,
    },
    {
      key: 'sProdFamilyNoName',
      dataKey: 'sProdFamilyNoName',
      title: '产品族名称',
      width: 140,
    },
    {
      key: 'sProdXtdNoName',
      dataKey: 'sProdXtdNoName',
      title: '产品名称',
      width: 140,
    },
    {
      key: 'iTestBackCount',
      dataKey: 'iTestBackCount',
      title: '测试返回次数',
      width: 120,
    },
    {
      key: 'last_dts009_handler',
      dataKey: 'last_dts009_handler',
      title: '最后开发修改人',
      width: 140,
    },
    {
      key: 'auto_pl_group_name',
      dataKey: 'auto_pl_group_name',
      title: '自动责任PL组',
      width: 150,
    },
    {
      key: 'last_dts010_handler',
      dataKey: 'last_dts010_handler',
      title: '最后审核修改人',
      width: 140,
    },
    {
      key: 'last_dts013_handler',
      dataKey: 'last_dts013_handler',
      title: '最后测试回归人',
      width: 140,
    },
    {
      key: 'iNumOfCloseDays',
      dataKey: 'iNumOfCloseDays',
      title: '关闭周期',
      width: 110,
    },
    {
      key: 'iNumOfFirmDays',
      dataKey: 'iNumOfFirmDays',
      title: '确认周期',
      width: 110,
    },
    {
      key: 'iNumOfLocateDays',
      dataKey: 'iNumOfLocateDays',
      title: '定位周期',
      width: 110,
    },
    {
      key: 'iNumofModifyDays',
      dataKey: 'iNumofModifyDays',
      title: '修改周期',
      width: 110,
    },
    {
      key: 'iNumofTestDays',
      dataKey: 'iNumofTestDays',
      title: '回归测试周期',
      width: 140,
    },
    {
      key: 'qa_group',
      title: 'QA填报',
      children: [
        {
          key: 'is_downstream',
          dataKey: 'is_downstream',
          title: '是否下游问题',
          width: 110,
        },
        {
          key: 'process_quality_type',
          dataKey: 'process_quality_type',
          title: '过程质量分类',
          minWidth: 160,
        },
        {
          key: 'need_aar',
          dataKey: 'need_aar',
          title: '是否需要AAR',
          width: 130,
        },
        {
          key: 'need_dev_analyze',
          dataKey: 'need_dev_analyze',
          title: '需开发分析',
          width: 120,
        },
        {
          key: 'need_test_analyze',
          dataKey: 'need_test_analyze',
          title: '需测试分析',
          width: 120,
        },
        {
          key: 'qa_remark',
          dataKey: 'qa_remark',
          title: 'QA备注',
          minWidth: 200,
        },
      ],
    },
    {
      key: 'dev_group',
      title: '开发填报',
      children: [
        {
          key: 'dev_owner_name',
          dataKey: 'dev_owner_name',
          title: '开发责任人',
          width: 140,
        },
        {
          key: 'issue_intro_stage',
          dataKey: 'issue_intro_stage',
          title: '问题引入阶段',
          width: 150,
        },
        {
          key: 'dev_feature',
          dataKey: 'dev_feature',
          title: '特性/功能',
          minWidth: 160,
        },
        {
          key: 'dev_sub_category',
          dataKey: 'dev_sub_category',
          title: '问题小类',
          minWidth: 180,
        },
        {
          key: 'dev_reason',
          dataKey: 'dev_reason',
          title: '问题原因',
          minWidth: 180,
        },
        {
          key: 'dev_intro_reason',
          dataKey: 'dev_intro_reason',
          title: '引入原因',
          minWidth: 180,
        },
        {
          key: 'dev_issue_intro_point',
          dataKey: 'dev_issue_intro_point',
          title: '问题引入点',
          minWidth: 160,
        },
        {
          key: 'dev_issue_probability',
          dataKey: 'dev_issue_probability',
          title: '问题概率',
          width: 130,
        },
        {
          key: 'dev_common_issue_type',
          dataKey: 'dev_common_issue_type',
          title: '是否共性问题',
          minWidth: 150,
        },
        {
          key: 'is_base_soft_issue',
          dataKey: 'is_base_soft_issue',
          title: '是否底软问题',
          width: 130,
        },
        {
          key: 'is_duplicate_issue',
          dataKey: 'is_duplicate_issue',
          title: '是否重复问题',
          width: 130,
        },
        {
          key: 'duplicate_issue_no',
          dataKey: 'duplicate_issue_no',
          title: '重复问题单号',
          minWidth: 180,
          showOverflowTooltip: true,
        },
        {
          key: 'dev_control_points',
          dataKey: 'dev_control_points',
          title: '需要补强的开发控制点',
          minWidth: 220,
        },
        {
          key: 'dev_intro_point_analysis',
          dataKey: 'dev_intro_point_analysis',
          title: '引入点分析',
          minWidth: 180,
        },
        {
          key: 'dev_improvements',
          dataKey: 'dev_improvements',
          title: '改进措施',
          minWidth: 200,
        },
        {
          key: 'dev_non_base_desc',
          dataKey: 'dev_non_base_desc',
          title: '非底软说明',
          width: 160,
        },
        {
          key: 'dev_aar_link',
          dataKey: 'dev_aar_link',
          title: 'AAR链接',
          minWidth: 180,
        },
        {
          key: 'dev_asset_link',
          dataKey: 'dev_asset_link',
          title: '落地资产链接',
          minWidth: 200,
        },
        {
          key: 'dev_status',
          dataKey: 'dev_status',
          title: '改进状态',
          width: 140,
        },
        {
          key: 'dev_remark',
          dataKey: 'dev_remark',
          title: '开发备注',
          minWidth: 200,
        },
      ],
    },
    {
      key: 'test_group',
      title: '测试填报',
      children: [
        {
          key: 'test_owner_name',
          dataKey: 'test_owner_name',
          title: '测试责任人',
          width: 140,
        },
        {
          key: 'test_miss_reason',
          dataKey: 'test_miss_reason',
          title: '漏测原因',
          minWidth: 180,
        },
        {
          key: 'test_standard_desc',
          dataKey: 'test_standard_desc',
          title: '规范问题描述',
          minWidth: 200,
        },
        {
          key: 'test_improvements',
          dataKey: 'test_improvements',
          title: '改进措施',
          minWidth: 200,
        },
        {
          key: 'test_non_test_desc',
          dataKey: 'test_non_test_desc',
          title: '非测试说明',
          minWidth: 180,
        },
        {
          key: 'test_asset_link',
          dataKey: 'test_asset_link',
          title: '落地资产链接',
          minWidth: 200,
        },
        {
          key: 'test_status',
          dataKey: 'test_status',
          title: '改进状态',
          width: 140,
        },
        {
          key: 'test_remark',
          dataKey: 'test_remark',
          title: '测试备注',
          minWidth: 200,
        },
      ],
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 130,
      fixed: 'right',
    },
  ]) as Columns;
}

export function resolveSeverityMeta(raw?: null | string): SeverityMeta {
  const text = String(raw || '').trim();
  const normalized = text.toLowerCase().replaceAll(/\s+/g, '');

  const has = (pattern: string) => normalized.includes(pattern);
  const equals = (pattern: string) => normalized === pattern;

  if (
    has('关键') ||
    has('致命') ||
    has('fatal') ||
    has('critical') ||
    equals('s0') ||
    equals('p0') ||
    has('blocker')
  ) {
    return {
      label: text || '关键',
      type: 'danger',
      tip: '最高优先级/影响范围最大',
    };
  }
  if (
    has('严重') ||
    has('high') ||
    has('major') ||
    equals('s1') ||
    equals('p1')
  ) {
    return { label: text || '严重', type: 'warning', tip: '高优先级/影响较大' };
  }
  if (
    has('一般') ||
    has('medium') ||
    has('normal') ||
    equals('s2') ||
    equals('p2')
  ) {
    return { label: text || '一般', type: 'info', tip: '中等优先级' };
  }
  if (
    has('提示') ||
    has('low') ||
    has('minor') ||
    equals('s3') ||
    equals('p3')
  ) {
    return { label: text || '提示', type: 'success', tip: '低优先级/提示类' };
  }

  return {
    label: text || '-',
    type: 'info',
    tip: '未识别的级别，按默认样式展示',
  };
}

export const DTS_QA_FORM_FIELDS: DtsFormFieldConfig[] = [
  {
    component: 'ApiSelect',
    fieldName: 'is_downstream',
    label: '是否下游问题',
    placeholder: '请选择',
    dictKey: 'yes_no',
  },
  {
    component: 'Input',
    fieldName: 'process_quality_type',
    label: '过程质量分类',
    placeholder: '请输入过程质量分类',
  },
  {
    component: 'ApiSelect',
    fieldName: 'need_aar',
    label: '是否需要AAR',
    placeholder: '请选择',
    dictKey: 'yes_no',
  },
  {
    component: 'ApiSelect',
    fieldName: 'need_dev_analyze',
    label: '需开发分析',
    placeholder: '请选择',
    dictKey: 'yes_no',
  },
  {
    component: 'ApiSelect',
    fieldName: 'need_test_analyze',
    label: '需测试分析',
    placeholder: '请选择',
    dictKey: 'yes_no',
  },
  {
    component: 'Textarea',
    fieldName: 'qa_remark',
    label: '备注',
    placeholder: '请输入备注',
    rows: 3,
  },
];

export const DTS_DEV_FORM_FIELDS: DtsFormFieldConfig[] = [
  {
    component: 'UserSelector',
    fieldName: 'dev_owner_id',
    label: '开发责任人',
    placeholder: '请选择开发责任人',
  },
  {
    component: 'Input',
    fieldName: 'dev_feature',
    label: '特性/功能',
    placeholder: '请输入特性/功能',
  },
  {
    component: 'ApiSelect',
    fieldName: 'issue_intro_stage',
    label: '问题引入阶段',
    placeholder: '请选择问题引入阶段',
    dictKey: 'issue_intro_stage',
  },
  {
    component: 'ApiSelect',
    fieldName: 'dev_sub_category',
    label: '问题小类',
    placeholder: '请选择问题小类（可多选）',
    dictKey: 'dev_sub_category',
    multiple: true,
  },
  {
    component: 'Textarea',
    fieldName: 'dev_reason',
    label: '问题原因',
    placeholder: '请输入问题原因',
    rows: 3,
  },
  {
    component: 'Textarea',
    fieldName: 'dev_intro_reason',
    label: '引入原因',
    placeholder: '请输入引入原因',
    rows: 3,
  },
  {
    component: 'ApiSelect',
    fieldName: 'dev_issue_intro_point',
    label: '问题引入点',
    placeholder: '请选择问题引入点',
    dictKey: 'dev_issue_intro_point',
  },
  {
    component: 'ApiSelect',
    fieldName: 'dev_issue_probability',
    label: '问题概率',
    placeholder: '请选择问题概率',
    dictKey: 'dev_issue_probability',
  },
  {
    component: 'ApiSelect',
    fieldName: 'dev_common_issue_type',
    label: '是否共性问题',
    placeholder: '请选择是否共性问题',
    dictKey: 'dev_common_issue_type',
  },
  {
    component: 'ApiSelect',
    fieldName: 'is_base_soft_issue',
    label: '是否底软问题',
    placeholder: '请选择是否底软问题',
    dictKey: 'yes_no',
  },
  {
    component: 'ApiSelect',
    fieldName: 'is_duplicate_issue',
    label: '是否重复问题',
    placeholder: '请选择是否重复问题',
    dictKey: 'yes_no',
  },
  {
    component: 'Input',
    fieldName: 'duplicate_issue_no',
    label: '重复问题单号',
    placeholder: '仅重复问题填写',
  },
  {
    component: 'ApiSelect',
    fieldName: 'dev_control_points',
    label: '需要补强的开发控制点',
    placeholder: '请选择开发控制点（可多选）',
    dictKey: 'dev_control_points',
    multiple: true,
  },
  {
    component: 'Textarea',
    fieldName: 'dev_intro_point_analysis',
    label: '引入点分析',
    placeholder: '请输入引入点分析',
    rows: 3,
  },
  {
    component: 'Textarea',
    fieldName: 'dev_improvements',
    label: '改进措施(开发)',
    placeholder: '一行一条（保存时自动拆分）',
    rows: 3,
  },
  {
    component: 'ApiSelect',
    fieldName: 'dev_non_base_desc',
    label: '非底软说明',
    placeholder: '请选择非底软问题说明（可多选）',
    dictKey: 'dev_non_base_desc',
    multiple: true,
  },
  {
    component: 'Input',
    fieldName: 'dev_aar_link',
    label: 'AAR链接',
    placeholder: '请输入AAR链接',
  },
  {
    component: 'Input',
    fieldName: 'dev_asset_link',
    label: '落地资产链接(开发)',
    placeholder: '请输入链接',
  },
  {
    component: 'ApiSelect',
    fieldName: 'dev_status',
    label: '改进状态(开发)',
    placeholder: '请选择改进状态',
    dictKey: 'action_status',
  },
  {
    component: 'Textarea',
    fieldName: 'dev_remark',
    label: '开发备注',
    placeholder: '请输入开发备注',
    rows: 3,
  },
];

export const DTS_TEST_FORM_FIELDS: DtsFormFieldConfig[] = [
  {
    component: 'UserSelector',
    fieldName: 'test_owner_id',
    label: '测试责任人',
    placeholder: '请选择测试责任人',
  },
  {
    component: 'ApiSelect',
    fieldName: 'test_miss_reason',
    label: '漏测原因',
    placeholder: '请选择漏测原因（可多选）',
    dictKey: 'test_miss_reason',
    multiple: true,
  },
  {
    component: 'Textarea',
    fieldName: 'test_standard_desc',
    label: '规范问题描述',
    placeholder: '请输入规范问题描述',
    rows: 3,
  },
  {
    component: 'Textarea',
    fieldName: 'test_improvements',
    label: '改进措施(测试)',
    placeholder: '一行一条（保存时自动拆分）',
    rows: 3,
  },
  {
    component: 'Textarea',
    fieldName: 'test_non_test_desc',
    label: '非测试说明',
    placeholder: '请输入非测试问题说明',
    rows: 2,
  },
  {
    component: 'Input',
    fieldName: 'test_asset_link',
    label: '落地资产链接(测试)',
    placeholder: '请输入链接',
  },
  {
    component: 'ApiSelect',
    fieldName: 'test_status',
    label: '改进状态(测试)',
    placeholder: '请选择改进状态',
    dictKey: 'action_status',
  },
  {
    component: 'Textarea',
    fieldName: 'test_remark',
    label: '测试备注',
    placeholder: '请输入测试备注',
    rows: 3,
  },
];

export function getDtsDictOptionsByKey(
  bundle: DtsDictOptions | null | undefined,
  key: keyof DtsDictOptions,
) {
  const safeBundle = normalizeDtsDictOptions(bundle);
  const options = safeBundle[key] || [];
  if (key === 'yes_no' && options.length === 0) {
    return [...YES_NO_OPTIONS];
  }
  return options;
}

export function normalizeDtsStringListValue(value: unknown): string[] {
  if (Array.isArray(value)) {
    const result: string[] = [];
    const seen = new Set<string>();
    value.forEach((item) => {
      const text = String(item || '').trim();
      if (!text || seen.has(text)) {
        return;
      }
      seen.add(text);
      result.push(text);
    });
    return result;
  }

  const text = String(value || '').trim();
  if (!text) {
    return [];
  }

  const parts = text.split(/\r?\n|,|，/);
  const result: string[] = [];
  const seen = new Set<string>();
  parts.forEach((part) => {
    const item = String(part || '').trim();
    if (!item || seen.has(item)) {
      return;
    }
    seen.add(item);
    result.push(item);
  });
  return result;
}

export function joinDtsTextareaLines(value: unknown): string {
  if (!Array.isArray(value)) {
    return String(value || '').trim();
  }
  return value
    .map((item) => String(item || '').trim())
    .filter(Boolean)
    .join('\n');
}

export function buildDtsExtensionSubmitPayload(raw: Record<string, any>) {
  const isDuplicateIssue = String(raw.is_duplicate_issue || '').trim();
  return {
    ...raw,
    duplicate_issue_no:
      isDuplicateIssue === '是'
        ? String(raw.duplicate_issue_no || '').trim()
        : '',
    dev_sub_category: normalizeDtsStringListValue(raw.dev_sub_category),
    dev_control_points: normalizeDtsStringListValue(raw.dev_control_points),
    dev_non_base_desc: normalizeDtsStringListValue(raw.dev_non_base_desc),
    dev_improvements: normalizeDtsStringListValue(raw.dev_improvements),
    test_miss_reason: normalizeDtsStringListValue(raw.test_miss_reason),
    test_improvements: normalizeDtsStringListValue(raw.test_improvements),
  };
}

function createDtsFormSchemaFromConfigs(
  fields: DtsFormFieldConfig[],
): VbenFormSchema[] {
  return fields.map((field) => {
    const schema: VbenFormSchema = {
      component: field.component,
      fieldName: field.fieldName,
      label: field.label,
      componentProps: {
        placeholder: field.placeholder,
      },
    };

    if (field.component === 'ApiSelect' && field.dictKey) {
      schema.componentProps = {
        ...createDtsDictApiSelectProps(
          field.dictKey,
          field.dictKey === 'yes_no' ? YES_NO_OPTIONS : [],
        ),
        placeholder: field.placeholder,
        ...(field.multiple
          ? {
              multiple: true,
              collapseTags: true,
              collapseTagsTooltip: true,
            }
          : {}),
      };
    }

    if (field.component === 'Textarea') {
      schema.componentProps = {
        placeholder: field.placeholder,
        rows: field.rows || 3,
      };
    }

    return schema;
  });
}

export function useQaFormSchema(): VbenFormSchema[] {
  return createDtsFormSchemaFromConfigs(DTS_QA_FORM_FIELDS);
}

export function useDevFormSchema(): VbenFormSchema[] {
  return createDtsFormSchemaFromConfigs(DTS_DEV_FORM_FIELDS);
}

export function useTestFormSchema(): VbenFormSchema[] {
  return createDtsFormSchemaFromConfigs(DTS_TEST_FORM_FIELDS);
}
