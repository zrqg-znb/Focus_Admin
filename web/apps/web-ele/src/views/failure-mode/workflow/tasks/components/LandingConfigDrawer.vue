<script lang="ts" setup>
import type {
  TaskFailureModeLandingDetail,
  TaskFailureModeLandingPayload,
  TaskFailureModeLandingProductRow,
  TaskFailureModeLandingResourceRow,
} from '#/api/failure_mode';

import { computed, ref } from 'vue';

import { ElEmpty, ElMessage, ElRadioButton, ElRadioGroup } from 'element-plus';

import { ZqDrawer } from '#/components/zq-drawer';

defineOptions({ name: 'FailureModeLandingConfigDrawer' });

const props = defineProps<{
  loadHandler: (
    taskId: string,
    failureModeId: string,
  ) => Promise<TaskFailureModeLandingDetail>;
  saveHandler: (
    taskId: string,
    failureModeId: string,
    payload: TaskFailureModeLandingPayload,
  ) => Promise<TaskFailureModeLandingDetail>;
}>();

interface DrawerContext {
  taskId: string;
  failureModeId: string;
  failureModeBrief: string;
  productName: string;
  readonly: boolean;
  subsystem: string;
  taskType: string;
  taskStatus: string;
}

interface LandingSection {
  key:
    | 'handling_rows'
    | 'huatuo_rows'
    | 'interception_rows'
    | 'observation_rows';
  rows: TaskFailureModeLandingResourceRow[];
  title: string;
  description: string;
}

const visible = ref(false);
const loading = ref(false);
const confirmLoading = ref(false);
const context = ref<DrawerContext | null>(null);
const detail = ref<null | TaskFailureModeLandingDetail>(null);
const readonly = computed(() => Boolean(context.value?.readonly));

const landingSections = computed<LandingSection[]>(() => [
  {
    key: 'interception_rows',
    rows: detail.value?.interception_rows || [],
    title: '产线拦截策略',
    description: '为每个产品单独标记落地状态，互不影响。',
  },
  {
    key: 'handling_rows',
    rows: detail.value?.handling_rows || [],
    title: '故障处理措施',
    description: '按当前措施类别为每个产品分别维护落地状态。',
  },
  {
    key: 'observation_rows',
    rows: detail.value?.observation_rows || [],
    title: '维测手段',
    description: '按当前维测类别为每个产品分别维护落地状态。',
  },
  {
    key: 'huatuo_rows',
    rows: detail.value?.huatuo_rows || [],
    title: '华佗诊断方案',
    description: '同一个诊断方案在不同产品下可以有不同落地状态。',
  },
]);

const productSummaryRows = computed(() => detail.value?.products || []);

const totalProductRowCount = computed(() =>
  landingSections.value.reduce(
    (sum, section) =>
      sum +
      section.rows.reduce(
        (sectionSum, row) => sectionSum + row.product_rows.length,
        0,
      ),
    0,
  ),
);

const selectedProductRowCount = computed(() =>
  landingSections.value.reduce(
    (sum, section) =>
      sum +
      section.rows.reduce(
        (sectionSum, row) =>
          sectionSum +
          row.product_rows.filter((item) => item.landing_status !== null)
            .length,
        0,
      ),
    0,
  ),
);

const landedProductRowCount = computed(() =>
  landingSections.value.reduce(
    (sum, section) =>
      sum +
      section.rows.reduce(
        (sectionSum, row) =>
          sectionSum +
          row.product_rows.filter((item) => item.landing_status === '已落地')
            .length,
        0,
      ),
    0,
  ),
);

const selectedProductRowSummary = computed(
  () => `${selectedProductRowCount.value}/${totalProductRowCount.value}`,
);

const landedProductRowSummary = computed(
  () => `${landedProductRowCount.value}/${totalProductRowCount.value}`,
);

const currentFailureModeStatusLabel = computed(() => {
  if (!detail.value) {
    return '-';
  }
  return detail.value.landing_completed
    ? detail.value.failure_mode_landing_status ||
        (detail.value.failure_mode_is_landed ? '已落地' : '未落地')
    : '待补齐';
});

const TRUTHY_LANDING_STATUS_VALUES = new Set(['1', 'on', 'true', 'yes']);
const FALSY_LANDING_STATUS_VALUES = new Set(['0', 'false', 'no', 'off']);

function normalizeLandingStatus(value: unknown): null | string {
  if (typeof value === 'boolean') {
    return value ? '已落地' : '未落地';
  }
  const text = String(value ?? '').trim();
  if (!text) {
    return null;
  }
  if (
    text === '已落地' ||
    text === '未落地' ||
    text === '不涉及' ||
    text === '部分落地'
  ) {
    return text;
  }
  const normalizedText = text.toLowerCase();
  if (TRUTHY_LANDING_STATUS_VALUES.has(normalizedText)) {
    return '已落地';
  }
  if (FALSY_LANDING_STATUS_VALUES.has(normalizedText)) {
    return '未落地';
  }
  return null;
}

