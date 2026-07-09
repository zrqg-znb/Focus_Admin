import { requestClient } from '#/api/request';

export interface ProjectOut {
  id: string;
  name: string;
  domain: string;
  type: string;
  code: string;
  managers_info: { id: string; name: string }[];
  is_closed: boolean;
  repo_url?: string;
  power_info_link?: ProjectVehicleLinkItem[] | string;
  hardware_software_interface_doc?: ProjectVehicleLinkItem[] | string;
  remark?: string;
  enable_milestone: boolean;
  enable_iteration: boolean;
  enable_iteration_quality_metrics: boolean;
  iteration_quality_oem_name?: null | string;
  iteration_quality_module?: null | string;
  enable_quality: boolean;
  enable_dts: boolean;
  enable_hardware_config: boolean;
  design_id?: null | string;
  sub_teams?: string[];
  viu_platform_id?: string;
  viu_platform_name?: string;
  idvp_platform_id?: string;
  idvp_platform_name?: string;
  phase_configs?: ProjectPhaseConfig[];
  release_plans?: ProjectReleasePlan[];
  ws_id?: string;
  version_c?: null | string;
  di_teams?: string[];
  sys_create_datetime?: string;
  is_favorited: boolean;
}

export interface ProjectVehicleLinkItem {
  chip_name: string;
  url: string;
}

export interface VehicleHardwareItem {
  point: string;
  board: string;
  config_type: string;
  bomid: string;
}

export interface ProjectPhaseConfig {
  id?: string;
  stage_name: string;
  stage_start?: string;
  stage_end?: string;
  scenario?: 'cockpit' | 'vehicle';
  vehicle_hardware?: VehicleHardwareItem[];
  cdc_platform_id?: string;
  cdc_platform_name?: string;
  smart_screen_version_id?: string;
  smart_screen_version_name?: string;
  smart_screen_version_ids?: string[];
  smart_screen_version_names?: string[];
}

export interface ProjectReleasePlan {
  branch_name: string;
  cdc_platform_id?: null | string;
  cdc_platform_name?: null | string;
  id?: string;
  idvp_platform_id?: null | string;
  idvp_platform_name?: null | string;
  order?: number;
  platform_name?: string;
  release_date: string;
  release_vehicles: string[];
  scenario?: 'cockpit' | 'vehicle';
  version_type: string;
  version_type_label?: string;
}

export interface ProjectCreatePayload {
  name: string;
  domain: string;
  type: string;
  code: string;
  manager_ids: string[];
  is_closed?: boolean;
  repo_url?: string;
  power_info_link?: ProjectVehicleLinkItem[];
  hardware_software_interface_doc?: ProjectVehicleLinkItem[];
  remark?: string;
  enable_milestone?: boolean;
  enable_iteration?: boolean;
  enable_iteration_quality_metrics?: boolean;
  iteration_quality_oem_name?: null | string;
  iteration_quality_module?: null | string;
  enable_quality?: boolean;
  enable_dts?: boolean;
  enable_hardware_config?: boolean;
  design_id?: null | string;
  sub_teams?: string[];
  idvp_platform_id?: string;
  phase_configs?: ProjectPhaseConfig[];
  release_plans?: ProjectReleasePlan[];
  ws_id?: string;
  version_c?: null | string;
  di_teams?: string[];
}

export interface ProjectUpdatePayload {
  name?: string;
  domain?: string;
  type?: string;
  code?: string;
  manager_ids?: string[];
  is_closed?: boolean;
  repo_url?: string;
  power_info_link?: ProjectVehicleLinkItem[];
  hardware_software_interface_doc?: ProjectVehicleLinkItem[];
  remark?: string;
  enable_milestone?: boolean;
  enable_iteration?: boolean;
  enable_iteration_quality_metrics?: boolean;
  iteration_quality_oem_name?: null | string;
  iteration_quality_module?: null | string;
  enable_quality?: boolean;
  enable_dts?: boolean;
  enable_hardware_config?: boolean;
  design_id?: null | string;
  sub_teams?: string[];
  idvp_platform_id?: string;
  phase_configs?: ProjectPhaseConfig[];
  release_plans?: ProjectReleasePlan[];
  ws_id?: string;
  version_c?: null | string;
  di_teams?: string[];
}

export interface ProjectFilterParams {
  hardware_scenario?: 'cockpit' | 'vehicle';
  keyword?: string;
  domain?: string;
  type?: string;
  manager_id?: string;
  idvp_platform_keyword?: string;
  cdc_platform_keyword?: string;
  smart_screen_keyword?: string;
  is_closed?: boolean;
  enable_milestone?: boolean;
  enable_iteration?: boolean;
  enable_quality?: boolean;
  enable_dts?: boolean;
  enable_hardware_config?: boolean;
  page?: number;
  pageSize?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}

const listEndpoint = '/api/project-manager/projects/';

export async function listProjectsApi(params?: ProjectFilterParams) {
  return requestClient.get<PaginatedResponse<ProjectOut>>(listEndpoint, {
    params,
  });
}

export async function createProjectApi(data: ProjectCreatePayload) {
  return requestClient.post<ProjectOut>(listEndpoint, data);
}

export async function updateProjectApi(id: string, data: ProjectUpdatePayload) {
  return requestClient.put<ProjectOut>(
    `/api/project-manager/projects/${id}`,
    data,
  );
}

export async function deleteProjectApi(id: string) {
  return requestClient.delete(`/api/project-manager/projects/${id}`);
}

export async function getProjectApi(id: string) {
  return requestClient.get<ProjectOut>(`/api/project-manager/projects/${id}`);
}

export async function favoriteProjectApi(id: string) {
  return requestClient.post<boolean>(
    `/api/project-manager/projects/${id}/favorite`,
  );
}

export async function unfavoriteProjectApi(id: string) {
  return requestClient.delete<boolean>(
    `/api/project-manager/projects/${id}/favorite`,
  );
}
