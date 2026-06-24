import { requestClient } from '#/api/request';

const base = '/api/environment-management';

export type EnvironmentDomain = 'cockpit' | 'vehicle';
export type EnvironmentCategory = 'ci' | 'dev' | 'test';
export type EnvironmentStatus = 'idle' | 'occupied';

export interface DeviceTypeItem {
  id: string;
  parent_id?: null | string;
  name: string;
  sort: number;
  is_active: boolean;
  children: DeviceTypeItem[];
}

export interface DeviceTypePayload {
  parent_id?: null | string;
  name: string;
  sort: number;
  is_active: boolean;
}

export interface TestDeviceItem {
  id: string;
  device_type_id: string;
  device_type_name: string;
  device_type_path: string;
  name: string;
  display_name: string;
  sort: number;
  is_active: boolean;
  remark: string;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface TestDevicePayload {
  device_type_id: string;
  name: string;
  sort: number;
  is_active: boolean;
  remark: string;
}

export interface DeviceOptionNode {
  value: string;
  label: string;
  disabled: boolean;
  node_type: 'device' | 'type';
  children: DeviceOptionNode[];
}

export interface EnvironmentAnnouncement {
  id?: null | string;
  title: string;
  content_html: string;
  enabled: boolean;
  updated_at?: null | string;
}

export interface EnvironmentAnnouncementPayload {
  title: string;
  content_html: string;
  enabled: boolean;
}

export interface EnvironmentDeviceBrief {
  id: string;
  device_id?: null | string;
  device_type_id: string;
  device_type_name: string;
  device_type_path: string;
  device_name: string;
  name: string;
  display_name: string;
  asset_number: string;
  remark: string;
  sort: number;
}

export interface EnvironmentDevicePayload {
  device_id: string;
  asset_number: string;
  remark: string;
  sort: number;
}

export interface EnvironmentItem {
  id: string;
  ip_address: string;
  account: string;
  can_view_secret: boolean;
  can_use_environment: boolean;
  domain: EnvironmentDomain;
  domain_label: string;
  category: EnvironmentCategory;
  category_label: string;
  bomid: string;
  project_name: string;
  vehicle_model: string;
  device_ids: string[];
  devices: EnvironmentDeviceBrief[];
  device_display: string;
  config_description: string;
  asset_number: string;
  shelf_location: string;
  remark: string;
  status: EnvironmentStatus;
  status_label: string;
  current_user_id?: null | string;
  current_user_name: string;
  is_current_user_occupying: boolean;
  occupied_at?: null | string;
  occupied_seconds: number;
  is_favorite: boolean;
  queue_count: number;
  my_queue_id?: null | string;
  my_queue_position?: null | number;
  first_queue_user_name: string;
  rdp_url: string;
  rdp_launcher_url: string;
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
  bomid: string;
  project_name: string;
  vehicle_model: string;
  devices: EnvironmentDevicePayload[];
  config_description: string;
  asset_number: string;
  shelf_location: string;
  remark: string;
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

export async function listDeviceTypesApi(params?: { active_only?: boolean }) {
  return requestClient.get<DeviceTypeItem[]>(`${base}/device-types`, {
    params,
  });
}

export async function createDeviceTypeApi(data: DeviceTypePayload) {
  return requestClient.post<DeviceTypeItem[]>(`${base}/device-types`, data);
}

export async function updateDeviceTypeApi(
  id: string,
  data: DeviceTypePayload,
) {
  return requestClient.put<DeviceTypeItem[]>(`${base}/device-types/${id}`, data);
}

export async function deleteDeviceTypeApi(id: string) {
  return requestClient.delete<boolean>(`${base}/device-types/${id}`);
}

export async function listDevicesApi(params?: Record<string, any>) {
  return requestClient.get<TestDeviceItem[]>(`${base}/devices`, { params });
}

export async function createDeviceApi(data: TestDevicePayload) {
  return requestClient.post<TestDeviceItem>(`${base}/devices`, data);
}

export async function updateDeviceApi(id: string, data: TestDevicePayload) {
  return requestClient.put<TestDeviceItem>(`${base}/devices/${id}`, data);
}

export async function deleteDeviceApi(id: string) {
  return requestClient.delete<boolean>(`${base}/devices/${id}`);
}

export async function listDeviceOptionsApi() {
  return requestClient.get<DeviceOptionNode[]>(`${base}/device-options`);
}

export async function getEnvironmentAnnouncementApi() {
  return requestClient.get<EnvironmentAnnouncement>(`${base}/announcement`);
}

export async function saveEnvironmentAnnouncementApi(
  data: EnvironmentAnnouncementPayload,
) {
  return requestClient.put<EnvironmentAnnouncement>(`${base}/announcement`, data);
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
