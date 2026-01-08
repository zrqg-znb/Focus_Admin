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

export interface CoreMetrics {
  code_quality: CodeQualitySummary;
  iteration: IterationSummary;
  performance: PerformanceSummary;
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
  status: 'completed' | 'pending' | 'delayed';
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

/**
 * 获取工作台聚合数据 (Deprecated: use split APIs below)
 */
export function getDashboardSummary() {
  return requestClient.get<DashboardSummary>('/api/dashboard/summary');
}

/**
 * 获取核心指标数据 (代码质量、迭代、性能)
 */
export function getCoreMetrics() {
  return requestClient.get<CoreMetrics>('/api/dashboard/core-metrics');
}

/**
 * 获取项目分布数据
 */
export function getProjectDistribution() {
  return requestClient.get<ProjectDistribution>('/api/dashboard/project-distribution');
}

/**
 * 获取收藏项目详情
 */
export function getFavoriteProjects() {
  return requestClient.get<FavoriteProjectDetail[]>('/api/dashboard/favorites');
}

/**
 * 获取即将到达的里程碑（支持筛选）
 * @param qg_types 筛选的 QG 类型列表，如 ["QG1", "QG3"]
 */
export function getUpcomingMilestones(qg_types?: string[]) {
  return requestClient.get<UpcomingMilestone[]>('/api/dashboard/milestones', {
    params: { qg_types },
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
  });
}
