<script lang="ts" setup>
import type {
  CmcPersonRecord,
  CmcSummary,
  CmcSyncTask,
} from '#/api/cmc-contribution';

import { computed, onMounted, onUnmounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { Filter } from '@element-plus/icons-vue';
import {
  ElButton,
  ElDatePicker,
  ElDialog,
  ElEmpty,
  ElInput,
  ElMessage,
  ElPopover,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus';

import {
  createCmcSyncTask,
  getCmcSummary,
  getCmcSyncTask,
  listCmcPersons,
} from '#/api/cmc-contribution';
import { useZqTable } from '#/components/zq-table';

defineOptions({ name: 'CmcContribution' });

const today = new Date();
const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
const formatDate = (value: Date) => value.toISOString().slice(0, 10);
const dateRange = ref<[string, string]>([
  formatDate(monthStart),
  formatDate(today),
]);
const activeTab = ref<'dashboard' | 'table'>('dashboard');
const summary = ref<CmcSummary>();
const loading = ref(false);
const userKeyword = ref('');
const userFilterVisible = ref(false);
const syncVisible = ref(false);
const syncRange = ref<[string, string]>();
const syncTask = ref<CmcSyncTask>();
const syncSubmitting = ref(false);
let pollTimer: ReturnType<typeof setInterval> | undefined;

const params = computed(() => ({
  startDate: dateRange.value[0],
  endDate: dateRange.value[1],
}));
const cards = computed(() => {
  const value = summary.value;
  if (!value) return [];
  const percent = (number: number) => `${(number * 100).toFixed(2)}%`;
  return [
    ['合入 MR', value.cnt_total],
    ['零检视 MR', value.zero_comment_mr_count],
    ['零检视占比', percent(value.zero_comment_rate)],
    ['有效检视意见', value.effective_comment_count],
    [
      '有效检视意见密度',
      value.effective_comment_density === null
        ? '--'
        : value.effective_comment_density.toFixed(4),
    ],
    ['检视代码行', value.checked_mr_lines],
    ['提交 MR 代码量', value.cmt_lines],
    ['贡献人数', value.contributor_count],
    [
      '严重 / 致命意见',
      `${value.major_comments_cnt} / ${value.fatal_comments_cnt}`,
    ],
    [
      '一般 / 建议意见',
      `${value.minor_comments_cnt} / ${value.sugge_comments_cnt}`,
    ],
    ['提交 Issue', value.cmt_issue],
  ];
});

const [Grid, gridApi] = useZqTable<CmcPersonRecord>({
  columns: [
    {
      field: 'user',
      minWidth: 140,
      slots: { header: 'header-user' },
      title: '人员',
    },
    { align: 'right', field: 'cnt_total', title: '合入MR' },
    { align: 'right', field: 'zero_comment_mr_count', title: '零检视MR' },
    {
      align: 'right',
      field: 'zero_comment_rate',
      formatter: ({ cellValue }) => `${(Number(cellValue) * 100).toFixed(2)}%`,
      title: '零检视占比',
    },
    { align: 'right', field: 'effective_comment_count', title: '有效检视意见' },
    {
      align: 'right',
      field: 'effective_comment_density',
      formatter: ({ cellValue }) =>
        cellValue === null ? '--' : Number(cellValue).toFixed(4),
      title: '意见密度',
    },
    { align: 'right', field: 'major_comments_cnt', title: '严重' },
    { align: 'right', field: 'fatal_comments_cnt', title: '致命' },
    { align: 'right', field: 'minor_comments_cnt', title: '一般' },
    { align: 'right', field: 'sugge_comments_cnt', title: '建议' },
    { align: 'right', field: 'cmt_issue', title: 'Issue' },
    { align: 'right', field: 'checked_mr_lines', title: '检视代码行' },
    { align: 'right', field: 'cmt_lines', title: '提交MR代码量' },
  ],
  pagerConfig: { enabled: true, pageSize: 20, pageSizes: [20, 50, 100] },
  proxyConfig: {
    ajax: {
      query: async ({ page }) =>
        listCmcPersons({
          ...params.value,
          page: page.currentPage,
          pageSize: page.pageSize,
          userKeyword: userKeyword.value,
        }),
    },
  },
});

async function loadSummary() {
  loading.value = true;
  try {
    summary.value = await getCmcSummary(params.value);
  } finally {
    loading.value = false;
  }
}
async function reloadAll(resetPage = true) {
  await loadSummary();
  if (activeTab.value === 'table')
    await gridApi.query({ page: resetPage ? 1 : undefined });
}
function applyUserFilter() {
  userFilterVisible.value = false;
  gridApi.query({ page: 1 });
}
function clearUserFilter() {
  userKeyword.value = '';
  applyUserFilter();
}
function stopPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = undefined;
}
async function pollTask(id: string) {
  const task = await getCmcSyncTask(id);
  syncTask.value = task;
  if (task.status === 'success') {
    stopPolling();
    ElMessage.success(
      `同步完成：${task.synced_dates.length} 天，${task.fetched_rows} 条数据`,
    );
    await reloadAll();
  }
  if (task.status === 'failed') {
    stopPolling();
    ElMessage.error(task.error_message || '同步任务失败');
  }
}
async function submitSync() {
  if (!syncRange.value?.[0] || !syncRange.value?.[1]) {
    ElMessage.warning('请选择同步日期范围');
    return;
  }
  syncSubmitting.value = true;
  try {
    syncTask.value = await createCmcSyncTask({
      startDate: syncRange.value[0],
      endDate: syncRange.value[1],
    });
    syncVisible.value = false;
    ElMessage.success('同步任务已提交');
    stopPolling();
    pollTimer = setInterval(() => pollTask(syncTask.value!.id), 2000);
  } finally {
    syncSubmitting.value = false;
  }
}
onMounted(loadSummary);
onUnmounted(stopPolling);
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full min-h-0 flex-col gap-3" v-loading="loading">
      <section
        class="flex flex-wrap items-center justify-between gap-3 rounded border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900"
      >
        <div class="flex items-center gap-3">
          <span class="font-medium">统计日期</span>
          <ElDatePicker
            v-model="dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            :clearable="false"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            @change="reloadAll"
          />
        </div>
        <div class="flex items-center gap-2">
          <ElTag
            v-if="syncTask"
            :type="
              syncTask.status === 'success'
                ? 'success'
                : syncTask.status === 'failed'
                  ? 'danger'
                  : 'warning'
            "
          >
            最近任务：{{ syncTask.status }}
          </ElTag>
          <ElButton type="primary" @click="syncVisible = true">
            管理员补数
          </ElButton>
        </div>
      </section>
      <ElTabs
        v-model="activeTab"
        class="min-h-0 flex-1"
        @tab-change="(tab) => tab === 'table' && gridApi.query({ page: 1 })"
      >
        <ElTabPane label="看板" name="dashboard">
          <div
            v-if="summary"
            class="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-6"
          >
            <div
              v-for="[label, value] in cards"
              :key="label"
              class="rounded border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900"
            >
              <div class="text-sm text-gray-500">{{ label }}</div>
              <div class="mt-2 text-2xl font-semibold">{{ value }}</div>
            </div>
          </div>
          <ElEmpty v-else description="当前日期范围暂无已同步数据" />
        </ElTabPane>
        <ElTabPane label="表格" name="table">
          <div class="min-h-100 h-[calc(100vh-290px)]">
            <Grid class="h-full">
              <template #header-user>
                <div class="flex items-center gap-1">
                  <span>人员</span>
                  <ElPopover
                    v-model:visible="userFilterVisible"
                    trigger="click"
                    width="240"
                  >
                    <template #reference>
                      <Filter class="cursor-pointer" :size="15" />
                    </template>
                    <div class="space-y-2">
                      <ElInput
                        v-model="userKeyword"
                        clearable
                        placeholder="输入人员名称"
                        @keyup.enter="applyUserFilter"
                      />
                      <div class="flex justify-end gap-2">
                        <ElButton link @click="clearUserFilter">清空</ElButton>
                        <ElButton type="primary" @click="applyUserFilter">
                          应用
                        </ElButton>
                      </div>
                    </div>
                  </ElPopover>
                </div>
              </template>
            </Grid>
          </div>
        </ElTabPane>
      </ElTabs>
    </div>
    <ElDialog v-model="syncVisible" title="CMC 数据补数" width="460px">
      <p class="mb-3 text-sm text-gray-500">
        一次最多同步 31 个自然日，任务在后台执行。
      </p>
      <ElDatePicker
        v-model="syncRange"
        class="w-full"
        type="daterange"
        value-format="YYYY-MM-DD"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
      />
      <template #footer>
        <ElButton @click="syncVisible = false">取消</ElButton>
        <ElButton :loading="syncSubmitting" type="primary" @click="submitSync">
          开始同步
        </ElButton>
      </template>
    </ElDialog>
  </Page>
</template>