function formatProductRowLabel(row: TaskFailureModeLandingProductRow) {
  return row.product_name || row.product_id || '未命名产品';
}

function formatSubsystems(subsystems: string[]) {
  const values = (subsystems || []).filter(Boolean);
  return values.length > 0 ? values.join(' / ') : '未绑定子系统';
}

function cloneProductRow(
  row: TaskFailureModeLandingProductRow,
): TaskFailureModeLandingProductRow {
  return {
    product_id: String(row.product_id || ''),
    product_name: String(row.product_name || ''),
    subsystems: [...(row.subsystems || [])],
    landing_status: normalizeLandingStatus(row.landing_status),
  };
}

function cloneResourceRow(
  row: TaskFailureModeLandingResourceRow,
): TaskFailureModeLandingResourceRow {
  return {
    resource_id: String(row.resource_id || ''),
    label: String(row.label || ''),
    subtitle: row.subtitle || null,
    group_key: String(row.group_key || ''),
    landing_status: normalizeLandingStatus(row.landing_status),
    product_rows: (row.product_rows || []).map((productRow) =>
      cloneProductRow(productRow),
    ),
  };
}

async function loadDetail() {
  if (!context.value) {
    return;
  }
  loading.value = true;
  try {
    detail.value = await props.loadHandler(
      context.value.taskId,
      context.value.failureModeId,
    );
  } finally {
    loading.value = false;
  }
}

async function open(nextContext: DrawerContext) {
  context.value = nextContext;
  visible.value = true;
  await loadDetail();
}

function buildPayload(): TaskFailureModeLandingPayload {
  return {
    products: (detail.value?.products || []).map((row) => cloneProductRow(row)),
    interception_rows: (detail.value?.interception_rows || []).map((row) =>
      cloneResourceRow(row),
    ),
    handling_rows: (detail.value?.handling_rows || []).map((row) =>
      cloneResourceRow(row),
    ),
    observation_rows: (detail.value?.observation_rows || []).map((row) =>
      cloneResourceRow(row),
    ),
    huatuo_rows: (detail.value?.huatuo_rows || []).map((row) =>
      cloneResourceRow(row),
    ),
  };
}

function validatePayload() {
  const incomplete = landingSections.value.some((section) =>
    section.rows.some((row) =>
      row.product_rows.some(
        (productRow) =>
          normalizeLandingStatus(productRow.landing_status) === null,
      ),
    ),
  );
  if (incomplete) {
    ElMessage.warning('请先为所有产品选择落地状态');
    return false;
  }
  return true;
}

async function handleConfirm() {
  if (!context.value || !detail.value || readonly.value) {
    return;
  }
  if (!validatePayload()) {
    return;
  }
  confirmLoading.value = true;
  try {
    detail.value = await props.saveHandler(
      context.value.taskId,
      context.value.failureModeId,
      buildPayload(),
    );
    ElMessage.success('落地配置已保存');
  } finally {
    confirmLoading.value = false;
  }
}

defineExpose({ open });
</script>

