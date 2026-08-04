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
    {
      field: 'enable_domain_metrics',
      title: '按领域获取',
      width: 120,
      formatter: ({ row }) => (row.enable_domain_metrics ? '启用' : '关闭'),
    },
    {
      field: 'domain_directory_set_name',
      title: '责任田目录配置',
      minWidth: 180,
      formatter: ({ row }) => row.domain_directory_set_name || '-',
    },
    {
      field: 'code_check_task_ids',
      title: 'CodeCheck ID列表',
      minWidth: 190,
      formatter: ({ row }) =>
        Array.isArray(row.code_check_task_ids) &&
        row.code_check_task_ids.length > 0
          ? row.code_check_task_ids.join(', ')
          : '-',
    },
    {
      field: 'dt_bin_task_ids',
      title: 'DT_Bin ID列表',
      minWidth: 180,
      formatter: ({ row }) =>
        Array.isArray(row.dt_bin_task_ids) && row.dt_bin_task_ids.length > 0
          ? row.dt_bin_task_ids.join(', ')
          : '-',
    },
    {
      field: 'cooddy_check_task_ids',
      title: 'Cooddy Check ID列表',
      minWidth: 210,
      formatter: ({ row }) =>
        Array.isArray(row.cooddy_check_task_ids) &&
        row.cooddy_check_task_ids.length > 0
          ? row.cooddy_check_task_ids.join(', ')
          : '-',
    },
    {
      field: 'bin_scope_task_ids',
      title: 'BinScope ID列表',
      minWidth: 190,
      formatter: ({ row }) =>
        Array.isArray(row.bin_scope_task_ids) &&
        row.bin_scope_task_ids.length > 0
          ? row.bin_scope_task_ids.join(', ')
          : '-',
    },
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
