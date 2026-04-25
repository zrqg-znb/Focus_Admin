import type {
  ProjectFileBrowserItem,
  ProjectRepositorySpec,
} from '@/shared/api/database';

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
import { useDebounce } from '@/shared/hooks';
import {
  getRepositoryTypeLabel,
  normalizeRepositoryType,
} from '@/shared/utils/projectUtils';
import {
  ChevronLeft,
  ChevronRight,
  File,
  FileCode,
  FileJson,
  FileText,
  Folder,
  FolderOpen,
  RefreshCw,
  RotateCcw,
  Search,
  Terminal,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
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
  onConfirm: (payload: {
    repositorySpec: ProjectRepositorySpec;
    repositorySignature?: string;
    selectedFiles: string[];
    selectedSummary: {
      directoryCount: number;
      fileCount: number;
      totalCount: number;
    };
  }) => void;
}

const PAGE_SIZE = 200;

const getFileIcon = (path: string) => {
  const ext = path.split('.').pop()?.toLowerCase() || '';
  const codeExts = [
    'c',
    'cc',
    'cpp',
    'cs',
    'go',
    'h',
    'hpp',
    'java',
    'js',
    'jsx',
    'kt',
    'php',
    'py',
    'rb',
    'rs',
    'sh',
    'swift',
    'ts',
    'tsx',
  ];
  const configExts = ['ini', 'json', 'toml', 'xml', 'yaml', 'yml'];

  if (codeExts.includes(ext)) {
    return <FileCode className="h-4 w-4 text-sky-400" />;
  }
  if (configExts.includes(ext)) {
    return <FileJson className="h-4 w-4 text-amber-400" />;
  }
  return <File className="text-muted-foreground h-4 w-4" />;
};

const formatSize = (bytes: number) => {
  if (bytes <= 0) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
};

const formatSyncTime = (timestamp?: null | number) => {
  if (!timestamp) return '';
  return new Date(timestamp * 1000).toLocaleString('zh-CN', {
    hour12: false,
  });
};

const getParentPath = (path: string) => {
  if (!path) return '';
  const parts = path.split('/');
  parts.pop();
  return parts.join('/');
};

