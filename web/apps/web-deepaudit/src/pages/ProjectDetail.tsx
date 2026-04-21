/**
 * Project Detail Page
 * Cyberpunk Terminal Aesthetic
 */

import type { ProjectCombinedStats } from '@/pages/project-detail/components/ProjectStatsCards';
import type { AgentFinding, AgentTask } from '@/shared/api/agentTasks';
import type {
  AggregatedAgentFinding,
  AggregatedAuditIssue,
  AuditIssue,
  AuditTask,
  CreateProjectForm,
  IssuesSummary,
  LatestProblem,
  Project,
  UnifiedTask,
} from '@/shared/types';

import CreateTaskDialog from '@/components/audit/CreateTaskDialog';
import TerminalProgressDialog from '@/components/audit/TerminalProgressDialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { ProjectIssuesTab } from '@/pages/project-detail/components/ProjectIssuesTab';
import { ProjectStatsCards } from '@/pages/project-detail/components/ProjectStatsCards';
import { ProjectTasksTab } from '@/pages/project-detail/components/ProjectTasksTab';
import { getAgentTasks, updateAgentFinding } from '@/shared/api/agentTasks';
import { apiClient } from '@/shared/api/serverClient';
import { api } from '@/shared/config/database';
import {
  PROJECT_DETAIL_ISSUES_FETCH_CONCURRENCY as ISSUES_FETCH_CONCURRENCY,
  PROJECT_DETAIL_ISSUES_MAX_TASKS as ISSUES_MAX_TASKS,
  REPOSITORY_PLATFORMS,
  PROJECT_DETAIL_REQUEST_TIMEOUT_MS as REQUEST_TIMEOUT_MS,
  SUPPORTED_LANGUAGES,
} from '@/shared/constants';
import { useAuth } from '@/shared/context/AuthContext';
import { DEEPAUDIT_ACTION_CODES } from '@/shared/focus/focusPermission';
import {
  getRepositoryTypeLabel,
  getSourceTypeLabel,
  isMultiRepository,
  isRepositoryProject,
  normalizeRepositoryType,
} from '@/shared/utils/projectUtils';
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  CheckCircle,
  Clock,
  Edit,
  ExternalLink,
  GitBranch,
  Shield,
  Terminal,
  Upload,
  XCircle,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { toast } from 'sonner';

