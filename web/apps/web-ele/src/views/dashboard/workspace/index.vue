<script lang="ts" setup>
import { onMounted, ref } from 'vue';
import { ElSelect, ElOption, ElSkeleton, ElSkeletonItem } from 'element-plus';
import { WorkbenchHeader } from '@vben/common-ui';
import { useUserStore } from '@vben/stores';
import { preferences } from '@vben/preferences';
import { 
  getCoreMetrics, 
  getFavoriteProjects, 
  getProjectDistribution, 
  getUpcomingMilestones,
  type CodeQualitySummary,
  type IterationSummary,
  type PerformanceSummary,
  type ProjectDistribution,
  type UpcomingMilestone,
  type FavoriteProjectDetail
} from '#/api/dashboard';
import ProjectPie from './components/ProjectPie.vue';
import ProjectBar from './components/ProjectBar.vue';
import MilestoneTable from './components/MilestoneTable.vue';
import MilestoneTimeline from './components/MilestoneTimeline.vue';

const userStore = useUserStore();

// 独立的状态变量
const coreMetrics = ref<{
  code_quality: CodeQualitySummary;
  iteration: IterationSummary;
  performance: PerformanceSummary;
} | null>(null);
const favoriteProjects = ref<FavoriteProjectDetail[]>([]);
const projectDistribution = ref<ProjectDistribution | null>(null);
const upcomingMilestones = ref<UpcomingMilestone[]>([]);

// 独立的 Loading 状态
const loadingCore = ref(true);
const loadingFavorites = ref(true);
const loadingDistribution = ref(true);
const loadingMilestones = ref(true);

// QG 筛选
const selectedQGs = ref<string[]>([]);
const milestoneFiltering = ref(false); // 仅用于筛选时的 loading
const filteredMilestones = ref<UpcomingMilestone[]>([]);

const qgOptions = Array.from({ length: 8 }, (_, i) => ({
  label: `QG${i + 1}`,
  value: `QG${i + 1}`,
}));

async function fetchMilestones(isFilter = false) {
  if (isFilter) {
    milestoneFiltering.value = true;
  } else {
    loadingMilestones.value = true;
  }
  
  try {
    const params = selectedQGs.value.length > 0 ? selectedQGs.value : undefined;
    const data = await getUpcomingMilestones(params);
    
    if (isFilter) {
      filteredMilestones.value = data;
    } else {
      upcomingMilestones.value = data;
      filteredMilestones.value = data;
    }
  } catch (error) {
    console.error('Failed to fetch milestones:', error);
  } finally {
    if (isFilter) {
      milestoneFiltering.value = false;
    } else {
      loadingMilestones.value = false;
    }
  }
}

function onQGChange() {
  fetchMilestones(true);
}

onMounted(() => {
  // 并发请求，互不阻塞
  getCoreMetrics().then(data => {
    coreMetrics.value = data;
    loadingCore.value = false;
  }).catch(e => {
    console.error('Core metrics error', e);
    loadingCore.value = false;
  });

  getFavoriteProjects().then(data => {
    favoriteProjects.value = data;
    loadingFavorites.value = false;
  }).catch(e => {
    console.error('Favorites error', e);
    loadingFavorites.value = false;
  });

  getProjectDistribution().then(data => {
    projectDistribution.value = data;
    loadingDistribution.value = false;
  }).catch(e => {
    console.error('Distribution error', e);
    loadingDistribution.value = false;
  });

  // Initial milestone load
  fetchMilestones(false);
});
</script>

