<script lang="ts" setup>
import { type PropType, ref, watch } from 'vue';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';
import type { EchartsUIType } from '@vben/plugins/echarts';

interface DataItem {
  name: string;
  value: number;
}

const props = defineProps({
  data: {
    type: Array as PropType<DataItem[]>,
    default: () => [],
  },
  title: {
    type: String,
    default: '项目类型',
  },
});

const chartRef = ref<EchartsUIType>();
const { renderEcharts } = useEcharts(chartRef);

watch(
  () => props.data,
  (newData) => {
    if (!newData || newData.length === 0) return;
    
    const categories = newData.map(item => item.name);
    const values = newData.map(item => item.value);

    renderEcharts({
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow',
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: [
        {
          type: 'category',
          data: categories,
          axisTick: {
            alignWithLabel: true,
          },
        },
      ],
      yAxis: [
        {
          type: 'value',
        },
      ],
      series: [
        {
          name: props.title,
          type: 'bar',
          barWidth: '60%',
          data: values,
          itemStyle: {
            borderRadius: [5, 5, 0, 0],
            color: '#5b8ff9',
          },
        },
      ],
    });
  },
  { immediate: true, deep: true },
);
</script>

<template>
  <div class="h-[300px] w-full">
    <EchartsUI ref="chartRef" />
  </div>
</template>
