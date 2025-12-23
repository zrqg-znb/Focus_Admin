import { ref, shallowRef } from 'vue';
import type { SystemFileManagerApi } from '#/api/core/file';
import { getFileList } from '#/api/core/file';

// 使用单例模式或者在顶层组件 provide
const currentFolderId = ref<string | null>(null);
const viewMode = ref<'grid' | 'list'>('grid');
const selectedFileIds = ref<Set<string>>(new Set());
const fileList = shallowRef<SystemFileManagerApi.FileItem[]>([]);
const loading = ref(false);
const breadcrumbs = ref<Array<{ id: string | null; name: string }>>([
  { id: null, name: '我的文件' },
]);
const createFolderDialogVisible = ref(false);

export function useFileManager() {
  const toggleViewMode = () => {
    viewMode.value = viewMode.value === 'grid' ? 'list' : 'grid';
  };

  const fetchFiles = async () => {
    loading.value = true;
    try {
      const res = await getFileList({
        parent_id: currentFolderId.value,
        page: 1,
        pageSize: 100,
      });
      fileList.value = res.items;
    } catch (error) {
      console.error(error);
    } finally {
      loading.value = false;
    }
  };

  const navigateToFolder = (folderId: string | null, folderName?: string) => {
    currentFolderId.value = folderId;
    selectedFileIds.value.clear();

    // 更新面包屑 (这里只是简单的逻辑，实际可能需要根据树结构查找完整路径)
    if (folderId === null) {
      breadcrumbs.value = [{ id: null, name: '我的文件' }];
    } else if (folderName) {
      // 如果是点击面包屑导航回去，需要截断
      const index = breadcrumbs.value.findIndex((b) => b.id === folderId);
      if (index !== -1) {
        breadcrumbs.value = breadcrumbs.value.slice(0, index + 1);
      } else {
        // 进入新文件夹
        breadcrumbs.value.push({ id: folderId, name: folderName });
      }
    }
    fetchFiles();
  };

  const toggleSelection = (id: string, multi: boolean) => {
    if (!multi) {
      selectedFileIds.value.clear();
      selectedFileIds.value.add(id);
    } else {
      if (selectedFileIds.value.has(id)) {
        selectedFileIds.value.delete(id);
      } else {
        selectedFileIds.value.add(id);
      }
    }
  };

  const clearSelection = () => {
    selectedFileIds.value.clear();
  };

  const openCreateFolderDialog = () => {
    createFolderDialogVisible.value = true;
  };

  return {
    currentFolderId,
    viewMode,
    selectedFileIds,
    fileList,
    loading,
    breadcrumbs,
    createFolderDialogVisible,
    toggleViewMode,
    navigateToFolder,
    toggleSelection,
    clearSelection,
    fetchFiles,
    openCreateFolderDialog,
  };
}
