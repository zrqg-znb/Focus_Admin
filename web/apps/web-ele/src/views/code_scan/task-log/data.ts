import type { ScanTaskItem } from '#/api/code_scan';
import type { ZqTableGridOptions } from '#/components/zq-table';

export interface CodeScanTaskLogRow extends ScanTaskItem {
  project_name: string;
}

export const TOOL_OPTIONS = [
  'tscan',
  'tsan',
  'cppcheck',
  'weggli',
  'cooddy',
  'binexplorer',
  'clang-tidy',
  'valgrind',
];

export const STATUS_OPTIONS = [
  { label: '等待中', value: 'pending' },
  { label: '解析中', value: 'processing' },
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' },
];

function withCenterAlign(columns: Record<string, any>[]) {
  return columns.map((column) => ({
    align: 'center',
    headerAlign: 'center',
    ...column,
  }));
}

export function useColumns(): ZqTableGridOptions<CodeScanTaskLogRow>['columns'] {
  return withCenterAlign([
    {
      key: 'project_name',
      dataKey: 'project_name',
      title: '项目名称',
      minWidth: 180,
      fixed: true,
    },
    {
      key: 'tool_name',
      dataKey: 'tool_name',
      title: '工具',
      width: 120,
    },
    {
      key: 'status',
      dataKey: 'status',
      title: '状态',
      width: 110,
    },
    {
      key: 'scan_time',
      dataKey: 'scan_time',
      title: '扫描时间',
      width: 180,
    },
    {
      key: 'processed_time',
      dataKey: 'processed_time',
      title: '完成时间',
      width: 180,
    },
    {
      key: 'report_file',
      dataKey: 'report_file',
      title: '报告文件',
      minWidth: 280,
    },
    {
      key: 'log',
      dataKey: 'log',
      title: '解析日志',
      minWidth: 320,
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 120,
      fixed: 'right',
      showOverflowTooltip: false,
    },
  ]) as ZqTableGridOptions<CodeScanTaskLogRow>['columns'];
}
