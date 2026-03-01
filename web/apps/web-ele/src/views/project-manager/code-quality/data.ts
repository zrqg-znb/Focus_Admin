import type { VbenFormSchema } from '#/adapter/form';
import type { ZqTableGridOptions } from '#/components/zq-table';

type MetricCategory = 'code_scan' | 'unit_test';
type ThresholdValueType = 'number' | 'ratio_percent';

export type ThresholdComparator = 'gt' | 'gte' | 'lt' | 'lte';

export interface QualityMetricColumnMeta {
  category: MetricCategory;
  definition: string;
  formula: string;
  key: string;
  thresholdComparator: ThresholdComparator;
  thresholdEnabled: boolean;
  thresholdUnit: string;
  thresholdValue: number;
  thresholdValueType: ThresholdValueType;
  title: string;
}

export const QUALITY_METRIC_COLUMNS = [
  {
    category: 'unit_test',
    definition: '单元测试分支覆盖率，用于评估分支路径测试完整性。',
    formula: 'UT分支覆盖率 = 已覆盖分支数 ÷ 分支总数 × 100%',
    key: 'UT_branch_coverage',
    thresholdComparator: 'lt',
    thresholdEnabled: true,
    thresholdUnit: '%',
    thresholdValue: 90,
    thresholdValueType: 'number',
    title: 'UT分支覆盖率',
  },
  {
    category: 'unit_test',
    definition: '单元测试行覆盖率，用于评估代码行测试覆盖程度。',
    formula: 'UT行覆盖率 = 已覆盖代码行数 ÷ 代码总行数 × 100%',
    key: 'UT_line_coverage',
    thresholdComparator: 'lt',
    thresholdEnabled: true,
    thresholdUnit: '%',
    thresholdValue: 90,
    thresholdValueType: 'number',
    title: 'UT行覆盖率',
  },
  {
    category: 'unit_test',
    definition: '单元测试文件覆盖率，用于评估文件级覆盖完整性。',
    formula: 'UT文件覆盖率 = 已覆盖文件数 ÷ 文件总数 × 100%',
    key: 'UT_file_coverage',
    thresholdComparator: 'lt',
    thresholdEnabled: true,
    thresholdUnit: '%',
    thresholdValue: 90,
    thresholdValueType: 'number',
    title: 'UT文件覆盖率',
  },
  {
    category: 'unit_test',
    definition: '单元测试函数覆盖率，用于评估函数级覆盖质量。',
    formula: 'UT函数覆盖率 = 已覆盖函数数 ÷ 函数总数 × 100%',
    key: 'UT_function_coverage',
    thresholdComparator: 'lt',
    thresholdEnabled: true,
    thresholdUnit: '%',
    thresholdValue: 90,
    thresholdValueType: 'number',
    title: 'UT函数覆盖率',
  },
  {
    category: 'unit_test',
    definition: 'MCDC覆盖率，用于评估条件判定组合覆盖充分性。',
    formula: 'UT MCDC覆盖率 = 已覆盖判定组合数 ÷ 判定组合总数 × 100%',
    key: 'UT_mcdc_coverage',
    thresholdComparator: 'lt',
    thresholdEnabled: true,
    thresholdUnit: '%',
    thresholdValue: 85,
    thresholdValueType: 'number',
    title: 'UT MCDC覆盖率',
  },
  {
    category: 'code_scan',
    definition: '代码规范检查通过率，衡量规则检查通过情况。',
    formula: 'Cmetrics通过率 = 通过检查项数 ÷ 检查总项数 × 100%',
    key: 'cmetrics_pass_rate',
    thresholdComparator: 'lt',
    thresholdEnabled: true,
    thresholdUnit: '%',
    thresholdValue: 100,
    thresholdValueType: 'number',
    title: 'Cmetrics通过率',
  },
  {
    category: 'code_scan',
    definition: '代码规模（KLOC）或代码行规模指标，用于衡量代码体量。',
    formula: '代码规模 = 代码总行数（或KLOC）',
    key: 'code_size',
    thresholdComparator: 'gt',
    thresholdEnabled: false,
    thresholdUnit: '',
    thresholdValue: 0,
    thresholdValueType: 'number',
    title: '代码规模',
  },
  {
    category: 'code_scan',
    definition: '代码重复率，用于衡量重复代码占比。',
    formula: '代码重复率 = 重复代码行数 ÷ 代码总行数 × 100%',
    key: 'code_duplication_ratio',
    thresholdComparator: 'gt',
    thresholdEnabled: true,
    thresholdUnit: '%',
    thresholdValue: 2.5,
    thresholdValueType: 'number',
    title: '代码重复率',
  },
  {
    category: 'code_scan',
    definition: '平均每个文件的代码行数，用于评估文件粒度复杂度。',
    formula: '平均每文件行数 = 代码总行数 ÷ 文件总数',
    key: 'lines_per_file',
    thresholdComparator: 'gt',
    thresholdEnabled: false,
    thresholdUnit: '',
    thresholdValue: 0,
    thresholdValueType: 'number',
    title: '平均每文件行数',
  },
  {
    category: 'code_scan',
    definition: '平均每个函数的代码行数，用于评估函数复杂度。',
    formula: '平均每函数行数 = 代码总行数 ÷ 函数总数',
    key: 'line_per_method',
    thresholdComparator: 'gt',
    thresholdEnabled: false,
    thresholdUnit: '',
    thresholdValue: 0,
    thresholdValueType: 'number',
    title: '平均每函数行数',
  },
  {
    category: 'code_scan',
    definition: 'MISRA遗留问题数量，用于评估规范风险项存量。',
    formula: 'MISRA遗留问题数 = 当前未关闭问题总数',
    key: 'misra_delay_num',
    thresholdComparator: 'gt',
    thresholdEnabled: true,
    thresholdUnit: '',
    thresholdValue: 0,
    thresholdValueType: 'number',
    title: 'MISRA遗留问题数',
  },
  {
    category: 'code_scan',
    definition: 'MISRA豁免问题数量，用于评估规则豁免规模。',
    formula: 'MISRA豁免问题数 = 当前豁免问题总数',
    key: 'misra_dismiss_num',
    thresholdComparator: 'gt',
    thresholdEnabled: false,
    thresholdUnit: '',
    thresholdValue: 0,
    thresholdValueType: 'number',
    title: 'MISRA豁免问题数',
  },
  {
    category: 'code_scan',
    definition: '超大头文件占比，用于衡量头文件规模分布风险。',
    formula: '超大头文件占比 = 超阈值头文件数 ÷ 头文件总数 × 100%',
    key: 'huge_headerfile_ratio',
    thresholdComparator: 'gt',
    thresholdEnabled: true,
    thresholdUnit: '%',
    thresholdValue: 1,
    thresholdValueType: 'number',
    title: '超大头文件占比',
  },
  {
    category: 'code_scan',
    definition: '冗余代码千行数，用于衡量冗余体量。',
    formula: '冗余代码KLOC = 冗余代码行数 ÷ 1000',
    key: 'redundant_code_kloc',
    thresholdComparator: 'gt',
    thresholdEnabled: true,
    thresholdUnit: '',
    thresholdValue: 0,
    thresholdValueType: 'number',
    title: '冗余代码KLOC',
  },
  {
    category: 'code_scan',
    definition: '冗余代码总量，用于衡量重复/冗余代码绝对规模。',
    formula: '冗余代码总量 = 冗余代码条目总数',
    key: 'redundant_code_total',
    thresholdComparator: 'gt',
    thresholdEnabled: true,
    thresholdUnit: '',
    thresholdValue: 0,
    thresholdValueType: 'number',
    title: '冗余代码总量',
  },
  {
    category: 'code_scan',
    definition: '安全缺陷密度，用于评估每单位代码的安全风险。',
    formula: '安全缺陷密度 = 安全缺陷数量 ÷ KLOC',
    key: 'safety_defect_density',
    thresholdComparator: 'gt',
    thresholdEnabled: true,
    thresholdUnit: '',
    thresholdValue: 0,
    thresholdValueType: 'number',
    title: '安全缺陷密度',
  },
] as const satisfies readonly QualityMetricColumnMeta[];