const buildFallbackRepositorySpec = ({
  branch,
  group,
  manifestXml,
  repositoryType,
}: Pick<
  FileSelectionDialogProps,
  'branch' | 'group' | 'manifestXml' | 'repositoryType'
>): ProjectRepositorySpec => ({
  repository_type: normalizeRepositoryType(repositoryType),
  repository_url: '',
  branch_name: branch || 'main',
  manifest_xml: manifestXml || '',
  group: group || '',
});

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
  const [items, setItems] = useState<ProjectFileBrowserItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedEntries, setSelectedEntries] = useState<
    Record<string, ProjectFileBrowserItem['kind']>
  >({});
  const [searchInput, setSearchInput] = useState('');
  const [currentPath, setCurrentPath] = useState('');
  const [hasMore, setHasMore] = useState(false);
  const [total, setTotal] = useState(0);
  const [lastSyncedAt, setLastSyncedAt] = useState<null | number>(null);
  const [sessionSpec, setSessionSpec] = useState<ProjectRepositorySpec>();
  const [sessionSignature, setSessionSignature] = useState('');
  const requestIdRef = useRef(0);
  const debouncedSearch = useDebounce(searchInput.trim(), 300);

  useEffect(() => {
    if (!open) {
      setItems([]);
      setLoading(false);
      setLoadingMore(false);
      setRefreshing(false);
      setSelectedEntries({});
      setSearchInput('');
      setCurrentPath('');
      setHasMore(false);
      setTotal(0);
      setLastSyncedAt(null);
      setSessionSpec(undefined);
      setSessionSignature('');
    }
  }, [open]);

  const loadEntries = async ({
    append = false,
    keyword = debouncedSearch,
    nextOffset = 0,
    nextPath = currentPath,
    refresh = false,
  }: {
    append?: boolean;
    keyword?: string;
    nextOffset?: number;
    nextPath?: string;
    refresh?: boolean;
  }) => {
    if (!open || !projectId) return;

    const requestId = ++requestIdRef.current;
    if (append) {
      setLoadingMore(true);
    } else if (refresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      const data = await api.browseProjectFiles(projectId, {
        repository_type: repositoryType,
        branch_name: branch,
        manifest_xml: manifestXml,
        group,
        path: nextPath,
        keyword,
        offset: nextOffset,
        limit: PAGE_SIZE,
        refresh,
        exclude_patterns: excludePatterns,
      });
      if (requestId !== requestIdRef.current) {
        return;
      }
      setItems((prev) => (append ? [...prev, ...data.items] : data.items));
      setHasMore(data.has_more);
      setTotal(data.total);
      setLastSyncedAt(data.last_synced_at ?? null);
      setSessionSpec(data.repository_spec);
      if (
        sessionSignature &&
        data.repository_signature &&
        sessionSignature !== data.repository_signature &&
        Object.keys(selectedEntries).length > 0
      ) {
        setSelectedEntries({});
        toast.warning('仓库规格已变化，请重新选择文件/目录');
      }
      setSessionSignature(data.repository_signature || '');
    } catch (error) {
      if (requestId !== requestIdRef.current) {
        return;
      }
      const errorMessage =
        error instanceof Error ? error.message : '加载文件浏览数据失败';
      toast.error(errorMessage);
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false);
        setLoadingMore(false);
        setRefreshing(false);
      }
    }
  };

  useEffect(() => {
    if (!open || !projectId) {
      return;
    }
    loadEntries({
      append: false,
      keyword: debouncedSearch,
      nextOffset: 0,
      nextPath: currentPath,
    });
  }, [
    open,
    projectId,
    repositoryType,
    branch,
    manifestXml,
    group,
    currentPath,
    debouncedSearch,
    excludePatterns,
  ]);

  const visibleItems = useMemo(
    () => items.map((item) => ({ kind: item.kind, path: item.path })),
    [items],
  );

  const selectedPaths = useMemo(
    () => Object.keys(selectedEntries),
    [selectedEntries],
  );

  const selectedSummary = useMemo(() => {
    const kinds = Object.values(selectedEntries);
    const directoryCount = kinds.filter((kind) => kind === 'directory').length;
    const fileCount = kinds.length - directoryCount;
    return {
      directoryCount,
      fileCount,
      totalCount: kinds.length,
    };
  }, [selectedEntries]);

  const breadcrumbs = useMemo(() => {
    const parts = currentPath ? currentPath.split('/') : [];
    const rows = [{ label: '根目录', path: '' }];
    let cumulative = '';
    parts.forEach((part) => {
      cumulative = cumulative ? `${cumulative}/${part}` : part;
      rows.push({ label: part, path: cumulative });
    });
    return rows;
  }, [currentPath]);

  const visibleSelectedCount = useMemo(
    () =>
      visibleItems.filter((item) => Boolean(selectedEntries[item.path])).length,
    [selectedEntries, visibleItems],
  );
  let browsingHint = '浏览根目录';
  if (debouncedSearch) {
    browsingHint = `搜索 "${debouncedSearch}" 的结果`;
  } else if (currentPath) {
    browsingHint = `浏览目录: ${currentPath}`;
  }

  const handleToggleItem = (
    path: string,
    kind: ProjectFileBrowserItem['kind'],
  ) => {
    setSelectedEntries((prev) => {
      if (prev[path]) {
        const { [path]: _removed, ...rest } = prev;
        return rest;
      }
      return {
        ...prev,
        [path]: kind,
      };
    });
  };

  const handleSelectVisible = () => {
    setSelectedEntries((prev) => {
      const next = { ...prev };
      visibleItems.forEach((item) => {
        next[item.path] = item.kind;
      });
      return next;
    });
  };

  const handleClearVisible = () => {
    const visiblePaths = new Set(visibleItems.map((item) => item.path));
    setSelectedEntries((prev) => {
      const remainingEntries = Object.entries(prev).filter(
        ([path]) => !visiblePaths.has(path),
      );
      return Object.fromEntries(remainingEntries);
    });
  };

  const handleLoadMore = () => {
    if (!hasMore || loadingMore) return;
    loadEntries({
      append: true,
      keyword: debouncedSearch,
      nextOffset: items.length,
      nextPath: currentPath,
    });
  };

  const handleRefresh = () => {
    loadEntries({
      append: false,
      keyword: debouncedSearch,
      nextOffset: 0,
      nextPath: currentPath,
      refresh: true,
    });
  };

  const handleConfirm = () => {
    if (selectedSummary.totalCount === 0) {
      toast.error('请至少选择一个文件或目录');
      return;
    }
    onConfirm({
      selectedFiles: [...selectedPaths].sort((a, b) => a.localeCompare(b)),
      selectedSummary,
      repositorySignature: sessionSignature || undefined,
      repositorySpec:
        sessionSpec ||
        buildFallbackRepositorySpec({
          branch,
          group,
          manifestXml,
          repositoryType,
        }),
    });
    onOpenChange(false);
  };

  const fileListContent = (() => {
    if (loading) {
      return (
        <div className="bg-background/80 absolute inset-0 flex items-center justify-center px-6 text-center backdrop-blur-sm">
          <div className="max-w-sm space-y-4">
            <div className="loading-spinner mx-auto" />
            <div className="space-y-2">
              <p className="text-foreground text-sm font-semibold">
                正在同步代码并读取文件目录...
              </p>
              <p className="text-muted-foreground text-xs leading-6">
                大仓库首次进入时只会加载当前目录或搜索结果，不再一次性展开完整代码树。
              </p>
            </div>
          </div>
        </div>
      );
    }

    if (items.length === 0) {
      return (
        <div className="text-muted-foreground absolute inset-0 flex flex-col items-center justify-center px-6 text-center">
          <FileText className="mb-2 h-12 w-12 opacity-20" />
          <p className="text-sm">
            {debouncedSearch
              ? '没有匹配的文件或目录'
              : '当前目录下没有可显示的文件'}
          </p>
        </div>
      );
    }

    return (
      <div className="custom-scrollbar h-full overflow-auto">
        <div className="space-y-2 p-3">
          {items.map((item) => {
            const isDirectory = item.kind === 'directory';
            const isChecked = Boolean(selectedEntries[item.path]);
            return (
              <div
                className="hover:bg-muted hover:border-border flex items-center gap-3 rounded border border-transparent p-2 transition-colors"
                key={`${item.kind}-${item.path}`}
              >
                <div onClick={(event) => event.stopPropagation()}>
                  <Checkbox
                    checked={isChecked}
                    className="border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                    onCheckedChange={() =>
                      handleToggleItem(item.path, item.kind)
                    }
                  />
                </div>

                {isDirectory ? (
                  currentPath === item.path ? (
                    <FolderOpen className="h-4 w-4 text-amber-400" />
                  ) : (
                    <Folder className="h-4 w-4 text-amber-400" />
                  )
                ) : (
                  getFileIcon(item.path)
                )}

                <div className="min-w-0 flex-1">
                  <p
                    className="text-foreground truncate font-mono text-sm"
                    title={item.path}
                  >
                    {item.path}
                  </p>
                  <p className="text-muted-foreground truncate text-xs">
                    {isDirectory ? '目录，递归包含其全部子文件' : '文件'}
                  </p>
                </div>

                {isDirectory && (
                  <Button
                    className="h-8 px-2 text-xs"
                    onClick={() => {
                      setSearchInput('');
                      setCurrentPath(item.path);
                    }}
                    size="sm"
                    variant="ghost"
                  >
                    <ChevronRight className="mr-1 h-3 w-3" />
                    进入
                  </Button>
                )}

                {item.size > 0 && (
                  <Badge className="cyber-badge-muted flex-shrink-0 font-mono text-xs">
                    {formatSize(item.size)}
                  </Badge>
                )}
              </div>
            );
          })}

          {hasMore && (
            <div className="flex justify-center pt-2">
              <Button
                className="cyber-btn-outline h-8 px-4 text-xs"
                disabled={loadingMore}
                onClick={handleLoadMore}
                variant="outline"
              >
                {loadingMore ? '加载中...' : '加载更多'}
              </Button>
            </div>
          )}
        </div>
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
                选择要审计的文件/目录
              </DialogTitle>
              <div className="text-muted-foreground flex flex-wrap gap-2 text-xs">
                <Badge className="cyber-badge-muted uppercase">
                  {getRepositoryTypeLabel(
                    sessionSpec?.repository_type || repositoryType,
                  )}
                </Badge>
                {sessionSpec?.branch_name || branch ? (
                  <Badge className="cyber-badge-muted uppercase">
                    分支: {sessionSpec?.branch_name || branch}
                  </Badge>
                ) : null}
                {sessionSpec?.manifest_xml || manifestXml ? (
                  <Badge className="cyber-badge-muted uppercase">
                    Manifest: {sessionSpec?.manifest_xml || manifestXml}
                  </Badge>
                ) : null}
                {sessionSpec?.group || group ? (
                  <Badge className="cyber-badge-muted uppercase">
                    Group: {sessionSpec?.group || group}
                  </Badge>
                ) : null}
                {lastSyncedAt ? (
                  <span className="text-muted-foreground">
                    最近同步: {formatSyncTime(lastSyncedAt)}
                  </span>
                ) : null}
              </div>
            </div>
          </div>
          {excludePatterns && excludePatterns.length > 0 && (
            <Badge className="cyber-badge-muted ml-auto text-xs">
              已排除 {excludePatterns.length} 种模式
            </Badge>
          )}
        </DialogHeader>

        <div className="flex min-h-0 flex-1 flex-col space-y-3 overflow-y-auto p-5">
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative min-w-[240px] flex-1">
              <Search className="text-muted-foreground absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform" />
              <Input
                className="cyber-input h-9 !pl-10"
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="搜索文件名或路径..."
                value={searchInput}
              />
            </div>

            <Button
              className="cyber-btn-outline h-9 px-3 text-xs"
              disabled={!currentPath}
              onClick={() => setCurrentPath(getParentPath(currentPath))}
              size="sm"
              variant="outline"
            >
              <ChevronLeft className="mr-1 h-3 w-3" />
              返回上级
            </Button>
            <Button
              className="cyber-btn-outline h-9 px-3 text-xs"
              disabled={refreshing}
              onClick={handleRefresh}
              size="sm"
              variant="outline"
            >
              <RefreshCw className="mr-1 h-3 w-3" />
              {refreshing ? '刷新中' : '刷新代码树'}
            </Button>
            {(searchInput || currentPath) && (
              <Button
                className="cyber-btn-outline text-muted-foreground h-9 px-3 text-xs"
                onClick={() => {
                  setSearchInput('');
                  setCurrentPath('');
                }}
                size="sm"
                variant="outline"
              >
                <RotateCcw className="mr-1 h-3 w-3" />
                回到根目录
              </Button>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              {breadcrumbs.map((item, index) => (
                <div
                  className="flex items-center gap-2"
                  key={item.path || 'root'}
                >
                  {index > 0 && (
                    <ChevronRight className="text-muted-foreground h-3 w-3" />
                  )}
                  <button
                    className={`font-mono text-xs ${item.path === currentPath ? 'text-foreground font-bold' : 'text-muted-foreground hover:text-foreground'}`}
                    onClick={() => setCurrentPath(item.path)}
                    type="button"
                  >
                    {item.label}
                  </button>
                </div>
              ))}
            </div>
            <div className="text-muted-foreground text-xs">
              当前已加载 {items.length}/{total} 项，已选{' '}
              <span className="text-primary font-bold">
                {selectedSummary.totalCount}
              </span>{' '}
              项
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <Button
                className="cyber-btn-outline h-8 px-3 text-xs"
                disabled={visibleItems.length === 0}
                onClick={handleSelectVisible}
                size="sm"
                variant="outline"
              >
                选择当前页可见项
              </Button>
              <Button
                className="cyber-btn-outline h-8 px-3 text-xs"
                disabled={visibleSelectedCount === 0}
                onClick={handleClearVisible}
                size="sm"
                variant="outline"
              >
                清空当前页选择
              </Button>
              <Button
                className="cyber-btn-outline h-8 px-3 text-xs"
                disabled={selectedSummary.totalCount === 0}
                onClick={() => setSelectedEntries({})}
                size="sm"
                variant="outline"
              >
                清空全部选择
              </Button>
            </div>
            <div className="text-muted-foreground text-xs">
              {browsingHint}
            </div>
          </div>

          <div className="border-border cyber-bg-elevated relative h-[450px] overflow-hidden rounded border">
            {fileListContent}
          </div>
        </div>

        <DialogFooter className="border-border bg-muted flex flex-shrink-0 justify-between border-t p-5">
          <div className="text-muted-foreground flex items-center gap-2 text-xs">
            <Terminal className="h-3 w-3" />
            提示：目录勾选后会递归包含全部子文件；大仓仍按懒加载和分页方式浏览。
          </div>
          <div className="flex gap-3">
            <Button
              className="cyber-btn-outline h-10 px-4"
              onClick={() => onOpenChange(false)}
              variant="outline"
            >
              取消
            </Button>
            <Button
              className="cyber-btn-primary h-10 px-5 font-semibold uppercase"
              disabled={selectedSummary.totalCount === 0}
              onClick={handleConfirm}
            >
              <FileText className="mr-2 h-4 w-4" />
              确认选择 ({selectedSummary.totalCount} 项)
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
