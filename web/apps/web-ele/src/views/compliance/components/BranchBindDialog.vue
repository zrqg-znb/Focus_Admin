<script lang="ts" setup>
import type {
  BranchItem,
  ComplianceBindMode,
  ComplianceBranchType,
  ComplianceDomain,
} from '#/api/compliance/base';

import { computed, ref, watch } from 'vue';

import { Search, Trash2 } from '@vben/icons';

import {
  ElButton,
  ElCheckbox,
  ElDialog,
  ElEmpty,
  ElInput,
  ElOption,
  ElPagination,
  ElRadioButton,
  ElRadioGroup,
  ElScrollbar,
  ElSelect,
  ElTag,
} from 'element-plus';

import { listBranchesApi } from '#/api/compliance/base';

const BIND_MODE_OPTIONS: Array<{ label: string; value: ComplianceBindMode }> = [
  { label: '追加绑定', value: 'append' },
  { label: '替换绑定', value: 'replace' },
];

const DOMAIN_OPTIONS: Array<{ label: string; value: ComplianceDomain }> = [
  { label: '座舱', value: 'cockpit' },
  { label: '车控', value: 'vehicle' },
];

const BRANCH_TYPE_OPTIONS: Array<{
  label: string;
  value: ComplianceBranchType;
}> = [
  { label: '开发', value: 'development' },
  { label: '主干', value: 'trunk' },
  { label: '发布', value: 'release' },
  { label: '其他', value: 'other' },
];

interface ConfirmPayload {
  branch_ids: string[];
  mode: ComplianceBindMode;
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

const mode = ref<ComplianceBindMode>('append');
const keyword = ref('');
const selectedDomain = ref('');
const selectedBranchType = ref('');
const branchRows = ref<BranchItem[]>([]);
const branchTotal = ref(0);
const branchPage = ref(1);
const branchPageSize = ref(10);
const loading = ref(false);
const selectedMap = ref<Record<string, BranchItem>>({});

const selectedIds = computed(() => Object.keys(selectedMap.value));
const selectedSet = computed(() => new Set(selectedIds.value));
const selectedBranches = computed(() =>
  Object.values(selectedMap.value).sort((left, right) =>
    left.branch_name.localeCompare(right.branch_name, 'zh-CN'),
  ),
);

async function loadBranches(resetPage = false) {
  if (resetPage) branchPage.value = 1;
  loading.value = true;
  try {
    const result = await listBranchesApi({
      branch_type:
        (selectedBranchType.value as ComplianceBranchType) || undefined,
      domain: (selectedDomain.value as ComplianceDomain) || undefined,
      keyword: keyword.value.trim() || undefined,
      page: branchPage.value,
      pageSize: branchPageSize.value,
    });
    branchRows.value = result.items || [];
    branchTotal.value = result.total || 0;
  } finally {
    loading.value = false;
  }
}

function resetDialog() {
  mode.value = 'append';
  keyword.value = '';
  selectedDomain.value = '';
  selectedBranchType.value = '';
  branchRows.value = [];
  branchTotal.value = 0;
  branchPage.value = 1;
  branchPageSize.value = 10;
  selectedMap.value = {};
}

function toggleBranch(item: BranchItem, checked: boolean) {
  // 用对象快照维护跨页选择，分页刷新时右侧清单仍然稳定保留。
  const next = { ...selectedMap.value };
  if (checked) {
    next[item.id] = item;
  } else {
    delete next[item.id];
  }
  selectedMap.value = next;
}

function selectCurrentPage() {
  // 批量选择只合并当前页数据，不覆盖用户之前跨页选中的分支。
  const next = { ...selectedMap.value };
  branchRows.value.forEach((item) => {
    next[item.id] = item;
  });
  selectedMap.value = next;
}

function clearCurrentPage() {
  // 清空当前页时保留其他页选择，降低误操作成本。
  const next = { ...selectedMap.value };
  branchRows.value.forEach((item) => {
    delete next[item.id];
  });
  selectedMap.value = next;
}

function clearAllSelected() {
  selectedMap.value = {};
}

function handleBranchPageChange() {
  loadBranches();
}

function handleBranchPageSizeChange() {
  loadBranches(true);
}

function toggleBranchByCard(item: BranchItem) {
  toggleBranch(item, !selectedSet.value.has(item.id));
}

function confirmSelection() {
  emit('confirm', {
    branch_ids: selectedIds.value,
    mode: mode.value,
  });
}

watch(
  () => props.modelValue,
  async (show) => {
    if (!show) return;
    resetDialog();
    await loadBranches(true);
  },
);
</script>

<template>
  <ElDialog
    v-model="visible"
    append-to-body
    class="compliance-bind-dialog"
    destroy-on-close
    top="5vh"
    width="min(1060px, calc(100vw - 32px))"
    :close-on-click-modal="false"
  >
    <template #header>
      <div class="bind-title">
        <div>
          <div class="bind-title__main">批量绑定分支</div>
          <div class="bind-title__sub">筛选分支并加入右侧清单，跨页选择会持续保留。</div>
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

    <div class="branch-bind-workbench">
      <section class="bind-panel candidate-panel">
        <div class="candidate-heading">
          <div>
            <div class="candidate-title">分支候选</div>
            <div class="candidate-hint">按名称、别名、用途、领域和分支类型收敛范围。</div>
          </div>
          <ElTag effect="plain">当前结果 {{ branchTotal }}</ElTag>
        </div>

