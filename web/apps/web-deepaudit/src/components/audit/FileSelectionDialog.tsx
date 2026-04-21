/**
 * File Selection Dialog
 * Cyberpunk Terminal Aesthetic
 */

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { api } from '@/shared/config/database';
import { getRepositoryTypeLabel } from '@/shared/utils/projectUtils';
import {
  CheckSquare,
  ChevronDown,
  ChevronRight,
  File,
  FileCode,
  FileJson,
  FileText,
  Filter,
  Folder,
  FolderOpen,
  RefreshCw,
  RotateCcw,
  Search,
  Square,
  Terminal,
} from 'lucide-react';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

interface FileSelectionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  branch?: string;
  manifestXml?: string;
  group?: string;
  repositoryType?: string;
  excludePatterns?: string[];
  onConfirm: (selectedFiles: string[]) => void;
}

interface FileNode {
  path: string;
  size: number;
}

interface FolderNode {
  name: string;
  path: string;
  files: FileNode[];
  subfolders: Map<string, FolderNode>;
  expanded: boolean;
}

// 文件类型图标映射
const getFileIcon = (path: string) => {
  const ext = path.split('.').pop()?.toLowerCase() || '';
  const codeExts = [
    'js',
    'ts',
    'tsx',
    'jsx',
    'py',
    'java',
    'go',
    'rs',
    'cpp',
    'c',
    'h',
    'cs',
    'php',
    'rb',
    'swift',
    'kt',
    'sh',
  ];
  const configExts = ['json', 'yml', 'yaml', 'toml', 'xml', 'ini'];

  if (codeExts.includes(ext)) {
    return <FileCode className="h-4 w-4 text-sky-400" />;
  }
  if (configExts.includes(ext)) {
    return <FileJson className="h-4 w-4 text-amber-400" />;
  }
  return <File className="text-muted-foreground h-4 w-4" />;
};

// 获取文件扩展名
const getExtension = (path: string): string => {
  const ext = path.split('.').pop()?.toLowerCase() || '';
  return ext;
};

// 构建文件夹树结构
const buildFolderTree = (files: FileNode[]): FolderNode => {
  const root: FolderNode = {
    name: '',
    path: '',
    files: [],
    subfolders: new Map(),
    expanded: true,
  };

  files.forEach((file) => {
    const parts = file.path.split('/');
    let current = root;

    // 遍历路径的每个部分（除了文件名）
    for (let i = 0; i < parts.length - 1; i++) {
      const folderName = parts[i];
      const folderPath = parts.slice(0, i + 1).join('/');

      if (!current.subfolders.has(folderName)) {
        current.subfolders.set(folderName, {
          name: folderName,
          path: folderPath,
          files: [],
          subfolders: new Map(),
          expanded: true,
        });
      }
      const nextFolder = current.subfolders.get(folderName);
      if (!nextFolder) {
        return;
      }
      current = nextFolder;
    }

    // 添加文件到当前文件夹
    current.files.push(file);
  });

  return root;
};

