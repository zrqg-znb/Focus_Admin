<script lang="ts" setup>
import type {
  CodeQualitySummary,
  DtsSummary,
  IterationSummary,
  FavoriteProjectDetail,
} from '#/api/dashboard';
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  ElSkeleton,
  ElSkeletonItem,
  ElInput,
  ElPagination,
  ElLink,
  ElEmpty,
  ElButton
} from 'element-plus';
import { IconifyIcon } from '@vben/icons';
import MilestoneTimeline from './MilestoneTimeline.vue';
import DtsCard from './DtsCard.vue';

const props = defineProps<{
  loadingCore: boolean;
  coreMetrics: {
    code_quality: CodeQualitySummary;
    iteration: IterationSummary;
    // performance excluded in favorite view
    dts: DtsSummary;
  } | null;
  loadingTimelines: boolean;
  projectTimelines: FavoriteProjectDetail[];
  projectTotal: number;
}>();

const emit = defineEmits<{
  (e: 'search-project', name: string): void;
  (e: 'page-change-project', page: number): void;
}>();

const router = useRouter();
const projectSearchName = ref('');
const projectPage = ref(1);
const projectPageSize = ref(5);

function onProjectSearch() {
  projectPage.value = 1;
  emit('search-project', projectSearchName.value);
}

function onProjectPageChange(page: number) {
  projectPage.value = page;
  emit('page-change-project', page);
}

// Navigation helpers
function go(path: string) {
  router.push(path);
}

function goProjectConfig() {
  router.push('/project-manager/project');
}
</script>

