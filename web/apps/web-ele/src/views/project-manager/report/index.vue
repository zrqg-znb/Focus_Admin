<script lang="ts" setup>
import type { ProjectReport } from '#/api/project-manager/report';
import { onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Page, WorkbenchHeader } from '@vben/common-ui';
import { ElSkeleton, ElButton, ElScrollbar } from 'element-plus';
import { IconifyIcon } from '@vben/icons';
import { getProjectReportApi } from '#/api/project-manager/report';

import ReportHeader from './ReportHeader.vue';
import MilestoneFishbone from './MilestoneFishbone.vue';
import DtsTrendChart from './DtsTrendChart.vue';
import IterationCard from './IterationCard.vue';
import CodeQualityCard from './CodeQualityCard.vue';
import ProjectSidebar from './ProjectSidebar.vue';

defineOptions({ name: 'ProjectDetailReport' });

const route = useRoute();
const router = useRouter();
const loading = ref(true);
const reportData = ref<ProjectReport | null>(null);
const iterationExpanded = ref(false);
const qualityExpanded = ref(false);

// Get projectId from route
const currentProjectId = ref(route.params.id as string);

async function fetchReport() {
  if (!currentProjectId.value) return;

  try {
    loading.value = true;
    reportData.value = await getProjectReportApi(currentProjectId.value);
    iterationExpanded.value = false;
    qualityExpanded.value = false;
  } catch (error) {
    console.error('Failed to fetch report', error);
  } finally {
    loading.value = false;
  }
}

function handleProjectSelect(id: string) {
  if (id === currentProjectId.value) return;
  router.push(`/project-manager/report/${id}`);
}

// Watch route changes to update data
watch(
  () => route.params.id,
  (newId) => {
    if (newId && typeof newId === 'string') {
      currentProjectId.value = newId;
      iterationExpanded.value = false;
      qualityExpanded.value = false;
      fetchReport();
    }
  }
);

function toggleIteration(expanded: boolean) {
  iterationExpanded.value = expanded;
}

function toggleQuality(expanded: boolean) {
  qualityExpanded.value = expanded;
}

onMounted(() => {
  if (currentProjectId.value) {
    fetchReport();
  }
});
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full w-full bg-gray-50/50 dark:bg-black overflow-hidden rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
      <!-- Sidebar -->
      <div class="w-[280px] flex-shrink-0 h-full border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-[#151515]">
         <ProjectSidebar :current-id="currentProjectId" @select="handleProjectSelect" />
      </div>

      <!-- Main Content -->
      <div class="flex-1 h-full overflow-hidden flex flex-col bg-white/50 dark:bg-[#151515]/50">
         <ElScrollbar>
            <div class="p-4">
              <WorkbenchHeader
                avatar="https://unpkg.com/@vbenjs/static-source@0.1.7/source/logo-v1.webp"
                class="mb-4 shadow-sm border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-[#151515]"
              >
                <template #title>
                   <div class="flex items-center gap-3">
                      <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 border border-blue-100 shadow-sm dark:bg-blue-900/20 dark:border-blue-800">
                         <IconifyIcon icon="lucide:file-bar-chart-2" class="text-xl text-blue-600 dark:text-blue-400" />
                      </div>
                      <div class="flex flex-col">
                         <h1 class="text-lg font-bold text-gray-900 dark:text-white leading-tight">项目详细报告</h1>
                         <span class="text-[10px] text-gray-400 font-normal uppercase tracking-wider">Project Analysis & Statistics</span>
                      </div>
                   </div>
                </template>
                <template #description>
                   <div v-if="reportData" class="flex items-center gap-2 text-sm text-gray-500 mt-1 ml-14">
                      <span class="font-medium text-gray-700 dark:text-gray-300">{{ reportData.project_name }}</span>
                      <span class="w-px h-3 bg-gray-300"></span>
                      <span>负责人: {{ reportData.manager }}</span>
                      <span class="w-px h-3 bg-gray-300"></span>
                      <span>生成时间: {{ new Date().toLocaleDateString() }}</span>
                   </div>
                   <ElSkeleton v-else animated :rows="1" class="w-64 mt-2 ml-14" />
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
                                 <MilestoneFishbone 
                                    :milestones="reportData.milestones" 
                                    :project-id="reportData.project_id"
                                    :project-name="reportData.project_name"
                                    @refresh="fetchReport"
                                 />
                              </div>
                           </div>
                        </div>

                      <!-- Row 2: Charts Area -->
                      <DtsTrendChart
                        v-if="reportData.dts_summary"
                        :trend-data="reportData.dts_trend"
                        :di-trend="reportData.dts_team_di_trend"
                      />

                      <!-- Row 3: Detail Cards -->
                      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                         <IterationCard
                           v-if="reportData.iteration"
                           :data="reportData.iteration"
                           :detail="reportData.iteration_detail"
                           :expanded="iterationExpanded"
                           @toggle="toggleIteration"
                         />
                         <CodeQualityCard
                           v-if="reportData.code_quality"
                           :data="reportData.code_quality"
                           :details="reportData.code_quality_details"
                           :expanded="qualityExpanded"
                           @toggle="toggleQuality"
                         />
                      </div>
                   </div>
                </template>
              </ElSkeleton>
              </div>
            </div>
         </ElScrollbar>
      </div>
    </div>
  </Page>
</template>
