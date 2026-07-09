<script lang="ts" setup>
import type {
  ReleasePlanFilterParams,
  ReleasePlanItem,
} from '#/api/project-manager/release-plan';

import { reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { Filter } from '@element-plus/icons-vue';
import {
  ElButton,
  ElDatePicker,
  ElIcon,
  ElInput,
  ElOption,
  ElPopover,
  ElSelect,
} from 'element-plus';

import { listReleasePlansApi } from '#/api/project-manager/release-plan';
import { useZqTable } from '#/components/zq-table';

import { useReleasePlanColumns, VERSION_TYPE_OPTIONS } from './data';

defineOptions({ name: 'ProjectReleasePlanDashboard' });

interface ReleasePlanQueryParams {
  page: {
    currentPage: number;
    pageSize: number;
  };
}

const filters = reactive<ReleasePlanFilterParams>({
  keyword: '',
  branch_name: '',
  version_type: '',
  platform_keyword: '',
  vehicle_keyword: '',
  release_date_start: '',
  release_date_end: '',
});
const dateRange = ref<string[]>([]);

function getQueryParams(extra: Partial<ReleasePlanFilterParams> = {}) {
  const [start, end] = dateRange.value || [];
  return {
    ...filters,
    release_date_start: start || filters.release_date_start || undefined,
    release_date_end: end || filters.release_date_end || undefined,
    ...extra,
  };
}

function applyFilter() {
  gridApi.reload();
}

function clearFilter(
  key:
    | 'branch_name'
    | 'keyword'
    | 'platform_keyword'
    | 'vehicle_keyword'
    | 'version_type',
) {
  filters[key] = undefined;
  gridApi.reload();
}

function clearDateFilter() {
  dateRange.value = [];
  gridApi.reload();
}

function formatProject(row: ReleasePlanItem) {
  const code = row.project_code ? ` / ${row.project_code}` : '';
  return `${row.project_name || '-'}${code}`;
}

function formatVehicles(row: ReleasePlanItem) {
  return (row.release_vehicles || []).join('、') || '-';
}

function formatManagers(row: ReleasePlanItem) {
  return (row.manager_names || []).join('、') || '-';
}

const [Grid, gridApi] = useZqTable({
  showSearchForm: false,
  gridOptions: {
    border: true,
    columns: useReleasePlanColumns(),
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [10, 20, 50, 100],
    },
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page }: ReleasePlanQueryParams) => {
          return await listReleasePlansApi({
            ...getQueryParams(),
            page: page.currentPage,
            pageSize: page.pageSize,
          });
        },
      },
    },
    stripe: true,
    toolbarConfig: {
      custom: true,
      refresh: true,
      zoom: true,
    },
  },
});
</script>

