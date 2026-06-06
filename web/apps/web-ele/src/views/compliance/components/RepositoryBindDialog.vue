<script lang="ts" setup>
import type {
  ComplianceBindMode,
  OrganizationItem,
  RepositoryItem,
} from '#/api/compliance/base';

import { computed, ref, watch } from 'vue';

import { Search, Trash2 } from '@vben/icons';

import {
  ElBreadcrumb,
  ElBreadcrumbItem,
  ElButton,
  ElCheckbox,
  ElDialog,
  ElEmpty,
  ElInput,
  ElPagination,
  ElRadioButton,
  ElRadioGroup,
  ElScrollbar,
  ElTag,
  ElTree,
} from 'element-plus';

import {
  listOrganizationsApi,
  listRepositoriesApi,
} from '#/api/compliance/base';

const BIND_MODE_OPTIONS: Array<{ label: string; value: ComplianceBindMode }> = [
  { label: '追加绑定', value: 'append' },
  { label: '替换绑定', value: 'replace' },
];

interface OrganizationTreeNode extends OrganizationItem {
  children?: OrganizationTreeNode[];
}

interface ConfirmPayload {
  mode: ComplianceBindMode;
  repository_ids: string[];
}

const props = withDefaults(
  defineProps<{
    confirmLoading?: boolean;
    modelValue: boolean;
  }>(),
  {
    confirmLoading: false,
  },
);

const emit = defineEmits<{
  (event: 'confirm', payload: ConfirmPayload): void;
  (event: 'update:modelValue', value: boolean): void;
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
});

const treeProps = { children: 'children', label: 'name' };
const mode = ref<ComplianceBindMode>('append');
const organizationKeyword = ref('');
const repositoryKeyword = ref('');
const selectedOrganizationId = ref('');
const organizationTree = ref<OrganizationTreeNode[]>([]);
const repositoryRows = ref<RepositoryItem[]>([]);
const repositoryTotal = ref(0);
const repositoryPage = ref(1);
const repositoryPageSize = ref(10);
const organizationLoading = ref(false);
const repositoryLoading = ref(false);
const selectedMap = ref<Record<string, RepositoryItem>>({});

const selectedIds = computed(() => Object.keys(selectedMap.value));
const selectedSet = computed(() => new Set(selectedIds.value));

const filteredOrganizationTree = computed(() =>
  filterOrganizationTree(organizationTree.value, organizationKeyword.value),
);

const selectedOrganizationPath = computed(() =>
  findOrganizationPath(organizationTree.value, selectedOrganizationId.value),
);

const selectedGroups = computed(() => {
  const grouped = new Map<
    string,
    { id: string; name: string; rows: RepositoryItem[] }
  >();
  Object.values(selectedMap.value).forEach((item) => {
    const key = item.organization_id || 'unknown';
    if (!grouped.has(key)) {
      grouped.set(key, {
        id: key,
        name: item.organization_name || '未归属组织',
        rows: [],
      });
    }
    grouped.get(key)!.rows.push(item);
  });
  return [...grouped.values()].map((group) => ({
    ...group,
    rows: group.rows.sort((left, right) =>
      left.project_name.localeCompare(right.project_name, 'zh-CN'),
    ),
  }));
});

const candidateTitle = computed(() => {
  if (selectedOrganizationPath.value.length > 0) {
    return (
      selectedOrganizationPath.value[selectedOrganizationPath.value.length - 1]
        ?.name || '当前组织'
    );
  }
  return repositoryKeyword.value.trim() ? '全局代码库搜索' : '选择组织';
});

const candidateHint = computed(() => {
  if (selectedOrganizationPath.value.length > 0) {
    return '展示当前组织直接关联的代码库，可继续切换组织进行跨组织选择。';
  }
  if (repositoryKeyword.value.trim()) {
    return '未限定组织时按关键词进行全局搜索。';
  }
  return '先从左侧组织树进入组织，或输入代码库关键词开始搜索。';
});

function normalizeKeyword(value: string) {
  return value.trim().toLowerCase();
}

function filterOrganizationTree(
  nodes: OrganizationTreeNode[],
  keyword: string,
): OrganizationTreeNode[] {
  // 保留命中组织及其祖先路径，避免搜索后组织层级丢失。
  const word = normalizeKeyword(keyword);
  if (!word) return nodes;
  const result: OrganizationTreeNode[] = [];
  for (const node of nodes) {
    const children = filterOrganizationTree(node.children || [], keyword);
    const matched = `${node.name} ${node.group_id}`
      .toLowerCase()
      .includes(word);
    if (matched || children.length > 0) {
      result.push({ ...node, children });
    }
  }
  return result;
}

