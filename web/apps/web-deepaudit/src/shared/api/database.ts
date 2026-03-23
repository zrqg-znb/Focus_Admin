import { apiClient } from "./serverClient";
import type {
  AuditIssue,
  AuditTask,
  CreateAuditTaskForm,
  CreateProjectForm,
  InstantAnalysis,
  InstantAnalysisForm,
  Profile,
  Project,
  ProjectMember,
} from "../types";
import {
  normalizeAgentTask,
  normalizeAuditIssue,
  normalizeAuditTask,
  normalizeCodeAnalysisResult,
  normalizeInstantRecord,
  normalizeProfile,
  normalizeProject,
  normalizeUserConfig,
  normalizeZipMeta,
} from "./focusAdapter";

const DEFAULT_CONFIG = {
  llmConfig: {
    llmProvider: "openai",
    llmApiKey: "",
    llmModel: "",
    llmBaseUrl: "",
    llmTimeout: 150_000,
    llmTemperature: 0.1,
    llmMaxTokens: 4096,
    llmFirstTokenTimeout: 30,
    llmStreamTimeout: 60,
    agentTimeout: 1800,
    subAgentTimeout: 600,
    toolTimeout: 60,
  },
  otherConfig: {
    githubToken: "",
    gitlabToken: "",
    giteaToken: "",
    maxAnalyzeFiles: 0,
    llmConcurrency: 3,
    llmGapMs: 500,
    outputLanguage: "zh-CN",
  },
};

function toItems<T>(payload: any, normalizer: (item: any) => T | null): T[] {
  const items = Array.isArray(payload) ? payload : payload?.items;
  if (!Array.isArray(items)) {
    return [];
  }
  return items.map(normalizer).filter(Boolean) as T[];
}

function toProjectMember(item: any): ProjectMember {
  return {
    id: item.member_id,
    project_id: item.project_id,
    user_id: item.id,
    role: item.role,
    permissions: JSON.stringify(item.permissions || {}),
    joined_at: item.sys_create_datetime || "",
    created_at: item.sys_create_datetime || "",
    user: normalizeProfile(item) as any,
  };
}

function toProject(item: any): null | Project {
  return normalizeProject(item) as Project | null;
}

async function getProjectsList() {
  const res = await apiClient.get("/projects/");
  return toItems<Project>(res.data, toProject);
}

async function getProjectMap() {
  const projects = await getProjectsList();
  return new Map(projects.map((item) => [item.id, item]));
}

function toAuditTaskWithProject(task: any, projectMap: Map<string, Project>) {
  const normalized = normalizeAuditTask(task) as any;
  if (normalized?.project_id && projectMap.has(normalized.project_id)) {
    normalized.project = projectMap.get(normalized.project_id);
  }
  return normalized as AuditTask;
}

function toAgentTaskWithProject(task: any, projectMap: Map<string, Project>) {
  const normalized = normalizeAgentTask(task) as any;
  if (normalized?.project_id && projectMap.has(normalized.project_id)) {
    normalized.project = projectMap.get(normalized.project_id);
  }
  return normalized;
}

