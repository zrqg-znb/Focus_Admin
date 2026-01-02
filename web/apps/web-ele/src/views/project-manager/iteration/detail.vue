<script lang="ts" setup>
import { onMounted, ref, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import { Page, useVbenDrawer, useVbenModal } from '@vben/common-ui';
import { useVbenVxeGrid, type VxeGridProps } from '#/adapter/vxe-table';
import { getProjectIterations, type IterationDetail } from '#/api/project-manager/iteration';
import { getProjectList } from '#/api/project-manager/project';
import { EchartsUI, useEcharts, type EchartsUIType } from '@vben/plugins/echarts';
import { ElDescriptions, ElDescriptionsItem, ElTabs, ElTabPane, ElButton, ElTag, ElMessage } from 'element-plus';
import { Plus, Edit } from '@vben/icons';

import IterationDrawer from './modules/iteration-drawer.vue';
import MetricModal from './modules/metric-modal.vue';

defineOptions({ name: 'IterationDetail' });

const route = useRoute();
const projectId = route.params.id as string;
const activeTab = ref('list');
const projectInfo = ref<any>({});
const iterationList = ref<IterationDetail[]>([]);
const chartRef = ref<EchartsUIType>();
const { renderEcharts } = useEcharts(chartRef);

const [Drawer, drawerApi] = useVbenDrawer({
  connectedComponent: IterationDrawer,
});

const [Modal, modalApi] = useVbenModal({
  connectedComponent: MetricModal,
});

const gridOptions: VxeGridProps = {
  columns: [
    { field: 'name', title: '迭代名称', minWidth: 150 },
    { field: 'code', title: '编码', width: 120 },
    { field: 'start_date', title: '开始时间', width: 120 },
    { field: 'end_date', title: '结束时间', width: 120 },
    { field: 'is_current', title: '当前迭代', width: 100, slots: { default: 'is_current' } },
    { field: 'is_healthy', title: '健康状态', width: 100, slots: { default: 'is_healthy' } },
    { field: 'action', title: '操作', width: 120, fixed: 'right', slots: { default: 'action' } },
  ],
  data: [],
  height: 'auto',
  pagerConfig: { enabled: false },
};

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions,
});

async function fetchData() {
  try {
    // 获取项目信息（为了展示项目名）
    const projectRes = await getProjectList({ page: 1, pageSize: 1, keyword: '', type: '', domain: '' }); 
    // 注意：这里为了简单直接取了列表，实际应该有个 getProjectDetail API，暂时先遍历查找或假定上个页面传参
    // 更好的方式是后端补充 getProjectDetail API。这里我们先 Mock 一下或只展示 ID
    // 为了严谨，我们先通过 ID 筛选
    // 由于 getProjectList 并不支持 ID 精确查找，我们这里暂时略过项目详情的获取，只展示 ID 或等待后端完善
    // 但为了用户体验，我们可以尝试获取一下列表，看能不能匹配到
    // 实际项目中应补充 getProjectDetail(id)
    projectInfo.value = { id: projectId, name: '加载中...' };
    const projects = await getProjectList({ page: 1, pageSize: 1000 });
    const found = projects.items.find(p => p.id === projectId);
    if (found) {
      projectInfo.value = found;
    }

    // 获取迭代列表
    iterationList.value = await getProjectIterations(projectId);
    gridApi.setGridOptions({ data: iterationList.value });
    
    updateChart();
  } catch (error) {
    console.error(error);
  }
}

function updateChart() {
  if (!chartRef.value) return;

  // 按开始时间排序
  const sortedList = [...iterationList.value].sort((a, b) => 
    new Date(a.start_date).getTime() - new Date(b.start_date).getTime()
  );

  const xAxisData = sortedList.map(i => i.name);
  const completionRateData = sortedList.map(i => i.latest_metric?.req_completion_rate || 0);
  const workloadData = sortedList.map(i => i.latest_metric?.req_workload || 0);

  renderEcharts({
    tooltip: { trigger: 'axis' },
    legend: { data: ['需求完成率', '需求工作量'] },
    xAxis: { type: 'category', data: xAxisData },
    yAxis: [
      { type: 'value', name: '完成率(%)', min: 0, max: 100 },
      { type: 'value', name: '工作量' },
    ],
    series: [
      {
        name: '需求完成率',
        type: 'line',
        data: completionRateData,
        yAxisIndex: 0,
      },
      {
        name: '需求工作量',
        type: 'bar',
        data: workloadData,
        yAxisIndex: 1,
        itemStyle: { opacity: 0.5 }
      },
    ],
  });
}

function onCreate() {
  drawerApi.setData({ project_id: projectId }).open();
}

function onRecordMetric(row: any) {
  modalApi.setData({ iteration_id: row.id }).open();
}

watch(activeTab, (val) => {
  if (val === 'trend') {
    // 切换 tab 后需要重新渲染图表以适应宽度
    setTimeout(() => {
      updateChart();
    }, 100);
  }
});

onMounted(() => {
  fetchData();
});
</script>

<template>
  <Page auto-content-height>
    <Drawer @success="fetchData" />
    <Modal @success="fetchData" />

    <div class="flex flex-col h-full gap-4">
      <ElCard shadow="never">
        <ElDescriptions title="项目信息" :column="4">
          <ElDescriptionsItem label="项目名称">{{ projectInfo.name }}</ElDescriptionsItem>
          <ElDescriptionsItem label="项目编码">{{ projectInfo.code }}</ElDescriptionsItem>
          <ElDescriptionsItem label="负责人">
            <span v-for="m in projectInfo.managers" :key="m.id" class="mr-2">{{ m.name }}</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="状态">
            <ElTag :type="projectInfo.is_closed ? 'info' : 'success'">{{ projectInfo.is_closed ? '已结项' : '进行中' }}</ElTag>
          </ElDescriptionsItem>
        </ElDescriptions>
      </ElCard>

      <ElCard shadow="never" class="flex-1 flex flex-col">
        <ElTabs v-model="activeTab" class="h-full flex flex-col">
          <ElTabPane label="迭代列表" name="list" class="h-full">
            <Grid>
              <template #toolbar-tools>
                <ElButton type="primary" @click="onCreate">
                  <Plus class="size-4 mr-1" /> 新建迭代
                </ElButton>
              </template>
              <template #is_current="{ row }">
                <ElTag v-if="row.is_current" type="success" effect="dark">Current</ElTag>
              </template>
              <template #is_healthy="{ row }">
                <ElTag :type="row.is_healthy ? 'success' : 'danger'">{{ row.is_healthy ? '健康' : '风险' }}</ElTag>
              </template>
              <template #action="{ row }">
                <ElButton link type="primary" @click="onRecordMetric(row)">
                  <Edit class="size-4 mr-1" /> 录入数据
                </ElButton>
              </template>
            </Grid>
          </ElTabPane>
          <ElTabPane label="趋势分析" name="trend" class="h-full">
            <div class="h-96 w-full">
              <EchartsUI ref="chartRef" />
            </div>
          </ElTabPane>
        </ElTabs>
      </ElCard>
    </div>
  </Page>
</template>
