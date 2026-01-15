import { requestClient } from '#/api/request';

export interface RadarIndicator {
  name: string;
  value: number;
  max: number;
}

export interface QGNode {
  name: string;
  date: string;
  status: string;
  has_risk?: boolean;
}

export interface DtsTrendItem {
  date: string;
  critical: number;
  major: number;
  minor: number;
  suggestion: number;
  solve_rate: number;
  critical_solve_rate: number;
}

export interface DtsTeamDiItem {
  team_name: string;
  di: number;
  target_di?: number | null;
}

export interface DtsTeamDiSeries {
  team_name: string;
  values: Array<number | null>;
}

export interface DtsTeamDiTrend {
  dates: string[];
  series: DtsTeamDiSeries[];
}

export interface IterationDetailMetrics {
  sr_num: number;
  dr_num: number;
  ar_num: number;
  sr_breakdown_rate: number;
  dr_breakdown_rate: number;
  ar_set_a_rate: number;
  dr_set_a_rate: number;
  ar_set_c_rate: number;
  dr_set_c_rate: number;
}

export interface CodeQualitySummary {
  total_projects: number;
  total_modules: number;
  total_loc: number;
  total_issues: number;
  avg_duplication_rate: number;
  health_score: number;
}

export interface CodeQualityModuleDetail {
  id: string;
  oem_name: string;
  module: string;
  owner_names: string[];
  owner_ids: string[];
  record_date?: string | null;
  loc: number;
  function_count: number;
  dangerous_func_count: number;
  duplication_rate: number;
  is_clean_code: boolean;
}

export interface IterationSummary {
  active_iterations: number;
  delayed_iterations: number;
  total_req_count: number;
  completion_rate: number;
}

export interface DtsSummary {
  total_issues: number;
  critical_issues: number;
  avg_solve_time: number;
  solve_rate: number;
}

export interface ProjectReport {
  project_id: string;
  project_name: string;
  manager: string;
  health_score: number;
  health_level: 'healthy' | 'warning' | 'error';
  radar_data: RadarIndicator[];
  milestones: QGNode[];
  dts_trend: DtsTrendItem[];
  dts_team_di?: DtsTeamDiItem[] | null;
  dts_team_di_trend?: DtsTeamDiTrend | null;
  code_quality: CodeQualitySummary | null;
  code_quality_details?: CodeQualityModuleDetail[] | null;
  iteration: IterationSummary | null;
  iteration_detail?: IterationDetailMetrics | null;
  dts_summary: DtsSummary | null;
}

export async function getProjectReportApi(projectId: string) {
  return requestClient.get<ProjectReport>(
    `/api/project-manager/report/${projectId}`,
  );
}
