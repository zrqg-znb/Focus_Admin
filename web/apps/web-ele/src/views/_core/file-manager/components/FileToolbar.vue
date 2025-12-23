<script setup lang="ts">
import { ref } from 'vue';
import {
  Search,
  LayoutGrid,
  List,
  Plus,
  RotateCw,
  Home,
  ChevronRight,
  Upload,
  Trash2
} from '@vben/icons';
import { ElBreadcrumb, ElBreadcrumbItem, ElButton, ElInput, ElDropdown, ElDropdownMenu, ElDropdownItem, ElMessage, ElMessageBox } from 'element-plus';
import { useFileManager } from '../composables/useFileManager';
import { uploadFile, batchDelete } from '#/api/core/file';

const { viewMode, breadcrumbs, currentFolderId, selectedFileIds, navigateToFolder, openCreateFolderDialog, fetchFiles, clearSelection } = useFileManager();

const fileInputRef = ref<HTMLInputElement | null>(null);
// ... (rest of the code)

const handleBatchDelete = async () => {
  if (selectedFileIds.value.size === 0) return;

  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedFileIds.value.size} 个项目吗？`, '提示', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    });

    await batchDelete({ ids: Array.from(selectedFileIds.value) });
    ElMessage.success('删除成功');
    clearSelection();
    fetchFiles();
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error);
    }
  }
};
const folderInputRef = ref<HTMLInputElement | null>(null);
const uploading = ref(false);

const handleBreadcrumbClick = (id: string | null, name: string) => {
  navigateToFolder(id, name);
};

const handleCreateFolder = () => {
  openCreateFolderDialog();
};

const handleUploadFile = () => {
  fileInputRef.value?.click();
};

const handleUploadFolder = () => {
  folderInputRef.value?.click();
};

const handleFileChange = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  const files = target.files;

  if (!files || files.length === 0) return;

  uploading.value = true;
  let successCount = 0;
  let failCount = 0;

  try {
    // 串行上传，避免并发过大
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (!file) continue;

      try {
        await uploadFile(file, currentFolderId.value || undefined);
        successCount++;
      } catch (error) {
        console.error(`Failed to upload ${file.name}`, error);
        failCount++;
      }
    }

    if (successCount > 0) {
      ElMessage.success(`成功上传 ${successCount} 个文件`);
      fetchFiles();
    }
    if (failCount > 0) {
      ElMessage.error(`${failCount} 个文件上传失败`);
    }
  } catch (error) {
    console.error(error);
    ElMessage.error('上传出错');
  } finally {
    uploading.value = false;
    // 清空 input，允许重复上传同名文件（虽然业务逻辑可能需要去重，但前端先允许）
    target.value = '';
  }
};
</script>

<template>
  <div class="flex items-center justify-between border-b border-border px-4 py-3">
    <!-- Hidden Inputs -->
    <input
      ref="fileInputRef"
      type="file"
      multiple
      class="hidden"
      @change="handleFileChange"
    />
    <input
      ref="folderInputRef"
      type="file"
      webkitdirectory
      class="hidden"
      @change="handleFileChange"
    />

    <!-- Breadcrumbs -->
    <div class="mr-4 flex flex-1 items-center overflow-hidden">
       <ElBreadcrumb :separator-icon="ChevronRight">
          <ElBreadcrumbItem v-for="(item, index) in breadcrumbs" :key="item.id || 'root'">
             <span
               class="flex cursor-pointer items-center gap-1 hover:text-primary"
               :class="{ 'font-bold text-foreground': index === breadcrumbs.length - 1 }"
               @click="handleBreadcrumbClick(item.id, item.name)"
             >
               <Home v-if="index === 0" class="size-4" />
               {{ item.name }}
             </span>
          </ElBreadcrumbItem>
       </ElBreadcrumb>
    </div>

    <!-- Actions -->
    <div class="flex flex-shrink-0 items-center gap-2 sm:gap-3">
       <ElInput placeholder="搜索..." class="w-32 sm:w-48">
          <template #prefix>
            <Search class="size-4" />
          </template>
       </ElInput>

       <div class="flex flex-shrink-0 items-center overflow-hidden rounded-md border border-border">
          <button
            class="p-2 hover:bg-accent"
            :class="{ 'bg-accent text-primary': viewMode === 'list' }"
            @click="viewMode = 'list'"
            title="列表视图"
          >
            <List class="size-4" />
          </button>
           <button
            class="p-2 hover:bg-accent"
            :class="{ 'bg-accent text-primary': viewMode === 'grid' }"
            @click="viewMode = 'grid'"
            title="网格视图"
          >
            <LayoutGrid class="size-4" />
          </button>
       </div>

       <ElButton circle @click="fetchFiles">
         <template #icon><RotateCw class="size-4" :class="{ 'animate-spin': uploading }" /></template>
       </ElButton>

       <ElButton v-if="selectedFileIds.size > 0" type="danger" plain @click="handleBatchDelete">
         <Trash2 class="mr-2 size-4" /> 批量删除
       </ElButton>

       <ElButton type="primary" @click="handleCreateFolder" class="hidden sm:flex">
         <Plus class="mr-2 size-4" /> 新建文件夹
       </ElButton>

       <ElDropdown trigger="click">
         <ElButton type="primary" :loading="uploading" class="hidden sm:flex">
           <Upload class="mr-2 size-4" /> 上传
         </ElButton>
         <ElButton circle type="primary" :loading="uploading" class="flex sm:hidden">
            <template #icon><Upload class="size-4" /></template>
         </ElButton>
         <template #dropdown>
           <ElDropdownMenu>
             <ElDropdownItem @click="handleUploadFile">上传文件</ElDropdownItem>
             <ElDropdownItem @click="handleUploadFolder">上传文件夹</ElDropdownItem>
           </ElDropdownMenu>
         </template>
       </ElDropdown>
    </div>
  </div>
</template>
