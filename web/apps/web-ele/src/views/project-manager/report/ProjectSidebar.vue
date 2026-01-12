<script lang="ts" setup>
import { ref, onMounted, computed, watch } from 'vue';
import { ElInput, ElTree, ElScrollbar, ElEmpty } from 'element-plus';
import { IconifyIcon } from '@vben/icons';
import { listProjectsApi } from '#/api/project-manager/project';
import type { ProjectOut } from '#/api/project-manager/project';

const emit = defineEmits<{
  (e: 'select', projectId: string): void;
}>();

const props = defineProps<{
  currentId?: string;
}>();

const loading = ref(false);
const filterText = ref('');
const treeRef = ref<InstanceType<typeof ElTree>>();
const projects = ref<ProjectOut[]>([]);

// Tree Data Structure
interface TreeNode {
  id: string;
  label: string;
  type: 'category' | 'project';
  children?: TreeNode[];
  data?: ProjectOut;
}

const treeData = computed<TreeNode[]>(() => {
  const groups: Record<string, ProjectOut[]> = {};
  
  // Group by domain
  projects.value.forEach(p => {
    const domain = p.domain || '未分类';
    if (!groups[domain]) {
      groups[domain] = [];
    }
    groups[domain].push(p);
  });
  
  return Object.keys(groups).map(domain => ({
    id: `domain-${domain}`,
    label: domain,
    type: 'category',
    children: groups[domain].map(p => ({
      id: p.id,
      label: p.name,
      type: 'project',
      data: p
    }))
  }));
});

watch(filterText, (val) => {
  treeRef.value!.filter(val);
});

const filterNode = (value: string, data: TreeNode) => {
  if (!value) return true;
  return data.label.toLowerCase().includes(value.toLowerCase());
};

const handleNodeClick = (data: TreeNode) => {
  if (data.type === 'project') {
    emit('select', data.id);
  }
};

async function fetchProjects() {
  loading.value = true;
  try {
    // Fetch all active projects (assuming pageSize 1000 covers most cases for now)
    const res = await listProjectsApi({ pageSize: 1000, is_closed: false });
    projects.value = res.items;
  } catch (error) {
    console.error('Failed to fetch projects', error);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  fetchProjects();
});
</script>

<template>
  <div class="h-full flex flex-col bg-white dark:bg-[#151515] border-r border-gray-200 dark:border-gray-800 rounded-l-xl overflow-hidden">
    <!-- Search Header -->
    <div class="p-4 border-b border-gray-100 dark:border-gray-800">
      <div class="flex items-center gap-2 mb-3">
         <IconifyIcon icon="lucide:folder-kanban" class="text-primary" />
         <span class="font-bold text-base">项目列表</span>
      </div>
      <ElInput
        v-model="filterText"
        placeholder="搜索项目..."
        prefix-icon="ep:search"
        clearable
        size="small"
      />
    </div>
    
    <!-- Project Tree -->
    <div class="flex-1 overflow-hidden relative">
       <ElScrollbar>
          <div v-if="projects.length === 0 && !loading" class="p-4 text-center">
             <ElEmpty description="暂无项目" image-size="60" />
          </div>
          
          <ElTree
            v-else
            ref="treeRef"
            class="filter-tree p-2"
            :data="treeData"
            :props="{ label: 'label', children: 'children' }"
            :filter-node-method="filterNode"
            :expand-on-click-node="false"
            highlight-current
            node-key="id"
            :current-node-key="currentId"
            @node-click="handleNodeClick"
          >
             <template #default="{ node, data }">
                <div class="flex items-center gap-2 w-full overflow-hidden">
                   <IconifyIcon 
                      v-if="data.type === 'category'" 
                      icon="lucide:folder" 
                      class="text-gray-400 flex-shrink-0" 
                   />
                   <IconifyIcon 
                      v-else 
                      icon="lucide:box" 
                      class="text-blue-500 flex-shrink-0" 
                   />
                   <span class="truncate text-sm" :class="{'font-medium': data.type === 'category'}">
                      {{ node.label }}
                   </span>
                </div>
             </template>
          </ElTree>
       </ElScrollbar>
    </div>
  </div>
</template>

<style scoped>
:deep(.el-tree-node__content) {
  height: 36px;
  border-radius: 6px;
  margin-bottom: 2px;
}
:deep(.el-tree-node__content:hover) {
  background-color: var(--el-fill-color-light);
}
:deep(.el-tree--highlight-current .el-tree-node.is-current > .el-tree-node__content) {
  background-color: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}
.dark :deep(.el-tree--highlight-current .el-tree-node.is-current > .el-tree-node__content) {
  background-color: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  /* Dark mode specific adjustment if needed */
  background-color: rgba(var(--el-color-primary-rgb), 0.2);
}
</style>