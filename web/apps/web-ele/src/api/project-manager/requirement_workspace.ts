import { requestClient } from '#/api/request';

export type RequirementWorkspaceFieldKey =
  | 'develop_users'
  | 'due_date'
  | 'planned_test_time'
  | 'test_users'
  | 'workload_kloc'
  | 'workload_man_day';

export interface RequirementWorkspaceFieldOverview {
  field_key: RequirementWorkspaceFieldKey;
  field_label: string;
  applicable_count: number;
  filled_count: number;
  missing_count: number;
  filled_rate: number;
}

export interface RequirementWorkspacePreviewItem {
  project_id: string;
  project_name: string;
  team_name: string;
  requirement_id: string;
  title: string;
  status_code: string;
  status_label: string;
  planned_test_time?: null | string;
  due_date?: null | string;
  completed_time?: null | string;
  accepted_time?: null | string;
  develop_user_display: string;
  test_user_display: string;
}

export interface RequirementWorkspaceMissingPreview {
  planned_test_time: RequirementWorkspacePreviewItem[];
  due_date: RequirementWorkspacePreviewItem[];
  develop_users: RequirementWorkspacePreviewItem[];
  test_users: RequirementWorkspacePreviewItem[];
  workload_man_day: RequirementWorkspacePreviewItem[];
  workload_kloc: RequirementWorkspacePreviewItem[];
}

export interface RequirementWorkspaceDelayPreview {
  development: RequirementWorkspacePreviewItem[];
  acceptance: RequirementWorkspacePreviewItem[];
}

export interface RequirementWorkspaceProjectFieldStat {
  applicable_count: number;
  filled_count: number;
  missing_count: number;
  filled_rate: number;
}

export interface RequirementWorkspaceProjectFields {
  planned_test_time: RequirementWorkspaceProjectFieldStat;
  due_date: RequirementWorkspaceProjectFieldStat;
  develop_users: RequirementWorkspaceProjectFieldStat;
  test_users: RequirementWorkspaceProjectFieldStat;
  workload_man_day: RequirementWorkspaceProjectFieldStat;
  workload_kloc: RequirementWorkspaceProjectFieldStat;
}

export interface RequirementWorkspaceProjectDelay {
  development_count: number;
  development_rate: number;
  acceptance_count: number;
  acceptance_rate: number;
}

export interface RequirementWorkspaceProjectRow {
  project_id: string;
  project_name: string;
  total_count: number;
  fields: RequirementWorkspaceProjectFields;
  delay: RequirementWorkspaceProjectDelay;
  completion_score: number;
}

export interface RequirementWorkspaceRefreshTask {
  id: string;
  scope: string;
  status: 'failed' | 'pending' | 'running' | 'success';
  message: string;
  error_message: string;
  started_at?: null | string;
  finished_at?: null | string;
  snapshot_date?: null | string;
  snapshot_id?: null | string;
}

export interface RequirementWorkspaceLatest {
  generated_at?: null | string;
  scope: string;
  project_count: number;
  requirement_count: number;
  field_overview: RequirementWorkspaceFieldOverview[];
  project_rows: RequirementWorkspaceProjectRow[];
  missing_previews: RequirementWorkspaceMissingPreview;
  delay_previews: RequirementWorkspaceDelayPreview;
  refresh_task?: null | RequirementWorkspaceRefreshTask;
}

const base = '/api/project-manager/requirement-workspace';
export type RequirementWorkspaceScope = 'all' | 'favorites';

export async function getRequirementWorkspaceLatestApi(
  scope: RequirementWorkspaceScope = 'all',
) {
  return requestClient.get<RequirementWorkspaceLatest>(`${base}/latest`, {
    params: { _ts: Date.now(), scope },
  });
}

export async function refreshRequirementWorkspaceApi(
  scope: RequirementWorkspaceScope = 'all',
) {
  return requestClient.post<RequirementWorkspaceRefreshTask>(
    `${base}/refresh`,
    null,
    {
      params: { scope },
    },
  );
}

export async function getRequirementWorkspaceRefreshTaskApi(taskId: string) {
  return requestClient.get<RequirementWorkspaceRefreshTask>(
    `${base}/refresh-task/${taskId}`,
    {
      params: { _ts: Date.now() },
    },
  );
}
