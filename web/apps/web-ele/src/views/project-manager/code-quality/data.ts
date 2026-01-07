import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { ProjectQualitySummary, ModuleQualityDetail } from '#/api/project-manager/code_quality';

export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    { component: 'Input', fieldName: 'keyword', label: '关键词' },
    { component: 'Input', fieldName: 'domain', label: '领域' },
    { component: 'Input', fieldName: 'type', label: '类型' },
    {
      component: 'DatePicker',
      fieldName: 'date',
      label: '日期',
      componentProps: {
        valueFormat: 'YYYY-MM-DD',
      },
    },
  ];
}

export function useSummaryColumns(
  onNameClick: (row: ProjectQualitySummary) => void,
): VxeTableGridOptions<ProjectQualitySummary>['columns'] {
  return [
    {
      field: 'project_name',
      title: '项目名',
      minWidth: 160,
      slots: { default: 'name_slot' }, // We will use a slot for the link
    },
    { field: 'project_domain', title: '领域', minWidth: 120 },
    { field: 'project_type', title: '类型', minWidth: 120 },
    { field: 'project_managers', title: '项目经理', minWidth: 150 },
    { field: 'record_date', title: '更新日期', minWidth: 120 },
    { field: 'total_loc', title: '总代码行', minWidth: 100 },
    { field: 'total_function_count', title: '函数总数', minWidth: 100 },
    { field: 'total_dangerous_func_count', title: '危险函数', minWidth: 100 },
    { field: 'avg_duplication_rate', title: '平均重复率', minWidth: 100, formatter: ({ cellValue }) => `${cellValue}%` },
    { field: 'module_count', title: '模块数', minWidth: 80 },
  ];
}

export function useDetailColumns(): VxeTableGridOptions<ModuleQualityDetail>['columns'] {
  return [
    { field: 'oem_name', title: 'OEM名称', minWidth: 150 },
    { field: 'module', title: '模块名', minWidth: 150 },
    {
      field: 'owner_names',
      title: '责任人',
      minWidth: 150,
      formatter: ({ cellValue }) => (cellValue || []).join('、'),
    },
    { field: 'record_date', title: '记录日期', minWidth: 120 },
    { field: 'loc', title: '代码行', minWidth: 100 },
    { field: 'function_count', title: '函数数', minWidth: 100 },
    { field: 'dangerous_func_count', title: '危险函数', minWidth: 100 },
    { field: 'duplication_rate', title: '重复率', minWidth: 100, formatter: ({ cellValue }) => `${cellValue}%` },
    {
      field: 'is_clean_code',
      title: 'Clean Code',
      minWidth: 100,
      cellRender: {
        name: 'CellTag',
        options: [
          { label: '是', value: true, type: 'success' },
          { label: '否', value: false, type: 'danger' },
        ],
      },
    },
  ];
}
