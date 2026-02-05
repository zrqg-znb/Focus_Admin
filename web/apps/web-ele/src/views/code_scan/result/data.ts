import type { VxeTableGridOptions } from '#/adapter/vxe-table';

export function useSummaryColumns(toolNames: string[]): VxeTableGridOptions<any>['columns'] {
  return [
    { field: 'project_name', title: '项目', minWidth: 240, slots: { default: 'project_name' } },
    { field: 'total', title: '总问题数', width: 100 },
    ...toolNames.map((name) => ({
      field: name,
      title: name,
      width: 120,
    })),
    { field: 'latest_time', title: '最新扫描时间', width: 180 },
  ];
}

export function useDetailColumns(): VxeTableGridOptions<any>['columns'] {
  return [
    { type: 'checkbox', width: 60 },
    { type: 'expand', width: 60, slots: { content: 'expand_content' } },
    { field: 'tool_name', title: '工具', width: 100 },
    { field: 'severity', title: '严重程度', width: 100, slots: { default: 'severity' } },
    { field: 'defect_type', title: '缺陷类型', width: 150 },
    { field: 'file_path', title: '文件路径', minWidth: 200 },
    { field: 'line_number', title: '行号', width: 80 },
    { field: 'description', title: '缺陷描述', minWidth: 300 },
    { field: 'shield_status', title: '状态', width: 120, slots: { default: 'shield_status' } },
  ];
}
