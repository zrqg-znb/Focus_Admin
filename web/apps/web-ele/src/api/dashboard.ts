import { requestClient } from '#/api/request';

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

export interface PerformanceSummary {
  total_indicators: number;
  abnormal_count: number;
  coverage_rate: number;
}

export interface DtsSummary {
  total_issues: number;
  critical_issues: number;
  avg_solve_time: number;
  solve_rate: number;
}

export interface CoreMetrics {
  code_quality: CodeQualitySummary;
  iteration: IterationSummary;
  performance: PerformanceSummary;
  dts: DtsSummary;
}

export interface NameValue {
  name: string;
  value: number;
}

export interface ProjectDistribution {
  by_domain: NameValue[];
  by_type: NameValue[];
}

export interface UpcomingMilestone {
  project_name: string;
  project_manager: string;
  qg_name: string;
  qg_date: string; // ISO Date String
  days_left: number;
}

export interface QGNode {
  name: string;
  date: string;
  status: 'completed' | 'delayed' | 'pending';
}

export interface FavoriteProjectDetail {
  id: string;
  name: string;
  domain: string;
  type: string;
  managers: string;
  loc: number;
  health_score: number;
  current_iteration?: string;
  iteration_progress: number;
  milestones: QGNode[];
}

export interface DashboardSummary {
  code_quality: CodeQualitySummary;
  iteration: IterationSummary;
  performance: PerformanceSummary;
  project_distribution: ProjectDistribution;
  upcoming_milestones: UpcomingMilestone[];
  favorite_projects: FavoriteProjectDetail[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * 获取工作台聚合数据 (Deprecated: use split APIs below)
 */
export function getDashboardSummary() {
  return requestClient.get<DashboardSummary>('/api/dashboard/summary');
}

/**
 * 获取核心指标数据 (代码质量、迭代、性能)
 */
export function getCoreMetrics(scope: 'all' | 'favorites' = 'all') {
  return requestClient.get<CoreMetrics>('/api/dashboard/core-metrics', {
    params: { scope },
  });
}

/**
 * 获取项目分布数据
 */
export function getProjectDistribution(scope: 'all' | 'favorites' = 'all') {
  return requestClient.get<ProjectDistribution>(
    '/api/dashboard/project-distribution',
    { params: { scope } },
  );
}

/**
 * 获取项目里程碑时间轴数据
 */
export function getProjectTimelines(
  scope: 'all' | 'favorites' = 'all',
  page = 1,
  pageSize = 5,
  name?: string,
) {
  return requestClient.get<PaginatedResponse<FavoriteProjectDetail>>(
    '/api/dashboard/project-timelines',
    {
      params: {
        scope,
        page,
        page_size: pageSize,
        name,
      },
    },
  );
}

/**
 * 获取收藏项目详情 (Legacy alias)
 */
export function getFavoriteProjects() {
  // Use default page 1, size 20 or similar for legacy support if needed, but return type changed.
  // Assuming legacy callers can handle the new structure or we wrap it.
  // For simplicity, let's just return the new structure.
  return getProjectTimelines('favorites', 1, 100);
}

/**
 * 获取即将到达的里程碑（支持筛选）
 * @param qg_types 筛选的 QG 类型列表，如 ["QG1", "QG3"]
 */
export function getUpcomingMilestones(
  qg_types?: string[],
  scope: 'all' | 'favorites' = 'all',
  page = 1,
  pageSize = 5,
) {
  return requestClient.get<PaginatedResponse<UpcomingMilestone>>(
    '/api/dashboard/milestones',
    {
      params: {
        qg_types,
        scope,
        page,
        page_size: pageSize,
      },
      // 自定义参数序列化，解决 Django Ninja 不识别 array[] 格式的问题
      paramsSerializer: (params) => {
        const searchParams = new URLSearchParams();
        Object.keys(params).forEach((key) => {
          const value = params[key];
          if (value === undefined || value === null) {
            return;
          }
          if (Array.isArray(value)) {
            value.forEach((v) => searchParams.append(key, v));
          } else {
            searchParams.append(key, value);
          }
        });
        return searchParams.toString();
      },
    },
  );
}
