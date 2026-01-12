<script lang="ts" setup>
import type {
  CodeQualitySummary,
  DtsSummary,
  IterationSummary,
  PerformanceSummary,
  ProjectDistribution,
  UpcomingMilestone,
  FavoriteProjectDetail,
} from '#/api/dashboard';
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import {
  ElSkeleton,
  ElSkeletonItem,
  ElInput,
  ElPagination,
  ElSelect,
  ElOption,
  ElLink,
  ElEmpty
} from 'element-plus';
import MilestoneTable from './MilestoneTable.vue';
import MilestoneTimeline from './MilestoneTimeline.vue';
import ProjectBar from './ProjectBar.vue';
import ProjectPie from './ProjectPie.vue';
import DtsCard from './DtsCard.vue';

const props = defineProps<{
  loadingCore: boolean;
  coreMetrics: {
    code_quality: CodeQualitySummary;
    iteration: IterationSummary;
    performance: PerformanceSummary;
    dts: DtsSummary;
  } | null;
  loadingTimelines: boolean;
  projectTimelines: FavoriteProjectDetail[];
  loadingDistribution: boolean;
  projectDistribution: ProjectDistribution | null;
  loadingMilestones: boolean;
  milestoneFiltering: boolean;
  milestoneTotal: number;
  filteredMilestones: UpcomingMilestone[];
  projectTotal: number;
}>();

const emit = defineEmits<{
  (e: 'search-project', name: string): void;
  (e: 'page-change-project', page: number): void;
  (e: 'page-change-milestone', page: number): void;
  (e: 'filter-milestone', qgs: string[]): void;
}>();

const router = useRouter();
const projectSearchName = ref('');
const projectPage = ref(1);
const projectPageSize = ref(5);
const selectedQGs = ref<string[]>([]);
const milestonePage = ref(1);
const milestonePageSize = ref(5);

const qgOptions = Array.from({ length: 8 }, (_, i) => ({
  label: `QG${i + 1}`,
  value: `QG${i + 1}`,
}));

function onProjectSearch() {
  projectPage.value = 1;
  emit('search-project', projectSearchName.value);
}

function onProjectPageChange(page: number) {
  projectPage.value = page;
  emit('page-change-project', page);
}

function onQGChange() {
  milestonePage.value = 1;
  emit('filter-milestone', selectedQGs.value);
}

function onMilestonePageChange(page: number) {
  milestonePage.value = page;
  emit('page-change-milestone', page);
}

// Navigation helpers
function go(path: string) {
  router.push(path);
}
</script>

<template>
  <div class="space-y-6">
    <!-- 1. 核心指标卡片 -->
    <div class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
      <template v-if="loadingCore">
        <div v-for="i in 4" :key="i" class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
          <div class="mb-6 flex items-center">
            <ElSkeletonItem variant="circle" style="width: 40px; height: 40px; margin-right: 12px" />
            <ElSkeletonItem variant="h3" style="width: 100px" />
          </div>
          <div class="space-y-4">
             <ElSkeletonItem variant="text" />
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

        <!-- 性能监控 -->
        <div class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-[#151515]">
          <div class="mb-6 flex items-center justify-between">
            <div class="flex items-center">
              <div class="mr-3 rounded-lg bg-orange-50 p-2 dark:bg-orange-900/20">
                <span class="text-xl font-bold text-orange-500">Perf</span>
              </div>
              <h3 class="text-lg font-bold">性能监控</h3>
            </div>
            <ElLink type="primary" :underline="false" @click="go('/performance/monitor')">更多 ></ElLink>
          </div>
          <div class="space-y-4">
             <div class="flex justify-between">
                <span class="text-gray-500">异常指标</span>
                <span class="font-bold text-red-500">{{ coreMetrics.performance.abnormal_count }}</span>
             </div>
             <div class="flex justify-between">
                <span class="text-gray-500">覆盖率</span>
                <span class="font-bold">{{ coreMetrics.performance.coverage_rate }}%</span>
             </div>
             <div class="bg-gray-50 dark:bg-gray-800 p-2 rounded text-sm flex items-center gap-2 mt-2">
                <div class="w-2 h-2 rounded-full" :class="coreMetrics.performance.abnormal_count === 0 ? 'bg-green-500' : 'bg-red-500'"></div>
                <span>{{ coreMetrics.performance.abnormal_count === 0 ? '系统运行正常' : '存在异常波动' }}</span>
             </div>
          </div>
        </div>

        <!-- DTS 监控 -->
        <DtsCard :data="coreMetrics.dts" />
      </template>
    </div>

    <!-- 2. 项目进度列表 -->
    <div class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
       <div class="mb-6 flex items-center justify-between">
         <div class="flex items-center">
            <div class="mr-3 rounded-lg bg-yellow-50 p-2 dark:bg-yellow-900/20">
               <span class="text-xl font-bold text-yellow-500">★</span>
            </div>
            <h3 class="text-lg font-bold">近期活跃项目进度</h3>
         </div>
         <div class="w-64">
            <ElInput
               v-model="projectSearchName"
               placeholder="搜索项目名称 (回车确认)"
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
             <div v-else class="py-10 text-center">
                <ElEmpty description="暂无项目数据" />
             </div>
          </template>
       </ElSkeleton>
    </div>

    <!-- 3. 图表区域 -->
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
       <template v-if="loadingDistribution">
          <ElSkeleton :count="2" class="h-[350px]" />
       </template>
       <template v-else-if="projectDistribution">
          <div class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
             <h3 class="mb-4 text-lg font-bold">项目领域分布</h3>
             <ProjectPie :data="projectDistribution.by_domain" title="领域分布" />
          </div>
          <div class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
             <h3 class="mb-4 text-lg font-bold">项目类型分布</h3>
             <ProjectBar :data="projectDistribution.by_type" title="类型分布" />
          </div>
       </template>
    </div>

    <!-- 4. 里程碑提醒 -->
    <div class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
       <div class="mb-6 flex items-center justify-between">
          <div class="flex items-center">
             <div class="mr-3 rounded-lg bg-green-50 p-2 dark:bg-green-900/20">
                <span class="text-xl font-bold text-green-500">QG</span>
             </div>
             <h3 class="text-lg font-bold">即将到达的里程碑 (未来30天)</h3>
          </div>
          <div class="flex gap-4 items-center">
             <div class="w-64">
                <ElSelect
                   v-model="selectedQGs"
                   multiple
                   placeholder="筛选 QG 节点"
                   collapse-tags
                   clearable
                   @change="onQGChange"
                >
                   <ElOption v-for="item in qgOptions" :key="item.value" :label="item.label" :value="item.value" />
                </ElSelect>
             </div>
             <ElLink type="primary" :underline="false" @click="go('/project-manager/milestone')">更多 ></ElLink>
          </div>
       </div>

       <ElSkeleton :loading="loadingMilestones" animated>
          <template #default>
             <div v-if="milestoneFiltering" class="py-10 text-center text-gray-500">加载中...</div>
             <div v-else>
                <MilestoneTable :milestones="filteredMilestones" />
                <div class="flex justify-end mt-4" v-if="milestoneTotal > milestonePageSize">
                   <ElPagination
                      v-model:current-page="milestonePage"
                      :page-size="milestonePageSize"
                      :total="milestoneTotal"
                      layout="prev, pager, next"
                      background
                      @current-change="onMilestonePageChange"
                   />
                </div>
             </div>
          </template>
       </ElSkeleton>
    </div>
  </div>
</template>
