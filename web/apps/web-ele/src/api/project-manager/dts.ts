import { requestClient } from '#/api/request';

export interface DtsProjectOverview {
  project_id: string;
  project_name: string;
  project_domain: string;
  project_type: string;
  project_managers: string;
  ws_id: string;
  root_teams_count: number;
  has_data_today: boolean;
}

export interface DtsData {
  di: number;
  target_di: number;
  today_in_di: number;
  today_out_di: number;
  solve_rate: string;
  critical_solve_rate: string;
  suggestion_num: number;
  minor_num: number;
  major_num: number;
  fatal_num: number;
}

export interface DtsTeam {
  id: string;
  team_name: string;
  latest_data: DtsData | null;
  children: DtsTeam[];
}

export interface DtsDashboard {
  project_id: string;
  root_teams: DtsTeam[];
}

export interface DtsPageResult {
  pageNo: number;
  pageSize: number;
  total: number;
  currentPageNo: number;
  npage: boolean;
}

export interface DtsDefect {
  defectNo: string;
  brief: string;
  severity: string;
  currentTeam: string;
  currentHandler: string;
  currentStageStayDay: number;
  progress: string;
}

export interface DtsDefectListResponse {
  pageResult: DtsPageResult;
  dataList: DtsDefect[];
}

export async function getDtsOverviewApi() {
  return requestClient.get<DtsProjectOverview[]>('/api/project-manager/dts/overview');
}

export async function syncDtsApi(projectId: string) {
  return requestClient.post<{ success: boolean; message: string }>(
    `/api/project-manager/dts/sync/${projectId}`,
  );
}

export async function getDtsDashboardApi(projectId: string) {
  return requestClient.get<DtsDashboard>(
    `/api/project-manager/dts/dashboard/${projectId}`,
  );
}

export async function getDtsDetailsApi(
  projectId: string,
  page = 1,
  pageSize = 10,
) {
  return requestClient.get<DtsDefectListResponse>(
    `/api/project-manager/dts/details/${projectId}`,
    { params: { page, page_size: pageSize } },
  );
}
