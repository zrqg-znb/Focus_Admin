import type { Column } from 'element-plus';

import type { VbenFormSchema } from '#/adapter/form';
import type { ScanProjectItem } from '#/api/code_scan';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { z } from '#/adapter/form';

export function getFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: '项目名称',
      rules: z.string().min(1, '请输入项目名称'),
    },
    {
      component: 'Input',
      fieldName: 'repo_url',
      label: '代码仓地址',
      rules: z.string().min(1, '请输入代码仓地址'),
    },
    {
      component: 'Input',
      fieldName: 'branch',
      label: '分支',
      defaultValue: 'master',
    },
    {
      component: 'UserSelector',
      fieldName: 'caretaker_id',
      label: '数据看护责任人',
      componentProps: {
        placeholder: '请选择数据看护责任人',
      },
    },
    {
      component: 'Input',
      fieldName: 'description',
      label: '描述',
      componentProps: {
        type: 'textarea',
      },
    },
    {
      component: 'Input',
      fieldName: 'path_shield_prefixes_text',
      label: '路径前缀屏蔽规则',
      componentProps: {
        type: 'textarea',
        rows: 4,
        placeholder: '每行一个路径前缀，例如：\n/src/generated/\n/third_party/',
      },
    },
  ];
}

export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'keyword',
      label: '关键词',
      componentProps: {
        placeholder: '搜索项目名或代码仓',
      },
    },
  ];
}

export function useZqColumns(): ZqTableGridOptions<ScanProjectItem>['columns'] {
  const columns: Column<ScanProjectItem>[] = [
    {
      key: 'name',
      dataKey: 'name',
      title: '项目名称',
      width: 180,
      fixed: true,
    },
    {
      key: 'project_key',
      dataKey: 'project_key',
      title: 'Project Key',
      width: 360,
    },
    {
      key: 'repo_url',
      dataKey: 'repo_url',
      title: '代码仓',
      width: 320,
    },
    {
      key: 'branch',
      dataKey: 'branch',
      title: '分支',
      width: 120,
    },
    {
      key: 'caretaker_name',
      dataKey: 'caretaker_name',
      title: '数据看护人',
      width: 140,
    },
    {
      key: 'sys_create_datetime',
      dataKey: 'sys_create_datetime',
      title: '创建时间',
      width: 180,
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 220,
      fixed: 'right',
      showOverflowTooltip: false,
    },
  ];

  return columns.map((column) => ({
    align: 'center',
    headerAlign: 'center',
    ...column,
  }));
}
