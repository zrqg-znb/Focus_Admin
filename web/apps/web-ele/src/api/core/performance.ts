import { requestClient } from '#/api/request';

export interface PerformanceIndicator {
  id: string;
  code?: string;
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
  project: string;
  module: string;
  chip_type: string;
  date: string;
  data: PerformanceDataUploadItem[];
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

export async function createIndicatorApi(data: any) {
  return requestClient.post('/api/performance/indicators', data);
}

export async function updateIndicatorApi(id: string, data: any) {
  return requestClient.put(`/api/performance/indicators/${id}`, data);
}

export async function deleteIndicatorApi(id: string) {
  return requestClient.delete(`/api/performance/indicators/${id}`);
}

export async function importIndicatorsApi(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  return requestClient.post('/api/performance/indicators/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export async function uploadPerformanceDataApi(data: PerformanceDataUploadPayload) {
  return requestClient.post('/api/performance/data/upload', data);
}

export async function getDashboardDataApi(params?: any) {
  return requestClient.get<PaginatedResponse<PerformanceDashboardItem>>('/api/performance/dashboard', { params });
}

export async function getTrendDataApi(indicatorId: string, days: number = 7) {
  return requestClient.get<any[]>('/api/performance/data/trend', { params: { indicator_id: indicatorId, days } });
}
