import { requestClient } from '#/api/request';

export interface PerformanceIndicator {
  id: string;
  code?: string;
  category: 'vehicle' | 'cockpit';
  name: string;
  module: string;
  project: string;
  chip_type: string;
  value_type: 'avg' | 'min' | 'max';
  baseline_value: number;
  baseline_unit: string;
  fluctuation_range: number;
  fluctuation_direction: 'up' | 'down' | 'none';
  owner_id?: string;
  owner_name?: string;
  sys_create_datetime?: string;
}

export interface PerformanceIndicatorData {
  id: string;
  indicator_id: string;
  date: string;
  value: number;
  fluctuation_value: number;
}

export interface PerformanceDashboardItem {
  id: string;
  name: string;
  code?: string;
  project: string;
  module: string;
  chip_type: string;
  baseline_value: number;
  baseline_unit: string;
  fluctuation_range: number;
  fluctuation_direction: string;
  current_value?: number;
  fluctuation_value?: number;
  data_date?: string;
  owner_name?: string;
}

export interface PerformanceDataUploadItem {
  code?: string;
  name?: string;
  value: number;
}

export interface PerformanceDataUploadPayload {
  category?: 'vehicle' | 'cockpit';
  project: string;
  module: string;
  chip_type: string;
  date: string;
  data: PerformanceDataUploadItem[];
}

export interface PerformanceTreeNode {
  key: string;
  label: string;
  type: 'category' | 'project' | 'module';
  children: PerformanceTreeNode[];
}

export interface PerformanceChipType {
  chip_type: string;
}

export interface PerformanceImportTaskStartResponse {
  task_id: string;
}

export interface PerformanceImportTask {
  id: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  progress: number;
  filename: string;
  total_rows?: number | null;
  processed_rows: number;
  success_count: number;
  error_count: number;
  message?: string;
  errors?: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}

export async function getIndicatorListApi(params?: any) {
  return requestClient.get<PaginatedResponse<PerformanceIndicator>>('/api/performance/indicators', { params });
}

export async function getIndicatorTreeApi() {
  return requestClient.get<PerformanceTreeNode[]>('/api/performance/tree');
}

export async function getChipTypesApi(params?: {
  category?: string;
  project?: string;
  module?: string;
}) {
  return requestClient.get<PerformanceChipType[]>('/api/performance/chip-types', { params });
}

export async function createIndicatorApi(data: any) {
  return requestClient.post('/api/performance/indicators', data);
}

export async function updateIndicatorApi(id: string, data: any) {
  return requestClient.put(`/api/performance/indicators/${id}`, data);
}

export async function deleteIndicatorApi(id: string) {
  return requestClient.delete(`/api/performance/indicators/${id}`);
}

export async function startIndicatorImportTaskApi(
  file: File,
  options?: { timeout?: number; onUploadProgress?: (evt: any) => void },
) {
  const formData = new FormData();
  formData.append('file', file);
  return requestClient.post<PerformanceImportTaskStartResponse>(
    '/api/performance/indicators/import',
    formData,
    {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: options?.timeout,
    onUploadProgress: options?.onUploadProgress,
    },
  );
}

export async function getIndicatorImportTaskApi(taskId: string) {
  return requestClient.get<PerformanceImportTask>(`/api/performance/indicators/import/${taskId}`);
}

export async function uploadPerformanceDataApi(data: PerformanceDataUploadPayload) {
  return requestClient.post('/api/performance/data/upload', data);
}

export async function getDashboardDataApi(params?: any) {
  return requestClient.get<PaginatedResponse<PerformanceDashboardItem>>('/api/performance/dashboard', { params });
}

export async function getTrendDataApi(
  indicatorId: string,
  params?: { days?: number; start_date?: string; end_date?: string },
) {
  return requestClient.get<any[]>('/api/performance/data/trend', {
    params: { indicator_id: indicatorId, days: params?.days ?? 7, ...params },
  });
}
