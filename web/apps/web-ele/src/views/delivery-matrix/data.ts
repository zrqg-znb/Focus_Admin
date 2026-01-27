import type { VxeTableGridOptions } from '@vben/plugins/vxe-table';

import type { VbenFormSchema } from '#/adapter/form';

import { getSimpleUserListApi } from '#/api/core/user';
import { getDomains, getGroups } from '#/api/delivery-matrix';
import { listProjectsApi } from '#/api/project-manager/project';

// --- Domain Schemas ---
export function useDomainFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: '领域名称',
      rules: 'required',
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: '领域编码',
      rules: 'required',
    },
    {
      component: 'ApiSelect',
      fieldName: 'interface_people_ids',
      label: '领域接口人',
      componentProps: {
        api: getSimpleUserListApi,
        labelField: 'name',
        valueField: 'id',
        mode: 'multiple',
      },
    },
  ];
}

export const domainColumns: VxeTableGridOptions['columns'] = [
  { type: 'checkbox', width: 50 },
  { field: 'name', title: '领域名称' },
  { field: 'code', title: '领域编码' },
  {
    field: 'interface_people_info',
    title: '领域接口人',
    formatter: ({ cellValue }) =>
      cellValue ? cellValue.map((u: any) => u.name).join(', ') : '',
  },
  { field: 'action', title: '操作', slots: { default: 'action' } },
];

// --- Group Schemas ---
export function useGroupFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: '项目群名称',
      rules: 'required',
    },
    {
      component: 'ApiSelect',
      fieldName: 'domain_id',
      label: '所属领域',
      rules: 'required',
      componentProps: {
        api: getDomains,
        labelField: 'name',
        valueField: 'id',
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'manager_ids',
      label: '项目群经理',
      componentProps: {
        api: getSimpleUserListApi,
        labelField: 'name',
        valueField: 'id',
        mode: 'multiple',
      },
    },
  ];
}

export const groupColumns: VxeTableGridOptions['columns'] = [
  { type: 'checkbox', width: 50 },
  { field: 'name', title: '项目群名称' },
  { field: 'domain_info.name', title: '所属领域' },
  {
    field: 'managers_info',
    title: '项目群经理',
    formatter: ({ cellValue }) =>
      cellValue ? cellValue.map((u: any) => u.name).join(', ') : '',
  },
  { field: 'action', title: '操作', slots: { default: 'action' } },
];

// --- Component Schemas ---
export function useComponentFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: '组件名称',
      rules: 'required',
    },
    {
      component: 'ApiSelect',
      fieldName: 'group_id',
      label: '所属项目群',
      rules: 'required',
      componentProps: {
        api: async () => {
          return await getGroups();
        },
        labelField: 'name',
        valueField: 'id',
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'manager_ids',
      label: '项目经理',
      componentProps: {
        api: getSimpleUserListApi,
        labelField: 'name',
        valueField: 'id',
        mode: 'multiple',
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'linked_project_id',
      label: '关联项目',
      componentProps: {
        api: async () => {
          const res = await listProjectsApi({ pageSize: 1000 });
          return res.items;
        },
        labelField: 'name',
        valueField: 'id',
        showSearch: true,
        optionFilterProp: 'label',
      },
    },
  ];
}

export const componentColumns: VxeTableGridOptions['columns'] = [
  { type: 'checkbox', width: 50 },
  { field: 'name', title: '组件名称' },
  { field: 'group_info.name', title: '所属项目群' },
  {
    field: 'managers_info',
    title: '项目经理',
    formatter: ({ cellValue }) =>
      cellValue ? cellValue.map((u: any) => u.name).join(', ') : '',
  },
  { field: 'linked_project_info.name', title: '关联项目' },
  { field: 'action', title: '操作', slots: { default: 'action' } },
];