<template>
  <div class="p-3">
    <WorkbenchHeader
      :avatar="userStore.userInfo?.avatar || preferences.app.defaultAvatar"
    >
      <template #title>
        早安, {{ userStore.userInfo?.realName }}, 开始您一天的工作吧！
      </template>
      <template #description>
        今日晴，20℃ - 32℃！这里是您的项目全景概览。
      </template>
    </WorkbenchHeader>

    <div class="space-y-6 mt-5">
      
      <!-- 0. 收藏项目 (骨架屏 + 内容) -->
      <!-- 始终保留占位，避免布局跳动，或者仅在 loading 或有数据时显示 -->
      <!-- 这里策略：如果 loading，显示骨架；如果 loaded 且有数据，显示内容；否则隐藏 -->
      <div v-if="loadingFavorites || favoriteProjects.length > 0" class="space-y-4">
        <div class="flex items-center">
          <div class="p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg mr-3">
             <span class="text-yellow-500 text-xl font-bold">★</span>
          </div>
          <h3 class="text-lg font-bold">我的关注项目</h3>
        </div>
        
        <ElSkeleton :loading="loadingFavorites" animated>
          <template #template>
            <div class="bg-white dark:bg-[#151515] p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800 mb-4">
              <div class="flex justify-between mb-6">
                 <div class="space-y-2">
                    <ElSkeletonItem variant="h3" style="width: 200px" />
                    <ElSkeletonItem variant="text" style="width: 300px" />
                 </div>
                 <div class="flex space-x-6">
                    <ElSkeletonItem variant="text" style="width: 80px" />
                    <ElSkeletonItem variant="text" style="width: 80px" />
                    <ElSkeletonItem variant="text" style="width: 80px" />
                 </div>
              </div>
              <ElSkeletonItem variant="rect" style="height: 60px; width: 100%" />
            </div>
          </template>
          
          <template #default>
            <div class="grid grid-cols-1 gap-6">
              <div 
                v-for="project in favoriteProjects" 
                :key="project.id"
                class="bg-white dark:bg-[#151515] p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800 hover:shadow-md transition-shadow"
              >
                <div class="flex justify-between items-start mb-6">
                  <div>
                    <h4 class="text-xl font-bold text-gray-900 dark:text-white mb-1">{{ project.name }}</h4>
                    <div class="flex space-x-3 text-sm text-gray-500">
                      <span>{{ project.domain }}</span>
                      <span>|</span>
                      <span>{{ project.type }}</span>
                      <span>|</span>
                      <span>负责人: {{ project.managers }}</span>
                    </div>
                  </div>
                  <div class="flex space-x-6 text-right">
                    <div>
                      <div class="text-gray-500 text-xs uppercase">Code Health</div>
                      <div class="text-xl font-bold" :class="project.health_score >= 80 ? 'text-green-500' : 'text-orange-500'">
                        {{ project.health_score }}
                      </div>
                    </div>
                    <div>
                      <div class="text-gray-500 text-xs uppercase">LOC</div>
                      <div class="text-xl font-bold">{{ project.loc.toLocaleString() }}</div>
                    </div>
                    <div>
                      <div class="text-gray-500 text-xs uppercase">Iteration</div>
                      <div class="text-xl font-bold">{{ project.iteration_progress }}%</div>
                      <div class="text-xs text-gray-400">{{ project.current_iteration || 'No Active Iteration' }}</div>
                    </div>
                  </div>
                </div>
                
                <div class="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
                  <MilestoneTimeline :milestones="project.milestones" />
                </div>
              </div>
            </div>
          </template>
        </ElSkeleton>
      </div>

      <!-- 1. 核心指标卡片 (骨架屏 + 内容) -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- 通用骨架模板 -->
        <template v-if="loadingCore">
           <div v-for="i in 3" :key="i" class="bg-white dark:bg-[#151515] p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800">
              <div class="flex items-center mb-6">
                 <ElSkeletonItem variant="circle" style="width: 40px; height: 40px; margin-right: 12px" />
                 <ElSkeletonItem variant="h3" style="width: 100px" />
              </div>
              <div class="space-y-4">
                 <div v-for="j in 4" :key="j" class="flex justify-between">
                    <ElSkeletonItem variant="text" style="width: 80px" />
                    <ElSkeletonItem variant="text" style="width: 40px" />
                 </div>
              </div>
           </div>
        </template>
        
        <template v-else-if="coreMetrics">
           <!-- 代码质量卡片 -->
          <div class="bg-white dark:bg-[#151515] p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800 hover:shadow-md transition-shadow">
            <div class="flex items-center mb-6">
              <div class="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg mr-3">
                <span class="text-blue-500 text-xl font-bold">Code</span>
              </div>
              <h3 class="text-lg font-bold">代码质量总结</h3>
            </div>
            
            <div class="space-y-4">
              <div class="flex justify-between items-center">
                <span class="text-gray-500 dark:text-gray-400">接入项目数</span>
                <span class="font-semibold text-lg">{{ coreMetrics.code_quality.total_projects }}</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-gray-500 dark:text-gray-400">总代码行</span>
                <span class="font-mono font-medium">{{ coreMetrics.code_quality.total_loc.toLocaleString() }}</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-gray-500 dark:text-gray-400">阻断问题</span>
                <span class="font-bold" :class="coreMetrics.code_quality.total_issues > 0 ? 'text-red-500' : 'text-gray-700'">
                  {{ coreMetrics.code_quality.total_issues }}
                </span>
              </div>
               <div class="flex justify-between items-center">
                <span class="text-gray-500 dark:text-gray-400">平均重复率</span>
                <span class="font-medium">{{ coreMetrics.code_quality.avg_duplication_rate }}%</span>
              </div>
               <div class="pt-4 mt-2 border-t border-gray-100 dark:border-gray-800 flex justify-between items-center">
                <span class="text-gray-500 dark:text-gray-400">健康得分</span>
                <span class="text-2xl font-bold text-green-600">{{ coreMetrics.code_quality.health_score }}</span>
              </div>
            </div>
          </div>

          <!-- 迭代健康卡片 -->
          <div class="bg-white dark:bg-[#151515] p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800 hover:shadow-md transition-shadow">
            <div class="flex items-center mb-6">
              <div class="p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg mr-3">
                 <span class="text-purple-500 text-xl font-bold">Iter</span>
              </div>
              <h3 class="text-lg font-bold">迭代健康总结</h3>
            </div>
            
            <div class="space-y-4">
              <div class="flex justify-between items-center">
                <span class="text-gray-500 dark:text-gray-400">进行中迭代</span>
                <span class="font-semibold text-lg">{{ coreMetrics.iteration.active_iterations }}</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-gray-500 dark:text-gray-400">延期迭代</span>
                <span class="font-bold text-lg" :class="coreMetrics.iteration.delayed_iterations > 0 ? 'text-red-500' : 'text-green-500'">
                  {{ coreMetrics.iteration.delayed_iterations }}
                </span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-gray-500 dark:text-gray-400">总需求数</span>
                <span class="font-medium">{{ coreMetrics.iteration.total_req_count }}</span>
              </div>
              <div class="mt-2">
                 <div class="flex justify-between text-sm mb-2">
                    <span class="text-gray-500 dark:text-gray-400">平均进度</span>
                    <span class="font-bold">{{ coreMetrics.iteration.completion_rate }}%</span>
                 </div>
                 <div class="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2">
                    <div 
                      class="bg-purple-500 h-2 rounded-full transition-all duration-500" 
                      :style="{ width: coreMetrics.iteration.completion_rate + '%' }"
                    ></div>
                 </div>
              </div>
            </div>
          </div>

          <!-- 性能监控卡片 -->
          <div class="bg-white dark:bg-[#151515] p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800 hover:shadow-md transition-shadow">
            <div class="flex items-center mb-6">
              <div class="p-2 bg-orange-50 dark:bg-orange-900/20 rounded-lg mr-3">
                 <span class="text-orange-500 text-xl font-bold">Perf</span>
              </div>
              <h3 class="text-lg font-bold">性能监控总结</h3>
            </div>
            
            <div class="space-y-4">
              <div class="flex justify-between items-center">
                <span class="text-gray-500 dark:text-gray-400">监控指标总数</span>
                <span class="font-semibold text-lg">{{ coreMetrics.performance.total_indicators }}</span>
              </div>
               <div class="flex justify-between items-center">
                <span class="text-gray-500 dark:text-gray-400">今日异常指标</span>
                <span class="font-bold text-xl text-red-500">{{ coreMetrics.performance.abnormal_count }}</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-gray-500 dark:text-gray-400">指标覆盖率</span>
                <span class="font-medium">{{ coreMetrics.performance.coverage_rate }}%</span>
              </div>
              <div class="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg text-sm">
                <div class="flex items-center">
                  <span class="w-2 h-2 rounded-full mr-2" :class="coreMetrics.performance.abnormal_count === 0 ? 'bg-green-500' : 'bg-red-500'"></span>
                  <span class="text-gray-600 dark:text-gray-300">
                    系统状态：
                    <span v-if="coreMetrics.performance.abnormal_count === 0" class="text-green-600 dark:text-green-400 font-bold">运行正常</span>
                    <span v-else class="text-red-500 font-bold">存在异常波动</span>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- 2. 图表区域 (骨架屏 + 内容) -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <template v-if="loadingDistribution">
           <div v-for="i in 2" :key="i" class="bg-white dark:bg-[#151515] p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800 h-[350px]">
              <ElSkeletonItem variant="h3" style="width: 150px; margin-bottom: 20px" />
              <div class="flex justify-center items-center h-[250px]">
                 <ElSkeletonItem variant="circle" style="width: 200px; height: 200px" />
              </div>
           </div>
        </template>
        <template v-else-if="projectDistribution">
          <div class="bg-white dark:bg-[#151515] p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800">
            <h3 class="text-lg font-bold mb-4">项目领域分布</h3>
            <ProjectPie :data="projectDistribution.by_domain" title="领域分布" />
          </div>
          <div class="bg-white dark:bg-[#151515] p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800">
            <h3 class="text-lg font-bold mb-4">项目类型分布</h3>
            <ProjectBar :data="projectDistribution.by_type" title="类型分布" />
          </div>
        </template>
      </div>

      <!-- 3. 里程碑提醒 (骨架屏 + 内容) -->
      <div class="bg-white dark:bg-[#151515] p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800">
        <div class="flex items-center justify-between mb-6">
          <div class="flex items-center">
            <div class="p-2 bg-green-50 dark:bg-green-900/20 rounded-lg mr-3">
               <span class="text-green-500 text-xl font-bold">QG</span>
            </div>
            <h3 class="text-lg font-bold">即将到达的里程碑 (未来30天)</h3>
          </div>
          
          <div class="w-64">
            <ElSelect
              v-model="selectedQGs"
              multiple
              placeholder="筛选 QG 节点"
              style="width: 100%"
              collapse-tags
              clearable
              @change="onQGChange"
            >
              <ElOption
                v-for="item in qgOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </ElSelect>
          </div>
        </div>
        
        <ElSkeleton :loading="loadingMilestones" animated :count="3">
          <template #template>
             <div class="flex items-center justify-between py-4 border-b">
                <ElSkeletonItem variant="text" style="width: 30%" />
                <ElSkeletonItem variant="text" style="width: 20%" />
                <ElSkeletonItem variant="text" style="width: 20%" />
                <ElSkeletonItem variant="text" style="width: 10%" />
             </div>
          </template>
          <template #default>
             <div v-if="milestoneFiltering" class="py-10 text-center text-gray-500">
                加载筛选数据中...
             </div>
             <MilestoneTable v-else :milestones="filteredMilestones" />
          </template>
        </ElSkeleton>
      </div>

    </div>
  </div>
</template>
