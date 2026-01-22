import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { PerformanceDashboardItem } from '#/api/core/performance';

/**
 * Get search form schema
 */
export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'project',
      label: '项目',
      componentProps: {
        placeholder: '请输入项目',
      },
    },
    {
      component: 'Input',
      fieldName: 'module',
      label: '模块',
      componentProps: {
        placeholder: '请输入模块',
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
    {
      component: 'DatePicker',
      fieldName: 'date',
      label: '数据日期',
      componentProps: {
        placeholder: '选择日期',
        valueFormat: 'YYYY-MM-DD',
      },
    },
  ];
}

/**
 * Get status tag type based on fluctuation
 */
export function getStatusType(row: PerformanceDashboardItem) {
  if (row.current_value === undefined || row.current_value === null)
    return 'info';

  const fVal = row.fluctuation_value || 0;
  const range = row.fluctuation_range || 0;

  if (row.fluctuation_direction === 'up') {
    if (fVal < -range) return 'danger';
    return 'success';
  } else if (row.fluctuation_direction === 'down') {
    if (fVal > range) return 'danger';
    return 'success';
  } else {
    if (Math.abs(fVal) > range) return 'warning';
    return 'success';
  }
}

/**
 * Get table columns configuration
 */
export function useColumns(): VxeTableGridOptions<PerformanceDashboardItem>['columns'] {
  return [
    {
      field: 'data_date',
      title: '数据日期',
      minWidth: 120,
      sortable: true,
    },
    {
      field: 'project',
      title: '项目',
      minWidth: 120,
    },
    {
      field: 'module',
      title: '模块',
      minWidth: 120,
    },
    {
      field: 'chip_type',
      title: '芯片',
      minWidth: 100,
    },
    {
      field: 'name',
      title: '指标名称',
      minWidth: 150,
    },
    {
      field: 'baseline_value',
      title: '基线值',
      minWidth: 120,
      formatter: ({ row }) =>
        `${row.baseline_value} ${row.baseline_unit || ''}`,
    },
    {
      field: 'current_value',
      title: '当前值',
      minWidth: 120,
    },
    {
      field: 'fluctuation_value',
      title: '浮动',
      minWidth: 120,
      slots: { default: 'fluctuation' },
    },
    {
      field: 'action',
      title: '操作',
      fixed: 'right',
      width: 150,
      slots: { default: 'action' },
    },
  ];
}
