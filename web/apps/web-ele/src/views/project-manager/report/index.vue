<script lang="ts" setup>
import { onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import { ElEmpty } from 'element-plus';

import { listProjectsApi } from '#/api/project-manager/project';
import { FuPage } from '#/components/fu-page';

import ProjectReportContent from './ProjectReportContent.vue';
import ProjectSidebar from './ProjectSidebar.vue';

defineOptions({ name: 'ProjectDetailReport', keepAlive: true });

const route = useRoute();

function normalizeRouteProjectId(routeProjectId: unknown) {
  if (!routeProjectId || typeof routeProjectId !== 'string') return '';
  return routeProjectId === ':id' ? '' : routeProjectId;
}

const currentProjectId = ref(normalizeRouteProjectId(route.params.id));

function handleProjectSelect(id: string) {
  if (id === currentProjectId.value) return;
  currentProjectId.value = id;
}

watch(
  () => route.params.id,
  (newId) => {
    const normalizedId = normalizeRouteProjectId(newId);
    if (normalizedId) {
      currentProjectId.value = normalizedId;
      return;
    }
    if (!currentProjectId.value) {
      void redirectToDefaultProject();
    }
  },
);

async function redirectToDefaultProject() {
  try {
    const res = await listProjectsApi({ pageSize: 1, is_closed: false });
    const firstProject = res.items?.[0];
    if (firstProject) {
      currentProjectId.value = firstProject.id;
    }
  } catch (error) {
    console.error(error);
  }
}

onMounted(() => {
  if (!currentProjectId.value) {
    redirectToDefaultProject();
  }
});
</script>

<template>
  <FuPage
    left-width="300px"
    :left-min-width="260"
    :left-max-width="420"
    :left-collapsible="false"
    :left-padding="false"
    :right-padding="false"
    left-content-class="h-full"
    right-content-class="h-full"
  >
    <template #left>
      <ProjectSidebar
        :current-id="currentProjectId"
        @select="handleProjectSelect"
      />
    </template>

    <template #right>
      <div class="h-full bg-white dark:bg-[#151515]">
        <ProjectReportContent
          v-if="currentProjectId"
          :project-id="currentProjectId"
        />
        <div v-else class="flex h-full items-center justify-center">
          <ElEmpty description="暂无可展示的项目报告" />
        </div>
      </div>
    </template>
  </FuPage>
</template>
