import type { Column } from 'element-plus';

import type { FailureModeTaskItem } from '#/api/failure_mode_workflow';
import type { ZqTableGridOptions } from '#/components/zq-table';

function withCenter<T extends Record<string, any>>(
  columns: Column<T>[],
): ZqTableGridOptions<T>['columns'] {
  return columns.map((column) => ({
    align: 'center',
    headerAlign: 'center',
    ...column,
  }));
}

export function useTaskColumns(): ZqTableGridOptions<FailureModeTaskItem>['columns'] {
  return withCenter<FailureModeTaskItem>([
    {
      key: 'task_no',
      dataKey: 'task_no',
      title: '任务编号',
      width: 190,
    },
    {
      key: 'name',
      dataKey: 'name',
      title: '任务名称',
      width: 250,
    },
    {
      key: 'task_type',
      dataKey: 'task_type',
      title: '任务类型',
      width: 120,
    },
    {
      key: 'product_name',
      dataKey: 'product_name',
      title: '产品(项目)',
      width: 200,
    },
    {
      key: 'subsystem',
      dataKey: 'subsystem',
      title: '子系统',
      width: 150,
    },
    {
      key: 'status',
      dataKey: 'status',
      title: '状态',
      width: 120,
      cellSlotName: 'cell-status',
    },
    {
      key: 'creator_info',
      dataKey: 'creator_info',
      title: '创建人(版本SE)',
      width: 150,
      cellSlotName: 'cell-creator',
    },
    {
      key: 'assignee_info',
      dataKey: 'assignee_info',
      title: '责任人(特性SE)',
      width: 150,
      cellSlotName: 'cell-assignee',
    },
    {
      key: 'sys_create_datetime',
      dataKey: 'sys_create_datetime',
      title: '创建时间',
      width: 180,
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 260,
      fixed: true,
      cellSlotName: 'cell-actions',
    },
  ]);
}
