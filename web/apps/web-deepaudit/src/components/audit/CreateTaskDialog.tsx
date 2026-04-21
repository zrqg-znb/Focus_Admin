/**
 * Create Task Dialog
 * Cyberpunk Terminal Aesthetic
 */

import type { AuditMode } from '@/components/agent/AgentModeSelector';
import type { PromptTemplate } from '@/shared/api/prompts';
import type { AuditRuleSet } from '@/shared/api/rules';
import type { Project } from '@/shared/types';

import AgentModeSelector from '@/components/agent/AgentModeSelector';
import { Badge } from '@/components/ui/badge';
import { BranchSelector } from '@/components/ui/branch-selector';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { runRepositoryAudit } from '@/features/projects/services/repoScan';
import {
  scanStoredZipFile,
  scanZipFile,
  validateZipFile,
} from '@/features/projects/services/repoZipScan';
import { createAgentTask } from '@/shared/api/agentTasks';
import { getPromptTemplates } from '@/shared/api/prompts';
import { getRuleSets } from '@/shared/api/rules';
import { api } from '@/shared/config/database';
import { useAuth } from '@/shared/context/AuthContext';
import { DEEPAUDIT_ACTION_CODES } from '@/shared/focus/focusPermission';
import {
  getRepositoryTypeLabel,
  isMultiRepository,
  isRepositoryProject,
  isZipProject,
} from '@/shared/utils/projectUtils';
import {
  Bot,
  ChevronRight,
  FolderOpen,
  GitBranch,
  Globe,
  Loader2,
  Package,
  Search,
  Settings2,
  Shield,
  Upload,
  Zap,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import FileSelectionDialog from './FileSelectionDialog';
import { useProjects } from './hooks/useTaskForm';
import { formatFileSize, useZipFile } from './hooks/useZipFile';

interface CreateTaskDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTaskCreated: () => void;
  onFastScanStarted?: (taskId: string) => void;
  preselectedProjectId?: string;
}

const DEFAULT_EXCLUDES = [
  'node_modules/**',
  '.git/**',
  'dist/**',
  'build/**',
  '*.log',
];