function findOrganizationPath(
  nodes: OrganizationTreeNode[],
  id: string,
  parents: OrganizationTreeNode[] = [],
): OrganizationTreeNode[] {
  // 按组织树真实层级生成面包屑路径。
  if (!id) return [];
  for (const node of nodes) {
    const path = [...parents, node];
    if (node.id === id) return path;
    const childPath = findOrganizationPath(node.children || [], id, path);
    if (childPath.length > 0) return childPath;
  }
  return [];
}

async function loadOrganizations() {
  organizationLoading.value = true;
  try {
    organizationTree.value = await listOrganizationsApi();
  } finally {
    organizationLoading.value = false;
  }
}

async function loadRepositories(resetPage = false) {
  if (resetPage) repositoryPage.value = 1;
  const keyword = repositoryKeyword.value.trim();
  if (!selectedOrganizationId.value && !keyword) {
    repositoryRows.value = [];
    repositoryTotal.value = 0;
    return;
  }
  repositoryLoading.value = true;
  try {
    const result = await listRepositoriesApi({
      keyword: keyword || undefined,
      organization_id: selectedOrganizationId.value || undefined,
      page: repositoryPage.value,
      pageSize: repositoryPageSize.value,
    });
    repositoryRows.value = result.items || [];
    repositoryTotal.value = result.total || 0;
  } finally {
    repositoryLoading.value = false;
  }
}

function resetDialog() {
  mode.value = 'append';
  organizationKeyword.value = '';
  repositoryKeyword.value = '';
  selectedOrganizationId.value = '';
  repositoryRows.value = [];
  repositoryTotal.value = 0;
  repositoryPage.value = 1;
  repositoryPageSize.value = 10;
  selectedMap.value = {};
}

async function selectOrganization(node: OrganizationTreeNode) {
  selectedOrganizationId.value = node.id;
  await loadRepositories(true);
}

function clearOrganization() {
  selectedOrganizationId.value = '';
  loadRepositories(true);
}

function toggleRepository(item: RepositoryItem, checked: boolean) {
  // 用对象快照维护跨页选择，避免分页刷新后丢失已选代码库。
  const next = { ...selectedMap.value };
  if (checked) {
    next[item.id] = item;
  } else {
    delete next[item.id];
  }
  selectedMap.value = next;
}

function selectCurrentPage() {
  // 批量操作只作用于当前页，同时保留其他组织和其他页已选项。
  const next = { ...selectedMap.value };
  repositoryRows.value.forEach((item) => {
    next[item.id] = item;
  });
  selectedMap.value = next;
}

function clearCurrentPage() {
  // 清空当前页不会影响跨组织保存在右侧清单里的其他选择。
  const next = { ...selectedMap.value };
  repositoryRows.value.forEach((item) => {
    delete next[item.id];
  });
  selectedMap.value = next;
}

function clearAllSelected() {
  selectedMap.value = {};
}

function handleRepositoryPageChange() {
  loadRepositories();
}

function handleRepositoryPageSizeChange() {
  loadRepositories(true);
}

function toggleRepositoryByCard(item: RepositoryItem) {
  toggleRepository(item, !selectedSet.value.has(item.id));
}

function confirmSelection() {
  emit('confirm', {
    mode: mode.value,
    repository_ids: selectedIds.value,
  });
}

watch(
  () => props.modelValue,
  async (show) => {
    if (!show) return;
    resetDialog();
    await loadOrganizations();
  },
);
</script>