export const api = {
  async getProfilesById(_id: string): Promise<Profile | null> {
    try {
      const res = await apiClient.get("/users/me");
      return normalizeProfile(res.data) as Profile;
    } catch {
      return null;
    }
  },

  async getProfilesCount(): Promise<number> {
    return 1;
  },

  async createProfiles(profile: Partial<Profile>): Promise<Profile> {
    return profile as Profile;
  },

  async updateProfile(_id: string, updates: Partial<Profile>): Promise<Profile> {
    const res = await apiClient.put("/users/me", {
      name: updates.full_name,
      mobile: updates.phone,
    });
    return normalizeProfile(res.data) as Profile;
  },

  async getAllProfiles(): Promise<Profile[]> {
    const current = await this.getProfilesById("me");
    return current ? [current] : [];
  },

  async getProjects(): Promise<Project[]> {
    return getProjectsList();
  },

  async getProjectById(id: string): Promise<Project | null> {
    try {
      const res = await apiClient.get(`/projects/${id}`);
      return normalizeProject(res.data) as Project;
    } catch {
      return null;
    }
  },

  async getProjectFiles(id: string, branch?: string, excludePatterns?: string[]): Promise<Array<{ path: string; size: number }>> {
    try {
      const params: Record<string, string> = {};
      if (branch) {
        params.branch_name = branch;
      }
      if (excludePatterns?.length) {
        params.exclude_patterns = excludePatterns.join(",");
      }
      const res = await apiClient.get(`/projects/${id}/files`, { params });
      return Array.isArray(res.data) ? res.data : [];
    } catch {
      return [];
    }
  },

  async getProjectBranches(id: string): Promise<{ branches: string[]; default_branch: string; error?: string }> {
    try {
      const [branchRes, project] = await Promise.all([
        apiClient.get(`/projects/${id}/branches`),
        this.getProjectById(id),
      ]);
      return {
        branches: Array.isArray(branchRes.data) ? branchRes.data : ["main"],
        default_branch: project?.default_branch || "main",
      };
    } catch (error) {
      return { branches: ["main"], default_branch: "main", error: String(error) };
    }
  },

  async uploadProjectZip(id: string, file: File): Promise<{ message: string; original_filename: string; file_size: number }> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiClient.post(`/projects/${id}/zip`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    const meta = normalizeZipMeta(res.data);
    return {
      message: "上传成功",
      original_filename: meta.original_filename || "",
      file_size: meta.file_size || 0,
    };
  },

  async createProject(project: CreateProjectForm & { owner_id?: string }): Promise<Project> {
    const res = await apiClient.post("/projects/", {
      name: project.name,
      description: project.description,
      source_type: project.source_type || "repository",
      repository_url: project.repository_url,
      repository_type: project.repository_type || "other",
      default_branch: project.default_branch || "main",
      programming_languages: project.programming_languages || [],
    });
    return normalizeProject(res.data) as Project;
  },

  async updateProject(id: string, updates: Partial<CreateProjectForm>): Promise<Project> {
    const res = await apiClient.put(`/projects/${id}`, {
      ...updates,
      programming_languages: updates.programming_languages,
    });
    return normalizeProject(res.data) as Project;
  },

  async deleteProject(id: string): Promise<void> {
    await apiClient.delete(`/projects/${id}`);
  },

  async getDeletedProjects(): Promise<Project[]> {
    const res = await apiClient.get("/projects/deleted");
    return toItems<Project>(res.data, toProject);
  },

  async restoreProject(id: string): Promise<void> {
    await apiClient.post(`/projects/${id}/restore`);
  },

  async permanentlyDeleteProject(id: string): Promise<void> {
    await apiClient.delete(`/projects/${id}/permanent`);
  },

  async getProjectMembers(projectId: string): Promise<ProjectMember[]> {
    try {
      const res = await apiClient.get(`/projects/${projectId}/members`);
      return Array.isArray(res.data) ? res.data.map(toProjectMember) : [];
    } catch {
      return [];
    }
  },

  async addProjectMember(projectId: string, userId: string, role: string = "member"): Promise<ProjectMember> {
    const res = await apiClient.post(`/projects/${projectId}/members`, {
      user_id: userId,
      role,
    });
    return toProjectMember(res.data);
  },

  async removeProjectMember(projectId: string, memberId: string): Promise<void> {
    await apiClient.delete(`/projects/${projectId}/members/${memberId}`);
  },

  async getAuditTasks(projectId?: string): Promise<AuditTask[]> {
    const params = projectId ? { project_id: projectId } : {};
    const [res, projectMap] = await Promise.all([
      apiClient.get("/tasks/", { params }),
      getProjectMap(),
    ]);
    return toItems<AuditTask>(res.data, (item) => toAuditTaskWithProject(item, projectMap));
  },

  async getAuditTaskById(id: string): Promise<AuditTask | null> {
    try {
      const res = await apiClient.get(`/tasks/${id}`);
      const task = normalizeAuditTask(res.data) as any;
      if (task?.project_id) {
        const project = await this.getProjectById(task.project_id);
        if (project) {
          task.project = project;
        }
      }
      return task as AuditTask;
    } catch {
      return null;
    }
  },

  async createAuditTask(task: CreateAuditTaskForm & { created_by?: string }): Promise<AuditTask> {
    const project = await this.getProjectById(task.project_id);
    const endpoint = project?.source_type === "zip" ? "/scan/zip" : "/scan/repository";
    const payload = {
      project_id: task.project_id,
      branch_name: task.branch_name || project?.default_branch || "main",
      exclude_patterns: task.exclude_patterns || [],
      file_paths: task.scan_config?.file_paths || [],
      rule_set_id: task.rule_set_id,
      prompt_template_id: task.prompt_template_id,
      include_tests: Boolean(task.scan_config?.include_tests),
      include_docs: Boolean(task.scan_config?.include_docs),
      max_file_size: task.scan_config?.max_file_size,
      analysis_depth: task.scan_config?.analysis_depth || "standard",
    };
    const res = await apiClient.post(endpoint, payload);
    const createdTask = normalizeAuditTask(res.data) as any;
    if (project) {
      createdTask.project = project;
    }
    return createdTask as AuditTask;
  },

  async updateAuditTask(id: string, updates: Partial<AuditTask>): Promise<AuditTask> {
    if (updates.status === "cancelled") {
      await this.cancelAuditTask(id);
      const cancelledTask = await this.getAuditTaskById(id);
      if (cancelledTask) {
        return cancelledTask;
      }
    }

    const current = await this.getAuditTaskById(id);
    return current || ({} as AuditTask);
  },

  async cancelAuditTask(id: string): Promise<void> {
    await apiClient.post(`/tasks/${id}/cancel`);
  },

  async getAuditIssues(taskId: string): Promise<AuditIssue[]> {
    const res = await apiClient.get(`/tasks/${taskId}/issues`);
    return toItems<AuditIssue>(res.data, normalizeAuditIssue);
  },

  async createAuditIssue(_issue: Omit<AuditIssue, "id" | "created_at" | "task" | "resolver">): Promise<AuditIssue> {
    return {} as AuditIssue;
  },

  async updateAuditIssue(taskId: string, issueId: string, updates: Partial<AuditIssue>): Promise<AuditIssue> {
    const res = await apiClient.put(`/tasks/${taskId}/issues/${issueId}`, {
      status: updates.status,
    });
    return normalizeAuditIssue(res.data) as AuditIssue;
  },

  async getInstantAnalyses(_userId?: string): Promise<InstantAnalysis[]> {
    try {
      const res = await apiClient.get("/scan/instant/history");
      return toItems<InstantAnalysis>(res.data, normalizeInstantRecord);
    } catch {
      return [];
    }
  },

  async createInstantAnalysis(_analysis: InstantAnalysisForm & {
    user_id: string;
    analysis_result?: string;
    issues_count?: number;
    quality_score?: number;
    analysis_time?: number;
  }): Promise<InstantAnalysis> {
    return {} as InstantAnalysis;
  },

  async deleteInstantAnalysis(analysisId: string): Promise<void> {
    await apiClient.delete(`/scan/instant/history/${analysisId}`);
  },

  async deleteAllInstantAnalyses(): Promise<void> {
    const items = await this.getInstantAnalyses();
    await Promise.all(items.map((item) => this.deleteInstantAnalysis(item.id)));
  },

  async exportTaskReportPDF(taskId: string): Promise<Blob> {
    const res = await apiClient.get(`/tasks/${taskId}/report/pdf`, { responseType: "blob" });
    return res.data;
  },

  async exportInstantReportPDF(analysisId: string): Promise<Blob> {
    const res = await apiClient.get(`/scan/instant/history/${analysisId}/report/pdf`, { responseType: "blob" });
    return res.data;
  },

  async getProjectStats(): Promise<{
    total_projects: number;
    active_projects: number;
    total_tasks: number;
    completed_tasks: number;
    total_issues: number;
    resolved_issues: number;
    avg_quality_score: number;
  }> {
    try {
      const [overviewRes, tasks, agentTasks] = await Promise.all([
        apiClient.get("/dashboard/overview"),
        this.getAuditTasks(),
        (async () => {
          const taskRes = await apiClient.get("/agent-tasks/");
          const projectMap = await getProjectMap();
          return toItems<any>(taskRes.data, (item) => toAgentTaskWithProject(item, projectMap));
        })(),
      ]);
      const overview = overviewRes.data || {};
      const projectSummary = overview.project_summary || {};
      const scanTaskSummary = overview.scan_task_summary || {};
      const agentTaskSummary = overview.agent_task_summary || {};
      const issueSummary = overview.issue_summary || {};
      const findingSummary = overview.finding_summary || {};
      const completedScores = [...tasks, ...agentTasks]
        .filter((item: any) => item.completed_at && Number(item.quality_score) > 0)
        .map((item: any) => Number(item.quality_score));
      const avgQualityScore = completedScores.length
        ? completedScores.reduce((sum, value) => sum + value, 0) / completedScores.length
        : 0;

      return {
        total_projects: projectSummary.total || 0,
        active_projects: projectSummary.active || 0,
        total_tasks: (scanTaskSummary.total || 0) + (agentTaskSummary.total || 0),
        completed_tasks: (scanTaskSummary.completed || 0) + (agentTaskSummary.completed || 0),
        total_issues: (issueSummary.total || 0) + (findingSummary.total || 0),
        resolved_issues: (issueSummary.resolved || 0) + (findingSummary.fixed || 0),
        avg_quality_score: avgQualityScore,
      };
    } catch {
      return {
        total_projects: 0,
        active_projects: 0,
        total_tasks: 0,
        completed_tasks: 0,
        total_issues: 0,
        resolved_issues: 0,
        avg_quality_score: 0,
      };
    }
  },

  async getDefaultConfig() {
    return DEFAULT_CONFIG;
  },

  async getUserConfig() {
    try {
      const res = await apiClient.get("/config/me");
      return normalizeUserConfig(res.data);
    } catch {
      return normalizeUserConfig(DEFAULT_CONFIG);
    }
  },

  async updateUserConfig(config: { llmConfig?: any; otherConfig?: any }) {
    const payload = {
      llm_config: {
        provider: config.llmConfig?.llmProvider,
        model: config.llmConfig?.llmModel,
        api_key: config.llmConfig?.llmApiKey,
        base_url: config.llmConfig?.llmBaseUrl,
        timeout: Math.max(1, Math.round((config.llmConfig?.llmTimeout || 150_000) / 1000)),
        temperature: config.llmConfig?.llmTemperature,
        max_tokens: config.llmConfig?.llmMaxTokens,
        first_token_timeout: config.llmConfig?.llmFirstTokenTimeout,
        stream_timeout: config.llmConfig?.llmStreamTimeout,
        agent_timeout: config.llmConfig?.agentTimeout,
        sub_agent_timeout: config.llmConfig?.subAgentTimeout,
        tool_timeout: config.llmConfig?.toolTimeout,
      },
      other_config: {
        github_token: config.otherConfig?.githubToken,
        gitlab_token: config.otherConfig?.gitlabToken,
        gitea_token: config.otherConfig?.giteaToken,
        output_language: config.otherConfig?.outputLanguage,
        scan_config: {
          max_analyze_files: config.otherConfig?.maxAnalyzeFiles,
          llm_concurrency: config.otherConfig?.llmConcurrency,
          llm_gap_ms: config.otherConfig?.llmGapMs,
        },
      },
    };
    const res = await apiClient.put("/config/me", payload);
    return normalizeUserConfig(res.data);
  },

  async deleteUserConfig(): Promise<void> {
    await this.updateUserConfig(DEFAULT_CONFIG);
  },

  async testLLMConnection(params: {
    provider: string;
    apiKey: string;
    model?: string;
    baseUrl?: string;
  }): Promise<{
    success: boolean;
    message: string;
    model?: string;
    response?: string;
    debug?: Record<string, unknown>;
  }> {
    if (!params.apiKey && params.provider !== "ollama") {
      return {
        success: false,
        message: "请先填写 API Key",
      };
    }
    const res = await apiClient.post("/config/test-llm", {
      provider: params.provider,
      api_key: params.apiKey,
      model: params.model || "",
      base_url: params.baseUrl || "",
    });
    return {
      success: !!res.data?.success,
      message: res.data?.message || "",
      model: res.data?.model,
      response: res.data?.response,
      debug: res.data?.debug,
    };
  },

  async getLLMProviders() {
    return {
      providers: [
        { id: "openai", name: "OpenAI", defaultModel: "gpt-5", models: ["gpt-5", "gpt-5-mini", "o3"], defaultBaseUrl: "" },
        { id: "claude", name: "Claude", defaultModel: "claude-sonnet-4.5", models: ["claude-sonnet-4.5", "claude-opus-4"], defaultBaseUrl: "" },
        { id: "deepseek", name: "DeepSeek", defaultModel: "deepseek-chat", models: ["deepseek-chat", "deepseek-reasoner"], defaultBaseUrl: "https://api.deepseek.com" },
        { id: "ollama", name: "Ollama", defaultModel: "llama3.3", models: ["llama3.3", "qwen3"], defaultBaseUrl: "http://127.0.0.1:11434" },
      ],
    };
  },

  async exportDatabase(): Promise<{ export_date: string; user_id: string; data: any }> {
    const res = await apiClient.get("/database/export");
    return {
      export_date: new Date().toISOString(),
      user_id: "current-user",
      data: res.data?.payload || {},
    };
  },

  async importDatabase(file: File): Promise<{ message: string; imported: { projects: number; tasks: number; issues: number; analyses: number; config: number } }> {
    const text = await file.text();
    const parsed = JSON.parse(text);
    const payload = parsed?.data || parsed?.payload || parsed || {};
    const res = await apiClient.post("/database/import", { payload });
    const imported = res.data?.imported || {};
    return {
      message: res.data?.message || "导入完成",
      imported: {
        projects: imported.projects || 0,
        tasks: imported.scan_tasks || imported.tasks || 0,
        issues: imported.issues || 0,
        analyses: imported.instant_records || imported.analyses || 0,
        config: imported.user_configs || imported.config || 0,
      },
    };
  },

  async clearDatabase(): Promise<{ message: string; deleted: { projects: number; tasks: number; issues: number; analyses: number; config: number } }> {
    const res = await apiClient.post("/database/clear", {});
    const deleted = res.data?.deleted || {};
    return {
      message: res.data?.message || "清空完成",
      deleted: {
        projects: deleted.projects || 0,
        tasks: deleted.scan_tasks || deleted.tasks || 0,
        issues: deleted.issues || 0,
        analyses: deleted.instant_records || deleted.analyses || 0,
        config: deleted.user_configs || deleted.configs || deleted.config || 0,
      },
    };
  },

  async getDatabaseStats(): Promise<{
    total_projects: number;
    active_projects: number;
    total_tasks: number;
    completed_tasks: number;
    pending_tasks: number;
    running_tasks: number;
    failed_tasks: number;
    total_issues: number;
    open_issues: number;
    resolved_issues: number;
    critical_issues: number;
    high_issues: number;
    medium_issues: number;
    low_issues: number;
    total_analyses: number;
    total_members: number;
    has_config: boolean;
  }> {
    try {
      const [overviewRes, healthRes, config] = await Promise.all([
        apiClient.get("/dashboard/overview"),
        apiClient.get("/database/health"),
        this.getUserConfig(),
      ]);
      const overview = overviewRes.data || {};
      const counts = healthRes.data?.counts || {};
      const projectSummary = overview.project_summary || {};
      const scanTaskSummary = overview.scan_task_summary || {};
      const agentTaskSummary = overview.agent_task_summary || {};
      const issueSummary = overview.issue_summary || {};
      const findingSummary = overview.finding_summary || {};
      const severity = overview.severity_distribution || {};
      return {
        total_projects: projectSummary.total || 0,
        active_projects: projectSummary.active || 0,
        total_tasks: (scanTaskSummary.total || 0) + (agentTaskSummary.total || 0),
        completed_tasks: (scanTaskSummary.completed || 0) + (agentTaskSummary.completed || 0),
        pending_tasks: (scanTaskSummary.pending || 0) + (agentTaskSummary.pending || 0),
        running_tasks: (scanTaskSummary.running || 0) + (agentTaskSummary.running || 0),
        failed_tasks: (scanTaskSummary.failed || 0) + (agentTaskSummary.failed || 0),
        total_issues: (issueSummary.total || 0) + (findingSummary.total || 0),
        open_issues: (issueSummary.open || 0) + (findingSummary.open || 0),
        resolved_issues: (issueSummary.resolved || 0) + (findingSummary.fixed || 0),
        critical_issues: severity.critical || 0,
        high_issues: severity.high || 0,
        medium_issues: severity.medium || 0,
        low_issues: severity.low || 0,
        total_analyses: counts.instant_records || 0,
        total_members: 0,
        has_config: Boolean(config?.llmConfig),
      };
    } catch {
      return {
        total_projects: 0,
        active_projects: 0,
        total_tasks: 0,
        completed_tasks: 0,
        pending_tasks: 0,
        running_tasks: 0,
        failed_tasks: 0,
        total_issues: 0,
        open_issues: 0,
        resolved_issues: 0,
        critical_issues: 0,
        high_issues: 0,
        medium_issues: 0,
        low_issues: 0,
        total_analyses: 0,
        total_members: 0,
        has_config: false,
      };
    }
  },

  async checkDatabaseHealth(): Promise<{
    status: "healthy" | "warning" | "error";
    database_connected: boolean;
    total_records: number;
    last_backup_date: string | null;
    issues: string[];
    warnings: string[];
  }> {
    try {
      const res = await apiClient.get("/database/health");
      const data = res.data || {};
      const counts = data.counts || {};
      const totalRecords = Object.values(counts as Record<string, unknown>).reduce<number>(
        (sum, value) => sum + Number(value || 0),
        0,
      );
      const issues: string[] = [];
      const warnings: string[] = [];
      if (data.docker_enabled && !data.docker_available) {
        warnings.push("Docker 沙箱当前不可用");
      }
      const missingPaths = Array.isArray(data.storage_paths)
        ? data.storage_paths.filter((item: any) => !item.exists).map((item: any) => item.name)
        : [];
      if (missingPaths.length) {
        warnings.push(`缺少存储目录: ${missingPaths.join(", ")}`);
      }
      return {
        status: issues.length ? "error" : warnings.length ? "warning" : "healthy",
        database_connected: true,
        total_records: totalRecords,
        last_backup_date: null,
        issues,
        warnings,
      };
    } catch {
      return {
        status: "error",
        database_connected: false,
        total_records: 0,
        last_backup_date: null,
        issues: ["无法连接到 DeepAudit 数据工具接口"],
        warnings: [],
      };
    }
  },
};
