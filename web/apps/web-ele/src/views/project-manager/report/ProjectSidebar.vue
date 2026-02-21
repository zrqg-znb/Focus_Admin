<script lang="ts" setup>
import type { PlatformConfig } from '#/api/project-manager/hardware';
import type { ProjectOut } from '#/api/project-manager/project';

import { computed, onMounted, ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';

import { ElEmpty, ElInput, ElScrollbar, ElTree } from 'element-plus';

import {
  listCdcPlatformsApi,
  listViuPlatformsApi,
} from '#/api/project-manager/hardware';
import { listProjectsApi } from '#/api/project-manager/project';

defineProps<{
  currentId?: string;
}>();

const emit = defineEmits<{
  (e: 'select', projectId: string): void;
}>();

const loading = ref(false);
const filterText = ref('');
const treeRef = ref<InstanceType<typeof ElTree>>();
const projects = ref<ProjectOut[]>([]);
const viuPlatforms = ref<PlatformConfig[]>([]);
const cdcPlatforms = ref<PlatformConfig[]>([]);

// Tree Data Structure
interface TreeNode {
  id: string;
  label: string;
  type: 'category' | 'platform' | 'project';
  children?: TreeNode[];
  data?: ProjectOut;
}

type DomainType = 'cockpit' | 'other' | 'vehicle';

const UNCONFIGURED_LABEL = '未配置';

function getDomainType(domain: string): DomainType {
  if (domain.includes('车控')) return 'vehicle';
  if (domain.includes('座舱')) return 'cockpit';
  return 'other';
}

function getCockpitPlatformName(project: ProjectOut) {
  const cockpitPhase = (project.phase_configs || []).find(
    (phase) => phase.scenario === 'cockpit' && phase.cdc_platform_name,
  );
  if (cockpitPhase?.cdc_platform_name) return cockpitPhase.cdc_platform_name;
  const anyPhase = (project.phase_configs || []).find(
    (phase) => !!phase.cdc_platform_name,
  );
  return anyPhase?.cdc_platform_name || '';
}

function getSecondLevelCategory(project: ProjectOut, domainType: DomainType) {
  if (domainType === 'vehicle') {
    return project.viu_platform_name?.trim() || UNCONFIGURED_LABEL;
  }
  if (domainType === 'cockpit') {
    return getCockpitPlatformName(project).trim() || UNCONFIGURED_LABEL;
  }
  return '';
}

function sortCategoryName(a: string, b: string) {
  if (a === UNCONFIGURED_LABEL && b !== UNCONFIGURED_LABEL) return 1;
  if (b === UNCONFIGURED_LABEL && a !== UNCONFIGURED_LABEL) return -1;
  return a.localeCompare(b, 'zh-CN');
}

const treeData = computed<TreeNode[]>(() => {
  const groups: Record<
    string,
    {
      domainType: DomainType;
      projects: ProjectOut[];
    }
  > = {};

  projects.value.forEach((project) => {
    const domainName = project.domain || '未分类';
    if (!groups[domainName]) {
      groups[domainName] = {
        domainType: getDomainType(domainName),
        projects: [],
      };
    }
    groups[domainName].projects.push(project);
  });

  return Object.entries(groups)
    .sort(([domainA], [domainB]) => domainA.localeCompare(domainB, 'zh-CN'))
    .map(([domainName, group]) => {
      const domainType = group.domainType;
      const domainNode: TreeNode = {
        id: `domain-${domainName}`,
        label: domainName,
        type: 'category',
        children: [],
      };

      if (domainType === 'other') {
        domainNode.children = [...group.projects]
          .sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
          .map((project) => ({
            id: project.id,
            label: project.name,
            type: 'project',
            data: project,
          }));
        return domainNode;
      }

      const configuredCategories =
        domainType === 'vehicle'
          ? viuPlatforms.value.map((platform) => platform.name)
          : cdcPlatforms.value.map((platform) => platform.name);
      const categoryMap: Record<string, ProjectOut[]> = {};
      for (const name of configuredCategories) {
        categoryMap[name] = [];
      }
      categoryMap[UNCONFIGURED_LABEL] = [];

      for (const project of group.projects) {
        const categoryName = getSecondLevelCategory(project, domainType);
        const finalCategory = categoryName || UNCONFIGURED_LABEL;
        if (!categoryMap[finalCategory]) {
          categoryMap[finalCategory] = [];
        }
        categoryMap[finalCategory].push(project);
      }

      domainNode.children = Object.keys(categoryMap)
        .sort(sortCategoryName)
        .map((categoryName) => ({
          id: `${domainName}-${categoryName}`,
          label: categoryName,
          type: 'platform',
          children: [...categoryMap[categoryName]]
            .sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
            .map((project) => ({
              id: project.id,
              label: project.name,
              type: 'project',
              data: project,
            })),
        }));

      return domainNode;
    });
});

watch(filterText, (val) => {
  treeRef.value?.filter(val);
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
    const [projectRes, viuRes, cdcRes] = await Promise.all([
      listProjectsApi({ pageSize: 1000, is_closed: false }),
      listViuPlatformsApi(),
      listCdcPlatformsApi(),
    ]);
    projects.value = projectRes.items || [];
    viuPlatforms.value = viuRes || [];
    cdcPlatforms.value = cdcRes || [];
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
  <div
    class="flex h-full flex-col overflow-hidden rounded-l-xl border-r border-gray-200 bg-white dark:border-gray-800 dark:bg-[#151515]"
  >
    <!-- Search Header -->
    <div class="border-b border-gray-100 p-4 dark:border-gray-800">
      <div class="mb-3 flex items-center gap-2">
        <IconifyIcon icon="lucide:folder-kanban" class="text-primary" />
        <span class="text-base font-bold">项目列表</span>
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
    <div class="relative flex-1 overflow-hidden">
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
            <div class="flex w-full items-center gap-2 overflow-hidden">
              <IconifyIcon
                v-if="data.type === 'category'"
                icon="lucide:folder"
                class="flex-shrink-0 text-gray-400"
              />
              <IconifyIcon
                v-else-if="data.type === 'platform'"
                icon="lucide:layers"
                class="flex-shrink-0 text-amber-500"
              />
              <IconifyIcon
                v-else
                icon="lucide:box"
                class="flex-shrink-0 text-blue-500"
              />
              <span
                class="truncate text-sm"
                :class="{ 'font-medium': data.type === 'category' }"
              >
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
:deep(
  .el-tree--highlight-current .el-tree-node.is-current > .el-tree-node__content
) {
  background-color: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}
.dark
  :deep(
    .el-tree--highlight-current
      .el-tree-node.is-current
      > .el-tree-node__content
  ) {
  background-color: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  /* Dark mode specific adjustment if needed */
  background-color: rgba(var(--el-color-primary-rgb), 0.2);
}
</style>