<template>
  <ElDialog
    v-model="visible"
    append-to-body
    class="compliance-bind-dialog"
    destroy-on-close
    top="4vh"
    width="min(1180px, calc(100vw - 32px))"
    :close-on-click-modal="false"
  >
    <template #header>
      <div class="bind-title">
        <div>
          <div class="bind-title__main">批量绑定代码库</div>
          <div class="bind-title__sub">先进入组织，再选择需要绑定到当前分支的代码库。</div>
        </div>
        <ElRadioGroup v-model="mode" class="bind-mode-switch">
          <ElRadioButton
            v-for="item in BIND_MODE_OPTIONS"
            :key="item.value"
            :label="item.value"
          >
            {{ item.label }}
          </ElRadioButton>
        </ElRadioGroup>
      </div>
    </template>

    <div class="repository-bind-workbench">
      <section class="bind-panel organization-panel">
        <div class="bind-panel__header">
          <span>组织导航</span>
          <ElTag size="small" effect="plain">{{ organizationTree.length }} 个根组织</ElTag>
        </div>
        <ElInput
          v-model="organizationKeyword"
          clearable
          class="bind-search"
          placeholder="搜索组织 / Group ID"
          :prefix-icon="Search"
        />
        <div class="organization-tree-wrap">
          <ElTree
            v-loading="organizationLoading"
            :data="filteredOrganizationTree"
            default-expand-all
            node-key="id"
            :props="treeProps"
            :current-node-key="selectedOrganizationId"
            :expand-on-click-node="false"
            highlight-current
            @node-click="selectOrganization"
          >
            <template #default="{ data }">
              <div class="organization-node">
                <span class="organization-node__name">{{ data.name }}</span>
                <ElTag size="small" effect="plain">{{ data.repository_count }}</ElTag>
              </div>
            </template>
          </ElTree>
          <ElEmpty
            v-if="!organizationLoading && filteredOrganizationTree.length === 0"
            description="未找到组织"
            :image-size="72"
          />
        </div>
      </section>

      <section class="bind-panel candidate-panel">
        <div class="candidate-heading">
          <div>
            <div class="candidate-title">{{ candidateTitle }}</div>
            <div class="candidate-hint">{{ candidateHint }}</div>
          </div>
          <ElButton v-if="selectedOrganizationId" text @click="clearOrganization">
            全局搜索
          </ElButton>
        </div>

        <ElBreadcrumb
          v-if="selectedOrganizationPath.length > 0"
          class="organization-breadcrumb"
          separator="/"
        >
          <ElBreadcrumbItem
            v-for="item in selectedOrganizationPath"
            :key="item.id"
          >
            <button class="breadcrumb-link" @click="selectOrganization(item)">
              {{ item.name }}
            </button>
          </ElBreadcrumbItem>
        </ElBreadcrumb>

        <div class="candidate-toolbar">
          <ElInput
            v-model="repositoryKeyword"
            clearable
            placeholder="搜索代码库名 / Project ID / URL"
            :prefix-icon="Search"
            @clear="loadRepositories(true)"
            @keyup.enter="loadRepositories(true)"
          />
          <ElButton @click="loadRepositories(true)">查询</ElButton>
        </div>

        <div class="candidate-actions">
          <div class="candidate-count">当前结果 {{ repositoryTotal }} 个，已选 {{ selectedIds.length }} 个</div>
          <div class="candidate-action-buttons">
            <ElButton :disabled="!repositoryRows.length" @click="selectCurrentPage">
              全选当前页
            </ElButton>
            <ElButton :disabled="!repositoryRows.length" @click="clearCurrentPage">
              清空当前页
            </ElButton>
          </div>
        </div>

        <ElScrollbar class="candidate-list">
          <div v-if="repositoryRows.length" class="candidate-list__inner">
            <div
              v-for="item in repositoryRows"
              :key="item.id"
              class="repository-card"
              :class="{ 'is-selected': selectedSet.has(item.id) }"
              role="button"
              tabindex="0"
              @click="toggleRepositoryByCard(item)"
              @keydown.enter.prevent="toggleRepositoryByCard(item)"
              @keydown.space.prevent="toggleRepositoryByCard(item)"
            >
              <ElCheckbox
                :model-value="selectedSet.has(item.id)"
                @click.stop
                @change="(checked) => toggleRepository(item, !!checked)"
              />
              <div class="repository-card__body">
                <div class="repository-card__title">
                  <span>{{ item.project_name }}</span>
                  <ElTag size="small" effect="plain">{{ item.project_id }}</ElTag>
                </div>
                <div class="repository-card__meta">
                  <span>{{ item.organization_name }}</span>
                  <span>{{ item.domain_label }}</span>
                  <span>{{ item.mode_label }}</span>
                  <span>分支 {{ item.branch_count }}</span>
                </div>
                <div class="repository-card__url">{{ item.project_url || '-' }}</div>
              </div>
            </div>
          </div>
          <ElEmpty
            v-else
            :description="
              selectedOrganizationId || repositoryKeyword
                ? '暂无匹配代码库'
                : '请选择组织或输入关键词'
            "
            :image-size="86"
          />
        </ElScrollbar>

        <div class="candidate-pagination">
          <ElPagination
            v-model:current-page="repositoryPage"
            v-model:page-size="repositoryPageSize"
            :total="repositoryTotal"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            small
            @current-change="handleRepositoryPageChange"
            @size-change="handleRepositoryPageSizeChange"
          />
        </div>
      </section>

      <aside class="bind-panel selected-panel">
        <div class="bind-panel__header">
          <span>已选代码库</span>
          <ElTag type="success" size="small" effect="light">{{ selectedIds.length }}</ElTag>
        </div>
        <div class="selected-actions">
          <ElButton text type="danger" :disabled="!selectedIds.length" @click="clearAllSelected">
            清空全部
          </ElButton>
        </div>
        <ElScrollbar class="selected-list">
          <div v-if="selectedGroups.length" class="selected-list__inner">
            <div
              v-for="group in selectedGroups"
              :key="group.id"
              class="selected-group"
            >
              <div class="selected-group__title">
                <span>{{ group.name }}</span>
                <ElTag size="small" effect="plain">{{ group.rows.length }}</ElTag>
              </div>
              <div
                v-for="item in group.rows"
                :key="item.id"
                class="selected-item"
              >
                <div class="selected-item__main">
                  <span class="selected-item__name">{{ item.project_name }}</span>
                  <span class="selected-item__id">{{ item.project_id }}</span>
                </div>
                <ElButton
                  circle
                  text
                  type="danger"
                  @click="toggleRepository(item, false)"
                >
                  <Trash2 class="size-4" />
                </ElButton>
              </div>
            </div>
          </div>
          <ElEmpty v-else description="暂无选中代码库" :image-size="74" />
        </ElScrollbar>
      </aside>
    </div>

    <template #footer>
      <div class="bind-footer">
        <span>确认后将以当前绑定方式作用于已勾选分支。</span>
        <div>
          <ElButton @click="visible = false">取消</ElButton>
          <ElButton
            type="primary"
            :disabled="!selectedIds.length"
            :loading="confirmLoading"
            @click="confirmSelection"
          >
            确定绑定
          </ElButton>
        </div>
      </div>
    </template>
  </ElDialog>
