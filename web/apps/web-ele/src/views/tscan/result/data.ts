import type { VxeTableGridOptions } from '#/adapter/vxe-table';

export function useColumns(): VxeTableGridOptions<any>['columns'] {
  return [
    { type: 'checkbox', width: 60 },
    { field: 'severity', title: '严重程度', width: 100, slots: { default: 'severity' } },
    { field: 'defect_type', title: '缺陷类型', width: 150 },
    { field: 'file_path', title: '文件路径', minWidth: 200 },
    { field: 'line_number', title: '行号', width: 80 },
    { field: 'description', title: '缺陷描述', minWidth: 300 },
    { field: 'shield_status', title: '状态', width: 120, slots: { default: 'shield_status' } },
  ];
}
