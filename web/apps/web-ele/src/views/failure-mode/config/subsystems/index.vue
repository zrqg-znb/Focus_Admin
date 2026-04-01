<script lang="ts" setup>
import type { FailureModeSubsystemConfigItem } from '#/api/failure_mode';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  ElButton,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElTooltip,
} from 'element-plus';

import {
  deleteFailureModeSubsystemConfigApi,
  listFailureModeSubsystemConfigsApi,
} from '#/api/failure_mode';
import { useZqTable } from '#/components/zq-table';

import SubsystemConfigDrawer from '../../components/SubsystemConfigDrawer.vue';
import { formatTextList, useSubsystemConfigColumns } from '../../data';

defineOptions({ name: 'FailureModeSubsystemConfigPage' });

interface GridQueryContext {
  page: {
    currentPage: number;
    pageSize: number;
  };
}

const drawerRef = ref<InstanceType<typeof SubsystemConfigDrawer>>();
const filters = reactive({ keyword: '' });

const [SubsystemConfigGrid, subsystemConfigGridApi] =
  useZqTable<FailureModeSubsystemConfigItem>({
    gridOptions: {
      border: true,
      columns:
        useSubsystemConfigColumns() as ZqTableGridOptions<FailureModeSubsystemConfigItem>['columns'],
      proxyConfig: {
        autoLoad: true,
        ajax: {
          query: async ({ page }: GridQueryContext) => {
            const response = await listFailureModeSubsystemConfigsApi({
              keyword: filters.keyword.trim() || undefined,
              page: page.currentPage,
              pageSize: page.pageSize,
            });
            return {
              items: response.items || [],
              total: response.total || 0,
            };
          },
        },
      },
      rowKey: 'id',
      stripe: true,
      toolbarConfig: {
        custom: true,
        refresh: true,
        search: false,
        zoom: true,
      },
      pagerConfig: {
        enabled: true,
        pageSize: 10,
        pageSizes: [10, 20, 50],
      },
    },
  });

async function handleSearch() {
  subsystemConfigGridApi.pagination.currentPage = 1;
  await subsystemConfigGridApi.query();
}

function handleReset() {
  filters.keyword = '';
  void handleSearch();
}

async function handleDelete(row: FailureModeSubsystemConfigItem) {
  try {
    await ElMessageBox.confirm('确认删除该子系统配置吗？', '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    });
    await deleteFailureModeSubsystemConfigApi(row.id);
    ElMessage.success('删除成功');
    await handleSearch();
  } catch (error) {
    if (error !== 'cancel') {
      throw error;
    }
  }
}

function handleSaved() {
  void handleSearch();
}
</script>

<template>
  <Page content-class="flex h-full min-h-0 flex-col" auto-content-height>
    <SubsystemConfigDrawer ref="drawerRef" @success="handleSaved" />

    <div class="flex min-h-0 flex-1 flex-col gap-4">
      <div class="rounded-xl bg-white p-4 shadow-sm">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div class="text-xl font-semibold text-gray-900">子系统配置</div>
            <div class="mt-1 text-sm text-gray-500">
              统一维护子系统、模块与芯片联动配置，供故障模式与工作流页面复用
            </div>
          </div>
          <ElButton type="primary" @click="drawerRef?.openCreate()">
            新增子系统配置
          </ElButton>
        </div>

        <div class="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1fr)_140px]">
          <ElInput
            v-model="filters.keyword"
            clearable
            placeholder="搜索子系统 / 模块 / 芯片"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
          <div class="flex items-center justify-end gap-2">
            <ElButton @click="handleReset">重置</ElButton>
            <ElButton type="primary" plain @click="handleSearch">查询</ElButton>
          </div>
        </div>
      </div>

      <div
        class="min-h-0 flex-1 overflow-hidden rounded-xl bg-white p-4 shadow-sm"
      >
        <SubsystemConfigGrid class="h-full">
          <template #cell-module_options="{ row }">
            {{ formatTextList(row.module_options) || '-' }}
          </template>
          <template #cell-chip_options="{ row }">
            {{ formatTextList(row.chip_options) || '-' }}
          </template>
          <template #cell-actions="{ row }">
            <div class="flex justify-center gap-1">
              <ElTooltip content="编辑" placement="top">
                <ElButton
                  circle
                  link
                  size="small"
                  type="primary"
                  @click="drawerRef?.openEdit(row.id)"
                >
                  <IconifyIcon icon="ep:edit" />
                </ElButton>
              </ElTooltip>
              <ElTooltip content="删除" placement="top">
                <ElButton
                  circle
                  link
                  size="small"
                  type="danger"
                  @click="handleDelete(row)"
                >
                  <IconifyIcon icon="ep:delete" />
                </ElButton>
              </ElTooltip>
            </div>
          </template>
        </SubsystemConfigGrid>
      </div>
    </div>
  </Page>
</template>
