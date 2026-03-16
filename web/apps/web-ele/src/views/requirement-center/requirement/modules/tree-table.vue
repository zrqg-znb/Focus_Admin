<script lang="ts" setup>
import type { OptionItem, RequirementTreeRow } from '../data';

import type { RequirementStatus } from '#/api/requirement-center/requirement';

import { computed, ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';

import {
  ElButton,
  ElDialog,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElProgress,
  ElSelect,
  ElTag,
  ElTooltip,
} from 'element-plus';

import {
  batchArchiveApi,
  batchAssignOwnerApi,
  batchAssignReviewerApi,
  batchPriorityApi,
} from '#/api/requirement-center/requirement';
import UserSelector from '#/components/zq-form/user-selector/user-selector.vue';
import { useZqTable } from '#/components/zq-table';

import {
  collectExpandableIds,
  dueCountdownText,
  formatDateText,
  getRequirementProgressPercent,
  getStatusLabel,
  isRequirementLeaf,
  useTreeColumns,
} from '../data';

defineOptions({ name: 'RequirementTreeTable' });

const props = defineProps<{
  expandedRowKeys: string[];
  loading: boolean;
  priorityOptions: OptionItem[];
  rows: RequirementTreeRow[];
}>();

const emit = defineEmits<{
  (e: 'assignOwner', row: RequirementTreeRow): void;
  (e: 'collapseAll'): void;
  (e: 'detail', row: RequirementTreeRow): void;
  (e: 'edit', row: RequirementTreeRow): void;
  (e: 'expandAll'): void;
  (e: 'refresh'): void;
  (e: 'update:expandedRowKeys', keys: string[]): void;
  (
    e: 'review',
    row: RequirementTreeRow,
    action: 'accept' | 'need_info' | 'reject',
  ): void;
  (e: 'split', row: RequirementTreeRow): void;
  (e: 'submit', row: RequirementTreeRow): void;
  (e: 'transition', row: RequirementTreeRow): void;
  (e: 'transferReviewer', row: RequirementTreeRow): void;
}>();

function handleExpandChange(row: RequirementTreeRow, expanded: unknown) {
  const id = String(row?.id || '').trim();
  if (!id) return;

  if (Array.isArray(expanded)) {
    // Compatible with "expand" type column, where expanded is expandedRows[].
    const nextKeys = expanded
      .map((item) => String(item?.id || '').trim())
      .filter(Boolean);
    emit('update:expandedRowKeys', nextKeys);
    return;
  }

  const nextExpanded = typeof expanded === 'boolean' ? expanded : true;
  const nextSet = new Set(
    (props.expandedRowKeys || []).map((key) => String(key).trim()),
  );
  if (nextExpanded) nextSet.add(id);
  else nextSet.delete(id);
  emit('update:expandedRowKeys', [...nextSet]);
}

function getPriorityTagType(priority?: string) {
  if (priority === 'urgent') return 'danger';
  if (priority === 'high') return 'warning';
  if (priority === 'medium') return 'primary';
  if (priority === 'low') return 'info';
  return '';
}

function getStatusTagType(status: RequirementStatus) {
  if (status === 'done') return 'success';
  if (status === 'rejected') return 'danger';
  if (status === 'archived') return 'info';
  if (status === 'submitted' || status === 'in_acceptance') return 'warning';
  return 'primary';
}

function getNextTransitionAction(status: RequirementStatus): null | {
  action: 'archive' | 'done' | 'in_acceptance' | 'in_dev' | 'planned';
  label: string;
} {
  if (status === 'accepted') return { action: 'planned', label: '推进排期' };
  if (status === 'planned') return { action: 'in_dev', label: '进入开发' };
  if (status === 'in_dev')
    return { action: 'in_acceptance', label: '进入验收' };
  if (status === 'in_acceptance') return { action: 'done', label: '标记完成' };
  if (status === 'done' || status === 'rejected') {
    return { action: 'archive', label: '归档' };
  }
  return null;
}

function canSplitRequirement(row: RequirementTreeRow) {
  return ['accepted', 'in_acceptance', 'in_dev', 'planned'].includes(
    row.status,
  );
}

const selectedRows = ref<RequirementTreeRow[]>([]);
const selectedIds = computed(() =>
  (selectedRows.value || [])
    .map((item) => String(item?.id || '').trim())
    .filter(Boolean),
);
const selectionCount = computed(() => selectedIds.value.length);

function handleSelectionChange(rows: RequirementTreeRow[]) {
  selectedRows.value = Array.isArray(rows) ? rows : [];
}

function ensureSelection() {
  if (selectedIds.value.length > 0) return true;
  ElMessage.warning('请先勾选至少一条需求');
  return false;
}

const expandableCount = computed(
  () => collectExpandableIds(props.rows || []).length,
);

const [Grid, gridApi] = useZqTable({
  tableTitle: '需求树表',
  gridOptions: {
    columns: useTreeColumns(),
    data: [],
    rowKey: 'id',
    treeProps: { children: 'children' },
    indent: 16,
    border: true,
    stripe: true,
    highlightCurrentRow: true,
    pagerConfig: { enabled: false },
    toolbarConfig: {
      custom: true,
      refresh: false,
      search: false,
      zoom: true,
    },
    'onExpand-change': handleExpandChange,
  },
});

watch(
  () => props.rows,
  (rows) => {
    selectedRows.value = [];
    gridApi.setState((prev) => ({
      gridOptions: {
        ...prev.gridOptions,
        data: Array.isArray(rows) ? rows : [],
      },
    }));
  },
  { immediate: true },
);

watch(
  () => props.expandedRowKeys,
  (keys) => {
    gridApi.setState((prev) => ({
      gridOptions: {
        ...prev.gridOptions,
        expandRowKeys: Array.isArray(keys) ? keys : [],
      },
    }));
  },
  { immediate: true },
);

watch(
  () => props.loading,
  (val) => {
    gridApi.setLoading(!!val);
    if (val) {
      selectedRows.value = [];
    }
  },
  { immediate: true },
);

// Batch dialogs
const batchReviewerVisible = ref(false);
const batchReviewerId = ref<string>('');
const batchReviewerNote = ref('');
function openBatchAssignReviewer() {
  if (!ensureSelection()) return;
  batchReviewerId.value = '';
  batchReviewerNote.value = '';
  batchReviewerVisible.value = true;
}
async function submitBatchAssignReviewer() {
  const reviewerId = String(batchReviewerId.value || '').trim();
  if (!reviewerId) {
    ElMessage.warning('请选择评审人');
    return;
  }
  try {
    const response = await batchAssignReviewerApi({
      requirement_ids: selectedIds.value,
      reviewer_id: reviewerId,
      note: batchReviewerNote.value || undefined,
    });
    ElMessage.success(`${response.msg}，成功 ${response.count} 条`);
    batchReviewerVisible.value = false;
    emit('refresh');
  } catch {
    // noop
  }
}

const batchOwnerVisible = ref(false);
const batchOwnerId = ref<string>('');
const batchOwnerNote = ref('');
function openBatchAssignOwner() {
  if (!ensureSelection()) return;
  batchOwnerId.value = '';
  batchOwnerNote.value = '';
  batchOwnerVisible.value = true;
}
async function submitBatchAssignOwner() {
  const ownerId = String(batchOwnerId.value || '').trim();
  if (!ownerId) {
    ElMessage.warning('请选择责任人');
    return;
  }
  try {
    const response = await batchAssignOwnerApi({
      requirement_ids: selectedIds.value,
      owner_id: ownerId,
      note: batchOwnerNote.value || undefined,
    });
    ElMessage.success(`${response.msg}，成功 ${response.count} 条`);
    batchOwnerVisible.value = false;
    emit('refresh');
  } catch {
    // noop
  }
}

const batchPriorityVisible = ref(false);
const batchPriority = ref('');
const batchPriorityNote = ref('');
function openBatchPriority() {
  if (!ensureSelection()) return;
  batchPriority.value = props.priorityOptions?.[0]?.value || '';
  batchPriorityNote.value = '';
  batchPriorityVisible.value = true;
}
async function submitBatchPriority() {
  const priority = String(batchPriority.value || '').trim();
  if (!priority) {
    ElMessage.warning('请选择优先级');
    return;
  }
  try {
    const response = await batchPriorityApi({
      requirement_ids: selectedIds.value,
      priority,
      note: batchPriorityNote.value || undefined,
    });
    ElMessage.success(`${response.msg}，成功 ${response.count} 条`);
    batchPriorityVisible.value = false;
    emit('refresh');
  } catch {
    // noop
  }
}

async function handleBatchArchive() {
  if (!ensureSelection()) return;
  try {
    await ElMessageBox.confirm(
      `确认归档选中的 ${selectionCount.value} 条需求吗？（仅已完成/已拒绝可归档）`,
      '批量归档',
      { type: 'warning' },
    );
  } catch {
    return;
  }

  try {
    const response = await batchArchiveApi({
      requirement_ids: selectedIds.value,
    });
    const skipped = response.skipped_ids || [];
    ElMessage.success(
      `${response.msg}，成功 ${response.count} 条${
        skipped.length > 0 ? `，跳过 ${skipped.length} 条` : ''
      }`,
    );
    if (skipped.length > 0) {
      await ElMessageBox.alert(skipped.join('\n'), '跳过的需求ID', {
        type: 'info',
        confirmButtonText: '知道了',
      });
    }
    emit('refresh');
  } catch {
    // noop
  }
}

function handleBatchCommand(command: string) {
  if (command === 'assign-reviewer') return openBatchAssignReviewer();
  if (command === 'assign-owner') return openBatchAssignOwner();
  if (command === 'priority') return openBatchPriority();
  if (command === 'archive') return handleBatchArchive();
}
</script>

<template>
  <div class="tree-table-wrapper">
    <Grid class="h-full" @selection-change="handleSelectionChange">
      <template #toolbar-actions>
        <div class="toolbar-left">
          <ElTag v-if="selectionCount > 0" type="info" size="small">
            已选 {{ selectionCount }}
          </ElTag>
          <ElTag v-if="expandableCount > 0" type="info" size="small">
            可展开 {{ expandableCount }}
          </ElTag>

          <ElButton size="small" @click="emit('expandAll')">
            展开全部
          </ElButton>
          <ElButton size="small" @click="emit('collapseAll')">
            折叠全部
          </ElButton>

          <ElDropdown trigger="click" @command="handleBatchCommand">
            <ElButton size="small" type="primary">
              批量操作
              <IconifyIcon icon="lucide:chevron-down" class="ml-1" />
            </ElButton>
            <template #dropdown>
              <ElDropdownMenu>
                <ElDropdownItem command="assign-reviewer">
                  批量分配评审人
                </ElDropdownItem>
                <ElDropdownItem command="assign-owner">
                  批量分配责任人
                </ElDropdownItem>
                <ElDropdownItem command="priority">
                  批量调整优先级
                </ElDropdownItem>
                <ElDropdownItem divided command="archive">
                  批量归档
                </ElDropdownItem>
              </ElDropdownMenu>
            </template>
          </ElDropdown>
        </div>
      </template>

      <template #toolbar-tools>
        <ElButton circle title="刷新" @click="emit('refresh')">
          <IconifyIcon icon="lucide:refresh-cw" />
        </ElButton>
      </template>

      <template #cell-title="{ row }">
        <div
          class="title-cell"
          :class="[
            isRequirementLeaf(row) ? 'is-leaf' : 'is-parent',
            `level-${row.level || 0}`,
          ]"
        >
          <div class="title-meta">
            <ElTag size="small" type="info">L{{ row.level || 0 }}</ElTag>
            <ElTag v-if="!isRequirementLeaf(row)" size="small" type="warning">
              父需求
            </ElTag>
            <ElTag v-if="!isRequirementLeaf(row)" size="small" type="info">
              子 {{ row.child_count || 0 }}
            </ElTag>
          </div>
          <div
            class="title-text"
            @click="emit('detail', row)"
            :title="row.title"
          >
            {{ row.title }}
          </div>
        </div>
      </template>

      <template #cell-status="{ row }">
        <ElTag size="small" :type="getStatusTagType(row.status)">
          {{ getStatusLabel(row.status) }}
        </ElTag>
      </template>

      <template #cell-progress="{ row }">
        <div class="progress-cell">
          <ElProgress
            :percentage="getRequirementProgressPercent(row)"
            :show-text="false"
            :stroke-width="8"
          />
          <div class="progress-text">
            {{ row.leaf_done || 0 }}/{{ row.leaf_total || 0 }}
          </div>
        </div>
      </template>

      <template #cell-priority="{ row }">
        <ElTag size="small" :type="getPriorityTagType(row.priority)">
          {{ row.priority || '-' }}
        </ElTag>
      </template>

      <template #cell-reviewer_info="{ row }">
        <div class="user-cell">
          <div class="user-label">
            {{ row.reviewer_info?.name || row.reviewer_info?.username || '-' }}
          </div>
          <ElButton
            link
            size="small"
            type="primary"
            @click="emit('transferReviewer', row)"
          >
            转交
          </ElButton>
        </div>
      </template>

      <template #cell-owner_info="{ row }">
        <div class="user-cell">
          <div class="user-label">
            {{ row.owner_info?.name || row.owner_info?.username || '-' }}
          </div>
          <ElButton
            link
            size="small"
            type="primary"
            @click="emit('assignOwner', row)"
          >
            分配
          </ElButton>
        </div>
      </template>

      <template #cell-review_due_at="{ row }">
        <ElTooltip
          :content="dueCountdownText(row.review_due_at)"
          placement="top"
        >
          <span :class="row.is_review_overdue ? 'text-danger' : ''">
            {{ formatDateText(row.review_due_at) }}
          </span>
        </ElTooltip>
      </template>

      <template #cell-dev_due_at="{ row }">
        <ElTooltip :content="dueCountdownText(row.dev_due_at)" placement="top">
          <span :class="row.is_dev_overdue ? 'text-danger' : ''">
            {{ formatDateText(row.dev_due_at) }}
          </span>
        </ElTooltip>
      </template>

      <template #cell-actions="{ row }">
        <div class="action-cell">
          <div class="action-icons">
            <ElTooltip content="查看详情" placement="top">
              <ElButton
                circle
                link
                size="small"
                type="primary"
                @click="emit('detail', row)"
              >
                <IconifyIcon icon="lucide:eye" />
              </ElButton>
            </ElTooltip>
            <ElTooltip content="编辑需求" placement="top">
              <ElButton circle link size="small" @click="emit('edit', row)">
                <IconifyIcon icon="lucide:pencil-line" />
              </ElButton>
            </ElTooltip>
            <ElTooltip
              v-if="canSplitRequirement(row)"
              content="拆解子需求"
              placement="top"
            >
              <ElButton
                circle
                link
                size="small"
                type="primary"
                @click="emit('split', row)"
              >
                <IconifyIcon icon="lucide:git-fork" />
              </ElButton>
            </ElTooltip>
          </div>

          <div class="action-flow">
            <ElButton
              v-if="
                isRequirementLeaf(row) &&
                (row.status === 'draft' || row.status === 'need_info')
              "
              size="small"
              type="warning"
              @click="emit('submit', row)"
            >
              提交评审
            </ElButton>
            <template
              v-if="isRequirementLeaf(row) && row.status === 'submitted'"
            >
              <ElButton
                size="small"
                type="success"
                @click="emit('review', row, 'accept')"
              >
                通过
              </ElButton>
              <ElButton
                size="small"
                type="warning"
                @click="emit('review', row, 'need_info')"
              >
                补充
              </ElButton>
              <ElButton
                size="small"
                type="danger"
                @click="emit('review', row, 'reject')"
              >
                驳回
              </ElButton>
            </template>
            <ElButton
              v-if="
                isRequirementLeaf(row) && getNextTransitionAction(row.status)
              "
              size="small"
              type="primary"
              @click="emit('transition', row)"
            >
              {{ getNextTransitionAction(row.status)?.label }}
            </ElButton>
          </div>
        </div>
      </template>
    </Grid>

    <ElDialog
      v-model="batchReviewerVisible"
      title="批量分配评审人"
      width="520px"
    >
      <div class="batch-form">
        <div class="text-sm text-gray-500">
          选中 {{ selectionCount }} 条需求
        </div>
        <UserSelector
          v-model="batchReviewerId"
          :multiple="false"
          display-mode="select"
          placeholder="选择评审人"
        />
        <ElInput v-model="batchReviewerNote" placeholder="备注（可选）" />
      </div>
      <template #footer>
        <ElButton @click="batchReviewerVisible = false">取消</ElButton>
        <ElButton type="primary" @click="submitBatchAssignReviewer">
          确定
        </ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="batchOwnerVisible" title="批量分配责任人" width="520px">
      <div class="batch-form">
        <div class="text-sm text-gray-500">
          选中 {{ selectionCount }} 条需求
        </div>
        <UserSelector
          v-model="batchOwnerId"
          :multiple="false"
          display-mode="select"
          placeholder="选择责任人"
        />
        <ElInput v-model="batchOwnerNote" placeholder="备注（可选）" />
      </div>
      <template #footer>
        <ElButton @click="batchOwnerVisible = false">取消</ElButton>
        <ElButton type="primary" @click="submitBatchAssignOwner">确定</ElButton>
      </template>
    </ElDialog>

    <ElDialog
      v-model="batchPriorityVisible"
      title="批量调整优先级"
      width="520px"
    >
      <div class="batch-form">
        <div class="text-sm text-gray-500">
          选中 {{ selectionCount }} 条需求
        </div>
        <ElSelect v-model="batchPriority" placeholder="选择优先级">
          <ElOption
            v-for="item in priorityOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </ElSelect>
        <ElInput v-model="batchPriorityNote" placeholder="备注（可选）" />
      </div>
      <template #footer>
        <ElButton @click="batchPriorityVisible = false">取消</ElButton>
        <ElButton type="primary" @click="submitBatchPriority">确定</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.tree-table-wrapper {
  min-height: 0;
  height: 100%;
}

.toolbar-left {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.title-cell {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
  padding-left: 2px;
}

.title-cell.is-parent::before {
  content: '';
  position: absolute;
  left: 0;
  top: 3px;
  bottom: 3px;
  width: 3px;
  border-radius: 999px;
  background: linear-gradient(
    180deg,
    rgb(79 70 229 / 70%),
    rgb(34 211 238 / 25%)
  );
}

.title-cell.is-parent {
  padding-left: 10px;
}

.title-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.title-text {
  max-width: 100%;
  cursor: pointer;
  color: rgb(30 64 175);
  font-weight: 600;
  line-height: 1.2;
  text-align: left;
}

.title-text:hover {
  text-decoration: underline;
}

.progress-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.progress-text {
  font-size: 12px;
  color: rgb(100 116 139);
}

.user-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.user-label {
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-start;
}

.action-icons {
  display: flex;
  align-items: center;
  gap: 2px;
}

.action-flow {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.batch-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
