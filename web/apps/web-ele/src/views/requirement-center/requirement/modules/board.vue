<script lang="ts" setup>
import type { RequirementBoardItem } from '../data';

import type { RequirementStatus } from '#/api/requirement-center/requirement';

import { computed, ref } from 'vue';

import { IconifyIcon } from '@vben/icons';

import {
  ElButton,
  ElCard,
  ElEmpty,
  ElProgress,
  ElScrollbar,
  ElSkeleton,
  ElSwitch,
  ElTag,
  ElTooltip,
} from 'element-plus';

import {
  dueCountdownText,
  formatDateText,
  getRequirementProgressPercent,
  isRequirementLeaf,
  REQUIREMENT_STATUS_OPTIONS,
} from '../data';

defineOptions({ name: 'RequirementBoard' });

const props = defineProps<{
  items: RequirementBoardItem[];
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: 'assignOwner', row: RequirementBoardItem): void;
  (e: 'detail', row: RequirementBoardItem): void;
  (e: 'edit', row: RequirementBoardItem): void;
  (
    e: 'review',
    row: RequirementBoardItem,
    action: 'accept' | 'need_info' | 'reject',
  ): void;
  (e: 'split', row: RequirementBoardItem): void;
  (e: 'submit', row: RequirementBoardItem): void;
  (e: 'transition', row: RequirementBoardItem): void;
  (e: 'transferReviewer', row: RequirementBoardItem): void;
}>();

interface BoardLane {
  color: string;
  count: number;
  description: string;
  dot: string;
  items: RequirementBoardItem[];
  label: string;
  status: RequirementStatus;
}

const leafOnly = ref(true);

const displayItems = computed(() => {
  const source = Array.isArray(props.items) ? props.items : [];
  if (!leafOnly.value) return source;
  return source.filter((item) => isRequirementLeaf(item));
});

const totalBoardCount = computed(() => displayItems.value.length);

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

const laneList = computed<BoardLane[]>(() =>
  REQUIREMENT_STATUS_OPTIONS.map((statusOption) => {
    const status = statusOption.value;
    const list = displayItems.value.filter((item) => item.status === status);
    return {
      color: STATUS_THEME[status].color,
      count: list.length,
      description: STATUS_DESCRIPTION[status],
      dot: STATUS_THEME[status].dot,
      items: list,
      label: statusOption.label,
      status,
    };
  }),
);

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

function getReviewerLabel(row: RequirementBoardItem) {
  return row.reviewer_info?.name || row.reviewer_info?.username || '-';
}

function getOwnerLabel(row: RequirementBoardItem) {
  return row.owner_info?.name || row.owner_info?.username || '-';
}

function getDisplayNameInitial(name: string) {
  const text = String(name || '').trim();
  if (!text) return '?';
  return text.slice(0, 1).toUpperCase();
}

