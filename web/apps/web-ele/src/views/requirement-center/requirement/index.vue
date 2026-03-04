<script lang="ts" setup>
import type {
  RequirementDashboardSummary,
  RequirementItem,
  RequirementStatus,
} from '#/api/requirement-center/requirement';

import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElCard,
  ElDialog,
  ElEmpty,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElScrollbar,
  ElSelect,
  ElSkeleton,
  ElTag,
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
  items: RequirementBoardItem[];
  label: string;
  value: RequirementStatus;
}

interface OptionItem {
  label: string;
  value: string;
}

interface RequirementBoardItem extends RequirementItem {
  ancestor_titles: string[];
}

interface RequirementFilterForm {
  keyword: string;
  overdue: '' | 'false' | 'true';
  owner_id: any;
  priority: string;
  reviewer_id: any;
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

const boardLanes = computed<BoardLane[]>(() =>
  REQUIREMENT_STATUS_OPTIONS.map((statusOption) => ({
    items: boardItems.value.filter(
      (item) => item.status === statusOption.value,
    ),
    label: statusOption.label,
    value: statusOption.value,
  })),
);

const totalBoardCount = computed(() => boardItems.value.length);

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

function isLeafNode(row: RequirementItem) {
  return isRequirementLeaf(row);
}

function getReviewerLabel(row: RequirementItem) {
  return row.reviewer_info?.name || row.reviewer_info?.username || '-';
}

function getOwnerLabel(row: RequirementItem) {
  return row.owner_info?.name || row.owner_info?.username || '-';
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
  if (status === 'accepted')
    return { action: 'planned', label: '推进到已排期' };
  if (status === 'planned') return { action: 'in_dev', label: '推进到开发中' };
  if (status === 'in_dev')
    return { action: 'in_acceptance', label: '推进到待验收' };
  if (status === 'in_acceptance')
    return { action: 'done', label: '推进到已完成' };
  if (status === 'done' || status === 'rejected') {
    return { action: 'archive', label: '归档' };
  }
  return null;
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
  const reviewerId = Array.isArray(form.reviewer_id)
    ? String(form.reviewer_id[0] || '')
    : String(form.reviewer_id || '');
  const ownerId = Array.isArray(form.owner_id)
    ? String(form.owner_id[0] || '')
    : String(form.owner_id || '');

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
    ElMessage.error('加载需求卡片看板失败');
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

onMounted(async () => {
  await loadDictOptions();
  await refreshAll();
});
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full min-h-0 flex-col gap-3">
      <ElCard class="requirement-hero-card" shadow="never">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div class="text-base font-semibold">需求中心 · 卡片看板</div>
            <div class="mt-1 text-sm text-gray-500">
              支持树形拆解、状态联动、责任到人的全流程闭环
            </div>
            <div class="mt-3 flex items-center gap-2">
              <ElTag type="info">总量 {{ summary.total_count }}</ElTag>
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
          <div class="flex items-center gap-2">
            <ElButton @click="goDashboard">详细看板</ElButton>
            <ElButton
              :loading="summaryLoading || boardLoading"
              type="primary"
              @click="refreshAll"
            >
              刷新
            </ElButton>
          </div>
        </div>
      </ElCard>

      <ElCard class="filter-card" shadow="never">
        <div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <ElInput
            v-model="filters.keyword"
            clearable
            placeholder="关键词（标题/描述/业务价值）"
            @keyup.enter="handleSearch"
          />
          <ElSelect v-model="filters.status" clearable placeholder="状态">
            <ElOption
              v-for="option in REQUIREMENT_STATUS_OPTIONS"
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
        </div>

        <div class="mt-3 flex flex-wrap items-center gap-2">
          <ElButton type="primary" @click="handleSearch">查询</ElButton>
          <ElButton @click="handleReset">重置</ElButton>
          <ElButton :loading="loadingDict" @click="openCreateDialog">
            新建需求
          </ElButton>
          <ElButton @click="handleBatchAssignReviewer">批量分配评审人</ElButton>
          <ElButton @click="handleBatchAssignOwner">批量分配责任人</ElButton>
          <ElButton @click="handleBatchPriority">批量改优先级</ElButton>
          <ElButton type="warning" @click="handleBatchArchive">
            批量归档
          </ElButton>
        </div>
      </ElCard>

      <div class="min-h-0 flex-1">
        <ElCard class="board-card h-full" shadow="never">
          <template #header>
            <div class="flex items-center justify-between">
              <span class="font-medium">需求卡片看板</span>
              <ElTag type="info">共 {{ totalBoardCount }} 项</ElTag>
            </div>
          </template>

          <ElSkeleton :loading="boardLoading" animated>
            <template #default>
              <div v-if="totalBoardCount === 0" class="board-empty">
                <ElEmpty description="暂无需求数据，可先新建需求" />
              </div>
              <ElScrollbar v-else class="board-scrollbar">
                <div class="board-lanes">
                  <div
                    v-for="lane in boardLanes"
                    :key="lane.value"
                    class="board-lane"
                  >
                    <div class="lane-header">
                      <div class="lane-title">{{ lane.label }}</div>
                      <ElTag size="small" :type="getStatusTagType(lane.value)">
                        {{ lane.items.length }}
                      </ElTag>
                    </div>
                    <div class="lane-content">
                      <ElEmpty
                        v-if="lane.items.length === 0"
                        :image-size="40"
                        description="暂无"
                      />
                      <div
                        v-for="row in lane.items"
                        :key="row.id"
                        class="requirement-card"
                      >
                        <div class="card-title-row">
                          <div class="card-title" :title="row.title">
                            {{ row.title }}
                          </div>
                          <ElTag size="small" type="info">
                            L{{ row.level || 0 }}
                          </ElTag>
                        </div>

                        <div
                          v-if="row.ancestor_titles.length > 0"
                          class="card-path"
                          :title="row.ancestor_titles.join(' / ')"
                        >
                          来源链路：{{ row.ancestor_titles.join(' / ') }}
                        </div>

                        <div class="card-tags">
                          <ElTag
                            size="small"
                            :type="getPriorityTagType(row.priority)"
                          >
                            {{ row.priority || '-' }}
                          </ElTag>
                          <ElTag size="small" type="info">
                            {{ row.type || '未分类' }}
                          </ElTag>
                          <ElTag size="small" type="info">
                            {{ row.source || '未标注来源' }}
                          </ElTag>
                          <ElTag
                            v-if="!isLeafNode(row)"
                            size="small"
                            type="warning"
                          >
                            父需求 · {{ row.child_count || 0 }}
                          </ElTag>
                        </div>

                        <div class="card-meta-row">
                          <span>评审：{{ getReviewerLabel(row) }}</span>
                        </div>
                        <div class="card-meta-row">
                          <span>责任：{{ getOwnerLabel(row) }}</span>
                        </div>
                        <div
                          class="card-meta-row"
                          :class="{ danger: row.is_review_overdue }"
                        >
                          <span>评审截止：{{ row.review_due_at || '-' }}</span>
                        </div>
                        <div
                          class="card-meta-row"
                          :class="{ danger: row.is_dev_overdue }"
                        >
                          <span>开发截止：{{ row.dev_due_at || '-' }}</span>
                        </div>

                        <div class="card-actions">
                          <ElButton
                            link
                            size="small"
                            type="primary"
                            @click="goDetail(row)"
                          >
                            详情
                          </ElButton>
                          <ElButton
                            link
                            size="small"
                            @click="openEditDialog(row)"
                          >
                            编辑
                          </ElButton>

                          <ElButton
                            v-if="
                              isLeafNode(row) &&
                              (row.status === 'draft' ||
                                row.status === 'need_info')
                            "
                            link
                            size="small"
                            type="warning"
                            @click="handleSubmit(row)"
                          >
                            提交
                          </ElButton>

                          <ElButton
                            v-if="isLeafNode(row) && row.status === 'submitted'"
                            link
                            size="small"
                            type="success"
                            @click="handleReview(row, 'accept')"
                          >
                            通过
                          </ElButton>
                          <ElButton
                            v-if="isLeafNode(row) && row.status === 'submitted'"
                            link
                            size="small"
                            type="warning"
                            @click="handleReview(row, 'need_info')"
                          >
                            补充
                          </ElButton>
                          <ElButton
                            v-if="isLeafNode(row) && row.status === 'submitted'"
                            link
                            size="small"
                            type="danger"
                            @click="handleReview(row, 'reject')"
                          >
                            驳回
                          </ElButton>

                          <ElButton
                            v-if="
                              isLeafNode(row) &&
                              getNextTransitionAction(row.status)
                            "
                            link
                            size="small"
                            type="primary"
                            @click="handleTransition(row)"
                          >
                            {{ getNextTransitionAction(row.status)?.label }}
                          </ElButton>

                          <ElButton
                            v-if="canSplitRequirement(row)"
                            link
                            size="small"
                            type="primary"
                            @click="openSplitDialog(row)"
                          >
                            拆解子需求
                          </ElButton>
                        </div>
                      </div>
                    </div>
                  </div>
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
.requirement-hero-card {
  border: 1px solid rgb(99 102 241 / 18%);
  background: linear-gradient(135deg, rgb(99 102 241 / 10%), rgb(255 255 255));
}

.filter-card {
  border: 1px solid rgb(148 163 184 / 14%);
}

.board-card {
  border: 1px solid rgb(148 163 184 / 14%);
}

.board-empty {
  display: flex;
  min-height: 320px;
  align-items: center;
  justify-content: center;
}

.board-scrollbar {
  height: calc(100vh - 370px);
  min-height: 360px;
}

.board-lanes {
  display: flex;
  gap: 12px;
  min-height: 100%;
  padding-bottom: 2px;
}

.board-lane {
  display: flex;
  width: 300px;
  min-width: 300px;
  flex-direction: column;
  border: 1px solid rgb(148 163 184 / 18%);
  border-radius: 12px;
  background: rgb(248 250 252 / 90%);
}

.lane-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid rgb(148 163 184 / 16%);
}

.lane-title {
  font-size: 13px;
  font-weight: 600;
  color: rgb(51 65 85);
}

.lane-content {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 10px;
  padding: 10px;
}

.requirement-card {
  border: 1px solid rgb(148 163 184 / 16%);
  border-radius: 10px;
  background: #fff;
  padding: 10px;
  transition: all 0.2s ease;
}

.requirement-card:hover {
  transform: translateY(-1px);
  border-color: rgb(99 102 241 / 40%);
  box-shadow: 0 8px 20px rgb(15 23 42 / 8%);
}

.card-title-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.card-title {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-weight: 600;
  color: rgb(30 41 59);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-path {
  margin-top: 6px;
  font-size: 11px;
  color: rgb(100 116 139);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-tags {
  margin-top: 8px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.card-meta-row {
  margin-top: 6px;
  font-size: 12px;
  color: rgb(71 85 105);
}

.card-meta-row.danger {
  color: rgb(220 38 38);
}

.card-actions {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
</style>
