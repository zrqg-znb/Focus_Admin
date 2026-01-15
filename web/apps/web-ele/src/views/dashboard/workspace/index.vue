<script lang="ts" setup>
import type {
  CodeQualitySummary,
  DtsSummary,
  FavoriteProjectDetail,
  IterationSummary,
  PerformanceSummary,
  ProjectDistribution,
  UpcomingMilestone,
} from '#/api/dashboard';

import { onMounted, ref } from 'vue';

import { WorkbenchHeader } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';
import { preferences } from '@vben/preferences';
import { useUserStore } from '@vben/stores';

import {
  ElRadioButton,
  ElRadioGroup,
} from 'element-plus';

import {
  getCoreMetrics,
  getProjectDistribution,
  getProjectTimelines,
  getUpcomingMilestones,
} from '#/api/dashboard';

import AllProjectsView from './components/AllProjectsView.vue';
import FavoriteProjectsView from './components/FavoriteProjectsView.vue';
import QGRiskCard from './components/QGRiskCard.vue';

const userStore = useUserStore();

// View Scope
const viewScope = ref<'all' | 'favorites'>('all');

// 独立的状态变量
const coreMetrics = ref<null | {
  code_quality: CodeQualitySummary;
  iteration: IterationSummary;
  performance: PerformanceSummary;
  dts: DtsSummary;
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
const milestoneFiltering = ref(false); // 仅用于筛选时的 loading
const filteredMilestones = ref<UpcomingMilestone[]>([]);

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

  if (scope === 'all') {
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
  } else {
      loadingDistribution.value = false;
      loadingMilestones.value = false;
  }
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

function onProjectSearch(name: string) {
  projectSearchName.value = name;
  projectPage.value = 1; // Reset to first page on search
  fetchProjectTimelines();
}

async function fetchMilestones(isFilter = false, qgs: string[] = []) {
  if (isFilter) {
    milestoneFiltering.value = true;
  }

  try {
    const params = qgs.length > 0 ? qgs : undefined;
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

function onMilestoneFilter(qgs: string[]) {
  milestonePage.value = 1; // Reset to first page
  fetchMilestones(true, qgs);
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

    <div class="mt-5">
      <div class="mb-5 h-[300px]">
        <QGRiskCard />
      </div>

      <AllProjectsView
        v-if="viewScope === 'all'"
        :loading-core="loadingCore"
        :core-metrics="coreMetrics"
        :loading-timelines="loadingTimelines"
        :project-timelines="projectTimelines"
        :project-total="projectTotal"
        :loading-distribution="loadingDistribution"
        :project-distribution="projectDistribution"
        :loading-milestones="loadingMilestones"
        :milestone-filtering="milestoneFiltering"
        :milestone-total="milestoneTotal"
        :filtered-milestones="filteredMilestones"
        @search-project="onProjectSearch"
        @page-change-project="onProjectPageChange"
        @page-change-milestone="onMilestonePageChange"
        @filter-milestone="onMilestoneFilter"
      />

      <FavoriteProjectsView
        v-else
        :loading-core="loadingCore"
        :core-metrics="coreMetrics"
        :loading-timelines="loadingTimelines"
        :project-timelines="projectTimelines"
        :project-total="projectTotal"
        @search-project="onProjectSearch"
        @page-change-project="onProjectPageChange"
      />
    </div>
  </div>
</template>
