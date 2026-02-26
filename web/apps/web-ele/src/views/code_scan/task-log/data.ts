import type { VxeTableGridOptions } from '#/adapter/vxe-table';

export function useColumns(): VxeTableGridOptions<any>['columns'] {
  return [
    { type: 'seq', width: 60 },
    { field: 'project_name', title: '项目名称', minWidth: 180 },
    { field: 'tool_name', title: '工具', width: 120 },
    { field: 'status', title: '状态', width: 110, slots: { default: 'status' } },
    { field: 'scan_time', title: '扫描时间', width: 180 },
    { field: 'processed_time', title: '完成时间', width: 180 },
    { field: 'report_file', title: '报告文件', minWidth: 260, showOverflow: true },
    { field: 'log', title: '解析日志', minWidth: 320, slots: { default: 'log' } },
    { field: 'action', title: '操作', width: 120, fixed: 'right', slots: { default: 'action' } },
  ];
}
