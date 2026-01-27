<script lang="ts" setup>
import type { DeliveryTreeNode } from '#/api/delivery-matrix';

import { computed, onMounted, ref } from 'vue';

import { IconifyIcon, Search } from '@vben/icons';

import {
  ElButton,
  ElCard,
  ElInput,
  ElScrollbar,
  ElSkeleton,
  ElSkeletonItem,
  ElTooltip,
} from 'element-plus';

import {
  deleteComponent,
  deleteDomain,
  deleteGroup,
  getAdminTree,
} from '#/api/delivery-matrix';

const emit = defineEmits<{
  add: [type: 'component' | 'domain' | 'group', parentNode?: DeliveryTreeNode];
  select: [node: DeliveryTreeNode | undefined];
}>();

const treeData = ref<DeliveryTreeNode[]>([]);
const loading = ref(false);
const selectedNodeId = ref<string>();
const searchKeyword = ref('');
const expandedIds = ref<Set<string>>(new Set());
const hoveredNodeId = ref<string>();

const filteredTreeData = computed(() => {
  if (!searchKeyword.value) return treeData.value;
  // Simple filter logic - recursive filter could be better but for now flatten search is ok or just filter top level
  // Let's implement a simple search that expands path
  return filterTree(treeData.value, searchKeyword.value);
});

function filterTree(
  nodes: DeliveryTreeNode[],
  keyword: string,
): DeliveryTreeNode[] {
  return nodes.reduce((acc: DeliveryTreeNode[], node) => {
    const matches = node.name.toLowerCase().includes(keyword.toLowerCase());
    const children = node.children ? filterTree(node.children, keyword) : [];

    if (matches || children.length > 0) {
      acc.push({ ...node, children });
      if (children.length > 0) {
        expandedIds.value.add(node.id);
      }
    }
    return acc;
  }, []);
}

const flattenedTree = computed(() => {
  const result: { level: number; node: DeliveryTreeNode }[] = [];
  const traverse = (nodes: DeliveryTreeNode[], level: number) => {
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
    treeData.value = await getAdminTree();
  } finally {
    loading.value = false;
  }
}

function toggleExpand(node: DeliveryTreeNode) {
  if (expandedIds.value.has(node.id)) {
    expandedIds.value.delete(node.id);
  } else {
    expandedIds.value.add(node.id);
  }
}

function onSelect(node: DeliveryTreeNode) {
  selectedNodeId.value = node.id;
  emit('select', node);
}

function onAdd(
  type: 'component' | 'domain' | 'group',
  parentNode?: DeliveryTreeNode,
) {
  emit('add', type, parentNode);
}

async function onDelete(node: DeliveryTreeNode) {
  try {
    switch (node.type) {
      case 'component': {
        {
          await deleteComponent(node.real_id);
          // No default
        }
        break;
      }
      case 'domain': {
        await deleteDomain(node.real_id);
        break;
      }
      case 'group': {
        await deleteGroup(node.real_id);
        break;
      }
    }

    await fetchTree();
    if (selectedNodeId.value === node.id) {
      selectedNodeId.value = undefined;
      emit('select', undefined);
    }
  } catch (error) {
    console.error(error);
  }
}

defineExpose({
  refresh: fetchTree,
  refreshNode: fetchTree, // For now just refresh all, optimization later
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
      <!-- Domain Add Button -->
      <!-- Only allow adding domain from top level? Yes -->
      <!-- But user said "Domain doesn't need CRUD interfaces", but let's keep it for completeness but hidden or restricted if needed.
           Wait, user said: "In management page, domain doesn't need CRUD interfaces because there are only two domains...".
           So maybe disable adding domains? Or just hide the button.
           "Left side is Domain Tree -> Project Group -> Component".
           So we need to allow adding Groups and Components.
      -->
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

              <!-- Icon based on type -->
              <IconifyIcon
                :icon="
                  item.node.type === 'domain'
                    ? 'carbon:enterprise'
                    : item.node.type === 'group'
                      ? 'carbon:folder'
                      : 'carbon:cube'
                "
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
                  v-if="item.node.type !== 'component'"
                >
                  <ElButton
                    link
                    type="primary"
                    size="small"
                    @click="
                      onAdd(
                        item.node.type === 'domain' ? 'group' : 'component',
                        item.node,
                      )
                    "
                  >
                    <IconifyIcon icon="ep:plus" />
                  </ElButton>
                </ElTooltip>
                <ElTooltip content="删除" v-if="item.node.type !== 'domain'">
                  <!-- Disable deleting domain per user request (implied) -->
                  <ElButton
                    link
                    type="danger"
                    size="small"
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