export type QualityMetricKey = (typeof QUALITY_METRIC_COLUMNS)[number]['key'];

export type QualityThresholdKey =
  | 'avg_duplication_rate'
  | 'clean_code_achieve_rate'
  | 'clean_code_rate'
  | QualityMetricKey;

export interface QualityThresholdConfigItem {
  comparator: ThresholdComparator;
  enabled: boolean;
  value: number;
}

export type QualityThresholdConfig = Record<
  QualityThresholdKey,
  QualityThresholdConfigItem
>;

export interface CodeQualityOverviewRow {
  avg_duplication_rate: number;
  clean_code_achieve_rate: number;
  clean_code_pass_modules: number;
  metric_num_map: Record<string, null | number>;
  metric_warning_map: Record<string, boolean>;
  module_count: number;
  oem_name: string;
  project_domain: string;
  project_id: string;
  project_managers: string;
  project_name: string;
  project_type: string;
  record_date: string;
  total_loc: number;
  total_node_count: number;
  unachieved_clean_code_text: string;
  warning_count: number;
  warning_metrics_text: string;
  warning_node_count: number;
  [key: string]: any;
}

export interface CodeQualityTreeRow {
  children?: CodeQualityTreeRow[];
  clean_code_rate: number;
  id: string;
  metric_num_map: Record<string, null | number>;
  metric_warning_map: Record<string, boolean>;
  module: string;
  module_id: string;
  node_key: string;
  node_name: string;
  oem_name: string;
  owner_editable: boolean;
  owner_ids: string[];
  owner_names_text: string;
  record_date: string;
  row_type: 'module' | 'node';
  total_node_count: number;
  unachieved_clean_code_text: string;
  warning_count: number;
  warning_metrics_text: string;
  warning_node_count: number;
  [key: string]: any;
}

