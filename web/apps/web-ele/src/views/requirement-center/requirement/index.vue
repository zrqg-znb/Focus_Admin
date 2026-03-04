<script lang="ts" setup>
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
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElEmpty,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElProgress,
  ElScrollbar,
  ElSelect,
  ElSkeleton,
  ElTag,
  ElTooltip,
} from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { getDictItemByCodeApi } from '#/api/core/dict';
import {
  batchArchiveApi,
  batchAssignOwnerApi,
  batchAssignReviewerApi,
  batchPriorityApi,
  createRequirementApi,
  createRequirementChildApi,
  getRequirementDashboardSummaryApi,
  listRequirementTreeApi,
  reviewRequirementApi,
  submitRequirementApi,
  transitionRequirementApi,
  updateRequirementApi,
} from '#/api/requirement-center/requirement';
import UserSelector from '#/components/zq-form/user-selector/user-selector.vue';

import {
  isRequirementLeaf,
  REQUIREMENT_STATUS_OPTIONS,
  useRequirementFormSchema,
} from './data';

defineOptions({ name: 'RequirementCenterList' });

interface BoardLane {
  color: string;
  count: number;
  description: string;
  dot: string;
  items: RequirementBoardItem[];
  label: string;
  status: RequirementStatus;
}

interface OptionItem {
  label: string;
  value: string;
}

interface RequirementBoardItem extends RequirementItem {
  ancestor_titles: string[];
}

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

const loadingDict = ref(false);
const boardLoading = ref(false);
const summaryLoading = ref(false);

const typeOptions = ref<OptionItem[]>([]);
const sourceOptions = ref<OptionItem[]>([]);
const priorityOptions = ref<OptionItem[]>([]);

const boardItems = ref<RequirementBoardItem[]>([]);
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
const splitParent = ref<null | RequirementBoardItem>(null);
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

const [Form, formApi] = useVbenForm({
  schema: useRequirementFormSchema([], [], []),
  showDefaultActions: false,
});

const STATUS_DESCRIPTION: Record<RequirementStatus, string> = {
  accepted: '已通过评审，等待排期推进',
  archived: '流程已结束并归档',
  done: '开发与验收均已完成',
  draft: '草稿态，待补充或提交',
  in_acceptance: '等待业务方验收反馈',
  in_dev: '开发责任人正在推进',
  need_info: '评审要求补充更多信息',
  planned: '已进入排期，待启动开发',
  rejected: '评审驳回，不再推进',
  submitted: '等待评审人处理',
};

const STATUS_THEME: Record<RequirementStatus, { color: string; dot: string }> =
  {
    accepted: {
      color: '#3b82f6',
      dot: 'linear-gradient(135deg, #3b82f6, #60a5fa)',
    },
    archived: {
      color: '#94a3b8',
      dot: 'linear-gradient(135deg, #94a3b8, #cbd5e1)',
    },
    done: {
      color: '#10b981',
      dot: 'linear-gradient(135deg, #10b981, #34d399)',
    },
    draft: {
      color: '#64748b',
      dot: 'linear-gradient(135deg, #64748b, #94a3b8)',
    },
    in_acceptance: {
      color: '#f59e0b',
      dot: 'linear-gradient(135deg, #f59e0b, #fbbf24)',
    },
    in_dev: {
      color: '#6366f1',
      dot: 'linear-gradient(135deg, #6366f1, #818cf8)',
    },
    need_info: {
      color: '#f97316',
      dot: 'linear-gradient(135deg, #f97316, #fb923c)',
    },
    planned: {
      color: '#0ea5e9',
      dot: 'linear-gradient(135deg, #0ea5e9, #38bdf8)',
    },
    rejected: {
      color: '#ef4444',
      dot: 'linear-gradient(135deg, #ef4444, #f87171)',
    },
    submitted: {
      color: '#8b5cf6',
      dot: 'linear-gradient(135deg, #8b5cf6, #a78bfa)',
    },
  };

