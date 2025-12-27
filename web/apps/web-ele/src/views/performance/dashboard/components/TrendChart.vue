<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';
import { ref, watch, onMounted } from 'vue';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';
import { getTrendDataApi } from '#/api/core/performance';

const props = defineProps<{
    indicatorId: string;
}>();

const chartRef = ref<EchartsUIType>();
const { renderEcharts } = useEcharts(chartRef);

async function fetchDataAndRender() {
    if (!props.indicatorId) return;
    
    try {
        const data = await getTrendDataApi(props.indicatorId);
        // data is Array of {date, value, fluctuation_value}
        const dates = data.map(item => item.date);
        const values = data.map(item => item.value);
        
        renderEcharts({
            grid: {
              bottom: 20,
              containLabel: true,
              left: '1%',
              right: '1%',
              top: '5%',
            },
            tooltip: {
                trigger: 'axis'
            },
            xAxis: {
                type: 'category',
                data: dates,
                boundaryGap: false
            },
            yAxis: {
                type: 'value'
            },
            series: [
                {
                    data: values,
                    type: 'line',
                    smooth: true,
                    areaStyle: {}
                }
            ]
        });
    } catch (e) {
        console.error(e);
    }
}

watch(() => props.indicatorId, () => {
    fetchDataAndRender();
});

onMounted(() => {
    fetchDataAndRender();
});
</script>

<template>
  <div class="h-64 w-full">
    <EchartsUI ref="chartRef" />
  </div>
</template>
