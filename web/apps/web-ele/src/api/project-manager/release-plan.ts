import { requestClient } from '#/api/request';

export interface ReleasePlanFilterParams {
  branch_name?: string;
  keyword?: string;
  page?: number;
  pageSize?: number;
  platform_keyword?: string;
  project_id?: string;
  release_date_end?: string;
  release_date_start?: string;
  scenario?: 'cockpit' | 'vehicle';
  vehicle_keyword?: string;
  version_type?: string;
}

export interface ReleasePlanItem {
  branch_name: string;
  cdc_platform_id?: null | string;
  cdc_platform_name?: null | string;
  id: string;
  idvp_platform_id?: null | string;
  idvp_platform_name?: null | string;
  manager_names: string[];
  order: number;
  platform_name: string;
  project_code: string;
  project_domain: string;
  project_id: string;
  project_name: string;
  release_date: string;
  release_vehicles: string[];
  scenario: 'cockpit' | 'vehicle';
  version_type: string;
  version_type_label: string;
}

export interface ReleasePlanProjectGroup {
  branch_count: number;
  branch_names: string[];
  latest_release_date?: null | string;
  manager_names: string[];
  next_release_date?: null | string;
  plan_count: number;
  plans: ReleasePlanItem[];
  platform_names: string[];
  project_code: string;
  project_domain: string;
  project_id: string;
  project_name: string;
  release_vehicles: string[];
  version_types: string[];
}

export interface ReleasePlanWeeklyTrend {
  count: number;
  week: string;
  week_start: string;
}

export interface ReleasePlanVersionWeeklyTrend {
  count: number;
  version_type: string;
  week: string;
  week_start: string;
}

export interface ReleasePlanProjectBoard {
  items: ReleasePlanProjectGroup[];
  total: number;
  version_weekly_trend: ReleasePlanVersionWeeklyTrend[];
  weekly_trend: ReleasePlanWeeklyTrend[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

const base = '/api/project-manager/release-plans';

export async function listReleasePlansApi(params?: ReleasePlanFilterParams) {
  return requestClient.get<PaginatedResponse<ReleasePlanItem>>(`${base}/`, {
    params,
  });
}

export async function getReleasePlanProjectBoardApi(
  params?: ReleasePlanFilterParams,
) {
  return requestClient.get<ReleasePlanProjectBoard>(`${base}/project-board`, {
    params,
  });
}
