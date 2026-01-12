<script lang="ts" setup>
import type { ProjectReport } from '#/api/project-manager/report';
import { onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { WorkbenchHeader } from '@vben/common-ui';
import { preferences } from '@vben/preferences';
import { ElSkeleton, ElButton } from 'element-plus';
import { IconifyIcon } from '@vben/icons';
import { getProjectReportApi } from '#/api/project-manager/report';

import ReportHeader from './ReportHeader.vue';
import MilestoneFishbone from './MilestoneFishbone.vue';
import DtsTrendChart from './DtsTrendChart.vue';
import IterationCard from './IterationCard.vue';
import CodeQualityCard from './CodeQualityCard.vue';

defineOptions({ name: 'ProjectDetailReport' });

const route = useRoute();
const projectId = route.params.id as string;
const loading = ref(true);
const reportData = ref<ProjectReport | null>(null);

async function fetchReport() {
  try {
    loading.value = true;
    reportData.value = await getProjectReportApi(projectId);
  } catch (error) {
    console.error('Failed to fetch report', error);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  fetchReport();
});
</script>

<template>
  <div class="p-4">
    <WorkbenchHeader
      avatar="https://unpkg.com/@vbenjs/static-source@0.1.7/source/logo-v1.webp"
      class="mb-4 shadow-sm border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-[#151515]"
    >
      <template #title>
         <span v-if="reportData">{{ reportData.project_name }}</span>
         <ElSkeleton v-else animated :rows="1" class="w-32 inline-block" />
      </template>
      <template #description>
         <div v-if="reportData" class="flex items-center gap-2 text-sm text-gray-500 mt-1">
            <span>项目详细报告</span>
            <span class="w-px h-3 bg-gray-300"></span>
            <span>负责人: {{ reportData.manager }}</span>
            <span class="w-px h-3 bg-gray-300"></span>
            <span>生成时间: {{ new Date().toLocaleDateString() }}</span>
         </div>
         <ElSkeleton v-else animated :rows="1" class="w-64 mt-2" />
      </template>
      <template #end>
         <ElButton type="primary" plain @click="fetchReport" :loading="loading" size="small">
            <template #icon>
               <IconifyIcon icon="lucide:refresh-cw" />
            </template>
            刷新数据
         </ElButton>
      </template>
    </WorkbenchHeader>

    <div class="space-y-4">
      <ElSkeleton :loading="loading" animated>
        <template #template>
           <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 h-[320px]">
              <div class="bg-gray-100 rounded-xl dark:bg-gray-800"></div>
              <div class="bg-gray-100 rounded-xl dark:bg-gray-800"></div>
           </div>
        </template>
        
        <template #default>
           <div v-if="reportData" class="space-y-4">
              <!-- Row 1: Overview & Milestones -->
              <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
                 <!-- Left: Health Overview -->
                 <ReportHeader 
                    class="h-[340px]"
                    :radar-data="reportData.radar_data" 
                    :health-score="reportData.health_score"
                    :health-level="reportData.health_level"
                 />
                 
                 <!-- Right: Milestones -->
                 <div class="h-[340px] rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-[#151515] flex flex-col">
                    <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
                       <h3 class="font-bold text-base flex items-center gap-2">
                          <span class="w-1 h-4 bg-blue-500 rounded-full"></span>
                          里程碑鱼骨图
                       </h3>
                       <span class="text-xs text-gray-400">项目全生命周期节点概览</span>
                    </div>
                    <div class="flex-1 overflow-hidden relative">
                       <MilestoneFishbone :milestones="reportData.milestones" />
                    </div>
                 </div>
              </div>
              
              <!-- Row 2: Charts Area -->
              <DtsTrendChart :trend-data="reportData.dts_trend" />
              
              <!-- Row 3: Detail Cards -->
              <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                 <IterationCard v-if="reportData.iteration" :data="reportData.iteration" />
                 <CodeQualityCard v-if="reportData.code_quality" :data="reportData.code_quality" />
              </div>
           </div>
        </template>
      </ElSkeleton>
    </div>
  </div>
</template>
