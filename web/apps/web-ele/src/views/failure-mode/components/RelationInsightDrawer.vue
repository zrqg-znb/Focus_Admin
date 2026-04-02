<script lang="ts" setup>
import type {
  FailureModeInsight,
  InterceptionInsight,
  UserBriefInfo,
} from '#/api/failure_mode';

import { computed, ref } from 'vue';

import { ElEmpty, ElMessage, ElTable, ElTableColumn } from 'element-plus';

import {
  getFailureModeInsightApi,
  getInterceptionStrategyInsightApi,
} from '#/api/failure_mode';
import { ZqDrawer } from '#/components/zq-drawer';

defineOptions({ name: 'RelationInsightDrawer' });

type InsightMode = 'failure_mode' | 'interception';

const visible = ref(false);
const loading = ref(false);
const mode = ref<InsightMode>('failure_mode');
const failureModeInsight = ref<FailureModeInsight | null>(null);
const interceptionInsight = ref<InterceptionInsight | null>(null);

const drawerTitle = computed(() => {
  return mode.value === 'failure_mode'
    ? '故障模式关联洞察'
    : '产线拦截策略关联洞察';
});

const currentRate = computed(() => {
  const landed =
    mode.value === 'failure_mode'
      ? failureModeInsight.value?.landed_product_count || 0
      : interceptionInsight.value?.landed_product_count || 0;
  const total =
    mode.value === 'failure_mode'
      ? failureModeInsight.value?.total_product_count || 0
      : interceptionInsight.value?.total_product_count || 0;
  return formatRate(landed, total);
});

function formatRate(numerator: number, denominator: number) {
  if (!denominator) {
    return '0%';
  }
  const value = ((numerator / denominator) * 100).toFixed(1);
  return value.endsWith('.0%') ? value.replace('.0%', '%') : `${value}%`;
}

function formatUserName(user?: null | UserBriefInfo) {
  return user?.name || user?.username || '-';
}

function formatTextList(items?: null | string[]) {
  return (items || []).filter(Boolean).join('、') || '-';
}

async function openFailureMode(id: string) {
  mode.value = 'failure_mode';
  interceptionInsight.value = null;
  visible.value = true;
  loading.value = true;
  try {
    failureModeInsight.value = await getFailureModeInsightApi(id);
  } catch (error) {
    visible.value = false;
    console.error(error);
    ElMessage.error('加载故障模式关联洞察失败');
  } finally {
    loading.value = false;
  }
}

async function openInterception(id: string) {
  mode.value = 'interception';
  failureModeInsight.value = null;
  visible.value = true;
  loading.value = true;
  try {
    interceptionInsight.value = await getInterceptionStrategyInsightApi(id);
  } catch (error) {
    visible.value = false;
    console.error(error);
    ElMessage.error('加载产线拦截策略关联洞察失败');
  } finally {
    loading.value = false;
  }
}

defineExpose({
  openFailureMode,
  openInterception,
});
</script>

