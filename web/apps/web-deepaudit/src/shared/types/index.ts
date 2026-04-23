// 通用选项接口
export interface Option {
  label: string;
  value: string;
  icon?: React.ComponentType<{ className?: string }>;
  withCount?: boolean;
}

// 用户相关类型
export interface Profile {
  id: string;
  phone?: string;
  email?: string;
  full_name?: string;
  avatar_url?: string;
  role: 'admin' | 'member';
  github_username?: string;
  gitlab_username?: string;
  created_at: string;
  updated_at: string;
}

// 项目来源类型
export type ProjectSourceType = 'repository' | 'zip';

// 仓库模式类型
export type RepositoryType = 'multi' | 'single';
// 兼容旧命名，后续请统一使用 RepositoryType
export type RepositoryPlatform = RepositoryType;

// 项目相关类型
export interface Project {
  id: string;
  name: string;
  description?: string;
  source_type: ProjectSourceType; // 项目来源: 'repository' (远程仓库) 或 'zip' (ZIP上传)
  repository_url?: string; // 仅 source_type='repository' 时有效
  repository_type?: RepositoryType; // 仓库模式: single / multi
  default_branch: string;
  manifest_xml?: string;
  group?: string;
  programming_languages: string;
  owner_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  owner?: Profile;
}

export interface ProjectMember {
  id: string;
  project_id: string;
  user_id: string;
  role: 'admin' | 'member' | 'owner' | 'viewer';
  permissions: string;
  joined_at: string;
  created_at: string;
  user?: Profile;
  project?: Project;
}

// 审计相关类型
export interface AuditTask {
  id: string;
  project_id: string;
  task_type: 'instant' | 'repository';
  status: 'cancelled' | 'completed' | 'failed' | 'pending' | 'running';
  repository_url?: string;
  repository_type?: RepositoryType;
  branch_name?: string;
  manifest_xml?: string;
  group?: string;
  exclude_patterns: string;
  scan_config: string;
  total_files: number;
  scanned_files: number;
  total_lines: number;
  issues_count: number;
  quality_score: number;
  started_at?: string;
  completed_at?: string;
  created_by: string;
  created_at: string;
  project?: Project;
  creator?: Profile;
}

export interface AuditIssue {
  id: string;
  task_id: string;
  file_path: string;
  line_number?: number;
  column_number?: number;
  issue_type: 'bug' | 'maintainability' | 'performance' | 'security' | 'style';
  severity: 'critical' | 'high' | 'low' | 'medium';
  title: string;
  description?: string;
  suggestion?: string;
  code_snippet?: string;
  ai_explanation?: string;
  status: 'false_positive' | 'open' | 'resolved';
  resolved_by?: string;
  resolved_at?: string;
  created_at: string;
  task?: AuditTask;
  resolver?: Profile;
}

export interface InstantAnalysis {
  id: string;
  user_id: string;
  language: string;
  code_content: string;
  analysis_result: string;
  issues_count: number;
  quality_score: number;
  analysis_time: number;
  created_at: string;
  user?: Profile;
}

// ProjectDetail 页面：前端聚合层类型（用于把 AuditTask / AgentTask 的结果统一展示）
export type AggregatedAuditIssue = AuditIssue & {
  task_completed_at?: null | string;
  task_created_at?: string;
};

export type AggregatedAgentFinding =
  import('@/shared/api/agentTasks').AgentFinding & {
    task_completed_at?: null | string;
    task_created_at?: string;
  };

export type IssuesSummary = {
  completedAgentTasksCount: number;
  completedAuditTasksCount: number;
  fetchedAgentTasksCount: number;
  fetchedAuditTasksCount: number;
  isLimited: boolean;
  maxTasks: number;
};

export type LatestProblem = {
  category?: null | string;
  created_at: string;
  description?: null | string;
  file_path?: null | string;
  id: string;
  kind: 'agent' | 'audit';
  line_end?: null | number;
  line_number?: null | number;
  severity: 'critical' | 'high' | 'low' | 'medium';
  status?: string;
  task_created_at?: string;
  task_id: string;
  title: string;
};

