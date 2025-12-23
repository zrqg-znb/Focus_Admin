<script setup lang="ts">
import { ref, watch } from 'vue';
import {
  ElCard,
  ElTable,
  ElTableColumn,
  ElPagination,
  ElInput,
  ElButton,
  ElMessage,
} from 'element-plus';
import { Search, RotateCw } from '@vben/icons';
import { queryTableDataApi } from '#/api/core/database-manager';
import type { TreeNode } from '../index.vue';
import type { QueryDataResponse } from '#/api/core/database-manager';

interface Props {
  node: TreeNode;
}

const props = defineProps<Props>();

const loading = ref(false);
const tableData = ref<QueryDataResponse | null>(null);
const page = ref(1);
const pageSize = ref(50);
const whereCondition = ref('');
const orderBy = ref('');

// 加载表数据
async function loadTableData() {
  if (!props.node.meta?.dbName || !props.node.meta?.table) {
    return;
  }

  loading.value = true;
  try {
    const data = await queryTableDataApi(props.node.meta.dbName, {
      table_name: props.node.meta.table,
      schema_name: props.node.meta.schema,
      page: page.value,
      page_size: pageSize.value,
      where: whereCondition.value || undefined,
      order_by: orderBy.value || undefined,
    });
    tableData.value = data;
  } catch (error) {
    console.error('Failed to load table data:', error);
    ElMessage.error('加载表数据失败');
  } finally {
    loading.value = false;
  }
}

// 处理分页变化
function handlePageChange(newPage: number) {
  page.value = newPage;
  loadTableData();
}

// 处理每页大小变化
function handleSizeChange(newSize: number) {
  pageSize.value = newSize;
  page.value = 1;
  loadTableData();
}

// 刷新
function handleRefresh() {
  page.value = 1;
  loadTableData();
}

// 监听节点变化
watch(
  () => props.node,
  () => {
    page.value = 1;
    whereCondition.value = '';
    orderBy.value = '';
    loadTableData();
  },
  { immediate: true },
);
</script>

<template>
  <div class="h-full flex flex-col gap-3">
    <!-- 查询条件 -->
    <ElCard shadow="never">
      <div class="flex gap-3 items-center">
        <div class="flex-1">
          <ElInput
            v-model="whereCondition"
            placeholder="WHERE 条件 (例: id > 100 AND status = 'active')"
            clearable
            @keyup.enter="handleRefresh"
          >
            <template #prefix>
              <Search :size="16" />
            </template>
          </ElInput>
        </div>
        <div class="w-64">
          <ElInput
            v-model="orderBy"
            placeholder="ORDER BY (例: id DESC)"
            clearable
            @keyup.enter="handleRefresh"
          />
        </div>
        <ElButton type="primary" @click="handleRefresh" :loading="loading">
          <RotateCw :size="16" :class="{ 'animate-spin': loading }" />
          <span class="ml-1">查询</span>
        </ElButton>
      </div>
    </ElCard>

    <!-- 数据表格 -->
    <ElCard shadow="never" class="flex-1" :body-style="{ padding: '12px', height: '100%' }">
      <ElTable
        :data="tableData?.rows || []"
        v-loading="loading"
        stripe
        border
        height="100%"
        style="width: 100%"
      >
        <ElTableColumn
          v-for="column in tableData?.columns || []"
          :key="column"
          :prop="column"
          :label="column"
          min-width="120"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span v-if="row[column] === null" class="text-gray-400 italic">NULL</span>
            <span v-else>{{ row[column] }}</span>
          </template>
        </ElTableColumn>
        <template #empty>
          <div class="text-gray-400">暂无数据</div>
        </template>
      </ElTable>
    </ElCard>

    <!-- 分页 -->
    <div class="flex justify-between items-center">
      <div class="text-sm text-gray-500">
        共 {{ tableData?.total?.toLocaleString() || 0 }} 条记录
      </div>
      <ElPagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100, 200]"
        :total="tableData?.total || 0"
        layout="sizes, prev, pager, next, jumper"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>
  </div>
</template>
