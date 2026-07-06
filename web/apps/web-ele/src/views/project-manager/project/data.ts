import type { Column } from 'element-plus';

import type { VbenFormSchema } from '#/adapter/form';
import type { ProjectOut } from '#/api/project-manager/project';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { z } from '#/adapter/form';

export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    { component: 'Input', fieldName: 'keyword', label: '关键词' },
    { component: 'Input', fieldName: 'domain', label: '领域' },
    { component: 'Input', fieldName: 'type', label: '类型' },
    { component: 'Input', fieldName: 'manager_id', label: '项目经理ID' },
    {
      component: 'Select',
      fieldName: 'is_closed',
      label: '是否结项',
      componentProps: {
        options: [
          { label: '全部', value: undefined },
          { label: '是', value: true },
          { label: '否', value: false },
        ],
        clearable: true,
      },
    },
    {
      component: 'Select',
      fieldName: 'enable_milestone',
      label: '统计里程碑',
      componentProps: {
        options: [
          { label: '全部', value: undefined },
          { label: '是', value: true },
          { label: '否', value: false },
        ],
        clearable: true,
      },
    },
    {
      component: 'Select',
      fieldName: 'enable_iteration',
      label: '统计迭代',
      componentProps: {
        options: [
          { label: '全部', value: undefined },
          { label: '是', value: true },
          { label: '否', value: false },
        ],
        clearable: true,
      },
    },
    {
      component: 'Select',
      fieldName: 'enable_quality',
      label: '统计代码质量',
      componentProps: {
        options: [
          { label: '全部', value: undefined },
          { label: '是', value: true },
          { label: '否', value: false },
        ],
        clearable: true,
      },
    },
    {
      component: 'Select',
      fieldName: 'enable_hardware_config',
      label: '开启典配',
      componentProps: {
        options: [
          { label: '全部', value: undefined },
          { label: '是', value: true },
          { label: '否', value: false },
        ],
        clearable: true,
      },
    },
  ];
}

export function useZqColumns(): ZqTableGridOptions<ProjectOut>['columns'] {
  const columns: Column<ProjectOut>[] = [
    {
      key: 'name',
      dataKey: 'name',
      title: '项目名',
      width: 180,
      fixed: true,
    },
    { key: 'domain', dataKey: 'domain', title: '项目领域', width: 120 },
    { key: 'type', dataKey: 'type', title: '项目类型', width: 120 },
    { key: 'code', dataKey: 'code', title: '项目编码', width: 160 },
    {
      key: 'managers_info',
      dataKey: 'managers_info',
      title: '项目经理',
      width: 180,
    },
    {
      key: 'is_closed',
      dataKey: 'is_closed',
      title: '是否结项',
      width: 110,
      align: 'center',
    },
    { key: 'repo_url', dataKey: 'repo_url', title: '制品仓号', width: 220 },
    {
      key: 'enable_milestone',
      dataKey: 'enable_milestone',
      title: '统计里程碑',
      width: 120,
      align: 'center',
    },
    {
      key: 'enable_iteration',
      dataKey: 'enable_iteration',
      title: '统计迭代',
      width: 120,
      align: 'center',
    },
    {
      key: 'enable_quality',
      dataKey: 'enable_quality',
      title: '统计代码质量',
      width: 130,
      align: 'center',
    },
    {
      key: 'enable_hardware_config',
      dataKey: 'enable_hardware_config',
      title: '开启典配',
      width: 120,
      align: 'center',
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
      width: 240,
      showOverflowTooltip: false,
    },
  ];

  return columns.map((column) => {
    return {
      align: 'center',
      headerAlign: 'center',
      ...column,
    };
  });
}

export function getProjectFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: '项目名',
      rules: z.string().min(1, '请输入项目名'),
    },
    {
      component: 'Input',
      fieldName: 'domain',
      label: '项目领域',
      rules: z.string().min(1, '请输入项目领域'),
    },
    {
      component: 'Input',
      fieldName: 'type',
      label: '项目类型',
      rules: z.string().min(1, '请输入项目类型'),
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: '项目编码',
      rules: z.string().min(1, '请输入项目编码'),
    },
    {
      component: 'UserSelector',
      fieldName: 'manager_ids',
      label: '项目经理',
      componentProps: { multiple: true, placeholder: '选择项目经理' },
      rules: z.array(z.string()).min(1, '至少选择一位项目经理'),
    },
    {
      component: 'RadioGroup',
      fieldName: 'is_closed',
      label: '是否结项',
      defaultValue: false,
      componentProps: {
        isButton: true,
        options: [
          { label: '否', value: false, type: 'success' },
          { label: '是', value: true, type: 'danger' },
        ],
      },
    },
    {
      component: 'Input',
      fieldName: 'repo_url',
      label: '制品仓',
      rules: z.string().min(1, '请输入制品仓号/地址'),
    },
    {
      component: 'Input',
      fieldName: 'remark',
      label: '备注',
      componentProps: {
        placeholder: '请输入备注',
        rows: 3,
      },
      rules: z.string().min(1, '请输入备注'),
    },
  ];
}
