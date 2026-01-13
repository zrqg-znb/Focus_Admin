<script setup lang="ts">
import type { ProjectConfigOut } from '#/api/integration-report';
import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';
import {
  ElButton,
  ElInput,
  ElMessage,
  ElSkeleton,
  ElSwitch,
  ElTag,
} from 'element-plus';

import {
  listIntegrationProjectsApi,
  toggleIntegrationSubscriptionApi,
} from '#/api/integration-report';

defineOptions({ name: 'DailyIntegrationSubscribe' });

const loading = ref(false);
const keyword = ref('');
const items = ref<ProjectConfigOut[]>([]);

const filtered = computed(() => {
  const k = keyword.value.trim().toLowerCase();
  if (!k) return items.value;
  return items.value.filter((p) => p.project_name.toLowerCase().includes(k));
});

async function reload() {
  try {
    loading.value = true;
    items.value = await listIntegrationProjectsApi();
  } finally {
    loading.value = false;
  }
}

async function toggle(row: ProjectConfigOut, val: boolean) {
  try {
    await toggleIntegrationSubscriptionApi(row.project_id, val);
    row.subscribed = val;
    ElMessage.success(val ? '订阅成功' : '已取消订阅');
  } catch (e) {
    row.subscribed = !val;
  }
}

onMounted(() => {
  reload();
});
</script>

<template>
  <Page auto-content-height>
    <div class="p-4 space-y-4">
      <div class="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
        <div class="flex items-center justify-between gap-3">
          <div class="flex items-center gap-2">
            <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 border border-indigo-100 dark:bg-indigo-900/20 dark:border-indigo-800">
              <IconifyIcon icon="lucide:mail" class="text-xl text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <div class="text-base font-bold text-gray-900 dark:text-white">每日集成报告邮件订阅</div>
              <div class="text-xs text-gray-400">订阅后将按你订阅的项目拆分发送</div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <ElInput v-model="keyword" placeholder="搜索项目名" clearable size="small" style="width: 220px" />
            <ElButton size="small" plain type="primary" :loading="loading" @click="reload">
              <template #icon><IconifyIcon icon="lucide:refresh-cw" /></template>
              刷新
            </ElButton>
          </div>
        </div>
      </div>

      <ElSkeleton :loading="loading" animated>
        <template #default>
          <div class="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
            <div class="mb-3 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="h-4 w-1 rounded-full bg-indigo-500" />
                <span class="font-bold text-gray-900 dark:text-white">订阅项目</span>
              </div>
              <ElTag type="info" size="small">指标明细在历史页与邮件中展示</ElTag>
            </div>

            <div class="overflow-auto">
              <table class="min-w-[860px] w-full text-sm">
                <thead>
                  <tr class="text-left text-xs text-gray-500">
                    <th class="py-2 pr-3">订阅</th>
                    <th class="py-2 pr-3">项目</th>
                    <th class="py-2 pr-3">负责人</th>
                    <th class="py-2 pr-3">最新日期</th>
                    <th class="py-2 pr-3">状态</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="p in filtered" :key="p.project_id" class="border-t border-gray-100 dark:border-gray-800">
                    <td class="py-3 pr-3">
                      <ElSwitch v-model="p.subscribed" @change="(v) => toggle(p, !!v)" />
                    </td>
                    <td class="py-3 pr-3">
                      <div class="font-bold text-gray-900 dark:text-white">{{ p.project_name }}</div>
                      <div class="text-[11px] text-gray-400">{{ p.project_domain }} · {{ p.project_type }}</div>
                    </td>
                    <td class="py-3 pr-3 text-gray-700 dark:text-gray-200">{{ p.project_managers || '-' }}</td>
                    <td class="py-3 pr-3 text-gray-500">{{ p.latest_date || '-' }}</td>
                    <td class="py-3 pr-3">
                      <ElTag v-if="p.enabled" type="success" size="small">已启用</ElTag>
                      <ElTag v-else type="warning" size="small">未启用</ElTag>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </template>
      </ElSkeleton>
    </div>
  </Page>
</template>
