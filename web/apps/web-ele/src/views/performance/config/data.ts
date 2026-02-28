import type { VbenFormSchema } from '#/adapter/form';
import type { PerformanceIndicator } from '#/api/core/performance';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { z } from '#/adapter/form';

/**
 * Get search form schema
 */
export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'search',
      label: '指标名称',
      componentProps: {
        placeholder: '请输入指标名称',
      },
    },
    {
      component: 'Input',
      fieldName: 'module',
      label: '所属模块',
      componentProps: {
        placeholder: '请输入所属模块',
      },
    },
    {
      component: 'Input',
      fieldName: 'project',
      label: '所属项目',
      componentProps: {
        placeholder: '请输入所属项目',
      },
    },
    {
      component: 'Input',
      fieldName: 'chip_type',
      label: '芯片类型',
      componentProps: {
        placeholder: '请输入芯片类型',
      },
    },
  ];
}

/**
 * Get form schema for Create/Edit
 */
export function getFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'code',
      label: 'Code',
      componentProps: {
        placeholder: '请输入业务唯一标识',
      },
    },
    {
      component: 'Select',
      fieldName: 'category',
      label: '分类',
      defaultValue: 'vehicle',
      componentProps: {
        options: [
          { label: '车控', value: 'vehicle' },
          { label: '座舱', value: 'cockpit' },
        ],
      },
      rules: z.string().min(1, '请选择分类'),
    },
    {
      component: 'Input',
      fieldName: 'name',
      label: '指标名称',
      rules: z.string().min(1, '请输入指标名称'),
    },
    {
      component: 'Input',
      fieldName: 'project',
      label: '所属项目',
      rules: z.string().min(1, '请输入所属项目'),
    },
    {
      component: 'Input',
      fieldName: 'module',
      label: '所属模块',
      rules: z.string().min(1, '请输入所属模块'),
    },
    {
      component: 'Input',
      fieldName: 'chip_type',
      label: '芯片类型',
      rules: z.string().min(1, '请输入芯片类型'),
    },
    {
      component: 'Select',
      fieldName: 'value_type',
      label: '值类型',
      defaultValue: 'avg',
      componentProps: {
        options: [
          { label: '平均值', value: 'avg' },
          { label: '最大值', value: 'max' },
          { label: '最小值', value: 'min' },
        ],
      },
    },
    {
      component: 'InputNumber',
      fieldName: 'baseline_value',
      label: '基线值',
      componentProps: {
        class: 'w-full',
      },
      rules: z.number().min(0, '请输入有效的基线值'),
    },
    {
      component: 'Input',
      fieldName: 'baseline_unit',
      label: '单位',
    },
    {
      component: 'InputNumber',
      fieldName: 'fluctuation_range',
      label: '允许浮动',
      componentProps: {
        class: 'w-full',
      },
      defaultValue: 0,
    },
    {
      component: 'Select',
      fieldName: 'fluctuation_direction',
      label: '浮动方向',
      defaultValue: 'none',
      componentProps: {
        options: [
          { label: '越大越好', value: 'up' },
          { label: '越小越好', value: 'down' },
          { label: '无方向', value: 'none' },
        ],
      },
    },
    {
      component: 'UserSelector', // Reusing the component from User module
      fieldName: 'owner_id',
      label: '责任人',
      componentProps: {
        placeholder: '请选择责任人',
        multiple: false,
      },
      rules: z.string().min(1, '请选择责任人'),
    },
  ];
}

/**
 * Get table columns configuration
 */
export function useColumns(): ZqTableGridOptions<PerformanceIndicator>['columns'] {
  const columns: NonNullable<
    ZqTableGridOptions<PerformanceIndicator>['columns']
  > = [
    {
      key: 'code',
      dataKey: 'code',
      title: 'Code',
      width: 150,
    },
    {
      key: 'category',
      dataKey: 'category',
      title: '分类',
      width: 90,
    },
    {
      key: 'name',
      dataKey: 'name',
      title: '名称',
      width: 150,
    },
    {
      key: 'project',
      dataKey: 'project',
      title: '项目',
      width: 100,
    },
    {
      key: 'module',
      dataKey: 'module',
      title: '模块',
      width: 100,
    },
    {
      key: 'chip_type',
      dataKey: 'chip_type',
      title: '芯片',
      width: 100,
    },
    {
      key: 'baseline_value',
      dataKey: 'baseline_value',
      title: '基线值',
      width: 120,
    },
    {
      key: 'fluctuation_range',
      dataKey: 'fluctuation_range',
      title: '允许浮动',
      width: 100,
    },
    {
      key: 'fluctuation_direction',
      dataKey: 'fluctuation_direction',
      title: '方向',
      width: 100,
    },
    {
      key: 'owner_name',
      dataKey: 'owner_name',
      title: '责任人',
      width: 100,
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      fixed: 'right',
      width: 150,
    },
  ];

  return columns.map((column) => ({
    ...column,
    align: 'center',
    headerAlign: 'center',
  }));
}
