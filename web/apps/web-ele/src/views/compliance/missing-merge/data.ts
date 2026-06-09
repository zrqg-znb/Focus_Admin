import type { Column } from 'element-plus';

import type { MissingMergeRecordItem } from '#/api/compliance/missing-merge';
import type { ZqTableGridOptions } from '#/components/zq-table';

export const STATUS_OPTIONS = [
  { label: '未处理', type: 'danger', value: 'open' },
  { label: '已补合', type: 'success', value: 'fixed' },
  { label: '已忽略', type: 'info', value: 'ignored' },
] as const;

export function getStatusTagType(status: string) {
  const option = STATUS_OPTIONS.find((item) => item.value === status);
  return option?.type || 'info';
}

export function useMissingMergeColumns(): ZqTableGridOptions<MissingMergeRecordItem>['columns'] {
  const columns: Column<MissingMergeRecordItem>[] = [
    {
      key: 'title',
      dataKey: 'title',
      title: '漏合CR',
      width: 300,
      fixed: true,
      showOverflowTooltip: false,
    },
    {
      key: 'status_label',
      dataKey: 'status_label',
      title: '状态',
      width: 100,
    },
    {
      key: 'repository_name',
      dataKey: 'repository_name',
      title: '代码库',
      width: 180,
    },
    {
      key: 'organization_name',
      dataKey: 'organization_name',
      title: '组织',
      width: 180,
    },
    {
      key: 'trunk_branch',
      dataKey: 'trunk_branch',
      title: '主干分支',
      width: 160,
    },
    {
      key: 'release_branch',
      dataKey: 'release_branch',
      title: '发布分支',
      width: 160,
    },
    {
      key: 'change_key',
      dataKey: 'change_key',
      title: 'Change Key',
      width: 190,
    },
    {
      key: 'author_username',
      dataKey: 'author_username',
      title: '创建人',
      width: 120,
    },
    {
      key: 'author_pl_group_name',
      dataKey: 'author_pl_group_name',
      title: 'PL组',
      width: 160,
    },
    {
      key: 'merged_at',
      dataKey: 'merged_at',
      title: '主干合入时间',
      width: 170,
    },
    {
      key: 'detected_at',
      dataKey: 'detected_at',
      title: '识别时间',
      width: 170,
    },
    {
      key: 'line_changes',
      dataKey: 'line_changes',
      title: '代码行变化',
      width: 120,
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 150,
      fixed: true,
      showOverflowTooltip: false,
    },
  ];

  return columns.map((column) => ({
    align: 'center',
    headerAlign: 'center',
    ...column,
  }));
}
