import type { Column } from 'element-plus';

import type { RepositoryItem } from '#/api/compliance/base';
import type { ZqTableGridOptions } from '#/components/zq-table';

export const DOMAIN_OPTIONS = [
  { label: '座舱', value: 'cockpit' },
  { label: '车控', value: 'vehicle' },
] as const;

export const MODE_OPTIONS = [
  { label: 'CR', value: 'CR' },
  { label: 'MR', value: 'MR' },
] as const;

export const BIND_MODE_OPTIONS = [
  { label: '追加绑定', value: 'append' },
  { label: '替换绑定', value: 'replace' },
] as const;

export function useRepositoryColumns(): ZqTableGridOptions<RepositoryItem>['columns'] {
  const columns: Column<RepositoryItem>[] = [
    {
      key: 'project_name',
      dataKey: 'project_name',
      title: '代码库',
      width: 220,
      fixed: true,
      showOverflowTooltip: false,
    },
    {
      key: 'project_id',
      dataKey: 'project_id',
      title: '代码库ID',
      width: 140,
    },
    {
      key: 'organization_name',
      dataKey: 'organization_name',
      title: '所属组织',
      width: 180,
    },
    {
      key: 'mode_label',
      dataKey: 'mode_label',
      title: '模式',
      width: 90,
    },
    {
      key: 'domain_label',
      dataKey: 'domain_label',
      title: '领域',
      width: 90,
    },
    {
      key: 'repo_type_label',
      dataKey: 'repo_type_label',
      title: '仓库类型',
      width: 130,
    },
    {
      key: 'responsibility_group_names',
      dataKey: 'responsibility_group_names',
      title: '责任PL组',
      width: 220,
      showOverflowTooltip: false,
    },
    {
      key: 'branch_count',
      dataKey: 'branch_count',
      title: '分支数',
      width: 90,
    },
    {
      key: 'project_url',
      dataKey: 'project_url',
      title: '代码库URL',
      width: 300,
      showOverflowTooltip: false,
    },
    {
      key: 'remark',
      dataKey: 'remark',
      title: '备注',
      width: 180,
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 140,
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
