<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { UserComplianceStat } from '#/api/compliance';

import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElCard, ElStatistic } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getDeptUsersStats } from '#/api/compliance';
import { UserAvatar } from '#/components/user-avatar';

import RiskDrawer from '../components/RiskDrawer.vue';
import { useDetailColumns, useDetailSearchFormSchema } from './data';

const route = useRoute();
const router = useRouter();
const deptId = computed(() => route.query.deptId as string);
const deptName = computed(() => (route.query.deptName as string) || '部门详情');

const drawerVisible = ref(false);
const currentUserId = ref('');
const currentUserName = ref('');

const summary = ref({
  total_risks: 0,
  unresolved_risks: 0,
  fixed_risks: 0,
  no_risk_risks: 0,
});

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useDetailSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    columns: useDetailColumns(),
    height: 'auto',
    keepSource: true,
    pagerConfig: { enabled: false },
    proxyConfig: {
      ajax: {
        query: async (_, formValues) => {
          if (!deptId.value) return [];

          const params: any = {};
          if (formValues.dateRange && formValues.dateRange.length === 2) {
            params.start_date = formValues.dateRange[0];
            params.end_date = formValues.dateRange[1];
          }

          const data = await getDeptUsersStats(deptId.value, params);

          summary.value = {
            total_risks: data.total_risks,
            unresolved_risks: data.unresolved_risks,
            fixed_risks: data.fixed_risks,
            no_risk_risks: data.no_risk_risks,
          };

          let items = data.items;
          if (formValues.user_name) {
            items = items.filter((item) =>
              item.user_name.includes(formValues.user_name),
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
  } as VxeTableGridOptions<UserComplianceStat>,
});

const handleViewRisks = (row: UserComplianceStat) => {
  currentUserId.value = row.user_id;
  currentUserName.value = row.user_name;
  drawerVisible.value = true;
};

const handleDrawerClose = () => {
  // Refresh data when drawer closes to update counts
  gridApi.query();
};

const goBack = () => {
  router.back();
};

// Re-query when deptId changes
watch(deptId, () => {
  gridApi.query();
});
</script>

<template>
  <Page :title="`${deptName} - 合规风险详情`" auto-content-height>
    <template #extra>
      <ElButton @click="goBack">返回</ElButton>
    </template>

    <div class="flex h-full flex-col gap-4">
      <div class="grid shrink-0 grid-cols-4 gap-4">
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic title="总风险数" :value="summary.total_risks" />
        </ElCard>
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic
            title="待处理"
            :value="summary.unresolved_risks"
            value-style="color: var(--el-color-danger)"
          />
        </ElCard>
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic
            title="已修复"
            :value="summary.fixed_risks"
            value-style="color: var(--el-color-success)"
          />
        </ElCard>
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic
            title="无风险"
            :value="summary.no_risk_risks"
            value-style="color: var(--el-color-info)"
          />
        </ElCard>
      </div>

      <div class="min-h-0 flex-1 overflow-hidden">
        <Grid>
          <template #user_name="{ row }">
            <div class="flex items-center gap-2">
              <UserAvatar
                :avatar="row.avatar"
                :name="row.user_name"
                :user-id="row.user_id"
                :size="30"
                :font-size="14"
              />
              <!--              <span>{{ row.user_name }}</span>-->
            </div>
          </template>

          <template #unresolved="{ row }">
            <span
              :class="{ 'font-bold text-red-500': row.unresolved_count > 0 }"
            >
              {{ row.unresolved_count }}
            </span>
          </template>
          <template #action="{ row }">
            <ElButton type="primary" link @click="handleViewRisks(row)">
              查看风险
            </ElButton>
          </template>
        </Grid>
      </div>
    </div>

    <RiskDrawer
      v-model="drawerVisible"
      :user-id="currentUserId"
      :user-name="currentUserName"
      @close="handleDrawerClose"
    />
  </Page>
</template>