export type UnifiedTask =
  | { kind: 'agent'; task: import('@/shared/api/agentTasks').AgentTask }
  | { kind: 'audit'; task: AuditTask };

// 表单相关类型
export interface CreateProjectForm {
  name: string;
  description?: string;
  source_type?: ProjectSourceType; // 项目来源类型
  repository_url?: string; // 仅 source_type='repository' 时需要
  repository_type?: RepositoryType; // 仓库模式
  default_branch?: string;
  manifest_xml?: string;
  group?: string;
  programming_languages: string[];
}

export interface CreateAuditTaskForm {
  project_id: string;
  task_type: 'instant' | 'repository';
  repository_url?: string;
  repository_type?: RepositoryType;
  branch_name?: string;
  manifest_xml?: string;
  group?: string;
  exclude_patterns: string[];
  rule_set_id?: string;
  prompt_template_id?: string;
  scan_config: {
    analysis_depth?: 'basic' | 'deep' | 'standard';
    file_paths?: string[];
    include_docs?: boolean;
    include_tests?: boolean;
    max_file_size?: number;
  };
}

export interface InstantAnalysisForm {
  language: string;
  code_content: string;
}

// 统计相关类型
export interface ProjectStats {
  total_projects: number;
  active_projects: number;
  total_tasks: number;
  completed_tasks: number;
  total_issues: number;
  resolved_issues: number;
  avg_quality_score: number;
}

export interface IssueStats {
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
  trend_data: Array<{
    count: number;
    date: string;
  }>;
}

// API响应类型
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

// 代码分析结果类型
export interface CodeAnalysisResult {
  issues: Array<{
    ai_explanation: any;
    code_snippet: string;
    column?: number;
    context_sources?: string[];
    cwe_id?: string;
    description: string;
    impact_scenario?: string;
    issue_type?: string;
    line: number;
    needs_runtime_verification?: boolean;
    root_cause?: string;
    severity: string;
    suggestion: string;
    title: string;
    type: string;
    trigger_condition?: string;
    verification_status?: string;
    xai?: {
      how: string;
      learn_more?: string;
      what: string;
      why: string;
    };
  }>;
  quality_score: number;
  summary: {
    critical_issues: number;
    high_issues: number;
    low_issues: number;
    medium_issues: number;
    total_issues: number;
  };
  metrics: {
    complexity: number;
    maintainability: number;
    performance: number;
    security: number;
  };
  analysis_profile?: {
    context_sources?: string[];
    engine?: string;
    language_profile?: {
      c_family_ratio?: number;
      dominant_family?: string;
      dominant_language?: string;
      is_c_family_dominant?: boolean;
      language_distribution?: Record<string, number>;
    };
    profile_mode?: string;
    prompt_template_id?: null | string;
    rule_set_id?: null | string;
    target_vulnerabilities?: string[];
  };
  // 后端返回的额外字段
  analysis_id?: string;
  analysis_time?: number;
}

// 仓库元信息类型
export interface Repository {
  id: string;
  name: string;
  full_name: string;
  description?: string;
  html_url: string;
  clone_url: string;
  default_branch: string;
  language?: string;
  languages?: Record<string, number>;
  private: boolean;
  updated_at: string;
}

export interface Branch {
  name: string;
  commit: {
    sha: string;
    url: string;
  };
  protected: boolean;
}

// 通知类型
export interface Notification {
  id: string;
  type: 'issue_resolved' | 'new_issue' | 'task_completed' | 'task_failed';
  title: string;
  message: string;
  data?: any;
  read: boolean;
  created_at: string;
}

// 系统配置类型
export interface SystemConfig {
  max_file_size: number;
  supported_languages: string[];
  analysis_timeout: number;
  max_concurrent_tasks: number;
  notification_settings: {
    email_enabled: boolean;
    webhook_url?: string;
  };
}