<template>
  <div class="space-y-6">
    <!-- 1. 核心指标卡片 (简化版，无性能监控) -->
    <div class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
      <template v-if="loadingCore">
        <div v-for="i in 3" :key="i" class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
           <ElSkeletonItem variant="h3" style="width: 100px; margin-bottom: 20px" />
           <div class="space-y-4">
              <ElSkeletonItem variant="text" />
              <ElSkeletonItem variant="text" />
           </div>
        </div>
      </template>

      <template v-else-if="coreMetrics">
        <!-- 代码质量 -->
        <div class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-[#151515]">
          <div class="mb-6 flex items-center justify-between">
            <div class="flex items-center">
              <div class="mr-3 rounded-lg bg-blue-50 p-2 dark:bg-blue-900/20">
                <span class="text-xl font-bold text-blue-500">Code</span>
              </div>
              <h3 class="text-lg font-bold">代码质量</h3>
            </div>
            <ElLink type="primary" :underline="false" @click="go('/project-manager/code-quality')">更多 ></ElLink>
          </div>
          <div class="space-y-4">
             <div class="flex justify-between">
                <span class="text-gray-500">接入项目</span>
                <span class="font-bold">{{ coreMetrics.code_quality.total_projects }}</span>
             </div>
             <div class="flex justify-between">
                <span class="text-gray-500">阻断问题</span>
                <span class="font-bold text-red-500">{{ coreMetrics.code_quality.total_issues }}</span>
             </div>
             <div class="flex justify-between border-t pt-2 mt-2">
                <span class="text-gray-500">健康得分</span>
                <span class="font-bold text-green-600 text-lg">{{ coreMetrics.code_quality.health_score }}</span>
             </div>
          </div>
        </div>

        <!-- 迭代健康 -->
        <div class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-[#151515]">
          <div class="mb-6 flex items-center justify-between">
            <div class="flex items-center">
              <div class="mr-3 rounded-lg bg-purple-50 p-2 dark:bg-purple-900/20">
                <span class="text-xl font-bold text-purple-500">Iter</span>
              </div>
              <h3 class="text-lg font-bold">迭代健康</h3>
            </div>
            <ElLink type="primary" :underline="false" @click="go('/project-manager/iteration')">更多 ></ElLink>
          </div>
          <div class="space-y-4">
             <div class="flex justify-between">
                <span class="text-gray-500">进行中</span>
                <span class="font-bold">{{ coreMetrics.iteration.active_iterations }}</span>
             </div>
             <div class="flex justify-between">
                <span class="text-gray-500">延期</span>
                <span class="font-bold text-red-500">{{ coreMetrics.iteration.delayed_iterations }}</span>
             </div>
             <div class="mt-2">
                <div class="flex justify-between text-sm mb-1">
                   <span class="text-gray-500">进度</span>
                   <span>{{ coreMetrics.iteration.completion_rate }}%</span>
                </div>
                <div class="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                   <div class="h-full bg-purple-500" :style="{ width: `${coreMetrics.iteration.completion_rate}%` }"></div>
                </div>
             </div>
          </div>
        </div>

        <!-- DTS 监控 -->
        <DtsCard :data="coreMetrics.dts" />
      </template>
    </div>

    <!-- 2. 关注项目列表 -->
    <div class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
       <div class="mb-6 flex items-center justify-between">
         <div class="flex items-center">
            <div class="mr-3 rounded-lg bg-yellow-50 p-2 dark:bg-yellow-900/20">
               <span class="text-xl font-bold text-yellow-500">★</span>
            </div>
            <h3 class="text-lg font-bold">我的关注项目进度</h3>
         </div>
         <div class="w-64">
            <ElInput
               v-model="projectSearchName"
               placeholder="搜索关注项目"
               clearable
               @change="onProjectSearch"
               @clear="onProjectSearch"
            >
               <template #prefix>
                  <IconifyIcon icon="lucide:search" />
               </template>
            </ElInput>
         </div>
       </div>

       <ElSkeleton :loading="loadingTimelines" animated>
          <template #default>
             <div v-if="projectTimelines.length > 0" class="space-y-8">
                <div v-for="project in projectTimelines" :key="project.id" class="border-b border-gray-100 pb-8 last:border-0 last:pb-0 dark:border-gray-800">
                   <div class="mb-4 flex items-start justify-between">
                      <div>
                         <h4 class="mb-1 text-lg font-bold">{{ project.name }}</h4>
                         <div class="flex space-x-3 text-sm text-gray-500">
                            <span>{{ project.domain }}</span>|
                            <span>{{ project.type }}</span>|
                            <span>负责人: {{ project.managers }}</span>
                         </div>
                      </div>
                      <!-- Metrics badges -->
                      <div class="flex space-x-6 text-right">
                         <div class="text-center">
                            <div class="text-xs uppercase text-gray-500">Health</div>
                            <div class="font-bold" :class="project.health_score >= 80 ? 'text-green-500' : 'text-orange-500'">{{ project.health_score }}</div>
                         </div>
                         <div class="text-center">
                            <div class="text-xs uppercase text-gray-500">LOC</div>
                            <div class="font-bold">{{ project.loc.toLocaleString() }}</div>
                         </div>
                         <div class="text-center">
                            <div class="text-xs uppercase text-gray-500">Iter</div>
                            <div class="font-bold">{{ project.iteration_progress }}%</div>
                         </div>
                      </div>
                   </div>
                   <div class="pl-2">
                      <MilestoneTimeline :milestones="project.milestones" />
                   </div>
                </div>
                <div class="flex justify-end mt-6" v-if="projectTotal > projectPageSize">
                   <ElPagination
                      v-model:current-page="projectPage"
                      :page-size="projectPageSize"
                      :total="projectTotal"
                      layout="prev, pager, next"
                      background
                      @current-change="onProjectPageChange"
                   />
                </div>
             </div>
             <!-- Empty state for favorites -->
             <div v-else class="py-16 text-center flex flex-col items-center">
                <ElEmpty description="暂无关注项目" />
                <div class="mt-4">
                   <p class="text-gray-500 mb-4">您还没有关注任何项目，去项目列表看看吧</p>
                   <ElButton type="primary" @click="goProjectConfig">去配置关注项目</ElButton>
                </div>
             </div>
          </template>
       </ElSkeleton>
    </div>

    <!-- 3. 图表区域 (Hidden in Favorites) -->
    <!-- 4. 里程碑提醒 (Hidden in Favorites) -->
  </div>
</template>
