<!-- eslint-disable vue/html-closing-bracket-newline, vue/multiline-html-element-content-newline -->
<script setup lang="ts">
/* eslint-disable vue/html-closing-bracket-newline, vue/multiline-html-element-content-newline */
import type { SkillRun } from '#/api/tools/agent-skills';

import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElTag } from 'element-plus';

import { listRunsApi } from '#/api/tools/agent-skills';
import { useZqTable } from '#/components/zq-table';

import { useRunColumns } from './data';

defineOptions({ name: 'AgentSkillsRecords' });
const router = useRouter();
const [Grid] = useZqTable<SkillRun>({
  gridOptions: {
    border: true,
    stripe: true,
    columns: useRunColumns(),
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page }: any) =>
          listRunsApi({ page: page.currentPage, pageSize: page.pageSize }),
      },
    },
    pagerConfig: { enabled: true, pageSize: 20, pageSizes: [10, 20, 50] },
    toolbarConfig: { custom: true, refresh: true, search: false, zoom: true },
  },
  showSearchForm: false,
});
const tags: Record<string, any> = {
  draft: 'info',
  queued: 'warning',
  running: 'warning',
  completed: 'success',
  failed: 'danger',
  cancelled: 'info',
};
</script>
<template>
  <Page title="优化记录" auto-content-height>
    <div class="flex h-full min-h-0 flex-col">
      <Grid class="h-full">
        <template #cell-status="{ row }">
          <ElTag :type="tags[row.status]">{{ row.status }}</ElTag> </template
        ><template #cell-baseline_score="{ row }">
          {{ row.baseline_score.toFixed(1) }}% </template
        ><template #cell-final_score="{ row }">
          {{ row.final_score.toFixed(1) }}% </template
        ><template #cell-actions="{ row }">
          <ElButton
            link
            type="primary"
            @click="
              router.push({
                path: '/tools/agent-skills/workbench',
                query: { runId: row.id },
              })
            "
          >
            查看
          </ElButton>
        </template>
      </Grid>
    </div>
  </Page>
</template>
