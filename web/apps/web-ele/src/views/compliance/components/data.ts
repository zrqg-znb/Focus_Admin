import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { ComplianceRecord } from '#/api/compliance';

export function useRiskColumns(): VxeTableGridOptions<ComplianceRecord>['columns'] {
  return [
    { field: 'change_id', title: 'ChangeId', width: 150 },
    { field: 'title', title: 'Title', minWidth: 200 },
    { field: 'update_time', title: 'UpdateTime', width: 160 },
    { field: 'url', title: 'URL', width: 80, slots: { default: 'url' } },
    { field: 'branches', title: 'Branches', minWidth: 200, slots: { default: 'branches' } },
    { field: 'status', title: '整体状态', width: 100, slots: { default: 'status' } },
    { field: 'action', title: '操作', width: 150, slots: { default: 'action' } },
  ];
}
