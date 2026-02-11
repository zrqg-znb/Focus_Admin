<script setup lang="ts">
import type { OrgNode } from '#/api/delivery-matrix';

import { computed, onMounted, ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';
import {
  ElButton,
  ElInput,
  ElPopover,
  ElSkeleton,
  ElSkeletonItem,
  ElTag,
  ElTree,
} from 'element-plus';

import { getTree } from '#/api/delivery-matrix';

type MaybeId = string | null | undefined;

const props = defineProps<{
  modelValue?: MaybeId;
  placeholder?: string;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', v: MaybeId): void;
  (e: 'change', v: MaybeId): void;
}>();

const visible = ref(false);
const loading = ref(false);
const treeData = ref<OrgNode[]>([]);
const searchKeyword = ref('');
const expandedIds = ref<Set<string>>(new Set());

const selectedNode = computed(() =>
  findNode(treeData.value, props.modelValue || undefined),
);

function highlight(text: string, keyword: string) {
  if (!keyword) return text;
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const reg = new RegExp(escaped, 'ig');
  return text.replace(reg, (m) => `<mark class="bg-yellow-200 text-gray-900">${m}</mark>`);
}

function filterTreeByKeyword(nodes: OrgNode[], keyword: string) {
  const q = keyword.trim().toLowerCase();
  const expanded = new Set<string>();

  const mapNode = (node: OrgNode): OrgNode & { __matched?: boolean } | null => {
    const selfMatch = node.name.toLowerCase().includes(q);
    const children = (node.children || [])
      .map(mapNode)
      .filter(Boolean) as OrgNode[];

    if (!q || selfMatch || children.length) {
      const copy: OrgNode & { __matched?: boolean } = {
        ...node,
        children,
      };
      if (selfMatch) copy.__matched = true;
      if (children.length) expanded.add(node.id);
      return copy;
    }
    return null;
  };

  return { filtered: nodes.map(mapNode).filter(Boolean) as OrgNode[], expanded };
}

const filteredTree = computed(() => {
  const { filtered, expanded } = filterTreeByKeyword(treeData.value, searchKeyword.value);
  expandedIds.value = expanded;
  return filtered;
});

async function loadTree() {
  loading.value = true;
  try {
    treeData.value = await getTree();
  } finally {
    loading.value = false;
  }
}

function findNode(nodes: OrgNode[], id?: string): OrgNode | undefined {
  if (!id) return undefined;
  for (const n of nodes) {
    if (n.id === id) return n;
    if (n.children) {
      const hit = findNode(n.children, id);
      if (hit) return hit;
    }
  }
  return undefined;
}

function onSelect(node: OrgNode) {
  emit('update:modelValue', node.id);
  emit('change', node.id);
  visible.value = false;
}

function onSetRoot() {
  emit('update:modelValue', null);
  emit('change', null);
  visible.value = false;
}

function onClear() {
  emit('update:modelValue', null);
  emit('change', null);
}

function defaultPlaceholder() {
  return props.placeholder || '请选择上级节点（留空为根节点）';
}

onMounted(loadTree);

watch(
  () => visible.value,
  (show) => {
    if (show && treeData.value.length === 0 && !loading.value) {
      loadTree();
    }
  },
);
</script>

<template>
  <div class="w-full">
    <div class="flex items-center gap-2">
      <div
        class="flex min-h-[38px] flex-1 items-center justify-between rounded-lg border border-gray-200 bg-white px-3 text-sm shadow-sm transition hover:border-primary/60"
      >
        <div class="flex flex-1 items-center gap-2">
          <IconifyIcon icon="carbon:tree-view" class="text-gray-400" />
          <span v-if="selectedNode" class="truncate text-gray-800">
            {{ selectedNode.name }}
          </span>
          <span v-else class="text-gray-400">{{ defaultPlaceholder() }}</span>
        </div>
        <div class="flex items-center gap-1">
          <ElButton v-if="modelValue" link size="small" @click="onClear">清除</ElButton>
          <ElPopover
            v-model:visible="visible"
            trigger="click"
            width="360px"
            popper-class="dm-parent-popover"
          >
            <template #reference>
              <ElButton type="primary" plain size="small">
                选择
              </ElButton>
            </template>
            <div class="space-y-3">
              <div class="rounded-lg bg-gradient-to-r from-sky-50 to-purple-50 p-3">
                <div class="flex items-center justify-between text-sm text-gray-700">
                  <div class="flex items-center gap-2">
                    <IconifyIcon icon="carbon:parent-child" class="text-base text-primary" />
                    <span>选择父节点</span>
                  </div>
                  <ElTag size="small" effect="light" type="info">留空为根节点</ElTag>
                </div>
                <div class="mt-2 flex flex-wrap gap-2">
                  <ElButton size="small" type="success" plain @click="onSetRoot">
                    <IconifyIcon icon="carbon:home" class="mr-1" />
                    设为根节点
                  </ElButton>
                </div>
              </div>

              <ElInput
                v-model="searchKeyword"
                placeholder="搜索节点名称"
                clearable
                :prefix-icon="'carbon:search'"
              />

              <div class="max-h-64 overflow-y-auto rounded-lg border border-gray-100 bg-white p-2">
                <ElSkeleton :loading="loading" animated :count="6">
                  <template #template>
                    <div v-for="i in 6" :key="i" class="py-2">
                      <ElSkeletonItem variant="text" style="width: 100%" />
                    </div>
                  </template>
                  <ElTree
                    :data="filteredTree"
                    node-key="id"
                    :default-expanded-keys="[...expandedIds]"
                    highlight-current
                    :props="{ label: 'name', children: 'children' }"
                    @node-click="onSelect"
                  >
                    <template #default="{ data }">
                      <span
                        class="flex items-center gap-2"
                        :class="{ 'font-semibold text-primary': (data as any).__matched }"
                        v-html="highlight(data.name, searchKeyword)"
                      ></span>
                    </template>
                  </ElTree>
                </ElSkeleton>
              </div>
            </div>
          </ElPopover>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dm-parent-popover {
  padding: 12px;
}
</style>
