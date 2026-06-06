import { requestClient } from '#/api/request';

import type {
  OrganizationItem,
  RepositoryItem,
  RepositoryListParams,
} from './base';

export type MissingMergeStatus = 'fixed' | 'ignored' | 'open';
export type MissingMergeScanStatus =
  | 'failed'
  | 'pending'
  | 'running'
  | 'success';
export type MissingMergeTriggerType = 'manual' | 'scheduled';
export type MissingMergeOperationSource = 'manual' | 'system';
export type MissingMergeOperationType =
  | 'auto_closed'
  | 'detected'
  | 'manual_handle'
  | 'reopened';

export interface MissingMergeOperationLogItem {
  from_status: string;
  from_status_label: string;
  id: string;
  operated_at: string;
  operation_type: MissingMergeOperationType;
  operation_type_label: string;
  operator_id?: null | string;
  operator_name: string;
  remark: string;
  source: MissingMergeOperationSource;
  source_label: string;
  to_status: string;
  to_status_label: string;
}

export interface MissingMergeRecordItem {
  added_lines: number;
  author_username: string;
  change_key: string;
  change_request_iid: string;
  description: string;
  detected_at: string;
  handle_remark: string;
  handled_at?: null | string;
  handled_by_id?: null | string;
  handled_by_name?: null | string;
  id: string;
  merged_at?: null | string;
  operation_logs: MissingMergeOperationLogItem[];
  organization_group_id: string;
  organization_id?: null | string;
  organization_name: string;
  project_id: string;
  release_branch: string;
  removed_lines: number;
  repository_id?: null | string;
  repository_name: string;
  repository_project_id: string;
  status: MissingMergeStatus;
  status_label: string;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
  target_branch: string;
  title: string;
  trunk_branch: string;
  web_url: string;
}

export interface MissingMergeRecordListParams {
  author_username?: string;
  detected_after?: string;
  detected_before?: string;
  keyword?: string;
  merged_after?: string;
  merged_before?: string;
  organization_id?: string;
  organization_ids?: string[];
  page?: number;
  pageSize?: number;
  release_branch?: string;
  repository_id?: string;
  repository_ids?: string[];
  status?: MissingMergeStatus;
  trunk_branch?: string;
}

export interface MissingMergeScanTaskItem {
  created_count: number;
  detected_count: number;
  error_message: string;
  filter_payload: Record<string, any>;
  finished_at?: null | string;
  fixed_count: number;
  id: string;
  merged_after: string;
  merged_before: string;
  scanned_branch_pair_count: number;
  scanned_organization_count: number;
  scanned_repository_count: number;
  started_at?: null | string;
  status: MissingMergeScanStatus;
  status_label: string;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
  trigger_type: MissingMergeTriggerType;
  trigger_type_label: string;
  updated_count: number;
}

export interface MissingMergeScanRunPayload {
  merged_after: string;
  merged_before: string;
  organization_id?: string;
  repository_id?: string;
  repository_ids?: string[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

export interface MissingMergeOptions {
  organizations: OrganizationItem[];
  repositories: RepositoryItem[];
}

const base = '/api/code-compliance/missing-merges';

export function listMissingMergeRecordsApi(
  params?: MissingMergeRecordListParams,
) {
  const normalizedParams = {
    ...params,
    organization_ids: params?.organization_ids?.length
      ? params.organization_ids.join(',')
      : undefined,
    repository_ids: params?.repository_ids?.length
      ? params.repository_ids.join(',')
      : undefined,
  };
  return requestClient.get<PaginatedResponse<MissingMergeRecordItem>>(
    `${base}/records`,
    { params: normalizedParams },
  );
}

export function getMissingMergeRecordApi(id: string) {
  return requestClient.get<MissingMergeRecordItem>(`${base}/records/${id}`);
}

export function listMissingMergeOptionsApi() {
  return requestClient.get<MissingMergeOptions>(`${base}/records/options`);
}

export function listMissingMergeRepositoryOptionsApi(
  params?: Pick<
    RepositoryListParams,
    'keyword' | 'organization_id' | 'page' | 'pageSize'
  >,
) {
  return requestClient.get<PaginatedResponse<RepositoryItem>>(
    `${base}/repositories/options`,
    { params },
  );
}

export function updateMissingMergeRecordStatusApi(
  id: string,
  data: { handle_remark: string; status: MissingMergeStatus },
) {
  return requestClient.put<MissingMergeRecordItem>(
    `${base}/records/${id}/status`,
    data,
  );
}

export function listMissingMergeScanTasksApi(params?: {
  page?: number;
  pageSize?: number;
  status?: MissingMergeScanStatus;
  trigger_type?: MissingMergeTriggerType;
}) {
  return requestClient.get<PaginatedResponse<MissingMergeScanTaskItem>>(
    `${base}/scan-tasks`,
    { params },
  );
}

export function runMissingMergeScanApi(data: MissingMergeScanRunPayload) {
  return requestClient.post<MissingMergeScanTaskItem>(
    `${base}/scan-tasks/run`,
    data,
  );
}
