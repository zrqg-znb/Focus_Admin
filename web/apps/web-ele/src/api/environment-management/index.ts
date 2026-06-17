import { requestClient } from '#/api/request';

const base = '/api/environment-management';

export type EnvironmentDomain = 'cockpit' | 'vehicle';
export type EnvironmentCategory = 'ci' | 'dev' | 'test';
export type EnvironmentStatus = 'idle' | 'occupied';

export interface EnvironmentItem {
  id: string;
  ip_address: string;
  account: string;
  password: string;
  can_view_secret: boolean;
  can_use_environment: boolean;
  domain: EnvironmentDomain;
  domain_label: string;
  category: EnvironmentCategory;
  category_label: string;
  project_name: string;
  vehicle_model: string;
  device_material: string;
  asset_number: string;
  device_display: string;
  config: Record<string, any>;
  shelf_location: string;
  status: EnvironmentStatus;
  status_label: string;
  current_user_id?: null | string;
  current_user_name: string;
  occupied_at?: null | string;
  occupied_seconds: number;
  is_favorite: boolean;
  queue_count: number;
  my_queue_id?: null | string;
  my_queue_position?: null | number;
  first_queue_user_name: string;
  rdp_url: string;
  sort: number;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface EnvironmentPayload {
  ip_address: string;
  account: string;
  password?: null | string;
  domain: EnvironmentDomain;
  category: EnvironmentCategory;
  project_name: string;
  vehicle_model: string;
  device_material: string;
  asset_number: string;
  config: Record<string, any>;
  shelf_location: string;
  sort: number;
}

export interface EnvironmentPage {
  items: EnvironmentItem[];
  total: number;
  page: number;
  limit: number;
}

export interface EnvironmentActionResult {
  success: boolean;
  message: string;
  environment: EnvironmentItem;
}

export interface QueueItem {
  id: string;
  user_id: string;
  user_name: string;
  queue_type: 'jump' | 'normal';
  queue_type_label: string;
  position: number;
  requested_at: string;
  is_me: boolean;
}

export interface EnvironmentRecord {
  id: string;
  operator_id?: null | string;
  operator_name: string;
  action: string;
  action_label: string;
  message: string;
  started_at?: null | string;
  ended_at?: null | string;
  duration_seconds: number;
  sys_create_datetime: string;
}

export interface RecordPage {
  items: EnvironmentRecord[];
  total: number;
  page: number;
  limit: number;
}

export async function listEnvironmentsApi(params?: Record<string, any>) {
  return requestClient.get<EnvironmentPage>(`${base}/environments`, {
    params,
  });
}

export async function createEnvironmentApi(data: EnvironmentPayload) {
  return requestClient.post<EnvironmentItem>(`${base}/environments`, data);
}

export async function updateEnvironmentApi(
  id: string,
  data: EnvironmentPayload,
) {
  return requestClient.put<EnvironmentItem>(`${base}/environments/${id}`, data);
}

export async function deleteEnvironmentApi(id: string) {
  return requestClient.delete<boolean>(`${base}/environments/${id}`);
}

export async function favoriteEnvironmentApi(id: string) {
  return requestClient.post<EnvironmentItem>(
    `${base}/environments/${id}/favorite`,
  );
}

export async function unfavoriteEnvironmentApi(id: string) {
  return requestClient.delete<EnvironmentItem>(
    `${base}/environments/${id}/favorite`,
  );
}

export async function occupyEnvironmentApi(id: string) {
  return requestClient.post<EnvironmentActionResult>(
    `${base}/environments/${id}/occupy`,
  );
}

export async function releaseEnvironmentApi(id: string) {
  return requestClient.post<EnvironmentActionResult>(
    `${base}/environments/${id}/release`,
  );
}

export async function queueEnvironmentApi(id: string) {
  return requestClient.post<EnvironmentItem>(
    `${base}/environments/${id}/queue`,
  );
}

export async function jumpQueueEnvironmentApi(id: string) {
  return requestClient.post<EnvironmentItem>(
    `${base}/environments/${id}/jump-queue`,
  );
}

export async function cancelMyQueueApi(id: string) {
  return requestClient.delete<EnvironmentItem>(
    `${base}/environments/${id}/queue/me`,
  );
}

export async function listEnvironmentQueueApi(id: string) {
  return requestClient.get<QueueItem[]>(`${base}/environments/${id}/queue`);
}

export async function listEnvironmentRecordsApi(
  id: string,
  params?: Record<string, any>,
) {
  return requestClient.get<RecordPage>(`${base}/environments/${id}/records`, {
    params,
  });
}
