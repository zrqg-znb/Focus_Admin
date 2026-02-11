<script lang="ts" setup>
import type { DtsTeamDiTrend, DtsTeamTrend, DtsTrendItem } from '#/api/project-manager/report';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';
import type { EchartsUIType } from '@vben/plugins/echarts';
import { ref, watch } from 'vue';

const props = defineProps<{
  trendData: DtsTrendItem[];
  issueTrend?: DtsTeamTrend | null;
  solveRateTrend?: DtsTeamTrend | null;
  criticalRateTrend?: DtsTeamTrend | null;
  diTrend?: DtsTeamDiTrend | null;
}>();

const chartRef = ref<EchartsUIType>();
const rateChartRef = ref<EchartsUIType>();
const diChartRef = ref<EchartsUIType>();
const { renderEcharts: setTrendOptions } = useEcharts(chartRef);
const { renderEcharts: setRateOptions } = useEcharts(rateChartRef);
const { renderEcharts: setDiOptions } = useEcharts(diChartRef);

watch(
  () => [props.trendData, props.issueTrend],
  () => {
    if (props.issueTrend && props.issueTrend.series?.length) {
      const dates = props.issueTrend.dates;
      const series = props.issueTrend.series.map((s) => ({
        name: s.team_name,
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        data: s.values,
      }));
      setTrendOptions({
        tooltip: { trigger: 'axis' },
        legend: { type: 'scroll', bottom: 0 },
        grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
        xAxis: { type: 'category', boundaryGap: false, data: dates },
        yAxis: { type: 'value' },
        series,
      });
      return;
    }

    if (!props.trendData.length) return;

    const dates = props.trendData.map((i) => i.date);

    // Fallback aggregated issue trend
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
          data: props.trendData.map((i) => i.critical),
          color: '#ef4444',
        },
        {
          name: '严重',
          type: 'line',
          stack: 'Total',
          areaStyle: {},
          emphasis: { focus: 'series' },
          data: props.trendData.map((i) => i.major),
          color: '#f97316',
        },
        {
          name: '一般',
          type: 'line',
          stack: 'Total',
          areaStyle: {},
          emphasis: { focus: 'series' },
          data: props.trendData.map((i) => i.minor),
          color: '#eab308',
        },
        {
          name: '建议',
          type: 'line',
          stack: 'Total',
          areaStyle: {},
          emphasis: { focus: 'series' },
          data: props.trendData.map((i) => i.suggestion),
          color: '#3b82f6',
        },
      ],
    });
  },
  { immediate: true }
);

watch(
  () => [props.trendData, props.solveRateTrend, props.criticalRateTrend],
  () => {
    if (props.solveRateTrend && props.solveRateTrend.series?.length) {
      const dates = props.solveRateTrend.dates;
      const criticalMap = new Map(
        (props.criticalRateTrend?.series || []).map((s) => [s.team_name, s.values]),
      );
      const series: any[] = [];
      props.solveRateTrend.series.forEach((s) => {
        series.push({
          name: `${s.team_name}-总体`,
          type: 'line',
          data: s.values,
          smooth: true,
          symbol: 'circle',
          symbolSize: 5,
        });
        const criticalValues = criticalMap.get(s.team_name);
        if (criticalValues) {
          series.push({
            name: `${s.team_name}-严重`,
            type: 'line',
            data: criticalValues,
            smooth: true,
            symbol: 'circle',
            symbolSize: 5,
            lineStyle: { type: 'dashed' },
          });
        }
      });

      setRateOptions({
        tooltip: { trigger: 'axis' },
        legend: { type: 'scroll', bottom: 0 },
        grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
        xAxis: { type: 'category', boundaryGap: false, data: dates },
        yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
        series,
      });
      return;
    }

    if (!props.trendData.length) return;
    const dates = props.trendData.map((i) => i.date);

    // Fallback aggregated rate trend
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
          data: props.trendData.map((i) => i.solve_rate),
          color: '#10b981',
          smooth: true,
          markLine: {
            data: [{ type: 'average', name: 'Avg' }],
          },
        },
        {
          name: '严重问题解决率',
          type: 'line',
          data: props.trendData.map((i) => i.critical_solve_rate),
          color: '#6366f1',
          smooth: true,
        },
      ],
    });
  },
  { immediate: true }
);

watch(
  () => props.diTrend,
  () => {
    if (!props.diTrend || !props.diTrend.dates?.length) return;
    const dates = props.diTrend.dates;
    const series = (props.diTrend.series || []).map((s) => ({
      name: s.team_name,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      data: s.values,
      connectNulls: false,
    }));

    setDiOptions({
      tooltip: { trigger: 'axis' },
      legend: { type: 'scroll', bottom: 0 },
      grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: dates },
      yAxis: { type: 'value' },
      series,
    });
  },
  { immediate: true }
);
</script>

<template>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
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

    <div class="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
      <div class="mb-4 flex items-center justify-between">
        <h3 class="text-lg font-bold">各团队 DI</h3>
        <span class="text-xs text-gray-400">近七天</span>
      </div>

      <div v-if="props.diTrend && props.diTrend.series && props.diTrend.series.length" class="h-[300px] w-full">
        <EchartsUI ref="diChartRef" />
      </div>
      <div v-else class="h-[300px] flex items-center justify-center text-sm text-gray-400">
        暂无团队 DI 数据
      </div>
    </div>
  </div>
</template>
