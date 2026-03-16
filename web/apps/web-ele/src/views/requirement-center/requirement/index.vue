<script lang="ts" setup>
import type {
  OptionItem,
  RequirementBoardItem,
  RequirementTreeRow,
} from './data';

import type {
  RequirementDashboardSummary,
  RequirementItem,
  RequirementStatus,
} from '#/api/requirement-center/requirement';

import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  ElButton,
  ElCard,
  ElDialog,
  ElDivider,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPagination,
  ElSelect,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { getDictItemByCodeApi } from '#/api/core/dict';
import {
  assignOwnerApi,
  createRequirementApi,
  createRequirementChildApi,
  getRequirementDashboardSummaryApi,
  listRequirementTreeApi,
  reviewRequirementApi,
  submitRequirementApi,
  transferReviewerApi,
  transitionRequirementApi,
  updateRequirementApi,
} from '#/api/requirement-center/requirement';
import UserSelector from '#/components/zq-form/user-selector/user-selector.vue';

import {
  collectExpandableIds,
  decorateRequirementTree,
  dueCountdownText,
  flattenRequirementTree,
  isRequirementLeaf,
  REQUIREMENT_STATUS_OPTIONS,
  useRequirementFormSchema,
} from './data';
import RequirementBoard from './modules/board.vue';
import RequirementTreeTable from './modules/tree-table.vue';

defineOptions({ name: 'RequirementCenterList' });

type UserSelectorValue = string | string[];

interface RequirementFilterForm {
  keyword: string;
  overdue: '' | 'false' | 'true';
  owner_id: '' | UserSelectorValue;
  priority: string;
  reviewer_id: '' | UserSelectorValue;
  source: string;
  status: '' | RequirementStatus;
  type: string;
}

const router = useRouter();

const activeTab = ref<'board' | 'tree'>('tree');

const loadingDict = ref(false);
const treeLoading = ref(false);
const summaryLoading = ref(false);

const typeOptions = ref<OptionItem[]>([]);
const sourceOptions = ref<OptionItem[]>([]);
const priorityOptions = ref<OptionItem[]>([]);

const treeRows = ref<RequirementTreeRow[]>([]);
const boardItems = ref<RequirementBoardItem[]>([]);
const expandedRowKeys = ref<string[]>([]);

const currentPage = ref(1);
const pageSize = ref(20);
const pageSizes = [10, 20, 50, 100];

const summary = ref<RequirementDashboardSummary>({
  closed_count: 0,
  dev_overdue_count: 0,
  open_count: 0,
  overdue_count: 0,
  owner_stats: [],
  priority_stats: [],
  review_overdue_count: 0,
  reviewer_stats: [],
  status_stats: [],
  total_count: 0,
});

const filters = ref<RequirementFilterForm>({
  keyword: '',
  overdue: '',
  owner_id: '',
  priority: '',
  reviewer_id: '',
  source: '',
  status: '',
  type: '',
});

const dialogVisible = ref(false);
const dialogTitle = ref('新建需求');
const isEditMode = ref(false);
const currentRequirementId = ref('');

const splitDialogVisible = ref(false);
const splitParent = ref<null | RequirementItem>(null);
const splitSubmitting = ref(false);
const splitForm = ref({
  acceptance_criteria: '',
  business_value: '',
  description: '',
  owner_id: '',
  priority: '',
  reviewer_id: '',
  source: '',
  title: '',
  type: '',
});

const transferDialogVisible = ref(false);
const transferSubmitting = ref(false);
const transferTarget = ref<null | RequirementItem>(null);
const transferReviewerId = ref<UserSelectorValue>('');
const transferNote = ref('');

const assignDialogVisible = ref(false);
const assignSubmitting = ref(false);
const assignTarget = ref<null | RequirementItem>(null);
const assignOwnerId = ref<UserSelectorValue>('');
const assignNote = ref('');

const [Form, formApi] = useVbenForm({
  schema: useRequirementFormSchema([], [], []),
  showDefaultActions: false,
});

const focusItems = computed(() =>
  [...boardItems.value]
    .filter((item) => item.is_review_overdue || item.is_dev_overdue)
    .slice(0, 8),
);

const pagedTreeRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return (treeRows.value || []).slice(start, end);
});

const pagedBoardItems = computed(() =>
  flattenRequirementTree(pagedTreeRows.value),
);