        <div class="branch-filter-grid">
          <ElInput
            v-model="keyword"
            clearable
            placeholder="搜索分支名 / 别名 / 用途"
            :prefix-icon="Search"
            @clear="loadBranches(true)"
            @keyup.enter="loadBranches(true)"
          />
          <ElSelect
            v-model="selectedDomain"
            clearable
            placeholder="领域"
            @change="loadBranches(true)"
            @clear="loadBranches(true)"
          >
            <ElOption
              v-for="item in DOMAIN_OPTIONS"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
          <ElSelect
            v-model="selectedBranchType"
            clearable
            placeholder="分支类型"
            @change="loadBranches(true)"
            @clear="loadBranches(true)"
          >
            <ElOption
              v-for="item in BRANCH_TYPE_OPTIONS"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
          <ElButton @click="loadBranches(true)">查询</ElButton>
        </div>

        <div class="candidate-actions">
          <div class="candidate-count">已选 {{ selectedIds.length }} 个</div>
          <div class="candidate-action-buttons">
            <ElButton :disabled="!branchRows.length" @click="selectCurrentPage">
              全选当前页
            </ElButton>
            <ElButton :disabled="!branchRows.length" @click="clearCurrentPage">
              清空当前页
            </ElButton>
          </div>
        </div>

        <ElScrollbar class="candidate-list">
          <div v-if="branchRows.length" class="candidate-list__inner">
            <div
              v-for="item in branchRows"
              :key="item.id"
              class="branch-card"
              :class="{ 'is-selected': selectedSet.has(item.id) }"
              role="button"
              tabindex="0"
              @click="toggleBranchByCard(item)"
              @keydown.enter.prevent="toggleBranchByCard(item)"
              @keydown.space.prevent="toggleBranchByCard(item)"
            >
              <ElCheckbox
                :model-value="selectedSet.has(item.id)"
                @click.stop
                @change="(checked) => toggleBranch(item, !!checked)"
              />
              <div class="branch-card__body">
                <div class="branch-card__title">
                  <span>{{ item.branch_name }}</span>
                  <ElTag size="small" effect="plain">{{ item.branch_type_label }}</ElTag>
                </div>
                <div class="branch-card__meta">
                  <span>{{ item.domain_label }}</span>
                  <span>关联代码库 {{ item.repository_count }}</span>
                  <span v-if="item.alias">别名：{{ item.alias }}</span>
                </div>
                <div class="branch-card__purpose">{{ item.purpose || '暂无用途说明' }}</div>
              </div>
            </div>
          </div>
          <ElEmpty v-else description="暂无匹配分支" :image-size="86" />
        </ElScrollbar>

        <div class="candidate-pagination">
          <ElPagination
            v-model:current-page="branchPage"
            v-model:page-size="branchPageSize"
            :total="branchTotal"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            small
            @current-change="handleBranchPageChange"
            @size-change="handleBranchPageSizeChange"
          />
        </div>
      </section>

      <aside class="bind-panel selected-panel">
        <div class="bind-panel__header">
          <span>已选分支</span>
          <ElTag type="success" size="small" effect="light">{{ selectedIds.length }}</ElTag>
        </div>
        <div class="selected-actions">
          <ElButton text type="danger" :disabled="!selectedIds.length" @click="clearAllSelected">
            清空全部
          </ElButton>
        </div>
        <ElScrollbar class="selected-list">
          <div v-if="selectedBranches.length" class="selected-list__inner">
            <div
              v-for="item in selectedBranches"
              :key="item.id"
              class="selected-item"
            >
              <div class="selected-item__main">
                <span class="selected-item__name">{{ item.branch_name }}</span>
                <span class="selected-item__meta">
                  {{ item.domain_label }} / {{ item.branch_type_label }}
                </span>
              </div>
              <ElButton
                circle
                text
                type="danger"
                @click="toggleBranch(item, false)"
              >
                <Trash2 class="size-4" />
              </ElButton>
            </div>
          </div>
          <ElEmpty v-else description="暂无选中分支" :image-size="74" />
        </ElScrollbar>
      </aside>
    </div>

    <template #footer>
      <div class="bind-footer">
        <span>确认后将以当前绑定方式作用于已勾选代码库。</span>
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
.branch-card__meta,
.branch-card__purpose,
.selected-item__meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.branch-bind-workbench {
  display: grid;
  grid-template-columns: minmax(520px, 1fr) 320px;
  gap: 12px;
  height: 620px;
  min-height: 0;
}

.bind-panel {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-bg-color);
}

.candidate-panel,
.selected-panel {
  display: flex;
  flex-direction: column;
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

.candidate-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.branch-filter-grid {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 140px 150px auto;
  gap: 8px;
  padding: 12px;
}

.candidate-actions {
  padding: 0 12px 10px;
}

.candidate-action-buttons {
  display: flex;
  gap: 8px;
}

.candidate-list,
.selected-list {
  flex: 1;
  min-height: 0;
}

.candidate-list__inner,
.selected-list__inner {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 12px 12px;
}

.branch-card {
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

.branch-card:hover,
.branch-card.is-selected {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.branch-card.is-selected {
  box-shadow: inset 3px 0 0 var(--el-color-primary);
}

.branch-card__body {
  min-width: 0;
}

.branch-card__title,
.branch-card__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.branch-card__title span:first-child,
.branch-card__purpose,
.selected-item__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.branch-card__title span:first-child {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.branch-card__meta,
.branch-card__purpose {
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

.selected-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-fill-color-extra-light);
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

@media (max-width: 980px) {
  .branch-bind-workbench {
    grid-template-columns: 1fr;
    height: auto;
  }

  .candidate-panel,
  .selected-panel {
    min-height: 360px;
  }

  .branch-filter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
