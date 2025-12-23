<script setup lang="ts">
import { ref, watch } from 'vue';
import { ElDescriptions, ElDescriptionsItem, ElDivider, ElSkeleton, ElMessage } from 'element-plus';
import { getDatabasesApi } from '#/api/core/database-manager';
import type { TreeNode } from '../index.vue';
import type { DatabaseInfo } from '#/api/core/database-manager';

interface Props {
  node: TreeNode;
}

const props = defineProps<Props>();

const loading = ref(false);
const databaseInfo = ref<DatabaseInfo | null>(null);

// 加载数据库信息
async function loadDatabaseInfo() {
  if (!props.node.meta?.dbName) {
    return;
  }

  loading.value = true;
  try {
    const databases = await getDatabasesApi(props.node.meta.dbName);
    databaseInfo.value = databases.find(
      (db) => db.name === props.node.meta?.database,
    ) || null;
  } catch (error) {
    console.error('Failed to load database info:', error);
    ElMessage.error('加载数据库信息失败');
  } finally {
    loading.value = false;
  }
}

// 格式化大小
function formatSize(bytes?: number) {
  if (!bytes) return '-';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`;
}

// 监听节点变化
watch(
  () => props.node,
  () => {
    loadDatabaseInfo();
  },
  { immediate: true },
);
</script>

<template>
  <div class="h-full space-y-6">
    <!-- 数据库基本信息 -->
    <div>
      <h3 class="mb-4 text-base font-semibold">数据库信息</h3>

      <ElSkeleton v-if="loading" :rows="5" animated />

      <ElDescriptions v-else-if="databaseInfo" :column="2" border>
        <ElDescriptionsItem label="数据库名称" :span="2">
          <span class="font-medium text-lg">{{ databaseInfo.name }}</span>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="所有者">
          {{ databaseInfo.owner || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="字符编码">
          {{ databaseInfo.encoding || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="排序规则">
          {{ databaseInfo.collation || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="表数量">
          <span class="font-medium text-primary">
            {{ databaseInfo.tables_count?.toLocaleString() || 0 }} 个
          </span>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="数据库大小" :span="2">
          <div class="flex items-center gap-2">
            <span class="font-medium">{{ databaseInfo.size || '-' }}</span>
            <span v-if="databaseInfo.size_bytes" class="text-sm text-gray-500">
              ({{ formatSize(databaseInfo.size_bytes) }})
            </span>
          </div>
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="databaseInfo.description" label="说明" :span="2">
          {{ databaseInfo.description }}
        </ElDescriptionsItem>
      </ElDescriptions>

      <div v-else class="text-center text-gray-400 py-8">
        未找到数据库信息
      </div>
    </div>

    <ElDivider />

    <!-- 快速操作 -->
    <div>
      <h3 class="mb-4 text-base font-semibold">快速操作</h3>
      <div class="space-y-3 text-sm">
        <div class="flex items-start gap-2">
          <span class="text-primary">📂</span>
          <div>
            <div class="font-medium">查看表列表</div>
            <div class="text-gray-500 text-xs mt-1">
              展开左侧树节点查看该数据库下的所有表
            </div>
          </div>
        </div>
        <div class="flex items-start gap-2">
          <span class="text-primary">🔍</span>
          <div>
            <div class="font-medium">搜索表</div>
            <div class="text-gray-500 text-xs mt-1">
              使用左侧搜索框快速查找表名
            </div>
          </div>
        </div>
        <div class="flex items-start gap-2">
          <span class="text-primary">⚡</span>
          <div>
            <div class="font-medium">执行SQL</div>
            <div class="text-gray-500 text-xs mt-1">
              选择任意表后切换到"SQL执行"标签页
            </div>
          </div>
        </div>
      </div>
    </div>

    <ElDivider />

    <!-- 统计信息 -->
    <div v-if="databaseInfo">
      <h3 class="mb-4 text-base font-semibold">统计信息</h3>
      <div class="grid grid-cols-2 gap-4">
        <div class="text-center p-4 bg-blue-50 rounded-lg">
          <div class="text-2xl font-bold text-blue-600">
            {{ databaseInfo.tables_count?.toLocaleString() || 0 }}
          </div>
          <div class="text-sm text-gray-600 mt-1">表数量</div>
        </div>
        <div class="text-center p-4 bg-green-50 rounded-lg">
          <div class="text-2xl font-bold text-green-600">
            {{ databaseInfo.size || '-' }}
          </div>
          <div class="text-sm text-gray-600 mt-1">数据库大小</div>
        </div>
      </div>
    </div>
  </div>
</template>