<template>
  <ZqDrawer
    v-model="visible"
    :confirm-loading="confirmLoading"
    confirm-text="保存落地配置"
    :loading="loading"
    :size="1120"
    :show-footer="!readonly"
    :title="readonly ? '落地情况' : '落地配置'"
    @confirm="handleConfirm"
  >
    <div class="fm-landing-drawer flex flex-col gap-4 pb-2">
      <div v-if="context" class="fm-landing-drawer__hero">
        <div class="fm-landing-drawer__hero-main">
          <div class="fm-landing-drawer__eyebrow">Task Landing Matrix</div>
          <div class="fm-landing-drawer__title">
            {{ context.failureModeBrief }}
          </div>
          <div class="fm-landing-drawer__meta">
            <span>任务范围：{{ context.productName || '公共任务' }}</span>
            <span>子系统：{{ context.subsystem || '-' }}</span>
            <span>任务类型：{{ context.taskType }}</span>
            <span>任务状态：{{ context.taskStatus }}</span>
          </div>
        </div>
        <div class="fm-landing-drawer__summary">
          <div class="fm-landing-drawer__summary-card">
            <span>故障模式状态</span>
            <strong>{{ currentFailureModeStatusLabel }}</strong>
            <small>按全部关联产品自动汇总</small>
          </div>
          <div class="fm-landing-drawer__summary-card">
            <span>产品数</span>
            <strong>{{ productSummaryRows.length }}</strong>
          </div>
          <div class="fm-landing-drawer__summary-card">
            <span>状态已选</span>
            <strong>{{ selectedProductRowCount }}</strong>
            <small>/ {{ totalProductRowCount }}</small>
          </div>
          <div class="fm-landing-drawer__summary-card">
            <span>已落地</span>
            <strong>{{ landedProductRowCount }}</strong>
            <small>/ {{ totalProductRowCount }}</small>
          </div>
        </div>
      </div>

      <template v-if="detail">
        <section class="fm-landing-drawer__panel">
          <div class="fm-landing-drawer__panel-header">
            <div>
              <div class="fm-landing-drawer__panel-title">产品汇总</div>
              <div class="fm-landing-drawer__panel-desc">
                同一个故障模式在不同产品下可以独立选择“已落地 / 未落地 /
                不涉及”。
              </div>
            </div>
            <div class="fm-landing-drawer__panel-hint">
              共 {{ productSummaryRows.length }} 个产品
            </div>
          </div>

          <ElEmpty
            v-if="productSummaryRows.length === 0"
            description="当前没有可展示的产品"
          />

          <div v-else class="fm-landing-drawer__product-summary-list">
            <div
              v-for="product in productSummaryRows"
              :key="product.product_id"
              class="fm-landing-drawer__product-summary-card"
            >
              <div class="fm-landing-drawer__product-summary-main">
                <div class="fm-landing-drawer__product-summary-title">
                  {{ formatProductRowLabel(product) }}
                </div>
                <div class="fm-landing-drawer__product-summary-subtitle">
                  {{ formatSubsystems(product.subsystems) }}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="fm-landing-drawer__panel">
          <div class="fm-landing-drawer__panel-header">
            <div>
              <div class="fm-landing-drawer__panel-title">故障模式派生结果</div>
              <div class="fm-landing-drawer__panel-desc">
                这里展示的是当前故障模式在全部关联产品下汇总后的落地情况。
              </div>
            </div>
          </div>
          <div class="fm-landing-drawer__summary-strip">
            <div
              class="fm-landing-drawer__summary-chip fm-landing-drawer__summary-chip--metric"
            >
              <span>状态已选</span>
              <strong>{{ selectedProductRowSummary }}</strong>
            </div>
            <div
              class="fm-landing-drawer__summary-chip fm-landing-drawer__summary-chip--metric"
            >
              <span>已落地</span>
              <strong>{{ landedProductRowSummary }}</strong>
            </div>
            <div
              v-if="totalProductRowCount === 0"
              class="fm-landing-drawer__summary-hint"
            >
              当前没有任何关联资源，故障模式默认未落地。
            </div>
          </div>
        </section>

        <section
          v-for="section in landingSections"
          :key="section.key"
          class="fm-landing-drawer__panel"
        >
          <div class="fm-landing-drawer__panel-header">
            <div>
              <div class="fm-landing-drawer__panel-title">
                {{ section.title }}
              </div>
              <div class="fm-landing-drawer__panel-desc">
                {{ section.description }}
              </div>
            </div>
            <div class="fm-landing-drawer__section-count">
              共 {{ section.rows.length }} 项
            </div>
          </div>

          <ElEmpty
            v-if="section.rows.length === 0"
            :description="`当前未绑定${section.title}`"
          />

          <div v-else class="fm-landing-drawer__resource-list">
            <div
              v-for="row in section.rows"
              :key="`${section.key}-${row.resource_id}`"
              class="fm-landing-drawer__resource-card"
            >
              <div class="fm-landing-drawer__resource-head">
                <div class="fm-landing-drawer__resource-main">
                  <div class="fm-landing-drawer__resource-title">
                    {{ row.label }}
                  </div>
                  <div
                    v-if="row.subtitle || row.group_key"
                    class="fm-landing-drawer__resource-meta"
                  >
                    <span v-if="row.subtitle">{{ row.subtitle }}</span>
                    <span v-if="row.group_key">{{ row.group_key }}</span>
                  </div>
                </div>
              </div>

              <div class="fm-landing-drawer__product-grid">
                <div
                  v-for="product in row.product_rows"
                  :key="`${section.key}-${row.resource_id}-${product.product_id}`"
                  class="fm-landing-drawer__product-card"
                >
                  <div class="fm-landing-drawer__product-card-head">
                    <div class="fm-landing-drawer__product-card-main">
                      <div class="fm-landing-drawer__product-card-title">
                        {{ formatProductRowLabel(product) }}
                      </div>
                      <div class="fm-landing-drawer__product-card-subtitle">
                        {{ formatSubsystems(product.subsystems) }}
                      </div>
                    </div>
                  </div>

                  <ElRadioGroup
                    v-model="product.landing_status"
                    class="fm-landing-drawer__radio-group"
                    :disabled="loading || confirmLoading || readonly"
                  >
                    <ElRadioButton label="已落地">已落地</ElRadioButton>
                    <ElRadioButton label="未落地">未落地</ElRadioButton>
                    <ElRadioButton label="不涉及">不涉及</ElRadioButton>
                  </ElRadioGroup>
                </div>
              </div>
            </div>
          </div>
        </section>
      </template>
    </div>
  </ZqDrawer>
