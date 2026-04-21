/**
 * Projects Page
 * Cyberpunk Terminal Aesthetic
 */

import type { CreateProjectForm, Project } from '@/shared/types';
import type { ZipFileMeta } from '@/shared/utils/zipStorage';

import CreateTaskDialog from '@/components/audit/CreateTaskDialog';
import TerminalProgressDialog from '@/components/audit/TerminalProgressDialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { validateZipFile } from '@/features/projects/services';
import { api } from '@/shared/config/database';
import { REPOSITORY_PLATFORMS, SUPPORTED_LANGUAGES } from '@/shared/constants';
import { useAuth } from '@/shared/context/AuthContext';
import { DEEPAUDIT_ACTION_CODES } from '@/shared/focus/focusPermission';
import {
  getRepositoryTypeLabel,
  getSourceTypeBadge,
  isMultiRepository,
  isRepositoryProject,
  isZipProject,
  normalizeRepositoryType,
} from '@/shared/utils/projectUtils';
import { getZipFileInfo, uploadZipFile } from '@/shared/utils/zipStorage';
import {
  Activity,
  AlertCircle,
  ArrowUpRight,
  Calendar,
  CheckCircle,
  Code,
  Edit,
  FileText,
  Folder,
  GitBranch,
  Key,
  Plus,
  Search,
  Shield,
  Terminal,
  Trash2,
  Upload,
  Users,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';

export default function Projects() {
  const { hasAccess } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showCreateTaskDialog, setShowCreateTaskDialog] = useState(false);
  const [selectedProjectForTask, setSelectedProjectForTask] =
    useState<string>('');
  const [showTerminal, setShowTerminal] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState<null | string>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<null | Project>(null);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [projectToEdit, setProjectToEdit] = useState<null | Project>(null);
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
  const [createForm, setCreateForm] = useState<CreateProjectForm>({
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

  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // 编辑对话框中的ZIP文件状态
  const [editZipInfo, setEditZipInfo] = useState<null | ZipFileMeta>(null);
  const [editZipFile, setEditZipFile] = useState<File | null>(null);
  const [loadingEditZipInfo, setLoadingEditZipInfo] = useState(false);
  const editZipInputRef = useRef<HTMLInputElement>(null);
  const canCreateProject = hasAccess(DEEPAUDIT_ACTION_CODES.PROJECTS_CREATE);
  const canUpdateProject = hasAccess(DEEPAUDIT_ACTION_CODES.PROJECTS_UPDATE);
  const canDeleteProject = hasAccess(DEEPAUDIT_ACTION_CODES.PROJECTS_DELETE);
  const canCreateFastTask = hasAccess(DEEPAUDIT_ACTION_CODES.TASKS_CREATE);
  const canCreateAgentTask = hasAccess(
    DEEPAUDIT_ACTION_CODES.AGENT_TASKS_CREATE,
  );
  const canCreateAnyTask = canCreateFastTask || canCreateAgentTask;

  // 将小写语言名转换为显示格式
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

  const editZipInfoContent = (() => {
    if (loadingEditZipInfo) {
      return (
        <div className="flex items-center space-x-3 rounded border border-sky-500/30 bg-sky-500/10 p-4">
          <div className="loading-spinner h-5 w-5"></div>
          <p className="font-mono text-sm font-bold text-sky-400">
            正在加载ZIP文件信息...
          </p>
        </div>
      );
    }

    if (editZipInfo?.has_file) {
      return (
        <div className="rounded border border-emerald-500/30 bg-emerald-500/10 p-4">
          <div className="flex items-start space-x-3">
            <FileText className="mt-0.5 h-5 w-5 text-emerald-400" />
            <div className="flex-1 font-mono text-sm">
              <p className="mb-1 font-bold uppercase text-emerald-300">
                当前存储的ZIP文件
              </p>
              <p className="text-xs text-emerald-400/80">
                文件名: {editZipInfo.original_filename}
                {editZipInfo.file_size && (
                  <>
                    {' '}
                    (
                    {editZipInfo.file_size >= 1024 * 1024
                      ? `${(editZipInfo.file_size / 1024 / 1024).toFixed(2)} MB`
                      : `${(editZipInfo.file_size / 1024).toFixed(2)} KB`}
                    )
                  </>
                )}
              </p>
              {editZipInfo.uploaded_at && (
                <p className="mt-0.5 text-xs text-emerald-500/60">
                  上传时间:{' '}
                  {new Date(editZipInfo.uploaded_at).toLocaleString('zh-CN')}
                </p>
              )}
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="rounded border border-amber-500/30 bg-amber-500/10 p-4">
        <div className="flex items-start space-x-3">
          <AlertCircle className="mt-0.5 h-5 w-5 text-amber-400" />
          <div className="font-mono text-sm">
            <p className="mb-1 font-bold uppercase text-amber-300">
              暂无ZIP文件
            </p>
            <p className="text-xs text-amber-400/80">
              此项目还没有上传ZIP文件，请上传文件以便进行代码审计。
            </p>
          </div>
        </div>
      </div>
    );
  })();

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      setLoading(true);
      const data = await api.getProjects();
      setProjects(data);
    } catch (error) {
      console.error('Failed to load projects:', error);
      toast.error('加载项目失败');
    } finally {
      setLoading(false);
    }
  };

  const handleFastScanStarted = (taskId: string) => {
    setCurrentTaskId(taskId);
    setShowTerminal(true);
  };

  const handleCreateProject = async () => {
    if (!canCreateProject) {
      toast.error('当前账号没有创建项目的权限');
      return;
    }
    if (!createForm.name.trim()) {
      toast.error('请输入项目名称');
      return;
    }
    if (createForm.source_type === 'repository') {
      if (!createForm.repository_url?.trim()) {
        toast.error('请输入仓库地址');
        return;
      }
      if (
        normalizeRepositoryType(createForm.repository_type) === 'multi' &&
        !createForm.manifest_xml?.trim()
      ) {
        toast.error('多仓项目必须填写 Manifest XML');
        return;
      }
    }

    try {
      await api.createProject({
        ...createForm,
      } as any);

      import('@/shared/utils/logger').then(({ logger }) => {
        logger.logUserAction('创建项目', {
          projectName: createForm.name,
          repositoryType: createForm.repository_type,
          languages: createForm.programming_languages,
        });
      });

      toast.success('项目创建成功');
      setShowCreateDialog(false);
      resetCreateForm();
      loadProjects();
    } catch (error) {
      console.error('Failed to create project:', error);
      import('@/shared/utils/errorHandler').then(({ handleError }) => {
        handleError(error, '创建项目失败');
      });
      const errorMessage = error instanceof Error ? error.message : '未知错误';
      toast.error(`创建项目失败: ${errorMessage}`);
    }
  };

  const resetCreateForm = () => {
    setCreateForm({
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
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const validation = validateZipFile(file);
    if (!validation.valid) {
      toast.error(validation.error);
      return;
    }

    setSelectedFile(file);
    event.target.value = '';
  };

  const handleUploadAndCreate = async () => {
    if (!canCreateProject) {
      toast.error('当前账号没有创建项目的权限');
      return;
    }
    if (!selectedFile) {
      toast.error('请先选择ZIP文件');
      return;
    }

    if (!createForm.name.trim()) {
      toast.error('请先输入项目名称');
      return;
    }

    try {
      setUploading(true);
      setUploadProgress(0);

      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 100) {
            clearInterval(progressInterval);
            return 100;
          }
          return prev + 20;
        });
      }, 100);

      const project = await api.createProject({
        ...createForm,
        source_type: 'zip',
        repository_type: 'single',
        repository_url: undefined,
      } as any);

      try {
        await uploadZipFile(project.id, selectedFile);
      } catch (error) {
        console.error('保存ZIP文件失败:', error);
      }

      clearInterval(progressInterval);
      setUploadProgress(100);

      import('@/shared/utils/logger').then(({ logger }) => {
        logger.logUserAction('上传ZIP文件创建项目', {
          projectName: project.name,
          fileName: selectedFile.name,
          fileSize: selectedFile.size,
        });
      });

      setShowCreateDialog(false);
      resetCreateForm();
      loadProjects();

      toast.success(`项目 "${project.name}" 已创建`, {
        description: 'ZIP文件已保存，您可以启动代码审计',
        duration: 4000,
      });
    } catch (error: any) {
      console.error('Upload failed:', error);
      import('@/shared/utils/errorHandler').then(({ handleError }) => {
        handleError(error, '上传ZIP文件失败');
      });
      const errorMessage = error?.message || '未知错误';
      toast.error(`上传失败: ${errorMessage}`);
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const filteredProjects = projects.filter(
    (project) =>
      project.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      project.description?.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  const getRepositoryIcon = (type?: string) => {
    switch (type) {
      case 'multi': {
        return <Key className="h-5 w-5 text-violet-500" />;
      }
      case 'single': {
        return <GitBranch className="h-5 w-5 text-sky-500" />;
      }
      default: {
        return <Folder className="text-muted-foreground h-5 w-5" />;
      }
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN');
  };

  const handleCreateTask = (projectId: string) => {
    if (!canCreateAnyTask) {
      toast.error('当前账号没有创建审计任务的权限');
      return;
    }
    setSelectedProjectForTask(projectId);
    setShowCreateTaskDialog(true);
  };

  const handleEditClick = async (project: Project) => {
    setProjectToEdit(project);
    setEditForm({
      name: project.name,
      description: project.description || '',
      source_type: project.source_type || 'repository',
      repository_url: project.repository_url || '',
      repository_type: normalizeRepositoryType(project.repository_type),
      default_branch: project.default_branch || 'main',
      manifest_xml: project.manifest_xml || '',
      group: project.group || '',
      programming_languages: project.programming_languages
        ? JSON.parse(project.programming_languages)
        : [],
    });
    setEditZipFile(null);
    setEditZipInfo(null);
    setShowEditDialog(true);

    if (project.source_type === 'zip') {
      setLoadingEditZipInfo(true);
      try {
        const zipInfo = await getZipFileInfo(project.id);
        setEditZipInfo(zipInfo);
      } catch (error) {
        console.error('加载ZIP文件信息失败:', error);
      } finally {
        setLoadingEditZipInfo(false);
      }
    }
  };

  const handleSaveEdit = async () => {
    if (!canUpdateProject) {
      toast.error('当前账号没有编辑项目的权限');
      return;
    }
    if (!projectToEdit) return;

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
      await api.updateProject(projectToEdit.id, editForm);

      if (editZipFile && editForm.source_type === 'zip') {
        const result = await uploadZipFile(projectToEdit.id, editZipFile);
        if (result.success) {
          toast.success(`ZIP文件已更新: ${result.original_filename}`);
        } else {
          toast.error(`ZIP文件上传失败: ${result.message}`);
        }
      }

      toast.success(`项目 "${editForm.name}" 已更新`);
      setShowEditDialog(false);
      setProjectToEdit(null);
      setEditZipFile(null);
      setEditZipInfo(null);
      loadProjects();
    } catch (error) {
      console.error('Failed to update project:', error);
      toast.error('更新项目失败');
    }
  };

  const handleToggleLanguage = (lang: string) => {
    const currentLanguages = editForm.programming_languages || [];
    const newLanguages = currentLanguages.includes(lang)
      ? currentLanguages.filter((l) => l !== lang)
      : [...currentLanguages, lang];

    setEditForm({ ...editForm, programming_languages: newLanguages });
  };

  const handleDeleteClick = (project: Project) => {
    if (!canDeleteProject) {
      toast.error('当前账号没有删除项目的权限');
      return;
    }
    setProjectToDelete(project);
    setShowDeleteDialog(true);
  };

  const handleConfirmDelete = async () => {
    if (!canDeleteProject) {
      toast.error('当前账号没有删除项目的权限');
      return;
    }
    if (!projectToDelete) return;

    try {
      await api.deleteProject(projectToDelete.id);

      import('@/shared/utils/logger').then(({ logger }) => {
        logger.logUserAction('删除项目', {
          projectId: projectToDelete.id,
          projectName: projectToDelete.name,
        });
      });

      toast.success(`项目 "${projectToDelete.name}" 已移到回收站`, {
        description: '您可以在回收站中恢复此项目',
        duration: 4000,
      });
      setShowDeleteDialog(false);
      setProjectToDelete(null);
      loadProjects();
    } catch (error) {
      console.error('Failed to delete project:', error);
      import('@/shared/utils/errorHandler').then(({ handleError }) => {
        handleError(error, '删除项目失败');
      });
      const errorMessage = error instanceof Error ? error.message : '未知错误';
      toast.error(`删除项目失败: ${errorMessage}`);
    }
  };

  const handleTaskCreated = () => {
    toast.success('审计任务已创建', {
      description:
        '因为网络和代码文件大小等因素，审计时长通常至少需要1分钟，请耐心等待...',
      duration: 5000,
    });
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

  return (
    <div className="bg-background relative min-h-screen space-y-6 p-6 font-mono">
      {/* Grid background */}
      <div className="cyber-grid-subtle pointer-events-none absolute inset-0" />

      {/* 创建项目对话框 */}
      <Dialog onOpenChange={setShowCreateDialog} open={showCreateDialog}>
        <DialogTrigger asChild className="hidden">
          <Button className="cyber-btn-primary">
            <Plus className="mr-2 h-5 w-5" />
            初始化项目
          </Button>
        </DialogTrigger>
        <DialogContent className="cyber-dialog border-border flex max-h-[85vh] !w-[min(90vw,700px)] !max-w-none flex-col gap-0 rounded-lg border p-0">
          {/* Terminal Header */}
          <div className="cyber-bg-elevated border-border flex flex-shrink-0 items-center gap-2 border-b px-4 py-3">
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded-full bg-red-500/80" />
              <div className="h-3 w-3 rounded-full bg-yellow-500/80" />
              <div className="h-3 w-3 rounded-full bg-green-500/80" />
            </div>
            <span className="text-muted-foreground ml-2 font-mono text-xs tracking-wider">
              new_project@focusaudit
            </span>
          </div>

          <DialogHeader className="flex-shrink-0 px-6 pt-4">
            <DialogTitle className="text-foreground flex items-center gap-2 font-mono text-lg uppercase tracking-wider">
              <Terminal className="text-primary h-5 w-5" />
              初始化新项目
            </DialogTitle>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto p-6">
            <Tabs className="w-full" defaultValue="repository">
              <TabsList className="bg-muted border-border flex h-auto w-full gap-1 rounded border p-1">
                <TabsTrigger
                  className="data-[state=active]:bg-primary data-[state=active]:text-foreground text-muted-foreground flex-1 rounded-sm py-2 font-mono font-bold uppercase transition-all"
                  value="repository"
                >
                  <GitBranch className="mr-2 h-4 w-4" />
                  Git 仓库
                </TabsTrigger>
                <TabsTrigger
                  className="data-[state=active]:bg-primary data-[state=active]:text-foreground text-muted-foreground flex-1 rounded-sm py-2 font-mono font-bold uppercase transition-all"
                  value="upload"
                >
                  <Upload className="mr-2 h-4 w-4" />
                  上传源码
                </TabsTrigger>
              </TabsList>

              <TabsContent
                className="mt-5 flex flex-col gap-5"
                value="repository"
              >
                <div className="grid grid-cols-2 gap-5">
                  <div className="space-y-1.5">
                    <Label
                      className="text-muted-foreground font-mono text-xs font-bold uppercase"
                      htmlFor="name"
                    >
                      项目名称 *
                    </Label>
                    <Input
                      className="cyber-input"
                      id="name"
                      onChange={(e) =>
                        setCreateForm({ ...createForm, name: e.target.value })
                      }
                      placeholder="输入项目名称"
                      value={createForm.name}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label
                      className="text-muted-foreground font-mono text-xs font-bold uppercase"
                      htmlFor="repository_type"
                    >
                      认证类型
                    </Label>
                    <Select
                      onValueChange={(value: any) =>
                        setCreateForm({ ...createForm, repository_type: value })
                      }
                      value={createForm.repository_type}
                    >
                      <SelectTrigger className="cyber-input">
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
                </div>

                <div className="space-y-1.5">
                  <Label
                    className="text-muted-foreground font-mono text-xs font-bold uppercase"
                    htmlFor="description"
                  >
                    描述
                  </Label>
                  <Textarea
                    className="cyber-input min-h-[80px]"
                    id="description"
                    onChange={(e) =>
                      setCreateForm({
                        ...createForm,
                        description: e.target.value,
                      })
                    }
                    placeholder="// 项目描述..."
                    rows={3}
                    value={createForm.description}
                  />
                </div>

                <div className="grid grid-cols-2 gap-5">
                  <div className="space-y-1.5">
                    <Label
                      className="text-muted-foreground font-mono text-xs font-bold uppercase"
                      htmlFor="repository_url"
                    >
                      仓库地址
                    </Label>
                    <Input
                      className="cyber-input"
                      id="repository_url"
                      onChange={(e) =>
                        setCreateForm({
                          ...createForm,
                          repository_url: e.target.value,
                        })
                      }
                      placeholder="https://codehub.example.com/team/repo.git 或 git@codehub.example.com:team/repo.git"
                      value={createForm.repository_url}
                    />
                    <p className="text-muted-foreground font-mono text-xs">
                      💡 单仓直接 clone；多仓会按 `git mm init` + `git mm sync`
                      拉取
                    </p>
                  </div>
                  <div className="space-y-1.5">
                    <Label
                      className="text-muted-foreground font-mono text-xs font-bold uppercase"
                      htmlFor="default_branch"
                    >
                      默认分支
                    </Label>
                    <Input
                      className="cyber-input"
                      id="default_branch"
                      onChange={(e) =>
                        setCreateForm({
                          ...createForm,
                          default_branch: e.target.value,
                        })
                      }
                      placeholder="main"
                      value={createForm.default_branch}
                    />
                  </div>
                </div>

                {createForm.repository_type === 'multi' && (
                  <div className="grid grid-cols-2 gap-5">
                    <div className="space-y-1.5">
                      <Label
                        className="text-muted-foreground font-mono text-xs font-bold uppercase"
                        htmlFor="manifest_xml"
                      >
                        Manifest XML *
                      </Label>
                      <Input
                        className="cyber-input"
                        id="manifest_xml"
                        onChange={(e) =>
                          setCreateForm({
                            ...createForm,
                            manifest_xml: e.target.value,
                          })
                        }
                        placeholder="default.xml"
                        value={createForm.manifest_xml || ''}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label
                        className="text-muted-foreground font-mono text-xs font-bold uppercase"
                        htmlFor="group"
                      >
                        Group
                      </Label>
                      <Input
                        className="cyber-input"
                        id="group"
                        onChange={(e) =>
                          setCreateForm({
                            ...createForm,
                            group: e.target.value,
                          })
                        }
                        placeholder="可选"
                        value={createForm.group || ''}
                      />
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <Label className="text-muted-foreground font-mono text-xs font-bold uppercase">
                    技术栈
                  </Label>
                  <div className="flex flex-wrap gap-2">
                    {supportedLanguages.map((lang) => (
                      <label
                        className={`flex cursor-pointer items-center space-x-2 rounded border px-3 py-1.5 transition-all ${
                          createForm.programming_languages.includes(lang)
                            ? 'border-primary bg-primary/10 text-primary'
                            : 'border-border hover:border-border text-muted-foreground'
                        }`}
                        key={lang}
                      >
                        <input
                          checked={createForm.programming_languages.includes(
                            lang,
                          )}
                          className="border-border text-primary h-3.5 w-3.5 rounded border bg-transparent focus:ring-0"
                          onChange={(e) => {
                            if (e.target.checked) {
                              setCreateForm({
                                ...createForm,
                                programming_languages: [
                                  ...createForm.programming_languages,
                                  lang,
                                ],
                              });
                            } else {
                              setCreateForm({
                                ...createForm,
                                programming_languages:
                                  createForm.programming_languages.filter(
                                    (l) => l !== lang,
                                  ),
                              });
                            }
                          }}
                          type="checkbox"
                        />
                        <span className="font-mono text-xs font-bold uppercase">
                          {lang}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="border-border flex justify-end space-x-4 border-t pt-4">
                  <Button
                    className="cyber-btn-outline"
                    onClick={() => setShowCreateDialog(false)}
                    variant="outline"
                  >
                    取消
                  </Button>
                  <Button
                    className="cyber-btn-primary"
                    disabled={!canCreateProject}
                    onClick={handleCreateProject}
                  >
                    执行创建
                  </Button>
                </div>
              </TabsContent>

              <TabsContent className="mt-5 flex flex-col gap-5" value="upload">
                <div className="space-y-1.5">
                  <Label
                    className="text-muted-foreground font-mono text-xs font-bold uppercase"
                    htmlFor="upload-name"
                  >
                    项目名称 *
                  </Label>
                  <Input
                    className="cyber-input"
                    id="upload-name"
                    onChange={(e) =>
                      setCreateForm({ ...createForm, name: e.target.value })
                    }
                    placeholder="输入项目名称"
                    value={createForm.name}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label
                    className="text-muted-foreground font-mono text-xs font-bold uppercase"
                    htmlFor="upload-description"
                  >
                    描述
                  </Label>
                  <Textarea
                    className="cyber-input min-h-[80px]"
                    id="upload-description"
                    onChange={(e) =>
                      setCreateForm({
                        ...createForm,
                        description: e.target.value,
                      })
                    }
                    placeholder="// 项目描述..."
                    rows={3}
                    value={createForm.description}
                  />
                </div>

                <div className="space-y-2">
                  <Label className="text-muted-foreground font-mono text-xs font-bold uppercase">
                    技术栈
                  </Label>
                  <div className="flex flex-wrap gap-2">
                    {supportedLanguages.map((lang) => (
                      <label
                        className={`flex cursor-pointer items-center space-x-2 rounded border px-3 py-1.5 transition-all ${
                          createForm.programming_languages.includes(lang)
                            ? 'border-primary bg-primary/10 text-primary'
                            : 'border-border hover:border-border text-muted-foreground'
                        }`}
                        key={lang}
                      >
                        <input
                          checked={createForm.programming_languages.includes(
                            lang,
                          )}
                          className="border-border text-primary h-3.5 w-3.5 rounded border bg-transparent focus:ring-0"
                          onChange={(e) => {
                            if (e.target.checked) {
                              setCreateForm({
                                ...createForm,
                                programming_languages: [
                                  ...createForm.programming_languages,
                                  lang,
                                ],
                              });
                            } else {
                              setCreateForm({
                                ...createForm,
                                programming_languages:
                                  createForm.programming_languages.filter(
                                    (l) => l !== lang,
                                  ),
                              });
                            }
                          }}
                          type="checkbox"
                        />
                        <span className="font-mono text-xs font-bold uppercase">
                          {lang}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="space-y-4">
                  <Label className="text-muted-foreground font-mono text-xs font-bold uppercase">
                    源代码
                  </Label>

                  {selectedFile ? (
                    <div className="border-border bg-muted/50 flex items-center justify-between rounded border p-4">
                      <div className="flex items-center space-x-3 overflow-hidden">
                        <div className="bg-muted border-border flex h-10 w-10 flex-shrink-0 items-center justify-center rounded border">
                          <FileText className="text-primary h-5 w-5" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-foreground truncate font-mono text-sm font-bold">
                            {selectedFile.name}
                          </p>
                          <p className="text-muted-foreground font-mono text-xs">
                            {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                          </p>
                        </div>
                      </div>
                      <Button
                        className="hover:bg-rose-500/10 hover:text-rose-400"
                        disabled={uploading}
                        onClick={() => setSelectedFile(null)}
                        size="icon"
                        variant="ghost"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ) : (
                    <div
                      className="border-border bg-muted/50 hover:bg-muted hover:border-border group cursor-pointer rounded border border-dashed p-6 text-center transition-colors"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <Upload className="text-muted-foreground group-hover:text-primary mx-auto mb-3 h-10 w-10 transition-colors" />
                      <h3 className="text-foreground mb-1 text-base font-bold uppercase">
                        上传 ZIP 归档
                      </h3>
                      <p className="text-muted-foreground mb-3 font-mono text-xs">
                        最大: 500MB // 格式: .ZIP
                      </p>
                      <input
                        accept=".zip"
                        className="hidden"
                        disabled={uploading}
                        onChange={handleFileSelect}
                        ref={fileInputRef}
                        type="file"
                      />
                      <Button
                        className="cyber-btn-outline h-8 text-xs"
                        disabled={uploading || !createForm.name.trim()}
                        onClick={(e) => {
                          e.stopPropagation();
                          fileInputRef.current?.click();
                        }}
                        type="button"
                        variant="outline"
                      >
                        <FileText className="mr-2 h-3 w-3" />
                        选择文件
                      </Button>
                    </div>
                  )}

                  {uploading && (
                    <div className="space-y-1.5">
                      <div className="text-muted-foreground flex items-center justify-between font-mono text-xs">
                        <span>上传并分析中...</span>
                        <span className="text-primary">{uploadProgress}%</span>
                      </div>
                      <Progress
                        className="bg-muted [&>div]:bg-primary h-2"
                        value={uploadProgress}
                      />
                    </div>
                  )}

                  <div className="rounded border border-amber-500/30 bg-amber-500/10 p-3">
                    <div className="flex items-start space-x-3">
                      <AlertCircle className="mt-0.5 h-4 w-4 text-amber-400" />
                      <div className="font-mono text-xs text-amber-300">
                        <p className="mb-1 font-bold uppercase">上传协议:</p>
                        <ul className="list-inside list-disc space-y-0.5 text-amber-400/80">
                          <li>确保完整的项目代码</li>
                          <li>移除 node_modules 等依赖目录</li>
                          <li>包含必要的配置文件</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="border-border mt-auto flex justify-end space-x-4 border-t pt-4">
                  <Button
                    className="cyber-btn-outline"
                    disabled={uploading}
                    onClick={() => setShowCreateDialog(false)}
                    variant="outline"
                  >
                    取消
                  </Button>
                  <Button
                    className="cyber-btn-primary"
                    disabled={!selectedFile || uploading || !canCreateProject}
                    onClick={handleUploadAndCreate}
                  >
                    {uploading ? '上传中...' : '执行创建'}
                  </Button>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </DialogContent>
      </Dialog>

      {/* Stats Section */}
      {projects.length > 0 && (
        <div className="relative z-10 grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="cyber-card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="stat-label">项目总数</p>
                <p className="stat-value">{projects.length}</p>
              </div>
              <div className="stat-icon text-primary">
                <Code className="h-6 w-6" />
              </div>
            </div>
          </div>

          <div className="cyber-card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="stat-label">活跃项目</p>
                <p className="stat-value">
                  {projects.filter((p) => p.is_active).length}
                </p>
              </div>
              <div className="stat-icon text-emerald-400">
                <Activity className="h-6 w-6" />
              </div>
            </div>
          </div>

          <div className="cyber-card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="stat-label">远程仓库</p>
                <p className="stat-value">
                  {projects.filter((p) => isRepositoryProject(p)).length}
                </p>
              </div>
              <div className="stat-icon text-sky-400">
                <GitBranch className="h-6 w-6" />
              </div>
            </div>
          </div>

          <div className="cyber-card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="stat-label">ZIP上传</p>
                <p className="stat-value">
                  {projects.filter((p) => isZipProject(p)).length}
                </p>
              </div>
              <div className="stat-icon text-amber-400">
                <Upload className="h-6 w-6" />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Search and Filter */}
      <div className="cyber-card relative z-10 flex items-center gap-4 p-4">
        <div className="relative flex-1">
          <Search className="text-muted-foreground absolute left-3 top-1/2 z-10 h-4 w-4 -translate-y-1/2 transform" />
          <Input
            className="cyber-input !pl-10"
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="搜索项目..."
            value={searchTerm}
          />
        </div>
        {canCreateProject && (
          <Button
            className="cyber-btn-primary h-10"
            onClick={() => setShowCreateDialog(true)}
          >
            <Plus className="mr-2 h-4 w-4" />
            新建项目
          </Button>
        )}
      </div>

      {/* Project List */}
      <div className="relative z-10 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredProjects.length > 0 ? (
          filteredProjects.map((project) => (
            <div
              className="cyber-card group flex h-full flex-col"
              key={project.id}
            >
              {/* Card Header */}
              <div className="border-border bg-muted/50 flex items-start justify-between border-b p-4">
                <div className="flex items-center space-x-3">
                  <div className="border-border bg-muted text-muted-foreground flex h-10 w-10 items-center justify-center rounded border">
                    {getRepositoryIcon(project.repository_type)}
                  </div>
                  <div>
                    <h3 className="text-foreground group-hover:text-primary text-base font-bold transition-colors">
                      <Link to={`/projects/${project.id}`}>{project.name}</Link>
                    </h3>
                    <div className="mt-1 flex items-center space-x-2">
                      <Badge
                        className={`cyber-badge ${project.is_active ? 'cyber-badge-success' : 'cyber-badge-muted'}`}
                      >
                        {project.is_active ? '活跃' : '暂停'}
                      </Badge>
                      <Badge
                        className={`cyber-badge ${isRepositoryProject(project) ? 'cyber-badge-info' : 'cyber-badge-warning'}`}
                      >
                        {getSourceTypeBadge(project.source_type)}
                      </Badge>
                      {isRepositoryProject(project) && (
                        <Badge className="cyber-badge cyber-badge-muted">
                          {getRepositoryTypeLabel(project.repository_type)}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Card Body */}
              <div className="flex-1 space-y-3 p-4">
                {project.description && (
                  <p className="text-muted-foreground border-border line-clamp-2 border-l-2 pl-2 font-mono text-sm">
                    {project.description}
                  </p>
                )}

                <div className="space-y-2">
                  {project.repository_url && (
                    <div className="text-muted-foreground bg-muted border-border flex items-center rounded border p-2 font-mono text-xs">
                      <GitBranch className="text-muted-foreground mr-2 h-3 w-3 flex-shrink-0" />
                      <a
                        className="hover:text-primary truncate transition-colors"
                        href={project.repository_url}
                        rel="noopener noreferrer"
                        target="_blank"
                      >
                        {project.repository_url.replace('https://', '')}
                      </a>
                    </div>
                  )}

                  <div className="text-muted-foreground flex items-center justify-between font-mono text-xs">
                    <span className="flex items-center">
                      <Calendar className="mr-1 h-3 w-3" />{' '}
                      {formatDate(project.created_at)}
                    </span>
                    <span className="flex items-center">
                      <Users className="mr-1 h-3 w-3" />{' '}
                      {project.owner?.full_name || '未知'}
                    </span>
                  </div>
                  {isRepositoryProject(project) &&
                    isMultiRepository(project) && (
                      <div className="text-muted-foreground space-y-1 font-mono text-xs">
                        <div>Manifest: {project.manifest_xml || '未设置'}</div>
                        <div>Group: {project.group || '未设置'}</div>
                      </div>
                    )}
                </div>

                {project.programming_languages && (
                  <div className="flex flex-wrap gap-1">
                    {JSON.parse(project.programming_languages)
                      .slice(0, 4)
                      .map((lang: string) => (
                        <span
                          className="border-primary/30 bg-primary/10 text-primary rounded border px-1.5 py-0.5 font-mono text-xs font-bold"
                          key={lang}
                        >
                          {lang.toUpperCase()}
                        </span>
                      ))}
                    {JSON.parse(project.programming_languages).length > 4 && (
                      <span className="border-border bg-muted text-muted-foreground rounded border px-1.5 py-0.5 font-mono text-xs font-bold">
                        +{JSON.parse(project.programming_languages).length - 4}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Card Footer */}
              <div className="border-border bg-muted/50 grid grid-cols-2 gap-2 border-t p-4">
                <Link className="col-span-2" to={`/projects/${project.id}`}>
                  <Button
                    className="cyber-btn-outline h-8 w-full text-xs"
                    variant="outline"
                  >
                    <Code className="mr-2 h-3 w-3" />
                    查看详情
                    <ArrowUpRight className="ml-auto h-3 w-3" />
                  </Button>
                </Link>
                {canCreateAnyTask && (
                  <Button
                    className="cyber-btn-primary h-8 text-xs"
                    onClick={() => handleCreateTask(project.id)}
                    size="sm"
                  >
                    <Shield className="mr-2 h-3 w-3" />
                    审计
                  </Button>
                )}
                {(canUpdateProject || canDeleteProject) && (
                  <div className="grid grid-cols-2 gap-2">
                    {canUpdateProject && (
                      <Button
                        className="cyber-btn-ghost h-8 px-0"
                        onClick={() => handleEditClick(project)}
                        size="sm"
                        variant="outline"
                      >
                        <Edit className="h-3 w-3" />
                      </Button>
                    )}
                    {canDeleteProject && (
                      <Button
                        className="cyber-btn-ghost h-8 px-0 hover:border-rose-500/30 hover:bg-rose-500/10 hover:text-rose-400"
                        onClick={() => handleDeleteClick(project)}
                        size="sm"
                        variant="outline"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        ) : (
          <div className="col-span-full">
            <div className="cyber-card border-dashed p-16 text-center">
              <Code className="text-muted-foreground mx-auto mb-4 h-16 w-16" />
              <h3 className="text-foreground mb-2 text-xl font-bold">
                {searchTerm ? '未找到匹配项' : '未初始化项目'}
              </h3>
              <p className="text-muted-foreground mb-6 font-mono">
                {searchTerm ? '调整搜索参数' : '初始化第一个项目以开始'}
              </p>
              {!searchTerm && canCreateProject && (
                <Button
                  className="cyber-btn-primary"
                  onClick={() => setShowCreateDialog(true)}
                >
                  <Plus className="mr-2 h-4 w-4" />
                  初始化项目
                </Button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Create Task Dialog */}
      <CreateTaskDialog
        onFastScanStarted={handleFastScanStarted}
        onOpenChange={setShowCreateTaskDialog}
        onTaskCreated={handleTaskCreated}
        open={showCreateTaskDialog}
        preselectedProjectId={selectedProjectForTask}
      />

      {/* Terminal Progress Dialog for Fast Scan */}
      <TerminalProgressDialog
        onOpenChange={setShowTerminal}
        open={showTerminal}
        taskId={currentTaskId}
        taskType="repository"
      />

      {/* Edit Dialog */}
      <Dialog onOpenChange={setShowEditDialog} open={showEditDialog}>
        <DialogContent className="cyber-dialog border-border flex max-h-[85vh] !w-[min(90vw,700px)] !max-w-none flex-col gap-0 rounded-lg border p-0">
          {/* Terminal Header */}
          <div className="cyber-bg-elevated border-border flex flex-shrink-0 items-center gap-2 border-b px-4 py-3">
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded-full bg-red-500/80" />
              <div className="h-3 w-3 rounded-full bg-yellow-500/80" />
              <div className="h-3 w-3 rounded-full bg-green-500/80" />
            </div>
            <span className="text-muted-foreground ml-2 font-mono text-xs tracking-wider">
              edit_project@focusaudit
            </span>
          </div>

          <DialogHeader className="flex-shrink-0 px-6 pt-4">
            <DialogTitle className="text-foreground flex items-center gap-2 font-mono text-lg uppercase tracking-wider">
              <Edit className="text-primary h-5 w-5" />
              编辑项目配置
              {projectToEdit && (
                <Badge
                  className={`ml-2 ${editForm.source_type === 'repository' ? 'cyber-badge-info' : 'cyber-badge-warning'}`}
                >
                  {editForm.source_type === 'repository'
                    ? '远程仓库'
                    : 'ZIP上传'}
                </Badge>
              )}
            </DialogTitle>
          </DialogHeader>

          <div className="flex-1 space-y-6 overflow-y-auto p-6">
            {/* 基本信息 */}
            <div className="space-y-4">
              <h3 className="text-muted-foreground border-border border-b pb-2 font-mono text-sm font-bold uppercase">
                基本信息
              </h3>
              <div>
                <Label
                  className="text-muted-foreground font-mono text-xs font-bold uppercase"
                  htmlFor="edit-name"
                >
                  项目名称 *
                </Label>
                <Input
                  className="cyber-input mt-1"
                  id="edit-name"
                  onChange={(e) =>
                    setEditForm({ ...editForm, name: e.target.value })
                  }
                  value={editForm.name}
                />
              </div>
              <div>
                <Label
                  className="text-muted-foreground font-mono text-xs font-bold uppercase"
                  htmlFor="edit-description"
                >
                  描述
                </Label>
                <Textarea
                  className="cyber-input mt-1"
                  id="edit-description"
                  onChange={(e) =>
                    setEditForm({ ...editForm, description: e.target.value })
                  }
                  rows={3}
                  value={editForm.description}
                />
              </div>
            </div>

            {/* 仓库信息 - 仅远程仓库类型显示 */}
            {editForm.source_type === 'repository' && (
              <div className="space-y-4">
                <h3 className="text-muted-foreground border-border flex items-center gap-2 border-b pb-2 font-mono text-sm font-bold uppercase">
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
                    id="edit-repo-url"
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        repository_url: e.target.value,
                      })
                    }
                    placeholder="https://codehub.example.com/team/repo.git 或 git@codehub.example.com:team/repo.git"
                    value={editForm.repository_url}
                  />
                  <p className="text-muted-foreground mt-1 font-mono text-xs">
                    💡 单仓直接 clone；多仓会按 `git mm init` + `git mm sync`
                    拉取
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label
                      className="text-muted-foreground font-mono text-xs font-bold uppercase"
                      htmlFor="edit-repo-type"
                    >
                      认证类型
                    </Label>
                    <Select
                      onValueChange={(value: any) =>
                        setEditForm({ ...editForm, repository_type: value })
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
                      htmlFor="edit-default-branch"
                    >
                      默认分支
                    </Label>
                    <Input
                      className="cyber-input mt-1"
                      id="edit-default-branch"
                      onChange={(e) =>
                        setEditForm({
                          ...editForm,
                          default_branch: e.target.value,
                        })
                      }
                      placeholder="main"
                      value={editForm.default_branch}
                    />
                  </div>
                </div>

                {editForm.repository_type === 'multi' && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label
                        className="text-muted-foreground font-mono text-xs font-bold uppercase"
                        htmlFor="edit-manifest-xml"
                      >
                        Manifest XML *
                      </Label>
                      <Input
                        className="cyber-input mt-1"
                        id="edit-manifest-xml"
                        onChange={(e) =>
                          setEditForm({
                            ...editForm,
                            manifest_xml: e.target.value,
                          })
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
                        id="edit-group"
                        onChange={(e) =>
                          setEditForm({ ...editForm, group: e.target.value })
                        }
                        placeholder="可选"
                        value={editForm.group || ''}
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ZIP项目文件管理 */}
            {editForm.source_type === 'zip' && (
              <div className="space-y-4">
                <h3 className="text-muted-foreground border-border flex items-center gap-2 border-b pb-2 font-mono text-sm font-bold uppercase">
                  <Upload className="h-4 w-4" />
                  ZIP文件管理
                </h3>

                {editZipInfoContent}

                {/* 上传新文件 */}
                <div className="space-y-2">
                  <Label className="text-muted-foreground font-mono text-xs font-bold uppercase">
                    {editZipInfo?.has_file ? '更新ZIP文件' : '上传ZIP文件'}
                  </Label>
                  <input
                    accept=".zip"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        const validation = validateZipFile(file);
                        if (!validation.valid) {
                          toast.error(validation.error || '文件无效');
                          e.target.value = '';
                          return;
                        }
                        setEditZipFile(file);
                        toast.success(`已选择文件: ${file.name}`);
                      }
                    }}
                    ref={editZipInputRef}
                    type="file"
                  />

                  {editZipFile ? (
                    <div className="flex items-center justify-between rounded border border-sky-500/30 bg-sky-500/10 p-3">
                      <div className="flex items-center space-x-2">
                        <FileText className="h-4 w-4 text-sky-400" />
                        <span className="font-mono text-sm font-bold text-sky-300">
                          {editZipFile.name}
                        </span>
                        <span className="text-muted-foreground text-xs">
                          ({(editZipFile.size / 1024 / 1024).toFixed(2)} MB)
                        </span>
                      </div>
                      <Button
                        className="cyber-btn-ghost h-7 text-xs"
                        onClick={() => setEditZipFile(null)}
                        size="sm"
                        variant="outline"
                      >
                        取消
                      </Button>
                    </div>
                  ) : (
                    <Button
                      className="cyber-btn-outline w-full"
                      onClick={() => editZipInputRef.current?.click()}
                      variant="outline"
                    >
                      <Upload className="mr-2 h-4 w-4" />
                      {editZipInfo?.has_file ? '选择新文件替换' : '选择ZIP文件'}
                    </Button>
                  )}
                </div>
              </div>
            )}

            {/* 技术栈 */}
            <div className="space-y-4">
              <h3 className="text-muted-foreground border-border border-b pb-2 font-mono text-sm font-bold uppercase">
                技术栈
              </h3>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {supportedLanguages.map((lang) => (
                  <div
                    className={`flex cursor-pointer items-center space-x-2 rounded border p-2 transition-all ${
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
                    <span className="font-mono text-sm font-bold uppercase">
                      {lang}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="bg-muted border-border flex flex-shrink-0 justify-end gap-3 border-t px-6 py-4">
            <Button
              className="cyber-btn-outline"
              onClick={() => setShowEditDialog(false)}
              variant="outline"
            >
              取消
            </Button>
            <Button
              className="cyber-btn-primary"
              disabled={!canUpdateProject}
              onClick={handleSaveEdit}
            >
              保存更改
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <AlertDialog onOpenChange={setShowDeleteDialog} open={showDeleteDialog}>
        <AlertDialogContent className="cyber-card border-border cyber-dialog !fixed p-0">
          {/* Terminal Header */}
          <div className="flex items-center gap-2 border-b border-rose-500/30 bg-rose-500/10 px-4 py-3">
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded-full bg-red-500/80" />
              <div className="h-3 w-3 rounded-full bg-yellow-500/80" />
              <div className="h-3 w-3 rounded-full bg-green-500/80" />
            </div>
            <span className="ml-2 font-mono text-xs tracking-wider text-rose-400">
              confirm_delete@focusaudit
            </span>
          </div>

          <AlertDialogHeader className="p-6">
            <AlertDialogTitle className="text-foreground flex items-center gap-2 font-mono text-lg uppercase tracking-wider">
              <Trash2 className="h-5 w-5 text-rose-400" />
              确认删除
            </AlertDialogTitle>
            <AlertDialogDescription className="text-muted-foreground font-mono">
              您确定要移动{' '}
              <span className="font-bold text-rose-400">
                "{projectToDelete?.name}"
              </span>{' '}
              到回收站吗？
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="px-6 pb-6">
            <div className="rounded border border-sky-500/30 bg-sky-500/10 p-4">
              <p className="mb-2 font-mono text-sm font-bold uppercase text-sky-300">
                系统通知:
              </p>
              <ul className="list-none space-y-1 font-mono text-xs text-sky-400/80">
                <li className="flex items-center gap-2">
                  <span className="text-sky-400">&gt;</span> 项目移至回收站
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-sky-400">&gt;</span> 可恢复
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-sky-400">&gt;</span> 审计数据保留
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-sky-400">&gt;</span> 在回收站中永久删除
                </li>
              </ul>
            </div>
          </div>

          <AlertDialogFooter className="border-border bg-muted/50 border-t p-4">
            <AlertDialogCancel className="cyber-btn-outline">
              取消
            </AlertDialogCancel>
            <AlertDialogAction
              className="cyber-btn text-foreground border-rose-500/50 bg-rose-500/90 hover:bg-rose-500"
              disabled={!canDeleteProject}
              onClick={handleConfirmDelete}
            >
              确认删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
