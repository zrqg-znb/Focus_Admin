<script setup lang="ts">
import type { HistoryRow, MetricCell } from '#/api/integration-report';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  ElButton,
  ElDatePicker,
  ElEmpty,
  ElInput,
  ElLink,
  ElMessage,
  ElSkeleton,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus';

import { queryIntegrationHistoryApi } from '#/api/integration-report';

defineOptions({ name: 'DailyIntegrationHistory' });

type HistoryTabKey = 'code' | 'dt';

const loading = ref(false);
const keyword = ref('');
const caretakerKeyword = ref('');
const range = ref<Date | null>(null);
const rows = ref<HistoryRow[]>([]);
const activeTab = ref<HistoryTabKey>('code');

function formatDate(d: Date) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

const startStr = computed(() => (range.value ? formatDate(range.value) : ''));
const endStr = computed(() => (range.value ? formatDate(range.value) : ''));
const hasRows = computed(() => rows.value.length > 0);
const resultCountText = computed(() => `共 ${rows.value.length} 条项目记录`);

const CODE_COLS = [
  { key: 'codecheck_error_num', name: 'CodeCheck 错误数' },
  { key: 'bin_scope_error_num', name: 'Bin Scope 错误数' },
  { key: 'build_check_error_num', name: 'Build 检测错误数' },
  { key: 'compile_error_num', name: 'Compile 错误数' },
  { key: 'tscan_error_num', name: 'TScan 问题数' },
  { key: 'tsan_error_num', name: 'TSan 问题数' },
  { key: 'valgrind_error_num', name: 'Valgrind 问题数' },
  { key: 'cppcheck_error_num', name: 'Cppcheck 问题数' },
  { key: 'weggli_error_num', name: 'Weggli 问题数' },
  { key: 'cooddy_error_num', name: 'Cooddy 问题数' },
  { key: 'binexplorer_error_num', name: 'BinExplorer 问题数' },
  { key: 'clang_tidy_error_num', name: 'Clang-Tidy 问题数' },
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
  if (c.value === undefined || c.value === null) return '未扫描';
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
      keyword: keyword.value.trim(),
      caretaker_keyword: caretakerKeyword.value.trim(),
    });
    rows.value = res.items;
  } catch {
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
  <Page content-class="flex h-full min-h-0 flex-col" auto-content-height>
    <div class="flex min-h-0 flex-1 flex-col gap-4 p-4">
      <div
        class="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-[#151515]"
      >
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-2">
            <div
              class="flex h-10 w-10 items-center justify-center rounded-xl border border-amber-100 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20"
            >
              <IconifyIcon
                icon="lucide:history"
                class="text-xl text-amber-600 dark:text-amber-400"
              />
            </div>
            <div>
              <div class="text-base font-bold text-gray-900 dark:text-white">
                每日集成监测历史数据
              </div>
              <div class="text-xs text-gray-400">
                按日期查看历史指标，并支持按配置、项目和数据看护人检索
              </div>
            </div>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <ElInput
              v-model="keyword"
              class="!w-48"
              clearable
              placeholder="搜索配置/项目"
              size="small"
              @keyup.enter="query"
            />
            <ElInput
              v-model="caretakerKeyword"
              class="!w-44"
              clearable
              placeholder="搜索数据看护人"
              size="small"
              @keyup.enter="query"
            />
            <ElDatePicker
              v-model="range"
              :clearable="false"
              size="small"
              type="date"
            />
            <ElButton
              :loading="loading"
              plain
              size="small"
              type="primary"
              @click="query"
            >
              <template #icon><IconifyIcon icon="lucide:search" /></template>
              查询
            </ElButton>
          </div>
        </div>
      </div>

      <ElSkeleton :loading="loading" animated class="min-h-0 flex-1">
        <template #default>
          <div
            class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-gray-200 bg-white p-3 shadow-sm dark:border-gray-800 dark:bg-[#151515]"
          >
            <div class="mb-2 flex flex-wrap items-center justify-between gap-3">
              <div class="flex items-center gap-2">
                <span class="h-4 w-1 rounded-full bg-blue-500"></span>
                <span class="font-bold text-gray-900 dark:text-white">
                  历史数据表
                </span>
                <ElTag size="small" type="info">{{ resultCountText }}</ElTag>
              </div>
              <ElTag size="small" type="warning">红色为预警项</ElTag>
            </div>

            <ElTabs v-model="activeTab" class="history-tabs min-h-0 flex-1">
              <ElTabPane label="代码检测类" name="code">
                <div v-if="hasRows" class="h-full overflow-auto">
                  <table class="history-table w-full min-w-[1960px] text-sm">
                    <thead>
                      <tr class="text-left text-xs text-gray-500">
                        <th class="py-2 pr-3">日期</th>
                        <th class="py-2 pr-3">配置</th>
                        <th class="py-2 pr-3">项目</th>
                        <th class="py-2 pr-3">数据看护人</th>
                        <th
                          v-for="col in CODE_COLS"
                          :key="col.key"
                          class="py-2 pr-3"
                        >
                          {{ col.name }}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="r in rows"
                        :key="`${r.record_date}-${r.config_id}`"
                        class="border-t border-gray-100 dark:border-gray-800"
                      >
                        <td class="py-3 pr-3 text-gray-500">
                          {{ r.record_date }}
                        </td>
                        <td
                          class="py-3 pr-3 font-bold text-gray-900 dark:text-white"
                        >
                          {{ r.config_name }}
                        </td>
                        <td class="py-3 pr-3 text-xs text-gray-500">
                          {{ r.project_name }}
                        </td>
                        <td class="py-3 pr-3 text-xs text-gray-500">
                          {{ r.caretaker_names || '-' }}
                        </td>
                        <td
                          v-for="col in CODE_COLS"
                          :key="col.key"
                          class="py-3 pr-3"
                        >
                          <ElLink
                            v-if="getMetric(r.code_metrics, col.key)?.url"
                            :href="
                              getMetric(r.code_metrics, col.key)?.url ||
                              undefined
                            "
                            target="_blank"
                            :underline="false"
                          >
                            <span
                              :class="
                                cellClass(getMetric(r.code_metrics, col.key))
                              "
                            >
                              {{ cellText(getMetric(r.code_metrics, col.key)) }}
                            </span>
                          </ElLink>
                          <span
                            v-else
                            :class="
                              cellClass(getMetric(r.code_metrics, col.key))
                            "
                          >
                            {{ cellText(getMetric(r.code_metrics, col.key)) }}
                          </span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="flex h-full items-center justify-center">
                  <ElEmpty description="暂无代码检测历史数据" />
                </div>
              </ElTabPane>

              <ElTabPane label="DT 测试数据" name="dt">
                <div v-if="hasRows" class="h-full overflow-auto">
                  <table class="history-table w-full min-w-[1260px] text-sm">
                    <thead>
                      <tr class="text-left text-xs text-gray-500">
                        <th class="py-2 pr-3">日期</th>
                        <th class="py-2 pr-3">配置</th>
                        <th class="py-2 pr-3">项目</th>
                        <th class="py-2 pr-3">数据看护人</th>
                        <th
                          v-for="col in DT_COLS"
                          :key="col.key"
                          class="py-2 pr-3"
                        >
                          {{ col.name }}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="r in rows"
                        :key="`dt-${r.record_date}-${r.config_id}`"
                        class="border-t border-gray-100 dark:border-gray-800"
                      >
                        <td class="py-3 pr-3 text-gray-500">
                          {{ r.record_date }}
                        </td>
                        <td
                          class="py-3 pr-3 font-bold text-gray-900 dark:text-white"
                        >
                          {{ r.config_name }}
                        </td>
                        <td class="py-3 pr-3 text-xs text-gray-500">
                          {{ r.project_name }}
                        </td>
                        <td class="py-3 pr-3 text-xs text-gray-500">
                          {{ r.caretaker_names || '-' }}
                        </td>
                        <td
                          v-for="col in DT_COLS"
                          :key="col.key"
                          class="py-3 pr-3"
                        >
                          <ElLink
                            v-if="getMetric(r.dt_metrics, col.key)?.url"
                            :href="
                              getMetric(r.dt_metrics, col.key)?.url || undefined
                            "
                            target="_blank"
                            :underline="false"
                          >
                            <span
                              :class="
                                cellClass(getMetric(r.dt_metrics, col.key))
                              "
                            >
                              {{ cellText(getMetric(r.dt_metrics, col.key)) }}
                            </span>
                          </ElLink>
                          <span
                            v-else
                            :class="cellClass(getMetric(r.dt_metrics, col.key))"
                          >
                            {{ cellText(getMetric(r.dt_metrics, col.key)) }}
                          </span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="flex h-full items-center justify-center">
                  <ElEmpty description="暂无 DT 测试历史数据" />
                </div>
              </ElTabPane>
            </ElTabs>
          </div>
        </template>
      </ElSkeleton>
    </div>
  </Page>
</template>

<style scoped>
.history-tabs {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

.history-tabs :deep(.el-tabs__header) {
  margin-bottom: 8px;
}

.history-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.history-tabs :deep(.el-tabs__nav) {
  gap: 6px;
}

.history-tabs :deep(.el-tabs__item) {
  border-radius: 9999px;
  height: 30px;
  line-height: 30px;
  padding: 0 14px;
}

.history-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.history-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.history-table thead th {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: inset 0 -1px 0 rgba(229, 231, 235, 0.9);
  backdrop-filter: blur(6px);
}

:global(.dark) .history-table thead th {
  background: rgba(21, 21, 21, 0.96);
  box-shadow: inset 0 -1px 0 rgba(31, 41, 55, 1);
}
</style>
