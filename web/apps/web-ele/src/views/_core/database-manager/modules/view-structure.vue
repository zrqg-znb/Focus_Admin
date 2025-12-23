<script setup lang="ts">
import { ref, watch } from 'vue';
import {
  ElCard,
  ElDescriptions,
  ElDescriptionsItem,
  ElTable,
  ElTableColumn,
  ElTag,
  ElMessage,
  ElButton,
  ElEmpty,
} from 'element-plus';
import { Copy, Eye, Database, Table, FileText } from '@vben/icons';
import { getViewStructureApi } from '#/api/core/database-manager';
import type { TreeNode } from '../index.vue';

interface Props {
  node: TreeNode;
}

const props = defineProps<Props>();

const loading = ref(false);
const viewStructure = ref<any>(null);

// 加载视图结构
async function loadViewStructure() {
  const viewName = (props.node.meta as any)?.view;
  if (!props.node.meta?.dbName || !viewName) {
    return;
  }

  loading.value = true;
  try {
    const data = await getViewStructureApi(
      props.node.meta.dbName,
      viewName,
      props.node.meta.schema,
    );
    viewStructure.value = data;
  } catch (error) {
    console.error('Failed to load view structure:', error);
    ElMessage.error('加载视图结构失败');
  } finally {
    loading.value = false;
  }
}

// 复制定义SQL
function copyDefinition() {
  if (viewStructure.value?.definition_sql) {
    navigator.clipboard.writeText(viewStructure.value.definition_sql);
    ElMessage.success('已复制到剪贴板');
  }
}

// 监听节点变化
watch(
  () => props.node,
  () => {
    loadViewStructure();
  },
  { immediate: true },
);
</script>

<template>
  <div class="h-full flex flex-col gap-4 overflow-auto p-4">
    <!-- 视图基本信息 -->
    <ElCard shadow="never" v-loading="loading">
      <template #header>
        <div class="flex items-center gap-2">
          <Eye :size="20" class="text-blue-500" />
          <span class="font-semibold">视图信息</span>
        </div>
      </template>

      <ElDescriptions v-if="viewStructure" :column="2" border>
        <ElDescriptionsItem label="视图名称">
          <span class="font-medium">{{ viewStructure.view_info.view_name }}</span>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="Schema">
          {{ viewStructure.view_info.schema_name || 'N/A' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="视图类型">
          <ElTag 
            :type="viewStructure.view_info.view_type === 'MATERIALIZED VIEW' ? 'warning' : 'primary'" 
            size="small"
          >
            {{ viewStructure.view_info.view_type === 'MATERIALIZED VIEW' ? '物化视图' : '普通视图' }}
          </ElTag>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="是否可更新">
          <ElTag :type="viewStructure.view_info.is_updatable ? 'success' : 'info'" size="small">
            {{ viewStructure.view_info.is_updatable ? '是' : '否' }}
          </ElTag>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="CHECK OPTION" v-if="viewStructure.view_info.view_type !== 'MATERIALIZED VIEW'">
          {{ viewStructure.view_info.check_option || 'NONE' }}
        </ElDescriptionsItem>
      </ElDescriptions>

      <ElEmpty v-else description="暂无数据" />
    </ElCard>

    <!-- 列信息 -->
    <ElCard shadow="never">
      <template #header>
        <div class="flex items-center gap-2">
          <Database :size="18" class="text-green-500" />
          <span class="font-semibold">列信息 ({{ viewStructure?.columns?.length || 0 }})</span>
        </div>
      </template>

      <ElTable
        v-if="viewStructure?.columns"
        :data="viewStructure.columns"
        border
        stripe
        max-height="300"
      >
        <ElTableColumn prop="column_name" label="列名" width="200" />
        <ElTableColumn prop="data_type" label="数据类型" width="150" />
        <ElTableColumn prop="is_nullable" label="可空" width="80" align="center">
          <template #default="{ row }">
            <ElTag :type="row.is_nullable ? 'info' : 'warning'" size="small">
              {{ row.is_nullable ? '是' : '否' }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="ordinal_position" label="位置" width="80" align="center" />
        <ElTableColumn prop="description" label="说明" min-width="200" show-overflow-tooltip />
      </ElTable>

      <ElEmpty v-else description="暂无列信息" />
    </ElCard>

    <!-- 依赖的表 -->
    <ElCard shadow="never">
      <template #header>
        <div class="flex items-center gap-2">
          <Table :size="18" class="text-orange-500" />
          <span class="font-semibold">依赖的表 ({{ viewStructure?.dependencies?.length || 0 }})</span>
        </div>
      </template>

      <div v-if="viewStructure?.dependencies && viewStructure.dependencies.length > 0" class="flex flex-wrap gap-2">
        <ElTag
          v-for="table in viewStructure.dependencies"
          :key="table"
          type="info"
          size="large"
        >
          <Table :size="14" class="mr-1" />
          {{ table }}
        </ElTag>
      </div>

      <ElEmpty v-else description="无依赖表" :image-size="60" />
    </ElCard>

    <!-- 视图定义SQL -->
    <ElCard shadow="never" class="flex-1">
      <template #header>
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-2">
            <FileText :size="18" class="text-purple-500" />
            <span class="font-semibold">视图定义</span>
          </div>
          <ElButton
            size="small"
            @click="copyDefinition"
            :disabled="!viewStructure?.definition_sql"
          >
            <Copy :size="14" />
            <span class="ml-1">复制</span>
          </ElButton>
        </div>
      </template>

      <pre
        v-if="viewStructure?.definition_sql"
        class="bg-gray-50 p-4 rounded text-sm overflow-auto max-h-96 leading-relaxed font-mono"
      >{{ viewStructure.definition_sql }}</pre>

      <ElEmpty v-else description="暂无定义" />
    </ElCard>

    <!-- 说明 -->
    <ElCard shadow="never">
      <template #header>
        <span class="font-semibold">说明</span>
      </template>
      <div class="text-sm text-gray-600 space-y-2">
        <p>
          <strong>视图（View）</strong> 是基于一个或多个表的虚拟表，不存储实际数据。
        </p>
        <ul class="list-disc list-inside space-y-1 ml-2">
          <li>视图可以简化复杂查询，提高数据安全性</li>
          <li>可更新视图允许通过视图修改基础表数据</li>
          <li>视图依赖的表被修改时，视图结构会自动更新</li>
          <li>删除视图不会影响基础表的数据</li>
        </ul>
      </div>
    </ElCard>
  </div>
</template>

<style scoped>
pre {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