<template>
  <Page auto-content-height>
    <div class="release-plan-page flex h-full min-h-0 flex-col">
      <Grid class="release-plan-grid h-full">
        <template #header-project_name>
          <span class="filter-header">
            <span>项目</span>
            <ElPopover trigger="click" width="240">
              <template #reference>
                <ElButton link :class="{ active: filters.keyword }">
                  <ElIcon><Filter /></ElIcon>
                </ElButton>
              </template>
              <div class="filter-panel">
                <ElInput
                  v-model="filters.keyword"
                  placeholder="项目/编码/分支"
                  @keyup.enter="applyFilter"
                />
                <div class="filter-panel__footer">
                  <button
                    type="button"
                    class="filter-action"
                    @click="clearFilter('keyword')"
                  >
                    清空
                  </button>
                  <button
                    type="button"
                    class="filter-action is-primary"
                    @click="applyFilter"
                  >
                    应用
                  </button>
                </div>
              </div>
            </ElPopover>
          </span>
        </template>
        <template #header-branch_name>
          <span class="filter-header">
            <span>分支</span>
            <ElPopover trigger="click" width="220">
              <template #reference>
                <ElButton link :class="{ active: filters.branch_name }">
                  <ElIcon><Filter /></ElIcon>
                </ElButton>
              </template>
              <div class="filter-panel">
                <ElInput
                  v-model="filters.branch_name"
                  placeholder="分支名"
                  @keyup.enter="applyFilter"
                />
                <div class="filter-panel__footer">
                  <button
                    type="button"
                    class="filter-action"
                    @click="clearFilter('branch_name')"
                  >
                    清空
                  </button>
                  <button
                    type="button"
                    class="filter-action is-primary"
                    @click="applyFilter"
                  >
                    应用
                  </button>
                </div>
              </div>
            </ElPopover>
          </span>
        </template>
        <template #header-release_date>
          <span class="filter-header">
            <span>发布日期</span>
            <ElPopover trigger="click" width="300">
              <template #reference>
                <ElButton link :class="{ active: dateRange.length > 0 }">
                  <ElIcon><Filter /></ElIcon>
                </ElButton>
              </template>
              <div class="filter-panel">
                <ElDatePicker
                  v-model="dateRange"
                  type="daterange"
                  value-format="YYYY-MM-DD"
                  start-placeholder="开始日期"
                  end-placeholder="结束日期"
                  class="w-full"
                  @change="applyFilter"
                />
                <div class="filter-panel__footer">
                  <button
                    type="button"
                    class="filter-action"
                    @click="clearDateFilter"
                  >
                    清空
                  </button>
                  <button
                    type="button"
                    class="filter-action is-primary"
                    @click="applyFilter"
                  >
                    应用
                  </button>
                </div>
              </div>
            </ElPopover>
          </span>
        </template>
        <template #header-version_type>
          <span class="filter-header">
            <span>版本类型</span>
            <ElPopover trigger="click" width="220">
              <template #reference>
                <ElButton link :class="{ active: filters.version_type }">
                  <ElIcon><Filter /></ElIcon>
                </ElButton>
              </template>
              <div class="filter-panel">
                <ElSelect
                  v-model="filters.version_type"
                  allow-create
                  clearable
                  default-first-option
                  filterable
                  placeholder="版本类型"
                  @change="applyFilter"
                >
                  <ElOption
                    v-for="item in VERSION_TYPE_OPTIONS"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </ElSelect>
                <div class="filter-panel__footer">
                  <button
                    type="button"
                    class="filter-action"
                    @click="clearFilter('version_type')"
                  >
                    清空
                  </button>
                  <button
                    type="button"
                    class="filter-action is-primary"
                    @click="applyFilter"
                  >
                    应用
                  </button>
                </div>
              </div>
            </ElPopover>
          </span>
        </template>
        <template #header-platform_name>
          <span class="filter-header">
            <span>发布平台</span>
            <ElPopover trigger="click" width="220">
              <template #reference>
                <ElButton link :class="{ active: filters.platform_keyword }">
                  <ElIcon><Filter /></ElIcon>
                </ElButton>
              </template>
              <div class="filter-panel">
                <ElInput
                  v-model="filters.platform_keyword"
                  placeholder="平台关键字"
                  @keyup.enter="applyFilter"
                />
                <div class="filter-panel__footer">
                  <button
                    type="button"
                    class="filter-action"
                    @click="clearFilter('platform_keyword')"
                  >
                    清空
                  </button>
                  <button
                    type="button"
                    class="filter-action is-primary"
                    @click="applyFilter"
                  >
                    应用
                  </button>
                </div>
              </div>
            </ElPopover>
          </span>
        </template>
        <template #header-release_vehicles>
          <span class="filter-header">
            <span>发布车型</span>
            <ElPopover trigger="click" width="220">
              <template #reference>
                <ElButton link :class="{ active: filters.vehicle_keyword }">
                  <ElIcon><Filter /></ElIcon>
                </ElButton>
              </template>
              <div class="filter-panel">
                <ElInput
                  v-model="filters.vehicle_keyword"
                  placeholder="车型关键字"
                  @keyup.enter="applyFilter"
                />
                <div class="filter-panel__footer">
                  <button
                    type="button"
                    class="filter-action"
                    @click="clearFilter('vehicle_keyword')"
                  >
                    清空
                  </button>
                  <button
                    type="button"
                    class="filter-action is-primary"
                    @click="applyFilter"
                  >
                    应用
                  </button>
                </div>
              </div>
            </ElPopover>
          </span>
        </template>
        <template #cell-project_name="{ row }">
          {{ formatProject(row) }}
        </template>
        <template #cell-release_vehicles="{ row }">
          {{ formatVehicles(row) }}
        </template>
        <template #cell-manager_names="{ row }">
          {{ formatManagers(row) }}
        </template>
      </Grid>
    </div>
  </Page>
</template>

<style scoped>
.release-plan-grid :deep(.el-table .cell) {
  line-height: 18px;
  white-space: nowrap;
}

.filter-header {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.filter-header :deep(.el-button.active) {
  color: var(--el-color-primary);
}

.filter-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.filter-panel__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.filter-action {
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: var(--el-bg-color);
  color: var(--el-text-color-regular);
  cursor: pointer;
  font-size: 12px;
  line-height: 1;
  padding: 7px 11px;
}

.filter-action.is-primary {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary);
  color: #fff;
}
</style>
