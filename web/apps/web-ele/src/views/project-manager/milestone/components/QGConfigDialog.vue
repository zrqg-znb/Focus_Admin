<script setup lang="ts">
import type { QGConfig } from '#/api/project-manager/milestone';

import { onMounted, ref, watch } from 'vue';

import { ElButton, ElDialog, ElInputNumber, ElMessage, ElSwitch, ElTable, ElTableColumn } from 'element-plus';

import { getQGConfigsApi, saveQGConfigApi } from '#/api/project-manager/milestone';

const props = defineProps<{
  modelValue: boolean;
  projectId: string; // Changed from milestoneId
  projectName: string;
}>();

const emit = defineEmits(['update:modelValue', 'close']);

const visible = ref(false);
const loading = ref(false);
const configs = ref<QGConfig[]>([]);

const QG_LIST = ['QG1', 'QG2', 'QG3', 'QG4', 'QG5', 'QG6', 'QG7', 'QG8'];

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val;
    if (val && props.projectId) {
      loadConfigs();
    }
  },
);

watch(
  () => visible.value,
  (val) => {
    emit('update:modelValue', val);
    if (!val) {
      emit('close');
    }
  },
);

async function loadConfigs() {
  loading.value = true;
  try {
    // We need to use project ID to fetch configs. 
    // Backend API needs to be updated to support fetching by project ID or frontend needs to find milestone ID first.
    // Assuming we will update backend to accept project ID for getting QG configs.
    const data = await getQGConfigsApi(props.projectId); // Updated API call
    // Merge with full QG list to ensure all are shown
    const merged = QG_LIST.map((qg) => {
      const existing = data.find((c) => c.qg_name === qg);
      return (
        existing || {
          id: '',
          milestone: '', // Not critical for display
          qg_name: qg,
          target_di: null,
          enabled: false,
          is_delayed: false,
        }
      );
    });
    configs.value = merged;
  } catch (e) {
    ElMessage.error('加载配置失败');
  } finally {
    loading.value = false;
  }
}

async function handleSave(row: QGConfig) {
  try {
    // Similarly, use project ID for saving
    const res = await saveQGConfigApi(props.projectId, { // Updated API call
      qg_name: row.qg_name,
      target_di: row.target_di,
      enabled: row.enabled,
      is_delayed: row.is_delayed,
    });
    // Update local id
    row.id = res.id;
    ElMessage.success(`${row.qg_name} 配置已保存`);
  } catch (e) {
    ElMessage.error('保存失败');
    // Revert switch if needed, but simple message is enough for now
  }
}
</script>

<template>
  <ElDialog v-model="visible" :title="`QG预警配置 - ${projectName}`" width="600px" append-to-body>
    <ElTable :data="configs" v-loading="loading" border style="width: 100%">
      <ElTableColumn prop="qg_name" label="QG点" width="100" />
      <ElTableColumn label="启用预警" width="100">
        <template #default="{ row }">
          <ElSwitch v-model="row.enabled" @change="() => handleSave(row)" />
        </template>
      </ElTableColumn>
      <ElTableColumn label="是否延期" width="100">
        <template #default="{ row }">
          <ElSwitch v-model="row.is_delayed" @change="() => handleSave(row)" />
        </template>
      </ElTableColumn>
      <ElTableColumn label="说明">
        <template #default="{ row }">
          <span v-if="row.enabled" class="text-xs text-gray-400">
            预警规则：目标DI自动从DTS获取，当前DI > 目标DI触发风险。
          </span>
          <span v-else class="text-xs text-gray-300">
            未启用
          </span>
        </template>
      </ElTableColumn>
    </ElTable>
    <template #footer>
      <div class="flex justify-end">
        <ElButton @click="visible = false">关闭</ElButton>
      </div>
    </template>
  </ElDialog>
</template>