const METRIC_META_MAP = new Map<QualityMetricKey, QualityMetricColumnMeta>(
  QUALITY_METRIC_COLUMNS.map((item) => [item.key as QualityMetricKey, item]),
);

const THRESHOLD_META_LIST: Array<{
  comparator: ThresholdComparator;
  defaultValue: number;
  enabled: boolean;
  key: QualityThresholdKey;
  valueType: ThresholdValueType;
}> = [
  {
    comparator: 'lt',
    defaultValue: 100,
    enabled: true,
    key: 'clean_code_achieve_rate',
    valueType: 'ratio_percent',
  },
  {
    comparator: 'lt',
    defaultValue: 100,
    enabled: true,
    key: 'clean_code_rate',
    valueType: 'ratio_percent',
  },
  {
    comparator: 'gt',
    defaultValue: 2.5,
    enabled: true,
    key: 'avg_duplication_rate',
    valueType: 'number',
  },
  ...QUALITY_METRIC_COLUMNS.map((item) => ({
    comparator: item.thresholdComparator,
    defaultValue: item.thresholdValue,
    enabled: item.thresholdEnabled,
    key: item.key as QualityThresholdKey,
    valueType: item.thresholdValueType,
  })),
];

const THRESHOLD_META_MAP = new Map<
  QualityThresholdKey,
  (typeof THRESHOLD_META_LIST)[number]
>(THRESHOLD_META_LIST.map((item) => [item.key, item]));

const WARNING_CLASS = 'text-red-500 font-semibold';

function compareByComparator(
  comparator: ThresholdComparator,
  left: number,
  right: number,
) {
  if (comparator === 'gt') return left > right;
  if (comparator === 'gte') return left >= right;
  if (comparator === 'lt') return left < right;
  return left <= right;
}

function toNumber(value: any): null | number {
  if (value === null || value === undefined) return null;
  if (typeof value === 'number') {
    return Number.isNaN(value) ? null : value;
  }
  if (typeof value === 'string') {
    const text = value.trim();
    if (!text) return null;
    const normalized = text.replaceAll(',', '').replaceAll('%', '');
    const parsed = Number(normalized);
    return Number.isNaN(parsed) ? null : parsed;
  }
  return null;
}

