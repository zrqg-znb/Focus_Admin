<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type { FailureModeStatisticsChartDatum } from '#/api/failure_mode';

import { ref, watch } from 'vue';

import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

const props = defineProps<{
  data: FailureModeStatisticsChartDatum[];
  title: string;
}>();

function resolveCssVar(name: string, fallback: string) {
  if (typeof window === 'undefined') {
    return fallback;
  }
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return value || fallback;
}

const chartRef = ref<EchartsUIType>();
const { renderEcharts } = useEcharts(chartRef);

watch(
  () => props.data,
  (value) => {
    const primary = resolveCssVar('--el-color-primary', '#409eff');
    const primaryLight = resolveCssVar('--el-color-primary-light-4', '#8cc5ff');
    const primaryMuted = resolveCssVar('--el-color-primary-light-8', '#d9ecff');
    renderEcharts({
      color: [primary, primaryLight, primaryMuted],
      tooltip: {
        trigger: 'item',
      },
      legend: {
        bottom: '0%',
        left: 'center',
      },
      series: [
        {
          name: props.title,
          type: 'pie',
          radius: ['42%', '72%'],
          center: ['50%', '46%'],
          itemStyle: {
            borderRadius: 12,
            borderColor: '#fff',
            borderWidth: 3,
          },
          label: {
            show: false,
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 18,
              fontWeight: 700,
              formatter: '{b}\n{c}',
            },
          },
          labelLine: {
            show: false,
          },
          data: value || [],
        },
      ],
    });
  },
  { deep: true, immediate: true },
);
</script>

<template>
  <div class="h-[300px] w-full">
    <EchartsUI ref="chartRef" />
  </div>
</template>
