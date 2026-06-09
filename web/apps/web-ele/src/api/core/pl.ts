import { requestClient } from '#/api/request';

export interface PlGroup {
  id: string;
  name: string;
  code?: string;
  status: boolean;
  description?: string;
  sort: number;
  pl_user_id: string;
  pl_user_name?: string;
  pl_user_username: string;
  member_count: number;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface PlGroupCreateInput {
  name: string;
  code?: string;
  status?: boolean;
  description?: string;
  sort?: number;
  pl_user_id: string;
}

export type PlGroupUpdateInput = Partial<PlGroupCreateInput>;

export interface PlGroupBatchDeleteInput {
  ids: string[];
}

export interface PlGroupBatchUpdateStatusInput {
  ids: string[];
  status: boolean;
}

export interface PlGroupListParams {
  page?: number;
  pageSize?: number;
  name?: string;
  code?: string;
  status?: boolean;
}

export interface PlGroupUser {
  id: string;
  username: string;
  name?: string;
  avatar?: string;
  email?: string;
  dept_name?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page?: number;
  pageSize?: number;
}

export async function createPlApi(data: PlGroupCreateInput) {
  return requestClient.post<PlGroup>('/api/core/pl', data);
}

export async function getPlListApi(params?: PlGroupListParams) {
  return requestClient.get<PaginatedResponse<PlGroup>>('/api/core/pl', {
    params,
  });
}

export async function getAllPlApi() {
  return requestClient.get<PlGroup[]>('/api/core/pl/all');
}

export async function getPlDetailApi(plId: string) {
  return requestClient.get<PlGroup>(`/api/core/pl/${plId}`);
}

export async function updatePlApi(plId: string, data: PlGroupUpdateInput) {
  return requestClient.put<PlGroup>(`/api/core/pl/${plId}`, data);
}

export async function patchPlApi(plId: string, data: PlGroupUpdateInput) {
  return requestClient.request<PlGroup>(`/api/core/pl/${plId}`, {
    data,
    method: 'PATCH',
  });
}

export async function deletePlApi(plId: string) {
  return requestClient.delete<PlGroup>(`/api/core/pl/${plId}`);
}

export async function batchDeletePlApi(data: PlGroupBatchDeleteInput) {
  return requestClient.post<{ count: number; failed_ids: string[] }>(
    '/api/core/pl/batch/delete',
    data,
  );
}

export async function batchUpdatePlStatusApi(
  data: PlGroupBatchUpdateStatusInput,
) {
  return requestClient.post<{ count: number }>(
    '/api/core/pl/batch/update-status',
    data,
  );
}

export async function getPlUsersApi(
  plId: string,
  params?: { name?: string; page?: number; pageSize?: number },
) {
  return requestClient.get<PaginatedResponse<PlGroupUser>>(
    `/api/core/pl/users/${plId}`,
    { params },
  );
}

export async function addPlUsersApi(
  plId: string,
  data: { user_ids: string[] },
) {
  return requestClient.post<{ count: number }>(
    `/api/core/pl/users/${plId}`,
    data,
  );
}

export async function removePlUsersApi(
  plId: string,
  data: { user_ids: string[] },
) {
  return requestClient.delete<{ count: number }>(`/api/core/pl/users/${plId}`, {
    data,
  });
}
