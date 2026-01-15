<script setup lang="ts">
import type { RiskConfirmPayload, RiskItem } from '#/api/project-manager/milestone';

import { onMounted, ref } from 'vue';

import { ElButton, ElCard, ElDialog, ElForm, ElFormItem, ElInput, ElMessage, ElPagination, ElTag } from 'element-plus';

import { confirmRiskApi, getPendingRisksApi, mockDailyCheckApi } from '#/api/project-manager/milestone';

const loading = ref(false);
const risks = ref<RiskItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(5);

const confirmDialogVisible = ref(false);
const currentRisk = ref<RiskItem | null>(null);
const confirmForm = ref<RiskConfirmPayload>({
  note: '',
  action: 'confirm',
});

async function mockDailyCheck() {
  try {
    await mockDailyCheckApi();
    ElMessage.success('已触发每日扫描');
    setTimeout(loadRisks, 1000); // Wait a bit for backend processing
  } catch (e) {
    ElMessage.error('触发扫描失败');
  }
}

async function loadRisks() {
  loading.value = true;
  try {
    const data = await getPendingRisksApi();
    risks.value = data;
    total.value = data.length;
  } catch (e) {
    ElMessage.error('加载风险项失败');
  } finally {
    loading.value = false;
  }
}

function handleConfirm(item: RiskItem) {
  currentRisk.value = item;
  confirmForm.value = {
    note: '',
    action: 'confirm',
  };
  confirmDialogVisible.value = true;
}

async function submitConfirm() {
  if (!currentRisk.value) return;
  try {
    await confirmRiskApi(currentRisk.value.id, confirmForm.value);
    ElMessage.success('操作成功');
    confirmDialogVisible.value = false;
    loadRisks();
  } catch (e) {
    ElMessage.error('操作失败');
  }
}

function getRiskTypeLabel(type: string) {
  const map: Record<string, string> = {
    dts: 'DTS问题',
    di: 'DI超标',
  };
  return map[type] || type;
}

function getStatusType(status: string) {
  const map: Record<string, 'warning' | 'success' | 'info'> = {
    pending: 'warning',
    confirmed: 'success',
    closed: 'info',
  };
  return map[status] || 'info';
}

function getStatusLabel(status: string) {
  const map: Record<string, string> = {
    pending: '待处理',
    confirmed: '已确认',
    closed: '已关闭',
  };
  return map[status] || status;
}

onMounted(() => {
  loadRisks();
});
</script>

<template>
  <ElCard class="h-full shadow-sm" body-class="p-4 h-full flex flex-col">
    <template #header>
      <div class="flex items-center justify-between">
        <span class="font-bold">QG 过点风险预警</span>
        <div class="flex gap-2">
          <ElButton size="small" type="success" plain @click="mockDailyCheck">模拟每日扫描</ElButton>
          <ElButton size="small" link type="primary" @click="loadRisks">刷新</ElButton>
        </div>
      </div>
    </template>

    <div v-if="loading" class="flex flex-1 items-center justify-center">
      <span class="text-gray-400">加载中...</span>
    </div>

    <div v-else-if="risks.length === 0" class="flex flex-1 items-center justify-center">
      <span class="text-gray-400">暂无待处理风险</span>
    </div>

    <div v-else class="flex flex-1 flex-col gap-3 overflow-y-auto">
      <div
        v-for="item in risks.slice((page - 1) * pageSize, page * pageSize)"
        :key="item.id"
        class="border-l-4 border-l-red-500 bg-red-50 p-3 dark:bg-red-900/10"
      >
        <div class="flex items-start justify-between">
          <div>
            <div class="flex items-center gap-2">
              <span class="font-bold text-gray-800 dark:text-gray-200">
                {{ item.project_name }}
              </span>
              <ElTag size="small" effect="plain">{{ item.qg_name }}</ElTag>
              <ElTag size="small" type="danger">{{ getRiskTypeLabel(item.risk_type) }}</ElTag>
            </div>
            <div class="mt-1 text-sm text-gray-600 dark:text-gray-400">
              {{ item.description }}
            </div>
            <div class="mt-1 text-xs text-gray-400">
              记录日期: {{ item.record_date }}
              <span v-if="item.status !== 'pending'" class="ml-2">
                状态: {{ getStatusLabel(item.status) }}
              </span>
            </div>
          </div>
          <ElButton
            v-if="item.status === 'pending'"
            size="small"
            type="primary"
            @click="handleConfirm(item)"
          >
            处理
          </ElButton>
        </div>
      </div>
    </div>

    <div v-if="risks.length > 0" class="mt-2 flex justify-end">
      <ElPagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        size="small"
      />
    </div>

    <!-- Confirm Dialog -->
    <ElDialog
      v-model="confirmDialogVisible"
      title="风险处理"
      width="500px"
      append-to-body
    >
      <ElForm :model="confirmForm" label-width="80px">
        <ElFormItem label="操作">
          <div class="flex gap-4">
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="radio" v-model="confirmForm.action" value="confirm" />
              <span>确认知晓 (持续跟踪)</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="radio" v-model="confirmForm.action" value="close" />
              <span>已解决 (关闭风险)</span>
            </label>
          </div>
        </ElFormItem>
        <ElFormItem label="备注" required>
          <ElInput
            v-model="confirmForm.note"
            type="textarea"
            :rows="3"
            placeholder="请填写处理情况或备注"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="confirmDialogVisible = false">取消</ElButton>
          <ElButton type="primary" @click="submitConfirm">提交</ElButton>
        </div>
      </template>
    </ElDialog>
  </ElCard>
</template>