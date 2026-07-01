import type { AutoTestReportDomain } from '../shared/domain';

import type {
  DailyOverviewRow,
  DailyResultItem,
  DownstreamCommitItem,
  DownstreamCommitUsageItem,
} from '#/api/auto-test-report';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { getAutoTestReportDomainMeta } from '../shared/domain';

export const RESULT_LABEL_MAP: Record<string, string> = {
  success: '成功',
  failed: '失败',
  timeout: '超时',
  skip: '跳过',
  missing: '未执行',
};

export const RESULT_TAG_MAP: Record<
  string,
  'danger' | 'info' | 'success' | 'warning'
> = {
  success: 'success',
  failed: 'danger',
  timeout: 'warning',
  skip: 'info',
  missing: 'info',
};

export const FAILURE_CATEGORY_LABEL_MAP: Record<string, string> = {
  version: '版本问题',
  environment: '环境问题',
  case: '用例问题',
};

export const FAILURE_CATEGORY_OPTIONS = Object.entries(
  FAILURE_CATEGORY_LABEL_MAP,
).map(([value, label]) => ({ label, value }));

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

export function useResultColumns(
  domain: AutoTestReportDomain,
): ZqTableGridOptions<DailyResultItem>['columns'] {
  const columns: ZqTableGridOptions<DailyResultItem>['columns'] = [
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
  ];

  if (domain === 'vehicle') {
    columns.push({
      key: 'viu_code',
      dataKey: 'viu_code',
      title: 'VIU编号',
      width: 120,
      align: 'center',
      headerAlign: 'center',
    });
  }

  columns.push(
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
      key: 'failure_category',
      dataKey: 'failure_category',
      title: '根因大类',
      width: 150,
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
      sortable: true,
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
      key: 'car_log_url',
      dataKey: 'car_log_url',
      title: '车机日志',
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
  );

  return columns;
}

export function useOverviewColumns(
  domain: AutoTestReportDomain,
): ZqTableGridOptions<DailyOverviewRow>['columns'] {
  const domainMeta = getAutoTestReportDomainMeta(domain);
  return [
    {
      key: 'platform_name',
      dataKey: 'platform_name',
      title: domainMeta.platformLabel,
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
      key: 'non_version_failure_count',
      dataKey: 'non_version_failure_count',
      title: '非版本问题失败数',
      width: 160,
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
      key: 'missing_result_count',
      dataKey: 'missing_result_count',
      title: '未执行',
      width: 100,
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

export function useCommitColumns(): ZqTableGridOptions<DownstreamCommitItem>['columns'] {
  return [
    {
      key: 'commit_id',
      dataKey: 'commit_id',
      title: 'Commit ID',
      width: 240,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'upload_count',
      dataKey: 'upload_count',
      title: '上传次数',
      width: 100,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'use_count',
      dataKey: 'use_count',
      title: '使用次数',
      width: 100,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'first_uploaded_at',
      dataKey: 'first_uploaded_at',
      title: '首次上传',
      width: 180,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'last_uploaded_at',
      dataKey: 'last_uploaded_at',
      title: '最近上传',
      width: 180,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'last_used_at',
      dataKey: 'last_used_at',
      title: '最近使用',
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

export function useCommitUsageColumns(): ZqTableGridOptions<DownstreamCommitUsageItem>['columns'] {
  return [
    {
      key: 'execute_date',
      dataKey: 'execute_date',
      title: '执行日期',
      width: 120,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'trigger_type',
      dataKey: 'trigger_type',
      title: '触发方式',
      width: 110,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'trigger_user_name',
      dataKey: 'trigger_user_name',
      title: '触发人',
      width: 120,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'success',
      dataKey: 'success',
      title: '结果',
      width: 100,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'message',
      dataKey: 'message',
      title: '消息',
      width: 320,
      align: 'center',
      headerAlign: 'center',
    },
    {
      key: 'used_at',
      dataKey: 'used_at',
      title: '使用时间',
      width: 180,
      align: 'center',
      headerAlign: 'center',
    },
  ];
}
