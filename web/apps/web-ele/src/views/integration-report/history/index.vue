<script setup lang="ts">
import type { HistoryRow, MetricCell, ProjectConfigOut } from '#/api/integration-report';
import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';
import { ElButton, ElDatePicker, ElLink, ElMessage, ElSkeleton, ElTag } from 'element-plus';

import { listIntegrationProjectsApi, queryIntegrationHistoryApi } from '#/api/integration-report';

defineOptions({ name: 'DailyIntegrationHistory' });

const loading = ref(false);
const range = ref<[Date, Date] | null>(null);
const rows = ref<HistoryRow[]>([]);
const projects = ref<ProjectConfigOut[]>([]);

const startStr = computed(() => (range.value ? range.value[0].toISOString().slice(0, 10) : ''));
const endStr = computed(() => (range.value ? range.value[1].toISOString().slice(0, 10) : ''));

function cellText(c: MetricCell) {
  if (c.text) return c.text;
  if (c.value === undefined || c.value === null) return '-';
  const s = `${c.value}`;
  return c.unit ? `${s}${c.unit}` : s;
}
function cellClass(c: MetricCell) {
  if (c.level === 'danger') return 'text-red-600 font-bold';
  if (c.level === 'warning') return 'text-orange-600 font-bold';
  return 'text-gray-700 dark:text-gray-200';
}

const codeKeys = computed(() => (projects.value[0]?.code_metrics || []).map((m) => m.key));
const dtKeys = computed(() => (projects.value[0]?.dt_metrics || []).map((m) => m.key));
const codeNameMap = computed(() => Object.fromEntries((projects.value[0]?.code_metrics || []).map((m) => [m.key, m.name])));
const dtNameMap = computed(() => Object.fromEntries((projects.value[0]?.dt_metrics || []).map((m) => [m.key, m.name])));

async function init() {
  projects.value = await listIntegrationProjectsApi();
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 6);
  range.value = [start, end];
}

async function query() {
  if (!range.value) return;
  try {
    loading.value = true;
    const res = await queryIntegrationHistoryApi({ start: startStr.value, end: endStr.value });
    rows.value = res.items;
  } catch (e) {
    ElMessage.error('查询失败');
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await init();
  await query();
});
</script>

<template>
  <Page auto-content-height>
    <div class="p-4 space-y-4">
      <div class="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
        <div class="flex items-center justify-between gap-3">
          <div class="flex items-center gap-2">
            <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 border border-amber-100 dark:bg-amber-900/20 dark:border-amber-800">
              <IconifyIcon icon="lucide:history" class="text-xl text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <div class="text-base font-bold text-gray-900 dark:text-white">每日集成监测历史数据</div>
              <div class="text-xs text-gray-400">展示选定日期范围内的各项目指标</div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <ElDatePicker v-model="range" type="daterange" unlink-panels size="small" />
            <ElButton size="small" plain type="primary" :loading="loading" @click="query">
              <template #icon><IconifyIcon icon="lucide:search" /></template>
              查询
            </ElButton>
          </div>
        </div>
      </div>

      <ElSkeleton :loading="loading" animated>
        <template #default>
          <div class="grid grid-cols-1 gap-4">
            <div class="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
              <div class="mb-3 flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="h-4 w-1 rounded-full bg-blue-500" />
                  <span class="font-bold text-gray-900 dark:text-white">代码检测类</span>
                </div>
                <ElTag type="info" size="small">红色为预警项</ElTag>
              </div>

              <div class="overflow-auto">
                <table class="min-w-[1100px] w-full text-sm">
                  <thead>
                    <tr class="text-left text-xs text-gray-500">
                      <th class="py-2 pr-3">日期</th>
                      <th class="py-2 pr-3">项目</th>
                      <th v-for="k in codeKeys" :key="k" class="py-2 pr-3">{{ codeNameMap[k] }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="r in rows" :key="`${r.record_date}-${r.project_id}`" class="border-t border-gray-100 dark:border-gray-800">
                      <td class="py-3 pr-3 text-gray-500">{{ r.record_date }}</td>
                      <td class="py-3 pr-3 font-bold text-gray-900 dark:text-white">{{ r.project_name }}</td>
                      <td v-for="c in r.code_metrics" :key="c.key" class="py-3 pr-3">
                        <ElLink v-if="c.url" :href="c.url" target="_blank" :underline="false" :class="cellClass(c)">
                          {{ cellText(c) }}
                        </ElLink>
                        <span v-else :class="cellClass(c)">{{ cellText(c) }}</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div class="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
              <div class="mb-3 flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="h-4 w-1 rounded-full bg-emerald-500" />
                  <span class="font-bold text-gray-900 dark:text-white">DT 测试数据</span>
                </div>
                <ElTag type="info" size="small">点击单元格跳转详情</ElTag>
              </div>

              <div class="overflow-auto">
                <table class="min-w-[1100px] w-full text-sm">
                  <thead>
                    <tr class="text-left text-xs text-gray-500">
                      <th class="py-2 pr-3">日期</th>
                      <th class="py-2 pr-3">项目</th>
                      <th v-for="k in dtKeys" :key="k" class="py-2 pr-3">{{ dtNameMap[k] }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="r in rows" :key="`dt-${r.record_date}-${r.project_id}`" class="border-t border-gray-100 dark:border-gray-800">
                      <td class="py-3 pr-3 text-gray-500">{{ r.record_date }}</td>
                      <td class="py-3 pr-3 font-bold text-gray-900 dark:text-white">{{ r.project_name }}</td>
                      <td v-for="c in r.dt_metrics" :key="c.key" class="py-3 pr-3">
                        <ElLink v-if="c.url" :href="c.url" target="_blank" :underline="false" :class="cellClass(c)">
                          {{ cellText(c) }}
                        </ElLink>
                        <span v-else :class="cellClass(c)">{{ cellText(c) }}</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </template>
      </ElSkeleton>
    </div>
  </Page>
</template>

