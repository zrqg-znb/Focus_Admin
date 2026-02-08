<script lang="ts" setup>
import type { OrgNode } from '#/api/delivery-matrix';

import { computed, onMounted, ref } from 'vue';

import { IconifyIcon, Search } from '@vben/icons';

import {
  ElButton,
  ElCard,
  ElInput,
  ElMessageBox,
  ElMessage,
  ElScrollbar,
  ElSkeleton,
  ElSkeletonItem,
  ElTooltip,
} from 'element-plus';

import {
  deleteNode,
  getTree,
} from '#/api/delivery-matrix';

const emit = defineEmits<{
  add: [parentNode?: OrgNode];
  select: [node: OrgNode | undefined];
}>();

const treeData = ref<OrgNode[]>([]);
const loading = ref(false);
const deleteLoading = ref(false);
const selectedNodeId = ref<string>();
const searchKeyword = ref('');
const expandedIds = ref<Set<string>>(new Set());
const hoveredNodeId = ref<string>();

const filteredTreeData = computed(() => {
  if (!searchKeyword.value) return treeData.value;
  // 不过滤，只展开匹配的节点
  const keyword = searchKeyword.value.toLowerCase();
  const matchedIds = new Set<string>();
  
  const findMatches = (nodes: OrgNode[]) => {
    for (const node of nodes) {
      if (node.name.toLowerCase().includes(keyword)) {
        matchedIds.add(node.id);
        // 展开父节点的逻辑需要在树遍历中处理
      }
      if (node.children) {
        findMatches(node.children);
      }
    }
  };
  
  findMatches(treeData.value);
  
  // 自动展开包含匹配节点的父节点
  const expandParents = (nodes: OrgNode[]): boolean => {
    let hasMatch = false;
    for (const node of nodes) {
      const childMatch = node.children ? expandParents(node.children) : false;
      const selfMatch = matchedIds.has(node.id);
      
      if (childMatch || selfMatch) {
        hasMatch = true;
        if (childMatch) {
          expandedIds.value.add(node.id);
        }
      }
    }
    return hasMatch;
  };
  
  expandParents(treeData.value);
  
  return treeData.value;
});

const flattenedTree = computed(() => {
  const result: { level: number; node: OrgNode }[] = [];
  const traverse = (nodes: OrgNode[], level: number) => {
    for (const node of nodes) {
      result.push({ node, level });
      if (expandedIds.value.has(node.id) && node.children) {
        traverse(node.children, level + 1);
      }
    }
  };
  traverse(filteredTreeData.value, 0);
  return result;
});

async function fetchTree() {
  loading.value = true;
  try {
    treeData.value = await getTree();
  } finally {
    loading.value = false;
  }
}

function toggleExpand(node: OrgNode) {
  if (expandedIds.value.has(node.id)) {
    expandedIds.value.delete(node.id);
  } else {
    expandedIds.value.add(node.id);
  }
}

function onSelect(node: OrgNode) {
  selectedNodeId.value = node.id;
  emit('select', node);
}

function onAdd(parentNode?: OrgNode) {
  emit('add', parentNode);
}

async function onDelete(node: OrgNode) {
  if (deleteLoading.value) return; // 防止重复点击
  
  try {
    await ElMessageBox.confirm('确定要删除该节点吗？此操作不可恢复。', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    });
    
    deleteLoading.value = true;
    await deleteNode(node.id);
    ElMessage.success('删除成功');
    await fetchTree();
    if (selectedNodeId.value === node.id) {
      selectedNodeId.value = undefined;
      emit('select', undefined);
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error);
      ElMessage.error('删除失败');
    }
  } finally {
    deleteLoading.value = false;
  }
}

defineExpose({
  refresh: fetchTree,
});

onMounted(fetchTree);
</script>

<template>
  <ElCard
    class="h-full border-none shadow-none"
    :body-style="{
      padding: '10px',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
    }"
  >
    <div class="mb-4 flex gap-2">
      <ElInput
        v-model="searchKeyword"
        placeholder="搜索..."
        :prefix-icon="Search"
        clearable
      />
       <ElTooltip content="添加根节点">
          <ElButton
            type="primary"
            size="small"
            @click="onAdd()"
          >
            <IconifyIcon icon="ep:plus" />
          </ElButton>
        </ElTooltip>
    </div>

    <div class="flex-1 overflow-hidden">
      <ElSkeleton :loading="loading" animated :count="8">
        <template #template>
          <div v-for="i in 8" :key="i" class="py-2">
            <ElSkeletonItem variant="text" style="width: 100%" />
          </div>
        </template>
        <template #default>
          <ElScrollbar>
            <div
              v-for="item in flattenedTree"
              :key="item.node.id"
              class="flex h-10 cursor-pointer items-center rounded px-2 transition-colors hover:bg-gray-100"
              :class="{
                'bg-blue-50 text-blue-600': selectedNodeId === item.node.id,
              }"
              :style="{ paddingLeft: `${item.level * 20 + 8}px` }"
              @click="onSelect(item.node)"
              @mouseenter="hoveredNodeId = item.node.id"
              @mouseleave="hoveredNodeId = undefined"
            >
              <!-- Expand Icon -->
              <div
                v-if="item.node.children && item.node.children.length > 0"
                class="mr-1 flex h-4 w-4 cursor-pointer items-center justify-center"
                @click.stop="toggleExpand(item.node)"
              >
                <IconifyIcon
                  icon="ep:caret-right"
                  class="transform transition-transform"
                  :class="{ 'rotate-90': expandedIds.has(item.node.id) }"
                />
              </div>
              <div v-else class="w-5"></div>

              <!-- Icon -->
              <IconifyIcon
                icon="carbon:folder"
                class="mr-2"
              />

              <span class="flex-1 truncate">{{ item.node.name }}</span>

              <!-- Actions -->
              <div
                v-if="hoveredNodeId === item.node.id"
                class="flex gap-1"
                @click.stop
              >
                <ElTooltip
                  content="添加子节点"
                >
                  <ElButton
                    link
                    type="primary"
                    size="small"
                    @click="onAdd(item.node)"
                  >
                    <IconifyIcon icon="ep:plus" />
                  </ElButton>
                </ElTooltip>
                
                <ElTooltip content="删除节点">
                    <ElButton
                    link
                    type="danger"
                    size="small"
                    :loading="deleteLoading"
                    @click="onDelete(item.node)"
                    >
                    <IconifyIcon icon="ep:delete" />
                    </ElButton>
                </ElTooltip>
              </div>
            </div>
          </ElScrollbar>
        </template>
      </ElSkeleton>
    </div>
  </ElCard>
</template>
