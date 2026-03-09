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
  ElSkeletonItem,
  ElTabPane,
  ElTabs,
} from 'element-plus';

import { queryIntegrationHistoryApi } from '#/api/integration-report';

defineOptions({ name: 'DailyIntegrationHistory' });

type HistoryTabKey = 'code' | 'dt';
type CodeSortOrder = 'asc' | 'desc';

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

const TEXT_SORT_KEYS = new Set([
  'caretaker_names',
  'config_name',
  'project_name',
]);
const codeSortState = ref<{ key: string; order: CodeSortOrder }>({
  key: 'record_date',
  order: 'desc',
});

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

function getCodeSortDefaultOrder(key: string): CodeSortOrder {
  return TEXT_SORT_KEYS.has(key) ? 'asc' : 'desc';
}

function toggleCodeSort(key: string) {
  if (codeSortState.value.key === key) {
    codeSortState.value.order =
      codeSortState.value.order === 'asc' ? 'desc' : 'asc';
    return;
  }
  codeSortState.value = {
    key,
    order: getCodeSortDefaultOrder(key),
  };
}

function codeSortIcon(key: string) {
  if (codeSortState.value.key !== key) {
    return 'lucide:arrow-up-down';
  }
  return codeSortState.value.order === 'asc'
    ? 'lucide:arrow-up'
    : 'lucide:arrow-down';
}

function getCodeSortValue(row: HistoryRow, key: string) {
  if (key === 'record_date') {
    return { rank: 3, value: new Date(row.record_date).getTime() };
  }
  if (key === 'config_name') {
    return { rank: 1, value: row.config_name || '' };
  }
  if (key === 'project_name') {
    return { rank: 1, value: row.project_name || '' };
  }
  if (key === 'caretaker_names') {
    return { rank: 1, value: row.caretaker_names || '' };
  }

  const metric = getMetric(row.code_metrics, key);
  if (metric?.value !== undefined && metric.value !== null) {
    return { rank: 3, value: Number(metric.value) };
  }

  const text = cellText(metric);
  if (text === 'error') {
    return { rank: 2, value: text };
  }
  if (text === '-') {
    return { rank: -1, value: text };
  }
  if (text === '未扫描') {
    return { rank: 0, value: text };
  }
  return { rank: 1, value: text };
}

function compareCodeSortValue(
  left: { rank: number; value: number | string },
  right: { rank: number; value: number | string },
  order: CodeSortOrder,
) {
  if (left.rank !== right.rank) {
    return order === 'asc' ? left.rank - right.rank : right.rank - left.rank;
  }

  if (typeof left.value === 'number' && typeof right.value === 'number') {
    return order === 'asc'
      ? left.value - right.value
      : right.value - left.value;
  }

  const result = `${left.value}`.localeCompare(`${right.value}`, 'zh-CN', {
    numeric: true,
    sensitivity: 'base',
  });
  return order === 'asc' ? result : -result;
}

