import type { ShieldApplicationItem } from '#/api/code_scan';
import type { ZqTableGridOptions } from '#/components/zq-table';

function withCenterAlign(columns: Record<string, any>[]) {
  return columns.map((column) => ({
    align: 'center',
    headerAlign: 'center',
    ...column,
  }));
}

export function useColumns(): ZqTableGridOptions<ShieldApplicationItem>['columns'] {
  return withCenterAlign([
    {
      type: 'selection',
      width: 60,
      fixed: 'left',
    },
    {
      type: 'index',
      width: 60,
      fixed: 'left',
      label: '#',
    },
    {
      key: 'applicant_name',
      dataKey: 'applicant_name',
      title: '申请人',
      width: 100,
    },
    {
      key: 'tool_name',
      dataKey: 'tool_name',
      title: '工具',
      width: 100,
    },
    {
      key: 'severity',
      dataKey: 'severity',
      title: '严重程度',
      width: 100,
    },
    {
      key: 'file_path',
      dataKey: 'file_path',
      title: '文件路径',
      minWidth: 220,
    },
    {
      key: 'defect_description',
      dataKey: 'defect_description',
      title: '缺陷描述',
      minWidth: 220,
    },
    {
      key: 'reason',
      dataKey: 'reason',
      title: '申请理由',
      minWidth: 220,
    },
    {
      key: 'status',
      dataKey: 'status',
      title: '状态',
      width: 100,
    },
    {
      key: 'sys_create_datetime',
      dataKey: 'sys_create_datetime',
      title: '申请时间',
      width: 180,
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 150,
      fixed: 'right',
      showOverflowTooltip: false,
    },
  ]) as ZqTableGridOptions<ShieldApplicationItem>['columns'];
}
