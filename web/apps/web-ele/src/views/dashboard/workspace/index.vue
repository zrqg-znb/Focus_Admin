<script lang="ts" setup>
import type {
  CodeQualitySummary,
  FavoriteProjectDetail,
  IterationSummary,
  PerformanceSummary,
  ProjectDistribution,
  UpcomingMilestone,
} from '#/api/dashboard';

import { onMounted, ref } from 'vue';

import { WorkbenchHeader } from '@vben/common-ui';
import { preferences } from '@vben/preferences';
import { useUserStore } from '@vben/stores';

import {
  ElOption,
  ElRadioButton,
  ElRadioGroup,
  ElSelect,
  ElSkeleton,
  ElSkeletonItem,
  ElInput,
  ElPagination
} from 'element-plus';

import {
  getCoreMetrics,
  getProjectDistribution,
  getProjectTimelines,
  getUpcomingMilestones,
} from '#/api/dashboard';

import MilestoneTable from './components/MilestoneTable.vue';
import MilestoneTimeline from './components/MilestoneTimeline.vue';
import ProjectBar from './components/ProjectBar.vue';
import ProjectPie from './components/ProjectPie.vue';

const userStore = useUserStore();

// View Scope
const viewScope = ref<'all' | 'favorites'>('all');

// 独立的状态变量
const coreMetrics = ref<null | {
  code_quality: CodeQualitySummary;
  iteration: IterationSummary;
  performance: PerformanceSummary;
}>(null);
const projectTimelines = ref<FavoriteProjectDetail[]>([]);
const projectDistribution = ref<null | ProjectDistribution>(null);
const upcomingMilestones = ref<UpcomingMilestone[]>([]);

// Pagination & Search State
const projectPage = ref(1);
const projectPageSize = ref(5);
const projectTotal = ref(0);
const projectSearchName = ref('');

const milestonePage = ref(1);
const milestonePageSize = ref(5);
const milestoneTotal = ref(0);

// 独立的 Loading 状态
const loadingCore = ref(true);
const loadingTimelines = ref(true);
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

async function loadData() {
  loadingCore.value = true;
  loadingTimelines.value = true;
  loadingDistribution.value = true;
  loadingMilestones.value = true;

  const scope = viewScope.value;

  // 并发请求，互不阻塞
  getCoreMetrics(scope)
    .then((data) => {
      coreMetrics.value = data;
      loadingCore.value = false;
    })
    .catch((error) => {
      console.error('Core metrics error', error);
      loadingCore.value = false;
    });

  // Timelines (Replacing Favorites)
  fetchProjectTimelines();

  getProjectDistribution(scope)
    .then((data) => {
      projectDistribution.value = data;
      loadingDistribution.value = false;
    })
    .catch((error) => {
      console.error('Distribution error', error);
      loadingDistribution.value = false;
    });

  // Milestones
  fetchMilestones(false);
}

function fetchProjectTimelines() {
  loadingTimelines.value = true;
  getProjectTimelines(viewScope.value, projectPage.value, projectPageSize.value, projectSearchName.value)
    .then((data) => {
      projectTimelines.value = data.items;
      projectTotal.value = data.total;
      loadingTimelines.value = false;
    })
    .catch((error) => {
      console.error('Timelines error', error);
      loadingTimelines.value = false;
    });
}

function onProjectPageChange(page: number) {
  projectPage.value = page;
  fetchProjectTimelines();
}

function onProjectSearch() {
  projectPage.value = 1; // Reset to first page on search
  fetchProjectTimelines();
}