const metrics = computed(() => [
  {
    icon: 'lucide:layers-3',
    label: '总需求',
    tone: 'indigo',
    value: summary.value.total_count,
  },
  {
    icon: 'lucide:activity',
    label: '进行中',
    tone: 'blue',
    value: summary.value.open_count,
  },
  {
    icon: 'lucide:check-check',
    label: '已关闭',
    tone: 'emerald',
    value: summary.value.closed_count,
  },
  {
    icon: 'lucide:alarm-clock-check',
    label: '总逾期',
    tone: summary.value.overdue_count > 0 ? 'rose' : 'emerald',
    value: summary.value.overdue_count,
  },
]);

function getMetricClass(tone: string) {
  const mapper: Record<string, string> = {
    blue: 'from-blue-500/20 to-blue-500/5 text-blue-700',
    emerald: 'from-emerald-500/20 to-emerald-500/5 text-emerald-700',
    indigo: 'from-indigo-500/20 to-indigo-500/5 text-indigo-700',
    rose: 'from-rose-500/20 to-rose-500/5 text-rose-700',
  };
  return mapper[tone] || mapper.indigo;
}

function normalizeDictOptions(items: any[] = []) {
  return items
    .filter((item) => item?.label && item?.value)
    .map((item) => ({
      label: String(item.label),
      value: String(item.value),
    }));
}

