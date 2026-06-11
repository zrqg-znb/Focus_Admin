<script lang="ts" setup>
import type {
  BranchRepositoryOrganizationItem,
  BranchRepositoryRelation,
  RepositoryItem,
} from '#/api/compliance/base';

import { computed, ref, watch } from 'vue';

import {
  ElDialog,
  ElEmpty,
  ElPagination,
  ElSkeleton,
  ElTag,
  ElTree,
} from 'element-plus';

import { getBranchRepositoriesApi } from '#/api/compliance/base';

const props = defineProps<{
  branchId?: string;
  modelValue: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
}>();

const loading = ref(false);
const relation = ref<BranchRepositoryRelation>();
const selectedOrganizationId = ref('');
const repositoryPage = ref(1);
const repositoryPageSize = ref(8);

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});

const selectedOrganization = computed(() =>
  findOrganization(relation.value?.organizations || [], selectedOrganizationId.value),
);

const selectedRepositories = computed<RepositoryItem[]>(() =>
  selectedOrganization.value?.repositories || [],
);
const pagedRepositories = computed(() => {
  const start = (repositoryPage.value - 1) * repositoryPageSize.value;
  return selectedRepositories.value.slice(start, start + repositoryPageSize.value);
});

function findFirstOrganization(
  nodes: BranchRepositoryOrganizationItem[],
): BranchRepositoryOrganizationItem | undefined {
  // 弹窗打开时默认定位到第一条真实绑定路径，减少用户空看一屏的概率。
  for (const node of nodes) {
    if (node.id) return node;
    const child = findFirstOrganization(node.children || []);
    if (child) return child;
  }
}

function findOrganization(
  nodes: BranchRepositoryOrganizationItem[],
  id: string,
): BranchRepositoryOrganizationItem | undefined {
  for (const node of nodes) {
    if (node.id === id) return node;
    const child = findOrganization(node.children || [], id);
    if (child) return child;
  }
}

function repositorySummary(nodes: BranchRepositoryOrganizationItem[]): number {
  return nodes.reduce((count, node) => {
    return count + node.repositories.length + repositorySummary(node.children || []);
  }, 0);
}

async function loadRelation() {
  if (!props.modelValue || !props.branchId) return;
  loading.value = true;
  try {
    relation.value = await getBranchRepositoriesApi(props.branchId);
    selectedOrganizationId.value =
      findFirstOrganization(relation.value.organizations)?.id || '';
    repositoryPage.value = 1;
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.modelValue, props.branchId],
  () => {
    if (props.modelValue) {
      loadRelation();
    } else {
      relation.value = undefined;
      selectedOrganizationId.value = '';
      repositoryPage.value = 1;
    }
  },
);

watch(selectedOrganizationId, () => {
  repositoryPage.value = 1;
});
</script>