export default function CreateTaskDialog({
  open,
  onOpenChange,
  onTaskCreated,
  onFastScanStarted,
  preselectedProjectId,
}: CreateTaskDialogProps) {
  const navigate = useNavigate();
  const { hasAccess } = useAuth();
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [branch, setBranch] = useState('main');
  const [manifestXml, setManifestXml] = useState('');
  const [group, setGroup] = useState('');
  const [branches, setBranches] = useState<string[]>([]);
  const [loadingBranches, setLoadingBranches] = useState(false);
  const [excludePatterns, setExcludePatterns] = useState(DEFAULT_EXCLUDES);
  const [selectedFiles, setSelectedFiles] = useState<string[] | undefined>();
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showFileSelection, setShowFileSelection] = useState(false);
  const [creating, setCreating] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [auditMode, setAuditMode] = useState<AuditMode>('agent');

  const [ruleSets, setRuleSets] = useState<AuditRuleSet[]>([]);
  const [promptTemplates, setPromptTemplates] = useState<PromptTemplate[]>([]);
  const [selectedRuleSetId, setSelectedRuleSetId] = useState<string>('');
  const [selectedPromptTemplateId, setSelectedPromptTemplateId] =
    useState<string>('');

  const { projects, loading, loadProjects } = useProjects();
  const selectedProject = projects.find((p) => p.id === selectedProjectId);
  const zipState = useZipFile(selectedProject, projects);
  const canCreateFastTask = hasAccess(DEEPAUDIT_ACTION_CODES.TASKS_CREATE);
  const canCreateAgentTask = hasAccess(
    DEEPAUDIT_ACTION_CODES.AGENT_TASKS_CREATE,
  );

  useEffect(() => {
    const loadBranches = async () => {
      const project = projects.find((p) => p.id === selectedProjectId);
      if (!project || !isRepositoryProject(project)) {
        setBranches([]);
        return;
      }

      setLoadingBranches(true);
      try {
        const result = await api.getProjectBranches(project.id);
        if (result.error) {
          toast.error(`加载分支失败: ${result.error}`);
        }
        setBranches(result.branches);
        if (result.default_branch) {
          setBranch(result.default_branch);
        }
      } catch (error) {
        const msg = error instanceof Error ? error.message : '未知错误';
        toast.error(`加载分支失败: ${msg}`);
        setBranches([project.default_branch || 'main']);
      } finally {
        setLoadingBranches(false);
      }
    };

    loadBranches();
  }, [selectedProjectId, projects]);

  const filteredProjects = useMemo(() => {
    if (!searchTerm) return projects;
    const term = searchTerm.toLowerCase();
    return projects.filter(
      (p) =>
        p.name.toLowerCase().includes(term) ||
        p.description?.toLowerCase().includes(term),
    );
  }, [projects, searchTerm]);

  useEffect(() => {
    const loadRulesAndPrompts = async () => {
      try {
        const [rulesRes, promptsRes] = await Promise.all([
          getRuleSets({ is_active: true }),
          getPromptTemplates({ is_active: true }),
        ]);
        setRuleSets(rulesRes.items);
        setPromptTemplates(promptsRes.items);
        const defaultRuleSet = rulesRes.items.find(
          (r: AuditRuleSet) => r.is_default,
        );
        if (defaultRuleSet) {
          setSelectedRuleSetId(defaultRuleSet.id);
        } else if (rulesRes.items.length > 0) {
          setSelectedRuleSetId(rulesRes.items[0].id);
        }
        const defaultPrompt = promptsRes.items.find(
          (p: PromptTemplate) => p.is_default,
        );
        if (defaultPrompt) {
          setSelectedPromptTemplateId(defaultPrompt.id);
        } else if (promptsRes.items.length > 0) {
          setSelectedPromptTemplateId(promptsRes.items[0].id);
        }
      } catch (error) {
        console.error('加载规则集和提示词失败:', error);
      }
    };
    loadRulesAndPrompts();
  }, []);

  useEffect(() => {
    if (open) {
      loadProjects();
      if (preselectedProjectId) {
        setSelectedProjectId(preselectedProjectId);
      }
      setSearchTerm('');
      setBranch('main');
      setManifestXml('');
      setGroup('');
      setShowAdvanced(false);
      const defaultRuleSet = ruleSets.find((r) => r.is_default);
      setSelectedRuleSetId(defaultRuleSet?.id || ruleSets[0]?.id || '');
      const defaultPrompt = promptTemplates.find((p) => p.is_default);
      setSelectedPromptTemplateId(
        defaultPrompt?.id || promptTemplates[0]?.id || '',
      );
      zipState.reset();
    }
  }, [open, preselectedProjectId, ruleSets, promptTemplates]);

  useEffect(() => {
    if (auditMode === 'agent' && !canCreateAgentTask && canCreateFastTask) {
      setAuditMode('fast');
    }
    if (auditMode === 'fast' && !canCreateFastTask && canCreateAgentTask) {
      setAuditMode('agent');
    }
  }, [auditMode, canCreateAgentTask, canCreateFastTask]);

  useEffect(() => {
    if (!selectedProject || !isRepositoryProject(selectedProject)) {
      setManifestXml('');
      setGroup('');
      return;
    }
    setBranch(selectedProject.default_branch || 'main');
    setManifestXml(selectedProject.manifest_xml || '');
    setGroup(selectedProject.group || '');
  }, [selectedProject?.id]);

  const excludePatternsRef = useRef(excludePatterns);
  useEffect(() => {
    if (excludePatternsRef.current !== excludePatterns && selectedFiles) {
      setSelectedFiles(undefined);
      toast.info('排除模式已更改，请重新选择文件');
    }
    excludePatternsRef.current = excludePatterns;
  }, [excludePatterns]);

  const handleStartScan = async () => {
    if (!selectedProject) {
      toast.error('请选择项目');
      return;
    }

    if (auditMode === 'agent' && !canCreateAgentTask) {
      toast.error('当前账号没有创建 Agent 审计任务的权限');
      return;
    }

    if (auditMode === 'fast' && !canCreateFastTask) {
      toast.error('当前账号没有创建快速审计任务的权限');
      return;
    }

    try {
      setCreating(true);
      let taskId: string;

      if (auditMode === 'agent') {
        const agentTask = await createAgentTask({
          project_id: selectedProject.id,
          name: `Agent审计-${selectedProject.name}`,
          branch_name: isRepositoryProject(selectedProject)
            ? branch
            : undefined,
          manifest_xml: isRepositoryProject(selectedProject)
            ? manifestXml || undefined
            : undefined,
          group: isRepositoryProject(selectedProject)
            ? group || undefined
            : undefined,
          exclude_patterns: excludePatterns,
          target_files: selectedFiles,
          verification_level: 'sandbox',
        });

        onOpenChange(false);
        onTaskCreated();
        toast.success('Agent 审计任务已创建');
        navigate(`/agent-audit/${agentTask.id}`);

        setSelectedProjectId('');
        setSelectedFiles(undefined);
        setExcludePatterns(DEFAULT_EXCLUDES);
        return;
      }

      if (isZipProject(selectedProject)) {
        if (zipState.useStoredZip && zipState.storedZipInfo?.has_file) {
          taskId = await scanStoredZipFile({
            projectId: selectedProject.id,
            excludePatterns,
            createdBy: 'local-user',
            filePaths: selectedFiles,
            ruleSetId: selectedRuleSetId || undefined,
            promptTemplateId: selectedPromptTemplateId || undefined,
          });
        } else if (zipState.zipFile) {
          taskId = await scanZipFile({
            projectId: selectedProject.id,
            zipFile: zipState.zipFile,
            excludePatterns,
            createdBy: 'local-user',
            ruleSetId: selectedRuleSetId || undefined,
            promptTemplateId: selectedPromptTemplateId || undefined,
          });
        } else {
          toast.error('请上传 ZIP 文件');
          return;
        }
      } else {
        if (!selectedProject.repository_url) {
          toast.error('仓库地址为空');
          return;
        }
        taskId = await runRepositoryAudit({
          projectId: selectedProject.id,
          repoUrl: selectedProject.repository_url,
          branch,
          manifestXml,
          group,
          exclude: excludePatterns,
          createdBy: 'local-user',
          filePaths: selectedFiles,
          ruleSetId: selectedRuleSetId || undefined,
          promptTemplateId: selectedPromptTemplateId || undefined,
        });
      }

      onOpenChange(false);
      onTaskCreated();
      if (onFastScanStarted) {
        onFastScanStarted(taskId);
      }
      toast.success('扫描任务已启动');

      setSelectedProjectId('');
      setSelectedFiles(undefined);
      setExcludePatterns(DEFAULT_EXCLUDES);
    } catch (error) {
      const msg = error instanceof Error ? error.message : '未知错误';
      toast.error(`启动失败: ${msg}`);
    } finally {
      setCreating(false);
    }
  };

  const canStart = useMemo(() => {
    if (!selectedProject) return false;
    if (isZipProject(selectedProject)) {
      return (
        (zipState.useStoredZip && zipState.storedZipInfo?.has_file) ||
        !!zipState.zipFile
      );
    }
    if (isMultiRepository(selectedProject)) {
      return (
        !!selectedProject.repository_url &&
        !!branch.trim() &&
        !!manifestXml.trim()
      );
    }
    return !!selectedProject.repository_url && !!branch.trim();
  }, [selectedProject, zipState, branch, manifestXml]);
  const canSubmitCurrentMode =
    auditMode === 'agent' ? canCreateAgentTask : canCreateFastTask;

  const projectListContent = (() => {
    if (loading) {
      return (
        <div className="flex h-full items-center justify-center">
          <Loader2 className="text-primary h-5 w-5 animate-spin" />
        </div>
      );
    }

    if (filteredProjects.length === 0) {
      return (
        <div className="text-muted-foreground flex h-full flex-col items-center justify-center font-mono">
          <Package className="mb-2 h-8 w-8 opacity-50" />
          <span className="text-sm">{searchTerm ? '未找到' : '暂无项目'}</span>
        </div>
      );
    }

    return (
      <div className="p-1">
        {filteredProjects.map((project) => (
          <ProjectCard
            key={project.id}
            onSelect={() => setSelectedProjectId(project.id)}
            project={project}
            selected={selectedProjectId === project.id}
          />
        ))}
      </div>
    );
  })();

  const startButtonContent = (() => {
    if (creating) {
      return (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          启动中...
        </>
      );
    }

    if (auditMode === 'agent') {
      return (
        <>
          <Bot className="mr-2 h-4 w-4" />
          启动 Agent 审计
        </>
      );
    }

    return (
      <>
        <Zap className="mr-2 h-4 w-4" />
        开始快速扫描
      </>
    );
  })();

  return (
    <>
      <Dialog onOpenChange={onOpenChange} open={open}>
        <DialogContent className="cyber-dialog border-border flex max-h-[85vh] !w-[min(90vw,520px)] !max-w-none flex-col gap-0 rounded-lg border p-0">
          {/* Header */}
          <DialogHeader className="border-border bg-muted flex-shrink-0 border-b px-5 py-4">
            <DialogTitle className="text-foreground flex items-center gap-3 font-mono">
              <div className="bg-primary/20 border-primary/30 rounded border p-2">
                <Shield className="text-primary h-5 w-5" />
              </div>
              <div>
                <span className="text-base font-bold uppercase tracking-wider">
                  开始代码审计
                </span>
                <p className="text-muted-foreground mt-0.5 text-xs font-normal">
                  Code Security Analysis
                </p>
              </div>
            </DialogTitle>
          </DialogHeader>

          <div className="flex-1 space-y-5 overflow-y-auto p-5">
            {/* 项目选择 */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground font-mono text-sm font-bold uppercase">
                  选择项目
                </span>
                <Badge className="cyber-badge-muted font-mono text-xs">
                  {filteredProjects.length} 个
                </Badge>
              </div>

              {/* 搜索框 */}
              <div className="relative">
                <Search className="text-muted-foreground absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" />
                <Input
                  className="cyber-input h-10 !pl-9"
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="搜索项目..."
                  value={searchTerm}
                />
              </div>

              {/* 项目列表 */}
              <ScrollArea className="border-border bg-muted/50 h-[180px] rounded border">
                {projectListContent}
              </ScrollArea>
            </div>

            {/* 审计模式选择 */}
            {selectedProject && (
              <AgentModeSelector
                disabled={creating}
                onChange={setAuditMode}
                value={auditMode}
              />
            )}

            {/* 配置区域 */}
            {selectedProject && (
              <div className="space-y-4">
                <span className="text-muted-foreground font-mono text-sm font-bold uppercase">
                  配置
                </span>

                {isRepositoryProject(selectedProject) ? (
                  <div className="border-border space-y-3 rounded border bg-blue-50 p-3 dark:bg-blue-950/20">
                    <div className="flex items-center gap-3">
                      <GitBranch className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                      <span className="text-muted-foreground w-12 font-mono text-base">
                        模式
                      </span>
                      <Badge className="cyber-badge-info font-mono text-xs">
                        {getRepositoryTypeLabel(
                          selectedProject.repository_type,
                        )}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-3">
                      <GitBranch className="h-5 w-5 text-blue-600 opacity-0 dark:text-blue-400" />
                      <span className="text-muted-foreground w-12 font-mono text-base">
                        分支
                      </span>
                      {loadingBranches ? (
                        <div className="flex flex-1 items-center gap-2">
                          <Loader2 className="h-4 w-4 animate-spin text-blue-600 dark:text-blue-400" />
                          <span className="font-mono text-sm text-blue-600 dark:text-blue-400">
                            加载中...
                          </span>
                        </div>
                      ) : (
                        <BranchSelector
                          branches={branches}
                          className="flex-1"
                          onChange={setBranch}
                          placeholder="选择分支"
                          value={branch}
                        />
                      )}
                    </div>

                    {isMultiRepository(selectedProject) && (
                      <>
                        <div className="flex items-center gap-3">
                          <GitBranch className="h-5 w-5 text-blue-600 opacity-0 dark:text-blue-400" />
                          <span className="text-muted-foreground w-12 font-mono text-base">
                            清单
                          </span>
                          <Input
                            className="cyber-input h-10 flex-1"
                            onChange={(e) => setManifestXml(e.target.value)}
                            placeholder={
                              selectedProject.manifest_xml || 'default.xml'
                            }
                            value={manifestXml}
                          />
                        </div>
                        <div className="flex items-center gap-3">
                          <GitBranch className="h-5 w-5 text-blue-600 opacity-0 dark:text-blue-400" />
                          <span className="text-muted-foreground w-12 font-mono text-base">
                            组
                          </span>
                          <Input
                            className="cyber-input h-10 flex-1"
                            onChange={(e) => setGroup(e.target.value)}
                            placeholder={selectedProject.group || '可选'}
                            value={group}
                          />
                        </div>
                        <p className="font-mono text-xs text-blue-700 dark:text-blue-300/80">
                          多仓会执行 `git mm init -u ... -b ... -m ... [-g
                          ...]`，随后执行 `git mm sync`
                        </p>
                      </>
                    )}
                  </div>
                ) : (
                  <ZipUploadCard
                    onUpload={async () => {
                      if (!zipState.zipFile || !selectedProject) return;
                      setUploading(true);
                      try {
                        await api.uploadProjectZip(
                          selectedProject.id,
                          zipState.zipFile,
                        );
                        toast.success('文件上传成功');
                        zipState.switchToStored();
                        loadProjects();
                      } catch (error) {
                        const msg =
                          error instanceof Error ? error.message : '上传失败';
                        toast.error(msg);
                      } finally {
                        setUploading(false);
                      }
                    }}
                    uploading={uploading}
                    zipState={zipState}
                  />
                )}

                {/* 规则集和提示词选择 - 仅快速扫描模式显示 */}
                {auditMode !== 'agent' && (
                  <div className="border-border space-y-3 rounded border bg-violet-50 p-3 dark:bg-violet-950/20">
                    <div className="mb-2 flex items-center gap-2">
                      <Zap className="h-4 w-4 text-violet-600 dark:text-violet-400" />
                      <span className="font-mono text-sm font-bold uppercase text-violet-700 dark:text-violet-300">
                        审计配置
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-muted-foreground mb-1 block font-mono text-xs font-bold uppercase">
                          规则集
                        </label>
                        <Select
                          onValueChange={setSelectedRuleSetId}
                          value={selectedRuleSetId}
                        >
                          <SelectTrigger className="cyber-input h-9 text-xs">
                            <SelectValue placeholder="选择规则集" />
                          </SelectTrigger>
                          <SelectContent className="cyber-dialog border-border">
                            {ruleSets.map((rs) => (
                              <SelectItem
                                className="font-mono text-xs"
                                key={rs.id}
                                value={rs.id}
                              >
                                {rs.name} {rs.is_default && '(默认)'} (
                                {rs.enabled_rules_count})
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <label className="text-muted-foreground mb-1 block font-mono text-xs font-bold uppercase">
                          提示词模板
                        </label>
                        <Select
                          onValueChange={setSelectedPromptTemplateId}
                          value={selectedPromptTemplateId}
                        >
                          <SelectTrigger className="cyber-input h-9 text-xs">
                            <SelectValue placeholder="选择提示词模板" />
                          </SelectTrigger>
                          <SelectContent className="cyber-dialog border-border">
                            {promptTemplates.map((pt) => (
                              <SelectItem
                                className="font-mono text-xs"
                                key={pt.id}
                                value={pt.id}
                              >
                                {pt.name} {pt.is_default && '(默认)'}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>
                )}

                {/* 高级选项 */}
                <Collapsible onOpenChange={setShowAdvanced} open={showAdvanced}>
                  <CollapsibleTrigger className="text-muted-foreground hover:text-foreground flex items-center gap-2 font-mono text-xs transition-colors">
                    <ChevronRight
                      className={`h-4 w-4 transition-transform ${showAdvanced ? 'rotate-90' : ''}`}
                    />
                    <Settings2 className="h-4 w-4" />
                    <span className="font-bold uppercase">高级选项</span>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="mt-3 space-y-3">
                    {/* 排除模式 */}
                    <div className="border-border bg-muted/50 space-y-3 rounded border border-dashed p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground font-mono text-xs font-bold uppercase">
                          排除模式
                        </span>
                        <button
                          className="text-primary hover:text-primary/80 font-mono text-xs"
                          onClick={() => setExcludePatterns(DEFAULT_EXCLUDES)}
                          type="button"
                        >
                          重置为默认
                        </button>
                      </div>

                      <div className="flex flex-wrap gap-1.5">
                        {excludePatterns.map((p) => (
                          <Badge
                            className="bg-muted text-foreground cursor-pointer border-0 font-mono text-xs hover:bg-rose-100 hover:text-rose-600 dark:hover:bg-rose-900/50 dark:hover:text-rose-400"
                            key={p}
                            onClick={() =>
                              setExcludePatterns((prev) =>
                                prev.filter((x) => x !== p),
                              )
                            }
                          >
                            {p} ×
                          </Badge>
                        ))}
                        {excludePatterns.length === 0 && (
                          <span className="text-muted-foreground font-mono text-xs">
                            无排除模式
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap gap-1">
                        <span className="text-muted-foreground mr-1 font-mono text-xs">
                          快捷添加:
                        </span>
                        {[
                          '.test.',
                          '.spec.',
                          '.min.',
                          'coverage/',
                          'docs/',
                          '.md',
                        ].map((pattern) => (
                          <button
                            className="border-border bg-muted hover:bg-muted text-muted-foreground hover:text-foreground rounded border px-1.5 py-0.5 font-mono text-xs disabled:cursor-not-allowed disabled:opacity-40"
                            disabled={excludePatterns.includes(pattern)}
                            key={pattern}
                            onClick={() => {
                              if (!excludePatterns.includes(pattern)) {
                                setExcludePatterns((prev) => [
                                  ...prev,
                                  pattern,
                                ]);
                              }
                            }}
                            type="button"
                          >
                            +{pattern}
                          </button>
                        ))}
                      </div>

                      <Input
                        className="cyber-input h-8 text-sm"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && e.currentTarget.value) {
                            const val = e.currentTarget.value.trim();
                            if (val && !excludePatterns.includes(val)) {
                              setExcludePatterns((prev) => [...prev, val]);
                            }
                            e.currentTarget.value = '';
                          }
                        }}
                        placeholder="添加自定义排除模式，回车确认"
                      />
                    </div>

                    {/* 文件选择 */}
                    {(() => {
                      const isRepo = isRepositoryProject(selectedProject);
                      const isZip = isZipProject(selectedProject);
                      const hasStoredZip = zipState.storedZipInfo?.has_file;
                      const useStored = zipState.useStoredZip;
                      const canSelectFiles =
                        isRepo || (isZip && useStored && hasStoredZip);

                      return (
                        <div className="border-border bg-muted/50 flex items-center justify-between rounded border border-dashed p-3">
                          <div>
                            <p className="text-muted-foreground font-mono text-xs font-bold uppercase">
                              扫描范围
                            </p>
                            <p className="text-foreground mt-1 text-sm font-bold">
                              {selectedFiles
                                ? `已选 ${selectedFiles.length} 个文件`
                                : '全部文件'}
                            </p>
                          </div>
                          <div className="flex gap-2">
                            {selectedFiles && canSelectFiles && (
                              <Button
                                className="h-8 text-xs text-rose-600 hover:bg-rose-100 hover:text-rose-700 dark:text-rose-400 dark:hover:bg-rose-900/30 dark:hover:text-rose-300"
                                onClick={() => setSelectedFiles(undefined)}
                                size="sm"
                                variant="ghost"
                              >
                                重置
                              </Button>
                            )}
                            <Button
                              className="cyber-btn-outline h-8 font-mono text-xs font-bold disabled:opacity-50"
                              disabled={!canSelectFiles}
                              onClick={() => setShowFileSelection(true)}
                              size="sm"
                              variant="outline"
                            >
                              <FolderOpen className="mr-1 h-3 w-3" />
                              选择文件
                            </Button>
                          </div>
                        </div>
                      );
                    })()}
                  </CollapsibleContent>
                </Collapsible>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="bg-muted border-border flex flex-shrink-0 justify-end gap-3 border-t px-5 py-4">
            <Button
              className="text-muted-foreground hover:text-foreground hover:bg-muted h-10 px-4 font-mono"
              disabled={creating}
              onClick={() => onOpenChange(false)}
              variant="ghost"
            >
              取消
            </Button>
            <Button
              className="cyber-btn-primary h-10 px-5 font-mono font-bold uppercase"
              disabled={!canStart || creating || !canSubmitCurrentMode}
              onClick={handleStartScan}
            >
              {startButtonContent}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <FileSelectionDialog
        branch={branch}
        excludePatterns={excludePatterns}
        group={group}
        manifestXml={manifestXml}
        onConfirm={setSelectedFiles}
        onOpenChange={setShowFileSelection}
        open={showFileSelection}
        projectId={selectedProjectId}
        repositoryType={selectedProject?.repository_type}
      />
    </>
  );
}

function ProjectCard({
  project,
  selected,
  onSelect,
}: {
  onSelect: () => void;
  project: Project;
  selected: boolean;
}) {
  const isRepo = isRepositoryProject(project);

  return (
    <div
      className={`flex cursor-pointer items-center gap-3 rounded p-3 transition-all ${
        selected
          ? 'bg-primary/10 border-primary/50 border'
          : 'hover:bg-muted border border-transparent'
      }`}
      onClick={onSelect}
    >
      <Checkbox
        checked={selected}
        className="border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary"
      />

      <div
        className={`rounded p-1.5 ${isRepo ? 'bg-blue-500/20' : 'bg-amber-500/20'}`}
      >
        {isRepo ? (
          <Globe className="h-4 w-4 text-blue-600 dark:text-blue-400" />
        ) : (
          <Package className="h-4 w-4 text-amber-600 dark:text-amber-400" />
        )}
      </div>

      <div className="min-w-0 flex-1 overflow-hidden">
        <div className="flex items-center gap-2">
          <span
            className={`truncate font-mono text-base ${selected ? 'text-foreground font-bold' : 'text-foreground'}`}
          >
            {project.name}
          </span>
          <Badge
            className={`px-1 py-0 font-mono text-xs ${
              isRepo
                ? 'border-blue-500/30 bg-blue-500/20 text-blue-600 dark:text-blue-400'
                : 'border-amber-500/30 bg-amber-500/20 text-amber-600 dark:text-amber-400'
            }`}
          >
            {isRepo ? 'REPO' : 'ZIP'}
          </Badge>
          {isRepo && (
            <Badge className="cyber-badge-muted font-mono text-xs uppercase">
              {getRepositoryTypeLabel(project.repository_type)}
            </Badge>
          )}
        </div>
        {project.description && (
          <p
            className="text-muted-foreground mt-0.5 line-clamp-2 font-mono text-sm"
            title={project.description}
          >
            {project.description}
          </p>
        )}
      </div>
    </div>
  );
}

function ZipUploadCard({
  zipState,
  onUpload,
  uploading,
}: {
  onUpload: () => void;
  uploading: boolean;
  zipState: ReturnType<typeof useZipFile>;
}) {
  if (zipState.loading) {
    return (
      <div className="border-border flex items-center gap-3 rounded border bg-blue-50 p-3 dark:bg-blue-950/20">
        <Loader2 className="h-5 w-5 animate-spin text-blue-600 dark:text-blue-400" />
        <span className="font-mono text-sm text-blue-600 dark:text-blue-400">
          检查文件中...
        </span>
      </div>
    );
  }

  if (zipState.storedZipInfo?.has_file) {
    return (
      <div className="border-border space-y-3 rounded border bg-emerald-50 p-3 dark:bg-emerald-950/20">
        <div className="flex items-center gap-3">
          <div className="rounded bg-emerald-500/20 p-1.5">
            <Package className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div className="flex-1">
            <p className="font-mono text-sm font-bold text-emerald-700 dark:text-emerald-300">
              {zipState.storedZipInfo.original_filename}
            </p>
            <p className="font-mono text-xs text-emerald-600 dark:text-emerald-500">
              {zipState.storedZipInfo.file_size &&
                formatFileSize(zipState.storedZipInfo.file_size)}
              {zipState.storedZipInfo.uploaded_at &&
                ` · ${new Date(zipState.storedZipInfo.uploaded_at).toLocaleDateString('zh-CN')}`}
            </p>
          </div>
        </div>

        <div className="flex gap-4 border-t border-emerald-500/20 pt-2">
          <label className="flex cursor-pointer items-center gap-2 font-mono text-sm">
            <input
              checked={zipState.useStoredZip}
              className="h-4 w-4 accent-emerald-500"
              onChange={() => zipState.switchToStored()}
              type="radio"
            />
            <span className="text-emerald-700 dark:text-emerald-300">
              使用此文件
            </span>
          </label>
          <label className="flex cursor-pointer items-center gap-2 font-mono text-sm">
            <input
              checked={!zipState.useStoredZip}
              className="h-4 w-4 accent-emerald-500"
              onChange={() => zipState.switchToUpload()}
              type="radio"
            />
            <span className="text-emerald-700 dark:text-emerald-300">
              上传新文件
            </span>
          </label>
        </div>

        {!zipState.useStoredZip && (
          <div className="flex items-center gap-2">
            <Input
              accept=".zip"
              className="border-border bg-background file:bg-primary/20 file:text-primary hover:file:bg-primary/30 focus:ring-primary/50 h-9 flex-1 rounded border px-3 py-1.5 font-mono text-sm file:mr-3 file:rounded file:border-0 file:px-3 file:py-1 file:font-mono file:text-xs focus:outline-none focus:ring-1"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  const v = validateZipFile(file);
                  if (!v.valid) {
                    toast.error(v.error || '文件无效');
                    e.target.value = '';
                    return;
                  }
                  zipState.handleFileSelect(file, e.target);
                }
              }}
              type="file"
            />
            {zipState.zipFile && (
              <Button
                className="cyber-btn-primary h-9 px-3"
                disabled={uploading}
                onClick={onUpload}
                size="sm"
              >
                {uploading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4" />
                )}
              </Button>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="rounded border border-dashed border-amber-500/50 bg-amber-50 p-3 dark:bg-amber-950/20">
      <div className="flex items-start gap-3">
        <div className="rounded bg-amber-500/20 p-1.5">
          <Upload className="h-4 w-4 text-amber-600 dark:text-amber-400" />
        </div>
        <div className="flex-1">
          <p className="font-mono text-sm font-bold uppercase text-amber-700 dark:text-amber-300">
            上传 ZIP 文件
          </p>
          <div className="mt-2 flex items-center gap-2">
            <Input
              accept=".zip"
              className="border-border bg-background file:bg-primary/20 file:text-primary hover:file:bg-primary/30 focus:ring-primary/50 h-9 flex-1 rounded border px-3 py-1.5 font-mono text-sm file:mr-3 file:rounded file:border-0 file:px-3 file:py-1 file:font-mono file:text-xs focus:outline-none focus:ring-1"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  const v = validateZipFile(file);
                  if (!v.valid) {
                    toast.error(v.error || '文件无效');
                    e.target.value = '';
                    return;
                  }
                  zipState.handleFileSelect(file, e.target);
                }
              }}
              type="file"
            />
            {zipState.zipFile && (
              <Button
                className="cyber-btn-primary h-9 px-3"
                disabled={uploading}
                onClick={onUpload}
                size="sm"
              >
                {uploading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4" />
                )}
              </Button>
            )}
          </div>
          {zipState.zipFile && (
            <p className="mt-2 font-mono text-xs text-amber-600 dark:text-amber-400">
              已选: {zipState.zipFile.name} (
              {formatFileSize(zipState.zipFile.size)})
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
