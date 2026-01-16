<template>
  <div class="risk-log-drawer-container">
    <ElDrawer
      v-model="visible"
      title="里程碑风险跟踪"
      size="800px"
      destroy-on-close
    >
      <div v-loading="loading" class="h-full flex flex-col">
        <div class="mb-4">
          <h3 class="text-lg font-bold">{{ projectName }} - 风险列表</h3>
        </div>
        
        <!-- Risk List -->
        <div class="flex-1 overflow-auto">
          <ElTable :data="riskList" stripe border style="width: 100%">
            <ElTableColumn prop="qg_name" label="里程碑" width="100" />
            <ElTableColumn prop="risk_type" label="类型" width="100">
              <template #default="{ row }">
                <ElTag :type="row.risk_type === 'dts' ? 'danger' : 'warning'">
                  {{ row.risk_type === 'dts' ? '问题单' : 'DI超标' }}
                </ElTag>
              </template>
            </ElTableColumn>
            <ElTableColumn prop="description" label="风险描述" min-width="200" show-overflow-tooltip />
            <ElTableColumn prop="record_date" label="记录日期" width="120" />
            <ElTableColumn prop="status" label="状态" width="100">
              <template #default="{ row }">
                <ElTag :type="getStatusType(row.status)">
                  {{ getStatusLabel(row.status) }}
                </ElTag>
              </template>
            </ElTableColumn>
            <ElTableColumn label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <ElButton link type="primary" @click="viewLogs(row)">日志</ElButton>
                <ElButton 
                  v-if="row.status !== 'closed'" 
                  link 
                  type="primary" 
                  @click="handleRisk(row)"
                >
                  处理
                </ElButton>
              </template>
            </ElTableColumn>
          </ElTable>
        </div>
      </div>

      <template #footer>
        <ElButton @click="visible = false">关闭</ElButton>
      </template>
    </ElDrawer>
    
    <RiskHandleDialog ref="riskHandleDialogRef" @success="fetchRisks" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { 
  ElDrawer, ElTable, ElTableColumn, ElTag, ElButton, 
} from 'element-plus';
import { 
  getProjectRisksApi, 
  type RiskItem,
} from '#/api/project-manager/milestone';
import RiskHandleDialog from './RiskHandleDialog.vue';

const visible = ref(false);
const loading = ref(false);
const projectName = ref('');
const riskList = ref<RiskItem[]>([]);
const currentProjectId = ref('');

const riskHandleDialogRef = ref();

function open(projectId: string, name: string) {
  currentProjectId.value = projectId;
  projectName.value = name;
  visible.value = true;
  fetchRisks();
}

async function fetchRisks() {
  loading.value = true;
  try {
    riskList.value = await getProjectRisksApi(currentProjectId.value);
  } finally {
    loading.value = false;
  }
}

function getStatusType(status: string) {
  switch (status) {
    case 'pending': return 'danger';
    case 'confirmed': return 'warning';
    case 'closed': return 'success';
    default: return 'info';
  }
}

function getStatusLabel(status: string) {
  switch (status) {
    case 'pending': return '待处理';
    case 'confirmed': return '已确认';
    case 'closed': return '已关闭';
    default: return status;
  }
}

function viewLogs(row: RiskItem) {
  riskHandleDialogRef.value?.open(row, 'logs');
}

function handleRisk(row: RiskItem) {
  riskHandleDialogRef.value?.open(row, 'handle');
}

defineExpose({ open });
</script>

<style scoped>
/* Optional styles */
</style>
