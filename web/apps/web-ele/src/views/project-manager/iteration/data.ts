import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { IterationDashboardItem, IterationDetailItem } from '#/api/project-manager/iteration';

export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    { component: 'Input', fieldName: 'keyword', label: '关键词' },
    { component: 'Input', fieldName: 'domain', label: '领域' },
    { component: 'Input', fieldName: 'type', label: '类型' },
  ];
}

export function useDashboardColumns(
  onNameClick: (row: IterationDashboardItem) => void,
): VxeTableGridOptions<IterationDashboardItem>['columns'] {
  return [
    {
      field: 'project_name',
      title: '项目名',
      minWidth: 160,
      slots: { default: 'name_slot' },
    },
    { field: 'project_domain', title: '领域', minWidth: 120 },
    { field: 'project_type', title: '类型', minWidth: 120 },
    { field: 'project_managers', title: '项目经理', minWidth: 150 },
    { field: 'current_iteration_name', title: '当前迭代', minWidth: 150 },
    { field: 'start_date', title: '开始时间', minWidth: 120 },
    { field: 'end_date', title: '结束时间', minWidth: 120 },
    {
      field: 'is_healthy',
      title: '健康状态',
      minWidth: 100,
      cellRender: {
        name: 'CellTag',
        options: [
          { label: '健康', value: true, type: 'success' },
          { label: '风险', value: false, type: 'danger' },
        ],
      },
    },
    { field: 'req_decomposition_rate', title: '需求分解率', minWidth: 100, formatter: ({ cellValue }) => `${(cellValue * 100).toFixed(1)}%` },
    { field: 'req_completion_rate', title: '完成率', minWidth: 100, formatter: ({ cellValue }) => `${(cellValue * 100).toFixed(1)}%` },
    { field: 'req_workload', title: '工作量', minWidth: 100 },
  ];
}

export function useDetailColumns(): VxeTableGridOptions<IterationDetailItem>['columns'] {
  return [
    { field: 'name', title: '迭代名称', minWidth: 150 },
    { field: 'code', title: '编码', minWidth: 120 },
    { field: 'start_date', title: '开始时间', minWidth: 120 },
    { field: 'end_date', title: '结束时间', minWidth: 120 },
    {
      field: 'is_current',
      title: '当前迭代',
      minWidth: 100,
      cellRender: {
        name: 'CellTag',
        options: [
          { label: '是', value: true, type: 'success' },
          { label: '否', value: false, type: 'info' },
        ],
      },
    },
    {
      field: 'is_healthy',
      title: '健康状态',
      minWidth: 100,
      cellRender: {
        name: 'CellTag',
        options: [
          { label: '健康', value: true, type: 'success' },
          { label: '风险', value: false, type: 'danger' },
        ],
      },
    },
    // Metrics are nested in latest_metric
    {
      field: 'latest_metric.req_decomposition_rate',
      title: '需求分解率',
      minWidth: 100,
      formatter: ({ cellValue }) => cellValue ? `${(cellValue * 100).toFixed(1)}%` : '-',
    },
    {
      field: 'latest_metric.req_completion_rate',
      title: '完成率',
      minWidth: 100,
      formatter: ({ cellValue }) => cellValue ? `${(cellValue * 100).toFixed(1)}%` : '-',
    },
    {
      field: 'latest_metric.req_drift_rate',
      title: '游离率',
      minWidth: 100,
      formatter: ({ cellValue }) => cellValue ? `${(cellValue * 100).toFixed(1)}%` : '-',
    },
    {
      field: 'latest_metric.req_workload',
      title: '工作量',
      minWidth: 100,
      formatter: ({ cellValue }) => cellValue ?? '-',
    },
  ];
}
