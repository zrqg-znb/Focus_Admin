<script lang="ts" setup>
import type {
  CodeQualitySummary,
  DtsSummary,
  IterationSummary,
  PerformanceSummary,
  ProjectDistribution,
  UpcomingMilestone,
} from '#/api/dashboard';

import { ref } from 'vue';
import { useRouter } from 'vue-router';

import {
  ElLink,
  ElOption,
  ElPagination,
  ElSelect,
  ElSkeleton,
  ElSkeletonItem,
} from 'element-plus';

import DtsCard from './DtsCard.vue';
import MilestoneTable from './MilestoneTable.vue';
import ProjectBar from './ProjectBar.vue';
import ProjectPie from './ProjectPie.vue';
import QGRiskCard from './QGRiskCard.vue';
import RequirementWorkspacePanel from './RequirementWorkspacePanel.vue';

defineProps<{
  coreMetrics: null | {
    code_quality: CodeQualitySummary;
    dts: DtsSummary;
    iteration: IterationSummary;
    performance: PerformanceSummary;
  };
  filteredMilestones: UpcomingMilestone[];
  loadingCore: boolean;
  loadingDistribution: boolean;
  loadingMilestones: boolean;
  milestoneFiltering: boolean;
  milestoneTotal: number;
  projectDistribution: null | ProjectDistribution;
}>();

const emit = defineEmits<{
  (e: 'filterMilestone', qgs: string[]): void;
  (e: 'pageChangeMilestone', page: number): void;
}>();

const router = useRouter();
const selectedQGs = ref<string[]>([]);
const milestonePage = ref(1);
const milestonePageSize = ref(5);

const qgOptions = Array.from({ length: 8 }, (_, i) => ({
  label: `QG${i + 1}`,
  value: `QG${i + 1}`,
}));

function onQGChange() {
  milestonePage.value = 1;
  emit('filterMilestone', selectedQGs.value);
}

