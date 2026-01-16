<script setup lang="ts">
import type { RiskConfirmPayload, RiskItem } from '#/api/project-manager/milestone';

import { onMounted, ref, watch, computed } from 'vue';

import { IconifyIcon } from '@vben/icons';
import { ElButton, ElDialog, ElForm, ElFormItem, ElInput, ElMessage, ElPagination, ElTag } from 'element-plus';

import { confirmRiskApi, getPendingRisksApi, mockDailyCheckApi } from '#/api/project-manager/milestone';

const props = defineProps<{
  scope?: 'all' | 'favorites';
}>();

const loading = ref(false);
const risks = ref<RiskItem[]>([]);
const page = ref(1);
const pageSize = ref(3); // Changed to 3 per page as requested
const searchKeyword = ref('');

// Client-side filtering
const filteredRisks = computed(() => {
  if (!searchKeyword.value) {
    return risks.value;
  }
  const keyword = searchKeyword.value.toLowerCase();
  return risks.value.filter(item => 
    item.project_name.toLowerCase().includes(keyword)
  );
});

// Pagination based on filtered results
const paginatedRisks = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return filteredRisks.value.slice(start, end);
});

const total = computed(() => filteredRisks.value.length);

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
    const data = await getPendingRisksApi(props.scope || 'all');
    risks.value = data;
    // Reset page if needed, but usually keeping it is fine unless out of bounds
    if ((page.value - 1) * pageSize.value >= data.length) {
      page.value = 1;
    }
  } catch (e) {
    ElMessage.error('加载风险项失败');
  } finally {
    loading.value = false;
  }
}

watch(() => props.scope, () => {
  page.value = 1;
  searchKeyword.value = ''; // Reset search on scope change
  loadRisks();
});

function onSearch() {
  page.value = 1; // Reset to first page on search
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
  <div class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
    <div class="mb-6 flex items-center justify-between">
      <div class="flex items-center">
        <div class="mr-3 rounded-lg bg-red-50 p-2 dark:bg-red-900/20">
           <span class="text-xl font-bold text-red-500">Risk</span>
        </div>
        <h3 class="text-lg font-bold">QG 过点风险预警</h3>
      </div>
      <div class="flex items-center gap-4">
        <div class="w-64">
           <ElInput
              v-model="searchKeyword"
              placeholder="搜索项目名称"
              clearable
              @input="onSearch"
              @clear="onSearch"
           >
              <template #prefix>
                 <IconifyIcon icon="lucide:search" />
              </template>
           </ElInput>
        </div>
        <div class="flex gap-2">
          <ElButton size="small" type="success" plain @click="mockDailyCheck">模拟每日扫描</ElButton>
          <ElButton size="small" link type="primary" @click="loadRisks">刷新</ElButton>
        </div>
      </div>
    </div>

    <div v-if="loading" class="flex h-[200px] items-center justify-center">
      <span class="text-gray-400">加载中...</span>
    </div>

    <div v-else-if="filteredRisks.length === 0" class="flex h-[100px] items-center justify-center">
      <span class="text-gray-400">暂无待处理风险</span>
    </div>

    <div v-else>
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
        <div
          v-for="item in paginatedRisks"
          :key="item.id"
          class="rounded-lg border-l-4 p-4 shadow-sm transition-shadow hover:shadow-md dark:bg-opacity-10"
          :class="[
            item.status === 'confirmed' 
              ? 'border-l-yellow-500 bg-yellow-50 dark:bg-yellow-900/10' 
              : 'border-l-red-500 bg-red-50 dark:bg-red-900/10'
          ]"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <div class="flex flex-wrap items-center gap-2">
                <span class="font-bold text-gray-800 dark:text-gray-200">
                  {{ item.project_name }}
                </span>
                <ElTag size="small" effect="plain">{{ item.qg_name }}</ElTag>
                <ElTag size="small" :type="item.status === 'confirmed' ? 'warning' : 'danger'">
                  {{ getRiskTypeLabel(item.risk_type) }}
                </ElTag>
              </div>
              <div class="mt-2 text-sm text-gray-600 dark:text-gray-400 line-clamp-2" :title="item.description">
                {{ item.description }}
              </div>
              <div class="mt-2 flex items-center justify-between text-xs text-gray-400">
                <span>{{ item.record_date }}</span>
                <span v-if="item.status !== 'pending'">
                  {{ getStatusLabel(item.status) }}
                </span>
              </div>
            </div>
          </div>
          <div class="mt-3 flex justify-end border-t border-gray-200/50 pt-2 dark:border-gray-700/50">
             <ElButton
              size="small"
              :type="item.status === 'confirmed' ? 'warning' : 'primary'"
              text
              bg
              @click="handleConfirm(item)"
            >
              {{ item.status === 'confirmed' ? '再次处理' : '立即处理' }}
            </ElButton>
          </div>
        </div>
      </div>
      
      <div v-if="total > pageSize" class="mt-4 flex justify-end">
        <ElPagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          size="small"
          background
        />
      </div>
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
  </div>
</template>
