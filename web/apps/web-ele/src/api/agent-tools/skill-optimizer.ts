import { requestClient } from '#/api/request';

const base = '/api/agent-tools/skill-optimizer';
const configGenerationTimeout = 2 * 60 * 1000;

export interface PageResult<T> {
  items: T[];
  total: number;
}
export interface Skill {
  id: string;
  name: string;
  description: string;
  original_filename: string;
  file_manifest: string[];
  sys_creator_name: string;
  sys_create_datetime?: string;
}
export interface Scenario {
  id: number;
  name: string;
  input: string;
}
export interface Evaluation {
  id: number;
  name: string;
  question: string;
  pass_condition: string;
}
export interface SkillRun {
  id: string;
  skill_id: string;
  skill_name: string;
  provider_id: string;
  provider_name: string;
  provider_model: string;
  status: string;
  max_rounds: number;
  scenarios: Scenario[];
  evaluations: Evaluation[];
  baseline_score: number;
  final_score: number;
  original_skill_md: string;
  improved_skill_md: string;
  error_message: string;
  cancel_requested: boolean;
  queued_at?: string;
  started_at?: string;
  completed_at?: string;
  sys_creator_name: string;
  sys_create_datetime?: string;
}
export interface Iteration {
  id: string;
  round_number: number;
  status: string;
  score_before: number;
  score_after: number;
  kept: boolean;
  strategy: string;
  diagnosis: string;
  description: string;
  evaluation_summary: Record<string, unknown>[];
  sys_create_datetime?: string;
}
export interface SkillTrace {
  id: string;
  round_number: number;
  stage: string;
  status: string;
  request_content: string;
  response_content: string;
  error_message: string;
  duration_ms: number;
  sys_create_datetime?: string;
}

export const listSkillsApi = (params: {
  keyword?: string;
  page?: number;
  pageSize?: number;
}) => requestClient.get<PageResult<Skill>>(`${base}/skills`, { params });
export const uploadSkillApi = (file: File) => {
  return requestClient.upload<Skill>(`${base}/skills/upload`, { file });
};
export const createRunApi = (data: {
  max_rounds: number;
  provider_id: string;
  skill_id: string;
}) => requestClient.post<SkillRun>(`${base}/runs`, data);
export const listRunsApi = (params: {
  page?: number;
  pageSize?: number;
  provider_id?: string;
  status?: string;
}) => requestClient.get<PageResult<SkillRun>>(`${base}/runs`, { params });
export const getRunApi = (id: string) =>
  requestClient.get<SkillRun>(`${base}/runs/${id}`);
export const saveRunConfigApi = (
  id: string,
  data: { evaluations: Evaluation[]; scenarios: Scenario[] },
) => requestClient.put<SkillRun>(`${base}/runs/${id}/config`, data);
export const regenerateRunConfigApi = (id: string) =>
  requestClient.post<SkillRun>(
    `${base}/runs/${id}/config/regenerate`,
    undefined,
    {
      timeout: configGenerationTimeout,
    },
  );
export const startRunApi = (id: string) =>
  requestClient.post<SkillRun>(`${base}/runs/${id}/start`);
export const cancelRunApi = (id: string) =>
  requestClient.post<SkillRun>(`${base}/runs/${id}/cancel`);
export const listIterationsApi = (id: string) =>
  requestClient.get<Iteration[]>(`${base}/runs/${id}/iterations`);
export const listTracesApi = (id: string) =>
  requestClient.get<SkillTrace[]>(`${base}/runs/${id}/traces`);
export const downloadRunUrl = (id: string) => `${base}/runs/${id}/download`;
export const downloadRunApi = (id: string) =>
  requestClient.get<Blob>(downloadRunUrl(id), { responseType: 'blob' });
