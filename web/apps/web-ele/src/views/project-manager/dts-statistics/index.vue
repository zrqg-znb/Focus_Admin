<script lang="ts" setup>
import type {
  DtsMergedDefect,
  DtsStatisticsQuery,
  DtsSummary,
} from '#/api/project-manager/dts-statistics';

import { computed, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import {
  getDtsList,
  getDtsSummary,
} from '#/api/project-manager/dts-statistics';
import { useZqTable } from '#/components/zq-table';

import { useColumns, useSearchFormSchema } from './data';
import DtsEditDrawer from './DtsEditDrawer.vue';

defineOptions({ name: 'DtsStatistics' });

type EditType = 'dev' | 'qa' | 'test';
type TabKey = 'dashboard' | 'list';

const activeTab = ref<TabKey>('list');

const editVisible = ref(false);
const editType = ref<EditType>('qa');
const editingRow = ref<DtsMergedDefect | null>(null);

const appliedFilters = ref<DtsStatisticsQuery | null>(null);
const summary = ref<DtsSummary | null>(null);
const summaryLoading = ref(false);

function openEdit(row: DtsMergedDefect, type: EditType) {
  editingRow.value = row;
  editType.value = type;
  editVisible.value = true;
}

function toQueryPayload(
  form: Record<string, any>,
  page: any,
): DtsStatisticsQuery | null {
  const project_ids = Array.isArray(form?.project_ids) ? form.project_ids : [];
  if (project_ids.length === 0) {
    return null;
  }

  const start_time = String(form?.start_time || '').trim();
  const end_time = String(form?.end_time || '').trim();
  if (!start_time || !end_time) {
    ElMessage.warning('请先选择开始时间和结束时间');
    return null;
  }

  return {
    project_ids,
    column_type: form?.column_type || 'openDefects',
    start_time,
    end_time,
    page_no: page?.currentPage || 1,
    page_size: page?.pageSize || 20,
  };
}

async function fetchSummary(force = false) {
  if (!appliedFilters.value) {
    summary.value = null;
    return;
  }
  if (!force && summary.value) {
    return;
  }
  summaryLoading.value = true;
  try {
    summary.value = await getDtsSummary(appliedFilters.value);
  } catch (error) {
    console.error(error);
    summary.value = null;
    ElMessage.error('加载总结看板失败');
  } finally {
    summaryLoading.value = false;
  }
}

const [Grid, gridApi] = useZqTable({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
    showCollapseButton: false,
  },
  gridOptions: {
    columns: useColumns(),
    border: true,
    stripe: true,
    rowKey: 'defectNo',
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({ form, page }: { form: any; page: any }) => {
          const payload = toQueryPayload(form, page);
          appliedFilters.value = payload;
          if (!payload) {
            summary.value = null;
            return { items: [], total: 0 };
          }
          const response = await getDtsList(payload);
          if (activeTab.value === 'dashboard') {
            void fetchSummary(true);
          }
          return { items: response.items || [], total: response.total || 0 };
        },
      },
    },
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [20, 50, 100, 200, 500],
    },
    toolbarConfig: {
      custom: true,
      refresh: true,
      search: true,
      zoom: true,
    },
  },
});

const hasSummary = computed(() => !!summary.value);

watch(
  () => activeTab.value,
  (tab) => {
    if (tab === 'dashboard') {
      void fetchSummary(true);
    }
  },
);

function handleSaved() {
  gridApi.reload();
  if (activeTab.value === 'dashboard') {
    void fetchSummary(true);
  }
}
</script>

<template>
  <Page auto-content-height>
    <el-tabs
      v-model="activeTab"
      class="dts-statistics-tabs flex h-full flex-col"
    >
      <el-tab-pane label="数据明细" name="list" class="h-full">
        <Grid class="h-full">
          <template #cell-project_names="{ row }">
            <span>{{ (row.project_names || []).join(', ') }}</span>
          </template>
          <template #cell-team_names="{ row }">
            <span>{{ (row.team_names || []).join(', ') }}</span>
          </template>
          <template #cell-actions="{ row }">
            <el-button
              type="primary"
              link
              size="small"
              @click="openEdit(row, 'qa')"
            >
              QA填报
            </el-button>
            <el-button
              type="primary"
              link
              size="small"
              @click="openEdit(row, 'dev')"
            >
              开发填报
            </el-button>
            <el-button
              type="primary"
              link
              size="small"
              @click="openEdit(row, 'test')"
            >
              测试填报
            </el-button>
          </template>
        </Grid>
      </el-tab-pane>
      <el-tab-pane label="统计看板" name="dashboard">
        <div v-loading="summaryLoading" class="rounded bg-white p-4">
          <template v-if="hasSummary && summary">
            <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
              <div class="rounded border border-slate-200 p-3">
                <div class="text-xs text-slate-500">总问题数</div>
                <div class="mt-1 text-xl font-semibold">
                  {{ summary.total_count }}
                </div>
              </div>
              <div class="rounded border border-slate-200 p-3">
                <div class="text-xs text-slate-500">未关闭</div>
                <div class="mt-1 text-xl font-semibold">
                  {{ summary.open_count }}
                </div>
              </div>
              <div class="rounded border border-slate-200 p-3">
                <div class="text-xs text-slate-500">已关闭</div>
                <div class="mt-1 text-xl font-semibold">
                  {{ summary.closed_count }}
                </div>
              </div>
              <div class="rounded border border-slate-200 p-3">
                <div class="text-xs text-slate-500">平均处理天数</div>
                <div class="mt-1 text-xl font-semibold">
                  {{ summary.avg_process_days }}
                </div>
              </div>
            </div>
          </template>
          <el-empty v-else description="请先选择筛选条件并查询明细" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <DtsEditDrawer
      v-model="editVisible"
      :edit-type="editType"
      :row="editingRow"
      @success="handleSaved"
    />
  </Page>
</template>
