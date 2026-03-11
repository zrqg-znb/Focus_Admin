import { requestClient } from '#/api/request';

export interface RequirementBoardFilterPayload {
  project_ids: string[];
  sub_teams?: string[];
  categories?: string[];
}

export interface RequirementBoardQuery extends RequirementBoardFilterPayload {
  page_no: number;
  page_size: number;
}

export interface RequirementBoardProjectOption {
  id: string;
  name: string;
  design_id?: null | string;
  sub_teams: string[];
  config_complete: boolean;
}

export interface RequirementBoardFilterOptions {
  projects: RequirementBoardProjectOption[];
}

export interface RequirementBoardItem {
  requirement_id: string;
  title: string;
  category: string;
  status_code: string;
  status_label: string;
  raw_status?: string;
  project_id: string;
  project_name: string;
  design_id?: null | string;
  team_name: string;
  planned_test_time?: null | string;
  due_date?: null | string;
  workload_kloc: number;
  workload_man_day: number;
  develop_user: string;
  test_user: string;
}

export interface RequirementBoardPage {
  items: RequirementBoardItem[];
  total: number;
  page_no: number;
  page_size: number;
  page_sum: number;
}

export interface RequirementStatusSummary {
  status_code: string;
  status_label: string;
  count: number;
}

export interface RequirementTypeSummary {
  category: string;
  total_count: number;
  total_workload_man_day: number;
  total_workload_kloc: number;
}

export interface RequirementProjectSummary {
  project_id: string;
  project_name: string;
  total_count: number;
  total_workload_man_day: number;
  total_workload_kloc: number;
}

export interface RequirementCompletionSummary {
  count: number;
  workload_man_day: number;
  workload_kloc: number;
  count_rate: number;
  workload_man_day_rate: number;
  workload_kloc_rate: number;
}

export interface RequirementTeamSummary {
  team_name: string;
  total_count: number;
  total_workload_man_day: number;
  total_workload_kloc: number;
  i_count: number;
  d_count: number;
  p_count: number;
  c_count: number;
  a_count: number;
  dev_done: RequirementCompletionSummary;
  acceptance_done: RequirementCompletionSummary;
}

export interface RequirementBoardSummary {
  total_count: number;
  total_workload_man_day: number;
  total_workload_kloc: number;
  status_summary: RequirementStatusSummary[];
  type_summary: RequirementTypeSummary[];
  project_summary: RequirementProjectSummary[];
  team_summary: RequirementTeamSummary[];
}

const base = '/api/project-manager/requirement-board';

export async function getRequirementBoardFilterOptionsApi() {
  return requestClient.get<RequirementBoardFilterOptions>(
    `${base}/filter-options`,
  );
}

export async function getRequirementBoardDataApi(data: RequirementBoardQuery) {
  return requestClient.post<RequirementBoardPage>(`${base}/data`, data);
}

export async function getRequirementBoardSummaryApi(
  data: RequirementBoardFilterPayload,
) {
  return requestClient.post<RequirementBoardSummary>(`${base}/summary`, data);
}
