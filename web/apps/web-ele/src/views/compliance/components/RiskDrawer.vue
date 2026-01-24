<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { ComplianceRecord } from '#/api/compliance';

import { ref, watch } from 'vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { ElButton, ElDrawer, ElMessage, ElRadioButton, ElRadioGroup, ElTag } from 'element-plus';

import { getUserRecords, updateRecordStatus } from '#/api/compliance';
import { useRiskColumns } from './data';

const props = defineProps<{
  userId: string;
  userName: string;
}>();

const visible = defineModel<boolean>({ default: false });
const emit = defineEmits(['close']);

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

watch(() => visible.value, (val) => {
  if (val) {
    // We need to wait for drawer animation or component mount?
    // gridApi.query() works if grid is mounted.
    // Since VxeGrid is inside Drawer, it might not be mounted immediately if destroy-on-close is true (default in VbenDrawer, but here using ElDrawer).
    // Let's rely on proxyConfig to fetch data when grid mounts/activates?
    // Actually, when visible becomes true, we can trigger query.
    setTimeout(() => {
        gridApi.query();
    }, 100);
  } else {
    emit('close');
  }
});

const handleStatusChange = async (row: ComplianceRecord, status: number) => {
  try {
    await updateRecordStatus(row.id, { status });
    ElMessage.success('状态更新成功');
    // Optimistic update
    row.status = status; 
  } catch (error) {
    gridApi.query();
  }
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
    size="80%"
    destroy-on-close
  >
    <div class="h-full flex flex-col p-4">
      <Grid class="flex-1">
        <template #url="{ row }">
          <a :href="row.url" target="_blank" class="text-blue-500 hover:underline">Link</a>
        </template>
        
        <template #branches="{ row }">
          <div class="flex flex-wrap gap-1">
            <ElTag v-for="branch in row.missing_branches" :key="branch" size="small" type="warning">
              {{ branch }}
            </ElTag>
          </div>
        </template>

        <template #status="{ row }">
          <ElTag :type="statusTypeMap[row.status]">{{ statusMap[row.status] }}</ElTag>
        </template>

        <template #action="{ row }">
          <div class="flex items-center gap-2">
            <ElRadioGroup v-model="row.status" size="small" @change="(val) => handleStatusChange(row, val as number)">
              <ElRadioButton :label="0">待处理</ElRadioButton>
              <ElRadioButton :label="1">无风险</ElRadioButton>
              <ElRadioButton :label="2">已修复</ElRadioButton>
            </ElRadioGroup>
          </div>
        </template>
      </Grid>
    </div>
  </ElDrawer>
</template>
