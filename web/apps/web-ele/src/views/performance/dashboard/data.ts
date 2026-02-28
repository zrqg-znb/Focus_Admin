import type { VbenFormSchema } from '#/adapter/form';
import type { PerformanceDashboardItem } from '#/api/core/performance';
import type { ZqTableGridOptions } from '#/components/zq-table';

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
export function useColumns(): ZqTableGridOptions<PerformanceDashboardItem>['columns'] {
  const columns: NonNullable<
    ZqTableGridOptions<PerformanceDashboardItem>['columns']
  > = [
    {
      key: 'data_date',
      dataKey: 'data_date',
      title: '数据日期',
      width: 120,
      sortable: true,
    },
    {
      key: 'project',
      dataKey: 'project',
      title: '项目',
      width: 120,
    },
    {
      key: 'module',
      dataKey: 'module',
      title: '模块',
      width: 120,
    },
    {
      key: 'chip_type',
      dataKey: 'chip_type',
      title: '芯片',
      width: 100,
    },
    {
      key: 'name',
      dataKey: 'name',
      title: '指标名称',
      width: 150,
    },
    {
      key: 'baseline_value',
      dataKey: 'baseline_value',
      title: '基线值',
      width: 120,
    },
    {
      key: 'current_value',
      dataKey: 'current_value',
      title: '当前值',
      width: 120,
    },
    {
      key: 'fluctuation_value',
      dataKey: 'fluctuation_value',
      title: '浮动',
      width: 120,
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