const sortedCodeRows = computed(() => {
  const { key, order } = codeSortState.value;
  return [...rows.value].sort((left, right) => {
    const diff = compareCodeSortValue(
      getCodeSortValue(left, key),
      getCodeSortValue(right, key),
      order,
    );
    if (diff !== 0) {
      return diff;
    }
    const fallbackDateDiff =
      new Date(right.record_date).getTime() -
      new Date(left.record_date).getTime();
    if (fallbackDateDiff !== 0) {
      return fallbackDateDiff;
    }
    return left.config_name.localeCompare(right.config_name, 'zh-CN', {
      numeric: true,
      sensitivity: 'base',
    });
  });
});

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

      <div
        class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-gray-200 bg-white p-3 shadow-sm dark:border-gray-800 dark:bg-[#151515]"
      >
        <ElTabs v-model="activeTab" class="history-tabs min-h-0 flex-1">
          <ElTabPane label="代码检测类" name="code">
            <ElSkeleton :loading="loading" animated class="h-full">
              <template #template>
                <div class="h-full overflow-auto">
                  <div
                    class="history-skeleton-track history-skeleton-track--code"
                  >
                    <div
                      class="history-skeleton-row history-skeleton-row--head"
                    >
                      <ElSkeletonItem
                        class="history-skeleton-cell history-skeleton-cell--narrow"
                        variant="text"
                      />
                      <ElSkeletonItem
                        class="history-skeleton-cell history-skeleton-cell--wide"
                        variant="text"
                      />
                      <ElSkeletonItem
                        class="history-skeleton-cell"
                        variant="text"
                      />
                      <ElSkeletonItem
                        class="history-skeleton-cell"
                        variant="text"
                      />
                      <ElSkeletonItem
                        v-for="index in 8"
                        :key="`code-head-${index}`"
                        class="history-skeleton-cell"
                        variant="text"
                      />
                    </div>
                    <div
                      v-for="rowIndex in 7"
                      :key="`code-row-${rowIndex}`"
                      class="history-skeleton-row"
                    >
                      <ElSkeletonItem
                        class="history-skeleton-cell history-skeleton-cell--narrow"
                        variant="text"
                      />
                      <ElSkeletonItem
                        class="history-skeleton-cell history-skeleton-cell--wide"
                        variant="text"
                      />
                      <ElSkeletonItem
                        class="history-skeleton-cell"
                        variant="text"
                      />
                      <ElSkeletonItem
                        class="history-skeleton-cell"
                        variant="text"
                      />
                      <ElSkeletonItem
                        v-for="index in 8"
                        :key="`code-cell-${rowIndex}-${index}`"
                        class="history-skeleton-cell"
                        variant="text"
                      />
                    </div>
                  </div>
                </div>
              </template>
              <template #default>
                <div v-if="hasRows" class="h-full overflow-auto">
                  <table class="history-table w-full min-w-[1960px] text-sm">
                    <thead>
                      <tr class="text-left text-xs text-gray-500">
                        <th class="py-2 pr-3">
                          <button
                            type="button"
                            class="history-sort-button"
                            :class="{
                              'is-active': codeSortState.key === 'record_date',
                            }"
                            @click="toggleCodeSort('record_date')"
                          >
                            日期
                            <IconifyIcon
                              :icon="codeSortIcon('record_date')"
                              class="history-sort-icon"
                            />
                          </button>
                        </th>
                        <th class="py-2 pr-3">
                          <button
                            type="button"
                            class="history-sort-button"
                            :class="{
                              'is-active': codeSortState.key === 'config_name',
                            }"
                            @click="toggleCodeSort('config_name')"
                          >
                            配置
                            <IconifyIcon
                              :icon="codeSortIcon('config_name')"
                              class="history-sort-icon"
                            />
                          </button>
                        </th>
                        <th class="py-2 pr-3">
                          <button
                            type="button"
                            class="history-sort-button"
                            :class="{
                              'is-active': codeSortState.key === 'project_name',
                            }"
                            @click="toggleCodeSort('project_name')"
                          >
                            项目
                            <IconifyIcon
                              :icon="codeSortIcon('project_name')"
                              class="history-sort-icon"
                            />
                          </button>
                        </th>
                        <th class="py-2 pr-3">
                          <button
                            type="button"
                            class="history-sort-button"
                            :class="{
                              'is-active':
                                codeSortState.key === 'caretaker_names',
                            }"
                            @click="toggleCodeSort('caretaker_names')"
                          >
                            数据看护人
                            <IconifyIcon
                              :icon="codeSortIcon('caretaker_names')"
                              class="history-sort-icon"
                            />
                          </button>
                        </th>
                        <th
                          v-for="col in CODE_COLS"
                          :key="col.key"
                          class="py-2 pr-3"
                        >
                          <button
                            type="button"
                            class="history-sort-button"
                            :class="{
                              'is-active': codeSortState.key === col.key,
                            }"
                            @click="toggleCodeSort(col.key)"
                          >
                            {{ col.name }}
                            <IconifyIcon
                              :icon="codeSortIcon(col.key)"
                              class="history-sort-icon"
                            />
                          </button>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="r in sortedCodeRows"
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
              </template>
            </ElSkeleton>
          </ElTabPane>

          <ElTabPane label="DT 测试数据" name="dt">
            <ElSkeleton :loading="loading" animated class="h-full">
              <template #template>
                <div class="h-full overflow-auto">
                  <div
                    class="history-skeleton-track history-skeleton-track--dt"
                  >
                    <div
                      class="history-skeleton-row history-skeleton-row--head"
                    >
                      <ElSkeletonItem
                        class="history-skeleton-cell history-skeleton-cell--narrow"
                        variant="text"
                      />
                      <ElSkeletonItem
                        class="history-skeleton-cell history-skeleton-cell--wide"
                        variant="text"
                      />
                      <ElSkeletonItem
                        class="history-skeleton-cell"
                        variant="text"
                      />
                      <ElSkeletonItem
                        class="history-skeleton-cell"
                        variant="text"
                      />
                      <ElSkeletonItem
                        v-for="index in 4"
                        :key="`dt-head-${index}`"
                        class="history-skeleton-cell"
                        variant="text"
                      />
                    </div>
                    <div
                      v-for="rowIndex in 7"
                      :key="`dt-row-${rowIndex}`"
                      class="history-skeleton-row"
                    >
                      <ElSkeletonItem
                        class="history-skeleton-cell history-skeleton-cell--narrow"
                        variant="text"
                      />
                      <ElSkeletonItem
                        class="history-skeleton-cell history-skeleton-cell--wide"
                        variant="text"
                      />
                      <ElSkeletonItem
                        class="history-skeleton-cell"
                        variant="text"
                      />
                      <ElSkeletonItem
                        class="history-skeleton-cell"
                        variant="text"
                      />
                      <ElSkeletonItem
                        v-for="index in 4"
                        :key="`dt-cell-${rowIndex}-${index}`"
                        class="history-skeleton-cell"
                        variant="text"
                      />
                    </div>
                  </div>
                </div>
              </template>
              <template #default>
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
              </template>
            </ElSkeleton>
          </ElTabPane>
        </ElTabs>
      </div>
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

.history-sort-button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font: inherit;
  padding: 0;
  white-space: nowrap;
}

.history-sort-button:hover {
  color: var(--el-text-color-primary);
}

.history-sort-button.is-active {
  color: var(--el-color-primary);
  font-weight: 600;
}

.history-sort-icon {
  font-size: 12px;
  opacity: 0.7;
}

.history-skeleton-track {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 100%;
  padding-top: 4px;
}

.history-skeleton-track--code {
  min-width: 1960px;
}

.history-skeleton-track--dt {
  min-width: 1260px;
}

.history-skeleton-row {
  display: flex;
  gap: 12px;
}

.history-skeleton-row--head {
  padding-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.history-skeleton-cell {
  flex-shrink: 0;
  width: 140px;
  height: 16px;
}

.history-skeleton-cell--wide {
  width: 220px;
}

.history-skeleton-cell--narrow {
  width: 90px;
}

.history-table {
  border-collapse: separate;
  border-spacing: 0;
}

.history-table thead th {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--el-bg-color) !important;
  color: var(--el-text-color-secondary);
  box-shadow: inset 0 -1px 0 var(--el-border-color-lighter);
}
</style>