function onMilestonePageChange(page: number) {
  milestonePage.value = page;
  emit('pageChangeMilestone', page);
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
        <div
          v-for="i in 4"
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
            <ElSkeletonItem variant="text" />
            <ElSkeletonItem variant="text" />
            <ElSkeletonItem variant="text" />
          </div>
        </div>
      </template>

      <template v-else-if="coreMetrics">
        <!-- 代码质量 -->
        <div
          class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-[#151515]"
        >
          <div class="mb-6 flex items-center justify-between">
            <div class="flex items-center">
              <div class="mr-3 rounded-lg bg-blue-50 p-2 dark:bg-blue-900/20">
                <span class="text-xl font-bold text-blue-500">Code</span>
              </div>
              <h3 class="text-lg font-bold">代码质量</h3>
            </div>
            <ElLink
              type="primary"
              :underline="false"
              @click="go('/project-manager/code-quality')"
            >
              更多 >
            </ElLink>
          </div>
          <div class="space-y-4">
            <div class="flex justify-between">
              <span class="text-gray-500">接入项目</span>
              <span class="font-bold">{{
                coreMetrics.code_quality.total_projects
              }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-500">阻断问题</span>
              <span class="font-bold text-red-500">{{
                coreMetrics.code_quality.total_issues
              }}</span>
            </div>
            <div class="mt-2 flex justify-between border-t pt-2">
              <span class="text-gray-500">健康得分</span>
              <span class="text-lg font-bold text-green-600">{{
                coreMetrics.code_quality.health_score
              }}</span>
            </div>
          </div>
        </div>

        <!-- 迭代健康 -->
        <div
          class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-[#151515]"
        >
          <div class="mb-6 flex items-center justify-between">
            <div class="flex items-center">
              <div
                class="mr-3 rounded-lg bg-purple-50 p-2 dark:bg-purple-900/20"
              >
                <span class="text-xl font-bold text-purple-500">Iter</span>
              </div>
              <h3 class="text-lg font-bold">迭代健康</h3>
            </div>
            <ElLink
              type="primary"
              :underline="false"
              @click="go('/project-manager/iteration')"
            >
              更多 >
            </ElLink>
          </div>
          <div class="space-y-4">
            <div class="flex justify-between">
              <span class="text-gray-500">进行中</span>
              <span class="font-bold">{{
                coreMetrics.iteration.active_iterations
              }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-500">延期</span>
              <span class="font-bold text-red-500">{{
                coreMetrics.iteration.delayed_iterations
              }}</span>
            </div>
            <div class="mt-2">
              <div class="mb-1 flex justify-between text-sm">
                <span class="text-gray-500">进度</span>
                <span>{{ coreMetrics.iteration.completion_rate }}%</span>
              </div>
              <div
                class="h-1.5 w-full overflow-hidden rounded-full bg-gray-100"
              >
                <div
                  class="h-full bg-purple-500"
                  :style="{
                    width: `${coreMetrics.iteration.completion_rate}%`,
                  }"
                ></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 性能监控 -->
        <div
          class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-[#151515]"
        >
          <div class="mb-6 flex items-center justify-between">
            <div class="flex items-center">
              <div
                class="mr-3 rounded-lg bg-orange-50 p-2 dark:bg-orange-900/20"
              >
                <span class="text-xl font-bold text-orange-500">Perf</span>
              </div>
              <h3 class="text-lg font-bold">性能监控</h3>
            </div>
            <ElLink
              type="primary"
              :underline="false"
              @click="go('/performance/monitor')"
            >
              更多 >
            </ElLink>
          </div>
          <div class="space-y-4">
            <div class="flex justify-between">
              <span class="text-gray-500">异常指标</span>
              <span class="font-bold text-red-500">{{
                coreMetrics.performance.abnormal_count
              }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-500">覆盖率</span>
              <span class="font-bold">
                {{ coreMetrics.performance.coverage_rate }}%
              </span>
            </div>
            <div
              class="mt-2 flex items-center gap-2 rounded bg-gray-50 p-2 text-sm dark:bg-gray-800"
            >
              <div
                class="h-2 w-2 rounded-full"
                :class="
                  coreMetrics.performance.abnormal_count === 0
                    ? 'bg-green-500'
                    : 'bg-red-500'
                "
              ></div>
              <span>{{
                coreMetrics.performance.abnormal_count === 0
                  ? '系统运行正常'
                  : '存在异常波动'
              }}</span>
            </div>
          </div>
        </div>

        <!-- DTS 监控 -->
        <DtsCard :data="coreMetrics.dts" />
      </template>
    </div>

    <!-- QG Risk Card -->
    <QGRiskCard scope="all" />

    <RequirementWorkspacePanel />

    <!-- 2. 图表区域 -->
    <div class="space-y-6">
      <template v-if="loadingDistribution">
        <ElSkeleton :count="5" class="h-[350px]" />
      </template>
      <template v-else-if="projectDistribution">
        <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
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
        </div>

        <div class="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <div
            class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]"
          >
            <h3 class="mb-4 text-lg font-bold">车控领域 IDVP 平台项目占比</h3>
            <ProjectPie
              :data="projectDistribution.vehicle_by_platform"
              title="IDVP 平台占比"
            />
          </div>
          <div
            class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]"
          >
            <h3 class="mb-4 text-lg font-bold">座舱领域 CDC 平台占比</h3>
            <ProjectPie
              :data="projectDistribution.cockpit_by_cdc_platform"
              title="CDC 平台占比"
            />
          </div>
          <div
            class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]"
          >
            <h3 class="mb-4 text-lg font-bold">座舱领域智慧屏版本占比</h3>
            <ProjectPie
              :data="projectDistribution.cockpit_by_smart_screen_version"
              title="智慧屏版本占比"
            />
          </div>
        </div>
      </template>
    </div>

    <!-- 3. 里程碑提醒 -->
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
        <div class="flex items-center gap-4">
          <div class="w-64">
            <ElSelect
              v-model="selectedQGs"
              multiple
              placeholder="筛选 QG 节点"
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
          <ElLink
            type="primary"
            :underline="false"
            @click="go('/project-manager/milestone')"
          >
            更多 >
          </ElLink>
        </div>
      </div>

      <ElSkeleton :loading="loadingMilestones" animated>
        <template #default>
          <div
            v-if="milestoneFiltering"
            class="py-10 text-center text-gray-500"
          >
            加载中...
          </div>
          <div v-else>
            <MilestoneTable :milestones="filteredMilestones" />
            <div
              class="mt-4 flex justify-end"
              v-if="milestoneTotal > milestonePageSize"
            >
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
