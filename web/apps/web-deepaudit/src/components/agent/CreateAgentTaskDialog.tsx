/**
 * Agent 审计任务创建对话框
 * Cyberpunk Terminal Aesthetic
 */

import type { Project } from '@/shared/types';
import type { ZipFileMeta } from '@/shared/utils/zipStorage';

import FileSelectionDialog from '@/components/audit/FileSelectionDialog';
import { Badge } from '@/components/ui/badge';
import { BranchSelector } from '@/components/ui/branch-selector';
import { Button } from '@/components/ui/button';
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
import { validateZipFile } from '@/features/projects/services/repoZipScan';
import { createAgentTask } from '@/shared/api/agentTasks';
import { api } from '@/shared/config/database';
import { useAuth } from '@/shared/context/AuthContext';
import { DEEPAUDIT_ACTION_CODES } from '@/shared/focus/focusPermission';
import {
  getRepositoryTypeLabel,
  isCFamilyProject,
  isMultiRepository,
  isRepositoryProject,
  isZipProject,
} from '@/shared/utils/projectUtils';
import { getZipFileInfo } from '@/shared/utils/zipStorage';
import {
  Bot,
  ChevronRight,
  FolderOpen,
  GitBranch,
  Globe,
  Loader2,
  Package,
  Play,
  Search,
  Settings2,
  Upload,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

interface CreateAgentTaskDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface SelectedRepositorySpec {
  branch_name?: string;
  group?: string;
  manifest_xml?: string;
  repository_type?: string;
  repository_url?: string;
}

const DEFAULT_EXCLUDES = [
  'node_modules/**',
  '.git/**',
  'dist/**',
  'build/**',
  '*.log',
];
const C_FAMILY_VULNERABILITY_PRESET = [
  'buffer_overflow',
  'out_of_bounds',
  'integer_overflow',
  'null_dereference',
  'use_after_free',
  'double_free',
  'uninitialized_memory',
  'resource_leak',
  'race_condition',
  'deadlock',
  'format_string',
  'api_contract_violation',
] as const;

export default function CreateAgentTaskDialog({
  open,
  onOpenChange,
}: CreateAgentTaskDialogProps) {
  const navigate = useNavigate();
  const { hasAccess } = useAuth();
  const canCreateAgentTask = hasAccess(
    DEEPAUDIT_ACTION_CODES.AGENT_TASKS_CREATE,
  );

  // 状态
  const [projects, setProjects] = useState<Project[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [branch, setBranch] = useState('main');
  const [manifestXml, setManifestXml] = useState('');
  const [group, setGroup] = useState('');
  const [branches, setBranches] = useState<string[]>([]);
  const [loadingBranches, setLoadingBranches] = useState(false);
  const [excludePatterns, setExcludePatterns] = useState(DEFAULT_EXCLUDES);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [creating, setCreating] = useState(false);

  // ZIP 文件状态
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [storedZipInfo, setStoredZipInfo] = useState<null | ZipFileMeta>(null);
  const [useStoredZip, setUseStoredZip] = useState(true);

  // 文件选择状态
  const [selectedFiles, setSelectedFiles] = useState<string[] | undefined>();
  const [selectedRepositorySpec, setSelectedRepositorySpec] =
    useState<SelectedRepositorySpec>();
  const [showFileSelection, setShowFileSelection] = useState(false);
  const selectionContextRef = useRef('');

  const selectedProject = projects.find((p) => p.id === selectedProjectId);

  // 加载项目列表
  useEffect(() => {
    if (open) {
      setLoadingProjects(true);
      api
        .getProjects()
        .then((data) => {
          setProjects(data.filter((p: Project) => p.is_active));
        })
        .catch(() => {
          toast.error('加载项目列表失败');
        })
        .finally(() => setLoadingProjects(false));

      // 重置状态
      setSelectedProjectId('');
      setSearchTerm('');
      setBranch('main');
      setManifestXml('');
      setGroup('');
      setExcludePatterns(DEFAULT_EXCLUDES);
      setShowAdvanced(false);
      setZipFile(null);
      setStoredZipInfo(null);
      setSelectedFiles(undefined);
      setSelectedRepositorySpec(undefined);
    }
  }, [open]);

  // 加载分支列表
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

  useEffect(() => {
    const nextSelectionContext = [
      selectedProjectId,
      selectedProject?.repository_type || '',
      branch,
      manifestXml,
      group,
      excludePatterns.join('\u0001'),
    ].join('|');
    if (
      selectionContextRef.current &&
      selectionContextRef.current !== nextSelectionContext &&
      selectedFiles
    ) {
      setSelectedFiles(undefined);
      setSelectedRepositorySpec(undefined);
      toast.info('仓库规格或排除规则已更改，请重新选择文件');
    }
    selectionContextRef.current = nextSelectionContext;
  }, [
    branch,
    excludePatterns,
    group,
    manifestXml,
    selectedFiles,
    selectedProject?.repository_type,
    selectedProjectId,
  ]);

  // 加载 ZIP 文件信息
  useEffect(() => {
    const loadZipInfo = async () => {
      if (!selectedProject || !isZipProject(selectedProject)) {
        setStoredZipInfo(null);
        return;
      }

      try {
        const info = await getZipFileInfo(selectedProject.id);
        setStoredZipInfo(info);
        setUseStoredZip(info.has_file);
      } catch {
        setStoredZipInfo(null);
      }
    };

    loadZipInfo();
  }, [selectedProject?.id]);

  // 过滤项目
  const filteredProjects = useMemo(() => {
    if (!searchTerm) return projects;
    const term = searchTerm.toLowerCase();
    return projects.filter(
      (p) =>
        p.name.toLowerCase().includes(term) ||
        p.description?.toLowerCase().includes(term),
    );
  }, [projects, searchTerm]);

  // 是否可以开始
  const canStart = useMemo(() => {
    if (!selectedProject) return false;
    if (isZipProject(selectedProject)) {
      return (useStoredZip && storedZipInfo?.has_file) || !!zipFile;
    }
    if (isMultiRepository(selectedProject)) {
      return (
        !!selectedProject.repository_url &&
        !!branch.trim() &&
        !!manifestXml.trim()
      );
    }
    return !!selectedProject.repository_url && !!branch.trim();
  }, [
    selectedProject,
    useStoredZip,
    storedZipInfo,
    zipFile,
    branch,
    manifestXml,
  ]);

  // 创建任务
  const handleCreate = async () => {
    if (!selectedProject) return;
    if (!canCreateAgentTask) {
      toast.error('当前账号没有创建 Agent 审计任务的权限');
      return;
    }

    setCreating(true);
    try {
      const effectiveRepositorySpec = isRepositoryProject(selectedProject)
        ? {
            repository_type:
              selectedRepositorySpec?.repository_type ||
              selectedProject.repository_type,
            repository_url:
              selectedRepositorySpec?.repository_url ||
              selectedProject.repository_url,
            branch_name: selectedRepositorySpec?.branch_name || branch,
            manifest_xml:
              selectedRepositorySpec?.manifest_xml || manifestXml || undefined,
            group: selectedRepositorySpec?.group || group || undefined,
          }
        : undefined;
      const agentTask = await createAgentTask({
        project_id: selectedProject.id,
        name: `Agent审计-${selectedProject.name}`,
        repository_url: effectiveRepositorySpec?.repository_url,
        repository_type: effectiveRepositorySpec?.repository_type as any,
        branch_name: effectiveRepositorySpec?.branch_name,
        manifest_xml: effectiveRepositorySpec?.manifest_xml,
        group: effectiveRepositorySpec?.group,
        exclude_patterns: excludePatterns,
        target_files: selectedFiles,
        verification_level: 'sandbox',
        target_vulnerabilities: isCFamilyProject(selectedProject)
          ? [...C_FAMILY_VULNERABILITY_PRESET]
          : undefined,
      });

      onOpenChange(false);
      toast.success('Agent 审计任务已创建');
      navigate(`/agent-audit/${agentTask.id}`);
    } catch (error) {
      const msg = error instanceof Error ? error.message : '创建失败';
      toast.error(msg);
    } finally {
      setCreating(false);
    }
  };

  // 处理文件上传
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const validation = validateZipFile(file);
      if (!validation.valid) {
        toast.error(validation.error || '文件无效');
        e.target.value = '';
        return;
      }
      setZipFile(file);
      setUseStoredZip(false);
    }
  };

  const projectListContent = (() => {
    if (loadingProjects) {
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
          <span className="text-sm">
            {searchTerm ? 'No matches' : 'No projects'}
          </span>
        </div>
      );
    }

    return (
      <div className="p-1">
        {filteredProjects.map((project) => (
          <ProjectItem
            key={project.id}
            onSelect={() => setSelectedProjectId(project.id)}
            project={project}
            selected={selectedProjectId === project.id}
          />
        ))}
      </div>
    );
  })();

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="cyber-dialog border-border flex max-h-[85vh] !w-[min(90vw,520px)] !max-w-none flex-col gap-0 rounded-lg border p-0">
        {/* Header */}
        <DialogHeader className="border-border bg-muted flex-shrink-0 border-b px-5 py-4">
          <DialogTitle className="text-foreground flex items-center gap-3 font-mono">
            <div className="bg-primary/20 border-primary/30 rounded border p-2">
              <Bot className="text-primary h-5 w-5" />
            </div>
            <div>
              <span className="text-base font-bold uppercase tracking-wider">
                New Agent Audit
              </span>
              <p className="text-muted-foreground mt-0.5 text-xs font-normal">
                AI-Powered Security Analysis
              </p>
            </div>
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 space-y-5 overflow-y-auto p-5">
          {/* 项目选择 */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground font-mono text-xs font-bold uppercase">
                Select Project
              </span>
              <Badge className="cyber-badge-muted font-mono text-xs">
                {filteredProjects.length} available
              </Badge>
            </div>

            {/* 搜索框 */}
            <div className="relative">
              <Search className="text-muted-foreground absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" />
              <Input
                className="cyber-input h-10 !pl-9"
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search projects..."
                value={searchTerm}
              />
            </div>

            {/* 项目列表 */}
            <ScrollArea className="border-border bg-muted/50 h-[200px] rounded border">
              {projectListContent}
            </ScrollArea>
          </div>

          {/* 配置区域 */}
          {selectedProject && (
            <div className="space-y-4">
              {/* 仓库项目：分支选择 */}
              {isRepositoryProject(selectedProject) && (
                <div className="border-border space-y-3 rounded border bg-blue-950/20 p-3">
                  <div className="flex items-center gap-3">
                    <GitBranch className="h-5 w-5 text-blue-400" />
                    <span className="text-muted-foreground w-16 font-mono text-sm">
                      Mode
                    </span>
                    <Badge className="cyber-badge-info font-mono text-xs">
                      {getRepositoryTypeLabel(selectedProject.repository_type)}
                    </Badge>
                  </div>

                  <div className="flex items-center gap-3">
                    <GitBranch className="h-5 w-5 text-blue-400 opacity-0" />
                    <span className="text-muted-foreground w-16 font-mono text-sm">
                      Branch
                    </span>
                    {loadingBranches ? (
                      <div className="flex flex-1 items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
                        <span className="font-mono text-sm text-blue-400">
                          Loading...
                        </span>
                      </div>
                    ) : (
                      <BranchSelector
                        branches={branches}
                        className="flex-1"
                        onChange={setBranch}
                        placeholder="Select branch"
                        value={branch}
                      />
                    )}
                  </div>

                  {isMultiRepository(selectedProject) && (
                    <>
                      <div className="flex items-center gap-3">
                        <GitBranch className="h-5 w-5 text-blue-400 opacity-0" />
                        <span className="text-muted-foreground w-16 font-mono text-sm">
                          Manifest
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
                        <GitBranch className="h-5 w-5 text-blue-400 opacity-0" />
                        <span className="text-muted-foreground w-16 font-mono text-sm">
                          Group
                        </span>
                        <Input
                          className="cyber-input h-10 flex-1"
                          onChange={(e) => setGroup(e.target.value)}
                          placeholder={selectedProject.group || '可选'}
                          value={group}
                        />
                      </div>
                      <p className="font-mono text-xs text-blue-300/80">
                        多仓会按 `git mm init -u ... -b ... -m ... [-g
                        ...]`，然后执行 `git mm sync` 拉取代码
                      </p>
                    </>
                  )}
                </div>
              )}

              {/* ZIP 项目：文件选择 */}
              {isZipProject(selectedProject) && (
                <div className="border-border space-y-3 rounded border bg-amber-950/20 p-3">
                  <div className="flex items-center gap-3">
                    <Package className="h-5 w-5 text-amber-400" />
                    <span className="text-muted-foreground font-mono text-sm font-bold uppercase">
                      ZIP File
                    </span>
                  </div>

                  {storedZipInfo?.has_file && (
                    <div
                      className={`cursor-pointer rounded border p-2 transition-colors ${
                        useStoredZip
                          ? 'border-emerald-500/50 bg-emerald-950/30'
                          : 'border-border hover:border-border bg-muted/50'
                      }`}
                      onClick={() => setUseStoredZip(true)}
                    >
                      <div className="flex items-center gap-2">
                        <div
                          className={`h-3 w-3 rounded-full border-2 ${
                            useStoredZip
                              ? 'border-emerald-500 bg-emerald-500'
                              : 'border-border'
                          }`}
                        />
                        <span className="text-foreground font-mono text-sm">
                          {storedZipInfo.original_filename}
                        </span>
                        <Badge className="cyber-badge-success text-xs">
                          Stored
                        </Badge>
                      </div>
                    </div>
                  )}

                  <div
                    className={`cursor-pointer rounded border p-2 transition-colors ${
                      !useStoredZip && zipFile
                        ? 'border-amber-500/50 bg-amber-950/30'
                        : 'border-border hover:border-border bg-muted/50'
                    }`}
                  >
                    <label className="flex cursor-pointer items-center gap-2">
                      <div
                        className={`h-3 w-3 rounded-full border-2 ${
                          !useStoredZip && zipFile
                            ? 'border-amber-500 bg-amber-500'
                            : 'border-border'
                        }`}
                      />
                      <Upload className="text-muted-foreground h-4 w-4" />
                      <span className="text-muted-foreground font-mono text-sm">
                        {zipFile ? zipFile.name : 'Upload new file...'}
                      </span>
                      <input
                        accept=".zip"
                        className="hidden"
                        onChange={handleFileChange}
                        type="file"
                      />
                    </label>
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
                  <span className="font-bold uppercase">Advanced Options</span>
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-3 space-y-3">
                  {selectedProject && isCFamilyProject(selectedProject) && (
                    <div className="border-border bg-muted/50 flex items-start gap-2 rounded border border-dashed p-3">
                      <Badge className="cyber-badge-info">
                        嵌入式 C/C++ 深度审计
                      </Badge>
                      <p className="text-muted-foreground text-xs leading-5">
                        将自动附带内存、边界、并发和 API 契约类漏洞预设，并默认使用
                        `sandbox` 验证级别。
                      </p>
                    </div>
                  )}
                  {/* 文件选择 */}
                  {(() => {
                    const isRepo = isRepositoryProject(selectedProject);
                    const isZip = isZipProject(selectedProject);
                    const hasStoredZip = storedZipInfo?.has_file;
                    const canSelectFiles =
                      isRepo || (isZip && useStoredZip && hasStoredZip);

                    return (
                      <div className="border-border bg-muted/50 flex items-center justify-between rounded border border-dashed p-3">
                        <div>
                          <p className="text-muted-foreground font-mono text-xs font-bold uppercase">
                            Scan Scope
                          </p>
                          <p className="text-foreground mt-1 font-mono text-sm font-bold">
                            {selectedFiles
                              ? `${selectedFiles.length} files selected`
                              : 'All files'}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          {selectedFiles && canSelectFiles && (
                            <Button
                              className="h-8 text-xs text-rose-400 hover:bg-rose-900/30 hover:text-rose-300"
                              onClick={() => {
                                setSelectedFiles(undefined);
                                setSelectedRepositorySpec(undefined);
                              }}
                              size="sm"
                              variant="ghost"
                            >
                              Reset
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
                            Select Files
                          </Button>
                        </div>
                      </div>
                    );
                  })()}

                  {/* 排除模式 */}
                  <div className="border-border bg-muted/50 space-y-3 rounded border border-dashed p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground font-mono text-xs font-bold uppercase">
                        Exclude Patterns
                      </span>
                      <button
                        className="text-primary hover:text-primary/80 font-mono text-xs"
                        onClick={() => setExcludePatterns(DEFAULT_EXCLUDES)}
                        type="button"
                      >
                        Reset
                      </button>
                    </div>

                    <div className="flex flex-wrap gap-1.5">
                      {excludePatterns.map((p) => (
                        <Badge
                          className="bg-muted text-foreground cursor-pointer border-0 font-mono text-xs hover:bg-rose-900/50 hover:text-rose-400"
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
                      placeholder="Add pattern, press Enter..."
                    />
                  </div>
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
            Cancel
          </Button>
          <Button
            className="cyber-btn-primary h-10 px-5 font-mono font-bold uppercase"
            disabled={!canStart || creating || !canCreateAgentTask}
            onClick={handleCreate}
          >
            {creating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Start Audit
              </>
            )}
          </Button>
        </div>
      </DialogContent>

      {/* 文件选择对话框 */}
      <FileSelectionDialog
        branch={branch}
        excludePatterns={excludePatterns}
        group={group}
        manifestXml={manifestXml}
        onConfirm={({ repositorySpec, selectedFiles: files }) => {
          setSelectedFiles(files);
          setSelectedRepositorySpec(repositorySpec);
        }}
        onOpenChange={setShowFileSelection}
        open={showFileSelection}
        projectId={selectedProjectId}
        repositoryType={selectedProject?.repository_type}
      />
    </Dialog>
  );
}

// 项目列表项
function ProjectItem({
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
      <div
        className={`rounded p-1.5 ${isRepo ? 'bg-blue-500/20' : 'bg-amber-500/20'}`}
      >
        {isRepo ? (
          <Globe className="h-4 w-4 text-blue-400" />
        ) : (
          <Package className="h-4 w-4 text-amber-400" />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span
            className={`truncate font-mono text-sm ${selected ? 'text-foreground font-bold' : 'text-foreground'}`}
          >
            {project.name}
          </span>
          <Badge
            className={`px-1 py-0 font-mono text-xs ${
              isRepo
                ? 'border-blue-500/30 bg-blue-500/20 text-blue-400'
                : 'border-amber-500/30 bg-amber-500/20 text-amber-400'
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
          <p className="text-muted-foreground mt-0.5 truncate font-mono text-xs">
            {project.description}
          </p>
        )}
      </div>

      {selected && (
        <div className="bg-primary h-2 w-2 animate-pulse rounded-full shadow-[0_0_8px_rgba(255,107,44,0.6)]" />
      )}
    </div>
  );
}