<template>
  <ElDialog
    v-model="visible"
    width="980px"
    destroy-on-close
    class="branch-relation-dialog"
    title="分支关联代码库"
  >
    <ElSkeleton :loading="loading" animated>
      <template v-if="relation">
        <div class="relation-header">
          <div>
            <div class="relation-title">{{ relation.branch.branch_name }}</div>
            <div class="relation-meta">
              {{ relation.branch.branch_type_label }} / {{ relation.branch.domain_label }}
              <span v-if="relation.branch.alias"> / {{ relation.branch.alias }}</span>
            </div>
          </div>
          <div class="relation-stat">
            <span>关联代码库</span>
            <strong>{{ repositorySummary(relation.organizations) }}</strong>
          </div>
        </div>

        <div v-if="relation.organizations.length" class="relation-workbench">
          <aside class="relation-tree">
            <div class="aside-title">组织路径</div>
            <ElTree
              node-key="id"
              :data="relation.organizations"
              :default-expand-all="true"
              :current-node-key="selectedOrganizationId"
              highlight-current
              @node-click="(node) => (selectedOrganizationId = node.id)"
            >
              <template #default="{ data }">
                <div class="tree-node">
                  <span class="tree-node-name">{{ data.name }}</span>
                  <ElTag size="small" type="info">{{ data.repository_count }}</ElTag>
                </div>
              </template>
            </ElTree>
          </aside>

          <section class="repository-panel">
            <div class="panel-title">
              <div>
                <span>{{ selectedOrganization?.name || '请选择组织' }}</span>
                <small>{{ selectedRepositories.length }} 个直接关联代码库</small>
              </div>
              <ElTag size="small" type="primary">Direct Repos</ElTag>
            </div>
            <div v-if="selectedRepositories.length" class="repository-list">
              <div
                v-for="repo in pagedRepositories"
                :key="repo.id"
                class="repository-row"
              >
                <div class="repo-main">
                  <strong>{{ repo.project_name }}</strong>
                  <span>{{ repo.project_id }}</span>
                </div>
                <div class="repo-tags">
                  <ElTag size="small">{{ repo.domain_label }}</ElTag>
                  <ElTag size="small" type="success">{{ repo.repo_type_label || '未分类' }}</ElTag>
                  <ElTag
                    v-for="group in repo.responsibility_group_names"
                    :key="group"
                    size="small"
                    type="warning"
                  >
                    {{ group }}
                  </ElTag>
                </div>
              </div>
              <ElPagination
                v-if="selectedRepositories.length > repositoryPageSize"
                v-model:current-page="repositoryPage"
                v-model:page-size="repositoryPageSize"
                background
                class="relation-pagination"
                layout="total, prev, pager, next, sizes"
                :page-sizes="[6, 8, 12, 20]"
                :total="selectedRepositories.length"
              />
            </div>
            <ElEmpty v-else description="该组织下没有直接关联代码库" />
          </section>
        </div>

        <ElEmpty v-else description="该分支暂未绑定代码库" />
      </template>
    </ElSkeleton>
  </ElDialog>
</template>

<style scoped lang="less">
.relation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: linear-gradient(180deg, var(--el-fill-color-extra-light), var(--el-bg-color));
}

.relation-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.relation-meta {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.relation-stat {
  min-width: 104px;
  padding: 9px 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  text-align: right;
  background: var(--el-fill-color-extra-light);
}

.relation-stat span {
  display: block;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.relation-stat strong {
  font-size: 24px;
  line-height: 1.2;
}

.relation-workbench {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 12px;
  min-height: 420px;
  padding-top: 14px;
}

.relation-tree,
.repository-panel {
  min-width: 0;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-bg-color);
}

.relation-tree {
  padding: 10px;
  overflow: auto;
  background:
    linear-gradient(90deg, var(--el-fill-color-extra-light), transparent 42%),
    var(--el-bg-color);
}

.aside-title {
  margin-bottom: 8px;
  padding: 0 4px 8px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  font-size: 12px;
  font-weight: 700;
  color: var(--el-text-color-regular);
}

.tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 8px;
}

.tree-node-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.repository-panel {
  padding: 14px;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  font-weight: 600;
}

.panel-title small {
  display: block;
  margin-top: 3px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.repository-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.repository-row {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) minmax(260px, 1.4fr);
  gap: 12px;
  align-items: center;
  padding: 11px 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-fill-color-extra-light);
  transition:
    border-color 0.16s ease,
    transform 0.16s ease;
}

.repository-row:hover {
  border-color: var(--el-color-primary-light-5);
  transform: translateY(-1px);
}

.repo-main strong,
.repo-main span {
  display: block;
}

.repo-main span {
  margin-top: 3px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.repo-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.relation-pagination {
  justify-content: flex-end;
  margin-top: 12px;
}

@media (max-width: 900px) {
  .relation-workbench,
  .repository-row {
    grid-template-columns: 1fr;
  }

  .repo-tags {
    justify-content: flex-start;
  }
}
</style>
