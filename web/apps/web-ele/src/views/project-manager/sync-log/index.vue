<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SyncLog } from '#/api/project-manager/sync_log';

import { Page } from '@vben/common-ui';

import { ElTag } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getSyncLogsApi } from '#/api/project-manager/sync_log';

import { useSyncLogColumns } from './data';

defineOptions({ name: 'SyncLogViewer' });

const [Grid] = useVbenVxeGrid({
  gridOptions: {
    columns: useSyncLogColumns(),
    height: 'auto',
    pagerConfig: { enabled: true },
    proxyConfig: {
      ajax: {
        query: async ({ page }) => {
          return await getSyncLogsApi({
            page: page.currentPage,
            pageSize: page.pageSize,
          });
        },
      },
    },
    toolbarConfig: {
      custom: true,
      refresh: { code: 'query' },
      zoom: true,
    },
  } as VxeTableGridOptions<SyncLog>,
});

function getStatusType(status: string) {
  switch (status) {
    case 'success': {
      return 'success';
    }
    case 'failed': {
      return 'danger';
    }
    case 'pending': {
      return 'warning';
    }
    default: {
      return 'info';
    }
  }
}

function getStatusText(status: string) {
  switch (status) {
    case 'success': {
      return '成功';
    }
    case 'failed': {
      return '失败';
    }
    case 'pending': {
      return '进行中';
    }
    default: {
      return '未知';
    }
  }
}
</script>

<template>
  <Page auto-content-height>
    <Grid>
      <template #status="{ row }">
        <ElTag :type="getStatusType(row.status)" size="small">
          {{ getStatusText(row.status) }}
        </ElTag>
      </template>
      <template #action>
        <!-- 预留详情按钮 -->
      </template>
    </Grid>
  </Page>
</template>
