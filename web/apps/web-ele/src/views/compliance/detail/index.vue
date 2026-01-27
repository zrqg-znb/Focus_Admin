<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { UserComplianceStat } from '#/api/compliance';

import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import { ElButton, ElCard, ElStatistic } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getPostUsersStats } from '#/api/compliance';
import { UserAvatar } from '#/components/user-avatar';

import RiskDrawer from '../components/RiskDrawer.vue';
import { useDetailColumns, useDetailSearchFormSchema } from './data';

const route = useRoute();
const router = useRouter();
const postId = computed(() => route.query.postId as string);
const postName = computed(() => (route.query.postName as string) || '岗位详情');

const drawerVisible = ref(false);
const currentUserId = ref('');
const currentUserName = ref('');

const summary = ref({
  total_risks: 0,
  unresolved_risks: 0,
  total_branch_risks: 0,
  unresolved_branch_risks: 0,
  fixed_branch_risks: 0,
  no_risk_branch_risks: 0,
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
          if (!postId.value) return [];

          const params: any = {};
          if (formValues.dateRange && formValues.dateRange.length === 2) {
            params.start_date = formValues.dateRange[0];
            params.end_date = formValues.dateRange[1];
          }

          const data = await getPostUsersStats(postId.value, params);

          summary.value = {
            total_risks: data.total_risks,
            unresolved_risks: data.unresolved_risks,
            total_branch_risks: data.total_branch_risks,
            unresolved_branch_risks: data.unresolved_branch_risks,
            fixed_branch_risks: data.fixed_branch_risks,
            no_risk_branch_risks: data.no_risk_branch_risks,
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

// Re-query when postId changes
watch(postId, () => {
  gridApi.query();
});
</script>

<template>
  <Page :title="`${postName} - 合规风险详情`" auto-content-height>
    <template #extra>
      <ElButton @click="goBack">返回</ElButton>
    </template>

    <div class="flex h-full flex-col gap-4">
      <div class="grid shrink-0 grid-cols-6 gap-4">
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic title="Change总数" :value="summary.total_risks" />
        </ElCard>
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic
            title="待处理Change"
            :value="summary.unresolved_risks"
            value-style="color: var(--el-color-danger)"
          />
        </ElCard>
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic title="分支风险总数" :value="summary.total_branch_risks" />
        </ElCard>
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic
            title="待处理分支风险"
            :value="summary.unresolved_branch_risks"
            value-style="color: var(--el-color-danger)"
          />
        </ElCard>
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic
            title="已修复分支风险"
            :value="summary.fixed_branch_risks"
            value-style="color: var(--el-color-success)"
          />
        </ElCard>
        <ElCard shadow="hover" class="!border-none">
          <ElStatistic
            title="无风险分支"
            :value="summary.no_risk_branch_risks"
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
            </div>
          </template>

          <template #unresolved="{ row }">
            <span
              :class="{ 'font-bold text-red-500': row.unresolved_count > 0 }"
            >
              {{ row.unresolved_count }}
            </span>
          </template>
          
          <template #unresolved_branch="{ row }">
            <span
              :class="{ 'font-bold text-red-500': row.unresolved_branch_count > 0 }"
            >
              {{ row.unresolved_branch_count }}
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
