<script lang="ts" setup>
import { onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Page } from '@vben/common-ui';
import { listProjectsApi } from '#/api/project-manager/project';

import ProjectSidebar from './ProjectSidebar.vue';
import ProjectReportContent from './ProjectReportContent.vue';

defineOptions({ name: 'ProjectDetailReport', keepAlive: true });

const route = useRoute();
const router = useRouter();

// Get projectId from route
const currentProjectId = ref(route.params.id && route.params.id !== ':id' ? (route.params.id as string) : '');

function handleProjectSelect(id: string) {
  if (id === currentProjectId.value) return;
  router.replace(`/project-manager/report/${id}`);
}

// Watch route changes to update data
watch(
  () => route.params.id,
  (newId) => {
    if (newId && typeof newId === 'string' && newId !== ':id') {
      currentProjectId.value = newId;
    } else {
      redirectToDefaultProject();
    }
  }
);

async function redirectToDefaultProject() {
  try {
    const res = await listProjectsApi({ pageSize: 1, is_closed: false });
    if (res.items && res.items.length > 0) {
      const firstProject = res.items[0];
      router.replace(`/project-manager/report/${firstProject.id}`);
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
  <Page auto-content-height>
    <div class="flex h-full w-full bg-gray-50/50 dark:bg-black overflow-hidden rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
      <!-- Sidebar -->
      <div class="w-[280px] flex-shrink-0 h-full border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-[#151515]">
         <ProjectSidebar :current-id="currentProjectId" @select="handleProjectSelect" />
      </div>

      <!-- Main Content -->
      <div class="flex-1 h-full overflow-hidden flex flex-col bg-white/50 dark:bg-[#151515]/50">
         <ProjectReportContent
           v-if="currentProjectId"
           :project-id="currentProjectId"
           :key="currentProjectId"
         />
      </div>
    </div>
  </Page>
</template>
