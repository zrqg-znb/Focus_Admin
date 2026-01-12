<script lang="ts" setup>
import type { DtsTrendItem } from '#/api/project-manager/report';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';
import type { EchartsUIType } from '@vben/plugins/echarts';
import { ref, watch } from 'vue';

const props = defineProps<{
  trendData: DtsTrendItem[];
}>();

const chartRef = ref<EchartsUIType>();
const rateChartRef = ref<EchartsUIType>();
const { renderEcharts: setTrendOptions } = useEcharts(chartRef);
const { renderEcharts: setRateOptions } = useEcharts(rateChartRef);

watch(
  () => props.trendData,
  () => {
    if (!props.trendData.length) return;
    
    const dates = props.trendData.map(i => i.date);
    
    // 1. Issue Counts Chart
    setTrendOptions({
      tooltip: { trigger: 'axis' },
      legend: { data: ['关键', '严重', '一般', '建议'], bottom: 0 },
      grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: dates },
      yAxis: { type: 'value' },
      series: [
        {
          name: '关键',
          type: 'line',
          stack: 'Total',
          areaStyle: {},
          emphasis: { focus: 'series' },
          data: props.trendData.map(i => i.critical),
          color: '#ef4444'
        },
        {
          name: '严重',
          type: 'line',
          stack: 'Total',
          areaStyle: {},
          emphasis: { focus: 'series' },
          data: props.trendData.map(i => i.major),
          color: '#f97316'
        },
        {
          name: '一般',
          type: 'line',
          stack: 'Total',
          areaStyle: {},
          emphasis: { focus: 'series' },
          data: props.trendData.map(i => i.minor),
          color: '#eab308'
        },
        {
          name: '建议',
          type: 'line',
          stack: 'Total',
          areaStyle: {},
          emphasis: { focus: 'series' },
          data: props.trendData.map(i => i.suggestion),
          color: '#3b82f6'
        }
      ]
    });
    
    // 2. Rate Chart
    setRateOptions({
       tooltip: { trigger: 'axis', formatter: '{b}<br />{a0}: {c0}%<br />{a1}: {c1}%' },
       legend: { data: ['总体解决率', '严重问题解决率'], bottom: 0 },
       grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
       xAxis: { type: 'category', boundaryGap: false, data: dates },
       yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
       series: [
         {
           name: '总体解决率',
           type: 'line',
           data: props.trendData.map(i => i.solve_rate),
           color: '#10b981',
           smooth: true,
           markLine: {
             data: [{ type: 'average', name: 'Avg' }]
           }
         },
         {
           name: '严重问题解决率',
           type: 'line',
           data: props.trendData.map(i => i.critical_solve_rate),
           color: '#6366f1',
           smooth: true
         }
       ]
    });
  },
  { immediate: true }
);
</script>

<template>
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <!-- Issue Trend -->
    <div class="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
      <h3 class="mb-4 text-lg font-bold">近七天问题单趋势</h3>
      <div class="h-[300px] w-full">
         <EchartsUI ref="chartRef" />
      </div>
    </div>
    
    <!-- Rate Trend -->
    <div class="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
      <h3 class="mb-4 text-lg font-bold">问题单解决率趋势</h3>
      <div class="h-[300px] w-full">
         <EchartsUI ref="rateChartRef" />
      </div>
    </div>
  </div>
</template>
