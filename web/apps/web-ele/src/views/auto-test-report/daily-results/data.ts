import type { DailyOverviewRow, DailyResultItem } from '#/api/auto-test-report';
import type { ZqTableGridOptions } from '#/components/zq-table';

export const RESULT_LABEL_MAP: Record<string, string> = {
  success: '成功',
  failed: '失败',
  timeout: '超时',
  skip: '跳过',
};

export const RESULT_TAG_MAP: Record<
  string,
  '' | 'danger' | 'info' | 'success' | 'warning'
> = {
  success: 'success',
  failed: 'danger',
  timeout: 'warning',
  skip: 'info',
};

export function formatDuration(seconds?: number) {
  const total = Math.max(Number(seconds || 0), 0);
  const hour = Math.floor(total / 3600);
  const minute = Math.floor((total % 3600) / 60);
  const second = total % 60;
  if (hour > 0) {
    return `${hour}h ${minute}m ${second}s`;
  }
  if (minute > 0) {
    return `${minute}m ${second}s`;
  }
  return `${second}s`;
}

export function useResultColumns(): ZqTableGridOptions<DailyResultItem>['columns'] {
  return [
    {
      key: 'case_no',
      dataKey: 'case_no',
      title: '用例编号',
      width: 180,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'case_name',
      dataKey: 'case_name',
      title: '用例名称',
      width: 260,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'remark',
      dataKey: 'remark',
      title: '用例备注',
      width: 220,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'status',
      dataKey: 'status',
      title: '执行结果',
      width: 140,
      align: 'center',
      headerAlign: 'center',
      slots: { header: 'header-status' },
    },
    {
      key: 'failure_reason',
      dataKey: 'failure_reason',
      title: '异常原因',
      width: 280,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'start_time',
      dataKey: 'start_time',
      title: '开始时间',
      width: 180,
      align: 'center',
      headerAlign: 'center',
      sortable: 'custom',
    },
    {
      key: 'duration_seconds',
      dataKey: 'duration_seconds',
      title: '执行时长',
      width: 120,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'log_url',
      dataKey: 'log_url',
      title: '运行日志',
      width: 240,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 100,
      align: 'center',
      headerAlign: 'center',
      showOverflowTooltip: false,
    },
  ];
}

export function useOverviewColumns(): ZqTableGridOptions<DailyOverviewRow>['columns'] {
  return [
    {
      key: 'platform_name',
      dataKey: 'platform_name',
      title: 'MCU平台',
      width: 140,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'vehicle_name',
      dataKey: 'vehicle_name',
      title: '车型',
      width: 180,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'vehicle_code',
      dataKey: 'vehicle_code',
      title: '车型编号',
      width: 160,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'total_count',
      dataKey: 'total_count',
      title: '总用例',
      width: 100,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'success_count',
      dataKey: 'success_count',
      title: '成功',
      width: 90,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'failed_count',
      dataKey: 'failed_count',
      title: '失败',
      width: 90,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'timeout_count',
      dataKey: 'timeout_count',
      title: '超时',
      width: 90,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'skip_count',
      dataKey: 'skip_count',
      title: '跳过',
      width: 90,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'is_abnormal',
      dataKey: 'is_abnormal',
      title: '状态',
      width: 100,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'total_duration_seconds',
      dataKey: 'total_duration_seconds',
      title: '总时长',
      width: 120,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'last_report_at',
      dataKey: 'last_report_at',
      title: '最近上报',
      width: 180,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 120,
      align: 'center',
      headerAlign: 'center',
      showOverflowTooltip: false,
    },
  ];
}
