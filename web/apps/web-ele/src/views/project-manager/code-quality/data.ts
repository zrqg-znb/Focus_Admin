import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';

const THRESHOLDS = {
  CLEAN_CODE_ACHIEVE_RATE: 1, // 100%
  CODE_DUPLICATION_RATE: 2.5, // 2.5%
};

export const QUALITY_METRIC_COLUMNS = [
  { key: 'UT_branch_coverage', title: 'UT分支覆盖率' },
  { key: 'UT_line_coverage', title: 'UT行覆盖率' },
  { key: 'UT_file_coverage', title: 'UT文件覆盖率' },
  { key: 'UT_function_coverage', title: 'UT函数覆盖率' },
  { key: 'UT_mcdc_coverage', title: 'UT MCDC覆盖率' },
  { key: 'cmetrics_pass_rate', title: 'Cmetrics通过率' },
  { key: 'code_size', title: '代码规模' },
  { key: 'code_duplication_ratio', title: '代码重复率' },
  { key: 'lines_per_file', title: '平均每文件行数' },
  { key: 'line_per_method', title: '平均每函数行数' },
  { key: 'misra_delay_num', title: 'MISRA遗留问题数' },
  { key: 'misra_dismiss_num', title: 'MISRA豁免问题数' },
  { key: 'huge_headerfile_ratio', title: '超大头文件占比' },
  { key: 'redundant_code_kloc', title: '冗余代码KLOC' },
  { key: 'redundant_code_total', title: '冗余代码总量' },
  { key: 'safety_defect_density', title: '安全缺陷密度' },
] as const;

export type QualityMetricKey = (typeof QUALITY_METRIC_COLUMNS)[number]['key'];

export function getMetricFieldName(key: QualityMetricKey) {
  return `metric_${key}`;
}

export interface CodeQualityOverviewRow {
  project_id: string;
  project_name: string;
  project_domain: string;
  project_type: string;
  project_managers: string;
  record_date: string;
  oem_name: string;
  module_count: number;
  clean_code_pass_modules: number;
  total_node_count: number;
  warning_node_count: number;
  warning_count: number;
  clean_code_achieve_rate: number;
  avg_duplication_rate: number;
  total_loc: number;
  warning_metrics_text: string;
  unachieved_clean_code_text: string;
  metric_warning_map: Record<string, boolean>;
  [key: string]: any;
}

export interface CodeQualityTreeRow {
  id: string;
  module_id: string;
  node_key: string;
  owner_editable: boolean;
  owner_ids: string[];
  row_type: 'module' | 'node';
  node_name: string;
  oem_name: string;
  module: string;
  owner_names_text: string;
  record_date: string;
  clean_code_rate: number;
  warning_count: number;
  warning_node_count: number;
  total_node_count: number;
  unachieved_clean_code_text: string;
  warning_metrics_text: string;
  metric_warning_map: Record<string, boolean>;
  children?: CodeQualityTreeRow[];
  [key: string]: any;
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

export function useSummaryColumns(): VxeTableGridOptions<CodeQualityOverviewRow>['columns'] {
  return [
    { type: 'seq', width: 60, fixed: 'left' },
    {
      field: 'project_name',
      title: '项目名',
      minWidth: 180,
      fixed: 'left',
      slots: { default: 'name_slot' },
    },
    { field: 'oem_name', title: 'OEMName', minWidth: 140, fixed: 'left' },
    { field: 'project_managers', title: '项目经理', minWidth: 150 },
    { field: 'record_date', title: '更新日期', minWidth: 120 },
    {
      field: 'clean_code_achieve_rate',
      title: 'CleanCode达成率',
      minWidth: 140,
      slots: { default: 'clean_code_achieve_rate_slot' },
      formatter: ({ cellValue }) =>
        `${((Number(cellValue) || 0) * 100).toFixed(2)}%`,
      className: ({ row }) =>
        Number(row.clean_code_achieve_rate || 0) <
        THRESHOLDS.CLEAN_CODE_ACHIEVE_RATE
          ? 'text-red-500 font-bold'
          : 'text-green-600 font-bold',
    },
    {
      field: 'avg_duplication_rate',
      title: '平均重复率',
      minWidth: 120,
      formatter: ({ cellValue }) => `${cellValue}%`,
      className: ({ row }) =>
        Number(row.avg_duplication_rate || 0) > THRESHOLDS.CODE_DUPLICATION_RATE
          ? 'text-red-500 font-bold'
          : '',
    },
    {
      field: 'total_loc',
      title: '总代码规模',
      minWidth: 120,
      formatter: ({ cellValue }) =>
        `${Number(cellValue || 0).toLocaleString()}`,
    },
    ...QUALITY_METRIC_COLUMNS.map((metric) => ({
      field: getMetricFieldName(metric.key),
      title: metric.title,
      minWidth: 140,
      className: ({ row }: { row: CodeQualityOverviewRow }) =>
        row.metric_warning_map?.[metric.key] ? 'text-red-500 font-bold' : '',
      showOverflow: true,
    })),
  ];
}

export function useDetailSearchFormSchema(): VbenFormSchema[] {
  return [
    { component: 'Input', fieldName: 'keyword', label: '关键词' },
    { component: 'Input', fieldName: 'oem_name', label: 'OEMName' },
    { component: 'Input', fieldName: 'module', label: '模块名' },
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

export function useDetailColumns(): VxeTableGridOptions<CodeQualityTreeRow>['columns'] {
  return [
    {
      field: 'node_name',
      title: '树节点',
      treeNode: true,
      minWidth: 240,
      fixed: 'left',
    },
    { field: 'oem_name', title: 'OEMName', minWidth: 140, fixed: 'left' },
    {
      field: 'owner_names_text',
      title: '责任人',
      minWidth: 220,
      slots: { default: 'owner_editor_slot' },
    },
    { field: 'record_date', title: '更新日期', width: 120 },
    {
      field: 'clean_code_rate',
      title: 'CleanCode达成率',
      width: 140,
      slots: { default: 'clean_code_rate_slot' },
      formatter: ({ cellValue }) =>
        `${((Number(cellValue) || 0) * 100).toFixed(2)}%`,
      className: ({ row }) =>
        Number(row.clean_code_rate || 0) < 1
          ? 'text-red-500 font-bold'
          : 'text-green-600 font-bold',
    },
    ...QUALITY_METRIC_COLUMNS.map((metric) => ({
      field: getMetricFieldName(metric.key),
      title: metric.title,
      minWidth: 140,
      className: ({ row }: { row: CodeQualityTreeRow }) =>
        row.metric_warning_map?.[metric.key] ? 'text-red-500 font-bold' : '',
      showOverflow: true,
    })),
  ];
}