async function fetchMilestones(isFilter = false) {
  if (isFilter) {
    milestoneFiltering.value = true;
  }

  try {
    const params = selectedQGs.value.length > 0 ? selectedQGs.value : undefined;
    const data = await getUpcomingMilestones(params, viewScope.value, milestonePage.value, milestonePageSize.value);

    // Update total
    milestoneTotal.value = data.total;

    if (isFilter) {
      filteredMilestones.value = data.items;
    } else {
      upcomingMilestones.value = data.items;
      filteredMilestones.value = data.items;
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

function onMilestonePageChange(page: number) {
  milestonePage.value = page;
  fetchMilestones(true); // Treat as filter refresh to show loading state if needed, or separate logic
}

function onQGChange() {
  milestonePage.value = 1; // Reset to first page
  fetchMilestones(true);
}

function onViewScopeChange() {
  // Reset pages
  projectPage.value = 1;
  milestonePage.value = 1;
  projectSearchName.value = '';
  loadData();
}

onMounted(() => {
  loadData();
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

      <!-- Right Side View Switcher -->
      <template #end>
        <div class="flex h-full items-center">
          <ElRadioGroup v-model="viewScope" @change="onViewScopeChange">
            <ElRadioButton label="all">
              <div class="flex items-center gap-1">
                <IconifyIcon icon="lucide:layout-grid" />
                <span>全量项目</span>
              </div>
            </ElRadioButton>
            <ElRadioButton label="favorites">
              <div class="flex items-center gap-1">
                <IconifyIcon icon="lucide:star" />
                <span>关注项目</span>
              </div>
            </ElRadioButton>
          </ElRadioGroup>
        </div>
      </template>
    </WorkbenchHeader>

    <div class="mt-5 space-y-6">
      <!-- 1. 核心指标卡片 (骨架屏 + 内容) -->
      <div class="grid grid-cols-1 gap-6 md:grid-cols-3">
        <!-- 通用骨架模板 -->
        <template v-if="loadingCore">
          <div
            v-for="i in 3"
            :key="i"
            class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]"
          >
            <div class="mb-6 flex items-center">
              <ElSkeletonItem
                variant="circle"
                style="width: 40px; height: 40px; margin-right: 12px"
              />
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
          <div
            class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-[#151515]"
          >
            <div class="mb-6 flex items-center">
              <div class="mr-3 rounded-lg bg-blue-50 p-2 dark:bg-blue-900/20">
                <span class="text-xl font-bold text-blue-500">Code</span>
              </div>
              <h3 class="text-lg font-bold">代码质量总结</h3>
            </div>

            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <span class="text-gray-500 dark:text-gray-400">接入项目数</span>
                <span class="text-lg font-semibold">{{
                  coreMetrics.code_quality.total_projects
                }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-gray-500 dark:text-gray-400">总代码行</span>
                <span class="font-mono font-medium">{{
                  coreMetrics.code_quality.total_loc.toLocaleString()
                }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-gray-500 dark:text-gray-400">阻断问题</span>
                <span
                  class="font-bold"
                  :class="
                    coreMetrics.code_quality.total_issues > 0
                      ? 'text-red-500'
                      : 'text-gray-700'
                  "
                >
                  {{ coreMetrics.code_quality.total_issues }}
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-gray-500 dark:text-gray-400">平均重复率</span>
                <span class="font-medium"
                  >{{ coreMetrics.code_quality.avg_duplication_rate }}%</span
                >
              </div>
              <div
                class="mt-2 flex items-center justify-between border-t border-gray-100 pt-4 dark:border-gray-800"
              >
                <span class="text-gray-500 dark:text-gray-400">健康得分</span>
                <span class="text-2xl font-bold text-green-600">{{
                  coreMetrics.code_quality.health_score
                }}</span>
              </div>
            </div>
          </div>

          <!-- 迭代健康卡片 -->
          <div
            class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-[#151515]"
          >
            <div class="mb-6 flex items-center">
              <div
                class="mr-3 rounded-lg bg-purple-50 p-2 dark:bg-purple-900/20"
              >
                <span class="text-xl font-bold text-purple-500">Iter</span>
              </div>
              <h3 class="text-lg font-bold">迭代健康总结</h3>
            </div>

            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <span class="text-gray-500 dark:text-gray-400">进行中迭代</span>
                <span class="text-lg font-semibold">{{
                  coreMetrics.iteration.active_iterations
                }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-gray-500 dark:text-gray-400">延期迭代</span>
                <span
                  class="text-lg font-bold"
                  :class="
                    coreMetrics.iteration.delayed_iterations > 0
                      ? 'text-red-500'
                      : 'text-green-500'
                  "
                >
                  {{ coreMetrics.iteration.delayed_iterations }}
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-gray-500 dark:text-gray-400">总需求数</span>
                <span class="font-medium">{{
                  coreMetrics.iteration.total_req_count
                }}</span>
              </div>
              <div class="mt-2">
                <div class="mb-2 flex justify-between text-sm">
                  <span class="text-gray-500 dark:text-gray-400">平均进度</span>
                  <span class="font-bold"
                    >{{ coreMetrics.iteration.completion_rate }}%</span
                  >
                </div>
                <div
                  class="h-2 w-full rounded-full bg-gray-100 dark:bg-gray-700"
                >
                  <div
                    class="h-2 rounded-full bg-purple-500 transition-all duration-500"
                    :style="{
                      width: `${coreMetrics.iteration.completion_rate}%`,
                    }"
                  ></div>
                </div>
              </div>
            </div>
          </div>

          <!-- 性能监控卡片 -->
          <div
            class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-[#151515]"
          >
            <div class="mb-6 flex items-center">
              <div
                class="mr-3 rounded-lg bg-orange-50 p-2 dark:bg-orange-900/20"
              >
                <span class="text-xl font-bold text-orange-500">Perf</span>
              </div>
              <h3 class="text-lg font-bold">性能监控总结</h3>
            </div>

            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <span class="text-gray-500 dark:text-gray-400"
                  >监控指标总数</span
                >
                <span class="text-lg font-semibold">{{
                  coreMetrics.performance.total_indicators
                }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-gray-500 dark:text-gray-400"
                  >今日异常指标</span
                >
                <span class="text-xl font-bold text-red-500">{{
                  coreMetrics.performance.abnormal_count
                }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-gray-500 dark:text-gray-400">指标覆盖率</span>
                <span class="font-medium"
                  >{{ coreMetrics.performance.coverage_rate }}%</span
                >
              </div>
              <div
                class="mt-4 rounded-lg bg-gray-50 p-4 text-sm dark:bg-gray-800"
              >
                <div class="flex items-center">
                  <span
                    class="mr-2 h-2 w-2 rounded-full"
                    :class="
                      coreMetrics.performance.abnormal_count === 0
                        ? 'bg-green-500'
                        : 'bg-red-500'
                    "
                  ></span>
                  <span class="text-gray-600 dark:text-gray-300">
                    系统状态：
                    <span
                      v-if="coreMetrics.performance.abnormal_count === 0"
                      class="font-bold text-green-600 dark:text-green-400"
                      >运行正常</span
                    >
                    <span v-else class="font-bold text-red-500"
                      >存在异常波动</span
                    >
                  </span>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- 2. 项目里程碑进度 (合并到一个大卡片) -->
      <!-- 仅在关注视图或有数据时显示 -->
      <div
        v-if="loadingTimelines || projectTimelines.length > 0"
        class="space-y-4"
      >
        <div
          class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]"
        >
          <div class="mb-6 flex items-center justify-between">
            <div class="flex items-center">
              <div
                class="mr-3 rounded-lg bg-yellow-50 p-2 dark:bg-yellow-900/20"
              >
                <span class="text-xl font-bold text-yellow-500">★</span>
              </div>
              <h3 class="text-lg font-bold">
                {{
                  viewScope === 'favorites'
                    ? '我的关注项目进度'
                    : '近期活跃项目进度'
                }}
              </h3>
            </div>

            <!-- Search Input -->
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
            <template #template>
              <div v-for="i in 3" :key="i" class="mb-8 last:mb-0">
                <div class="mb-4 flex justify-between">
                  <div class="space-y-2">
                    <ElSkeletonItem variant="h3" style="width: 200px" />
                    <ElSkeletonItem variant="text" style="width: 300px" />
                  </div>
                </div>
                <ElSkeletonItem
                  variant="rect"
                  style="height: 60px; width: 100%"
                />
              </div>
            </template>

            <template #default>
              <div class="space-y-8">
                <div
                  v-for="(project, index) in projectTimelines"
                  :key="project.id"
                  class="relative border-b border-gray-100 pb-8 last:border-0 last:pb-0 dark:border-gray-800"
                >
                  <div class="mb-4 flex items-start justify-between">
                    <div>
                      <h4
                        class="mb-1 text-lg font-bold text-gray-900 dark:text-white"
                      >
                        {{ project.name }}
                      </h4>
                      <div class="flex space-x-3 text-sm text-gray-500">
                        <span>{{ project.domain }}</span>
                        <span>|</span>
                        <span>{{ project.type }}</span>
                        <span>|</span>
                        <span>负责人: {{ project.managers }}</span>
                      </div>
                    </div>
                    <div class="flex space-x-6 text-right">
                      <div class="text-center">
                        <div class="text-xs uppercase text-gray-500">
                          Code Health
                        </div>
                        <div
                          class="font-bold"
                          :class="
                            project.health_score >= 80
                              ? 'text-green-500'
                              : 'text-orange-500'
                          "
                        >
                          {{ project.health_score }}
                        </div>
                      </div>
                      <div class="text-center">
                        <div class="text-xs uppercase text-gray-500">LOC</div>
                        <div class="font-bold">
                          {{ project.loc.toLocaleString() }}
                        </div>
                      </div>
                      <div class="text-center">
                        <div class="text-xs uppercase text-gray-500">
                          Iteration
                        </div>
                        <div class="font-bold">
                          {{ project.iteration_progress }}%
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 里程碑时间轴 (绳结) -->
                  <div class="pl-2">
                    <MilestoneTimeline :milestones="project.milestones" />
                  </div>
                </div>
              </div>

              <!-- Pagination -->
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
            </template>
          </ElSkeleton>
        </div>
      </div>

      <!-- 3. 图表区域 (骨架屏 + 内容) -->
      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <template v-if="loadingDistribution">
          <div
            v-for="i in 2"
            :key="i"
            class="h-[350px] rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]"
          >
            <ElSkeletonItem
              variant="h3"
              style="width: 150px; margin-bottom: 20px"
            />
            <div class="flex h-[250px] items-center justify-center">
              <ElSkeletonItem
                variant="circle"
                style="width: 200px; height: 200px"
              />
            </div>
          </div>
        </template>
        <template v-else-if="projectDistribution">
          <div
            class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]"
          >
            <h3 class="mb-4 text-lg font-bold">项目领域分布</h3>
            <ProjectPie
              :data="projectDistribution.by_domain"
              title="领域分布"
            />
          </div>
          <div
            class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]"
          >
            <h3 class="mb-4 text-lg font-bold">项目类型分布</h3>
            <ProjectBar :data="projectDistribution.by_type" title="类型分布" />
          </div>
        </template>
      </div>

      <!-- 4. 里程碑提醒 (骨架屏 + 内容) -->
      <div
        class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]"
      >
        <div class="mb-6 flex items-center justify-between">
          <div class="flex items-center">
            <div class="mr-3 rounded-lg bg-green-50 p-2 dark:bg-green-900/20">
              <span class="text-xl font-bold text-green-500">QG</span>
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
            <div class="flex items-center justify-between border-b py-4">
              <ElSkeletonItem variant="text" style="width: 30%" />
              <ElSkeletonItem variant="text" style="width: 20%" />
              <ElSkeletonItem variant="text" style="width: 20%" />
              <ElSkeletonItem variant="text" style="width: 10%" />
            </div>
          </template>
          <template #default>
            <div
              v-if="milestoneFiltering"
              class="py-10 text-center text-gray-500"
            >
              加载筛选数据中...
            </div>
            <div v-else>
               <MilestoneTable :milestones="filteredMilestones" />
               <!-- Pagination -->
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
  </div>
</template>
