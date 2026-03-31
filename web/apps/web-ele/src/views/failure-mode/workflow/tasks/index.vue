<script setup lang="ts">
import { onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

defineOptions({ name: 'FailureModeWorkflowTasksLegacyRedirect' });

const route = useRoute();
const router = useRouter();

onMounted(() => {
  router.replace({
    path: '/failure-mode/tasks',
    query: route.query,
  });
});
</script>

<template>
  <Page auto-content-height>
    <div
      class="flex min-h-[240px] items-center justify-center text-sm text-gray-500"
    >
      正在跳转到新的任务管理页面...
    </div>
  </Page>
</template>
