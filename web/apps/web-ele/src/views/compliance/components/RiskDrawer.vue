<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { ComplianceRecord } from '#/api/compliance';

import { ref, watch } from 'vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { ElButton, ElDrawer, ElMessage, ElTag } from 'element-plus';

import { getUserRecords, updateRecordStatus } from '#/api/compliance';
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

watch(() => visible.value, (val) => {
  if (val) {
    setTimeout(() => {
        gridApi.query();
    }, 100);
  } else {
    emit('close');
  }
});

const handleProcess = (row: ComplianceRecord) => {
  currentRecord.value = row;
  dialogVisible.value = true;
};

const handleDialogSubmit = async (row: ComplianceRecord, remark: string) => {
  try {
    await updateRecordStatus(row.id, { status: row.status, remark });
    ElMessage.success('处理成功');
    gridApi.query(); // Reload to show updated log
  } catch (error) {
    // Error handled by request interceptor usually
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
          <ElButton type="primary" size="small" @click="handleProcess(row)">
            处理 / 查看记录
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
