import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
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

export function useColumns(): VxeTableGridOptions<any>['columns'] {
  return [
    { type: 'seq', width: 60 },
    { field: 'name', title: '项目名称', minWidth: 150 },
    { field: 'project_key', title: 'Project Key', minWidth: 300, showOverflow: true },
    { field: 'repo_url', title: '代码仓', minWidth: 250 },
    { field: 'branch', title: '分支', width: 100 },
    { field: 'caretaker_name', title: '数据看护人', width: 120 },
    {
        field: 'action',
        title: '操作',
        fixed: 'right',
        width: 150,
        slots: { default: 'action' }
    }
  ];
}
