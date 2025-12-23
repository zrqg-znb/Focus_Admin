<script setup lang="ts">
import { ref, watch } from 'vue';
import { ElDescriptions, ElDescriptionsItem, ElMessage, ElButton, ElTag, ElTabs, ElTabPane, ElDivider } from 'element-plus';
import { Copy, Database, Table, Eye } from '@vben/icons';
import { getTablesApi, getViewsApi } from '#/api/core/database-manager';
import type { TreeNode } from '../index.vue';

interface Props {
  node: TreeNode;
}

const props = defineProps<Props>();

const loading = ref(false);
const tableCount = ref(0);
const viewCount = ref(0);
const tableList = ref<any[]>([]);
const viewList = ref<any[]>([]);

// 加载Schema信息
async function loadSchemaInfo() {
  if (!props.node.meta?.dbName || !props.node.meta?.schema) {
    return;
  }

  loading.value = true;
  try {
    // 同时获取该Schema下的所有表和视图
    const [tables, views] = await Promise.all([
      getTablesApi(props.node.meta.dbName, props.node.meta.database, props.node.meta.schema),
      getViewsApi(props.node.meta.dbName, props.node.meta.database, props.node.meta.schema),
    ]);
    tableList.value = tables;
    tableCount.value = tables.length;
    viewList.value = views;
    viewCount.value = views.length;
  } catch (error) {
    console.error('Failed to load schema info:', error);
    ElMessage.error('加载Schema信息失败');
  } finally {
    loading.value = false;
  }
}

// 复制Schema名称
function copySchemaName() {
  if (props.node.meta?.schema) {
    navigator.clipboard.writeText(props.node.meta.schema);
    ElMessage.success('已复制到剪贴板');
  }
}

// 监听节点变化
watch(
  () => props.node,
  () => {
    loadSchemaInfo();
  },
  { immediate: true },
);
</script>

<template>
  <div class="h-full space-y-6" v-loading="loading">
    <!-- Schema基本信息 -->
    <div>
      <div class="mb-4 flex justify-between items-center">
        <div class="flex items-center gap-2">
          <Database :size="20" class="text-blue-500" />
          <h3 class="text-base font-semibold">Schema 信息</h3>
        </div>
        <ElButton size="small" @click="copySchemaName">
          <Copy :size="14" />
          <span class="ml-1">复制名称</span>
        </ElButton>
      </div>

      <ElDescriptions :column="2" border>
        <ElDescriptionsItem label="Schema名称">
          <span class="font-medium">{{ node.meta?.schema }}</span>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="数据库">
          {{ node.meta?.database }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="数据库类型">
          <ElTag :type="node.meta?.dbType === 'postgresql' ? 'primary' : 'warning'">
            {{ node.meta?.dbType?.toUpperCase() }}
          </ElTag>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="对象统计">
          <div class="flex items-center gap-4">
            <div class="flex items-center gap-1">
              <Table :size="16" />
              <span class="font-semibold text-blue-600">{{ tableCount }}</span>
              <span class="text-xs text-gray-500">表</span>
            </div>
            <div class="flex items-center gap-1">
              <Eye :size="16" />
              <span class="font-semibold text-green-600">{{ viewCount }}</span>
              <span class="text-xs text-gray-500">视图</span>
            </div>
          </div>
        </ElDescriptionsItem>
      </ElDescriptions>
    </div>

    <ElDivider />

    <!-- 表和视图列表 -->
    <div class="flex-1">
      <div class="mb-4 flex items-center gap-2">
        <Database :size="18" class="text-green-500" />
        <h3 class="text-base font-semibold">数据库对象</h3>
      </div>

      <ElTabs>
        <!-- 表列表 -->
        <ElTabPane>
          <template #label>
            <div class="flex items-center gap-2">
              <Table :size="16" />
              <span>表 ({{ tableCount }})</span>
            </div>
          </template>

          <div v-if="tableList.length === 0" class="text-center text-gray-400 py-8">
            该Schema下暂无表
          </div>

          <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div
              v-for="table in tableList"
              :key="table.table_name"
              class="p-3 border rounded-lg hover:border-blue-400 hover:shadow-sm transition-all cursor-pointer"
            >
              <div class="flex items-start gap-2">
                <Table :size="16" class="text-gray-500 mt-1" />
                <div class="flex-1 min-w-0">
                  <div class="font-medium text-sm truncate" :title="table.table_name">
                    {{ table.table_name }}
                  </div>
                  <div v-if="table.description" class="text-xs text-gray-500 mt-1 truncate">
                    {{ table.description }}
                  </div>
                  <div class="flex gap-2 mt-2 text-xs text-gray-400">
                    <span v-if="table.row_count !== undefined">
                      {{ table.row_count?.toLocaleString() }} 行
                    </span>
                    <span v-if="table.total_size">
                      {{ table.total_size }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </ElTabPane>

        <!-- 视图列表 -->
        <ElTabPane>
          <template #label>
            <div class="flex items-center gap-2">
              <Eye :size="16" />
              <span>视图 ({{ viewCount }})</span>
            </div>
          </template>

          <div v-if="viewList.length === 0" class="text-center text-gray-400 py-8">
            该Schema下暂无视图
          </div>

          <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div
              v-for="view in viewList"
              :key="view.view_name"
              class="p-3 border rounded-lg hover:border-green-400 hover:shadow-sm transition-all cursor-pointer"
            >
              <div class="flex items-start gap-2">
                <Eye :size="16" class="text-green-500 mt-1" />
                <div class="flex-1 min-w-0">
                  <div class="font-medium text-sm truncate" :title="view.view_name">
                    {{ view.view_name }}
                  </div>
                  <div v-if="view.description" class="text-xs text-gray-500 mt-1 truncate">
                    {{ view.description }}
                  </div>
                  <div class="flex gap-2 mt-2 text-xs">
                    <ElTag v-if="view.view_type === 'MATERIALIZED VIEW'" type="warning" size="small">
                      物化视图
                    </ElTag>
                    <ElTag v-else-if="view.is_updatable" type="success" size="small">可更新</ElTag>
                    <ElTag v-else type="info" size="small">只读</ElTag>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </ElTabPane>
      </ElTabs>
    </div>

    <ElDivider />

    <!-- Schema说明 -->
    <div>
      <h3 class="mb-4 text-base font-semibold">说明</h3>
      <div class="text-sm text-gray-600 space-y-2">
        <p>
          <strong>Schema</strong> 是数据库对象的逻辑容器，用于组织和管理表、视图、函数等对象。
        </p>
        <ul class="list-disc list-inside space-y-1 ml-2">
          <li>PostgreSQL: 每个数据库可以包含多个Schema，默认Schema为 <code class="px-1 bg-gray-100 rounded">public</code></li>
          <li>SQL Server: 使用Schema来组织数据库对象，默认Schema为 <code class="px-1 bg-gray-100 rounded">dbo</code></li>
          <li>MySQL: 不支持Schema概念，数据库即为最高层级容器</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
code {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 0.9em;
}
</style>
