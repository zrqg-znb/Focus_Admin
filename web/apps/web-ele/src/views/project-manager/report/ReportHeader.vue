<script lang="ts" setup>
import { computed, ref, watch } from 'vue';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';
import type { EchartsUIType } from '@vben/plugins/echarts';

const props = defineProps<{
  radarData: Array<{ name: string; value: number; max: number }>;
  healthScore: number;
  healthLevel: 'healthy' | 'warning' | 'error';
}>();

const chartRef = ref<EchartsUIType>();
const { renderEcharts } = useEcharts(chartRef);

const bgColor = computed(() => {
  switch (props.healthLevel) {
    case 'healthy':
      return 'bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border-green-100 dark:border-green-800';
    case 'warning':
      return 'bg-gradient-to-br from-orange-50 to-amber-50 dark:from-orange-900/20 dark:to-amber-900/20 border-orange-100 dark:border-orange-800';
    case 'error':
      return 'bg-gradient-to-br from-red-50 to-rose-50 dark:from-red-900/20 dark:to-rose-900/20 border-red-100 dark:border-red-800';
    default:
      return 'bg-gray-50';
  }
});

const scoreColor = computed(() => {
    switch (props.healthLevel) {
    case 'healthy': return 'text-green-600';
    case 'warning': return 'text-orange-600';
    case 'error': return 'text-red-600';
    default: return 'text-gray-600';
  }
})

watch(
  () => props.radarData,
  () => {
    if (!props.radarData.length) return;
    
    renderEcharts({
      radar: {
        indicator: props.radarData.map(item => ({ name: item.name, max: item.max })),
        splitArea: {
          areaStyle: {
            color: ['rgba(255,255,255,0.8)', 'rgba(255,255,255,0.6)']
          }
        },
        axisName: {
          color: '#666'
        }
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: props.radarData.map(item => item.value),
              name: 'Project Health',
              areaStyle: {
                color: props.healthLevel === 'healthy' ? 'rgba(34, 197, 94, 0.4)' : 
                       props.healthLevel === 'warning' ? 'rgba(249, 115, 22, 0.4)' : 
                       'rgba(239, 68, 68, 0.4)'
              },
              itemStyle: {
                color: props.healthLevel === 'healthy' ? '#22c55e' : 
                       props.healthLevel === 'warning' ? '#f97316' : 
                       '#ef4444'
              }
            }
          ]
        }
      ]
    });
  },
  { immediate: true }
);
</script>

<template>
  <div class="h-full rounded-2xl border p-6 transition-all shadow-sm" :class="bgColor">
    <div class="flex h-full items-center justify-between">
      <!-- Radar Chart -->
      <div class="h-64 w-64 flex-shrink-0">
         <EchartsUI ref="chartRef" />
      </div>
      
      <!-- Text Description -->
      <div class="flex-1 pl-8">
        <h2 class="text-lg font-medium text-gray-500 mb-2">项目健康度</h2>
        <div class="text-5xl font-bold mb-4" :class="scoreColor">
          {{ healthScore }}
          <span class="text-lg font-normal text-gray-500">/ 100</span>
        </div>
        
        <div class="space-y-3">
           <div class="flex items-center gap-2" v-if="healthLevel === 'healthy'">
              <div class="w-2 h-2 rounded-full bg-green-500"></div>
              <span class="text-gray-700 dark:text-gray-300">项目运行良好，各项指标正常。</span>
           </div>
           <div class="flex items-center gap-2" v-if="healthLevel === 'warning'">
              <div class="w-2 h-2 rounded-full bg-orange-500"></div>
              <span class="text-gray-700 dark:text-gray-300">项目存在潜在风险，请关注警告指标。</span>
           </div>
           <div class="flex items-center gap-2" v-if="healthLevel === 'error'">
              <div class="w-2 h-2 rounded-full bg-red-500"></div>
              <span class="text-gray-700 dark:text-gray-300">项目处于高风险状态，建议立即介入。</span>
           </div>
        </div>
      </div>
    </div>
  </div>
</template>
