import { requestClient } from '#/api/request';

export interface SyncLog {
  id: string;
  project_id: string;
  sync_type: string;
  sync_type_display: string;
  status: 'failed' | 'pending' | 'success';
  result_summary: string;
  detail_log: string;
  duration: number;
  sys_create_datetime: string;
  creator_name: string;
}

/**
 * 获取同步日志列表
 */
export function getSyncLogsApi(params: { page: number; pageSize: number }) {
  return requestClient.get<{ items: SyncLog[]; total: number }>(
    '/api/project-manager/sync-logs',
    {
      params,
    },
  );
}
