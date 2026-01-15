<script lang="ts" setup>
import type { QGNode } from '#/api/project-manager/report';
import { computed } from 'vue';
import { ElTooltip } from 'element-plus';

const props = defineProps<{
  milestones: QGNode[];
}>();

// Fishbone Logic
// We will alternate items top and bottom
const fishboneItems = computed(() => {
  return props.milestones.map((ms, index) => {
    const t = parseDate((ms as any).date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const isPast = typeof t === 'number' ? t < today.getTime() : false;
    
    // Check if node has risk (mock logic for now, similar to Gantt)
    // Assuming backend will provide `has_risk` or we check status
    const hasRisk = (ms as any).has_risk || ms.status === 'delayed'; // Fallback to status

    return {
      ...ms,
      isTop: index % 2 === 0,
      isPast,
      hasRisk,
      left: `${(index / (props.milestones.length - 1 || 1)) * 90 + 5}%` // Distributed 5% to 95%
    };
  });
});

function parseDate(value: unknown): number | null {
  if (!value) return null;
  const d = new Date(String(value));
  const t = d.getTime();
  return Number.isFinite(t) ? t : null;
}

const todayPosition = computed(() => {
  const dates = props.milestones
    .map((m) => parseDate((m as any).date))
    .filter((t): t is number => typeof t === 'number');
  if (dates.length < 2) return null;

  const min = Math.min(...dates);
  const max = Math.max(...dates);
  if (max <= min) return null;

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
    case 'completed': return 'bg-green-500 border-green-200';
    case 'pending': return 'bg-blue-500 border-blue-200';
    case 'delayed': return 'bg-red-500 border-red-200';
    default: return 'bg-gray-300';
  }
}
</script>

<template>
  <div class="h-full w-full flex items-center px-4 relative">
      <!-- Main Axis -->
      <div class="absolute w-[calc(100%-48px)] left-6 h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full z-0">
         <div
           v-if="todayPosition"
           class="absolute left-0 top-0 h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400"
           :style="{ width: `${todayPosition.ratio * 100}%` }"
         />
         <div class="absolute right-0 -top-1.5 w-0 h-0 border-l-[12px] border-l-gray-100 border-t-[6px] border-t-transparent border-b-[6px] border-b-transparent dark:border-l-gray-700"></div>
      </div>

      <div
        v-if="todayPosition"
        class="absolute top-1/2 -translate-y-1/2 z-10 pointer-events-none"
        :style="{ left: todayPosition.left }"
      >
        <div class="relative -translate-x-1/2">
          <div class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-10 w-0.5 bg-primary/70" />
          <div class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-3 w-3 rounded-full bg-primary shadow-sm ring-4 ring-primary/20" />
          <div class="absolute left-1/2 -top-7 -translate-x-1/2 rounded-full bg-primary px-2 py-0.5 text-[10px] font-bold text-white shadow-sm">
            今日
          </div>
        </div>
      </div>
      
      <!-- Nodes -->
      <div v-for="(item, index) in fishboneItems" :key="index" 
           class="absolute h-full flex flex-col items-center justify-center transition-all group hover:z-20"
           :style="{ left: item.left }">
           
         <!-- Connection Line (Top) -->
         <div v-if="item.isTop" 
              class="absolute left-1/2 top-1/2 h-12 w-0.5 -translate-x-1/2 -translate-y-full bg-gray-200 dark:bg-gray-600 origin-bottom -rotate-[20deg] group-hover:bg-primary transition-colors"
              :class="{ 'bg-red-400': item.hasRisk }"></div>
         
         <!-- Connection Line (Bottom) -->
         <div v-if="!item.isTop" 
              class="absolute left-1/2 top-1/2 h-12 w-0.5 -translate-x-1/2 bg-gray-200 dark:bg-gray-600 origin-top rotate-[20deg] group-hover:bg-primary transition-colors"
              :class="{ 'bg-red-400': item.hasRisk }"></div>
         
         <!-- Content Bubble -->
         <div class="absolute w-28 p-2 rounded-xl border bg-white dark:bg-gray-800 shadow-sm text-center z-10 transition-all duration-300 hover:shadow-md hover:scale-110 cursor-default"
              :class="[
                  item.isTop ? 'bottom-[65%]' : 'top-[65%]',
                  item.hasRisk 
                    ? 'border-red-500 bg-red-50 dark:bg-red-900/30 animate-pulse-border'
                    : item.status === 'delayed'
                      ? 'border-red-200 bg-red-50 dark:bg-red-900/20'
                      : item.isPast
                        ? 'border-emerald-200 bg-emerald-50/60 dark:border-emerald-900/40 dark:bg-emerald-900/10'
                        : 'border-gray-200 dark:border-gray-700'
              ]">
            <div class="text-xs font-bold truncate text-gray-800 dark:text-gray-100" :title="item.name">{{ item.name }}</div>
            <div class="text-[10px] text-gray-400 mt-0.5 font-mono">{{ item.date }}</div>
            
            <div v-if="item.hasRisk" class="mt-1 flex items-center justify-center gap-1">
               <span class="text-[10px] font-bold text-red-500">⚠ 风险预警</span>
            </div>
            
            <div v-else class="mt-1.5 h-1.5 w-full rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                <div class="h-full w-full transition-all duration-500" :class="getStatusColor(item.status).split(' ')[0]"></div>
            </div>
         </div>
         
         <!-- Axis Point -->
         <div class="w-3.5 h-3.5 rounded-full border-[3px] bg-white z-10 transition-all group-hover:scale-125 group-hover:border-primary" 
              :class="item.hasRisk 
                ? 'border-red-500 bg-red-100'
                : item.status === 'delayed'
                  ? 'border-red-400'
                  : item.isPast
                    ? 'border-emerald-400'
                    : 'border-gray-300 dark:border-gray-500'"></div>
      </div>
  </div>
</template>

<style scoped>
@keyframes pulse-border {
  0% { border-color: rgba(239, 68, 68, 0.5); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
  50% { border-color: rgba(239, 68, 68, 1); box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.1); }
  100% { border-color: rgba(239, 68, 68, 0.5); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
}
.animate-pulse-border {
  animation: pulse-border 2s infinite;
}
</style>
