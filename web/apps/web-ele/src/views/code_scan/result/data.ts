import type {
  LatestScanResultItem,
  ProjectOverviewItem,
  ShieldStatus,
} from '#/api/code_scan';
import type { ZqTableGridOptions } from '#/components/zq-table';

export interface ProjectOverviewTableRow extends ProjectOverviewItem {
  [key: string]: null | number | Record<string, number> | string | undefined;
}

export const ALL_SCAN_TOOLS = [
  'tscan',
  'tsan',
  'cppcheck',
  'weggli',
  'cooddy',
  'binexplorer',
  'clang-tidy',
  'valgrind',
];

export const SHIELD_STATUS_OPTIONS: ShieldStatus[] = [
  'Normal',
  'Pending',
  'Shielded',
  'Rejected',
];

function withCenterAlign(columns: Record<string, any>[]) {
  return columns.map((column) => ({
    align: 'center',
    headerAlign: 'center',
    ...column,
  }));
}

function formatCount(cellValue: null | number | undefined) {
  if (cellValue === undefined || cellValue === null) return '未扫描';
  return String(cellValue);
}

export function useSummaryColumns(
  toolNames: string[],
): ZqTableGridOptions<ProjectOverviewTableRow>['columns'] {
  return withCenterAlign([
    {
      key: 'project_name',
      dataKey: 'project_name',
      title: '项目',
      minWidth: 240,
      fixed: true,
    },
    {
      key: 'total',
      dataKey: 'total',
      title: '总问题数',
      width: 100,
      formatter: (row: ProjectOverviewTableRow) => formatCount(row.total),
    },
    ...toolNames.map((name) => ({
      key: name,
      dataKey: name,
      title: name,
      width: 120,
      formatter: (row: ProjectOverviewTableRow) =>
        formatCount(row[name] as null | number | undefined),
    })),
    {
      key: 'latest_time',
      dataKey: 'latest_time',
      title: '最新扫描时间',
      width: 180,
    },
  ]) as ZqTableGridOptions<ProjectOverviewTableRow>['columns'];
}

export function useDetailColumns(): ZqTableGridOptions<LatestScanResultItem>['columns'] {
  return withCenterAlign([
    {
      type: 'selection',
      width: 60,
      fixed: 'left',
    },
    {
      type: 'expand',
      width: 60,
      fixed: 'left',
      slots: { default: 'expand_content' },
    },
    {
      key: 'tool_name',
      dataKey: 'tool_name',
      title: '工具',
      width: 100,
    },
    {
      key: 'sub_module',
      dataKey: 'sub_module',
      title: '子模块',
      width: 140,
      formatter: (row: LatestScanResultItem) => row.sub_module || '-',
    },
    {
      key: 'severity',
      dataKey: 'severity',
      title: '严重程度',
      width: 100,
    },
    {
      key: 'defect_type',
      dataKey: 'defect_type',
      title: '缺陷类型',
      width: 150,
    },
    {
      key: 'file_path',
      dataKey: 'file_path',
      title: '文件路径',
      minWidth: 220,
    },
    {
      key: 'line_number',
      dataKey: 'line_number',
      title: '行号',
      width: 80,
    },
    {
      key: 'description',
      dataKey: 'description',
      title: '缺陷描述',
      minWidth: 320,
    },
    {
      key: 'shield_status',
      dataKey: 'shield_status',
      title: '状态',
      columnKey: 'shield_status',
      filterMultiple: false,
      filters: SHIELD_STATUS_OPTIONS.map((status) => ({
        text: status,
        value: status,
      })),
      width: 120,
    },
  ]) as ZqTableGridOptions<LatestScanResultItem>['columns'];
}
