<script lang="ts" setup>
import type { QGNode } from '#/api/project-manager/report';

import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';

import { ElButton, ElEmpty, ElMessage } from 'element-plus';

import { getProjectRisksApi } from '#/api/project-manager/milestone';

import RiskHandleDialog from '../milestone/components/RiskHandleDialog.vue';

const props = defineProps<{
  milestones: QGNode[];
  projectId: string;
  projectName: string;
}>();

const emit = defineEmits(['refresh']);
const router = useRouter();

const riskHandleDialogRef = ref();
const loadingRisk = ref(false);

function goToConfig() {
  router.push('/project-manager/project');
}

// Fishbone Logic
// We will alternate items top and bottom
const fishboneItems = computed(() => {
  return props.milestones.map((ms, index) => {
    const t = parseDate((ms as any).date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const isPast = typeof t === 'number' ? t < today.getTime() : false;

    // Check risk status from backend
    // risk_status: 'pending' (Error) | 'confirmed' (Warning) | null
    const riskStatus = (ms as any).risk_status;
    const hasRisk = (ms as any).has_risk || !!riskStatus;

    return {
      ...ms,
      isTop: index % 2 === 0,
      isPast,
      hasRisk,
      riskStatus,
      left: `${(index / (props.milestones.length - 1 || 1)) * 90 + 5}%`, // Distributed 5% to 95%
    };
  });
});

function parseDate(value: unknown): null | number {
  if (!value) {
    return null;
  }
  const d = new Date(String(value));
  const t = d.getTime();
  return Number.isFinite(t) ? t : null;
}

const todayPosition = computed(() => {
  const dates = props.milestones
    .map((m) => parseDate((m as any).date))
    .filter((t): t is number => typeof t === 'number');
  if (dates.length < 2) {
    return null;
  }

  const min = Math.min(...dates);
  const max = Math.max(...dates);
  if (max <= min) {
    return null;
  }

  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const t = now.getTime();

  const ratio = Math.min(1, Math.max(0, (t - min) / (max - min)));
  return {
    left: `${ratio * 90 + 5}%`,
    ratio,
  };
});

function getStatusColor(status: string) {
  switch (status) {
    case 'completed': {
      return 'bg-green-500 border-green-200';
    }
    case 'delayed': {
      return 'bg-red-500 border-red-200';
    }
    case 'pending': {
      return 'bg-blue-500 border-blue-200';
    }
    default: {
      return 'bg-gray-300';
    }
  }
}

async function handleNodeClick(item: any) {
  if (item.hasRisk) {
    loadingRisk.value = true;
    try {
      // Fetch risks for the project
      const risks = await getProjectRisksApi(props.projectId);

      // Match the specific risk for this QG node
      // Prioritize active risks (not closed), then look for closed ones
      const riskItem =
        risks.find((r) => r.qg_name === item.name && r.status !== 'closed') ||
        risks.find((r) => r.qg_name === item.name);

      if (riskItem) {
        riskHandleDialogRef.value?.open(riskItem);
      } else {
        ElMessage.warning(`未找到里程碑 [${item.name}] 的关联风险详情`);
      }
    } catch (error) {
      console.error('Failed to fetch risk details:', error);
      ElMessage.error('获取风险详情失败，请稍后重试');
    } finally {
      loadingRisk.value = false;
    }
  }
}

function handleRiskSuccess() {
  emit('refresh');
}

function getRiskClasses(item: any) {
  if (!item.hasRisk) {
    if (item.status === 'delayed') {
      return 'border-red-200 bg-red-50 dark:bg-red-900/20';
    }
    if (item.isPast) {
      return 'border-emerald-200 bg-emerald-50/60 dark:border-emerald-900/40 dark:bg-emerald-900/10';
    }
    return 'border-gray-200 dark:border-gray-700';
  }

  // Risk Styling
  if (item.riskStatus === 'confirmed') {
    return 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/30 animate-pulse-yellow cursor-pointer hover:bg-yellow-100';
  }
  // Default to pending (red)
  return 'border-red-500 bg-red-50 dark:bg-red-900/30 animate-pulse-border cursor-pointer hover:bg-red-100';
}
</script>

<template>
  <div
    v-if="!milestones || milestones.length === 0"
    class="flex h-full w-full flex-col items-center justify-center"
  >
    <ElEmpty description="该项目未开启里程碑配置，请前往项目配置页面开启并添加数据" />
    <ElButton class="mt-4" type="primary" @click="goToConfig">
      去项目配置页面
    </ElButton>
  </div>
  <div
    v-else
    v-loading="loadingRisk"
    class="relative flex h-full w-full items-center px-4"
  >
    <!-- Main Axis -->
    <div
      class="absolute left-6 z-0 h-1.5 w-[calc(100%-48px)] rounded-full bg-gray-100 dark:bg-gray-700"
    >
      <div
        v-if="todayPosition"
        :style="{ width: `${todayPosition.ratio * 100}%` }"
        class="absolute left-0 top-0 h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400"
      ></div>
      <div
        class="absolute -top-1.5 right-0 h-0 w-0 border-b-[6px] border-l-[12px] border-t-[6px] border-b-transparent border-l-gray-100 border-t-transparent dark:border-l-gray-700"
      ></div>
    </div>

    <div
      v-if="todayPosition"
      :style="{ left: todayPosition.left }"
      class="pointer-events-none absolute top-1/2 z-10 -translate-y-1/2"
    >
      <div class="relative -translate-x-1/2">
        <div
          class="absolute left-1/2 top-1/2 h-10 w-0.5 -translate-x-1/2 -translate-y-1/2 bg-primary/70"
        ></div>
        <div
          class="absolute left-1/2 top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary shadow-sm ring-4 ring-primary/20"
        ></div>
        <div
          class="absolute -top-7 left-1/2 -translate-x-1/2 rounded-full bg-primary px-2 py-0.5 text-[10px] font-bold text-white shadow-sm"
        >
          今日
        </div>
      </div>
    </div>

    <!-- Nodes -->
    <div
      v-for="(item, index) in fishboneItems"
      :key="index"
      :style="{ left: item.left }"
      class="group absolute flex h-full flex-col items-center justify-center transition-all hover:z-20"
    >
      <!-- Connection Line (Top) -->
      <div
        v-if="item.isTop"
        :class="{
          'bg-red-400': item.hasRisk && item.riskStatus !== 'confirmed',
          'bg-yellow-500': item.hasRisk && item.riskStatus === 'confirmed',
        }"
        class="absolute left-1/2 top-1/2 h-12 w-0.5 -translate-x-1/2 -translate-y-full origin-bottom -rotate-[20deg] bg-gray-200 transition-colors group-hover:bg-primary dark:bg-gray-600"
      ></div>

      <!-- Connection Line (Bottom) -->
      <div
        v-if="!item.isTop"
        :class="{
          'bg-red-400': item.hasRisk && item.riskStatus !== 'confirmed',
          'bg-yellow-500': item.hasRisk && item.riskStatus === 'confirmed',
        }"
        class="absolute left-1/2 top-1/2 h-12 w-0.5 -translate-x-1/2 origin-top rotate-[20deg] bg-gray-200 transition-colors group-hover:bg-primary dark:bg-gray-600"
      ></div>

      <!-- Content Bubble -->
      <div
        :class="[
          item.isTop ? 'bottom-[65%]' : 'top-[65%]',
          getRiskClasses(item),
        ]"
        class="absolute z-10 w-28 rounded-xl border p-2 text-center shadow-sm transition-all duration-300 hover:scale-110 hover:shadow-md"
        @click="handleNodeClick(item)"
      >
        <div
          :title="item.name"
          class="truncate text-xs font-bold text-gray-800 dark:text-gray-100"
        >
          {{ item.name }}
        </div>
        <div class="mt-0.5 font-mono text-[10px] text-gray-400">
          {{ item.date }}
        </div>

        <div
          v-if="item.hasRisk"
          class="mt-1 flex items-center justify-center gap-1"
        >
          <span
            :class="
              item.riskStatus === 'confirmed'
                ? 'text-yellow-600'
                : 'text-red-500'
            "
            class="text-[10px] font-bold"
          >
            {{ item.riskStatus === 'confirmed' ? '⚠ 已确认' : '⚠ 风险预警' }}
          </span>
        </div>

        <div
          v-else
          class="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-700"
        >
          <div
            :class="getStatusColor(item.status).split(' ')[0]"
            class="h-full w-full transition-all duration-500"
          ></div>
        </div>
      </div>

      <!-- Axis Point -->
      <div
        :class="
          item.hasRisk
            ? item.riskStatus === 'confirmed'
              ? 'border-yellow-500 bg-yellow-100'
              : 'border-red-500 bg-red-100'
            : item.status === 'delayed'
              ? 'border-red-400'
              : item.isPast
                ? 'border-emerald-400'
                : 'border-gray-300 dark:border-gray-500'
        "
        class="z-10 h-3.5 w-3.5 rounded-full border-[3px] bg-white transition-all group-hover:border-primary group-hover:scale-125"
      ></div>
    </div>

    <RiskHandleDialog ref="riskHandleDialogRef" @success="handleRiskSuccess" />
  </div>
</template>

<style scoped>
@keyframes pulse-border {
  0% {
    border-color: rgb(239 68 68 / 50%);
    box-shadow: 0 0 0 0 rgb(239 68 68 / 40%);
  }
  50% {
    border-color: rgb(239 68 68 / 100%);
    box-shadow: 0 0 0 4px rgb(239 68 68 / 10%);
  }
  100% {
    border-color: rgb(239 68 68 / 50%);
    box-shadow: 0 0 0 0 rgb(239 68 68 / 40%);
  }
}

.animate-pulse-border {
  animation: pulse-border 2s infinite;
}

@keyframes pulse-yellow {
  0% {
    border-color: rgb(234 179 8 / 50%);
    box-shadow: 0 0 0 0 rgb(234 179 8 / 40%);
  }
  50% {
    border-color: rgb(234 179 8 / 100%);
    box-shadow: 0 0 0 4px rgb(234 179 8 / 10%);
  }
  100% {
    border-color: rgb(234 179 8 / 50%);
    box-shadow: 0 0 0 0 rgb(234 179 8 / 40%);
  }
}

.animate-pulse-yellow {
  animation: pulse-yellow 2s infinite;
}
</style>
