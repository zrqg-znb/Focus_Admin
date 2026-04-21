/**
 * Instant Analysis Page
 * Cyberpunk Terminal Aesthetic
 */

import type { PromptTemplate } from '@/shared/api/prompts';
import type {
  CodeAnalysisResult,
  InstantAnalysis as InstantAnalysisType,
  Project,
} from '@/shared/types';

import InstantExportDialog from '@/components/reports/InstantExportDialog';
import { Badge } from '@/components/ui/badge';
import { BranchSelector } from '@/components/ui/branch-selector';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { CodeAnalysisEngine } from '@/features/analysis/services';
import { getPromptTemplates } from '@/shared/api/prompts';
import { api } from '@/shared/config/database';
import { useAuth } from '@/shared/context/AuthContext';
import { DEEPAUDIT_ACTION_CODES } from '@/shared/focus/focusPermission';
import { parseAIExplanation } from '@/shared/utils/aiExplanation';
import {
  getRepositoryTypeLabel,
  isMultiRepository,
} from '@/shared/utils/projectUtils';
import {
  AlertTriangle,
  CheckCircle,
  ChevronRight,
  Clock,
  Code,
  Download,
  FileText,
  FolderGit2,
  GitBranch,
  History,
  Info,
  Lightbulb,
  MessageSquare,
  Search,
  Shield,
  Target,
  Terminal,
  TrendingUp,
  Upload,
  X,
  Zap,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

type AnalysisMode = 'repository' | 'snippet';

function parsePatternInput(value: string) {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function getErrorMessage(error: unknown, fallback: string) {
  if (typeof error === 'object' && error !== null) {
    const record = error as { message?: string };
    return record.message || fallback;
  }
  return fallback;
}

export default function InstantAnalysis() {
  const navigate = useNavigate();
  const { hasAccess } = useAuth();
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('');
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>('snippet');
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<CodeAnalysisResult | null>(null);
  const [analysisTime, setAnalysisTime] = useState(0);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [currentAnalysisId, setCurrentAnalysisId] = useState<null | string>(
    null,
  );
  const fileInputRef = useRef<HTMLInputElement>(null);
  const loadingCardRef = useRef<HTMLDivElement>(null);

  // History related state
  const [showHistory, setShowHistory] = useState(false);
  const [historyRecords, setHistoryRecords] = useState<InstantAnalysisType[]>(
    [],
  );
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [selectedHistoryId, setSelectedHistoryId] = useState<null | string>(
    null,
  );
  const [repositoryProjects, setRepositoryProjects] = useState<Project[]>([]);
  const [projectSearch, setProjectSearch] = useState('');
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [availableBranches, setAvailableBranches] = useState<string[]>([]);
  const [loadingBranches, setLoadingBranches] = useState(false);
  const [selectedBranch, setSelectedBranch] = useState('');
  const [selectedManifestXml, setSelectedManifestXml] = useState('');
  const [selectedGroup, setSelectedGroup] = useState('');
  const [repositoryExcludePatterns, setRepositoryExcludePatterns] =
    useState('');
  const [repositoryAnalysisDepth, setRepositoryAnalysisDepth] = useState<
    'basic' | 'deep' | 'standard'
  >('standard');

  // Prompt templates
  const [promptTemplates, setPromptTemplates] = useState<PromptTemplate[]>([]);
  const [selectedPromptTemplateId, setSelectedPromptTemplateId] =
    useState<string>('');
  const canExportReport = hasAccess(DEEPAUDIT_ACTION_CODES.REPORTS_EXPORT);
  const canCreateAuditTask = hasAccess(DEEPAUDIT_ACTION_CODES.TASKS_CREATE);

  const supportedLanguages = CodeAnalysisEngine.getSupportedLanguages();

  // Load prompt templates
  useEffect(() => {
    const loadPromptTemplates = async () => {
      try {
        const res = await getPromptTemplates({ is_active: true });
        setPromptTemplates(res.items);
        const defaultTemplate = res.items.find((t) => t.is_default);
        if (defaultTemplate) {
          setSelectedPromptTemplateId(defaultTemplate.id);
        } else if (res.items.length > 0) {
          setSelectedPromptTemplateId(res.items[0].id);
        }
      } catch (error) {
        console.error('加载提示词模板失败:', error);
      }
    };
    loadPromptTemplates();
  }, []);

  useEffect(() => {
    const loadRepositoryProjects = async () => {
      try {
        setLoadingProjects(true);
        const projects = await CodeAnalysisEngine.getRepositories();
        setRepositoryProjects(projects);
        setSelectedProjectId((current) => current || projects[0]?.id || '');
      } catch (error) {
        console.error('加载仓库项目失败:', error);
        toast.error('加载仓库项目失败');
      } finally {
        setLoadingProjects(false);
      }
    };
    void loadRepositoryProjects();
  }, []);

  useEffect(() => {
    if (!selectedProjectId) {
      setAvailableBranches([]);
      setSelectedBranch('');
      setSelectedManifestXml('');
      setSelectedGroup('');
      return;
    }
    const loadBranches = async () => {
      try {
        setLoadingBranches(true);
        const payload = await CodeAnalysisEngine.getBranches(selectedProjectId);
        const branches =
          payload.branches.length > 0
            ? payload.branches
            : [payload.default_branch || 'main'];
        setAvailableBranches(branches);
        setSelectedBranch((current) => {
          if (current && branches.includes(current)) {
            return current;
          }
          return payload.default_branch || branches[0] || 'main';
        });
      } catch (error) {
        console.error('加载项目分支失败:', error);
        setAvailableBranches(['main']);
        setSelectedBranch('main');
      } finally {
        setLoadingBranches(false);
      }
    };
    void loadBranches();
  }, [selectedProjectId]);

  useEffect(() => {
    const project = repositoryProjects.find(
      (item) => item.id === selectedProjectId,
    );
    if (!project) {
      setSelectedManifestXml('');
      setSelectedGroup('');
      return;
    }
    setSelectedManifestXml(project.manifest_xml || '');
    setSelectedGroup(project.group || '');
  }, [selectedProjectId, repositoryProjects]);

  // Load history
  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const records = await api.getInstantAnalyses();
      setHistoryRecords(records);
    } catch (error) {
      console.error('Failed to load history:', error);
      toast.error('加载历史记录失败');
    } finally {
      setLoadingHistory(false);
    }
  };

  // View history record details
  const viewHistoryRecord = (record: InstantAnalysisType) => {
    try {
      const analysisResult = JSON.parse(
        record.analysis_result,
      ) as CodeAnalysisResult;
      setResult(analysisResult);
      setLanguage(record.language);
      setAnalysisTime(record.analysis_time);
      setSelectedHistoryId(record.id);
      setCurrentAnalysisId(record.id);
      setShowHistory(false);
      toast.success('已加载历史分析结果');
    } catch (error) {
      console.error('Failed to parse history record:', error);
      toast.error('解析历史记录失败');
    }
  };

  // Format date
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Delete single history record
  const deleteHistoryRecord = async (e: React.MouseEvent, recordId: string) => {
    e.stopPropagation();
    try {
      await api.deleteInstantAnalysis(recordId);
      setHistoryRecords((prev) => prev.filter((r) => r.id !== recordId));
      if (selectedHistoryId === recordId) {
        setSelectedHistoryId(null);
        setResult(null);
      }
      toast.success('删除成功');
    } catch (error) {
      console.error('Failed to delete history:', error);
      toast.error('删除失败');
    }
  };

  // Clear all history
  const clearAllHistory = async () => {
    // eslint-disable-next-line no-alert
    if (!confirm('确定要清空所有历史记录吗？此操作不可恢复。')) return;
    try {
      await api.deleteAllInstantAnalyses();
      setHistoryRecords([]);
      setSelectedHistoryId(null);
      toast.success('已清空所有历史记录');
    } catch (error) {
      console.error('Failed to clear history:', error);
      toast.error('清空失败');
    }
  };

  // Toggle history panel
  const toggleHistory = () => {
    if (!showHistory) {
      loadHistory();
    }
    setShowHistory(!showHistory);
  };

  // Auto scroll to loading card when analyzing
  useEffect(() => {
    if (analyzing && loadingCardRef.current) {
      requestAnimationFrame(() => {
        setTimeout(() => {
          if (loadingCardRef.current) {
            loadingCardRef.current.scrollIntoView({
              behavior: 'smooth',
              block: 'center',
            });
          }
        }, 50);
      });
    }
  }, [analyzing]);

  // Example codes
  const exampleCodes = {
    javascript: `// 示例JavaScript代码 - 包含多种问题
var userName = "admin";
var password = "123456"; // 硬编码密码

function validateUser(input) {
    if (input == userName) { // 使用 == 比较
        console.log("User validated"); // 生产代码中的console.log
        return true;
    }
    return false;
}

// 性能问题：循环中重复计算长度
function processItems(items) {
    for (var i = 0; i < items.length; i++) {
        for (var j = 0; j < items.length; j++) {
            console.log(items[i] + items[j]);
        }
    }
}

// 安全问题：使用eval
function executeCode(userInput) {
    eval(userInput); // 危险的eval使用
}`,
    python: `# 示例Python代码 - 包含多种问题
import *  # 通配符导入

password = "secret123"  # 硬编码密码

def process_data(data):
    try:
        result = []
        for item in data:
            print(item)  # 使用print而非logging
            result.append(item * 2)
        return result
    except:  # 裸露的except语句
        pass`,
    java: `// 示例Java代码 - 包含多种问题
public class Example {
    private String password = "admin123"; // 硬编码密码

    public void processData() {
        System.out.println("Processing..."); // 使用System.out.print

        try {
            String data = getData();
        } catch (Exception e) {
            // 空的异常处理
        }
    }
}`,
  };

  const handleAnalyze = async () => {
    if (!code.trim()) {
      toast.error('请输入要分析的代码');
      return;
    }
    if (!language) {
      toast.error('请选择编程语言');
      return;
    }

    try {
      setAnalyzing(true);
      setTimeout(() => {
        window.scrollTo({
          top: document.body.scrollHeight,
          behavior: 'smooth',
        });
      }, 100);

      const startTime = Date.now();
      const analysisResult = await CodeAnalysisEngine.analyzeCode(
        code,
        language,
        selectedPromptTemplateId || undefined,
      );
      const endTime = Date.now();
      const duration = (endTime - startTime) / 1000;

      setResult(analysisResult);
      setAnalysisTime(analysisResult.analysis_time || duration);
      setCurrentAnalysisId(analysisResult.analysis_id || null);

      toast.success(`分析完成！发现 ${analysisResult.issues.length} 个问题`);
    } catch (error) {
      console.error('Analysis failed:', error);
      toast.error(getErrorMessage(error, '分析失败，请稍后重试'));
    } finally {
      setAnalyzing(false);
      setCode('');
    }
  };

  const handleRepositoryAnalyze = async () => {
    if (!canCreateAuditTask) {
      toast.error('当前账号没有创建仓库审计任务的权限');
      return;
    }
    if (!selectedProjectId) {
      toast.error('请选择一个仓库项目');
      return;
    }
    if (!selectedBranch.trim()) {
      toast.error('请选择要分析的分支');
      return;
    }
    const selectedProject = repositoryProjects.find(
      (project) => project.id === selectedProjectId,
    );
    if (
      selectedProject &&
      isMultiRepository(selectedProject) &&
      !selectedManifestXml.trim()
    ) {
      toast.error('多仓项目必须填写 Manifest XML');
      return;
    }

    try {
      setAnalyzing(true);
      const createdTask = await CodeAnalysisEngine.analyzeRepository({
        projectId: selectedProjectId,
        branch: selectedBranch.trim(),
        manifestXml: selectedManifestXml.trim() || undefined,
        group: selectedGroup.trim() || undefined,
        excludePatterns: parsePatternInput(repositoryExcludePatterns),
        promptTemplateId: selectedPromptTemplateId || undefined,
        analysisDepth: repositoryAnalysisDepth,
      });
      toast.success('仓库审计任务已创建，正在跳转到任务详情');
      navigate(`/tasks/${createdTask.id}`);
    } catch (error) {
      console.error('Repository analysis failed:', error);
      toast.error(error instanceof Error ? error.message : '启动仓库分析失败');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const content = await file.text();
    setCode(content);

    const extension = file.name.split('.').pop()?.toLowerCase();
    const languageMap: Record<string, string> = {
      js: 'javascript',
      jsx: 'javascript',
      ts: 'typescript',
      tsx: 'typescript',
      py: 'python',
      java: 'java',
      go: 'go',
      rs: 'rust',
      cpp: 'cpp',
      c: 'cpp',
      cs: 'csharp',
      php: 'php',
      rb: 'ruby',
      swift: 'swift',
      kt: 'kotlin',
    };

    if (extension && languageMap[extension]) {
      setLanguage(languageMap[extension]);
    }
  };

  const loadExampleCode = (lang: string) => {
    const example = exampleCodes[lang as keyof typeof exampleCodes];
    if (example) {
      setCode(example);
      setLanguage(lang);
      toast.success(`已加载${lang}示例代码`);
    }
  };

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

  const getQualityBadgeClass = (score: number) => {
    if (score >= 80) {
      return 'cyber-badge-success';
    }
    if (score >= 60) {
      return 'cyber-badge-warning';
    }
    return 'cyber-badge-danger';
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

  const clearAnalysis = () => {
    setCode('');
    setLanguage('');
    setResult(null);
    setAnalysisTime(0);
  };

  const selectedProject =
    repositoryProjects.find((project) => project.id === selectedProjectId) ||
    null;
  const filteredProjects = repositoryProjects.filter((project) => {
    const keyword = projectSearch.trim().toLowerCase();
    if (!keyword) {
      return true;
    }
    return (
      project.name.toLowerCase().includes(keyword) ||
      project.description?.toLowerCase().includes(keyword) ||
      project.repository_url?.toLowerCase().includes(keyword)
    );
  });

  const historyContent = (() => {
    if (loadingHistory) {
      return (
        <div className="py-8 text-center">
          <div className="loading-spinner mx-auto mb-4"></div>
          <p className="text-muted-foreground font-mono">加载中...</p>
        </div>
      );
    }

    if (historyRecords.length === 0) {
      return (
        <div className="empty-state">
          <History className="empty-state-icon" />
          <p className="empty-state-title">暂无历史记录</p>
          <p className="empty-state-description">
            完成代码分析后，记录将显示在这里
          </p>
        </div>
      );
    }

    return (
      <ScrollArea className="h-[400px]">
        <div className="space-y-3">
          {historyRecords.map((record) => (
            <button
              className={`cursor-pointer rounded-lg border p-4 transition-colors ${
                selectedHistoryId === record.id
                  ? 'bg-primary/10 border-primary/30'
                  : 'bg-muted/50 border-border hover:bg-muted hover:border-border'
              } w-full text-left`}
              key={record.id}
              onClick={() => viewHistoryRecord(record)}
              type="button"
            >
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge className="cyber-badge-muted">{record.language}</Badge>
                  <span className="text-muted-foreground font-mono text-sm">
                    {formatDate(record.created_at)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge
                    className={`font-mono ${getQualityBadgeClass(record.quality_score ?? 0)}`}
                  >
                    评分: {(record.quality_score ?? 0).toFixed(1)}
                  </Badge>
                  <Button
                    className="h-6 w-6 p-0 hover:bg-rose-500/10 hover:text-rose-400"
                    onClick={(e) => deleteHistoryRecord(e, record.id)}
                    size="sm"
                    variant="ghost"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                  <ChevronRight className="text-muted-foreground h-4 w-4" />
                </div>
              </div>
              <div className="text-muted-foreground flex items-center gap-4 font-mono text-xs">
                <span className="flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  {record.issues_count} 个问题
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {(record.analysis_time ?? 0).toFixed(2)}s
                </span>
              </div>
            </button>
          ))}
        </div>
      </ScrollArea>
    );
  })();

  const projectListContent = (() => {
    if (loadingProjects) {
      return (
        <div className="cyber-card text-muted-foreground p-6 text-center font-mono text-sm">
          加载仓库项目中...
        </div>
      );
    }

    if (filteredProjects.length === 0) {
      return (
        <div className="cyber-card text-muted-foreground p-6 text-center font-mono text-sm">
          当前没有可用于仓库分析的项目
        </div>
      );
    }

    return filteredProjects.map((project) => {
      const active = project.id === selectedProjectId;

      return (
        <button
          className={`w-full rounded-lg border p-4 text-left transition-all ${
            active
              ? 'border-primary bg-primary/10 shadow-[0_0_0_1px_rgba(255,107,44,0.35)]'
              : 'border-border bg-background hover:border-primary/40'
          }`}
          key={project.id}
          onClick={() => setSelectedProjectId(project.id)}
          type="button"
        >
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="text-foreground font-semibold">
                {project.name}
              </div>
              <div className="text-muted-foreground mt-1 truncate font-mono text-xs">
                {project.repository_url}
              </div>
            </div>
            <Badge
              className={`font-mono text-xs ${isMultiRepository(project) ? 'cyber-badge-info' : 'cyber-badge-muted'}`}
            >
              {getRepositoryTypeLabel(project.repository_type)}
            </Badge>
          </div>
        </button>
      );
    });
  })();

  // Render issue with cyberpunk style
  const renderIssue = (
    issue: CodeAnalysisResult['issues'][number],
    index: number,
  ) => (
    <div
      className="cyber-card hover:border-border group mb-4 p-4 transition-all"
      key={index}
    >
      <div className="border-border mb-3 flex items-start justify-between border-b pb-3">
        <div className="flex items-start space-x-3">
          <div
            className={`flex h-10 w-10 items-center justify-center rounded-lg ${getSeverityIconClasses(issue.severity)}`}
          >
            {getTypeIcon(issue.type)}
          </div>
          <div className="flex-1">
            <h4 className="text-foreground group-hover:text-primary mb-1 text-base font-bold uppercase transition-colors">
              {issue.title}
            </h4>
            <div className="text-muted-foreground flex items-center space-x-1 font-mono text-xs">
              <span className="text-primary">&gt;</span>
              <span>LINE: {issue.line}</span>
              {issue.column && <span>, COL: {issue.column}</span>}
            </div>
          </div>
        </div>
        <Badge
          className={`${getSeverityClasses(issue.severity)} rounded px-2 py-1 text-xs font-bold uppercase`}
        >
          {getSeverityLabel(issue.severity)}
        </Badge>
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
            <span className="text-muted-foreground font-mono text-xs">
              LINE: {issue.line}
            </span>
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

            if (parsedExplanation.hasStructuredContent) {
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
    </div>
  );

  return (
    <div className="cyber-bg-elevated relative min-h-screen space-y-6 p-6 font-mono">
      {/* Grid background */}
      <div className="cyber-grid-subtle pointer-events-none absolute inset-0" />

      {/* History Panel */}
      {showHistory && (
        <div className="cyber-card relative z-10 p-0">
          <div className="cyber-card-header">
            <History className="text-primary h-5 w-5" />
            <h3 className="text-foreground text-lg font-bold uppercase tracking-wider">
              分析历史记录
            </h3>
            <div className="ml-auto flex items-center gap-2">
              {historyRecords.length > 0 && (
                <Button
                  className="cyber-btn h-8 border-rose-500/30 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20"
                  onClick={clearAllHistory}
                  size="sm"
                  variant="outline"
                >
                  清空全部
                </Button>
              )}
              <Button
                className="cyber-btn-ghost h-8 w-8 p-0"
                onClick={() => setShowHistory(false)}
                size="sm"
                variant="outline"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div className="p-4">{historyContent}</div>
        </div>
      )}

      {/* Code Input Area */}
      <div className="cyber-card relative z-10 p-0">
        <div className="cyber-card-header">
          <Terminal className="text-primary h-5 w-5" />
          <h3 className="text-foreground text-lg font-bold uppercase tracking-wider">
            {analysisMode === 'snippet' ? '代码分析' : '仓库分析'}
          </h3>
          <div className="ml-auto flex items-center gap-2">
            <Button
              className={`h-8 ${showHistory ? 'cyber-btn-primary' : 'cyber-btn-outline'}`}
              onClick={toggleHistory}
              size="sm"
              variant="outline"
            >
              <History className="mr-2 h-4 w-4" />
              历史记录
            </Button>
            {result && (
              <Button
                className="cyber-btn-outline h-8"
                onClick={clearAnalysis}
                size="sm"
                variant="outline"
              >
                <X className="mr-2 h-4 w-4" />
                重新分析
              </Button>
            )}
          </div>
        </div>

        <div className="space-y-4 p-6">
          <Tabs
            className="space-y-4"
            onValueChange={(value) => setAnalysisMode(value as AnalysisMode)}
            value={analysisMode}
          >
            <TabsList className="bg-muted border-border grid h-auto w-full grid-cols-2 gap-1 rounded-lg border p-1">
              <TabsTrigger
                className="data-[state=active]:bg-primary data-[state=active]:text-foreground text-muted-foreground flex items-center gap-2 rounded py-2.5 font-mono text-xs font-bold uppercase transition-all"
                value="snippet"
              >
                <Code className="h-3 w-3" />
                代码片段
              </TabsTrigger>
              <TabsTrigger
                className="data-[state=active]:bg-primary data-[state=active]:text-foreground text-muted-foreground flex items-center gap-2 rounded py-2.5 font-mono text-xs font-bold uppercase transition-all"
                value="repository"
              >
                <FolderGit2 className="h-3 w-3" />
                仓库项目
              </TabsTrigger>
            </TabsList>

            <TabsContent className="space-y-4" value="snippet">
              <div className="flex flex-col gap-3 sm:flex-row">
                <div className="flex-1 space-y-1">
                  <Label className="text-muted-foreground text-xs font-bold uppercase">
                    编程语言
                  </Label>
                  <Select onValueChange={setLanguage} value={language}>
                    <SelectTrigger className="cyber-input h-10">
                      <SelectValue placeholder="选择编程语言" />
                    </SelectTrigger>
                    <SelectContent className="cyber-dialog border-border">
                      {supportedLanguages.map((lang) => (
                        <SelectItem key={lang} value={lang}>
                          {lang.charAt(0).toUpperCase() + lang.slice(1)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex-1 space-y-1">
                  <Label className="text-muted-foreground text-xs font-bold uppercase">
                    提示词模板
                  </Label>
                  <Select
                    onValueChange={setSelectedPromptTemplateId}
                    value={selectedPromptTemplateId}
                  >
                    <SelectTrigger className="cyber-input h-10">
                      <div className="flex items-center gap-2">
                        <MessageSquare className="h-4 w-4 text-violet-400" />
                        <SelectValue placeholder="选择提示词模板" />
                      </div>
                    </SelectTrigger>
                    <SelectContent className="cyber-dialog border-border">
                      {promptTemplates.map((pt) => (
                        <SelectItem key={pt.id} value={pt.id}>
                          {pt.name} {pt.is_default && '(默认)'}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-end">
                  <Button
                    className="cyber-btn-outline h-10"
                    disabled={analyzing}
                    onClick={() => fileInputRef.current?.click()}
                    variant="outline"
                  >
                    <Upload className="mr-2 h-4 w-4" />
                    上传文件
                  </Button>
                </div>
                <input
                  accept=".js,.jsx,.ts,.tsx,.py,.java,.go,.rs,.cpp,.c,.cc,.h,.hh,.cs,.php,.rb,.swift,.kt"
                  className="hidden"
                  onChange={handleFileUpload}
                  ref={fileInputRef}
                  type="file"
                />
              </div>

              <div className="bg-muted border-border flex flex-wrap items-center gap-2 rounded border p-3">
                <span className="text-muted-foreground mr-2 text-xs font-bold uppercase">
                  示例：
                </span>
                {['javascript', 'python', 'java'].map((lang) => (
                  <Button
                    className="cyber-btn-ghost h-7 px-2 text-xs"
                    disabled={analyzing}
                    key={lang}
                    onClick={() => loadExampleCode(lang)}
                    size="sm"
                    variant="outline"
                  >
                    {lang.charAt(0).toUpperCase() + lang.slice(1)}
                  </Button>
                ))}
              </div>

              <div className="relative">
                <div className="bg-muted text-muted-foreground border-border absolute right-0 top-0 z-10 rounded-bl border-b border-l px-2 py-1 font-mono text-xs uppercase">
                  Editor
                </div>
                <Textarea
                  className="cyber-bg-elevated border-border focus:border-primary/50 placeholder:text-muted-foreground min-h-[300px] border p-4 font-mono text-sm text-emerald-400 focus:ring-0"
                  disabled={analyzing}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="// 粘贴代码或上传文件..."
                  value={code}
                />
                <div className="text-muted-foreground mt-1 text-right font-mono text-xs">
                  {code.length} 字符，{code.split('\n').length} 行
                </div>
              </div>

              <Button
                className="cyber-btn-primary h-12 w-full text-lg font-bold uppercase"
                disabled={!code.trim() || !language || analyzing}
                onClick={handleAnalyze}
              >
                {analyzing ? (
                  <>
                    <div className="loading-spinner mr-3 h-5 w-5"></div>
                    分析中...
                  </>
                ) : (
                  <>
                    <Zap className="mr-2 h-5 w-5" />
                    开始分析
                  </>
                )}
              </Button>
            </TabsContent>

            <TabsContent className="space-y-4" value="repository">
              <div className="border-border bg-muted/40 rounded-lg border p-4">
                <div className="text-foreground flex items-center gap-2 text-sm font-semibold">
                  <FolderGit2 className="text-primary h-4 w-4" />
                  启动真实仓库审计任务
                </div>
                <p className="text-muted-foreground mt-2 text-xs leading-6">
                  这里会直接复用 FocusAudit
                  的仓库扫描后端，创建正式审计任务并跳转到任务详情，而不是走任何
                  mock 流程。
                </p>
              </div>

              <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
                <div className="space-y-3">
                  <Label className="text-muted-foreground text-xs font-bold uppercase">
                    仓库项目
                  </Label>
                  <div className="relative">
                    <Search className="text-muted-foreground absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" />
                    <Input
                      className="cyber-input pl-10"
                      onChange={(event) => setProjectSearch(event.target.value)}
                      placeholder="搜索项目名称或仓库地址"
                      value={projectSearch}
                    />
                  </div>
                  <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
                    {projectListContent}
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs font-bold uppercase">
                      目标分支
                    </Label>
                    <BranchSelector
                      branches={availableBranches}
                      className="h-10 w-full"
                      disabled={!selectedProjectId || loadingBranches}
                      onChange={setSelectedBranch}
                      value={selectedBranch}
                    />
                    <p className="text-muted-foreground text-xs">
                      {loadingBranches
                        ? '正在拉取分支列表...'
                        : `可选分支 ${availableBranches.length || 0} 个`}
                    </p>
                  </div>

                  {selectedProject && isMultiRepository(selectedProject) && (
                    <>
                      <div className="space-y-2">
                        <Label className="text-muted-foreground text-xs font-bold uppercase">
                          Manifest XML
                        </Label>
                        <Input
                          className="cyber-input h-10"
                          onChange={(event) =>
                            setSelectedManifestXml(event.target.value)
                          }
                          placeholder={
                            selectedProject.manifest_xml || 'default.xml'
                          }
                          value={selectedManifestXml}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-muted-foreground text-xs font-bold uppercase">
                          Group
                        </Label>
                        <Input
                          className="cyber-input h-10"
                          onChange={(event) =>
                            setSelectedGroup(event.target.value)
                          }
                          placeholder={selectedProject.group || '可选'}
                          value={selectedGroup}
                        />
                        <p className="text-muted-foreground text-xs">
                          多仓会按 `git mm init -u ... -b ... -m ... [-g ...]`
                          后再执行 `git mm sync`
                        </p>
                      </div>
                    </>
                  )}

                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs font-bold uppercase">
                      提示词模板
                    </Label>
                    <Select
                      onValueChange={setSelectedPromptTemplateId}
                      value={selectedPromptTemplateId}
                    >
                      <SelectTrigger className="cyber-input h-10">
                        <div className="flex items-center gap-2">
                          <MessageSquare className="h-4 w-4 text-violet-400" />
                          <SelectValue placeholder="选择提示词模板" />
                        </div>
                      </SelectTrigger>
                      <SelectContent className="cyber-dialog border-border">
                        {promptTemplates.map((pt) => (
                          <SelectItem key={pt.id} value={pt.id}>
                            {pt.name} {pt.is_default && '(默认)'}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs font-bold uppercase">
                      分析深度
                    </Label>
                    <Select
                      onValueChange={(value: 'basic' | 'deep' | 'standard') =>
                        setRepositoryAnalysisDepth(value)
                      }
                      value={repositoryAnalysisDepth}
                    >
                      <SelectTrigger className="cyber-input h-10">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="cyber-dialog border-border">
                        <SelectItem value="basic">Basic</SelectItem>
                        <SelectItem value="standard">Standard</SelectItem>
                        <SelectItem value="deep">Deep</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs font-bold uppercase">
                      排除模式
                    </Label>
                    <Textarea
                      className="cyber-input min-h-32 font-mono text-xs"
                      onChange={(event) =>
                        setRepositoryExcludePatterns(event.target.value)
                      }
                      placeholder={
                        '每行一个，或使用逗号分隔，例如\nnode_modules/**\ndist/**\n*.min.js'
                      }
                      value={repositoryExcludePatterns}
                    />
                  </div>

                  {selectedProject && (
                    <div className="border-border bg-muted/30 text-muted-foreground rounded-lg border p-4 font-mono text-xs">
                      <div className="text-foreground flex items-center gap-2">
                        <GitBranch className="text-primary h-4 w-4" />
                        当前项目
                      </div>
                      <div className="mt-3 space-y-2">
                        <div>名称: {selectedProject.name}</div>
                        <div className="break-all">
                          仓库: {selectedProject.repository_url}
                        </div>
                        <div>
                          模式:{' '}
                          {getRepositoryTypeLabel(
                            selectedProject.repository_type,
                          )}
                        </div>
                        <div>
                          默认分支: {selectedProject.default_branch || 'main'}
                        </div>
                        {isMultiRepository(selectedProject) && (
                          <>
                            <div>
                              Manifest: {selectedManifestXml || '未设置'}
                            </div>
                            <div>Group: {selectedGroup || '未设置'}</div>
                          </>
                        )}
                      </div>
                    </div>
                  )}

                  <Button
                    className="cyber-btn-primary h-12 w-full text-base font-bold uppercase"
                    disabled={
                      !selectedProjectId ||
                      !selectedBranch ||
                      (selectedProject
                        ? isMultiRepository(selectedProject) &&
                          !selectedManifestXml.trim()
                        : false) ||
                      analyzing ||
                      !canCreateAuditTask
                    }
                    onClick={handleRepositoryAnalyze}
                  >
                    {analyzing ? (
                      <>
                        <div className="loading-spinner mr-3 h-5 w-5"></div>
                        创建任务中...
                      </>
                    ) : (
                      <>
                        <FolderGit2 className="mr-2 h-5 w-5" />
                        启动仓库审计
                      </>
                    )}
                  </Button>
                  {!canCreateAuditTask && (
                    <p className="text-xs text-amber-400">
                      当前账号没有创建仓库审计任务的权限。
                    </p>
                  )}
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Analysis Results */}
      {result && (
        <div className="relative z-10 space-y-6">
          {/* Results Overview */}
          <div className="cyber-card p-0">
            <div className="cyber-card-header">
              <CheckCircle className="h-5 w-5 text-emerald-400" />
              <h3 className="text-foreground text-lg font-bold uppercase tracking-wider">
                分析结果
              </h3>
              <div className="ml-auto flex items-center gap-2">
                <Badge className="cyber-badge-muted">
                  <Clock className="mr-1 h-3 w-3" />
                  {(analysisTime ?? 0).toFixed(2)}s
                </Badge>
                <Badge className="cyber-badge-muted uppercase">
                  {language}
                </Badge>
                {canExportReport && (
                  <Button
                    className="cyber-btn-primary h-8"
                    onClick={() => setExportDialogOpen(true)}
                    size="sm"
                  >
                    <Download className="mr-2 h-4 w-4" />
                    导出报告
                  </Button>
                )}
              </div>
            </div>
            <div className="p-6">
              {/* Core Metrics */}
              <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
                <div className="cyber-card p-4 text-center">
                  <div className="stat-icon text-primary mx-auto mb-3">
                    <Target className="h-6 w-6" />
                  </div>
                  <div className="stat-value text-primary mb-1">
                    {(result.quality_score ?? 0).toFixed(1)}
                  </div>
                  <p className="stat-label mb-2">质量评分</p>
                  <Progress
                    className="bg-muted [&>div]:bg-primary h-2"
                    value={result.quality_score ?? 0}
                  />
                </div>

                <div className="cyber-card p-4 text-center">
                  <div className="stat-icon mx-auto mb-3 text-rose-400">
                    <AlertTriangle className="h-6 w-6" />
                  </div>
                  <div className="stat-value mb-1 text-rose-400">
                    {(result.summary?.critical_issues ?? 0) +
                      (result.summary?.high_issues ?? 0)}
                  </div>
                  <p className="stat-label mb-1">严重问题</p>
                  <div className="text-xs uppercase text-rose-400">
                    需要立即处理
                  </div>
                </div>

                <div className="cyber-card p-4 text-center">
                  <div className="stat-icon mx-auto mb-3 text-amber-400">
                    <Info className="h-6 w-6" />
                  </div>
                  <div className="stat-value mb-1 text-amber-400">
                    {(result.summary?.medium_issues ?? 0) +
                      (result.summary?.low_issues ?? 0)}
                  </div>
                  <p className="stat-label mb-1">一般问题</p>
                  <div className="text-xs uppercase text-amber-400">
                    建议优化
                  </div>
                </div>

                <div className="cyber-card p-4 text-center">
                  <div className="stat-icon mx-auto mb-3 text-emerald-400">
                    <FileText className="h-6 w-6" />
                  </div>
                  <div className="stat-value mb-1 text-emerald-400">
                    {result.issues.length}
                  </div>
                  <p className="stat-label mb-1">总问题数</p>
                  <div className="text-xs uppercase text-emerald-400">
                    已全部识别
                  </div>
                </div>
              </div>

              {/* Detailed Metrics */}
              <div className="bg-muted border-border rounded-lg border p-4">
                <h3 className="section-title mb-4 flex items-center gap-2 text-sm">
                  <TrendingUp className="h-4 w-4" />
                  详细指标
                </h3>
                <div className="grid grid-cols-2 gap-6 font-mono lg:grid-cols-4">
                  {[
                    { label: '复杂度', value: result.metrics?.complexity ?? 0 },
                    {
                      label: '可维护性',
                      value: result.metrics?.maintainability ?? 0,
                    },
                    { label: '安全性', value: result.metrics?.security ?? 0 },
                    { label: '性能', value: result.metrics?.performance ?? 0 },
                  ].map((metric) => (
                    <div className="text-center" key={metric.label}>
                      <div className="text-foreground mb-1 text-xl font-bold">
                        {metric.value}
                      </div>
                      <p className="text-muted-foreground mb-2 text-xs uppercase">
                        {metric.label}
                      </p>
                      <Progress
                        className="bg-muted [&>div]:bg-primary h-2"
                        value={metric.value}
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Issues Detail */}
          <div className="cyber-card p-0">
            <div className="cyber-card-header">
              <Shield className="h-5 w-5 text-amber-400" />
              <h3 className="text-foreground text-lg font-bold uppercase tracking-wider">
                发现的问题 ({result.issues.length})
              </h3>
            </div>
            <div className="p-6">
              {result.issues.length > 0 ? (
                <Tabs className="w-full" defaultValue="all">
                  <TabsList className="bg-muted border-border mb-6 grid h-auto w-full grid-cols-4 gap-1 rounded border p-1">
                    <TabsTrigger
                      className="data-[state=active]:bg-primary data-[state=active]:text-foreground text-muted-foreground rounded-sm py-2 font-mono text-xs font-bold uppercase transition-all"
                      value="all"
                    >
                      全部 ({result.issues.length})
                    </TabsTrigger>
                    <TabsTrigger
                      className="data-[state=active]:text-foreground text-muted-foreground rounded-sm py-2 font-mono text-xs font-bold uppercase transition-all data-[state=active]:bg-rose-500"
                      value="critical"
                    >
                      严重 (
                      {
                        result.issues.filter((i) => i.severity === 'critical')
                          .length
                      }
                      )
                    </TabsTrigger>
                    <TabsTrigger
                      className="data-[state=active]:text-foreground text-muted-foreground rounded-sm py-2 font-mono text-xs font-bold uppercase transition-all data-[state=active]:bg-orange-500"
                      value="high"
                    >
                      高 (
                      {
                        result.issues.filter((i) => i.severity === 'high')
                          .length
                      }
                      )
                    </TabsTrigger>
                    <TabsTrigger
                      className="data-[state=active]:text-background text-muted-foreground rounded-sm py-2 font-mono text-xs font-bold uppercase transition-all data-[state=active]:bg-amber-500"
                      value="medium"
                    >
                      中等 (
                      {
                        result.issues.filter((i) => i.severity === 'medium')
                          .length
                      }
                      )
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent className="mt-0 space-y-4" value="all">
                    {result.issues.map((issue, index) =>
                      renderIssue(issue, index),
                    )}
                  </TabsContent>

                  {['critical', 'high', 'medium'].map((severity) => (
                    <TabsContent
                      className="mt-0 space-y-4"
                      key={severity}
                      value={severity}
                    >
                      {(() => {
                        const severityLabel = (() => {
                          if (severity === 'critical') {
                            return '严重';
                          }
                          if (severity === 'high') {
                            return '高优先级';
                          }
                          return '中等优先级';
                        })();

                        return result.issues.some(
                          (issue) => issue.severity === severity,
                        ) ? (
                          result.issues
                            .filter((issue) => issue.severity === severity)
                            .map((issue, index) => renderIssue(issue, index))
                        ) : (
                          <div className="cyber-card border-dashed p-12 text-center">
                            <CheckCircle className="mx-auto mb-4 h-16 w-16 text-emerald-400" />
                            <h3 className="text-foreground mb-2 text-lg font-bold uppercase">
                              没有发现
                              {severityLabel}
                              问题
                            </h3>
                            <p className="text-muted-foreground font-mono">
                              代码在此级别的检查中表现良好
                            </p>
                          </div>
                        );
                      })()}
                    </TabsContent>
                  ))}
                </Tabs>
              ) : (
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
              )}
            </div>
          </div>
        </div>
      )}

      {/* Analyzing State */}
      {analyzing && (
        <div className="cyber-card relative z-10 p-0">
          <div className="px-6 py-16 text-center" ref={loadingCardRef}>
            <div className="bg-primary/20 border-primary/40 mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-lg border">
              <div className="loading-spinner h-12 w-12"></div>
            </div>
            <h3 className="text-foreground mb-3 text-2xl font-bold uppercase">
              AI正在分析您的代码
            </h3>
            <p className="text-muted-foreground mb-6 font-mono">
              请稍候，这通常需要至少30秒钟...
            </p>
            <p className="text-muted-foreground mb-6 font-mono text-sm">
              分析时长取决于您的网络环境、代码长度以及使用的模型等因素
            </p>
            <div className="bg-primary/10 border-primary/30 mx-auto max-w-md rounded border p-4">
              <p className="text-primary font-mono text-sm">
                正在进行安全检测、性能分析、代码风格检查等多维度评估
                <br />
                请勿离开页面！
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Export Report Dialog */}
      {result && (
        <InstantExportDialog
          analysisId={currentAnalysisId}
          analysisResult={result}
          analysisTime={analysisTime}
          language={language}
          onOpenChange={setExportDialogOpen}
          open={exportDialogOpen}
        />
      )}
    </div>
  );
}
