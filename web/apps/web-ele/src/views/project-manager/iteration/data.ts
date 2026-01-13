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

const formatRate = ({ cellValue }: { cellValue: number }) => {
  return cellValue !== undefined && cellValue !== null ? `${(cellValue * 100).toFixed(1)}%` : '-';
};

export function useDashboardColumns(
  onNameClick: (row: IterationDashboardItem) => void,
): VxeTableGridOptions<IterationDashboardItem>['columns'] {
  return [
    {
      field: 'project_name',
      title: '项目名',
      minWidth: 160,
      slots: { default: 'name_slot' },
      fixed: 'left',
    },
    { field: 'project_domain', title: '领域', minWidth: 100 },
    { field: 'project_type', title: '类型', minWidth: 100 },
    { field: 'current_iteration_name', title: '当前迭代', minWidth: 140 },
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
    {
      title: '分解率',
      children: [
        { field: 'dr_breakdown_rate', title: 'DR分解率', minWidth: 100, formatter: formatRate },
        { field: 'sr_breakdown_rate', title: 'SR分解率', minWidth: 100, formatter: formatRate },
      ]
    },
    {
      title: '置A率',
      children: [
        { field: 'dr_set_a_rate', title: 'DR置A率', minWidth: 100, formatter: formatRate },
        { field: 'ar_set_a_rate', title: 'AR置A率', minWidth: 100, formatter: formatRate },
      ]
    },
    {
      title: '置C率(C+A)',
      children: [
        { field: 'dr_set_c_rate', title: 'DR置C率', minWidth: 100, formatter: formatRate },
        { field: 'ar_set_c_rate', title: 'AR置C率', minWidth: 100, formatter: formatRate },
      ]
    },
    { field: 'start_date', title: '开始时间', minWidth: 110 },
    { field: 'end_date', title: '结束时间', minWidth: 110 },
  ];
}

export function useDetailColumns(): VxeTableGridOptions<IterationDetailItem>['columns'] {
  return [
    { field: 'name', title: '迭代名称', minWidth: 150, fixed: 'left' },
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
    {
      title: '分解率',
      children: [
        { 
          field: 'latest_metric.dr_breakdown_rate', 
          title: 'DR分解率', 
          minWidth: 100, 
          formatter: formatRate 
        },
        { 
          field: 'latest_metric.sr_breakdown_rate', 
          title: 'SR分解率', 
          minWidth: 100, 
          formatter: formatRate 
        },
      ]
    },
    {
      title: '置A率',
      children: [
        { 
          field: 'latest_metric.dr_set_a_rate', 
          title: 'DR置A率', 
          minWidth: 100, 
          formatter: formatRate 
        },
        { 
          field: 'latest_metric.ar_set_a_rate', 
          title: 'AR置A率', 
          minWidth: 100, 
          formatter: formatRate 
        },
      ]
    },
  ];
}
