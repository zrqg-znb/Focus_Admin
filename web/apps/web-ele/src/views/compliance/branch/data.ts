import type { Column } from 'element-plus';

import type { BranchItem } from '#/api/compliance/base';
import type { ZqTableGridOptions } from '#/components/zq-table';

export const DOMAIN_OPTIONS = [
  { label: '座舱', value: 'cockpit' },
  { label: '车控', value: 'vehicle' },
] as const;

export const BRANCH_TYPE_OPTIONS = [
  { label: '开发', value: 'development' },
  { label: '主干', value: 'trunk' },
  { label: '发布', value: 'release' },
  { label: '其他', value: 'other' },
] as const;

export const BIND_MODE_OPTIONS = [
  { label: '追加绑定', value: 'append' },
  { label: '替换绑定', value: 'replace' },
] as const;

export function useBranchColumns(): ZqTableGridOptions<BranchItem>['columns'] {
  const columns: Column<BranchItem>[] = [
    {
      key: 'branch_name',
      dataKey: 'branch_name',
      title: '分支名称',
      width: 220,
      fixed: true,
      showOverflowTooltip: false,
    },
    {
      key: 'alias',
      dataKey: 'alias',
      title: '别名',
      width: 140,
    },
    {
      key: 'branch_type_label',
      dataKey: 'branch_type_label',
      title: '类型',
      width: 90,
    },
    {
      key: 'domain_label',
      dataKey: 'domain_label',
      title: '领域',
      width: 90,
    },
    {
      key: 'created_date',
      dataKey: 'created_date',
      title: '创建日期',
      width: 130,
    },
    {
      key: 'purpose',
      dataKey: 'purpose',
      title: '用途',
      width: 260,
      showOverflowTooltip: false,
    },
    {
      key: 'repository_count',
      dataKey: 'repository_count',
      title: '关联仓库数',
      width: 110,
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
