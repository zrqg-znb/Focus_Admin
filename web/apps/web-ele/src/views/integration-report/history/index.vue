<script setup lang="ts">
import type { HistoryRow, MetricCell } from '#/api/integration-report';
import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';
import { ElButton, ElDatePicker, ElInput, ElLink, ElMessage, ElSkeleton, ElTag } from 'element-plus';

import { queryIntegrationHistoryApi } from '#/api/integration-report';

defineOptions({ name: 'DailyIntegrationHistory' });

const loading = ref(false);
const keyword = ref('');
const range = ref<Date | null>(null);
const rows = ref<HistoryRow[]>([]);

function formatDate(d: Date) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

const startStr = computed(() => (range.value ? formatDate(range.value) : ''));
const endStr = computed(() => (range.value ? formatDate(range.value) : ''));

const CODE_COLS = [
  { key: 'codecheck_error_num', name: 'CodeCheck 错误数' },
  { key: 'bin_scope_error_num', name: 'Bin Scope 错误数' },
  { key: 'build_check_error_num', name: 'Build 检测错误数' },
  { key: 'compile_error_num', name: 'Compile 错误数' },
];

const DT_COLS = [
  { key: 'dt_pass_rate', name: 'DT 通过率' },
  { key: 'dt_pass_num', name: 'DT 通过数' },
  { key: 'dt_line_coverage', name: '行覆盖率' },
  { key: 'dt_method_coverage', name: '方法覆盖率' },
];

function cellText(c?: MetricCell) {
  if (!c) return '-';
  if (c.text) return c.text;
  if (c.value === undefined || c.value === null) return '-';
  const s = `${c.value}`;
  return c.unit ? `${s}${c.unit}` : s;
}
function cellClass(c?: MetricCell) {
  if (!c) return 'text-gray-400';
  if (c.level === 'danger') return 'text-red-600 font-bold';
  if (c.level === 'warning') return 'text-orange-600 font-bold';
  return 'text-gray-700 dark:text-gray-200';
}

function getMetric(metrics: MetricCell[], key: string) {
  return metrics.find((m) => m.key === key);
}

async function query() {
  if (!range.value) return;
  try {
    loading.value = true;
    const res = await queryIntegrationHistoryApi({
      start: startStr.value,
      end: endStr.value,
      keyword: keyword.value,
    });
    rows.value = res.items;
  } catch (e) {
    ElMessage.error('查询失败');
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  range.value = new Date();
  query();
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
            <ElInput
              v-model="keyword"
              class="!w-48"
              clearable
              placeholder="搜索配置/项目"
              size="small"
              @keyup.enter="query"
            />
            <ElDatePicker v-model="range" :clearable="false" size="small" type="date" />
            <ElButton :loading="loading" plain size="small" type="primary" @click="query">
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
                      <th class="py-2 pr-3">配置</th>
                      <th class="py-2 pr-3">项目</th>
                      <th v-for="col in CODE_COLS" :key="col.key" class="py-2 pr-3">{{ col.name }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="r in rows" :key="`${r.record_date}-${r.config_id}`" class="border-t border-gray-100 dark:border-gray-800">
                      <td class="py-3 pr-3 text-gray-500">{{ r.record_date }}</td>
                      <td class="py-3 pr-3 font-bold text-gray-900 dark:text-white">{{ r.config_name }}</td>
                      <td class="py-3 pr-3 text-gray-500 text-xs">{{ r.project_name }}</td>
                      <td v-for="col in CODE_COLS" :key="col.key" class="py-3 pr-3">
                        <ElLink
                          v-if="getMetric(r.code_metrics, col.key)?.url"
                          :href="getMetric(r.code_metrics, col.key)?.url || undefined"
                          target="_blank"
                          :underline="false"
                        >
                          <span :class="cellClass(getMetric(r.code_metrics, col.key))">
                            {{ cellText(getMetric(r.code_metrics, col.key)) }}
                          </span>
                        </ElLink>
                        <span v-else :class="cellClass(getMetric(r.code_metrics, col.key))">
                          {{ cellText(getMetric(r.code_metrics, col.key)) }}
                        </span>
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
                      <th class="py-2 pr-3">配置</th>
                      <th class="py-2 pr-3">项目</th>
                      <th v-for="col in DT_COLS" :key="col.key" class="py-2 pr-3">{{ col.name }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="r in rows" :key="`dt-${r.record_date}-${r.config_id}`" class="border-t border-gray-100 dark:border-gray-800">
                      <td class="py-3 pr-3 text-gray-500">{{ r.record_date }}</td>
                      <td class="py-3 pr-3 font-bold text-gray-900 dark:text-white">{{ r.config_name }}</td>
                      <td class="py-3 pr-3 text-gray-500 text-xs">{{ r.project_name }}</td>
                      <td v-for="col in DT_COLS" :key="col.key" class="py-3 pr-3">
                        <ElLink
                          v-if="getMetric(r.dt_metrics, col.key)?.url"
                          :href="getMetric(r.dt_metrics, col.key)?.url || undefined"
                          target="_blank"
                          :underline="false"
                        >
                          <span :class="cellClass(getMetric(r.dt_metrics, col.key))">
                            {{ cellText(getMetric(r.dt_metrics, col.key)) }}
                          </span>
                        </ElLink>
                        <span v-else :class="cellClass(getMetric(r.dt_metrics, col.key))">
                          {{ cellText(getMetric(r.dt_metrics, col.key)) }}
                        </span>
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