function getThresholdValue(
  row: CodeQualityOverviewRow | CodeQualityTreeRow,
  key: QualityThresholdKey,
) {
  if (key === 'clean_code_achieve_rate' || key === 'clean_code_rate') {
    return toNumber((row as any)[key]);
  }
  if (key === 'avg_duplication_rate') {
    return toNumber((row as any).avg_duplication_rate);
  }

  const numMap = (row as any).metric_num_map as Record<string, null | number>;
  const numeric = toNumber(numMap?.[key]);
  if (numeric !== null) return numeric;
  return toNumber((row as any)[getMetricFieldName(key as QualityMetricKey)]);
}

function withCenterAlign(columns: Record<string, any>[]): any[] {
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

export function getMetricFieldName(key: QualityMetricKey) {
  return `metric_${key}`;
}

export function createDefaultThresholdConfig(): QualityThresholdConfig {
  const config = {} as QualityThresholdConfig;
  for (const item of THRESHOLD_META_LIST) {
    config[item.key] = {
      comparator: item.comparator,
      enabled: item.enabled,
      value: item.defaultValue,
    };
  }
  return config;
}

export const QUALITY_THRESHOLD_CONFIG: QualityThresholdConfig = {
  ...createDefaultThresholdConfig(),
  avg_duplication_rate: {
    comparator: 'gt',
    enabled: true,
    value: 2.5,
  },
  clean_code_achieve_rate: {
    comparator: 'lt',
    enabled: true,
    value: 100,
  },
  clean_code_rate: {
    comparator: 'lt',
    enabled: true,
    value: 100,
  },
  code_duplication_ratio: {
    comparator: 'gt',
    enabled: true,
    value: 2.5,
  },
  huge_headerfile_ratio: {
    comparator: 'gt',
    enabled: true,
    value: 1,
  },
  misra_delay_num: {
    comparator: 'gt',
    enabled: true,
    value: 0,
  },
  redundant_code_kloc: {
    comparator: 'gt',
    enabled: true,
    value: 0,
  },
  redundant_code_total: {
    comparator: 'gt',
    enabled: true,
    value: 0,
  },
  safety_defect_density: {
    comparator: 'gt',
    enabled: true,
    value: 0,
  },
};

export function loadQualityThresholdConfig(): QualityThresholdConfig {
  const config = {} as QualityThresholdConfig;
  for (const [key, item] of Object.entries(QUALITY_THRESHOLD_CONFIG)) {
    config[key as QualityThresholdKey] = {
      comparator: item.comparator,
      enabled: item.enabled,
      value: item.value,
    };
  }
  return config;
}

export function saveQualityThresholdConfig(_config: QualityThresholdConfig) {}

export function isThresholdExceeded(
  row: CodeQualityOverviewRow | CodeQualityTreeRow,
  key: QualityThresholdKey,
  config: QualityThresholdConfig,
) {
  const threshold = config[key];
  if (!threshold?.enabled) return false;
  const meta = THRESHOLD_META_MAP.get(key);
  if (!meta) return false;

  const rawValue = getThresholdValue(row, key);
  if (rawValue === null) return false;

  const comparableValue =
    meta.valueType === 'ratio_percent' ? rawValue * 100 : rawValue;
  return compareByComparator(
    threshold.comparator,
    comparableValue,
    Number(threshold.value || 0),
  );
}

export function getMetricWarningClass(
  row: CodeQualityOverviewRow | CodeQualityTreeRow,
  key: QualityMetricKey,
  config: QualityThresholdConfig,
) {
  const backendWarning = Boolean(row.metric_warning_map?.[key]);
  const thresholdWarning = isThresholdExceeded(
    row,
    key as QualityThresholdKey,
    config,
  );
  return backendWarning || thresholdWarning ? WARNING_CLASS : '';
}

function getMetricKeyFromFieldName(fieldName: string): null | QualityMetricKey {
  if (!fieldName.startsWith('metric_')) {
    return null;
  }
  const key = fieldName.replace(/^metric_/, '') as QualityMetricKey;
  return METRIC_META_MAP.has(key) ? key : null;
}

export function getThresholdCellClassName(
  row: CodeQualityOverviewRow | CodeQualityTreeRow,
  fieldName: string,
  config: QualityThresholdConfig,
) {
  if (fieldName === 'clean_code_achieve_rate' || fieldName === 'clean_code_rate') {
    return isThresholdExceeded(row, fieldName, config)
      ? WARNING_CLASS
      : 'text-green-600 font-semibold';
  }
  if (fieldName === 'avg_duplication_rate') {
    return isThresholdExceeded(row, 'avg_duplication_rate', config)
      ? WARNING_CLASS
      : '';
  }
  const metricKey = getMetricKeyFromFieldName(fieldName);
  if (!metricKey) return '';
  return getMetricWarningClass(row, metricKey, config);
}

export function createThresholdCellClassName(
  getThresholdConfig: () => QualityThresholdConfig,
) {
  return ({
    row,
    column,
  }: {
    column: { prop?: string; property?: string };
    row: CodeQualityOverviewRow | CodeQualityTreeRow;
  }) => {
    const fieldName = String(column?.property || column?.prop || '');
    if (!fieldName) return '';
    return getThresholdCellClassName(row, fieldName, getThresholdConfig());
  };
}

export function getOverviewColumns(): ZqTableGridOptions<CodeQualityOverviewRow>['columns'] {
  const unitTestColumns = QUALITY_METRIC_COLUMNS.filter(
    (item) => item.category === 'unit_test',
  ).map((metric) => ({
    dataKey: getMetricFieldName(metric.key as QualityMetricKey),
    headerHelp: {
      definition: metric.definition,
      formula: metric.formula,
    },
    key: getMetricFieldName(metric.key as QualityMetricKey),
    title: metric.title,
    width: 150,
  }));

  const codeScanColumns = QUALITY_METRIC_COLUMNS.filter(
    (item) => item.category === 'code_scan',
  ).map((metric) => ({
    dataKey: getMetricFieldName(metric.key as QualityMetricKey),
    headerHelp: {
      definition: metric.definition,
      formula: metric.formula,
    },
    key: getMetricFieldName(metric.key as QualityMetricKey),
    title: metric.title,
    width: 150,
  }));

  return withCenterAlign([
    {
      dataKey: 'project_name',
      fixed: true,
      headerHelp: {
        definition: '项目名称，点击可进入项目代码质量详情。',
      },
      key: 'project_name',
      title: '项目名',
      width: 180,
    },
    {
      dataKey: 'oem_name',
      fixed: true,
      headerHelp: {
        definition: 'OEM配置名称，用于区分项目下不同模块分组。',
      },
      key: 'oem_name',
      title: 'OEMName',
      width: 140,
    },
    {
      dataKey: 'project_managers',
      headerHelp: {
        definition: '项目责任经理信息。',
      },
      key: 'project_managers',
      title: '项目经理',
      width: 150,
    },
    {
      dataKey: 'record_date',
      headerHelp: {
        definition: '当前统计数据对应的记录日期。',
      },
      key: 'record_date',
      title: '更新日期',
      width: 120,
    },
    {
      dataKey: 'clean_code_achieve_rate',
      headerHelp: {
        definition: '项目CleanCode综合达成率。',
        formula: '达成率 = (11 - 未达标项数) ÷ 11 × 100%',
      },
      key: 'clean_code_achieve_rate',
      title: 'CleanCode达成率',
      width: 150,
    },
    {
      dataKey: 'avg_duplication_rate',
      headerHelp: {
        definition: '模块平均代码重复率。',
        formula: '平均重复率 = 模块重复率总和 ÷ 模块数',
      },
      key: 'avg_duplication_rate',
      title: '平均重复率',
      width: 120,
    },
    {
      dataKey: 'total_loc',
      headerHelp: {
        definition: '总代码规模（行数统计）。',
      },
      key: 'total_loc',
      title: '总代码规模',
      width: 130,
    },
    {
      children: unitTestColumns,
      headerHelp: {
        definition: '单元测试覆盖与测试充分性相关指标。',
      },
      key: 'unit_test_metrics',
      title: '单元测试类',
    },
    {
      children: codeScanColumns,
      headerHelp: {
        definition: '静态扫描与规范质量相关指标。',
      },
      key: 'code_scan_metrics',
      title: '代码扫描类',
    },
  ]) as ZqTableGridOptions<CodeQualityOverviewRow>['columns'];
}

export function getDetailColumns(): ZqTableGridOptions<CodeQualityTreeRow>['columns'] {
  const unitTestColumns = QUALITY_METRIC_COLUMNS.filter(
    (item) => item.category === 'unit_test',
  ).map((metric) => ({
    dataKey: getMetricFieldName(metric.key as QualityMetricKey),
    headerHelp: {
      definition: metric.definition,
      formula: metric.formula,
    },
    key: getMetricFieldName(metric.key as QualityMetricKey),
    title: metric.title,
    width: 150,
  }));

  const codeScanColumns = QUALITY_METRIC_COLUMNS.filter(
    (item) => item.category === 'code_scan',
  ).map((metric) => ({
    dataKey: getMetricFieldName(metric.key as QualityMetricKey),
    headerHelp: {
      definition: metric.definition,
      formula: metric.formula,
    },
    key: getMetricFieldName(metric.key as QualityMetricKey),
    title: metric.title,
    width: 150,
  }));

  return withCenterAlign([
    {
      dataKey: 'node_name',
      fixed: true,
      headerAlign: 'left',
      headerHelp: {
        definition: '质量树节点名称，支持展开/折叠查看子节点。',
      },
      key: 'node_name',
      title: '树节点',
      width: 260,
    },
    {
      dataKey: 'oem_name',
      headerHelp: {
        definition: '节点所属OEM分组。',
      },
      key: 'oem_name',
      title: 'OEMName',
      width: 150,
    },
    {
      dataKey: 'owner_names_text',
      headerHelp: {
        definition: '节点责任人，支持右键/点击编辑。',
      },
      key: 'owner_names_text',
      title: '责任人',
      width: 220,
    },
    {
      dataKey: 'record_date',
      headerHelp: {
        definition: '当前节点数据的记录日期。',
      },
      key: 'record_date',
      title: '更新日期',
      width: 120,
    },
    {
      dataKey: 'clean_code_rate',
      headerHelp: {
        definition: '当前节点CleanCode达成率。',
        formula: '达成率 = (11 - 未达标项数) ÷ 11 × 100%',
      },
      key: 'clean_code_rate',
      title: 'CleanCode达成率',
      width: 150,
    },
    {
      children: unitTestColumns,
      headerHelp: {
        definition: '单元测试覆盖与测试充分性相关指标。',
      },
      key: 'unit_test_metrics',
      title: '单元测试类',
    },
    {
      children: codeScanColumns,
      headerHelp: {
        definition: '静态扫描与规范质量相关指标。',
      },
      key: 'code_scan_metrics',
      title: '代码扫描类',
    },
  ]) as ZqTableGridOptions<CodeQualityTreeRow>['columns'];
}

export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    { component: 'Input', fieldName: 'keyword', label: '关键词' },
    { component: 'Input', fieldName: 'oem_name', label: 'OEMName' },
    {
      component: 'DatePicker',
      fieldName: 'date',
      label: '日期',
      componentProps: {
        valueFormat: 'YYYY-MM-DD',
      },
    },
  ];
}

export function useDetailSearchFormSchema(): VbenFormSchema[] {
  return [
    { component: 'Input', fieldName: 'keyword', label: '关键词' },
    { component: 'Input', fieldName: 'oem_name', label: 'OEMName' },
    { component: 'Input', fieldName: 'module', label: '模块名' },
    {
      component: 'DatePicker',
      fieldName: 'date',
      label: '日期',
      componentProps: {
        valueFormat: 'YYYY-MM-DD',
      },
    },
    {
      component: 'Select',
      fieldName: 'warning_only',
      label: '预警筛选',
      componentProps: {
        options: [
          { label: '全部', value: '' },
          { label: '仅预警', value: 'yes' },
          { label: '仅正常', value: 'no' },
        ],
      },
    },
  ];
}

export function getMetricDefinition(key: QualityMetricKey) {
  return METRIC_META_MAP.get(key)?.definition || '';
}
