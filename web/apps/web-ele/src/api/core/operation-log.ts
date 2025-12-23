import type { PaginatedResponse } from './user';

import { requestClient } from '#/api/request';

export interface OperationLog {
  id: string;
  request_username: string;
  request_ip: string;
  request_method: string;
  request_path: string;
  request_modular?: string;
  request_body?: Record<string, any> | null;
  response_code?: number | null;
  request_os?: string;
  request_browser?: string;
  request_msg?: string;
  status: boolean;
  json_result?: Record<string, any> | null;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface OperationLogListParams {
  page?: number;
  pageSize?: number;
  request_username?: string;
  request_ip?: string;
  request_method?: string;
  request_path?: string;
  request_modular?: string;
  status?: boolean;
  response_code?: number;
}

export async function getOperationLogListApi(params?: OperationLogListParams) {
  return requestClient.get<PaginatedResponse<OperationLog>>(
    '/api/core/operation-log',
    { params },
  );
}

export async function getOperationLogDetailApi(logId: string) {
  return requestClient.get<OperationLog>(`/api/core/operation-log/${logId}`);
}

export async function deleteOperationLogApi(logId: string) {
  return requestClient.delete(`/api/core/operation-log/${logId}`);
}

export async function batchDeleteOperationLogApi(ids: string[]) {
  return requestClient.delete('/api/core/operation-log/batch/delete', {
    params: { ids },
  });
}

