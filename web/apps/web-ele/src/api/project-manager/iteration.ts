import { requestClient } from '../request';

export interface Iteration {
  id: string;
  project_id: string;
  name: string;
  code: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  is_healthy: boolean;
}

export interface IterationMetric {
  id: string;
  iteration_id: string;
  record_date: string;
  req_decomposition_rate: number;
  req_drift_rate: number;
  req_completion_rate: number;
  req_workload: number;
  completed_workload: number;
}

export interface IterationDetail extends Iteration {
  latest_metric?: IterationMetric;
}

export interface IterationOverview {
  project_id: string;
  project_name: string;
  current_iteration?: Iteration;
  latest_metric?: IterationMetric;
}

export interface IterationCreate {
  project_id: string;
  name: string;
  code: string;
  start_date: string;
  end_date: string;
  is_current?: boolean;
  is_healthy?: boolean;
}

export interface IterationMetricCreate {
  iteration_id: string;
  record_date: string;
  req_decomposition_rate: number;
  req_drift_rate: number;
  req_completion_rate: number;
  req_workload: number;
  completed_workload: number;
}

enum Api {
  Overview = '/project-manager/iterations/overview',
  ProjectIterations = '/project-manager/iterations/project',
  Base = '/project-manager/iterations',
}

export const getIterationOverview = () => {
  return requestClient.get<IterationOverview[]>(Api.Overview);
};

export const getProjectIterations = (projectId: string) => {
  return requestClient.get<IterationDetail[]>(`${Api.ProjectIterations}/${projectId}`);
};

export const createIteration = (data: IterationCreate) => {
  return requestClient.post<Iteration>(Api.Base, data);
};

export const recordIterationMetric = (iterationId: string, data: IterationMetricCreate) => {
  return requestClient.post<IterationMetric>(`${Api.Base}/${iterationId}/metrics`, data);
};
