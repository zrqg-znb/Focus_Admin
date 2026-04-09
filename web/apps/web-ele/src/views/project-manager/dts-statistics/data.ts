import type { VbenFormSchema } from '#/adapter/form';
import type { PlGroup } from '#/api/core/pl';
import type {
  DtsDictOptions,
  DtsMergedDefect,
} from '#/api/project-manager/dts-statistics';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { getAllPlApi } from '#/api/core/pl';
import { getDtsDictOptions } from '#/api/project-manager/dts-statistics';

type Columns = ZqTableGridOptions<DtsMergedDefect>['columns'];

const YES_NO_OPTIONS = [
  { label: '是', value: '是' },
  { label: '否', value: '否' },
];

type SelectOption = { label: string; value: string };

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
    qa_category: normalizeSelectOptions(safeBundle.qa_category),
    process_quality_type: normalizeSelectOptions(
      safeBundle.process_quality_type,
    ),
    dev_sub_category: normalizeSelectOptions(safeBundle.dev_sub_category),
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
  | 'dev_non_base_desc'
  | 'dev_status'
  | 'dev_sub_category'
  | 'is_dev_analyzed'
  | 'is_downstream'
  | 'is_test_analyzed'
  | 'need_dev_analyze'
  | 'need_test_analyze'
  | 'process_quality_type'
  | 'qa_category'
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
    case 'dev_non_base_desc': {
      return safeOptions.dev_non_base_desc;
    }
    case 'dev_status': {
      return safeOptions.action_status;
    }
    case 'dev_sub_category': {
      return safeOptions.dev_sub_category;
    }
    case 'is_dev_analyzed':
    case 'is_downstream':
    case 'is_test_analyzed':
    case 'need_dev_analyze':
    case 'need_test_analyze': {
      return safeOptions.yes_no.length > 0
        ? safeOptions.yes_no
        : YES_NO_OPTIONS;
    }
    case 'process_quality_type': {
      return safeOptions.process_quality_type;
    }
    case 'qa_category': {
      return safeOptions.qa_category;
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
    field === 'is_downstream' ||
    field === 'need_dev_analyze' ||
    field === 'need_test_analyze' ||
    field === 'is_dev_analyzed' ||
    field === 'is_test_analyzed'
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
  field: 'dev_sub_category' | 'test_miss_reason',
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
      key: 'sDeptOneNoName',
      dataKey: 'sDeptOneNoName',
      title: '提出方部门',
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
          key: 'qa_category',
          dataKey: 'qa_category',
          title: 'QA大类',
          width: 140,
        },
        {
          key: 'pl_group_name',
          dataKey: 'pl_group_name',
          title: '责任PL组',
          width: 160,
        },
        {
          key: 'is_downstream',
          dataKey: 'is_downstream',
          title: '是否下游',
          width: 110,
        },
        {
          key: 'process_quality_type',
          dataKey: 'process_quality_type',
          title: '过程质量分类',
          minWidth: 160,
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
          key: 'dev_owner_name',
          dataKey: 'dev_owner_name',
          title: '开发责任人',
          width: 140,
        },
        {
          key: 'test_owner_name',
          dataKey: 'test_owner_name',
          title: '测试责任人',
          width: 140,
        },
        {
          key: 'is_dev_analyzed',
          dataKey: 'is_dev_analyzed',
          title: '开发分析完成',
          width: 140,
        },
        {
          key: 'is_test_analyzed',
          dataKey: 'is_test_analyzed',
          title: '测试分析完成',
          width: 140,
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
      ],
    },
    {
      key: 'test_group',
      title: '测试填报',
      children: [
        {
          key: 'test_feature',
          dataKey: 'test_feature',
          title: '特效/功能',
          width: 160,
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

async function fetchPlGroups(): Promise<PlGroup[]> {
  const items = await getAllPlApi();
  return (items || []).filter((item) => item.status);
}

export function useQaFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'ApiSelect',
      fieldName: 'qa_category',
      label: '问题大类',
      componentProps: {
        ...createDtsDictApiSelectProps('qa_category'),
        placeholder: '请选择问题大类',
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'pl_group_id',
      label: '责任PL组',
      componentProps: {
        api: fetchPlGroups,
        labelField: 'name',
        valueField: 'id',
        showSearch: true,
        optionFilterProp: 'label',
        placeholder: '请选择责任PL组',
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'is_downstream',
      label: '是否下游问题',
      componentProps: {
        ...createDtsDictApiSelectProps('yes_no', YES_NO_OPTIONS),
        placeholder: '请选择',
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'process_quality_type',
      label: '过程质量分类',
      componentProps: {
        ...createDtsDictApiSelectProps('process_quality_type'),
        placeholder: '请选择过程质量分类',
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'need_dev_analyze',
      label: '需开发分析',
      componentProps: {
        ...createDtsDictApiSelectProps('yes_no', YES_NO_OPTIONS),
        placeholder: '请选择',
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'need_test_analyze',
      label: '需测试分析',
      componentProps: {
        ...createDtsDictApiSelectProps('yes_no', YES_NO_OPTIONS),
        placeholder: '请选择',
      },
    },
    {
      component: 'UserSelector',
      fieldName: 'dev_owner_id',
      label: '开发责任人',
      componentProps: {
        placeholder: '请选择开发责任人',
      },
    },
    {
      component: 'UserSelector',
      fieldName: 'test_owner_id',
      label: '测试责任人',
      componentProps: {
        placeholder: '请选择测试责任人',
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'is_dev_analyzed',
      label: '开发分析完成',
      componentProps: {
        ...createDtsDictApiSelectProps('yes_no', YES_NO_OPTIONS),
        placeholder: '请选择',
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'is_test_analyzed',
      label: '测试分析完成',
      componentProps: {
        ...createDtsDictApiSelectProps('yes_no', YES_NO_OPTIONS),
        placeholder: '请选择',
      },
    },
    {
      component: 'Textarea',
      fieldName: 'qa_remark',
      label: '备注',
      componentProps: {
        placeholder: '请输入备注',
        rows: 3,
      },
    },
  ];
}

export function useDevFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'ApiSelect',
      fieldName: 'dev_sub_category',
      label: '问题小类',
      componentProps: {
        ...createDtsDictApiSelectProps('dev_sub_category'),
        multiple: true,
        collapseTags: true,
        collapseTagsTooltip: true,
        placeholder: '请选择问题小类（可多选）',
      },
    },
    {
      component: 'Textarea',
      fieldName: 'dev_reason',
      label: '问题原因',
      componentProps: {
        placeholder: '请输入问题原因',
        rows: 3,
      },
    },
    {
      component: 'Textarea',
      fieldName: 'dev_intro_reason',
      label: '引入原因',
      componentProps: {
        placeholder: '请输入引入原因',
        rows: 3,
      },
    },
    {
      component: 'Textarea',
      fieldName: 'dev_improvements',
      label: '改进措施(开发)',
      componentProps: {
        placeholder: '一行一条（保存时自动拆分）',
        rows: 3,
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'dev_non_base_desc',
      label: '非底软说明',
      componentProps: {
        ...createDtsDictApiSelectProps('dev_non_base_desc'),
        multiple: true,
        collapseTags: true,
        collapseTagsTooltip: true,
        placeholder: '请选择非底软问题说明（可多选）',
      },
    },
    {
      component: 'Input',
      fieldName: 'dev_asset_link',
      label: '落地资产链接(开发)',
      componentProps: {
        placeholder: '请输入链接',
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'dev_status',
      label: '改进状态(开发)',
      componentProps: {
        ...createDtsDictApiSelectProps('action_status'),
        placeholder: '请选择改进状态',
      },
    },
  ];
}

export function useTestFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'test_feature',
      label: '特效/功能',
      componentProps: {
        placeholder: '请输入特效/功能',
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'test_miss_reason',
      label: '漏测原因',
      componentProps: {
        ...createDtsDictApiSelectProps('test_miss_reason'),
        multiple: true,
        collapseTags: true,
        collapseTagsTooltip: true,
        placeholder: '请选择漏测原因（可多选）',
      },
    },
    {
      component: 'Textarea',
      fieldName: 'test_standard_desc',
      label: '规范问题描述',
      componentProps: {
        placeholder: '请输入规范问题描述',
        rows: 3,
      },
    },
    {
      component: 'Textarea',
      fieldName: 'test_improvements',
      label: '改进措施(测试)',
      componentProps: {
        placeholder: '一行一条（保存时自动拆分）',
        rows: 3,
      },
    },
    {
      component: 'Textarea',
      fieldName: 'test_non_test_desc',
      label: '非测试说明',
      componentProps: {
        placeholder: '请输入非测试问题说明',
        rows: 2,
      },
    },
    {
      component: 'Input',
      fieldName: 'test_asset_link',
      label: '落地资产链接(测试)',
      componentProps: {
        placeholder: '请输入链接',
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'test_status',
      label: '改进状态(测试)',
      componentProps: {
        ...createDtsDictApiSelectProps('action_status'),
        placeholder: '请选择改进状态',
      },
    },
  ];
}

export function normalizeProjectOptions(items: ProjectOut[]) {
  return (items || [])
    .map((item) => ({
      ...item,
      di_teams: Array.isArray(item.di_teams) ? item.di_teams : [],
      version_c: (item as any).version_c as string | undefined,
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}
