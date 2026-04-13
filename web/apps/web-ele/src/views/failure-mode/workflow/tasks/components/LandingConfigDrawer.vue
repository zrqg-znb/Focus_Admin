<script lang="ts" setup>
import type {
  TaskFailureModeLandingDetail,
  TaskFailureModeLandingPayload,
  TaskFailureModeLandingRow,
} from '#/api/failure_mode';

import { computed, ref } from 'vue';

import {
  ElEmpty,
  ElMessage,
  ElRadioButton,
  ElRadioGroup,
  ElTag,
} from 'element-plus';

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
  rows: TaskFailureModeLandingRow[];
  title: string;
}

const visible = ref(false);
const loading = ref(false);
const confirmLoading = ref(false);
const context = ref<DrawerContext | null>(null);
const detail = ref<null | TaskFailureModeLandingDetail>(null);
const readonly = computed(() => Boolean(context.value?.readonly));

const landingSections = computed<LandingSection[]>(() => {
  return [
    {
      key: 'interception_rows',
      rows: detail.value?.interception_rows || [],
      title: '产线拦截策略',
    },
    {
      key: 'handling_rows',
      rows: detail.value?.handling_rows || [],
      title: '故障处理措施',
    },
    {
      key: 'observation_rows',
      rows: detail.value?.observation_rows || [],
      title: '维测手段',
    },
    {
      key: 'huatuo_rows',
      rows: detail.value?.huatuo_rows || [],
      title: '华佗诊断方案',
    },
  ];
});

const landedResourceCount = computed(() => {
  return landingSections.value.reduce((sum, section) => {
    return sum + section.rows.filter((item) => item.is_landed === true).length;
  }, 0);
});

const filledResourceCount = computed(() => {
  return landingSections.value.reduce((sum, section) => {
    return (
      sum +
      section.rows.filter((item) => typeof item.is_landed === 'boolean').length
    );
  }, 0);
});

const totalResourceCount = computed(() => {
  return landingSections.value.reduce((sum, section) => {
    return sum + section.rows.length;
  }, 0);
});

const currentFailureModeStatusLabel = computed(() => {
  return detail.value?.failure_mode_is_landed ? '已落地' : '未落地';
});

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

async function handleConfirm() {
  if (!context.value || !detail.value || readonly.value) {
    return;
  }
  confirmLoading.value = true;
  try {
    detail.value = await props.saveHandler(
      context.value.taskId,
      context.value.failureModeId,
      {
        interception_rows: detail.value.interception_rows,
        handling_rows: detail.value.handling_rows,
        observation_rows: detail.value.observation_rows,
        huatuo_rows: detail.value.huatuo_rows,
      },
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
    :size="1080"
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
            <span>产品：{{ context.productName }}</span>
            <span>子系统：{{ context.subsystem }}</span>
            <span>任务类型：{{ context.taskType }}</span>
            <span>任务状态：{{ context.taskStatus }}</span>
          </div>
        </div>
        <div class="fm-landing-drawer__summary">
          <div class="fm-landing-drawer__summary-card">
            <span>当前派生结果</span>
            <strong>{{ currentFailureModeStatusLabel }}</strong>
          </div>
          <div class="fm-landing-drawer__summary-card">
            <span>已填写资源</span>
            <strong>{{ filledResourceCount }}</strong>
            <small>/ {{ totalResourceCount }}</small>
          </div>
          <div class="fm-landing-drawer__summary-card">
            <span>资源已落地</span>
            <strong>{{ landedResourceCount }}</strong>
            <small>/ {{ totalResourceCount }}</small>
          </div>
          <div class="fm-landing-drawer__summary-card">
            <span>{{ readonly ? '查看模式' : '填写进度' }}</span>
            <ElTag
              :type="
                readonly
                  ? 'info'
                  : detail?.landing_completed
                    ? 'success'
                    : 'warning'
              "
              effect="light"
              round
            >
              {{
                readonly
                  ? '只读查看'
                  : detail?.landing_completed
                    ? '已补齐'
                    : '待补齐'
              }}
            </ElTag>
          </div>
        </div>
      </div>

      <template v-if="detail">
        <section class="fm-landing-drawer__panel">
          <div class="fm-landing-drawer__panel-header">
            <div>
              <div class="fm-landing-drawer__panel-title">故障模式派生结果</div>
              <div class="fm-landing-drawer__panel-desc">
                故障模式本身不再单独录入落地状态，只根据当前绑定的四类资源自动推导。
              </div>
            </div>
          </div>
          <div class="fm-landing-drawer__summary-strip">
            <div class="fm-landing-drawer__summary-chip">
              <span>故障模式状态</span>
              <ElTag
                :type="detail.failure_mode_is_landed ? 'success' : 'info'"
                effect="light"
                round
              >
                {{ currentFailureModeStatusLabel }}
              </ElTag>
            </div>
            <div class="fm-landing-drawer__summary-chip">
              <span>填写完整度</span>
              <strong>
                {{ filledResourceCount }}/{{ totalResourceCount }}
              </strong>
            </div>
            <div
              v-if="totalResourceCount === 0"
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
                当前按任务内最新绑定关系维护产品级显式落地状态，故障模式结果会随这里的填写实时派生。
              </div>
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
              class="fm-landing-drawer__resource-row"
            >
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
              <ElRadioGroup
                v-model="row.is_landed"
                :disabled="loading || confirmLoading || readonly"
              >
                <ElRadioButton :label="true">已落地</ElRadioButton>
                <ElRadioButton :label="false">未落地</ElRadioButton>
              </ElRadioGroup>
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
  border: 1px solid color-mix(in srgb, var(--el-color-primary) 18%, transparent);
  border-radius: 20px;
  background:
    radial-gradient(
      circle at top right,
      color-mix(in srgb, var(--el-color-primary) 16%, transparent),
      transparent 32%
    ),
    linear-gradient(
      135deg,
      color-mix(in srgb, var(--el-color-primary-light-9) 88%, white) 0%,
      color-mix(in srgb, var(--el-color-primary-light-8) 52%, white) 48%,
      #ffffff 100%
    );
  padding: 20px;
}

.fm-landing-drawer__eyebrow {
  color: var(--el-color-primary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.fm-landing-drawer__title {
  margin-top: 10px;
  color: #111827;
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
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.fm-landing-drawer__summary-card {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.88);
  padding: 14px 16px;
  color: #64748b;
}

.fm-landing-drawer__summary-card strong {
  color: #111827;
  font-size: 22px;
  font-weight: 700;
}

.fm-landing-drawer__summary-card small {
  color: #94a3b8;
  font-size: 12px;
}

.fm-landing-drawer__panel {
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.96);
  padding: 16px;
}

.fm-landing-drawer__panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.fm-landing-drawer__panel-title {
  color: #111827;
  font-size: 16px;
  font-weight: 700;
}

.fm-landing-drawer__panel-desc {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.fm-landing-drawer__resource-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
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
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.82);
  padding: 12px 14px;
  color: #334155;
  font-size: 13px;
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

.fm-landing-drawer__resource-row {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.82);
  padding: 14px 16px;
}

.fm-landing-drawer__resource-main {
  min-width: 0;
  flex: 1;
}

.fm-landing-drawer__resource-title {
  color: #111827;
  font-size: 14px;
  font-weight: 600;
}

.fm-landing-drawer__resource-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
}

@media (max-width: 860px) {
  .fm-landing-drawer__resource-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
