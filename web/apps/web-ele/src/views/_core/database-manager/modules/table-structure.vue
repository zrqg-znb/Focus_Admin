<script setup lang="ts">
import { ref, watch } from 'vue';
import { ElTable, ElTableColumn, ElTag, ElMessage, ElButton, ElDivider } from 'element-plus';
import { Copy } from '@vben/icons';
import { getTableStructureApi, getTableDDLApi } from '#/api/core/database-manager';
import type { TreeNode } from '../index.vue';
import type { TableStructure } from '#/api/core/database-manager';

interface Props {
  node: TreeNode;
}

const props = defineProps<Props>();

const loading = ref(false);
const loadingDDL = ref(false);
const tableStructure = ref<TableStructure | null>(null);
const ddlStatement = ref('');

// 加载DDL语句
async function loadTableDDL() {
  if (!props.node.meta?.dbName || !props.node.meta?.table) {
    return;
  }

  loadingDDL.value = true;
  try {
    const data = await getTableDDLApi(
      props.node.meta.dbName,
      props.node.meta.table,
      props.node.meta.database,
      props.node.meta.schema,
    );
    ddlStatement.value = data.ddl;
  } catch (error) {
    console.error('Failed to load table DDL:', error);
    ElMessage.error('加载DDL语句失败');
    ddlStatement.value = '-- 加载DDL失败，请检查数据库连接';
  } finally {
    loadingDDL.value = false;
  }
}

// 复制DDL
function copyDDL() {
  if (ddlStatement.value) {
    navigator.clipboard.writeText(ddlStatement.value);
    ElMessage.success('已复制到剪贴板');
  }
}

// 加载表结构
async function loadTableStructure() {
  if (!props.node.meta?.dbName || !props.node.meta?.table) {
    return;
  }

  loading.value = true;
  try {
    const data = await getTableStructureApi(
      props.node.meta.dbName,
      props.node.meta.table,
      props.node.meta.database,
      props.node.meta.schema,
    );
    tableStructure.value = data;
  } catch (error) {
    console.error('Failed to load table structure:', error);
    ElMessage.error('加载表结构失败');
  } finally {
    loading.value = false;
  }
}

// 监听节点变化
watch(
  () => props.node,
  () => {
    loadTableStructure();
    loadTableDDL();
  },
  { immediate: true },
);
</script>

<template>
  <div class="h-full space-y-6">
    <!-- 表信息 -->
    <div v-if="tableStructure">
      <h3 class="mb-4 text-base font-semibold">表信息</h3>
      <div class="grid grid-cols-2 gap-4 text-sm rounded-lg border p-4">
        <div class="flex justify-between">
          <span class="text-gray-500">表名:</span>
          <span class="font-medium">{{ tableStructure.table_info.table_name }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-gray-500">类型:</span>
          <span>{{ tableStructure.table_info.table_type || 'TABLE' }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-gray-500">行数:</span>
          <span>{{ tableStructure.table_info.row_count?.toLocaleString() || '-' }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-gray-500">大小:</span>
          <span>{{ tableStructure.table_info.total_size || '-' }}</span>
        </div>
      </div>
    </div>

    <ElDivider />

    <!-- 字段列表 -->
    <div class="flex-1">
      <h3 class="mb-4 text-base font-semibold">字段 ({{ tableStructure?.columns.length || 0 }})</h3>
      <ElTable
        :data="tableStructure?.columns || []"
        v-loading="loading"
        stripe
        border
        height="300"
      >
        <ElTableColumn prop="column_name" label="字段名" width="150" />
        <ElTableColumn prop="data_type" label="数据类型" width="120" />
        <ElTableColumn label="可空" width="80" align="center">
          <template #default="{ row }">
            <ElTag :type="row.is_nullable ? 'info' : 'success'" size="small">
              {{ row.is_nullable ? 'YES' : 'NO' }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="column_default" label="默认值" width="120" />
        <ElTableColumn label="主键" width="80" align="center">
          <template #default="{ row }">
            <ElTag v-if="row.is_primary_key" type="danger" size="small">PK</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="唯一" width="80" align="center">
          <template #default="{ row }">
            <ElTag v-if="row.is_unique" type="warning" size="small">UQ</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="description" label="说明" min-width="150" show-overflow-tooltip />
      </ElTable>
    </div>

    <ElDivider />

    <!-- DDL语句 -->
    <div v-loading="loadingDDL">
      <div class="mb-4 flex justify-between items-center">
        <h3 class="text-base font-semibold">DDL语句</h3>
        <ElButton size="small" @click="copyDDL" :disabled="!ddlStatement">
          <Copy :size="14" />
          <span class="ml-1">复制</span>
        </ElButton>
      </div>
      <pre class="bg-gray-50 p-4 rounded-lg border text-sm overflow-auto max-h-96 leading-relaxed font-mono">{{ ddlStatement || '-- 加载中...' }}</pre>
    </div>

    <ElDivider />

    <!-- 索引列表 -->
    <div>
      <h3 class="mb-4 text-base font-semibold">索引 ({{ tableStructure?.indexes.length || 0 }})</h3>
      <ElTable
        :data="tableStructure?.indexes || []"
        v-loading="loading"
        stripe
        border
        max-height="200"
      >
        <ElTableColumn prop="index_name" label="索引名" width="180" />
        <ElTableColumn prop="index_type" label="类型" width="100" />
        <ElTableColumn prop="columns" label="字段" min-width="150" />
        <ElTableColumn label="唯一" width="80" align="center">
          <template #default="{ row }">
            <ElTag v-if="row.is_unique" type="warning" size="small">UQ</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="主键" width="80" align="center">
          <template #default="{ row }">
            <ElTag v-if="row.is_primary" type="danger" size="small">PK</ElTag>
          </template>
        </ElTableColumn>
      </ElTable>
    </div>

    <ElDivider />

    <!-- 约束列表 -->
    <div>
      <h3 class="mb-4 text-base font-semibold">约束 ({{ tableStructure?.constraints.length || 0 }})</h3>
      <ElTable
        :data="tableStructure?.constraints || []"
        v-loading="loading"
        stripe
        border
        max-height="200"
      >
        <ElTableColumn prop="constraint_name" label="约束名" width="180" />
        <ElTableColumn prop="constraint_type" label="类型" width="120" />
        <ElTableColumn prop="columns" label="字段" width="150" />
        <ElTableColumn prop="definition" label="定义" min-width="200" show-overflow-tooltip />
      </ElTable>
    </div>
  </div>
</template>