function canSplitRequirement(row: RequirementBoardItem) {
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
</script>

<template>
  <ElCard class="board-card" shadow="never">
    <template #header>
      <div class="board-header">
        <div class="board-title">
          <IconifyIcon icon="lucide:layout-panel-top" />
          需求推进看板
        </div>
        <div class="board-controls">
          <div class="leaf-switch">
            <ElSwitch
              v-model="leafOnly"
              inline-prompt
              active-text="叶"
              inactive-text="全"
            />
            <span class="leaf-switch-label">仅叶子</span>
          </div>
          <ElTag type="info">共 {{ totalBoardCount }} 项</ElTag>
        </div>
      </div>
    </template>

    <ElSkeleton :loading="loading" animated>
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
                        v-if="!isRequirementLeaf(item)"
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
                    <span class="chip">{{ item.source || '未标注来源' }}</span>
                    <span v-if="!isRequirementLeaf(item)" class="chip warning">
                      子需求 {{ item.child_count || 0 }}
                    </span>
                  </div>

                  <div class="card-users">
                    <div class="user-pill">
                      <span class="avatar-badge">
                        {{ getDisplayNameInitial(getReviewerLabel(item)) }}
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
                      :percentage="getRequirementProgressPercent(item)"
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
                          @click="emit('detail', item)"
                        >
                          <IconifyIcon icon="lucide:eye" />
                        </ElButton>
                      </ElTooltip>
                      <ElTooltip content="编辑需求" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          @click="emit('edit', item)"
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
                          @click="emit('split', item)"
                        >
                          <IconifyIcon icon="lucide:git-fork" />
                        </ElButton>
                      </ElTooltip>
                      <ElTooltip content="转交评审人" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="primary"
                          @click="emit('transferReviewer', item)"
                        >
                          <IconifyIcon icon="lucide:user-cog" />
                        </ElButton>
                      </ElTooltip>
                      <ElTooltip content="分配责任人" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="primary"
                          @click="emit('assignOwner', item)"
                        >
                          <IconifyIcon icon="lucide:user-plus" />
                        </ElButton>
                      </ElTooltip>
                    </div>

                    <div class="flow-actions">
                      <ElButton
                        v-if="
                          isRequirementLeaf(item) &&
                          (item.status === 'draft' ||
                            item.status === 'need_info')
                        "
                        size="small"
                        type="warning"
                        @click="emit('submit', item)"
                      >
                        提交评审
                      </ElButton>
                      <template
                        v-if="
                          isRequirementLeaf(item) && item.status === 'submitted'
                        "
                      >
                        <ElButton
                          size="small"
                          type="success"
                          @click="emit('review', item, 'accept')"
                        >
                          通过
                        </ElButton>
                        <ElButton
                          size="small"
                          type="warning"
                          @click="emit('review', item, 'need_info')"
                        >
                          补充
                        </ElButton>
                        <ElButton
                          size="small"
                          type="danger"
                          @click="emit('review', item, 'reject')"
                        >
                          驳回
                        </ElButton>
                      </template>
                      <ElButton
                        v-if="
                          isRequirementLeaf(item) &&
                          getNextTransitionAction(item.status)
                        "
                        size="small"
                        type="primary"
                        @click="emit('transition', item)"
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
</template>

<style scoped>
.board-card {
  border: 1px solid rgb(148 163 184 / 16%);
}

.board-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.board-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: rgb(30 41 59);
}

.board-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.leaf-switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.leaf-switch-label {
  font-size: 12px;
  color: rgb(100 116 139);
}

.board-empty {
  padding: 18px 0;
}

.board-scrollbar {
  height: calc(100vh - 420px);
}

.lane-row {
  display: flex;
  gap: 14px;
  padding-bottom: 12px;
}

.lane {
  width: 340px;
  min-width: 340px;
  border-radius: 14px;
  border: 1px solid rgb(148 163 184 / 14%);
  background: rgb(248 250 252);
  padding: 12px;
}

.lane-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 8px;
}

.lane-header-main {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}

.lane-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  margin-top: 4px;
  flex-shrink: 0;
}

.lane-title-wrap {
  min-width: 0;
}

.lane-title {
  font-weight: 700;
  color: rgb(30 41 59);
  line-height: 1.2;
}

.lane-desc {
  margin-top: 3px;
  font-size: 12px;
  color: rgb(100 116 139);
}

.lane-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.requirement-card {
  border-radius: 14px;
  border: 1px solid rgb(148 163 184 / 14%);
  background: #fff;
  padding: 12px;
  box-shadow: 0 8px 20px rgb(15 23 42 / 6%);
  transition: transform 0.18s ease;
}

.requirement-card:hover {
  transform: translateY(-2px);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.card-head-left {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.card-title {
  margin-top: 8px;
  font-weight: 700;
  color: rgb(15 23 42);
  line-height: 1.3;
}

.card-desc {
  margin-top: 6px;
  font-size: 12px;
  color: rgb(71 85 105);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ancestor-chain {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.ancestor-label {
  font-size: 11px;
  color: rgb(100 116 139);
}

.ancestor-item {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgb(241 245 249);
  color: rgb(71 85 105);
}

.card-chip-row {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgb(226 232 240);
  color: rgb(51 65 85);
}

.chip.warning {
  background: rgb(254 243 199);
  color: rgb(146 64 14);
}

.card-users {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.user-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: rgb(71 85 105);
}

.avatar-badge {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgb(226 232 240);
  color: rgb(30 41 59);
  font-weight: 700;
  flex-shrink: 0;
}

.label-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.due-row {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.due-item {
  border-radius: 12px;
  border: 1px solid rgb(148 163 184 / 14%);
  padding: 8px;
  background: rgb(248 250 252);
}

.due-item.danger {
  border-color: rgb(244 63 94 / 35%);
  background: rgb(255 241 242);
}

.due-label {
  font-size: 11px;
  color: rgb(100 116 139);
}

.due-value {
  margin-top: 4px;
  font-weight: 700;
  color: rgb(30 41 59);
  font-size: 12px;
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

@media (max-width: 1200px) {
  .board-scrollbar {
    height: calc(100vh - 520px);
  }
}
</style>
