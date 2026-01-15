import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridOptions } from '#/adapter/vxe-table';
import type { MilestoneBoardItem } from '#/api/project-manager/milestone';

export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'keyword',
      label: '项目搜索',
      componentProps: {
        placeholder: '输入项目名称/编码',
      },
    },
    {
      component: 'Input',
      fieldName: 'project_type',
      label: '项目类型',
    },
    {
      component: 'Input',
      fieldName: 'manager_id',
      label: '负责人',
    },
  ];
}

export function useTableColumns(): VxeTableGridOptions<MilestoneBoardItem>['columns'] {
  return [
    { field: 'project_name', title: '项目名称', minWidth: 200, fixed: 'left' },
    { field: 'project_domain', title: '领域', minWidth: 100 },
    { field: 'project_type', title: '类型', minWidth: 100 },
    {
      field: 'manager_names',
      title: '负责人',
      minWidth: 150,
      formatter: ({ cellValue }) => (cellValue || []).join(', '),
    },
    { field: 'qg1_date', title: 'QG1', minWidth: 120 },
    { field: 'qg2_date', title: 'QG2', minWidth: 120 },
    { field: 'qg3_date', title: 'QG3', minWidth: 120 },
    { field: 'qg4_date', title: 'QG4', minWidth: 120 },
    { field: 'qg5_date', title: 'QG5', minWidth: 120 },
    { field: 'qg6_date', title: 'QG6', minWidth: 120 },
    { field: 'qg7_date', title: 'QG7', minWidth: 120 },
    { field: 'qg8_date', title: 'QG8', minWidth: 120 },
  ];
}
