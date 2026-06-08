import type { Column } from 'element-plus';

import type {
  MissingMergeScanTaskItem,
  MissingMergeScanStatus,
  MissingMergeTriggerType,
} from '#/api/compliance/missing-merge';
import type { ZqTableGridOptions } from '#/components/zq-table';

export type TagType = 'danger' | 'info' | 'primary' | 'success' | 'warning';

export const TASK_STATUS_OPTIONS: Array<{
  label: string;
  type: TagType;
  value: MissingMergeScanStatus;
}> = [
  { label: '待执行', type: 'info', value: 'pending' },
  { label: '执行中', type: 'warning', value: 'running' },
  { label: '成功', type: 'success', value: 'success' },
  { label: '失败', type: 'danger', value: 'failed' },
];

export const TASK_TRIGGER_OPTIONS: Array<{
  label: string;
  value: MissingMergeTriggerType;
}> = [
  { label: '手动', value: 'manual' },
  { label: '定时', value: 'scheduled' },
];

export function getTaskStatusTagType(status: string): TagType {
  const option = TASK_STATUS_OPTIONS.find((item) => item.value === status);
  return option?.type || 'info';
}

export function useMissingMergeTaskColumns(): ZqTableGridOptions<MissingMergeScanTaskItem>['columns'] {
  const columns: Column<MissingMergeScanTaskItem>[] = [
    {
      key: 'status_label',
      dataKey: 'status_label',
      title: '状态',
      width: 100,
      fixed: true,
      showOverflowTooltip: false,
    },
    {
      key: 'trigger_type_label',
      dataKey: 'trigger_type_label',
      title: '触发方式',
      width: 100,
    },
    {
      key: 'merged_range',
      dataKey: 'merged_range',
      title: '合入时间范围',
      width: 310,
      showOverflowTooltip: false,
    },
    {
      key: 'started_at',
      dataKey: 'started_at',
      title: '开始时间',
      width: 170,
    },
    {
      key: 'finished_at',
      dataKey: 'finished_at',
      title: '结束时间',
      width: 170,
    },
    {
      key: 'duration',
      dataKey: 'duration',
      title: '耗时',
      width: 100,
    },
    {
      key: 'scan_counts',
      dataKey: 'scan_counts',
      title: '扫描范围',
      width: 180,
      showOverflowTooltip: false,
    },
    {
      key: 'risk_counts',
      dataKey: 'risk_counts',
      title: '风险结果',
      width: 220,
      showOverflowTooltip: false,
    },
    {
      key: 'error_message',
      dataKey: 'error_message',
      title: '错误摘要',
      width: 240,
      showOverflowTooltip: false,
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 110,
      fixed: true,
      showOverflowTooltip: false,
    },
  ];

  return columns.map((column) => ({
    align: 'center',
    headerAlign: 'center',
    ...column,
  }));
}
