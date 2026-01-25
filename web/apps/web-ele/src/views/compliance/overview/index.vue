<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { DeptComplianceStat } from '#/api/compliance';

import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElCard, ElStatistic } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getDeptStats } from '#/api/compliance';

import { useOverviewColumns, useOverviewSearchFormSchema } from './data';

const router = useRouter();

const summary = ref({
  total_risks: 0,
  unresolved_risks: 0,
  affected_users: 0,
  affected_branches: 0,
});

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useOverviewSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    columns: useOverviewColumns(),
    height: 'auto',
    keepSource: true,
    pagerConfig: { enabled: false },
    proxyConfig: {
      ajax: {
        query: async (_, formValues) => {
          const data = await getDeptStats();

          summary.value = {
            total_risks: data.total_risks,
            unresolved_risks: data.unresolved_risks,
            affected_users: data.affected_users,
            affected_branches: data.affected_branches,
          };

          let items = data.items;
          if (formValues.dept_name) {
            items = items.filter((item) =>
              item.dept_name.includes(formValues.dept_name),
            );
          }
          return items;
        },
      },
    },
    toolbarConfig: {
      refresh: { code: 'query' },
      search: true,
      zoom: true,
    },
  } as VxeTableGridOptions<DeptComplianceStat>,
});

const handleViewDetail = (row: DeptComplianceStat) => {
  router.push({
    path: '/compliance/detail',
    query: { deptId: row.dept_id, deptName: row.dept_name },
  });
};
</script>

<template>
  <Page title="合规风险概览" auto-content-height>
    <div class="flex h-full flex-col gap-4">
      <div class="grid shrink-0 grid-cols-4 gap-4">
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic title="总风险数" :value="summary.total_risks" />
        </ElCard>
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic
            title="待处理风险"
            :value="summary.unresolved_risks"
            value-style="color: var(--el-color-danger)"
          />
        </ElCard>
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic title="涉及用户" :value="summary.affected_users" />
        </ElCard>
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic title="涉及分支" :value="summary.affected_branches" />
        </ElCard>
      </div>

      <div class="min-h-0 flex-1 overflow-hidden">
        <Grid>
          <template #unresolved="{ row }">
            <span
              :class="{ 'font-bold text-red-500': row.unresolved_count > 0 }"
            >
              {{ row.unresolved_count }}
            </span>
          </template>
          <template #action="{ row }">
            <ElButton type="primary" link @click="handleViewDetail(row)">
              查看详情
            </ElButton>
          </template>
        </Grid>
      </div>
    </div>
  </Page>
</template>