export default function FileSelectionDialog({
  open,
  onOpenChange,
  projectId,
  branch,
  manifestXml,
  group,
  repositoryType,
  excludePatterns,
  onConfirm,
}: FileSelectionDialogProps) {
  const [files, setFiles] = useState<FileNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(
    new Set(),
  );
  const [viewMode, setViewMode] = useState<'flat' | 'tree'>('tree');
  const [filterType, setFilterType] = useState<string>('');

  useEffect(() => {
    if (open && projectId) {
      loadFiles();
    } else {
      setFiles([]);
      setSelectedFiles(new Set());
      setSearchTerm('');
      setExpandedFolders(new Set());
      setFilterType('');
    }
  }, [open, projectId, branch, excludePatterns]);

  const loadFiles = async () => {
    try {
      setLoading(true);
      const data = await api.getProjectFiles(projectId, {
        branch_name: branch,
        manifest_xml: manifestXml,
        group,
        exclude_patterns: excludePatterns,
      });
      setFiles(data);
      setSelectedFiles(new Set(data.map((f) => f.path)));
      // 默认展开所有文件夹
      const folders = new Set<string>();
      data.forEach((f) => {
        const parts = f.path.split('/');
        for (let i = 1; i < parts.length; i++) {
          folders.add(parts.slice(0, i).join('/'));
        }
      });
      setExpandedFolders(folders);
    } catch (error) {
      console.error('Failed to load files:', error);
      const errorMessage =
        error instanceof Error ? error.message : '加载文件列表失败';
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // 获取所有文件类型
  const fileTypes = useMemo(() => {
    const types = new Map<string, number>();
    files.forEach((f) => {
      const ext = getExtension(f.path);
      if (ext) {
        types.set(ext, (types.get(ext) || 0) + 1);
      }
    });
    return [...types.entries()].sort((a, b) => b[1] - a[1]);
  }, [files]);

  // 过滤后的文件
  const filteredFiles = useMemo(() => {
    let result = files;

    // 按搜索词过滤
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter((f) => f.path.toLowerCase().includes(term));
    }

    // 按文件类型过滤
    if (filterType) {
      result = result.filter((f) => getExtension(f.path) === filterType);
    }

    return result;
  }, [files, searchTerm, filterType]);

  // 构建文件夹树
  const folderTree = useMemo(
    () => buildFolderTree(filteredFiles),
    [filteredFiles],
  );

  const handleToggleFile = useCallback((path: string) => {
    setSelectedFiles((prev) => {
      const newSelected = new Set(prev);
      if (newSelected.has(path)) {
        newSelected.delete(path);
      } else {
        newSelected.add(path);
      }
      return newSelected;
    });
  }, []);

  const handleToggleFolder = useCallback(
    (folderPath: string) => {
      // 获取该文件夹下的所有文件
      const folderFiles = filteredFiles.filter(
        (f) => f.path.startsWith(`${folderPath}/`) || f.path === folderPath,
      );

      setSelectedFiles((prev) => {
        const newSelected = new Set(prev);
        const allSelected = folderFiles.every((f) => newSelected.has(f.path));

        if (allSelected) {
          // 取消选择该文件夹下的所有文件
          folderFiles.forEach((f) => newSelected.delete(f.path));
        } else {
          // 选择该文件夹下的所有文件
          folderFiles.forEach((f) => newSelected.add(f.path));
        }
        return newSelected;
      });
    },
    [filteredFiles],
  );

  const handleExpandFolder = useCallback((folderPath: string) => {
    setExpandedFolders((prev) => {
      const newExpanded = new Set(prev);
      if (newExpanded.has(folderPath)) {
        newExpanded.delete(folderPath);
      } else {
        newExpanded.add(folderPath);
      }
      return newExpanded;
    });
  }, []);

  const handleExpandAll = useCallback(() => {
    const folders = new Set<string>();
    filteredFiles.forEach((f) => {
      const parts = f.path.split('/');
      for (let i = 1; i < parts.length; i++) {
        folders.add(parts.slice(0, i).join('/'));
      }
    });
    setExpandedFolders(folders);
  }, [filteredFiles]);

  const handleCollapseAll = useCallback(() => {
    setExpandedFolders(new Set());
  }, []);

  const handleSelectAll = () => {
    setSelectedFiles(new Set(filteredFiles.map((f) => f.path)));
  };

  const handleDeselectAll = () => {
    const filteredPaths = new Set(filteredFiles.map((f) => f.path));
    setSelectedFiles((prev) => {
      const newSelected = new Set(prev);
      filteredPaths.forEach((p) => newSelected.delete(p));
      return newSelected;
    });
  };

  const handleInvertSelection = () => {
    const filteredPaths = new Set(filteredFiles.map((f) => f.path));
    setSelectedFiles((prev) => {
      const newSelected = new Set(prev);
      filteredPaths.forEach((p) => {
        if (newSelected.has(p)) {
          newSelected.delete(p);
        } else {
          newSelected.add(p);
        }
      });
      return newSelected;
    });
  };

  const handleConfirm = () => {
    if (selectedFiles.size === 0) {
      toast.error('请至少选择一个文件');
      return;
    }
    onConfirm([...selectedFiles]);
    onOpenChange(false);
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  // 检查文件夹的选中状态
  const getFolderSelectionState = (
    folderPath: string,
  ): 'all' | 'none' | 'some' => {
    const folderFiles = filteredFiles.filter((f) =>
      f.path.startsWith(`${folderPath}/`),
    );
    if (folderFiles.length === 0) return 'none';

    const selectedCount = folderFiles.filter((f) =>
      selectedFiles.has(f.path),
    ).length;
    if (selectedCount === 0) return 'none';
    if (selectedCount === folderFiles.length) return 'all';
    return 'some';
  };

  // 渲染文件夹树
  const renderFolderTree = (node: FolderNode, depth: number = 0) => {
    const items: React.ReactNode[] = [];

    // 渲染子文件夹
    [...node.subfolders.values()]
      .sort((a, b) => a.name.localeCompare(b.name))
      .forEach((folder) => {
        const isExpanded = expandedFolders.has(folder.path);
        const selectionState = getFolderSelectionState(folder.path);

        items.push(
          <div key={`folder-${folder.path}`}>
            <div
              className="hover:bg-muted hover:border-border flex cursor-pointer items-center space-x-2 rounded border border-transparent p-2 transition-colors"
              style={{ paddingLeft: `${depth * 16 + 8}px` }}
            >
              <button
                className="hover:bg-muted rounded p-0.5"
                onClick={(e) => {
                  e.stopPropagation();
                  handleExpandFolder(folder.path);
                }}
              >
                {isExpanded ? (
                  <ChevronDown className="text-muted-foreground h-4 w-4" />
                ) : (
                  <ChevronRight className="text-muted-foreground h-4 w-4" />
                )}
              </button>
              <div onClick={(e) => e.stopPropagation()}>
                <Checkbox
                  checked={selectionState === 'all'}
                  className="border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary data-[state=indeterminate]:bg-background0"
                  onCheckedChange={() => handleToggleFolder(folder.path)}
                  ref={(el) => {
                    if (el) {
                      let state = 'unchecked';
                      if (selectionState === 'some') {
                        state = 'indeterminate';
                      } else if (selectionState === 'all') {
                        state = 'checked';
                      }
                      (el as HTMLButtonElement).dataset.state = state;
                    }
                  }}
                />
              </div>
              {isExpanded ? (
                <FolderOpen className="h-4 w-4 text-amber-400" />
              ) : (
                <Folder className="h-4 w-4 text-amber-400" />
              )}
              <span
                className="text-foreground flex-1 font-mono text-sm font-medium"
                onClick={() => handleExpandFolder(folder.path)}
              >
                {folder.name}
              </span>
              <Badge className="cyber-badge-muted font-mono text-xs">
                {
                  filteredFiles.filter((f) =>
                    f.path.startsWith(`${folder.path}/`),
                  ).length
                }
              </Badge>
            </div>
            {isExpanded && renderFolderTree(folder, depth + 1)}
          </div>,
        );
      });

    // 渲染文件
    node.files
      .sort((a, b) => a.path.localeCompare(b.path))
      .forEach((file) => {
        const fileName = file.path.split('/').pop() || file.path;
        items.push(
          <div
            className="hover:bg-muted hover:border-border flex cursor-pointer items-center space-x-3 rounded border border-transparent p-2 transition-colors"
            key={`file-${file.path}`}
            onClick={() => handleToggleFile(file.path)}
            style={{ paddingLeft: `${depth * 16 + 32}px` }}
          >
            <div onClick={(e) => e.stopPropagation()}>
              <Checkbox
                checked={selectedFiles.has(file.path)}
                className="border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                onCheckedChange={() => handleToggleFile(file.path)}
              />
            </div>
            {getFileIcon(file.path)}
            <span
              className="text-foreground min-w-0 flex-1 truncate font-mono text-sm"
              title={file.path}
            >
              {fileName}
            </span>
            {file.size > 0 && (
              <Badge className="cyber-badge-muted flex-shrink-0 font-mono text-xs">
                {formatSize(file.size)}
              </Badge>
            )}
          </div>,
        );
      });

    return items;
  };

  // 渲染扁平列表
  const renderFlatList = () => {
    return filteredFiles.map((file) => (
      <div
        className="hover:bg-muted hover:border-border flex cursor-pointer items-center space-x-3 rounded border border-transparent p-2 transition-colors"
        key={file.path}
        onClick={() => handleToggleFile(file.path)}
      >
        <div onClick={(e) => e.stopPropagation()}>
          <Checkbox
            checked={selectedFiles.has(file.path)}
            className="border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary"
            onCheckedChange={() => handleToggleFile(file.path)}
          />
        </div>
        {getFileIcon(file.path)}
        <div className="min-w-0 flex-1">
          <p
            className="text-foreground truncate font-mono text-sm"
            title={file.path}
          >
            {file.path}
          </p>
        </div>
        {file.size > 0 && (
          <Badge className="cyber-badge-muted flex-shrink-0 font-mono text-xs">
            {formatSize(file.size)}
          </Badge>
        )}
      </div>
    ));
  };

  const fileListContent = (() => {
    if (loading) {
      return (
        <div className="bg-background/80 absolute inset-0 flex items-center justify-center px-6 text-center backdrop-blur-sm">
          <div className="max-w-sm space-y-4">
            <div className="loading-spinner mx-auto" />
            <div className="space-y-2">
              <p className="text-foreground text-sm font-semibold">
                正在同步代码并读取文件列表...
              </p>
              <p className="text-muted-foreground text-xs leading-6">
                大型仓库首次加载可能需要更久，请稍候。
              </p>
            </div>
          </div>
        </div>
      );
    }

    if (filteredFiles.length > 0) {
      const folderContent =
        viewMode === 'tree' ? renderFolderTree(folderTree) : renderFlatList();
      return (
        <div className="custom-scrollbar h-full overflow-auto">
          <div className="p-2">{folderContent}</div>
        </div>
      );
    }

    return (
      <div className="text-muted-foreground absolute inset-0 flex flex-col items-center justify-center">
        <FileText className="mb-2 h-12 w-12 opacity-20" />
        <p className="font-mono text-sm">
          {searchTerm || filterType ? '没有匹配的文件' : '没有找到文件'}
        </p>
      </div>
    );
  })();

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="cyber-card cyber-dialog !fixed flex max-h-[85vh] !w-[95vw] !max-w-[1000px] flex-col p-0">
        <DialogHeader className="cyber-card-header flex-shrink-0">
          <div className="flex items-center gap-3">
            <FolderOpen className="text-primary h-5 w-5" />
            <div className="flex flex-col gap-1">
              <DialogTitle className="text-foreground text-lg font-bold uppercase tracking-wider">
                选择要审计的文件
              </DialogTitle>
              <div className="text-muted-foreground flex flex-wrap gap-2 font-mono text-xs">
                {repositoryType && (
                  <Badge className="cyber-badge-muted uppercase">
                    {getRepositoryTypeLabel(repositoryType)}
                  </Badge>
                )}
                {branch && (
                  <Badge className="cyber-badge-muted uppercase">
                    分支: {branch}
                  </Badge>
                )}
                {manifestXml && (
                  <Badge className="cyber-badge-muted uppercase">
                    Manifest: {manifestXml}
                  </Badge>
                )}
                {group && (
                  <Badge className="cyber-badge-muted uppercase">
                    Group: {group}
                  </Badge>
                )}
                {repositoryType === 'multi' && (
                  <span className="text-muted-foreground">
                    多仓会先执行 `git mm init` 再同步代码
                  </span>
                )}
              </div>
            </div>
          </div>
          {excludePatterns && excludePatterns.length > 0 && (
            <Badge className="cyber-badge-muted ml-auto font-mono text-xs">
              已排除 {excludePatterns.length} 种模式
            </Badge>
          )}
        </DialogHeader>

        <div className="flex min-h-0 flex-1 flex-col space-y-3 overflow-y-auto p-5">
          {/* 工具栏 */}
          <div className="flex flex-wrap items-center gap-2">
            {/* 搜索框 */}
            <div className="relative min-w-[200px] flex-1">
              <Search className="text-muted-foreground absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform" />
              <Input
                className="cyber-input h-9 !pl-10"
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="搜索文件..."
                value={searchTerm}
              />
            </div>

            {/* 文件类型筛选 */}
            {fileTypes.length > 0 && (
              <div className="flex items-center gap-1">
                <Filter className="text-muted-foreground h-4 w-4" />
                <select
                  className="border-border cyber-bg-elevated text-foreground h-9 rounded border px-2 py-1 font-mono text-xs"
                  onChange={(e) => setFilterType(e.target.value)}
                  value={filterType}
                >
                  <option value="">全部类型</option>
                  {fileTypes.slice(0, 10).map(([ext, count]) => (
                    <option key={ext} value={ext}>
                      .{ext} ({count})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* 视图切换 */}
            <div className="border-border flex overflow-hidden rounded border">
              <button
                className={`px-3 py-1.5 font-mono text-xs uppercase ${viewMode === 'tree' ? 'bg-primary text-foreground' : 'bg-muted text-muted-foreground hover:bg-muted'}`}
                onClick={() => setViewMode('tree')}
              >
                树形
              </button>
              <button
                className={`border-border border-l px-3 py-1.5 font-mono text-xs uppercase ${viewMode === 'flat' ? 'bg-primary text-foreground' : 'bg-muted text-muted-foreground hover:bg-muted'}`}
                onClick={() => setViewMode('flat')}
              >
                列表
              </button>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button
                className="cyber-btn-outline h-8 px-3 font-mono text-xs"
                onClick={handleSelectAll}
                size="sm"
                variant="outline"
              >
                <CheckSquare className="mr-1 h-3 w-3" />
                全选
              </Button>
              <Button
                className="cyber-btn-outline h-8 px-3 font-mono text-xs"
                onClick={handleDeselectAll}
                size="sm"
                variant="outline"
              >
                <Square className="mr-1 h-3 w-3" />
                清空
              </Button>
              <Button
                className="cyber-btn-outline h-8 px-3 font-mono text-xs"
                onClick={handleInvertSelection}
                size="sm"
                variant="outline"
              >
                <RefreshCw className="mr-1 h-3 w-3" />
                反选
              </Button>
              {viewMode === 'tree' && (
                <>
                  <Button
                    className="cyber-btn-outline h-8 px-3 font-mono text-xs"
                    onClick={handleExpandAll}
                    size="sm"
                    variant="outline"
                  >
                    <ChevronDown className="mr-1 h-3 w-3" />
                    展开
                  </Button>
                  <Button
                    className="cyber-btn-outline h-8 px-3 font-mono text-xs"
                    onClick={handleCollapseAll}
                    size="sm"
                    variant="outline"
                  >
                    <ChevronRight className="mr-1 h-3 w-3" />
                    折叠
                  </Button>
                </>
              )}
              {(searchTerm || filterType) && (
                <Button
                  className="cyber-btn-outline text-muted-foreground h-8 px-3 font-mono text-xs"
                  onClick={() => {
                    setSearchTerm('');
                    setFilterType('');
                  }}
                  size="sm"
                  variant="outline"
                >
                  <RotateCcw className="mr-1 h-3 w-3" />
                  重置筛选
                </Button>
              )}
            </div>
            <div className="text-muted-foreground font-mono text-sm">
              {searchTerm || filterType ? (
                <span>
                  筛选: {filteredFiles.length}/{files.length} 个文件， 已选{' '}
                  <span className="text-primary font-bold">
                    {selectedFiles.size}
                  </span>{' '}
                  个
                </span>
              ) : (
                <span>
                  共 {files.length} 个文件，已选{' '}
                  <span className="text-primary font-bold">
                    {selectedFiles.size}
                  </span>{' '}
                  个
                </span>
              )}
            </div>
          </div>

          {/* 文件列表 */}
          <div className="border-border cyber-bg-elevated relative h-[450px] overflow-hidden rounded border">
            {fileListContent}
          </div>
        </div>

        <DialogFooter className="border-border bg-muted flex flex-shrink-0 justify-between border-t p-5">
          <div className="text-muted-foreground flex items-center gap-2 font-mono text-xs">
            <Terminal className="h-3 w-3" />
            提示：点击文件夹可展开/折叠，点击文件夹复选框可批量选择
          </div>
          <div className="flex gap-3">
            <Button
              className="cyber-btn-outline h-10 px-4 font-mono"
              onClick={() => onOpenChange(false)}
              variant="outline"
            >
              取消
            </Button>
            <Button
              className="cyber-btn-primary h-10 px-5 font-mono font-bold uppercase"
              disabled={selectedFiles.size === 0}
              onClick={handleConfirm}
            >
              <FileText className="mr-2 h-4 w-4" />
              确认选择 ({selectedFiles.size})
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
