/**
 * Recycle Bin Page
 * Cyberpunk Terminal Aesthetic
 */

import type { Project } from '@/shared/types';

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
import { Input } from '@/components/ui/input';
import { api } from '@/shared/config/database';
import { useAuth } from '@/shared/context/AuthContext';
import { DEEPAUDIT_ACTION_CODES } from '@/shared/focus/focusPermission';
import {
  getRepositoryTypeLabel,
  getSourceTypeBadge,
  isRepositoryProject,
} from '@/shared/utils/projectUtils';
import {
  AlertTriangle,
  Calendar,
  ExternalLink,
  GitBranch,
  Inbox,
  RotateCcw,
  Search,
  Trash2,
  Users,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

export default function RecycleBin() {
  const { hasAccess } = useAuth();
  const [deletedProjects, setDeletedProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showRestoreDialog, setShowRestoreDialog] = useState(false);
  const [showPermanentDeleteDialog, setShowPermanentDeleteDialog] =
    useState(false);
  const [selectedProject, setSelectedProject] = useState<null | Project>(null);
  const canRestoreProject = hasAccess(DEEPAUDIT_ACTION_CODES.PROJECTS_RESTORE);
  const canDeleteProject = hasAccess(DEEPAUDIT_ACTION_CODES.PROJECTS_DELETE);

  useEffect(() => {
    loadDeletedProjects();
  }, []);

  const loadDeletedProjects = async () => {
    try {
      setLoading(true);
      const data = await api.getDeletedProjects();
      setDeletedProjects(data);
    } catch (error) {
      console.error('Failed to load deleted projects:', error);
      toast.error('加载已删除项目失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRestoreClick = (project: Project) => {
    if (!canRestoreProject) {
      toast.error('当前账号没有恢复项目的权限');
      return;
    }
    setSelectedProject(project);
    setShowRestoreDialog(true);
  };

  const handlePermanentDeleteClick = (project: Project) => {
    if (!canDeleteProject) {
      toast.error('当前账号没有永久删除项目的权限');
      return;
    }
    setSelectedProject(project);
    setShowPermanentDeleteDialog(true);
  };

  const handleConfirmRestore = async () => {
    if (!selectedProject) return;
    if (!canRestoreProject) {
      toast.error('当前账号没有恢复项目的权限');
      return;
    }

    try {
      await api.restoreProject(selectedProject.id);
      toast.success(`项目 "${selectedProject.name}" 已恢复`);
      setShowRestoreDialog(false);
      setSelectedProject(null);
      loadDeletedProjects();
    } catch (error) {
      console.error('Failed to restore project:', error);
      toast.error('恢复项目失败');
    }
  };

  const handleConfirmPermanentDelete = async () => {
    if (!selectedProject) return;
    if (!canDeleteProject) {
      toast.error('当前账号没有永久删除项目的权限');
      return;
    }

    try {
      await api.permanentlyDeleteProject(selectedProject.id);

      toast.success(`项目 "${selectedProject.name}" 已永久删除`);
      setShowPermanentDeleteDialog(false);
      setSelectedProject(null);
      loadDeletedProjects();
    } catch (error) {
      console.error('Failed to permanently delete project:', error);
      toast.error('永久删除项目失败');
    }
  };

  const filteredProjects = deletedProjects.filter(
    (project) =>
      project.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      project.description?.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  const getRepositoryIcon = (type?: string) => {
    switch (type) {
      case 'multi': {
        return '🗂️';
      }
      case 'single': {
        return '🧬';
      }
      default: {
        return '📁';
      }
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN');
  };

  if (loading) {
    return (
      <div className="cyber-bg-elevated flex min-h-screen items-center justify-center">
        <div className="space-y-4 text-center">
          <div className="loading-spinner mx-auto" />
          <p className="text-muted-foreground font-mono text-sm uppercase tracking-wider">
            加载中...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="cyber-bg-elevated relative min-h-screen space-y-6 p-6">
      {/* Grid background */}
      <div className="cyber-grid-subtle pointer-events-none absolute inset-0" />

      {/* Search Bar */}
      <div className="cyber-card relative z-10 p-0">
        <div className="cyber-card-header">
          <Trash2 className="h-5 w-5 text-rose-400" />
          <h3 className="text-foreground text-lg font-bold uppercase tracking-wider">
            回收站
          </h3>
          <Badge className="cyber-badge-muted ml-2">
            {deletedProjects.length} 个项目
          </Badge>
        </div>
        <div className="p-4">
          <div className="relative">
            <Search className="text-muted-foreground absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform" />
            <Input
              className="cyber-input h-10 !pl-10"
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="搜索已删除的项目..."
              value={searchTerm}
            />
          </div>
        </div>
      </div>

      {/* Projects Grid */}
      <div className="relative z-10 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredProjects.length > 0 ? (
          filteredProjects.map((project) => (
            <div
              className="cyber-card hover:border-border group p-0 transition-all"
              key={project.id}
            >
              {/* Project Header */}
              <div className="border-border bg-muted/50 border-b p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="bg-muted border-border flex h-10 w-10 items-center justify-center rounded border text-lg">
                      {getRepositoryIcon(project.repository_type)}
                    </div>
                    <div>
                      <h3 className="text-foreground group-hover:text-primary max-w-[150px] truncate text-base font-bold uppercase transition-colors">
                        {project.name}
                      </h3>
                      {project.description && (
                        <p className="text-muted-foreground mt-1 line-clamp-1 text-xs">
                          {project.description}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <Badge className="cyber-badge-danger">已删除</Badge>
                    <Badge
                      className={`${isRepositoryProject(project) ? 'cyber-badge-info' : 'cyber-badge-warning'}`}
                    >
                      {getSourceTypeBadge(project.source_type)}
                    </Badge>
                    {isRepositoryProject(project) && (
                      <Badge className="cyber-badge-muted">
                        {getRepositoryTypeLabel(project.repository_type)}
                      </Badge>
                    )}
                  </div>
                </div>
              </div>

              <div className="space-y-4 p-4">
                {/* Project Info */}
                <div className="space-y-3">
                  {isRepositoryProject(project) && project.repository_url && (
                    <div className="text-muted-foreground flex items-center text-xs">
                      <GitBranch className="text-muted-foreground mr-2 h-4 w-4 flex-shrink-0" />
                      <a
                        className="hover:text-primary flex items-center truncate transition-colors"
                        href={project.repository_url}
                        rel="noopener noreferrer"
                        target="_blank"
                      >
                        <span className="truncate">
                          {project.repository_url.replace('https://', '')}
                        </span>
                        <ExternalLink className="ml-1 h-3 w-3 flex-shrink-0" />
                      </a>
                    </div>
                  )}

                  <div className="text-muted-foreground flex items-center justify-between text-xs">
                    <div className="flex items-center">
                      <Calendar className="text-muted-foreground mr-2 h-4 w-4" />
                      删除于 {formatDate(project.updated_at)}
                    </div>
                    <div className="flex items-center">
                      <Users className="text-muted-foreground mr-2 h-4 w-4" />
                      {project.owner?.full_name || '未知'}
                    </div>
                  </div>
                </div>

                {/* Programming Languages */}
                {project.programming_languages && (
                  <div className="flex flex-wrap gap-2">
                    {JSON.parse(project.programming_languages)
                      .slice(0, 4)
                      .map((lang: string) => (
                        <Badge className="cyber-badge-muted text-xs" key={lang}>
                          {lang}
                        </Badge>
                      ))}
                    {JSON.parse(project.programming_languages).length > 4 && (
                      <Badge className="cyber-badge-muted text-xs">
                        +{JSON.parse(project.programming_languages).length - 4}
                      </Badge>
                    )}
                  </div>
                )}

                {/* Action Buttons */}
                {canRestoreProject || canDeleteProject ? (
                  <div className="border-border flex gap-2 border-t pt-3">
                    {canRestoreProject && (
                      <Button
                        className="cyber-btn-outline h-9 flex-1 border-emerald-500/30 text-emerald-400 hover:border-emerald-500/50 hover:bg-emerald-500/10"
                        onClick={() => handleRestoreClick(project)}
                        size="sm"
                        variant="outline"
                      >
                        <RotateCcw className="mr-2 h-4 w-4" />
                        恢复
                      </Button>
                    )}
                    {canDeleteProject && (
                      <Button
                        className="cyber-btn-outline h-9 flex-1 border-rose-500/30 text-rose-400 hover:border-rose-500/50 hover:bg-rose-500/10"
                        onClick={() => handlePermanentDeleteClick(project)}
                        size="sm"
                        variant="outline"
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        永久删除
                      </Button>
                    )}
                  </div>
                ) : (
                  <div className="border-border text-muted-foreground border-t pt-3 text-xs">
                    当前账号无可执行操作
                  </div>
                )}
              </div>
            </div>
          ))
        ) : (
          <div className="cyber-card col-span-full p-16">
            <div className="empty-state">
              <Inbox className="empty-state-icon" />
              <p className="empty-state-title">
                {searchTerm ? '未找到匹配的项目' : '回收站为空'}
              </p>
              <p className="empty-state-description">
                {searchTerm ? '尝试调整搜索条件' : '回收站中没有已删除的项目'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Restore Dialog */}
      <AlertDialog onOpenChange={setShowRestoreDialog} open={showRestoreDialog}>
        <AlertDialogContent className="cyber-card cyber-dialog !fixed max-w-md p-0">
          <AlertDialogHeader className="cyber-card-header">
            <RotateCcw className="h-5 w-5 text-emerald-400" />
            <AlertDialogTitle className="text-foreground text-lg font-bold uppercase tracking-wider">
              确认恢复项目
            </AlertDialogTitle>
          </AlertDialogHeader>
          <AlertDialogDescription className="text-muted-foreground p-6">
            您确定要恢复项目{' '}
            <span className="text-foreground font-bold">
              "{selectedProject?.name}"
            </span>{' '}
            吗？
            <br />
            <br />
            恢复后，该项目将重新出现在项目列表中，您可以继续使用该项目的所有功能。
          </AlertDialogDescription>
          <AlertDialogFooter className="border-border flex gap-3 border-t p-4">
            <AlertDialogCancel className="cyber-btn-outline">
              取消
            </AlertDialogCancel>
            <AlertDialogAction
              className="cyber-btn-primary border-emerald-500 bg-emerald-600 hover:bg-emerald-500"
              onClick={handleConfirmRestore}
            >
              确认恢复
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Permanent Delete Dialog */}
      <AlertDialog
        onOpenChange={setShowPermanentDeleteDialog}
        open={showPermanentDeleteDialog}
      >
        <AlertDialogContent className="cyber-card cyber-dialog !fixed max-w-md p-0">
          <AlertDialogHeader className="flex flex-row items-center gap-2 border-b border-rose-500/30 bg-rose-500/10 p-4">
            <AlertTriangle className="h-5 w-5 text-rose-400" />
            <AlertDialogTitle className="text-lg font-bold uppercase tracking-wider text-rose-400">
              警告：永久删除项目
            </AlertDialogTitle>
          </AlertDialogHeader>
          <AlertDialogDescription className="text-muted-foreground p-6">
            您确定要
            <span className="font-bold uppercase text-rose-400">永久删除</span>
            项目{' '}
            <span className="text-foreground font-bold">
              "{selectedProject?.name}"
            </span>{' '}
            吗？
            <br />
            <br />
            <div className="rounded border border-rose-500/30 bg-rose-500/10 p-4">
              <p className="mb-2 flex items-center font-bold uppercase text-rose-400">
                <AlertTriangle className="mr-2 h-4 w-4" />
                此操作不可撤销！
              </p>
              <ul className="list-inside list-disc space-y-1 text-xs text-rose-300/80">
                <li>项目数据将被永久删除</li>
                <li>相关的审计任务可能会受影响</li>
                <li>无法通过任何方式恢复</li>
              </ul>
            </div>
          </AlertDialogDescription>
          <AlertDialogFooter className="border-border flex gap-3 border-t p-4">
            <AlertDialogCancel className="cyber-btn-outline">
              取消
            </AlertDialogCancel>
            <AlertDialogAction
              className="cyber-btn-primary border-rose-500 bg-rose-600 hover:bg-rose-500"
              onClick={handleConfirmPermanentDelete}
            >
              确认永久删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