</template>

<style scoped>
.fm-landing-drawer__hero {
  display: grid;
  gap: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  background: #ffffff;
  padding: 20px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.04);
}

.fm-landing-drawer__eyebrow {
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.fm-landing-drawer__title {
  margin-top: 10px;
  color: #0f172a;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.25;
}

.fm-landing-drawer__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 10px;
  color: #64748b;
  font-size: 13px;
}

.fm-landing-drawer__summary {
  display: grid;
  gap: 12px;
  grid-template-columns: 1.2fr repeat(3, minmax(0, 1fr));
}

.fm-landing-drawer__summary-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  min-height: 96px;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background: #f8fafc;
  padding: 16px 18px;
  color: #64748b;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}

.fm-landing-drawer__summary-card span {
  font-size: 12px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.fm-landing-drawer__summary-card strong {
  color: #111827;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.1;
}

.fm-landing-drawer__summary-card small {
  color: #94a3b8;
  font-size: 12px;
}

.fm-landing-drawer__panel {
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  background: #ffffff;
  padding: 18px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
}

.fm-landing-drawer__panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.fm-landing-drawer__panel-title {
  color: #0f172a;
  font-size: 17px;
  font-weight: 700;
}

.fm-landing-drawer__panel-desc {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.fm-landing-drawer__panel-hint,
.fm-landing-drawer__section-count {
  color: #64748b;
  font-size: 13px;
  white-space: nowrap;
}

.fm-landing-drawer__product-summary-list {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  margin-top: 16px;
}

.fm-landing-drawer__product-summary-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background: #ffffff;
  padding: 16px 16px 14px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}

.fm-landing-drawer__product-summary-main,
.fm-landing-drawer__product-card-main,
.fm-landing-drawer__resource-main {
  min-width: 0;
  flex: 1;
}

.fm-landing-drawer__product-summary-title,
.fm-landing-drawer__product-card-title,
.fm-landing-drawer__resource-title {
  color: #111827;
  font-size: 14px;
  font-weight: 600;
}

.fm-landing-drawer__product-summary-subtitle,
.fm-landing-drawer__product-card-subtitle,
.fm-landing-drawer__resource-meta {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.55;
}

.fm-landing-drawer__summary-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 14px;
}

.fm-landing-drawer__summary-chip,
.fm-landing-drawer__summary-hint {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #f8fafc;
  padding: 12px 14px;
  color: #334155;
  font-size: 13px;
}

.fm-landing-drawer__summary-chip--metric {
  min-width: 180px;
}

.fm-landing-drawer__summary-chip strong {
  color: #111827;
  font-size: 16px;
  font-weight: 700;
}

.fm-landing-drawer__summary-hint {
  line-height: 1.6;
}

.fm-landing-drawer__resource-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.fm-landing-drawer__resource-card {
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background: #ffffff;
  padding: 16px 16px 14px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}

.fm-landing-drawer__resource-head,
.fm-landing-drawer__product-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.fm-landing-drawer__product-grid {
  display: grid;
  gap: 14px;
  margin-top: 14px;
}

.fm-landing-drawer__product-card {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #ffffff;
  padding: 14px 14px 16px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}

.fm-landing-drawer__radio-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.fm-landing-drawer__radio-group :deep(.el-radio-button) {
  margin-right: 0;
}

.fm-landing-drawer__radio-group :deep(.el-radio-button__inner) {
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  background: #f8fafc;
  color: #334155;
  font-weight: 600;
  min-width: 84px;
  padding: 0 16px;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.fm-landing-drawer__radio-group
  :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  color: #fff;
  background: var(--el-color-primary);
  border-color: var(--el-color-primary);
  box-shadow: 0 10px 22px
    color-mix(in srgb, var(--el-color-primary) 28%, transparent);
  transform: translateY(-1px);
}

.fm-landing-drawer__radio-group :deep(.el-radio-button__inner:hover) {
  color: var(--el-color-primary);
  border-color: var(--el-color-primary);
}

@media (max-width: 860px) {
  .fm-landing-drawer__hero,
  .fm-landing-drawer__panel {
    padding: 16px;
  }

  .fm-landing-drawer__summary {
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  }

  .fm-landing-drawer__resource-head,
  .fm-landing-drawer__product-card-head,
  .fm-landing-drawer__product-summary-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .fm-landing-drawer__panel-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .fm-landing-drawer__summary-strip {
    flex-direction: column;
  }

  .fm-landing-drawer__radio-group {
    gap: 6px;
  }
}
</style>