function parseAttachmentText(value: string): string[] {
  return String(value || '')
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function toAttachmentText(attachments?: string[]) {
  return Array.isArray(attachments) ? attachments.join(',') : '';
}

function normalizeSingleUserValue(value: '' | UserSelectorValue) {
  if (!value) return '';
  if (Array.isArray(value)) return String(value[0] || '').trim();
  return String(value || '').trim();
}

function buildFilterParams() {
  const form = filters.value;
  const payload: Record<string, any> = {};
  const reviewerId = normalizeSingleUserValue(form.reviewer_id);
  const ownerId = normalizeSingleUserValue(form.owner_id);

  if (form.keyword.trim()) payload.keyword = form.keyword.trim();
  if (form.status) payload.status = form.status;
  if (form.priority) payload.priority = form.priority;
  if (form.type) payload.type = form.type;
  if (form.source) payload.source = form.source;
  if (reviewerId) payload.reviewer_id = reviewerId;
  if (ownerId) payload.owner_id = ownerId;
  if (form.overdue === 'true') payload.overdue = true;
  if (form.overdue === 'false') payload.overdue = false;

  return payload;
}

async function loadDictOptions() {
  loadingDict.value = true;
  try {
    const [typeItems, sourceItems, priorityItems] = await Promise.all([
      getDictItemByCodeApi('requirement_type').catch(() => []),
      getDictItemByCodeApi('requirement_source').catch(() => []),
      getDictItemByCodeApi('requirement_priority').catch(() => []),
    ]);

    typeOptions.value = normalizeDictOptions(typeItems);
    sourceOptions.value = normalizeDictOptions(sourceItems);
    priorityOptions.value = normalizeDictOptions(priorityItems);
  } finally {
    if (typeOptions.value.length === 0) {
      typeOptions.value = [
        { label: '功能需求', value: 'feature' },
        { label: '优化需求', value: 'improvement' },
        { label: '缺陷修复', value: 'bugfix' },
      ];
    }
    if (sourceOptions.value.length === 0) {
      sourceOptions.value = [
        { label: '业务方', value: 'biz' },
        { label: '客户反馈', value: 'customer' },
        { label: '内部改进', value: 'internal' },
      ];
    }
    if (priorityOptions.value.length === 0) {
      priorityOptions.value = [
        { label: '低', value: 'low' },
        { label: '中', value: 'medium' },
        { label: '高', value: 'high' },
        { label: '紧急', value: 'urgent' },
      ];
    }
    formApi.updateSchema(
      useRequirementFormSchema(
        typeOptions.value,
        sourceOptions.value,
        priorityOptions.value,
      ),
    );
    loadingDict.value = false;
  }
}

async function loadSummary() {
  summaryLoading.value = true;
  try {
    summary.value = await getRequirementDashboardSummaryApi();
  } catch {
    ElMessage.error('加载看板摘要失败');
  } finally {
    summaryLoading.value = false;
  }
}

async function loadTree() {
  treeLoading.value = true;
  try {
    const treeRowsRaw = await listRequirementTreeApi(buildFilterParams());
    const decorated = decorateRequirementTree(treeRowsRaw || []);
    treeRows.value = decorated;
    boardItems.value = flattenRequirementTree(decorated);

    const maxPage = Math.max(1, Math.ceil(decorated.length / pageSize.value));
    if (currentPage.value > maxPage) {
      currentPage.value = 1;
    }
  } catch {
    treeRows.value = [];
    boardItems.value = [];
    ElMessage.error('加载需求树失败');
  } finally {
    treeLoading.value = false;
  }
}

async function refreshAll() {
  await Promise.all([loadSummary(), loadTree()]);
}

async function handleSearch() {
  currentPage.value = 1;
  await loadTree();
}

async function handleQuickStatus(status: RequirementStatus) {
  filters.value.status = filters.value.status === status ? '' : status;
  currentPage.value = 1;
  await loadTree();
}

async function handleReset() {
  filters.value = {
    keyword: '',
    overdue: '',
    owner_id: '',
    priority: '',
    reviewer_id: '',
    source: '',
    status: '',
    type: '',
  };
  currentPage.value = 1;
  await loadTree();
}

function goDetail(row: RequirementItem) {
  router.push(`/requirement-center/requirement/detail/${row.id}`);
}

function goDashboard() {
  router.push('/requirement-center/requirement/dashboard');
}

function isLeafNode(row: RequirementItem) {
  return isRequirementLeaf(row);
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

async function openCreateDialog() {
  isEditMode.value = false;
  dialogTitle.value = '新建需求';
  currentRequirementId.value = '';
  formApi.setValues({
    acceptance_criteria: '',
    attachments_text: '',
    business_value: '',
    description: '',
    owner_id: '',
    priority: priorityOptions.value[0]?.value || 'medium',
    reviewer_id: '',
    source: sourceOptions.value[0]?.value || '',
    title: '',
    type: typeOptions.value[0]?.value || '',
  });
  dialogVisible.value = true;
}

async function openEditDialog(row: RequirementItem) {
  isEditMode.value = true;
  dialogTitle.value = `编辑需求 - ${row.title}`;
  currentRequirementId.value = row.id;
  formApi.setValues({
    acceptance_criteria: row.acceptance_criteria || '',
    attachments_text: toAttachmentText(row.attachments),
    business_value: row.business_value || '',
    description: row.description || '',
    owner_id: row.owner_id || '',
    priority: row.priority || '',
    reviewer_id: row.reviewer_id || '',
    source: row.source || '',
    title: row.title || '',
    type: row.type || '',
  });
  dialogVisible.value = true;
}

async function submitForm() {
  const { valid } = await formApi.validate();
  if (!valid) return;
  const values = await formApi.getValues<any>();

  const payload = {
    acceptance_criteria: values.acceptance_criteria || '',
    attachments: parseAttachmentText(values.attachments_text),
    business_value: values.business_value || '',
    description: values.description || '',
    owner_id: values.owner_id || undefined,
    priority: values.priority || 'medium',
    reviewer_id: values.reviewer_id || undefined,
    source: values.source || '',
    title: values.title || '',
    type: values.type || '',
  };

  try {
    if (isEditMode.value) {
      await updateRequirementApi(currentRequirementId.value, payload);
      ElMessage.success('需求更新成功');
    } else {
      await createRequirementApi(payload);
      ElMessage.success('需求创建成功');
    }
    dialogVisible.value = false;
    await refreshAll();
  } catch {
    // noop
  }
}

function openSplitDialog(row: RequirementItem) {
  splitParent.value = row;
  splitForm.value = {
    acceptance_criteria: '',
    business_value: '',
    description: '',
    owner_id: row.owner_id || '',
    priority: row.priority || '',
    reviewer_id: row.reviewer_id || '',
    source: row.source || '',
    title: '',
    type: row.type || '',
  };
  splitDialogVisible.value = true;
}

async function submitSplitForm() {
  if (!splitParent.value) return;
  const title = splitForm.value.title.trim();
  if (!title) {
    ElMessage.warning('请输入子需求标题');
    return;
  }
  splitSubmitting.value = true;
  try {
    await createRequirementChildApi(splitParent.value.id, {
      acceptance_criteria: splitForm.value.acceptance_criteria || '',
      business_value: splitForm.value.business_value || '',
      description: splitForm.value.description || '',
      owner_id: splitForm.value.owner_id || undefined,
      priority: splitForm.value.priority || undefined,
      reviewer_id: splitForm.value.reviewer_id || undefined,
      source: splitForm.value.source || undefined,
      title,
      type: splitForm.value.type || undefined,
    });
    ElMessage.success('拆解子需求成功');
    splitDialogVisible.value = false;
    await refreshAll();
  } finally {
    splitSubmitting.value = false;
  }
}

async function handleSubmit(row: RequirementItem) {
  if (!isLeafNode(row)) {
    ElMessage.warning('非叶子需求不允许人工提交流转');
    return;
  }
  await ElMessageBox.confirm('确认提交该需求进入评审吗？', '提示', {
    type: 'warning',
  });
  await submitRequirementApi(row.id);
  ElMessage.success('提交成功');
  await refreshAll();
}

async function handleReview(
  row: RequirementItem,
  action: 'accept' | 'need_info' | 'reject',
) {
  if (!isLeafNode(row)) {
    ElMessage.warning('非叶子需求不允许人工评审');
    return;
  }
  await reviewRequirementApi(row.id, { action });
  ElMessage.success('评审操作成功');
  await refreshAll();
}

async function handleTransition(row: RequirementItem) {
  if (!isLeafNode(row)) {
    ElMessage.warning('非叶子需求不允许人工流转');
    return;
  }
  const nextAction = getNextTransitionAction(row.status);
  if (!nextAction) return;
  await transitionRequirementApi(row.id, { action: nextAction.action });
  ElMessage.success(`${nextAction.label} 成功`);
  await refreshAll();
}

function openTransferReviewerDialog(row: RequirementItem) {
  transferTarget.value = row;
  transferReviewerId.value = row.reviewer_id || '';
  transferNote.value = '';
  transferDialogVisible.value = true;
}

async function submitTransferReviewer() {
  if (!transferTarget.value) return;
  const reviewerId = normalizeSingleUserValue(transferReviewerId.value);
  if (!reviewerId) {
    ElMessage.warning('请选择评审人');
    return;
  }
  transferSubmitting.value = true;
  try {
    await transferReviewerApi(
      transferTarget.value.id,
      reviewerId,
      transferNote.value || '',
    );
    ElMessage.success('转交评审人成功');
    transferDialogVisible.value = false;
    await refreshAll();
  } finally {
    transferSubmitting.value = false;
  }
}

function openAssignOwnerDialog(row: RequirementItem) {
  assignTarget.value = row;
  assignOwnerId.value = row.owner_id || '';
  assignNote.value = '';
  assignDialogVisible.value = true;
}

async function submitAssignOwner() {
  if (!assignTarget.value) return;
  const ownerId = normalizeSingleUserValue(assignOwnerId.value);
  if (!ownerId) {
    ElMessage.warning('请选择责任人');
    return;
  }
  assignSubmitting.value = true;
  try {
    await assignOwnerApi(
      assignTarget.value.id,
      ownerId,
      assignNote.value || '',
    );
    ElMessage.success('分配责任人成功');
    assignDialogVisible.value = false;
    await refreshAll();
  } finally {
    assignSubmitting.value = false;
  }
}

function expandAll() {
  expandedRowKeys.value = collectExpandableIds(treeRows.value);
}

function collapseAll() {
  expandedRowKeys.value = [];
}

function handlePageSizeChange(size: number) {
  pageSize.value = size;
  currentPage.value = 1;
}

onMounted(async () => {
  await loadDictOptions();
  await refreshAll();
});
</script>

<template>
  <Page auto-content-height>
    <div class="requirement-page">
      <ElCard class="hero-card" shadow="never">
        <div class="hero-top">
          <div class="hero-left">
            <div class="hero-title">
              <span class="hero-dot"></span>
              需求控制台 · Tree & Board
            </div>
            <div class="hero-desc">
              统一视图完成树形拆解、状态流转、责任闭环与逾期风险跟踪。
            </div>
            <div class="hero-tags">
              <ElTag type="info">总需求 {{ summary.total_count }}</ElTag>
              <ElTag :type="summary.overdue_count > 0 ? 'danger' : 'success'">
                逾期 {{ summary.overdue_count }}
              </ElTag>
              <ElTag
                :type="summary.review_overdue_count > 0 ? 'danger' : 'success'"
              >
                评审逾期 {{ summary.review_overdue_count }}
              </ElTag>
              <ElTag
                :type="summary.dev_overdue_count > 0 ? 'danger' : 'success'"
              >
                开发逾期 {{ summary.dev_overdue_count }}
              </ElTag>
            </div>
          </div>
          <div class="hero-actions">
            <ElButton @click="goDashboard">
              <IconifyIcon icon="lucide:bar-chart-3" />
              统计看板
            </ElButton>
            <ElButton
              :loading="summaryLoading || treeLoading"
              type="primary"
              @click="refreshAll"
            >
              <IconifyIcon icon="lucide:refresh-cw" />
              刷新
            </ElButton>
          </div>
        </div>
        <div class="metric-grid">
          <div
            v-for="metric in metrics"
            :key="metric.label"
            class="metric-item"
            :class="getMetricClass(metric.tone)"
          >
            <div class="metric-icon-wrap">
              <IconifyIcon :icon="metric.icon" />
            </div>
            <div class="metric-main">
              <div class="metric-label">{{ metric.label }}</div>
              <div class="metric-value">{{ metric.value }}</div>
            </div>
          </div>
        </div>
      </ElCard>

      <ElCard class="filter-card" shadow="never">
        <div class="filter-grid">
          <ElInput
            v-model="filters.keyword"
            clearable
            placeholder="搜索标题/描述/业务价值"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <IconifyIcon icon="lucide:search" />
            </template>
          </ElInput>

          <ElSelect v-model="filters.type" clearable placeholder="需求类型">
            <ElOption
              v-for="option in typeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </ElSelect>

          <ElSelect v-model="filters.source" clearable placeholder="需求来源">
            <ElOption
              v-for="option in sourceOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </ElSelect>

          <ElSelect v-model="filters.priority" clearable placeholder="优先级">
            <ElOption
              v-for="option in priorityOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </ElSelect>

          <UserSelector
            v-model="filters.reviewer_id"
            :multiple="false"
            display-mode="select"
            placeholder="评审人"
          />
          <UserSelector
            v-model="filters.owner_id"
            :multiple="false"
            display-mode="select"
            placeholder="责任人"
          />
          <ElSelect v-model="filters.overdue" clearable placeholder="逾期筛选">
            <ElOption label="全部" value="" />
            <ElOption label="仅逾期" value="true" />
            <ElOption label="仅未逾期" value="false" />
          </ElSelect>
          <ElSelect v-model="filters.status" clearable placeholder="状态筛选">
            <ElOption
              v-for="option in REQUIREMENT_STATUS_OPTIONS"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </ElSelect>
        </div>

        <div class="status-chip-row">
          <div class="chip-title">快捷状态筛选：</div>
          <div class="chip-wrap">
            <button
              v-for="option in REQUIREMENT_STATUS_OPTIONS"
              :key="option.value"
              class="status-chip"
              :class="{ active: filters.status === option.value }"
              type="button"
              @click="handleQuickStatus(option.value)"
            >
              {{ option.label }}
            </button>
          </div>
        </div>

        <ElDivider />

        <div class="action-row">
          <div class="left-actions">
            <ElButton type="primary" @click="handleSearch">查询</ElButton>
            <ElButton @click="handleReset">重置</ElButton>
            <ElButton :loading="loadingDict" @click="openCreateDialog">
              <IconifyIcon icon="lucide:plus" />
              新建需求
            </ElButton>
          </div>
          <div class="right-actions">
            <ElTabs v-model="activeTab" class="view-tabs" type="card">
              <ElTabPane label="树表" name="tree" />
              <ElTabPane label="看板" name="board" />
            </ElTabs>
          </div>
        </div>
      </ElCard>

      <ElCard v-if="focusItems.length > 0" class="focus-card" shadow="never">
        <template #header>
          <div class="focus-header">
            <div class="focus-title">
              <IconifyIcon icon="lucide:flame" />
              风险焦点（逾期优先）
            </div>
            <ElTag type="danger">共 {{ focusItems.length }} 项</ElTag>
          </div>
        </template>
        <div class="focus-grid">
          <button
            v-for="item in focusItems"
            :key="item.id"
            class="focus-item"
            type="button"
            @click="goDetail(item)"
          >
            <div class="focus-item-title">{{ item.title }}</div>
            <div class="focus-item-meta">
              {{ item.is_review_overdue ? '评审逾期' : '开发逾期' }} ·
              {{
                dueCountdownText(
                  item.is_review_overdue ? item.review_due_at : item.dev_due_at,
                )
              }}
            </div>
          </button>
        </div>
      </ElCard>

      <div class="view-wrapper">
        <div v-show="activeTab === 'tree'" class="view-panel">
          <RequirementTreeTable
            :rows="pagedTreeRows"
            :loading="treeLoading"
            v-model:expanded-row-keys="expandedRowKeys"
            :priority-options="priorityOptions"
            @refresh="refreshAll"
            @expand-all="expandAll"
            @collapse-all="collapseAll"
            @detail="goDetail"
            @edit="openEditDialog"
            @split="openSplitDialog"
            @submit="handleSubmit"
            @review="handleReview"
            @transition="handleTransition"
            @transfer-reviewer="openTransferReviewerDialog"
            @assign-owner="openAssignOwnerDialog"
          />
        </div>

        <div v-show="activeTab === 'board'" class="view-panel">
          <RequirementBoard
            :items="pagedBoardItems"
            :loading="treeLoading"
            @detail="goDetail"
            @edit="openEditDialog"
            @split="openSplitDialog"
            @submit="handleSubmit"
            @review="handleReview"
            @transition="handleTransition"
            @transfer-reviewer="openTransferReviewerDialog"
            @assign-owner="openAssignOwnerDialog"
          />
        </div>
      </div>

      <div class="pager-row">
        <ElPagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="pageSizes"
          :total="treeRows.length"
          background
          layout="total, sizes, ->, prev, pager, next, jumper"
          small
          @size-change="handlePageSizeChange"
        />
      </div>

      <ElDialog v-model="dialogVisible" :title="dialogTitle" width="760px">
        <Form />
        <template #footer>
          <ElButton @click="dialogVisible = false">取消</ElButton>
          <ElButton type="primary" @click="submitForm">保存</ElButton>
        </template>
      </ElDialog>

      <ElDialog
        v-model="splitDialogVisible"
        :title="`拆解子需求${splitParent ? ` - ${splitParent.title}` : ''}`"
        width="720px"
      >
        <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
          <ElInput
            v-model="splitForm.title"
            maxlength="255"
            placeholder="请输入子需求标题"
          />
          <ElInput
            v-model="splitForm.priority"
            placeholder="优先级（默认继承父需求）"
          />
          <ElInput
            v-model="splitForm.type"
            placeholder="需求类型（默认继承）"
          />
          <ElInput
            v-model="splitForm.source"
            placeholder="需求来源（默认继承）"
          />
          <UserSelector
            v-model="splitForm.reviewer_id"
            :multiple="false"
            display-mode="select"
            placeholder="评审人（默认继承）"
          />
          <UserSelector
            v-model="splitForm.owner_id"
            :multiple="false"
            display-mode="select"
            placeholder="责任人（默认继承）"
          />
          <ElInput
            v-model="splitForm.description"
            :rows="3"
            class="md:col-span-2"
            placeholder="子需求描述"
            type="textarea"
          />
          <ElInput
            v-model="splitForm.business_value"
            :rows="2"
            class="md:col-span-2"
            placeholder="业务价值"
            type="textarea"
          />
          <ElInput
            v-model="splitForm.acceptance_criteria"
            :rows="2"
            class="md:col-span-2"
            placeholder="验收标准"
            type="textarea"
          />
        </div>
        <template #footer>
          <ElButton @click="splitDialogVisible = false">取消</ElButton>
          <ElButton
            :loading="splitSubmitting"
            type="primary"
            @click="submitSplitForm"
          >
            创建子需求
          </ElButton>
        </template>
      </ElDialog>

      <ElDialog
        v-model="transferDialogVisible"
        title="转交评审人"
        width="520px"
      >
        <div class="batch-form">
          <div class="text-sm text-gray-500">
            {{ transferTarget?.title || '-' }}
          </div>
          <UserSelector
            v-model="transferReviewerId"
            :multiple="false"
            display-mode="select"
            placeholder="选择评审人"
          />
          <ElInput v-model="transferNote" placeholder="备注（可选）" />
        </div>
        <template #footer>
          <ElButton @click="transferDialogVisible = false">取消</ElButton>
          <ElButton
            :loading="transferSubmitting"
            type="primary"
            @click="submitTransferReviewer"
          >
            确定
          </ElButton>
        </template>
      </ElDialog>

      <ElDialog v-model="assignDialogVisible" title="分配责任人" width="520px">
        <div class="batch-form">
          <div class="text-sm text-gray-500">
            {{ assignTarget?.title || '-' }}
          </div>
          <UserSelector
            v-model="assignOwnerId"
            :multiple="false"
            display-mode="select"
            placeholder="选择责任人"
          />
          <ElInput v-model="assignNote" placeholder="备注（可选）" />
        </div>
        <template #footer>
          <ElButton @click="assignDialogVisible = false">取消</ElButton>
          <ElButton
            :loading="assignSubmitting"
            type="primary"
            @click="submitAssignOwner"
          >
            确定
          </ElButton>
        </template>
      </ElDialog>
    </div>
  </Page>
</template>

<style scoped>
.requirement-page {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  gap: 12px;
}

.hero-card {
  border: 1px solid rgb(99 102 241 / 22%);
  background:
    radial-gradient(circle at 15% 0%, rgb(99 102 241 / 18%), transparent 40%),
    radial-gradient(circle at 90% 20%, rgb(59 130 246 / 16%), transparent 44%),
    linear-gradient(135deg, #fff, rgb(248 250 255));
}

.hero-top {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.hero-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
  color: rgb(30 41 59);
}

.hero-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(120deg, #4f46e5, #06b6d4);
  box-shadow: 0 0 0 4px rgb(79 70 229 / 15%);
}

.hero-desc {
  margin-top: 8px;
  max-width: 820px;
  color: rgb(100 116 139);
  font-size: 13px;
}

.hero-tags {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.metric-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.metric-item {
  display: flex;
  align-items: center;
  gap: 10px;
  border-radius: 12px;
  border: 1px solid rgb(148 163 184 / 20%);
  background-image: linear-gradient(135deg, rgb(99 102 241 / 8%), #fff);
  padding: 10px 12px;
}

.metric-icon-wrap {
  display: flex;
  width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: rgb(255 255 255 / 80%);
  box-shadow: inset 0 0 0 1px rgb(148 163 184 / 15%);
}

.metric-main {
  min-width: 0;
}

.metric-label {
  font-size: 12px;
  color: rgb(100 116 139);
}

.metric-value {
  margin-top: 2px;
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
}

.filter-card,
.focus-card {
  border: 1px solid rgb(148 163 184 / 16%);
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.status-chip-row {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.chip-title {
  color: rgb(100 116 139);
  font-size: 12px;
  white-space: nowrap;
}

.chip-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.status-chip {
  border: 1px solid rgb(203 213 225);
  border-radius: 999px;
  padding: 4px 10px;
  background: rgb(248 250 252);
  color: rgb(71 85 105);
  font-size: 12px;
  transition: all 0.2s ease;
}

.status-chip:hover {
  border-color: rgb(99 102 241 / 55%);
  color: rgb(79 70 229);
}

.status-chip.active {
  background: rgb(79 70 229);
  border-color: rgb(79 70 229);
  color: #fff;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.left-actions,
.right-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.view-tabs :deep(.el-tabs__header) {
  margin: 0;
}

.focus-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.focus-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: rgb(30 41 59);
}

.focus-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.focus-item {
  border: 1px solid rgb(148 163 184 / 18%);
  border-radius: 14px;
  padding: 10px 12px;
  background: linear-gradient(140deg, rgb(255 255 255), rgb(248 250 252));
  text-align: left;
  transition: transform 0.18s ease;
}

.focus-item:hover {
  transform: translateY(-2px);
}

.focus-item-title {
  font-weight: 700;
  color: rgb(15 23 42);
  line-height: 1.2;
}

.focus-item-meta {
  margin-top: 6px;
  font-size: 12px;
  color: rgb(100 116 139);
}

.view-wrapper {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.view-panel {
  flex: 1;
  min-height: 0;
}

.pager-row {
  display: flex;
  justify-content: flex-end;
  padding: 12px 6px 0;
}

.batch-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (max-width: 1600px) {
  .metric-grid,
  .focus-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1200px) {
  .filter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .metric-grid,
  .focus-grid,
  .filter-grid {
    grid-template-columns: repeat(1, minmax(0, 1fr));
  }
}
</style>
