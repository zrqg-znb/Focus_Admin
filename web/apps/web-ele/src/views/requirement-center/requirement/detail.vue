<script lang="ts" setup>
import type {
  RequirementComment,
  RequirementItem,
  RequirementLogItem,
} from '#/api/requirement-center/requirement';

import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElCard,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElInput,
  ElMessage,
  ElTag,
  ElTimeline,
  ElTimelineItem,
} from 'element-plus';

import {
  createRequirementChildApi,
  createRequirementCommentApi,
  getRequirementApi,
  listRequirementChildrenApi,
  listRequirementCommentsApi,
  listRequirementLogsApi,
  reviewRequirementApi,
  submitRequirementApi,
  transitionRequirementApi,
} from '#/api/requirement-center/requirement';
import UserSelector from '#/components/zq-form/user-selector/user-selector.vue';

import { getStatusLabel } from './data';

defineOptions({ name: 'RequirementCenterDetail' });

const route = useRoute();
const router = useRouter();
const requirementId = computed(() => String(route.params.id || ''));

const loading = ref(false);
const detail = ref<null | RequirementItem>(null);
const comments = ref<RequirementComment[]>([]);
const logs = ref<RequirementLogItem[]>([]);
const children = ref<RequirementItem[]>([]);
const commentText = ref('');
const mentionUserIds = ref<string[]>([]);

const splitDialogVisible = ref(false);
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

async function loadDetail() {
  if (!requirementId.value) return;
  loading.value = true;
  try {
    const [detailData, commentData, logData, childData] = await Promise.all([
      getRequirementApi(requirementId.value),
      listRequirementCommentsApi(requirementId.value),
      listRequirementLogsApi(requirementId.value),
      listRequirementChildrenApi(requirementId.value),
    ]);
    detail.value = detailData;
    comments.value = commentData || [];
    logs.value = logData || [];
    children.value = childData || [];
  } finally {
    loading.value = false;
  }
}

function getStatusTagType(status?: string) {
  if (status === 'done') return 'success';
  if (status === 'rejected') return 'danger';
  if (status === 'archived') return 'info';
  if (status === 'submitted' || status === 'in_acceptance') return 'warning';
  return 'primary';
}

async function handleSubmit() {
  if (!detail.value) return;
  if (!isLeafNode.value) {
    ElMessage.warning('非叶子需求不允许人工提交流转');
    return;
  }
  await submitRequirementApi(detail.value.id);
  ElMessage.success('提交成功');
  await loadDetail();
}

async function handleReview(action: 'accept' | 'need_info' | 'reject') {
  if (!detail.value) return;
  if (!isLeafNode.value) {
    ElMessage.warning('非叶子需求不允许人工评审');
    return;
  }
  await reviewRequirementApi(detail.value.id, { action });
  ElMessage.success('评审操作成功');
  await loadDetail();
}

async function handleTransition(
  action: 'archive' | 'done' | 'in_acceptance' | 'in_dev' | 'planned',
) {
  if (!detail.value) return;
  if (!isLeafNode.value) {
    ElMessage.warning('非叶子需求不允许人工流转');
    return;
  }
  await transitionRequirementApi(detail.value.id, { action });
  ElMessage.success('状态流转成功');
  await loadDetail();
}

async function handleCommentSubmit() {
  if (!detail.value) return;
  const content = commentText.value.trim();
  if (!content) {
    ElMessage.warning('请输入评论内容');
    return;
  }
  const mentionIds = [
    ...new Set(
      (Array.isArray(mentionUserIds.value) ? mentionUserIds.value : [])
        .map((item) => String(item || '').trim())
        .filter(Boolean),
    ),
  ];
  await createRequirementCommentApi(detail.value.id, content, mentionIds);
  commentText.value = '';
  mentionUserIds.value = [];
  ElMessage.success('评论成功');
  await loadDetail();
}

const isLeafNode = computed(() => {
  if (!detail.value) return true;
  if (typeof detail.value.is_leaf === 'boolean') {
    return detail.value.is_leaf;
  }
  return !(detail.value.child_count || 0);
});

const parentPathIds = computed(() => {
  const pathText = detail.value?.tree_path || '';
  if (!pathText) return [];
  const ids = pathText.split('/').filter(Boolean);
  if (ids.length <= 1) return [];
  return ids.slice(0, -1);
});

function canSplitRequirement(row: null | RequirementItem) {
  if (!row) return false;
  return ['accepted', 'in_acceptance', 'in_dev', 'planned'].includes(
    row.status,
  );
}

