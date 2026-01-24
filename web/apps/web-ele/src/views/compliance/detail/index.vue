<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { UserComplianceStat } from '#/api/compliance';

import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { ElButton } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getDeptUsersStats } from '#/api/compliance';

import RiskDrawer from '../components/RiskDrawer.vue';
import { useDetailColumns, useDetailSearchFormSchema } from './data';

const route = useRoute();
const router = useRouter();
const deptId = computed(() => route.query.deptId as string);
const deptName = computed(() => route.query.deptName as string || '部门详情');

const drawerVisible = ref(false);
const currentUserId = ref('');
const currentUserName = ref('');

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
          const data = await getDeptUsersStats(deptId.value);
          if (formValues.user_name) {
            return data.filter(item => item.user_name.includes(formValues.user_name));
          }
          return data;
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

// Re-query when deptId changes (though usually page reloads or route changes trigger component mount)
watch(deptId, () => {
  gridApi.query();
});
</script>

<template>
  <Page :title="`${deptName} - 合规风险详情`" auto-content-height>
    <template #extra>
      <ElButton @click="goBack">返回</ElButton>
    </template>
    
    <Grid>
      <template #unresolved="{ row }">
        <span :class="{'text-red-500 font-bold': row.unresolved_count > 0}">
          {{ row.unresolved_count }}
        </span>
      </template>
      <template #action="{ row }">
        <ElButton type="primary" link @click="handleViewRisks(row)">
          查看风险
        </ElButton>
      </template>
    </Grid>

    <RiskDrawer
      v-model="drawerVisible"
      :user-id="currentUserId"
      :user-name="currentUserName"
      @close="handleDrawerClose"
    />
  </Page>
</template>
