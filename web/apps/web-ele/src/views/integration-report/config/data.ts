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
  _onActionClick?: OnActionClickFn<ProjectConfigManageRow>,
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
    { field: 'dt_bin_task_id', title: 'DT_Bin ID', minWidth: 150 },
    {
      field: 'cooddy_check_task_id',
      title: 'Cooddy Check ID',
      minWidth: 170,
    },
    { field: 'bin_scope_task_id', title: 'BinScope ID', minWidth: 150 },
    { field: 'build_check_task_id', title: 'BuildCheck ID', minWidth: 150 },
    { field: 'compile_check_task_id', title: 'CompileCheck ID', minWidth: 150 },
    {
      field: 'code_scan_project_key',
      title: 'CodeScan ProjectKey',
      minWidth: 180,
    },
    {
      field: 'valgrind_sub_modules',
      title: 'TSan / Valgrind 子模块',
      minWidth: 220,
      formatter: ({ row }) =>
        Array.isArray(row.valgrind_sub_modules) &&
        row.valgrind_sub_modules.length > 0
          ? row.valgrind_sub_modules.join(', ')
          : '-',
    },
    { field: 'dt_project_id', title: 'DT Project ID', minWidth: 150 },
    {
      field: 'enable_dt_fuzz',
      title: 'DT_FUZZ',
      width: 100,
      formatter: ({ row }) => (row.enable_dt_fuzz ? '启用' : '关闭'),
    },
    {
      field: 'dt_fuzz_version_name',
      title: 'DT_FUZZ versionName',
      minWidth: 190,
    },
    {
      field: 'dt_fuzz_branches',
      title: 'DT_FUZZ 分支',
      minWidth: 180,
      formatter: ({ row }) =>
        Array.isArray(row.dt_fuzz_branches) && row.dt_fuzz_branches.length > 0
          ? row.dt_fuzz_branches.join(', ')
          : '-',
    },
    { field: 'dt_fuzz_pbi_id', title: 'DT_FUZZ pbiId', minWidth: 150 },
    {
      field: 'dt_fuzz_domain_id',
      title: 'DT_FUZZ domian-id',
      minWidth: 170,
    },
    {
      field: 'dt_fuzz_project_id',
      title: 'DT_FUZZ project-id',
      minWidth: 170,
    },
    {
      field: 'action',
      title: '操作',
      width: 150,
      fixed: 'right',
      slots: { default: 'action_default' },
    },
  ];
}