function openSplitDialog() {
  if (!detail.value) return;
  splitForm.value = {
    acceptance_criteria: '',
    business_value: '',
    description: '',
    owner_id: detail.value.owner_id || '',
    priority: detail.value.priority || '',
    reviewer_id: detail.value.reviewer_id || '',
    source: detail.value.source || '',
    title: '',
    type: detail.value.type || '',
  };
  splitDialogVisible.value = true;
}

async function submitSplitForm() {
  if (!detail.value) return;
  const title = splitForm.value.title.trim();
  if (!title) {
    ElMessage.warning('请输入子需求标题');
    return;
  }
  splitSubmitting.value = true;
  try {
    await createRequirementChildApi(detail.value.id, {
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
    await loadDetail();
  } finally {
    splitSubmitting.value = false;
  }
}

onMounted(loadDetail);
</script>

<template>
  <Page auto-content-height>
    <ElCard class="detail-hero-card mb-3" shadow="never">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div class="text-base font-semibold">
            {{ detail?.title || '需求详情' }}
          </div>
          <div class="mt-1 text-sm text-gray-500">
            ID：{{ detail?.id || '-' }}
          </div>
          <div class="mt-3 flex flex-wrap items-center gap-2">
            <ElTag :type="getStatusTagType(detail?.status)">
              {{ detail ? getStatusLabel(detail.status) : '-' }}
            </ElTag>
            <ElTag type="info">优先级 {{ detail?.priority || '-' }}</ElTag>
            <ElTag :type="isLeafNode ? 'success' : 'warning'">
              {{ isLeafNode ? '叶子需求' : '父需求' }}
            </ElTag>
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <ElButton @click="router.push('/requirement-center/requirement')">
            返回列表
          </ElButton>
          <ElButton
            v-if="
              detail &&
              isLeafNode &&
              (detail.status === 'draft' || detail.status === 'need_info')
            "
            type="warning"
            @click="handleSubmit"
          >
            提交评审
          </ElButton>
          <ElButton
            v-if="detail && isLeafNode && detail.status === 'submitted'"
            type="success"
            @click="handleReview('accept')"
          >
            评审通过
          </ElButton>
          <ElButton
            v-if="detail && isLeafNode && detail.status === 'submitted'"
            type="warning"
            @click="handleReview('need_info')"
          >
            需补充
          </ElButton>
          <ElButton
            v-if="detail && isLeafNode && detail.status === 'submitted'"
            type="danger"
            @click="handleReview('reject')"
          >
            驳回
          </ElButton>
          <ElButton
            v-if="detail && isLeafNode && detail.status === 'accepted'"
            type="primary"
            @click="handleTransition('planned')"
          >
            推进已排期
          </ElButton>
          <ElButton
            v-if="detail && isLeafNode && detail.status === 'planned'"
            type="primary"
            @click="handleTransition('in_dev')"
          >
            推进开发中
          </ElButton>
          <ElButton
            v-if="detail && isLeafNode && detail.status === 'in_dev'"
            type="primary"
            @click="handleTransition('in_acceptance')"
          >
            推进待验收
          </ElButton>
          <ElButton
            v-if="detail && isLeafNode && detail.status === 'in_acceptance'"
            type="success"
            @click="handleTransition('done')"
          >
            标记完成
          </ElButton>
          <ElButton
            v-if="
              detail &&
              isLeafNode &&
              (detail.status === 'done' || detail.status === 'rejected')
            "
            @click="handleTransition('archive')"
          >
            归档
          </ElButton>
          <ElButton
            v-if="canSplitRequirement(detail)"
            type="primary"
            @click="openSplitDialog"
          >
            拆解子需求
          </ElButton>
        </div>
      </div>
    </ElCard>

    <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
      <ElCard
        v-loading="loading"
        class="detail-info-card"
        header="需求信息"
        shadow="never"
      >
        <ElDescriptions :column="2" border>
          <ElDescriptionsItem label="标题" :span="2">
            {{ detail?.title || '-' }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="状态">
            <ElTag :type="getStatusTagType(detail?.status)">
              {{ detail ? getStatusLabel(detail.status) : '-' }}
            </ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="节点类型">
            <ElTag :type="isLeafNode ? 'success' : 'warning'">
              {{ isLeafNode ? '叶子需求' : '父需求' }}
            </ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="父需求路径" :span="2">
            <div class="flex flex-wrap gap-1">
              <ElTag
                v-for="item in parentPathIds"
                :key="item"
                effect="plain"
                size="small"
                type="info"
              >
                {{ item }}
              </ElTag>
              <span v-if="parentPathIds.length === 0">-</span>
            </div>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="优先级">
            {{ detail?.priority || '-' }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="类型">
            {{ detail?.type || '-' }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="来源">
            {{ detail?.source || '-' }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="提单人">
            {{
              detail?.submitter_info?.name ||
              detail?.submitter_info?.username ||
              '-'
            }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="评审人">
            {{
              detail?.reviewer_info?.name ||
              detail?.reviewer_info?.username ||
              '-'
            }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="责任人">
            {{
              detail?.owner_info?.name || detail?.owner_info?.username || '-'
            }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="评审截止">
            <span :class="detail?.is_review_overdue ? 'text-danger' : ''">
              {{ detail?.review_due_at || '-' }}
            </span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="开发截止">
            <span :class="detail?.is_dev_overdue ? 'text-danger' : ''">
              {{ detail?.dev_due_at || '-' }}
            </span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="需求描述" :span="2">
            {{ detail?.description || '-' }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="业务价值" :span="2">
            {{ detail?.business_value || '-' }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="验收标准" :span="2">
            {{ detail?.acceptance_criteria || '-' }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="附件ID" :span="2">
            {{ (detail?.attachments || []).join(', ') || '-' }}
          </ElDescriptionsItem>
        </ElDescriptions>
      </ElCard>

      <ElCard class="detail-info-card" header="评论区" shadow="never">
        <div class="mb-3">
          <ElInput
            v-model="commentText"
            :rows="4"
            placeholder="输入评论内容，支持 @ 提及提醒"
            type="textarea"
          />
          <UserSelector
            v-model="mentionUserIds"
            class="mt-2"
            display-mode="select"
            :multiple="true"
            placeholder="@相关用户（可多选）"
          />
          <div class="mt-2 text-right">
            <ElButton type="primary" @click="handleCommentSubmit">
              发表评论
            </ElButton>
          </div>
        </div>
        <ElTimeline>
          <ElTimelineItem
            v-for="item in comments"
            :key="item.id"
            :timestamp="item.sys_create_datetime"
          >
            <div class="text-sm text-gray-600">
              {{
                item.commenter_info?.name ||
                item.commenter_info?.username ||
                '匿名'
              }}
            </div>
            <div class="mt-1">{{ item.content }}</div>
            <div
              v-if="item.mentions?.length"
              class="mt-1 text-xs text-blue-600"
            >
              @{{ item.mentions.join(' @') }}
            </div>
          </ElTimelineItem>
        </ElTimeline>
      </ElCard>
    </div>

    <ElCard class="detail-info-card mt-3" header="子需求列表" shadow="never">
      <div
        v-if="children.length === 0"
        class="py-8 text-center text-sm text-gray-500"
      >
        暂无子需求
      </div>
      <div v-else class="grid grid-cols-1 gap-2">
        <div
          v-for="child in children"
          :key="child.id"
          class="flex items-center justify-between rounded border border-gray-200 px-3 py-2"
        >
          <div class="min-w-0 flex-1">
            <div class="truncate font-medium">{{ child.title }}</div>
            <div class="mt-1 text-xs text-gray-500">{{ child.id }}</div>
          </div>
          <div class="ml-3 flex items-center gap-2">
            <ElTag size="small">{{ getStatusLabel(child.status) }}</ElTag>
            <ElButton
              link
              size="small"
              type="primary"
              @click="
                router.push(
                  `/requirement-center/requirement/detail/${child.id}`,
                )
              "
            >
              查看
            </ElButton>
          </div>
        </div>
      </div>
    </ElCard>

    <ElCard class="detail-info-card mt-3" header="操作日志" shadow="never">
      <ElTimeline>
        <ElTimelineItem
          v-for="item in logs"
          :key="item.id"
          :timestamp="item.sys_create_datetime"
        >
          <div class="font-medium">
            {{ item.action }}
            <span
              v-if="item.from_status || item.to_status"
              class="ml-1 text-xs text-gray-500"
            >
              {{ item.from_status || '-' }} → {{ item.to_status || '-' }}
            </span>
          </div>
          <div class="text-sm text-gray-600">
            {{
              item.operator_info?.name || item.operator_info?.username || '系统'
            }}
          </div>
          <div v-if="item.note" class="mt-1">{{ item.note }}</div>
        </ElTimelineItem>
      </ElTimeline>
    </ElCard>

    <ElDialog
      v-model="splitDialogVisible"
      :title="`拆解子需求${detail ? ` - ${detail.title}` : ''}`"
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
.detail-hero-card {
  border: 1px solid rgb(59 130 246 / 16%);
  background: linear-gradient(120deg, rgb(59 130 246 / 8%), rgb(255 255 255));
}

.detail-info-card {
  border: 1px solid rgb(148 163 184 / 14%);
}
</style>