</template>

<style scoped lang="less">
.bind-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.bind-title__main {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.bind-title__sub,
.candidate-hint,
.candidate-count,
.bind-footer,
.repository-card__meta,
.repository-card__url,
.selected-item__id {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.repository-bind-workbench {
  display: grid;
  grid-template-columns: 260px minmax(420px, 1fr) 300px;
  gap: 12px;
  height: 640px;
  min-height: 0;
}

.bind-panel {
  min-width: 0;
  min-height: 0;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-bg-color);
}

.organization-panel,
.candidate-panel,
.selected-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.bind-panel__header,
.candidate-heading,
.candidate-actions,
.selected-actions,
.bind-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.bind-panel__header,
.candidate-heading {
  padding: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  font-weight: 600;
}

.bind-search,
.candidate-toolbar {
  margin: 12px;
}

.candidate-toolbar {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) auto;
  gap: 8px;
}

.organization-tree-wrap,
.candidate-list,
.selected-list {
  flex: 1;
  min-height: 0;
}

.organization-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-width: 0;
  gap: 8px;
  padding-right: 6px;
}

.organization-node__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.organization-breadcrumb {
  padding: 10px 12px 0;
}

.breadcrumb-link {
  padding: 0;
  border: 0;
  color: var(--el-color-primary);
  cursor: pointer;
  background: transparent;
}

.candidate-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.candidate-actions {
  padding: 0 12px 10px;
}

.candidate-action-buttons {
  display: flex;
  gap: 8px;
}

.candidate-list__inner,
.selected-list__inner {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 12px 12px;
}

.repository-card {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 8px;
  padding: 10px;
  cursor: pointer;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-fill-color-extra-light);
  transition:
    border-color 0.18s ease,
    background 0.18s ease,
    box-shadow 0.18s ease;
}

.repository-card:hover,
.repository-card.is-selected {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.repository-card.is-selected {
  box-shadow: inset 3px 0 0 var(--el-color-primary);
}

.repository-card__body {
  min-width: 0;
}

.repository-card__title,
.repository-card__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.repository-card__title span:first-child,
.repository-card__url,
.selected-item__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.repository-card__title span:first-child {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.repository-card__meta,
.repository-card__url {
  margin-top: 4px;
}

.candidate-pagination {
  display: flex;
  justify-content: flex-end;
  padding: 10px 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.selected-actions {
  padding: 8px 12px;
}

.selected-group {
  overflow: hidden;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}

.selected-group__title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 600;
  background: var(--el-fill-color-light);
}

.selected-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border-top: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
}

.selected-item__main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.selected-item__name {
  font-size: 13px;
  font-weight: 600;
}

@media (max-width: 1100px) {
  .repository-bind-workbench {
    grid-template-columns: 1fr;
    height: auto;
  }

  .organization-panel,
  .candidate-panel,
  .selected-panel {
    min-height: 360px;
  }
}
</style>
