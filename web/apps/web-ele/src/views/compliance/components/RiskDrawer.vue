<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { ComplianceRecord } from '#/api/compliance';

import { ref, watch } from 'vue';

import { ElButton, ElDrawer, ElMessage, ElTag } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getUserRecords } from '#/api/compliance';

import { useRiskColumns } from './data';
import RiskHandleDialog from './RiskHandleDialog.vue';

const props = defineProps<{
  userId: string;
  userName: string;
}>();

const visible = defineModel<boolean>({ default: false });
const emit = defineEmits(['close']);

const dialogVisible = ref(false);
const currentRecord = ref<ComplianceRecord | null>(null);

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: useRiskColumns(),
    height: 'auto',
    keepSource: true,
    pagerConfig: { enabled: false },
    proxyConfig: {
      ajax: {
        query: async () => {
          if (!props.userId) return [];
          return await getUserRecords(props.userId);
        },
      },
    },
    toolbarConfig: {
      refresh: { code: 'query' },
      zoom: true,
    },
  } as VxeTableGridOptions<ComplianceRecord>,
});

watch(
  () => visible.value,
  (val) => {
    if (val) {
      setTimeout(() => {
        gridApi.query();
      }, 100);
    } else {
      emit('close');
    }
  },
);

const handleProcess = (row: ComplianceRecord) => {
  currentRecord.value = row;
  dialogVisible.value = true;
};

const handleDialogSubmit = () => {
  gridApi.query(); // Reload to show updated statuses
};

const statusMap: Record<number, string> = {
  0: '待处理',
  1: '无风险',
  2: '已修复',
};

const statusTypeMap: Record<number, string> = {
  0: 'danger',
  1: 'info',
  2: 'success',
};
</script>

<template>
  <ElDrawer
    v-model="visible"
    :title="`${userName} - 风险记录`"
    destroy-on-close
    size="80%"
  >
    <div class="flex h-full flex-col p-4">
      <Grid class="flex-1">
        <template #url="{ row }">
          <a
            :href="row.url"
            class="text-blue-500 hover:underline"
            target="_blank"
            >Link</a
          >
        </template>

        <template #branches="{ row }">
          <div class="flex flex-wrap gap-1">
            <ElTag
              v-for="branch in row.branches"
              :key="branch.id"
              :type="statusTypeMap[branch.status]"
              size="small"
            >
              {{ branch.branch_name }}
            </ElTag>
          </div>
        </template>

        <template #status="{ row }">
          <ElTag :type="statusTypeMap[row.status]">{{
            statusMap[row.status]
          }}</ElTag>
        </template>

        <template #action="{ row }">
          <ElButton size="small" type="primary" @click="handleProcess(row)">
            分支处理
          </ElButton>
        </template>
      </Grid>

      <RiskHandleDialog
        v-model="dialogVisible"
        :record="currentRecord"
        @submit="handleDialogSubmit"
      />
    </div>
  </ElDrawer>
</template>
