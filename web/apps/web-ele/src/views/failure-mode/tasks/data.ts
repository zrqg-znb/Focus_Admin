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

export const FM_TASK_STATUS_OPTIONS = [
  { label: '全部', value: '' },
  { label: '创建', value: 'CREATED' },
  { label: '梳理/修订中', value: 'PROCESSING' },
  { label: '评审中', value: 'REVIEWING' },
  { label: '已关闭', value: 'CLOSED' },
];

export const FM_TASK_STATUS_LABEL_MAP: Record<string, string> = {
  CLOSED: '已关闭',
  CREATED: '创建',
  PROCESSING: '梳理/修订中',
  REVIEWING: '评审中',
};

export const FM_TASK_TYPE_LABEL_MAP: Record<string, string> = {
  CREATE: '创建',
  DELETE: '删除',
  REVISE: '修订',
};

export function getTaskStatusTagType(status: string) {
  switch (status) {
    case 'CLOSED': {
      return 'success';
    }
    case 'CREATED': {
      return 'info';
    }
    case 'PROCESSING': {
      return 'primary';
    }
    case 'REVIEWING': {
      return 'warning';
    }
    default: {
      return 'info';
    }
  }
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
      cellSlotName: 'cell-task-type',
    },
    {
      key: 'product_name',
      dataKey: 'product_name',
      title: '产品',
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
      width: 130,
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
      key: 'current_processor_info',
      dataKey: 'current_processor_info',
      title: '当前待办人',
      width: 150,
      cellSlotName: 'cell-current-processor',
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
      width: 160,
      fixed: true,
      cellSlotName: 'cell-actions',
    },
  ]);
}
