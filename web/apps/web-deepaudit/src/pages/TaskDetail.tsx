/**
 * Task Detail Page
 * Cyberpunk Terminal Aesthetic
 */

import type { AuditIssue, AuditTask } from '@/shared/types';

import ExportReportDialog from '@/components/reports/ExportReportDialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { api } from '@/shared/config/database';
import { useAuth } from '@/shared/context/AuthContext';
import { DEEPAUDIT_ACTION_CODES } from '@/shared/focus/focusPermission';
import { parseAIExplanation } from '@/shared/utils/aiExplanation';
import {
  getRepositoryTypeLabel,
  getSourceTypeLabel,
  isMultiRepository,
  isRepositoryProject,
} from '@/shared/utils/projectUtils';
import { calculateTaskProgress } from '@/shared/utils/utils';
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Bug,
  Calendar,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Code,
  Download,
  FileText,
  GitBranch,
  Info,
  Lightbulb,
  Shield,
  TrendingUp,
  XCircle,
  Zap,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { toast } from 'sonner';

// Issues List Component
function IssuesList({
  issues,
  onStatusChange,
}: {
  issues: AuditIssue[];
  onStatusChange?: (issue: AuditIssue, newStatus: string) => void;
}) {
  const getSeverityClasses = (severity: string) => {
    switch (severity) {
      case 'critical': {
        return 'severity-critical';
      }
      case 'high': {
        return 'severity-high';
      }
      case 'low': {
        return 'severity-low';
      }
      case 'medium': {
        return 'severity-medium';
      }
      default: {
        return 'severity-info';
      }
    }
  };

  const getSeverityIconClasses = (severity: string) => {
    switch (severity) {
      case 'critical': {
        return 'bg-rose-500/20 text-rose-400';
      }
      case 'high': {
        return 'bg-orange-500/20 text-orange-400';
      }
      case 'medium': {
        return 'bg-amber-500/20 text-amber-400';
      }
      default: {
        return 'bg-sky-500/20 text-sky-400';
      }
    }
  };

  const getSeverityLabel = (severity: string) => {
    switch (severity) {
      case 'critical': {
        return '严重';
      }
      case 'high': {
        return '高';
      }
      case 'medium': {
        return '中等';
      }
      default: {
        return '低';
      }
    }
  };

  const getIssueStatusLabel = (status: string) => {
    switch (status) {
      case 'false_positive': {
        return '误报';
      }
      case 'resolved': {
        return '已解决';
      }
      default: {
        return '待处理';
      }
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'bug': {
        return <AlertTriangle className="h-4 w-4" />;
      }
      case 'maintainability': {
        return <FileText className="h-4 w-4" />;
      }
      case 'performance': {
        return <Zap className="h-4 w-4" />;
      }
      case 'security': {
        return <Shield className="h-4 w-4" />;
      }
      case 'style': {
        return <Code className="h-4 w-4" />;
      }
      default: {
        return <Info className="h-4 w-4" />;
      }
    }
  };

  const criticalIssues = issues.filter(
    (issue) => issue.severity === 'critical',
  );
  const highIssues = issues.filter((issue) => issue.severity === 'high');
  const mediumIssues = issues.filter((issue) => issue.severity === 'medium');
  const lowIssues = issues.filter((issue) => issue.severity === 'low');

  const renderIssue = (issue: AuditIssue, index: number) => (
    <div
      className="cyber-card hover:border-border group p-4 transition-all"
      key={issue.id || index}
    >
      <div className="mb-3 flex items-start justify-between">
        <div className="flex items-start space-x-3">
          <div
            className={`flex h-10 w-10 items-center justify-center rounded-lg ${getSeverityIconClasses(issue.severity)}`}
          >
            {getTypeIcon(issue.issue_type)}
          </div>
          <div className="flex-1">
            <h4 className="text-foreground group-hover:text-primary mb-1 text-base font-bold uppercase transition-colors">
              {issue.title}
            </h4>
            <div className="text-muted-foreground flex items-center space-x-1 font-mono text-xs">
              <FileText className="h-3 w-3" />
              <span className="bg-muted border-border rounded border px-2 py-0.5">
                {issue.file_path}
              </span>
            </div>
            {issue.line_number && (
              <div className="text-muted-foreground mt-1 flex items-center space-x-1 font-mono text-xs">
                <span className="text-primary">&gt;</span>
                <span>LINE: {issue.line_number}</span>
                {issue.column_number && (
                  <span>, COL: {issue.column_number}</span>
                )}
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {onStatusChange && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  className="font-mono text-xs"
                  size="sm"
                  variant="outline"
                >
                  {getIssueStatusLabel(issue.status)}
                  <ChevronDown className="ml-1 h-3 w-3" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onClick={() => onStatusChange(issue, 'resolved')}
                >
                  已解决
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => onStatusChange(issue, 'false_positive')}
                >
                  误报
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onStatusChange(issue, 'open')}>
                  恢复
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
          <Badge
            className={`${getSeverityClasses(issue.severity)} rounded px-2 py-1 text-xs font-bold uppercase`}
          >
            {getSeverityLabel(issue.severity)}
          </Badge>
        </div>
      </div>

      {issue.description && (
        <div className="bg-muted border-border mb-3 rounded border p-3 font-mono">
          <div className="border-border mb-1 flex items-center border-b pb-1">
            <Info className="text-muted-foreground mr-1 h-3 w-3" />
            <span className="text-muted-foreground text-xs font-bold uppercase">
              问题详情
            </span>
          </div>
          <p className="text-foreground mt-1 text-xs leading-relaxed">
            {issue.description}
          </p>
        </div>
      )}

      {issue.code_snippet && (
        <div className="cyber-bg-elevated border-border mb-3 rounded border p-3">
          <div className="border-border mb-2 flex items-center justify-between border-b pb-1">
            <div className="flex items-center space-x-1">
              <div className="bg-primary flex h-4 w-4 items-center justify-center rounded">
                <Code className="text-foreground h-2 w-2" />
              </div>
              <span className="font-mono text-xs font-bold uppercase text-emerald-600 dark:text-emerald-400">
                CODE_SNIPPET
              </span>
            </div>
            {issue.line_number && (
              <span className="text-muted-foreground font-mono text-xs">
                LINE: {issue.line_number}
              </span>
            )}
          </div>
          <div className="border-border rounded border bg-slate-100 p-2 dark:bg-black/40">
            <pre className="overflow-x-auto font-mono text-xs text-emerald-700 dark:text-emerald-400">
              <code>{issue.code_snippet}</code>
            </pre>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {issue.suggestion && (
          <div className="rounded border border-sky-500/30 bg-sky-500/10 p-3">
            <div className="mb-2 flex items-center border-b border-sky-500/20 pb-1">
              <div className="mr-2 flex h-5 w-5 items-center justify-center rounded border border-sky-500/40 bg-sky-500/20">
                <Lightbulb className="h-3 w-3 text-sky-600 dark:text-sky-400" />
              </div>
              <span className="text-sm font-bold uppercase text-sky-700 dark:text-sky-300">
                修复建议
              </span>
            </div>
            <p className="font-mono text-xs leading-relaxed text-sky-800 dark:text-sky-200/80">
              {issue.suggestion}
            </p>
          </div>
        )}

        {issue.ai_explanation &&
          (() => {
            const parsedExplanation = parseAIExplanation(issue.ai_explanation);

            if (!parsedExplanation) {
              return null;
            }

            return (
              <div className="rounded border border-violet-500/30 bg-violet-500/10 p-3">
                <div className="mb-2 flex items-center border-b border-violet-500/20 pb-1">
                  <div className="mr-2 flex h-5 w-5 items-center justify-center rounded border border-violet-500/40 bg-violet-500/20">
                    <Zap className="h-3 w-3 text-violet-600 dark:text-violet-400" />
                  </div>
                  <span className="text-sm font-bold uppercase text-violet-700 dark:text-violet-300">
                    AI 解释
                  </span>
                </div>

                {(() => {
                  if (parsedExplanation.hasStructuredContent) {
                    return (
                      <div className="space-y-2 font-mono text-xs">
                        {parsedExplanation.what && (
                          <div className="border-l-2 border-rose-500 pl-2">
                            <span className="font-bold uppercase text-rose-600 dark:text-rose-400">
                              问题：
                            </span>
                            <span className="text-foreground ml-1 whitespace-pre-wrap break-all">
                              {parsedExplanation.what}
                            </span>
                          </div>
                        )}

                        {parsedExplanation.why && (
                          <div className="border-l-2 border-amber-500 pl-2">
                            <span className="font-bold uppercase text-amber-600 dark:text-amber-400">
                              原因：
                            </span>
                            <span className="text-foreground ml-1 whitespace-pre-wrap break-all">
                              {parsedExplanation.why}
                            </span>
                          </div>
                        )}

                        {parsedExplanation.how && (
                          <div className="border-l-2 border-emerald-500 pl-2">
                            <span className="font-bold uppercase text-emerald-600 dark:text-emerald-400">
                              方案：
                            </span>
                            <span className="text-foreground ml-1 whitespace-pre-wrap break-all">
                              {parsedExplanation.how}
                            </span>
                          </div>
                        )}

                        {parsedExplanation.learnMore && (
                          <div className="border-l-2 border-sky-500 pl-2">
                            <span className="font-bold uppercase text-sky-600 dark:text-sky-400">
                              链接：
                            </span>
                            {(() => {
                              if (parsedExplanation.learnMoreHref) {
                                return (
                                  <a
                                    className="ml-1 break-all font-bold text-sky-600 hover:text-sky-500 hover:underline dark:text-sky-400 dark:hover:text-sky-300"
                                    href={parsedExplanation.learnMoreHref}
                                    rel="noopener noreferrer"
                                    target="_blank"
                                  >
                                    {parsedExplanation.learnMore}
                                  </a>
                                );
                              }

                              return (
                                <span className="text-foreground ml-1 whitespace-pre-wrap break-all">
                                  {parsedExplanation.learnMore}
                                </span>
                              );
                            })()}
                          </div>
                        )}

                        {parsedExplanation.extraEntries.map((entry) => (
                          <div
                            className="border-l-2 border-violet-500/60 pl-2"
                            key={entry.key}
                          >
                            <span className="font-bold uppercase text-violet-600 dark:text-violet-400">
                              {entry.label}：
                            </span>
                            <span className="text-foreground ml-1 whitespace-pre-wrap break-all">
                              {entry.value}
                            </span>
                          </div>
                        ))}
                      </div>
                    );
                  }

                  if (parsedExplanation.rawText) {
                    return (
                      <p className="text-foreground whitespace-pre-wrap break-all font-mono text-xs leading-relaxed">
                        {parsedExplanation.rawText}
                      </p>
                    );
                  }

                  return null;
                })()}
              </div>
            );
          })()}
      </div>
    </div>
  );

  if (issues.length === 0) {
    return (
      <div className="cyber-card border-dashed p-16 text-center">
        <CheckCircle className="mx-auto mb-4 h-16 w-16 text-emerald-600 dark:text-emerald-400" />
        <h3 className="mb-2 text-xl font-bold uppercase text-emerald-700 dark:text-emerald-300">
          代码质量优秀！
        </h3>
        <p className="mb-4 font-mono text-emerald-600 dark:text-emerald-400/80">
          恭喜！没有发现任何问题
        </p>
        <div className="mx-auto max-w-md rounded border border-emerald-500/30 bg-emerald-500/10 p-4">
          <p className="font-mono text-sm text-emerald-700 dark:text-emerald-300/80">
            您的代码通过了所有质量检查，包括安全性、性能、可维护性等各个方面的评估。
          </p>
        </div>
      </div>
    );
  }

  return (
    <Tabs className="w-full" defaultValue="all">
      <TabsList className="bg-muted border-border grid h-auto w-full grid-cols-5 gap-1 rounded border p-1">
        <TabsTrigger
          className="data-[state=active]:bg-primary data-[state=active]:text-foreground text-muted-foreground rounded-sm py-2 font-mono text-xs font-bold uppercase transition-all"
          value="all"
        >
          全部 ({issues.length})
        </TabsTrigger>
        <TabsTrigger
          className="data-[state=active]:text-foreground text-muted-foreground rounded-sm py-2 font-mono text-xs font-bold uppercase transition-all data-[state=active]:bg-rose-500"
          value="critical"
        >
          严重 ({criticalIssues.length})
        </TabsTrigger>
        <TabsTrigger
          className="data-[state=active]:text-foreground text-muted-foreground rounded-sm py-2 font-mono text-xs font-bold uppercase transition-all data-[state=active]:bg-orange-500"
          value="high"
        >
          高 ({highIssues.length})
        </TabsTrigger>
        <TabsTrigger
          className="data-[state=active]:text-background text-muted-foreground rounded-sm py-2 font-mono text-xs font-bold uppercase transition-all data-[state=active]:bg-amber-500"
          value="medium"
        >
          中等 ({mediumIssues.length})
        </TabsTrigger>
        <TabsTrigger
          className="data-[state=active]:text-foreground text-muted-foreground rounded-sm py-2 font-mono text-xs font-bold uppercase transition-all data-[state=active]:bg-sky-500"
          value="low"
        >
          低 ({lowIssues.length})
        </TabsTrigger>
      </TabsList>

      <TabsContent className="mt-6 space-y-4" value="all">
        {issues.map((issue, index) => renderIssue(issue, index))}
      </TabsContent>

      <TabsContent className="mt-6 space-y-4" value="critical">
        {criticalIssues.length > 0 ? (
          criticalIssues.map((issue, index) => renderIssue(issue, index))
        ) : (
          <div className="cyber-card border-dashed p-12 text-center">
            <CheckCircle className="mx-auto mb-4 h-16 w-16 text-emerald-400" />
            <h3 className="text-foreground mb-2 text-lg font-bold uppercase">
              没有发现严重问题
            </h3>
            <p className="text-muted-foreground font-mono">
              代码在严重级别的检查中表现良好
            </p>
          </div>
        )}
      </TabsContent>

      <TabsContent className="mt-6 space-y-4" value="high">
        {highIssues.length > 0 ? (
          highIssues.map((issue, index) => renderIssue(issue, index))
        ) : (
          <div className="cyber-card border-dashed p-12 text-center">
            <CheckCircle className="mx-auto mb-4 h-16 w-16 text-emerald-400" />
            <h3 className="text-foreground mb-2 text-lg font-bold uppercase">
              没有发现高优先级问题
            </h3>
            <p className="text-muted-foreground font-mono">
              代码在高优先级检查中表现良好
            </p>
          </div>
        )}
      </TabsContent>

      <TabsContent className="mt-6 space-y-4" value="medium">
        {mediumIssues.length > 0 ? (
          mediumIssues.map((issue, index) => renderIssue(issue, index))
        ) : (
          <div className="cyber-card border-dashed p-12 text-center">
            <CheckCircle className="mx-auto mb-4 h-16 w-16 text-emerald-400" />
            <h3 className="text-foreground mb-2 text-lg font-bold uppercase">
              没有发现中等优先级问题
            </h3>
            <p className="text-muted-foreground font-mono">
              代码在中等优先级检查中表现良好
            </p>
          </div>
        )}
      </TabsContent>

      <TabsContent className="mt-6 space-y-4" value="low">
        {lowIssues.length > 0 ? (
          lowIssues.map((issue, index) => renderIssue(issue, index))
        ) : (
          <div className="cyber-card border-dashed p-12 text-center">
            <CheckCircle className="mx-auto mb-4 h-16 w-16 text-emerald-400" />
            <h3 className="text-foreground mb-2 text-lg font-bold uppercase">
              没有发现低优先级问题
            </h3>
            <p className="text-muted-foreground font-mono">
              代码在低优先级检查中表现良好
            </p>
          </div>
        )}
      </TabsContent>
    </Tabs>
  );
}

export default function TaskDetail() {
  const { id } = useParams<{ id: string }>();
  const { hasAccess } = useAuth();
  const [task, setTask] = useState<AuditTask | null>(null);
  const [issues, setIssues] = useState<AuditIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [scanConfigExpanded, setScanConfigExpanded] = useState(false);

  // Zombie task detection
  const [lastProgressTime, setLastProgressTime] = useState<number>(Date.now());
  const [lastProgress, setLastProgress] = useState<number>(0);
  const ZOMBIE_TIMEOUT = 180_000;
  const canCancelTask = hasAccess(DEEPAUDIT_ACTION_CODES.TASKS_CANCEL);
  const canExportReport = hasAccess(DEEPAUDIT_ACTION_CODES.REPORTS_EXPORT);
  const canUpdateIssues = hasAccess(DEEPAUDIT_ACTION_CODES.ISSUES_UPDATE);

  useEffect(() => {
    if (id) {
      loadTaskDetail();
    }
  }, [id]);

  // Silent progress update for running tasks
  useEffect(() => {
    if (!task || !id) {
      return;
    }

    if (task.status === 'running' || task.status === 'pending') {
      const intervalId = setInterval(async () => {
        try {
          const [taskData, issuesData] = await Promise.all([
            api.getAuditTaskById(id),
            api.getAuditIssues(id),
          ]);

          if (!taskData) {
            console.error('任务数据获取失败');
            return;
          }

          const currentProgress = taskData.scanned_files || 0;
          if (currentProgress !== lastProgress) {
            setLastProgress(currentProgress);
            setLastProgressTime(Date.now());
          } else if (
            taskData.status === 'running' &&
            Date.now() - lastProgressTime > ZOMBIE_TIMEOUT
          ) {
            toast.warning('任务可能已停止响应，建议取消后重试', {
              id: 'zombie-warning',
              duration: 10_000,
            });
          }

          if (
            taskData.status !== task.status ||
            taskData.scanned_files !== task.scanned_files ||
            taskData.issues_count !== task.issues_count
          ) {
            setTask(taskData);
            setIssues(issuesData);

            if (
              ['cancelled', 'completed', 'failed'].includes(taskData.status)
            ) {
              clearInterval(intervalId);
            }
          }
        } catch (error) {
          console.error('静默更新任务失败:', error);
          toast.error('获取任务状态失败，请检查网络连接', {
            id: 'network-error',
            duration: 5000,
          });
        }
      }, 3000);

      return () => clearInterval(intervalId);
    }
  }, [task?.status, task?.scanned_files, id, lastProgress, lastProgressTime]);

  const handleCancelTask = async () => {
    if (!id || cancelling) return;
    if (!canCancelTask) {
      toast.error('当前账号没有取消任务的权限');
      return;
    }

    try {
      setCancelling(true);
      await api.cancelAuditTask(id);
      toast.success('任务已取消');
      const taskData = await api.getAuditTaskById(id);
      if (taskData) {
        setTask(taskData);
      }
    } catch (error: any) {
      console.error('取消任务失败:', error);
      toast.error(error?.response?.data?.detail || '取消任务失败');
    } finally {
      setCancelling(false);
    }
  };

  const loadTaskDetail = async () => {
    if (!id) return;

    try {
      setLoading(true);
      const [taskData, issuesData] = await Promise.all([
        api.getAuditTaskById(id),
        api.getAuditIssues(id),
      ]);

      setTask(taskData);
      setIssues(issuesData);
    } catch (error) {
      console.error('Failed to load task detail:', error);
      toast.error('加载任务详情失败');
    } finally {
      setLoading(false);
    }
  };

  const handleIssueStatusChange = async (
    issue: AuditIssue,
    newStatus: string,
  ) => {
    if (!id) return;
    if (!canUpdateIssues) {
      toast.error('当前账号没有更新问题状态的权限');
      return;
    }
    try {
      await api.updateAuditIssue(id, issue.id, { status: newStatus } as any);
      toast.success('状态已更新');
      const issuesData = await api.getAuditIssues(id);
      setIssues(issuesData);
    } catch (error) {
      console.error('Failed to update issue status:', error);
      toast.error('状态更新失败');
    }
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="space-y-4 text-center">
          <div className="loading-spinner mx-auto" />
          <p className="text-muted-foreground font-mono text-sm uppercase tracking-wider">
            加载任务详情...
          </p>
        </div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="cyber-bg-elevated min-h-screen space-y-6 p-6 font-mono">
        <div className="flex items-center space-x-4">
          <Link to="/audit-tasks">
            <Button
              className="cyber-btn-ghost h-10 w-10 p-0"
              size="sm"
              variant="outline"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
        </div>
        <div className="cyber-card p-16 text-center">
          <AlertTriangle className="mx-auto mb-4 h-16 w-16 text-rose-400" />
          <h3 className="text-foreground mb-2 text-xl font-bold uppercase">
            任务不存在
          </h3>
          <p className="text-muted-foreground font-mono">
            请检查任务ID是否正确
          </p>
        </div>
      </div>
    );
  }

  const progressPercentage = calculateTaskProgress(
    task.scanned_files,
    task.total_files,
  );

  return (
    <div className="cyber-bg-elevated relative min-h-screen space-y-6 p-6 font-mono">
      {/* Grid background */}
      <div className="cyber-grid-subtle pointer-events-none absolute inset-0" />

      {/* Top Action Bar */}
      <div className="relative z-10 flex items-center justify-between">
        <Link to="/audit-tasks">
          <Button
            className="cyber-btn-ghost h-10 w-10 p-0"
            size="sm"
            variant="outline"
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>

        <div className="flex items-center space-x-3">
          {getStatusBadge(task.status)}

          {(task.status === 'running' || task.status === 'pending') &&
            canCancelTask && (
              <Button
                className="cyber-btn text-foreground h-10 border-rose-500/50 bg-rose-500/90 hover:bg-rose-500"
                disabled={cancelling}
                onClick={handleCancelTask}
                size="sm"
              >
                <XCircle className="mr-2 h-4 w-4" />
                {cancelling ? '取消中...' : '取消任务'}
              </Button>
            )}

          {task.status === 'completed' && canExportReport && (
            <Button
              className="cyber-btn-primary h-10"
              onClick={() => setExportDialogOpen(true)}
              size="sm"
            >
              <Download className="mr-2 h-4 w-4" />
              导出报告
            </Button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="relative z-10 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="cyber-card p-4">
          <div className="flex items-center justify-between">
            <div className="w-full">
              <p className="stat-label">扫描进度</p>
              <p className="stat-value mb-2">{progressPercentage}%</p>
              <Progress
                className="bg-muted [&>div]:bg-primary h-2"
                value={progressPercentage}
              />
            </div>
            <div className="stat-icon text-primary ml-4">
              <Activity className="h-6 w-6" />
            </div>
          </div>
        </div>

        <div className="cyber-card p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="stat-label">发现问题</p>
              <p className="stat-value text-amber-400">{task.issues_count}</p>
            </div>
            <div className="stat-icon text-amber-400">
              <Bug className="h-6 w-6" />
            </div>
          </div>
        </div>

        <div className="cyber-card p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="stat-label">质量评分</p>
              <p className="stat-value text-emerald-400">
                {task.quality_score.toFixed(1)}
              </p>
            </div>
            <div className="stat-icon text-emerald-400">
              <TrendingUp className="h-6 w-6" />
            </div>
          </div>
        </div>

        <div className="cyber-card p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="stat-label">代码行数</p>
              <p className="stat-value text-violet-400">
                {task.total_lines.toLocaleString()}
              </p>
            </div>
            <div className="stat-icon text-violet-400">
              <FileText className="h-6 w-6" />
            </div>
          </div>
        </div>
      </div>

      {/* Task Info */}
      <div className="relative z-10 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="cyber-card p-0">
            <div className="cyber-card-header">
              <Shield className="text-primary h-5 w-5" />
              <h3 className="text-foreground text-lg font-bold uppercase tracking-wider">
                任务信息
              </h3>
            </div>
            <div className="space-y-4 p-6 font-mono">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-muted-foreground mb-1 text-xs font-bold uppercase">
                    任务类型
                  </p>
                  <p className="text-foreground text-base font-bold">
                    {task.task_type === 'repository'
                      ? '仓库审计任务'
                      : '即时分析任务'}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground mb-1 text-xs font-bold uppercase">
                    目标分支
                  </p>
                  <p className="text-foreground flex items-center text-base font-bold">
                    <GitBranch className="mr-1 h-4 w-4" />
                    {task.branch_name || '默认分支'}
                  </p>
                </div>
                {task.manifest_xml && (
                  <div>
                    <p className="text-muted-foreground mb-1 text-xs font-bold uppercase">
                      Manifest XML
                    </p>
                    <p className="text-foreground text-base font-bold">
                      {task.manifest_xml}
                    </p>
                  </div>
                )}
                {task.group && (
                  <div>
                    <p className="text-muted-foreground mb-1 text-xs font-bold uppercase">
                      Group
                    </p>
                    <p className="text-foreground text-base font-bold">
                      {task.group}
                    </p>
                  </div>
                )}
                <div>
                  <p className="text-muted-foreground mb-1 text-xs font-bold uppercase">
                    创建时间
                  </p>
                  <p className="text-foreground flex items-center text-base font-bold">
                    <Calendar className="mr-1 h-4 w-4" />
                    {formatDate(task.created_at)}
                  </p>
                </div>
                {task.completed_at && (
                  <div>
                    <p className="text-muted-foreground mb-1 text-xs font-bold uppercase">
                      完成时间
                    </p>
                    <p className="text-foreground flex items-center text-base font-bold">
                      <CheckCircle className="mr-1 h-4 w-4" />
                      {formatDate(task.completed_at)}
                    </p>
                  </div>
                )}
              </div>

              {task.exclude_patterns && (
                <div>
                  <p className="text-muted-foreground mb-2 text-xs font-bold uppercase">
                    排除模式
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {JSON.parse(task.exclude_patterns).map(
                      (pattern: string) => (
                        <Badge className="cyber-badge-muted" key={pattern}>
                          {pattern}
                        </Badge>
                      ),
                    )}
                  </div>
                </div>
              )}

              {task.scan_config && (
                <div>
                  <button
                    className="text-muted-foreground hover:text-foreground mb-2 flex items-center gap-2 text-xs font-bold uppercase transition-colors"
                    onClick={() => setScanConfigExpanded(!scanConfigExpanded)}
                    type="button"
                  >
                    {scanConfigExpanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    扫描配置
                  </button>
                  {scanConfigExpanded && (
                    <div className="cyber-bg-elevated border-border rounded border p-3">
                      <pre className="overflow-x-auto font-mono text-xs text-emerald-700 dark:text-emerald-400">
                        {JSON.stringify(JSON.parse(task.scan_config), null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        <div>
          <div className="cyber-card p-0">
            <div className="cyber-card-header">
              <FileText className="text-primary h-5 w-5" />
              <h3 className="text-foreground text-lg font-bold uppercase tracking-wider">
                项目信息
              </h3>
            </div>
            <div className="space-y-4 p-6 font-mono">
              {task.project ? (
                <>
                  <div>
                    <p className="text-muted-foreground mb-1 text-xs font-bold uppercase">
                      项目名称
                    </p>
                    <Link
                      className="text-primary text-base font-bold hover:underline"
                      to={`/projects/${task.project.id}`}
                    >
                      {task.project.name}
                    </Link>
                  </div>
                  {task.project.description && (
                    <div>
                      <p className="text-muted-foreground mb-1 text-xs font-bold uppercase">
                        项目描述
                      </p>
                      <p className="text-foreground text-sm">
                        {task.project.description}
                      </p>
                    </div>
                  )}
                  <div>
                    <p className="text-muted-foreground mb-1 text-xs font-bold uppercase">
                      项目类型
                    </p>
                    <p className="text-foreground text-base font-bold">
                      {getSourceTypeLabel(task.project.source_type)}
                    </p>
                  </div>
                  {isRepositoryProject(task.project) && (
                    <>
                      <div>
                        <p className="text-muted-foreground mb-1 text-xs font-bold uppercase">
                          仓库模式
                        </p>
                        <p className="text-foreground text-base font-bold">
                          {getRepositoryTypeLabel(task.project.repository_type)}
                        </p>
                      </div>
                      {isMultiRepository(task.project) && (
                        <>
                          <div>
                            <p className="text-muted-foreground mb-1 text-xs font-bold uppercase">
                              项目 Manifest
                            </p>
                            <p className="text-foreground text-base font-bold">
                              {task.project.manifest_xml || '未设置'}
                            </p>
                          </div>
                          <div>
                            <p className="text-muted-foreground mb-1 text-xs font-bold uppercase">
                              项目 Group
                            </p>
                            <p className="text-foreground text-base font-bold">
                              {task.project.group || '未设置'}
                            </p>
                          </div>
                        </>
                      )}
                    </>
                  )}
                  {task.project.programming_languages && (
                    <div>
                      <p className="text-muted-foreground mb-2 text-xs font-bold uppercase">
                        编程语言
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {JSON.parse(task.project.programming_languages).map(
                          (lang: string) => (
                            <Badge className="cyber-badge-primary" key={lang}>
                              {lang}
                            </Badge>
                          ),
                        )}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-muted-foreground font-bold">
                  项目信息不可用
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Issues List */}
      {issues.length > 0 && (
        <div className="cyber-card relative z-10 p-0">
          <div className="cyber-card-header">
            <Bug className="h-5 w-5 text-amber-400" />
            <h3 className="text-foreground text-lg font-bold uppercase tracking-wider">
              发现的问题 ({issues.length})
            </h3>
          </div>
          <div className="p-6">
            <IssuesList
              issues={issues}
              onStatusChange={
                canUpdateIssues ? handleIssueStatusChange : undefined
              }
            />
          </div>
        </div>
      )}

      {/* Export Report Dialog */}
      {task && (
        <ExportReportDialog
          issues={issues}
          onOpenChange={setExportDialogOpen}
          open={exportDialogOpen}
          task={task}
        />
      )}
    </div>
  );
}
