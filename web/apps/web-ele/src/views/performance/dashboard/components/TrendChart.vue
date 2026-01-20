<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import { onMounted, ref, watch } from 'vue';

import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

import { getTrendDataApi } from '#/api/core/performance';

const props = defineProps<{
  baselineValue?: number;
  indicatorId: string;
  startDate?: string;
  endDate?: string;
}>();

const chartRef = ref<EchartsUIType>();
const { renderEcharts } = useEcharts(chartRef);
const loading = ref(false);

async function fetchDataAndRender() {
  if (!props.indicatorId) return;

  loading.value = true;
  try {
    const data = await getTrendDataApi(props.indicatorId, {
      start_date: props.startDate,
      end_date: props.endDate,
    });
    // data is Array of {date, value, fluctuation_value}
    const dates = data.map((item) => item.date);
    const values = data.map((item) => item.value);

    renderEcharts({
      grid: {
        bottom: 30,
        containLabel: true,
        left: 20,
        right: 40,
        top: 40,
      },
      tooltip: {
        trigger: 'axis',
      },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: false,
      },
      yAxis: {
        type: 'value',
        scale: true, // Avoid starting from 0 if values are large and close to each other
      },
      series: [
        {
          data: values,
          type: 'line',
          smooth: true,
          areaStyle: {
            opacity: 0.1,
          },
          itemStyle: {
            color: '#409eff',
          },
          markLine:
            props.baselineValue === undefined
              ? undefined
              : {
                  data: [
                    {
                      yAxis: props.baselineValue,
                      name: '基线值',
                      lineStyle: {
                        color: '#f56c6c',
                        type: 'dashed',
                        width: 2,
                      },
                      label: {
                        formatter: '基线: {c}',
                        position: 'end',
                      },
                    },
                  ],
                  symbol: ['none', 'none'],
                  animation: false,
                },
        },
      ],
    });
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.indicatorId,
  () => {
    fetchDataAndRender();
  },
);

onMounted(() => {
  fetchDataAndRender();
});
</script>

<template>
  <div class="h-80 w-full p-4" v-loading="loading">
    <EchartsUI ref="chartRef" />
  </div>
</template>