const STATUS_PROGRESS: RequirementStatus[] = [
  'draft',
  'submitted',
  'accepted',
  'planned',
  'in_dev',
  'in_acceptance',
  'done',
  'archived',
];

const laneList = computed<BoardLane[]>(() =>
  REQUIREMENT_STATUS_OPTIONS.map((statusOption) => {
    const status = statusOption.value;
    return {
      color: STATUS_THEME[status].color,
      count: boardItems.value.filter((item) => item.status === status).length,
      description: STATUS_DESCRIPTION[status],
      dot: STATUS_THEME[status].dot,
      items: boardItems.value.filter((item) => item.status === status),
      label: statusOption.label,
      status,
    };
  }),
);

const focusItems = computed(() =>
  [...boardItems.value]
    .filter((item) => item.is_review_overdue || item.is_dev_overdue)
    .slice(0, 8),
);

const totalBoardCount = computed(() => boardItems.value.length);

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

function parseIdText(value: string): string[] {
  return String(value || '')
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function toAttachmentText(attachments?: string[]) {
  return Array.isArray(attachments) ? attachments.join(',') : '';
}

function isLeafNode(row: RequirementItem) {
  return isRequirementLeaf(row);
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

function getReviewerLabel(row: RequirementItem) {
  return row.reviewer_info?.name || row.reviewer_info?.username || '-';
}

function getOwnerLabel(row: RequirementItem) {
  return row.owner_info?.name || row.owner_info?.username || '-';
}

function getDisplayNameInitial(name: string) {
  const text = String(name || '').trim();
  if (!text) return '?';
  return text.slice(0, 1).toUpperCase();
}

function canSplitRequirement(row: RequirementItem) {
  return ['accepted', 'in_acceptance', 'in_dev', 'planned'].includes(
    row.status,
  );
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

function getProgressPercent(status: RequirementStatus) {
  const index = STATUS_PROGRESS.indexOf(status);
  if (index === -1) return 12;
  return Math.max(12, Math.round(((index + 1) / STATUS_PROGRESS.length) * 100));
}

function formatDateText(value?: null | string) {
  if (!value) return '-';
  return String(value).replace('T', ' ').slice(0, 16);
}

function dueCountdownText(value?: null | string) {
  if (!value) return '未设置截止时间';
  const target = new Date(value).getTime();
  if (Number.isNaN(target)) return '截止时间格式异常';
  const diff = target - Date.now();
  const day = Math.ceil(diff / (24 * 60 * 60 * 1000));
  if (day > 0) return `剩余 ${day} 天`;
  if (day === 0) return '今天到期';
  return `逾期 ${Math.abs(day)} 天`;
}

function normalizeSingleUserValue(value: '' | UserSelectorValue) {
  if (!value) return '';
  if (Array.isArray(value)) return String(value[0] || '').trim();
  return String(value || '').trim();
}

function flattenTree(
  nodes: RequirementItem[] = [],
  ancestors: string[] = [],
): RequirementBoardItem[] {
  const results: RequirementBoardItem[] = [];
  for (const node of nodes) {
    results.push({
      ...node,
      ancestor_titles: ancestors,
    });
    const childNodes = Array.isArray(node.children) ? node.children : [];
    if (childNodes.length > 0) {
      results.push(...flattenTree(childNodes, [...ancestors, node.title]));
    }
  }
  return results;
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

async function loadBoard() {
  boardLoading.value = true;
  try {
    const treeRows = await listRequirementTreeApi(buildFilterParams());
    boardItems.value = flattenTree(treeRows || []);
  } catch {
    boardItems.value = [];
    ElMessage.error('加载需求看板失败');
  } finally {
    boardLoading.value = false;
  }
}

async function refreshAll() {
  await Promise.all([loadSummary(), loadBoard()]);
}

async function handleSearch() {
  await loadBoard();
}

async function handleQuickStatus(status: RequirementStatus) {
  filters.value.status = filters.value.status === status ? '' : status;
  await loadBoard();
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
  await loadBoard();
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

function openSplitDialog(row: RequirementBoardItem) {
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

function goDetail(row: RequirementItem) {
  router.push(`/requirement-center/requirement/detail/${row.id}`);
}

function goDashboard() {
  router.push('/requirement-center/requirement/dashboard');
}

async function promptRequirementIds() {
  const result = await ElMessageBox.prompt(
    '请输入需求ID（多个逗号分隔）',
    '批量操作',
    {
      confirmButtonText: '确定',
      inputPlaceholder: '例如: id1,id2,id3',
      type: 'warning',
    },
  );
  const ids = parseIdText(result.value);
  if (ids.length === 0) {
    ElMessage.warning('请输入至少一个需求ID');
    return [];
  }
  return ids;
}

async function handleBatchAssignReviewer() {
  const ids = await promptRequirementIds();
  if (ids.length === 0) return;

  const reviewerResult = await ElMessageBox.prompt(
    '请输入评审人ID',
    '批量分配评审人',
    {
      confirmButtonText: '确定',
    },
  );
  const reviewerId = String(reviewerResult.value || '').trim();
  if (!reviewerId) return;

  const response = await batchAssignReviewerApi({
    requirement_ids: ids,
    reviewer_id: reviewerId,
  });
  ElMessage.success(`${response.msg}，成功 ${response.count} 条`);
  await refreshAll();
}

async function handleBatchAssignOwner() {
  const ids = await promptRequirementIds();
  if (ids.length === 0) return;

  const ownerResult = await ElMessageBox.prompt(
    '请输入责任人ID',
    '批量分配责任人',
    {
      confirmButtonText: '确定',
    },
  );
  const ownerId = String(ownerResult.value || '').trim();
  if (!ownerId) return;

  const response = await batchAssignOwnerApi({
    owner_id: ownerId,
    requirement_ids: ids,
  });
  ElMessage.success(`${response.msg}，成功 ${response.count} 条`);
  await refreshAll();
}

async function handleBatchPriority() {
  const ids = await promptRequirementIds();
  if (ids.length === 0) return;

  const priorityResult = await ElMessageBox.prompt(
    '请输入优先级值（如 high/medium/low/urgent）',
    '批量调整优先级',
    {
      confirmButtonText: '确定',
    },
  );
  const priority = String(priorityResult.value || '').trim();
  if (!priority) return;

  const response = await batchPriorityApi({
    priority,
    requirement_ids: ids,
  });
  ElMessage.success(`${response.msg}，成功 ${response.count} 条`);
  await refreshAll();
}

async function handleBatchArchive() {
  const ids = await promptRequirementIds();
  if (ids.length === 0) return;

  const response = await batchArchiveApi({
    requirement_ids: ids,
  });
  ElMessage.success(`${response.msg}，成功 ${response.count} 条`);
  await refreshAll();
}

async function handleBatchCommand(command: string) {
  if (command === 'assign-reviewer') return handleBatchAssignReviewer();
  if (command === 'assign-owner') return handleBatchAssignOwner();
  if (command === 'priority') return handleBatchPriority();
  if (command === 'archive') return handleBatchArchive();
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
              需求控制台 · Design Board
            </div>
            <div class="hero-desc">
              聚焦树形拆解、状态流转、责任闭环与逾期风险，统一在同一视图完成推进。
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
              :loading="summaryLoading || boardLoading"
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
            <ElDropdown trigger="click" @command="handleBatchCommand">
              <ElButton>
                批量操作
                <IconifyIcon icon="lucide:chevron-down" />
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
                  <ElDropdownItem command="archive">批量归档</ElDropdownItem>
                </ElDropdownMenu>
              </template>
            </ElDropdown>
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

      <div class="board-wrapper">
        <ElCard class="board-card" shadow="never">
          <template #header>
            <div class="board-header">
              <div class="board-title">
                <IconifyIcon icon="lucide:layout-panel-top" />
                需求设计看板
              </div>
              <ElTag type="info">共 {{ totalBoardCount }} 项</ElTag>
            </div>
          </template>

          <ElSkeleton :loading="boardLoading" animated>
            <template #default>
              <div v-if="totalBoardCount === 0" class="board-empty">
                <ElEmpty description="当前没有符合筛选条件的需求" />
              </div>
              <ElScrollbar v-else class="board-scrollbar">
                <div class="lane-row">
                  <section
                    v-for="lane in laneList"
                    :key="lane.status"
                    class="lane"
                    :style="{ '--lane-color': lane.color }"
                  >
                    <header class="lane-header">
                      <div class="lane-header-main">
                        <span
                          class="lane-dot"
                          :style="{ background: lane.dot }"
                        ></span>
                        <div class="lane-title-wrap">
                          <div class="lane-title">{{ lane.label }}</div>
                          <div class="lane-desc">{{ lane.description }}</div>
                        </div>
                      </div>
                      <ElTag size="small" :type="getStatusTagType(lane.status)">
                        {{ lane.count }}
                      </ElTag>
                    </header>

                    <div class="lane-content">
                      <ElEmpty
                        v-if="lane.items.length === 0"
                        :image-size="42"
                        description="暂无"
                      />

                      <article
                        v-for="item in lane.items"
                        :key="item.id"
                        class="requirement-card"
                      >
                        <div class="card-head">
                          <div class="card-head-left">
                            <ElTag size="small" type="info">
                              L{{ item.level || 0 }}
                            </ElTag>
                            <ElTag
                              v-if="!isLeafNode(item)"
                              size="small"
                              type="warning"
                            >
                              父需求
                            </ElTag>
                          </div>
                          <div class="card-head-right">
                            <ElTag
                              size="small"
                              :type="getPriorityTagType(item.priority)"
                            >
                              {{ item.priority || '-' }}
                            </ElTag>
                          </div>
                        </div>

                        <div class="card-title" :title="item.title">
                          {{ item.title }}
                        </div>

                        <div v-if="item.description" class="card-desc">
                          {{ item.description }}
                        </div>

                        <div
                          v-if="item.ancestor_titles.length > 0"
                          class="ancestor-chain"
                        >
                          <span class="ancestor-label">链路</span>
                          <span
                            v-for="(ancestor, index) in item.ancestor_titles"
                            :key="`${item.id}-${ancestor}-${index}`"
                            class="ancestor-item"
                          >
                            {{ ancestor }}
                          </span>
                        </div>

                        <div class="card-chip-row">
                          <span class="chip">{{ item.type || '未分类' }}</span>
                          <span class="chip">{{
                            item.source || '未标注来源'
                          }}</span>
                          <span v-if="!isLeafNode(item)" class="chip warning">
                            子需求 {{ item.child_count || 0 }}
                          </span>
                        </div>

                        <div class="card-users">
                          <div class="user-pill">
                            <span class="avatar-badge">
                              {{
                                getDisplayNameInitial(getReviewerLabel(item))
                              }}
                            </span>
                            <span class="label-text">
                              评审 {{ getReviewerLabel(item) }}
                            </span>
                          </div>
                          <div class="user-pill">
                            <span class="avatar-badge">
                              {{ getDisplayNameInitial(getOwnerLabel(item)) }}
                            </span>
                            <span class="label-text">
                              责任 {{ getOwnerLabel(item) }}
                            </span>
                          </div>
                        </div>

                        <div class="due-row">
                          <div
                            class="due-item"
                            :class="{ danger: item.is_review_overdue }"
                          >
                            <div class="due-label">评审截止</div>
                            <div class="due-value">
                              {{ formatDateText(item.review_due_at) }}
                            </div>
                            <div class="due-tip">
                              {{ dueCountdownText(item.review_due_at) }}
                            </div>
                          </div>
                          <div
                            class="due-item"
                            :class="{ danger: item.is_dev_overdue }"
                          >
                            <div class="due-label">开发截止</div>
                            <div class="due-value">
                              {{ formatDateText(item.dev_due_at) }}
                            </div>
                            <div class="due-tip">
                              {{ dueCountdownText(item.dev_due_at) }}
                            </div>
                          </div>
                        </div>

                        <div class="progress-wrap">
                          <ElProgress
                            :percentage="getProgressPercent(item.status)"
                            :show-text="false"
                            :color="lane.color"
                            :stroke-width="6"
                          />
                        </div>

                        <div class="card-actions">
                          <div class="main-actions">
                            <ElTooltip content="查看详情" placement="top">
                              <ElButton
                                circle
                                link
                                size="small"
                                type="primary"
                                @click="goDetail(item)"
                              >
                                <IconifyIcon icon="lucide:eye" />
                              </ElButton>
                            </ElTooltip>
                            <ElTooltip content="编辑需求" placement="top">
                              <ElButton
                                circle
                                link
                                size="small"
                                @click="openEditDialog(item)"
                              >
                                <IconifyIcon icon="lucide:pencil-line" />
                              </ElButton>
                            </ElTooltip>
                            <ElTooltip
                              v-if="canSplitRequirement(item)"
                              content="拆解子需求"
                              placement="top"
                            >
                              <ElButton
                                circle
                                link
                                size="small"
                                type="primary"
                                @click="openSplitDialog(item)"
                              >
                                <IconifyIcon icon="lucide:git-fork" />
                              </ElButton>
                            </ElTooltip>
                          </div>

                          <div class="flow-actions">
                            <ElButton
                              v-if="
                                isLeafNode(item) &&
                                (item.status === 'draft' ||
                                  item.status === 'need_info')
                              "
                              size="small"
                              type="warning"
                              @click="handleSubmit(item)"
                            >
                              提交评审
                            </ElButton>
                            <template
                              v-if="
                                isLeafNode(item) && item.status === 'submitted'
                              "
                            >
                              <ElButton
                                size="small"
                                type="success"
                                @click="handleReview(item, 'accept')"
                              >
                                通过
                              </ElButton>
                              <ElButton
                                size="small"
                                type="warning"
                                @click="handleReview(item, 'need_info')"
                              >
                                补充
                              </ElButton>
                              <ElButton
                                size="small"
                                type="danger"
                                @click="handleReview(item, 'reject')"
                              >
                                驳回
                              </ElButton>
                            </template>
                            <ElButton
                              v-if="
                                isLeafNode(item) &&
                                getNextTransitionAction(item.status)
                              "
                              size="small"
                              type="primary"
                              @click="handleTransition(item)"
                            >
                              {{ getNextTransitionAction(item.status)?.label }}
                            </ElButton>
                          </div>
                        </div>
                      </article>
                    </div>
                  </section>
                </div>
              </ElScrollbar>
            </template>
          </ElSkeleton>
        </ElCard>
      </div>
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
        <ElInput v-model="splitForm.type" placeholder="需求类型（默认继承）" />
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
.focus-card,
.board-card {
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

.focus-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.focus-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: rgb(30 41 59);
}

.focus-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.focus-item {
  text-align: left;
  border: 1px solid rgb(254 205 211);
  background: linear-gradient(135deg, rgb(255 241 242), #fff);
  border-radius: 10px;
  padding: 8px 10px;
  transition: all 0.2s ease;
}

.focus-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 20px rgb(244 63 94 / 10%);
}

.focus-item-title {
  font-size: 13px;
  font-weight: 600;
  color: rgb(15 23 42);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.focus-item-meta {
  margin-top: 4px;
  font-size: 11px;
  color: rgb(190 24 93);
}

.board-wrapper {
  min-height: 0;
  flex: 1;
}

.board-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.board-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: rgb(30 41 59);
}

.board-empty {
  min-height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.board-scrollbar {
  min-height: 420px;
  height: calc(100vh - 420px);
}

.lane-row {
  display: flex;
  gap: 12px;
  padding-bottom: 2px;
}

.lane {
  width: 332px;
  min-width: 332px;
  border: 1px solid color-mix(in srgb, var(--lane-color) 18%, #e2e8f0);
  border-radius: 14px;
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--lane-color) 8%, #fff),
    #fff 120px
  );
}

.lane-header {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 10px;
  border-bottom: 1px solid rgb(226 232 240);
  background: rgb(255 255 255 / 85%);
  backdrop-filter: blur(6px);
  border-radius: 14px 14px 0 0;
}

.lane-header-main {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.lane-dot {
  width: 11px;
  height: 11px;
  border-radius: 999px;
  margin-top: 4px;
}

.lane-title {
  font-size: 13px;
  font-weight: 700;
  color: rgb(30 41 59);
}

.lane-desc {
  margin-top: 2px;
  font-size: 11px;
  color: rgb(100 116 139);
  line-height: 1.3;
}

.lane-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px;
}

.requirement-card {
  border: 1px solid rgb(226 232 240);
  border-radius: 12px;
  background: #fff;
  padding: 10px;
  transition: all 0.22s ease;
}

.requirement-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 24px rgb(15 23 42 / 8%);
  border-color: color-mix(in srgb, var(--lane-color) 48%, #dbeafe);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.card-head-left,
.card-head-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.card-title {
  margin-top: 8px;
  font-size: 14px;
  font-weight: 700;
  color: rgb(15 23 42);
  line-height: 1.35;
}

.card-desc {
  margin-top: 6px;
  font-size: 12px;
  color: rgb(100 116 139);
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.ancestor-chain {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ancestor-label {
  font-size: 11px;
  color: rgb(100 116 139);
}

.ancestor-item {
  font-size: 11px;
  border-radius: 999px;
  padding: 1px 8px;
  background: rgb(239 246 255);
  color: rgb(30 64 175);
}

.card-chip-row {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  background: rgb(248 250 252);
  color: rgb(71 85 105);
  border: 1px solid rgb(226 232 240);
  padding: 2px 8px;
  font-size: 11px;
}

.chip.warning {
  background: rgb(255 251 235);
  border-color: rgb(253 230 138);
  color: rgb(180 83 9);
}

.card-users {
  margin-top: 9px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 5px;
}

.user-pill {
  display: flex;
  align-items: center;
  gap: 7px;
}

.avatar-badge {
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: linear-gradient(
    135deg,
    rgb(79 70 229 / 18%),
    rgb(14 165 233 / 16%)
  );
  color: rgb(51 65 85);
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
}

.label-text {
  font-size: 12px;
  color: rgb(51 65 85);
}

.due-row {
  margin-top: 8px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.due-item {
  border: 1px solid rgb(226 232 240);
  border-radius: 10px;
  padding: 6px 7px;
  background: rgb(248 250 252 / 70%);
}

.due-item.danger {
  border-color: rgb(252 165 165);
  background: rgb(255 241 242);
}

.due-label {
  font-size: 10px;
  color: rgb(100 116 139);
}

.due-value {
  margin-top: 2px;
  font-size: 11px;
  color: rgb(30 41 59);
}

.due-tip {
  margin-top: 2px;
  font-size: 10px;
  color: rgb(71 85 105);
}

.due-item.danger .due-tip {
  color: rgb(190 24 93);
}

.progress-wrap {
  margin-top: 9px;
}

.card-actions {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.main-actions {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 2px;
}

.flow-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
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

  .board-scrollbar {
    height: calc(100vh - 380px);
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
