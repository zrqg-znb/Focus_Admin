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

export interface CodeQualitySummary {
  total_projects: number;
  total_modules: number;
  total_loc: number;
  total_issues: number;
  avg_duplication_rate: number;
  health_score: number;
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
  code_quality: CodeQualitySummary | null;
  iteration: IterationSummary | null;
  dts_summary: DtsSummary | null;
}

export async function getProjectReportApi(projectId: string) {
  return requestClient.get<ProjectReport>(
    `/api/project-manager/report/${projectId}`,
  );
}
