import { requestClient } from '#/api/request';

export interface CmcDateRange {
  endDate: string;
  startDate: string;
}
export interface CmcSummary {
  cnt_total: number;
  zero_comment_mr_count: number;
  zero_comment_rate: number;
  effective_comment_count: number;
  effective_comment_density: null | number;
  checked_mr_lines: number;
  cmt_lines: number;
  contributor_count: number;
  major_comments_cnt: number;
  fatal_comments_cnt: number;
  minor_comments_cnt: number;
  sugge_comments_cnt: number;
  cmt_issue: number;
}
export interface CmcPersonRecord extends Omit<CmcSummary, 'contributor_count'> {
  user: string;
}
export interface CmcPersonPage {
  items: CmcPersonRecord[];
  total: number;
}
export interface CmcTrendPoint {
  checked_mr_lines: number;
  cnt_total: number;
  date: string;
  effective_comment_count: number;
  zero_comment_mr_count: number;
}
export interface CmcPersonRanking {
  checked_mr_lines: number;
  cnt_total: number;
  effective_comment_count: number;
  effective_comment_density: null | number;
  user: string;
}
export interface CmcCommentDistribution {
  label: string;
  value: number;
}
export interface CmcSyncTask {
  id: string;
  trigger_type: string;
  status: 'failed' | 'pending' | 'running' | 'success';
  start_date: string;
  end_date: string;
  requested_dates: string[];
  synced_dates: string[];
  fetched_pages: number;
  fetched_rows: number;
  error_message: string;
  started_at?: null | string;
  finished_at?: null | string;
}

const base = '/api/cmc-contribution';
export const getCmcSummary = (params: CmcDateRange) =>
  requestClient.get<CmcSummary>(`${base}/dashboard/summary`, { params });
export const getCmcTrend = (params: CmcDateRange) =>
  requestClient.get<CmcTrendPoint[]>(`${base}/dashboard/trend`, { params });
export const getCmcPersonRanking = (params: CmcDateRange) =>
  requestClient.get<CmcPersonRanking[]>(`${base}/dashboard/person-ranking`, {
    params,
  });
export const getCmcCommentDistribution = (params: CmcDateRange) =>
  requestClient.get<CmcCommentDistribution[]>(
    `${base}/dashboard/comment-distribution`,
    { params },
  );
export const listCmcPersons = (
  params: CmcDateRange & {
    page: number;
    pageSize: number;
    sortField?: string;
    sortOrder?: 'asc' | 'desc';
    userKeyword?: string;
  },
) => requestClient.get<CmcPersonPage>(`${base}/persons`, { params });
export const createCmcSyncTask = (data: CmcDateRange) =>
  requestClient.post<CmcSyncTask>(`${base}/sync-tasks`, data);
export const getCmcSyncTask = (id: string) =>
  requestClient.get<CmcSyncTask>(`${base}/sync-tasks/${id}`);