function parseProjectProgrammingLanguages(project: null | Project): string[] {
  if (!project?.programming_languages) {
    return [];
  }
  try {
    const parsed = JSON.parse(project.programming_languages);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function buildEditFormFromProject(project: Project): CreateProjectForm {
  return {
    name: project.name,
    description: project.description || '',
    source_type: project.source_type || 'repository',
    repository_url: project.repository_url || '',
    repository_type: normalizeRepositoryType(project.repository_type),
    default_branch: project.default_branch || 'main',
    manifest_xml: project.manifest_xml || '',
    group: project.group || '',
    programming_languages: parseProjectProgrammingLanguages(project),
  };
}

export default function ProjectDetail() {
  const { hasAccess } = useAuth();
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<null | Project>(null);
  const [auditTasks, setAuditTasks] = useState<AuditTask[]>([]);
  const [agentTasks, setAgentTasks] = useState<AgentTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateTaskDialog, setShowCreateTaskDialog] = useState(false);
  const [showTerminalDialog, setShowTerminalDialog] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState<null | string>(null);
  const [editForm, setEditForm] = useState<CreateProjectForm>({
    name: '',
    description: '',
    source_type: 'repository',
    repository_url: '',
    repository_type: 'single',
    default_branch: 'main',
    manifest_xml: '',
    group: '',
    programming_languages: [],
  });
  const [settingsDirty, setSettingsDirty] = useState(false);
  const [settingsProjectId, setSettingsProjectId] = useState<null | string>(
    null,
  );
  const [activeTab, setActiveTab] = useState('overview');
  const [latestIssues, setLatestIssues] = useState<AggregatedAuditIssue[]>([]);
  const [latestFindings, setLatestFindings] = useState<
    AggregatedAgentFinding[]
  >([]);
  const [loadingIssues, setLoadingIssues] = useState(false);
  const [issuesSummary, setIssuesSummary] = useState<IssuesSummary>({
    completedAuditTasksCount: 0,
    completedAgentTasksCount: 0,
    fetchedAuditTasksCount: 0,
    fetchedAgentTasksCount: 0,
    isLimited: false,
    maxTasks: 20,
  });
  const canCreateFastTask = hasAccess(DEEPAUDIT_ACTION_CODES.TASKS_CREATE);
  const canCreateAgentTask = hasAccess(
    DEEPAUDIT_ACTION_CODES.AGENT_TASKS_CREATE,
  );
  const canCreateAnyTask = canCreateFastTask || canCreateAgentTask;
  const canUpdateProject = hasAccess(DEEPAUDIT_ACTION_CODES.PROJECTS_UPDATE);
  const canUpdateIssues = hasAccess(DEEPAUDIT_ACTION_CODES.ISSUES_UPDATE);

  const syncEditFormFromProject = (nextProject: Project) => {
    setEditForm(buildEditFormFromProject(nextProject));
    setSettingsDirty(false);
    setSettingsProjectId(nextProject.id);
  };

  const updateEditForm = (patch: Partial<CreateProjectForm>) => {
    setSettingsDirty(true);
    setEditForm((current) => ({ ...current, ...patch }));
  };

  // ============ Helpers ============

  async function withTimeout<T>(
    promise: Promise<T>,
    timeoutMs: number,
    label: string,
  ): Promise<T> {
    let timeoutId: number | undefined;
    const timeoutPromise = new Promise<T>((_resolve, reject) => {
      timeoutId = window.setTimeout(
        () => reject(new Error(`${label} timed out after ${timeoutMs}ms`)),
        timeoutMs,
      );
    });
    try {
      return await Promise.race([promise, timeoutPromise]);
    } finally {
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
    }
  }

  async function mapWithConcurrency<T, R>(
    items: T[],
    concurrency: number,
    mapper: (item: T) => Promise<R>,
  ): Promise<PromiseSettledResult<R>[]> {
    const results: PromiseSettledResult<R>[] = Array.from({
      length: items.length,
    });
    let nextIndex = 0;

    async function worker(): Promise<void> {
      while (true) {
        const currentIndex = nextIndex++;
        if (currentIndex >= items.length) return;
        try {
          const value = await mapper(items[currentIndex]);
          results[currentIndex] = { status: 'fulfilled', value };
        } catch (error) {
          results[currentIndex] = { status: 'rejected', reason: error };
        }
      }
    }

    const workers = Array.from({ length: Math.max(1, concurrency) }, () =>
      worker(),
    );
    await Promise.all(workers);
    return results;
  }

  async function fetchAuditIssues(taskId: string): Promise<AuditIssue[]> {
    // Use apiClient directly so we can control timeout behavior at the call site
    const res = await withTimeout(
      apiClient.get(`/tasks/${taskId}/issues`),
      REQUEST_TIMEOUT_MS,
      `GET /tasks/${taskId}/issues`,
    );
    return res.data;
  }

  async function fetchAgentFindings(taskId: string): Promise<AgentFinding[]> {
    const res = await withTimeout(
      apiClient.get(`/agent-tasks/${taskId}/findings`),
      REQUEST_TIMEOUT_MS,
      `GET /agent-tasks/${taskId}/findings`,
    );
    return res.data;
  }

  useEffect(() => {
    if (
      activeTab === 'issues' &&
      (auditTasks.length > 0 || agentTasks.length > 0)
    ) {
      loadLatestIssues();
    }
  }, [activeTab, auditTasks, agentTasks]);

  const loadLatestIssues = async () => {
    const completedAuditTasks = auditTasks
      .filter((t: AuditTask) => t.status === 'completed')
      .sort(
        (a: AuditTask, b: AuditTask) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );
    const completedAgentTasks = agentTasks
      .filter((t: AgentTask) => t.status === 'completed')
      .sort(
        (a: AgentTask, b: AgentTask) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );

    const limitedAuditTasks = completedAuditTasks.slice(0, ISSUES_MAX_TASKS);
    const limitedAgentTasks = completedAgentTasks.slice(0, ISSUES_MAX_TASKS);

    setIssuesSummary({
      completedAuditTasksCount: completedAuditTasks.length,
      completedAgentTasksCount: completedAgentTasks.length,
      fetchedAuditTasksCount: limitedAuditTasks.length,
      fetchedAgentTasksCount: limitedAgentTasks.length,
      isLimited:
        completedAuditTasks.length > ISSUES_MAX_TASKS ||
        completedAgentTasks.length > ISSUES_MAX_TASKS,
      maxTasks: ISSUES_MAX_TASKS,
    });

    if (limitedAuditTasks.length === 0 && limitedAgentTasks.length === 0) {
      setLatestIssues([]);
      setLatestFindings([]);
      return;
    }

    setLoadingIssues(true);
    try {
      const [issuesResults, findingsResults] = await Promise.all([
        mapWithConcurrency(
          limitedAuditTasks,
          ISSUES_FETCH_CONCURRENCY,
          async (task: AuditTask) => {
            const issues = await fetchAuditIssues(task.id);
            const enriched: AggregatedAuditIssue[] = (issues || []).map(
              (issue) => ({
                ...(issue as AuditIssue),
                task_created_at: task.created_at,
                task_completed_at: task.completed_at,
              }),
            );
            return enriched;
          },
        ),
        mapWithConcurrency(
          limitedAgentTasks,
          ISSUES_FETCH_CONCURRENCY,
          async (task: AgentTask) => {
            const findings = await fetchAgentFindings(task.id);
            const enriched: AggregatedAgentFinding[] = (findings || []).map(
              (finding) => ({
                ...(finding as AgentFinding),
                task_created_at: task.created_at,
                task_completed_at: task.completed_at,
              }),
            );
            return enriched;
          },
        ),
      ]);

      const flatIssues = issuesResults
        .filter(
          (
            r: PromiseSettledResult<AggregatedAuditIssue[]>,
          ): r is PromiseFulfilledResult<AggregatedAuditIssue[]> =>
            r.status === 'fulfilled',
        )
        .flatMap(
          (r: PromiseFulfilledResult<AggregatedAuditIssue[]>) => r.value,
        );
      const flatFindings = findingsResults
        .filter(
          (
            r: PromiseSettledResult<AggregatedAgentFinding[]>,
          ): r is PromiseFulfilledResult<AggregatedAgentFinding[]> =>
            r.status === 'fulfilled',
        )
        .flatMap(
          (r: PromiseFulfilledResult<AggregatedAgentFinding[]>) => r.value,
        );

      const severityRank: Record<string, number> = {
        critical: 4,
        high: 3,
        medium: 2,
        low: 1,
      };
      flatIssues.sort((a: AggregatedAuditIssue, b: AggregatedAuditIssue) => {
        const createdAtA = new Date(a.created_at).getTime();
        const createdAtB = new Date(b.created_at).getTime();
        if (createdAtA !== createdAtB) return createdAtB - createdAtA;

        const severityA = severityRank[a.severity] ?? 0;
        const severityB = severityRank[b.severity] ?? 0;
        if (severityA !== severityB) return severityB - severityA;

        const taskCreatedAtA = a.task_created_at
          ? new Date(a.task_created_at).getTime()
          : 0;
        const taskCreatedAtB = b.task_created_at
          ? new Date(b.task_created_at).getTime()
          : 0;
        return taskCreatedAtB - taskCreatedAtA;
      });

      setLatestIssues(flatIssues);
      flatFindings.sort(
        (a: AggregatedAgentFinding, b: AggregatedAgentFinding) => {
          const createdAtA = new Date(a.created_at).getTime();
          const createdAtB = new Date(b.created_at).getTime();
          if (createdAtA !== createdAtB) return createdAtB - createdAtA;

          const severityA =
            severityRank[String(a.severity || '').toLowerCase()] ?? 0;
          const severityB =
            severityRank[String(b.severity || '').toLowerCase()] ?? 0;
          if (severityA !== severityB) return severityB - severityA;

          const taskCreatedAtA = a.task_created_at
            ? new Date(a.task_created_at).getTime()
            : 0;
          const taskCreatedAtB = b.task_created_at
            ? new Date(b.task_created_at).getTime()
            : 0;
          return taskCreatedAtB - taskCreatedAtA;
        },
      );
      setLatestFindings(flatFindings);
    } catch (error) {
      console.error('Failed to load issues:', error);
      toast.error('加载问题列表失败');
    } finally {
      setLoadingIssues(false);
    }
  };

  const latestProblems: LatestProblem[] = useMemo(() => {
    const parsePathLineFromTitle = (title: string) => {
      // Pattern examples:
      // "path/to/File.java:66 - Something"
      // "path/to/File.java:137-138 - Something"
      // Security hardening:
      // - Cap title length
      // - Restrict acceptable path characters
      // - Reject absolute paths and path traversal segments
      const safeTitle = String(title || '').slice(0, 500);
      const separatorIndex = safeTitle.indexOf(' - ');
      if (separatorIndex === -1) return null;
      const head = safeTitle.slice(0, separatorIndex);
      const rest = safeTitle.slice(separatorIndex + 3);
      const match = head.match(/^([\w.\-/]+):(\d+)(?:-(\d+))?$/);
      if (!match) return null;
      const [, rawPath, lineStartStr, lineEndStr] = match;

      if (
        rawPath.startsWith('/') ||
        rawPath.includes('..') ||
        rawPath.includes('\u0000')
      )
        return null;

      const lineStart = Number(lineStartStr);
      const lineEnd = lineEndStr ? Number(lineEndStr) : null;
      const normalizedLineStart = Number.isFinite(lineStart)
        ? lineStart
        : Number.NaN;
      const normalizedLineEnd =
        lineEnd !== null && Number.isFinite(lineEnd) ? lineEnd : null;
      if (!Number.isFinite(normalizedLineStart) || normalizedLineStart <= 0)
        return null;
      return {
        file_path: rawPath,
        line_start: normalizedLineStart,
        line_end:
          normalizedLineEnd !== null && normalizedLineEnd > 0
            ? normalizedLineEnd
            : null,
        rest_title: rest,
      };
    };

    const normalizeSeverity = (s: unknown): LatestProblem['severity'] => {
      const v = String(s || '').toLowerCase();
      if (v === 'critical') return 'critical';
      if (v === 'high') return 'high';
      if (v === 'medium') return 'medium';
      return 'low';
    };

    const audit: LatestProblem[] = latestIssues.map((i) => ({
      // AuditIssue 在后端 schema 里可能叫 message（frontend type 没显式定义），这里做兼容兜底
      // 同时优先展示更"可读"的说明字段，避免 UI 出现大量 '-'
      kind: 'audit',
      id: i.id,
      task_id: i.task_id,
      task_created_at: i.task_created_at,
      created_at: i.created_at,
      severity: normalizeSeverity(i.severity),
      title: i.title || '(未命名问题)',
      description:
        i.description ??
        (i as any).message ??
        (i as any).ai_explanation ??
        (i as any).suggestion ??
        (i as any).code_snippet ??
        null,
      file_path: i.file_path,
      line_number: i.line_number ?? null,
      category: (i as any).issue_type ?? null,
      status: i.status ?? null,
    }));

    const agent: LatestProblem[] = latestFindings.map((f) => {
      const rawTitle = f.title || '(未命名漏洞)';
      const parsed =
        !f.file_path || f.file_path === '-'
          ? parsePathLineFromTitle(rawTitle)
          : null;

      return {
        kind: 'agent',
        id: f.id,
        task_id: f.task_id,
        task_created_at: f.task_created_at,
        created_at: f.created_at,
        severity: normalizeSeverity(f.severity),
        // 如果 title 里带了 "path:line - xxx"，则剥离掉路径前缀，仅保留 xxx，避免标题重复且过长
        title: parsed?.rest_title || rawTitle,
        description: f.description,
        // 如果后端没给 file_path，尽量从 title 解析出来填到"文件"列
        file_path: f.file_path ?? parsed?.file_path ?? null,
        line_number: (f.line_start ?? parsed?.line_start ?? null) as any,
        line_end: (f.line_end ?? parsed?.line_end ?? null) as any,
        category: (f as any).vulnerability_type ?? null,
        status: f.status ?? null,
      };
    });

    const merged = [...audit, ...agent];
    // 按时间倒序（最新在前），时间相同再按严重程度
    const severityRank: Record<string, number> = {
      critical: 4,
      high: 3,
      medium: 2,
      low: 1,
    };
    merged.sort((a, b) => {
      const createdAtA = new Date(a.created_at).getTime();
      const createdAtB = new Date(b.created_at).getTime();
      if (createdAtA !== createdAtB) return createdAtB - createdAtA;

      const severityA = severityRank[a.severity] ?? 0;
      const severityB = severityRank[b.severity] ?? 0;
      if (severityA !== severityB) return severityB - severityA;

      const taskCreatedAtA = a.task_created_at
        ? new Date(a.task_created_at).getTime()
        : 0;
      const taskCreatedAtB = b.task_created_at
        ? new Date(b.task_created_at).getTime()
        : 0;
      return taskCreatedAtB - taskCreatedAtA;
    });
    return merged;
  }, [latestIssues, latestFindings]);

  const handleStatusChange = async (
    problem: LatestProblem,
    newStatus: string,
  ) => {
    if (!canUpdateIssues) {
      toast.error('当前账号没有更新问题状态的权限');
      return;
    }
    try {
      await (problem.kind === 'agent'
        ? updateAgentFinding(problem.task_id, problem.id, { status: newStatus })
        : api.updateAuditIssue(problem.task_id, problem.id, {
            status: newStatus,
          } as any));
      toast.success('状态已更新');
      await loadLatestIssues();
    } catch (error) {
      console.error('Failed to update status:', error);
      toast.error('状态更新失败');
    }
  };

  const handleOpenSettings = () => {
    if (!canUpdateProject) {
      toast.error('当前账号没有编辑项目的权限');
      return;
    }
    if (!project) return;

    syncEditFormFromProject(project);
    setActiveTab('settings');
  };

  const formatLanguageName = (lang: string): string => {
    const nameMap: Record<string, string> = {
      javascript: 'JavaScript',
      typescript: 'TypeScript',
      python: 'Python',
      java: 'Java',
      go: 'Go',
      rust: 'Rust',
      cpp: 'C++',
      csharp: 'C#',
      php: 'PHP',
      ruby: 'Ruby',
      swift: 'Swift',
      kotlin: 'Kotlin',
    };
    return nameMap[lang] || lang.charAt(0).toUpperCase() + lang.slice(1);
  };

  const supportedLanguages = SUPPORTED_LANGUAGES.map((lang) =>
    formatLanguageName(lang),
  );

  useEffect(() => {
    if (id) {
      loadProjectData();
    }
  }, [id]);

  useEffect(() => {
    if (!project) {
      return;
    }
    if (settingsProjectId !== project.id) {
      syncEditFormFromProject(project);
      return;
    }
    if (!settingsDirty) {
      setEditForm(buildEditFormFromProject(project));
    }
  }, [project, settingsDirty, settingsProjectId]);

  const loadProjectData = async () => {
    if (!id) return;

    try {
      setLoading(true);
      const [projectRes, auditTasksRes, agentTasksRes] =
        await Promise.allSettled([
          api.getProjectById(id),
          api.getAuditTasks(id),
          getAgentTasks({ project_id: id }),
        ]);

      if (projectRes.status === 'fulfilled') {
        setProject(projectRes.value);
      } else {
        console.error('Failed to load project:', projectRes.reason);
        setProject(null);
      }

      if (auditTasksRes.status === 'fulfilled') {
        setAuditTasks(
          Array.isArray(auditTasksRes.value) ? auditTasksRes.value : [],
        );
      } else {
        console.error('Failed to load audit tasks:', auditTasksRes.reason);
        setAuditTasks([]);
      }

      if (agentTasksRes.status === 'fulfilled') {
        setAgentTasks(
          Array.isArray(agentTasksRes.value) ? agentTasksRes.value : [],
        );
      } else {
        // do not silently swallow: log for debugging and degrade gracefully
        console.warn('Failed to load agent tasks:', agentTasksRes.reason);
        setAgentTasks([]);
      }
    } catch (error) {
      console.error('Failed to load project data:', error);
      toast.error('加载项目数据失败');
    } finally {
      setLoading(false);
    }
  };

  const unifiedTasks: UnifiedTask[] = useMemo(() => {
    const merged: UnifiedTask[] = [
      ...auditTasks.map((t) => ({ kind: 'audit' as const, task: t })),
      ...agentTasks.map((t) => ({ kind: 'agent' as const, task: t })),
    ];
    merged.sort(
      (a, b) =>
        new Date((b.task as any).created_at).getTime() -
        new Date((a.task as any).created_at).getTime(),
    );
    return merged;
  }, [auditTasks, agentTasks]);

  const combinedStats: ProjectCombinedStats = useMemo(() => {
    const totalTasks = auditTasks.length + agentTasks.length;
    const completedTasks =
      auditTasks.filter((t) => t.status === 'completed').length +
      agentTasks.filter((t) => t.status === 'completed').length;
    const totalIssues =
      auditTasks.reduce((sum, t) => sum + (t.issues_count || 0), 0) +
      agentTasks.reduce((sum, t) => sum + (t.findings_count || 0), 0);
    const avgQualityScore =
      totalTasks > 0
        ? (auditTasks.reduce((sum, t) => sum + (t.quality_score || 0), 0) +
            agentTasks.reduce((sum, t) => sum + (t.quality_score || 0), 0)) /
          totalTasks
        : 0;
    return { totalTasks, completedTasks, totalIssues, avgQualityScore };
  }, [auditTasks, agentTasks]);

  const handleRunAudit = () => {
    if (!canCreateAnyTask) {
      toast.error('当前账号没有创建审计任务的权限');
      return;
    }
    setShowCreateTaskDialog(true);
  };

  const handleSaveSettings = async () => {
    if (!canUpdateProject) {
      toast.error('当前账号没有编辑项目的权限');
      return;
    }
    if (!id) return;

    if (!editForm.name.trim()) {
      toast.error('项目名称不能为空');
      return;
    }
    if (editForm.source_type === 'repository') {
      if (!editForm.repository_url?.trim()) {
        toast.error('仓库地址不能为空');
        return;
      }
      if (
        normalizeRepositoryType(editForm.repository_type) === 'multi' &&
        !editForm.manifest_xml?.trim()
      ) {
        toast.error('多仓项目必须填写 Manifest XML');
        return;
      }
    }

    try {
      await api.updateProject(id, editForm);
      toast.success('项目信息已保存');
      setSettingsDirty(false);
      loadProjectData();
    } catch (error) {
      console.error('Failed to update project:', error);
      toast.error('保存失败');
    }
  };

  const handleToggleLanguage = (lang: string) => {
    if (!canUpdateProject) {
      return;
    }
    const currentLanguages = editForm.programming_languages || [];
    const newLanguages = currentLanguages.includes(lang)
      ? currentLanguages.filter((l) => l !== lang)
      : [...currentLanguages, lang];

    setSettingsDirty(true);
    setEditForm({ ...editForm, programming_languages: newLanguages });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'cancelled': {
        return <Badge className="cyber-badge-muted">已取消</Badge>;
      }
      case 'completed': {
        return <Badge className="cyber-badge-success">完成</Badge>;
      }
      case 'failed': {
        return <Badge className="cyber-badge-danger">失败</Badge>;
      }
      case 'running': {
        return <Badge className="cyber-badge-info">运行中</Badge>;
      }
      default: {
        return <Badge className="cyber-badge-muted">等待中</Badge>;
      }
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'cancelled': {
        return <XCircle className="text-muted-foreground h-4 w-4" />;
      }
      case 'completed': {
        return <CheckCircle className="h-4 w-4 text-emerald-400" />;
      }
      case 'failed': {
        return <AlertTriangle className="h-4 w-4 text-rose-400" />;
      }
      case 'running': {
        return <Activity className="h-4 w-4 text-sky-400" />;
      }
      default: {
        return <Clock className="text-muted-foreground h-4 w-4" />;
      }
    }
  };

  const getTaskStatusClass = (status: string) => {
    switch (status) {
      case 'completed': {
        return 'bg-emerald-500/20';
      }
      case 'failed': {
        return 'bg-rose-500/20';
      }
      case 'running': {
        return 'bg-sky-500/20';
      }
      default: {
        return 'bg-muted';
      }
    }
  };

  const getTaskTypeLabel = (task: UnifiedTask) => {
    if (task.kind === 'audit') {
      return (task.task as AuditTask).task_type === 'repository'
        ? '审计任务'
        : '即时分析';
    }
    return 'Agent 审计';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleCreateTask = () => {
    if (!canCreateAnyTask) {
      toast.error('当前账号没有创建审计任务的权限');
      return;
    }
    setShowCreateTaskDialog(true);
  };

  const handleTaskCreated = () => {
    toast.success('审计任务已创建', {
      description:
        '因为网络和代码文件大小等因素，审计时长通常至少需要1分钟，请耐心等待...',
      duration: 5000,
    });
    loadProjectData();
  };

  const handleFastScanStarted = (taskId: string) => {
    setCurrentTaskId(taskId);
    setShowTerminalDialog(true);
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="space-y-4 text-center">
          <div className="loading-spinner mx-auto" />
          <p className="text-muted-foreground font-mono text-sm uppercase tracking-wider">
            加载项目数据...
          </p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="cyber-card p-8 text-center">
          <AlertTriangle className="mx-auto mb-4 h-16 w-16 text-rose-400" />
          <h2 className="text-foreground mb-2 text-2xl font-bold uppercase">
            项目未找到
          </h2>
          <p className="text-muted-foreground mb-4 font-mono">
            请检查项目ID是否正确
          </p>
          <Link to="/projects">
            <Button className="cyber-btn-primary">
              <ArrowLeft className="mr-2 h-4 w-4" />
              返回项目列表
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="cyber-bg-elevated relative min-h-screen space-y-6 p-6 font-mono">
      {/* Grid background */}
      <div className="cyber-grid-subtle pointer-events-none absolute inset-0" />

      {/* 顶部操作栏 */}
      <div className="relative z-10 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/projects">
            <Button
              className="cyber-btn-ghost flex h-10 w-10 items-center justify-center p-0"
              size="sm"
              variant="outline"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-foreground text-2xl font-bold uppercase tracking-wider">
              {project.name}
            </h1>
            <Badge
              className={`${project.is_active ? 'cyber-badge-success' : 'cyber-badge-muted'}`}
            >
              {project.is_active ? '活跃' : '暂停'}
            </Badge>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {canCreateAnyTask && (
            <Button className="cyber-btn-primary" onClick={handleRunAudit}>
              <Shield className="mr-2 h-4 w-4" />
              启动审计
            </Button>
          )}
          {canUpdateProject && (
            <Button
              className="cyber-btn-outline"
              onClick={handleOpenSettings}
              variant="outline"
            >
              <Edit className="mr-2 h-4 w-4" />
              编辑
            </Button>
          )}
        </div>
      </div>

      {/* 统计卡片 */}
      <ProjectStatsCards stats={combinedStats} />

      {/* 主要内容 */}
      <Tabs
        className="relative z-10 w-full"
        onValueChange={setActiveTab}
        value={activeTab}
      >
        <TabsList className="bg-muted border-border grid h-auto w-full grid-cols-4 gap-1 rounded border p-1">
          <TabsTrigger
            className="data-[state=active]:bg-primary data-[state=active]:text-foreground text-muted-foreground rounded-sm py-2 font-mono font-bold uppercase transition-all"
            value="overview"
          >
            项目概览
          </TabsTrigger>
          <TabsTrigger
            className="data-[state=active]:bg-primary data-[state=active]:text-foreground text-muted-foreground rounded-sm py-2 font-mono font-bold uppercase transition-all"
            value="tasks"
          >
            审计任务
          </TabsTrigger>
          <TabsTrigger
            className="data-[state=active]:bg-primary data-[state=active]:text-foreground text-muted-foreground rounded-sm py-2 font-mono font-bold uppercase transition-all"
            value="issues"
          >
            问题管理
          </TabsTrigger>
          <TabsTrigger
            className="data-[state=active]:bg-primary data-[state=active]:text-foreground text-muted-foreground rounded-sm py-2 font-mono font-bold uppercase transition-all"
            value="settings"
          >
            项目设置
          </TabsTrigger>
        </TabsList>

        <TabsContent className="mt-6 flex flex-col gap-6" value="overview">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* 项目信息 */}
            <div className="cyber-card p-4">
              <div className="section-header">
                <Terminal className="text-primary h-5 w-5" />
                <h3 className="section-title">项目信息</h3>
              </div>
              <div className="space-y-4 font-mono">
                <div className="space-y-3">
                  {project.repository_url && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground text-sm uppercase">
                        仓库地址
                      </span>
                      <a
                        className="text-primary flex items-center text-sm font-bold hover:underline"
                        href={project.repository_url}
                        rel="noopener noreferrer"
                        target="_blank"
                      >
                        查看仓库
                        <ExternalLink className="ml-1 h-3 w-3" />
                      </a>
                    </div>
                  )}

                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground text-sm uppercase">
                      项目类型
                    </span>
                    <Badge
                      className={`${isRepositoryProject(project) ? 'cyber-badge-info' : 'cyber-badge-warning'}`}
                    >
                      {getSourceTypeLabel(project.source_type)}
                    </Badge>
                  </div>

                  {isRepositoryProject(project) && (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground text-sm uppercase">
                          仓库模式
                        </span>
                        <Badge className="cyber-badge-muted">
                          {getRepositoryTypeLabel(project.repository_type)}
                        </Badge>
                      </div>

                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground text-sm uppercase">
                          默认分支
                        </span>
                        <span className="text-foreground bg-muted border-border rounded border px-2 py-0.5 text-sm font-bold">
                          {project.default_branch}
                        </span>
                      </div>
                      {isMultiRepository(project) && (
                        <>
                          <div className="flex items-center justify-between">
                            <span className="text-muted-foreground text-sm uppercase">
                              Manifest XML
                            </span>
                            <span className="text-foreground bg-muted border-border rounded border px-2 py-0.5 text-sm font-bold">
                              {project.manifest_xml || '未设置'}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-muted-foreground text-sm uppercase">
                              Group
                            </span>
                            <span className="text-foreground bg-muted border-border rounded border px-2 py-0.5 text-sm font-bold">
                              {project.group || '未设置'}
                            </span>
                          </div>
                        </>
                      )}
                    </>
                  )}

                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground text-sm uppercase">
                      创建时间
                    </span>
                    <span className="text-foreground text-sm">
                      {formatDate(project.created_at)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground text-sm uppercase">
                      所有者
                    </span>
                    <span className="text-foreground text-sm">
                      {project.owner?.full_name ||
                        project.owner?.phone ||
                        '未知'}
                    </span>
                  </div>
                </div>

                {project.programming_languages && (
                  <div className="border-border border-t pt-4">
                    <h4 className="text-muted-foreground mb-2 text-sm font-bold uppercase">
                      支持的编程语言
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {JSON.parse(project.programming_languages).map(
                        (lang: string) => (
                          <Badge className="cyber-badge-primary" key={lang}>
                            {lang}
                          </Badge>
                        ),
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* 最近活动 */}
            <div className="cyber-card p-4">
              <div className="section-header">
                <Clock className="h-5 w-5 text-emerald-400" />
                <h3 className="section-title">最近活动</h3>
              </div>
              <div>
                {unifiedTasks.length > 0 ? (
                  <div className="space-y-2">
                    {unifiedTasks.slice(0, 5).map((t) => (
                      <Link
                        className="bg-muted/50 hover:bg-muted group flex items-center justify-between rounded-lg p-3 transition-all"
                        key={`${t.kind}:${t.task.id}`}
                        to={
                          t.kind === 'audit'
                            ? `/tasks/${t.task.id}`
                            : `/agent-audit/${t.task.id}`
                        }
                      >
                        <div className="flex items-center space-x-3">
                          <div
                            className={`flex h-8 w-8 items-center justify-center rounded-lg ${getTaskStatusClass(t.task.status)}`}
                          >
                            {getStatusIcon(t.task.status)}
                          </div>
                          <div>
                            <p className="text-foreground group-hover:text-primary text-sm font-bold uppercase transition-colors">
                              {getTaskTypeLabel(t)}
                            </p>
                            <p className="text-muted-foreground font-mono text-xs">
                              {formatDate(t.task.created_at)}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge
                            className={
                              t.kind === 'agent'
                                ? 'cyber-badge-info'
                                : 'cyber-badge-muted'
                            }
                          >
                            {t.kind === 'agent' ? 'AGENT' : 'AUDIT'}
                          </Badge>
                          {getStatusBadge(t.task.status)}
                        </div>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">
                    <Activity className="empty-state-icon" />
                    <p className="empty-state-description">暂无活动记录</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent className="mt-6 flex flex-col gap-6" value="tasks">
          <ProjectTasksTab
            formatDate={formatDate}
            onCreateTask={handleCreateTask}
            renderStatusBadge={getStatusBadge}
            renderStatusIcon={getStatusIcon}
            unifiedTasks={unifiedTasks}
          />
        </TabsContent>

        <TabsContent className="mt-6 flex flex-col gap-6" value="issues">
          <ProjectIssuesTab
            formatDate={formatDate}
            hasAnyTasks={auditTasks.length > 0 || agentTasks.length > 0}
            issuesSummary={issuesSummary}
            latestProblems={latestProblems}
            loading={loadingIssues}
            onStatusChange={canUpdateIssues ? handleStatusChange : undefined}
          />
        </TabsContent>

        <TabsContent className="mt-6 flex flex-col gap-6" value="settings">
          <div className="cyber-card p-6">
            <div className="section-header">
              <Edit className="text-primary h-5 w-5" />
              <h3 className="section-title">编辑项目配置</h3>
            </div>
            {!canUpdateProject && (
              <div className="rounded border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-300">
                当前账号没有编辑权限，以下配置仅供查看。
              </div>
            )}

            <div className="flex flex-col gap-6">
              {/* 基本信息 */}
              <div className="space-y-4">
                <div>
                  <Label
                    className="text-muted-foreground font-mono text-xs font-bold uppercase"
                    htmlFor="edit-name"
                  >
                    项目名称 *
                  </Label>
                  <Input
                    className="cyber-input mt-1"
                    disabled={!canUpdateProject}
                    id="edit-name"
                    onChange={(e) => updateEditForm({ name: e.target.value })}
                    placeholder="输入项目名称"
                    value={editForm.name}
                  />
                </div>

                <div>
                  <Label
                    className="text-muted-foreground font-mono text-xs font-bold uppercase"
                    htmlFor="edit-description"
                  >
                    项目描述
                  </Label>
                  <Textarea
                    className="cyber-input mt-1 min-h-[80px]"
                    disabled={!canUpdateProject}
                    id="edit-description"
                    onChange={(e) =>
                      updateEditForm({ description: e.target.value })
                    }
                    placeholder="输入项目描述"
                    rows={3}
                    value={editForm.description}
                  />
                </div>
              </div>

              {/* 仓库信息 - 仅远程仓库类型显示 */}
              {editForm.source_type === 'repository' && (
                <div className="border-border space-y-4 border-t pt-4">
                  <h3 className="text-muted-foreground flex items-center gap-2 font-mono text-sm font-bold uppercase">
                    <GitBranch className="h-4 w-4" />
                    仓库信息
                  </h3>

                  <div>
                    <Label
                      className="text-muted-foreground font-mono text-xs font-bold uppercase"
                      htmlFor="edit-repo-url"
                    >
                      仓库地址
                    </Label>
                    <Input
                      className="cyber-input mt-1"
                      disabled={!canUpdateProject}
                      id="edit-repo-url"
                      onChange={(e) =>
                        updateEditForm({ repository_url: e.target.value })
                      }
                      placeholder="https://codehub.example.com/team/repo.git 或 git@codehub.example.com:team/repo.git"
                      value={editForm.repository_url}
                    />
                  </div>

                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div>
                      <Label
                        className="text-muted-foreground font-mono text-xs font-bold uppercase"
                        htmlFor="edit-repo-type"
                      >
                        认证类型
                      </Label>
                      <Select
                        disabled={!canUpdateProject}
                        onValueChange={(value: any) =>
                          updateEditForm({ repository_type: value })
                        }
                        value={editForm.repository_type}
                      >
                        <SelectTrigger
                          className="cyber-input mt-1"
                          id="edit-repo-type"
                        >
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="cyber-dialog border-border">
                          {REPOSITORY_PLATFORMS.map((platform) => (
                            <SelectItem
                              key={platform.value}
                              value={platform.value}
                            >
                              {platform.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <Label
                        className="text-muted-foreground font-mono text-xs font-bold uppercase"
                        htmlFor="edit-branch"
                      >
                        默认分支
                      </Label>
                      <Input
                        className="cyber-input mt-1"
                        disabled={!canUpdateProject}
                        id="edit-branch"
                        onChange={(e) =>
                          updateEditForm({ default_branch: e.target.value })
                        }
                        placeholder="main"
                        value={editForm.default_branch}
                      />
                    </div>
                  </div>

                  {editForm.repository_type === 'multi' && (
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                      <div>
                        <Label
                          className="text-muted-foreground font-mono text-xs font-bold uppercase"
                          htmlFor="edit-manifest-xml"
                        >
                          Manifest XML *
                        </Label>
                        <Input
                          className="cyber-input mt-1"
                          disabled={!canUpdateProject}
                          id="edit-manifest-xml"
                          onChange={(e) =>
                            updateEditForm({ manifest_xml: e.target.value })
                          }
                          placeholder="default.xml"
                          value={editForm.manifest_xml || ''}
                        />
                      </div>
                      <div>
                        <Label
                          className="text-muted-foreground font-mono text-xs font-bold uppercase"
                          htmlFor="edit-group"
                        >
                          Group
                        </Label>
                        <Input
                          className="cyber-input mt-1"
                          disabled={!canUpdateProject}
                          id="edit-group"
                          onChange={(e) =>
                            updateEditForm({ group: e.target.value })
                          }
                          placeholder="可选"
                          value={editForm.group || ''}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ZIP项目提示 */}
              {editForm.source_type === 'zip' && (
                <div className="border-border border-t pt-4">
                  <div className="rounded border border-amber-500/30 bg-amber-500/10 p-4">
                    <div className="flex items-start space-x-3">
                      <Upload className="mt-0.5 h-5 w-5 text-amber-400" />
                      <div className="font-mono text-sm">
                        <p className="mb-1 font-bold uppercase text-amber-300">
                          ZIP上传项目
                        </p>
                        <p className="text-xs text-amber-400/80">
                          此项目通过ZIP文件上传创建。每次进行代码审计时，需要在创建任务时重新上传ZIP文件。
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* 编程语言 */}
              <div className="border-border space-y-4 border-t pt-4">
                <h3 className="text-muted-foreground font-mono text-sm font-bold uppercase">
                  编程语言
                </h3>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {supportedLanguages.map((lang) => (
                    <div
                      className={`flex cursor-pointer items-center space-x-2 rounded border p-3 transition-all ${
                        editForm.programming_languages?.includes(lang)
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-border hover:border-border text-muted-foreground'
                      }`}
                      key={lang}
                      onClick={() => handleToggleLanguage(lang)}
                    >
                      <div
                        className={`flex h-4 w-4 items-center justify-center rounded-sm border-2 ${
                          editForm.programming_languages?.includes(lang)
                            ? 'bg-primary border-primary'
                            : 'border-border'
                        }`}
                      >
                        {editForm.programming_languages?.includes(lang) && (
                          <CheckCircle className="text-foreground h-3 w-3" />
                        )}
                      </div>
                      <span className="font-mono text-sm font-bold">
                        {lang}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="border-border flex justify-end space-x-3 border-t pt-6">
                <Button
                  className="cyber-btn-primary"
                  disabled={!canUpdateProject}
                  onClick={handleSaveSettings}
                >
                  <Edit className="mr-2 h-4 w-4" />
                  保存修改
                </Button>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {/* 创建任务对话框 */}
      <CreateTaskDialog
        onFastScanStarted={handleFastScanStarted}
        onOpenChange={setShowCreateTaskDialog}
        onTaskCreated={handleTaskCreated}
        open={showCreateTaskDialog}
        preselectedProjectId={id}
      />

      {/* 终端进度对话框 */}
      <TerminalProgressDialog
        onOpenChange={setShowTerminalDialog}
        open={showTerminalDialog}
        taskId={currentTaskId}
        taskType="repository"
      />
    </div>
  );
}
