import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SyncLog } from '#/api/project-manager/sync_log';

export function useSyncLogColumns(): VxeTableGridOptions<SyncLog>['columns'] {
  return [
    { type: 'seq', width: 50 },
    { field: 'sync_type_display', title: '同步类型', width: 120 },
    { field: 'project_id', title: '项目ID', width: 150 },
    {
      field: 'status',
      title: '状态',
      width: 100,
      slots: { default: 'status' },
    },
    { field: 'result_summary', title: '结果摘要', minWidth: 200 },
    { field: 'duration', title: '耗时(s)', width: 100 },
    { field: 'creator_name', title: '触发人', width: 120 },
    { field: 'sys_create_datetime', title: '触发时间', width: 180 },
    {
      title: '操作',
      width: 100,
      fixed: 'right',
      slots: { default: 'action' },
    },
  ];
}
