<script lang="ts" setup>
import { onMounted, ref, computed } from 'vue';
import { useRoute } from 'vue-router';
import { Page, useVbenModal } from '@vben/common-ui';
import { getProjectQualityDetails, type ModuleQualityDetail } from '#/api/project-manager/quality';
import { getProjectList } from '#/api/project-manager/project';
import { EchartsUI, useEcharts, type EchartsUIType } from '@vben/plugins/echarts';
import { ElRow, ElCol, ElCard, ElMenu, ElMenuItem, ElEmpty, ElButton, ElDescriptions, ElDescriptionsItem } from 'element-plus';
import { Edit } from '@vben/icons';
import MetricModal from './modules/metric-modal.vue';

defineOptions({ name: 'QualityDetail' });

const route = useRoute();
const projectId = route.params.id as string;
const projectInfo = ref<any>({});
const moduleDetails = ref<ModuleQualityDetail[]>([]);
const activeModuleIndex = ref<string>('0');

const chartScaleRef = ref<EchartsUIType>();
const { renderEcharts: renderScaleChart } = useEcharts(chartScaleRef);

const chartIssueRef = ref<EchartsUIType>();
const { renderEcharts: renderIssueChart } = useEcharts(chartIssueRef);

const [Modal, modalApi] = useVbenModal({
  connectedComponent: MetricModal,
});

const currentModule = computed(() => {
  if (moduleDetails.value.length === 0) return null;
  return moduleDetails.value[Number(activeModuleIndex.value)];
});

async function fetchData() {
  try {
    // 获取项目信息
    projectInfo.value = { id: projectId, name: '加载中...' };
    const projects = await getProjectList({ page: 1, pageSize: 1000 });
    const found = projects.items.find(p => p.id === projectId);
    if (found) {
      projectInfo.value = found;
    }

    // 获取模块详情
    moduleDetails.value = await getProjectQualityDetails(projectId);
    if (moduleDetails.value.length > 0 && !currentModule.value) {
      activeModuleIndex.value = '0';
    }

    updateCharts();
  } catch (error) {
    console.error(error);
  }
}

function updateCharts() {
  if (!currentModule.value) return;

  const metrics = currentModule.value.metrics_history || [];
  if (metrics.length === 0) {
    // 处理空数据情况，清空图表或显示空状态
    // 这里简单地渲染空图表
    renderScaleChart({ title: { text: '代码规模趋势' }, series: [] });
    renderIssueChart({ title: { text: '质量问题趋势' }, series: [] });
    return;
  }

  const xAxisData = metrics.map(m => m.record_date);

  // Chart 1: Code Scale
  renderScaleChart({
    title: { text: '代码规模趋势' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['代码行数', '函数个数'] },
    xAxis: { type: 'category', data: xAxisData },
    yAxis: { type: 'value' },
    series: [
      { name: '代码行数', type: 'line', data: metrics.map(m => m.loc) },
      { name: '函数个数', type: 'line', data: metrics.map(m => m.function_count) },
    ],
  });

  // Chart 2: Quality Issues
  renderIssueChart({
    title: { text: '质量问题趋势' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['重复率(%)', '危险函数'] },
    xAxis: { type: 'category', data: xAxisData },
    yAxis: [
      { type: 'value', name: '重复率(%)', min: 0, max: 100 },
      { type: 'value', name: '个数' },
    ],
    series: [
      { name: '重复率(%)', type: 'line', data: metrics.map(m => m.duplication_rate), yAxisIndex: 0 },
      { name: '危险函数', type: 'bar', data: metrics.map(m => m.dangerous_func_count), yAxisIndex: 1 },
    ],
  });
}

function onSelectModule(index: string) {
  activeModuleIndex.value = index;
  setTimeout(() => updateCharts(), 100);
}

function onRecordMetric() {
  if (currentModule.value) {
    modalApi.setData({ module_id: currentModule.value.module_info.id }).open();
  }
}

onMounted(() => {
  fetchData();
});
</script>

<template>
  <Page auto-content-height>
    <Modal @success="fetchData" />

    <div class="h-full flex flex-col gap-4">
      <ElCard shadow="never">
        <h2 class="text-lg font-bold">{{ projectInfo.name }} - 代码质量详情</h2>
      </ElCard>

      <div class="flex-1 flex gap-4 overflow-hidden">
        <!-- 左侧模块列表 -->
        <ElCard shadow="never" class="w-1/5 h-full overflow-y-auto" :body-style="{ padding: '0' }">
          <div v-if="moduleDetails.length === 0" class="p-4 text-center text-gray-400">
            暂无模块
          </div>
          <ElMenu
            v-else
            :default-active="activeModuleIndex"
            class="border-none"
            @select="onSelectModule"
          >
            <ElMenuItem v-for="(item, index) in moduleDetails" :key="index" :index="String(index)">
              <span class="truncate">{{ item.module_info.name }}</span>
            </ElMenuItem>
          </ElMenu>
        </ElCard>

        <!-- 右侧图表区域 -->
        <ElCard shadow="never" class="flex-1 h-full overflow-y-auto">
          <div v-if="!currentModule" class="h-full flex items-center justify-center">
            <ElEmpty description="请选择模块查看详情" />
          </div>

          <div v-else class="flex flex-col gap-6">
            <div class="flex justify-between items-center border-b pb-4">
              <ElDescriptions :column="2">
                <ElDescriptionsItem label="模块名称">{{ currentModule.module_info.name }}</ElDescriptionsItem>
                <ElDescriptionsItem label="责任人">{{ currentModule.module_info.owner_name || '未指定' }}</ElDescriptionsItem>
              </ElDescriptions>
              <ElButton type="primary" @click="onRecordMetric">
                <Edit class="size-4 mr-1" /> 录入数据
              </ElButton>
            </div>

            <div class="h-80 w-full">
              <EchartsUI ref="chartScaleRef" />
            </div>

            <div class="h-80 w-full">
              <EchartsUI ref="chartIssueRef" />
            </div>
          </div>
        </ElCard>
      </div>
    </div>
  </Page>
</template>