<template>
  <ZqDrawer
    v-model="visible"
    :loading="loading"
    :show-footer="false"
    :size="1180"
    :title="drawerTitle"
  >
    <div class="fm-relation-insight flex flex-col gap-4 pb-2">
      <div
        v-if="mode === 'failure_mode' && failureModeInsight"
        class="fm-relation-insight__hero"
      >
        <div class="fm-relation-insight__hero-title">
          {{ failureModeInsight.brief }}
        </div>
        <div class="fm-relation-insight__hero-meta">
          <span>子系统：{{ failureModeInsight.subsystem || '-' }}</span>
          <span>状态：{{ failureModeInsight.status || '-' }}</span>
        </div>
      </div>

      <div
        v-else-if="mode === 'interception' && interceptionInsight"
        class="fm-relation-insight__hero"
      >
        <div class="fm-relation-insight__hero-title">
          {{ interceptionInsight.interception_item }}
        </div>
        <div class="fm-relation-insight__hero-meta">
          <span>工位：{{ interceptionInsight.station || '-' }}</span>
        </div>
      </div>

      <div
        v-if="mode === 'failure_mode' && failureModeInsight"
        class="fm-relation-insight__summary-grid"
      >
        <div class="fm-relation-insight__summary-card">
          <div class="fm-relation-insight__summary-label">已落地产品数</div>
          <div class="fm-relation-insight__summary-value">
            {{ failureModeInsight.landed_product_count }}
          </div>
        </div>
        <div class="fm-relation-insight__summary-card">
          <div class="fm-relation-insight__summary-label">已纳管产品总数</div>
          <div class="fm-relation-insight__summary-value">
            {{ failureModeInsight.total_product_count }}
          </div>
        </div>
        <div class="fm-relation-insight__summary-card">
          <div class="fm-relation-insight__summary-label">落地率</div>
          <div class="fm-relation-insight__summary-value">
            {{ currentRate }}
          </div>
        </div>
      </div>

      <div
        v-else-if="mode === 'interception' && interceptionInsight"
        class="fm-relation-insight__summary-grid"
      >
        <div class="fm-relation-insight__summary-card">
          <div class="fm-relation-insight__summary-label">关联故障模式数</div>
          <div class="fm-relation-insight__summary-value">
            {{ interceptionInsight.related_failure_mode_count }}
          </div>
        </div>
        <div class="fm-relation-insight__summary-card">
          <div class="fm-relation-insight__summary-label">已落地产品数</div>
          <div class="fm-relation-insight__summary-value">
            {{ interceptionInsight.landed_product_count }}
          </div>
        </div>
        <div class="fm-relation-insight__summary-card">
          <div class="fm-relation-insight__summary-label">落地率</div>
          <div class="fm-relation-insight__summary-value">
            {{ currentRate }}
          </div>
        </div>
      </div>

      <section
        v-if="mode === 'failure_mode' && failureModeInsight"
        class="fm-relation-insight__panel"
      >
        <div class="fm-relation-insight__panel-title">落地产品</div>
        <ElEmpty
          v-if="failureModeInsight.product_rows.length === 0"
          description="当前故障模式尚未落地到任何产品基线"
        />
        <ElTable v-else :data="failureModeInsight.product_rows" border stripe>
          <ElTableColumn label="产品" min-width="220" prop="product_name" />
          <ElTableColumn label="主版本SE" min-width="160">
            <template #default="{ row }">
              {{ formatUserName(row.owner_info) }}
            </template>
          </ElTableColumn>
          <ElTableColumn label="落地子系统" min-width="220">
            <template #default="{ row }">
              {{ formatTextList(row.subsystems) }}
            </template>
          </ElTableColumn>
          <ElTableColumn
            label="最近落地时间"
            min-width="180"
            prop="landed_at"
          />
        </ElTable>
      </section>

      <div
        v-else-if="mode === 'interception' && interceptionInsight"
        class="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]"
      >
        <section class="fm-relation-insight__panel">
          <div class="fm-relation-insight__panel-title">关联故障模式</div>
          <ElEmpty
            v-if="interceptionInsight.failure_mode_rows.length === 0"
            description="当前产线拦截策略尚未关联任何故障模式"
          />
          <ElTable
            v-else
            :data="interceptionInsight.failure_mode_rows"
            border
            stripe
          >
            <ElTableColumn
              label="故障模式"
              min-width="240"
              prop="failure_mode_brief"
            />
            <ElTableColumn label="子系统" min-width="140" prop="subsystem" />
            <ElTableColumn label="状态" min-width="120" prop="status" />
            <ElTableColumn label="已落地产品" min-width="220">
              <template #default="{ row }">
                {{ formatTextList(row.product_names) }}
              </template>
            </ElTableColumn>
            <ElTableColumn
              label="产品数"
              min-width="90"
              prop="landed_product_count"
            />
          </ElTable>
        </section>

        <section class="fm-relation-insight__panel">
          <div class="fm-relation-insight__panel-title">落地产品</div>
          <ElEmpty
            v-if="interceptionInsight.product_rows.length === 0"
            description="当前产线拦截策略尚未通过故障模式落地到任何产品"
          />
          <ElTable
            v-else
            :data="interceptionInsight.product_rows"
            border
            stripe
          >
            <ElTableColumn label="产品" min-width="180" prop="product_name" />
            <ElTableColumn label="主版本SE" min-width="140">
              <template #default="{ row }">
                {{ formatUserName(row.owner_info) }}
              </template>
            </ElTableColumn>
            <ElTableColumn label="通过哪些故障模式落地" min-width="260">
              <template #default="{ row }">
                {{ formatTextList(row.failure_mode_briefs) }}
              </template>
            </ElTableColumn>
          </ElTable>
        </section>
      </div>
    </div>
  </ZqDrawer>
</template>

<style scoped>
.fm-relation-insight__hero {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: linear-gradient(
    135deg,
    rgba(248, 250, 252, 0.96),
    rgba(239, 246, 255, 0.9)
  );
  padding: 18px 20px;
}

.fm-relation-insight__hero-title {
  color: #0f172a;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.5;
}

.fm-relation-insight__hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-top: 8px;
  color: #475569;
  font-size: 13px;
}

.fm-relation-insight__summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.fm-relation-insight__summary-card {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #fff;
  padding: 16px 18px;
}

.fm-relation-insight__summary-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.fm-relation-insight__summary-value {
  margin-top: 8px;
  color: #0f172a;
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}

.fm-relation-insight__panel {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fff;
  padding: 16px;
}

.fm-relation-insight__panel-title {
  margin-bottom: 12px;
  color: #0f172a;
  font-size: 15px;
  font-weight: 700;
}

@media (max-width: 960px) {
  .fm-relation-insight__summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
