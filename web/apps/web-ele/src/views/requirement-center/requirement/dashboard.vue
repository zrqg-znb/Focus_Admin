<script lang="ts" setup>
import type { RequirementDashboardSummary } from '#/api/requirement-center/requirement';

import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  ElButton,
  ElCard,
  ElEmpty,
  ElMessage,
  ElProgress,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import { getRequirementDashboardSummaryApi } from '#/api/requirement-center/requirement';

defineOptions({ name: 'RequirementDashboard' });

interface MetricCard {
  accent: string;
  icon: string;
  key:
    | 'closed_count'
    | 'dev_overdue_count'
    | 'open_count'
    | 'overdue_count'
    | 'review_overdue_count'
    | 'total_count';
  label: string;
  trend?: string;
}

const router = useRouter();
const loading = ref(false);
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

const metricCards: MetricCard[] = [
  {
    key: 'total_count',
    label: '需求总量',
    icon: 'lucide:clipboard-list',
    accent: 'from-indigo-500/15 to-indigo-600/5',
  },
  {
    key: 'open_count',
    label: '进行中',
    icon: 'lucide:activity',
    accent: 'from-blue-500/15 to-blue-600/5',
  },
  {
    key: 'closed_count',
    label: '已关闭',
    icon: 'lucide:check-circle-2',
    accent: 'from-emerald-500/15 to-emerald-600/5',
  },
  {
    key: 'overdue_count',
    label: '逾期总数',
    icon: 'lucide:clock-alert',
    accent: 'from-rose-500/15 to-rose-600/5',
  },
  {
    key: 'review_overdue_count',
    label: '评审逾期',
    icon: 'lucide:eye',
    accent: 'from-orange-500/15 to-orange-600/5',
  },
  {
    key: 'dev_overdue_count',
    label: '开发逾期',
    icon: 'lucide:hammer',
    accent: 'from-purple-500/15 to-purple-600/5',
  },
];

const total = computed(() => Math.max(summary.value.total_count || 0, 1));

function calcPercent(count: number) {
  return Number(((Number(count || 0) / total.value) * 100).toFixed(1));
}

function getTagType(count: number): '' | 'danger' | 'success' {
  return Number(count || 0) > 0 ? 'danger' : 'success';
}

async function loadSummary() {
  loading.value = true;
  try {
    summary.value = await getRequirementDashboardSummaryApi();
  } catch {
    ElMessage.error('需求看板加载失败，请稍后重试');
  } finally {
    loading.value = false;
  }
}

onMounted(loadSummary);
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full flex-col gap-3">
      <ElCard class="dashboard-hero" shadow="never">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div class="text-base font-semibold">需求中心可视化看板</div>
            <div class="mt-1 text-sm text-gray-500">
              实时查看需求总览、逾期风险与责任分布
            </div>
            <div class="mt-3 flex items-center gap-2">
              <ElTag :type="getTagType(summary.overdue_count)">
                逾期 {{ summary.overdue_count }}
              </ElTag>
              <ElTag type="info"> 本期关闭 {{ summary.closed_count }} </ElTag>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <ElButton @click="router.push('/requirement-center/requirement')">
              返回列表
            </ElButton>
            <ElButton :loading="loading" type="primary" @click="loadSummary">
              刷新看板
            </ElButton>
          </div>
        </div>
      </ElCard>

      <div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        <ElCard
          v-for="item in metricCards"
          :key="item.key"
          class="metric-card"
          shadow="never"
        >
          <div class="metric-card__inner">
            <div
              class="metric-card__icon"
              :class="`bg-gradient-to-br ${item.accent}`"
            >
              <IconifyIcon :icon="item.icon" />
            </div>
            <div class="min-w-0 flex-1">
              <div class="text-xs text-gray-500">{{ item.label }}</div>
              <div class="mt-1 text-2xl font-semibold">
                {{ summary[item.key] }}
              </div>
              <div class="mt-2 text-xs text-gray-400">
                占比 {{ calcPercent(summary[item.key]) }}%
              </div>
            </div>
          </div>
        </ElCard>
      </div>

      <div class="grid grid-cols-1 gap-3 xl:grid-cols-2">
        <ElCard class="panel-card" header="状态分布" shadow="never">
          <ElEmpty
            v-if="(summary.status_stats || []).length === 0"
            description="暂无状态数据"
          />
          <div v-else class="space-y-3">
            <div
              v-for="item in summary.status_stats || []"
              :key="item.key"
              class="rounded-xl border border-gray-100 px-3 py-2"
            >
              <div class="mb-2 flex items-center justify-between text-sm">
                <span>{{ item.label }}</span>
                <span class="font-medium">{{ item.count }}</span>
              </div>
              <ElProgress
                :percentage="calcPercent(item.count)"
                :show-text="false"
                color="#6366f1"
              />
            </div>
          </div>
        </ElCard>

        <ElCard class="panel-card" header="优先级分布" shadow="never">
          <ElEmpty
            v-if="(summary.priority_stats || []).length === 0"
            description="暂无优先级数据"
          />
          <div v-else class="space-y-3">
            <div
              v-for="item in summary.priority_stats || []"
              :key="item.key"
              class="rounded-xl border border-gray-100 px-3 py-2"
            >
              <div class="mb-2 flex items-center justify-between text-sm">
                <span>{{ item.label }}</span>
                <span class="font-medium">{{ item.count }}</span>
              </div>
              <ElProgress
                :percentage="calcPercent(item.count)"
                :show-text="false"
                color="#8b5cf6"
              />
            </div>
          </div>
        </ElCard>

        <ElCard class="panel-card" header="评审人 Top10" shadow="never">
          <ElTable :data="summary.reviewer_stats || []" size="small">
            <ElTableColumn label="评审人" min-width="160" prop="label" />
            <ElTableColumn label="数量" min-width="100" prop="count" />
            <ElTableColumn label="占比" min-width="120">
              <template #default="{ row }">
                {{ calcPercent(row.count) }}%
              </template>
            </ElTableColumn>
          </ElTable>
        </ElCard>

        <ElCard class="panel-card" header="责任人 Top10" shadow="never">
          <ElTable :data="summary.owner_stats || []" size="small">
            <ElTableColumn label="责任人" min-width="160" prop="label" />
            <ElTableColumn label="数量" min-width="100" prop="count" />
            <ElTableColumn label="占比" min-width="120">
              <template #default="{ row }">
                {{ calcPercent(row.count) }}%
              </template>
            </ElTableColumn>
          </ElTable>
        </ElCard>
      </div>
    </div>
  </Page>
</template>

<style scoped>
.dashboard-hero {
  border: 1px solid rgb(99 102 241 / 18%);
  background: linear-gradient(135deg, rgb(99 102 241 / 8%), rgb(255 255 255));
}

.metric-card {
  border: 1px solid rgb(148 163 184 / 15%);
  transition: all 0.2s ease;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 30px rgb(15 23 42 / 8%);
}

.metric-card__inner {
  display: flex;
  align-items: center;
  gap: 12px;
}

.metric-card__icon {
  display: flex;
  height: 44px;
  width: 44px;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  color: rgb(51 65 85);
  font-size: 20px;
}

.panel-card {
  border: 1px solid rgb(148 163 184 / 14%);
}
</style>
