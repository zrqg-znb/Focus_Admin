<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type { FailureModeStatisticsChartDatum } from '#/api/failure_mode';

import { computed, ref, watch } from 'vue';

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

const seriesData = computed(() => props.data || []);

watch(
  seriesData,
  (value) => {
    const primary = resolveCssVar('--el-color-primary', '#409eff');
    const primaryLight = resolveCssVar('--el-color-primary-light-3', '#79bbff');
    renderEcharts({
      color: [primary],
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow',
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '10%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: value.map((item) => item.name),
        axisLabel: {
          interval: 0,
          rotate: value.length > 6 ? 24 : 0,
        },
      },
      yAxis: {
        type: 'value',
        splitLine: {
          lineStyle: { color: 'rgba(148,163,184,0.18)' },
        },
      },
      series: [
        {
          name: props.title,
          type: 'bar',
          barMaxWidth: 38,
          data: value.map((item) => item.value),
          itemStyle: {
            borderRadius: [10, 10, 0, 0],
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: primaryLight },
                { offset: 1, color: primary },
              ],
            },
          },
        },
      ],
    });
  },
  { deep: true, immediate: true },
);
</script>

<template>
  <div class="h-[360px] w-full">
    <EchartsUI ref="chartRef" />
  </div>
</template>
