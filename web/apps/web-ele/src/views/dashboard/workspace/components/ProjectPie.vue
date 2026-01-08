<script lang="ts" setup>
import { computed, type PropType, ref, watch } from 'vue';
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
    default: '项目分布',
  },
});

const chartRef = ref<EchartsUIType>();
const { renderEcharts } = useEcharts(chartRef);

watch(
  () => props.data,
  (newData) => {
    if (!newData || newData.length === 0) return;
    
    renderEcharts({
      tooltip: {
        trigger: 'item',
      },
      legend: {
        bottom: '1%',
        left: 'center',
      },
      series: [
        {
          name: props.title,
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: {
            show: false,
            position: 'center',
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 20,
              fontWeight: 'bold',
            },
          },
          labelLine: {
            show: false,
          },
          data: newData,
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
