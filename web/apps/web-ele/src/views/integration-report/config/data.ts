import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridOptions } from '#/adapter/vxe-table';
import type { ProjectConfigManageRow } from '#/api/integration-report';

export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    {
      fieldName: 'project_name',
      label: '搜索配置/项目',
      component: 'Input',
      componentProps: {
        placeholder: '搜索配置名或项目名',
      },
    },
  ];
}

export function useColumns(
  onActionClick?: OnActionClickFn<ProjectConfigManageRow>,
): VxeTableGridOptions<ProjectConfigManageRow>['columns'] {
  return [
    { type: 'checkbox', width: 50, fixed: 'left' },
    { type: 'seq', width: 50, fixed: 'left' },
    { field: 'name', title: '配置名称', minWidth: 180, fixed: 'left' },
    { field: 'project_name', title: '所属项目', minWidth: 150 },
    { field: 'managers', title: '负责人', minWidth: 120 },
    {
      field: 'enabled',
      title: '启用',
      width: 90,
      slots: { default: 'enabled_default' },
    },
    { field: 'code_check_task_id', title: 'CodeCheck ID', minWidth: 150 },
    { field: 'bin_scope_task_id', title: 'BinScope ID', minWidth: 150 },
    { field: 'build_check_task_id', title: 'BuildCheck ID', minWidth: 150 },
    { field: 'compile_check_task_id', title: 'CompileCheck ID', minWidth: 150 },
    { field: 'dt_project_id', title: 'DT Project ID', minWidth: 150 },
    {
      field: 'action',
      title: '操作',
      width: 100,
      fixed: 'right',
      slots: { default: 'action_default' },
    },
  ];
}