<script setup lang="ts">
import type { TreeNode } from '../index.vue';

import { ref, watch } from 'vue';

import { RotateCw } from '@vben/icons';

import {
  ElButton,
  ElDescriptions,
  ElDescriptionsItem,
  ElDivider,
  ElMessage,
  ElTag,
} from 'element-plus';

import { testDatabaseConnectionApi } from '#/api/core/database-manager';

interface Props {
  node: TreeNode;
}

const props = defineProps<Props>();

const testing = ref(false);
const connectionStatus = ref<{
  message: string;
  success: boolean;
  tested: boolean;
}>({
  success: false,
  message: '',
  tested: false,
});

// 测试连接
async function testConnection() {
  if (!props.node.meta?.dbName) {
    return;
  }

  testing.value = true;
  try {
    const result = await testDatabaseConnectionApi(props.node.meta.dbName);
    connectionStatus.value = {
      success: result.success,
      message: result.message,
      tested: true,
    };

    if (result.success) {
      ElMessage.success('连接测试成功');
    } else {
      ElMessage.error('连接测试失败');
    }
  } catch (error: any) {
    connectionStatus.value = {
      success: false,
      message: error.message || '连接失败',
      tested: true,
    };
    ElMessage.error('连接测试失败');
  } finally {
    testing.value = false;
  }
}

// 监听节点变化，重置状态
watch(
  () => props.node,
  () => {
    connectionStatus.value.tested = false;
  },
);
</script>

<script lang="ts">
// 获取数据库类型颜色
function getDbTypeColor(dbType?: string) {
  const type = dbType?.toLowerCase();
  switch (type) {
    case 'mysql': {
      return 'warning';
    }
    case 'postgresql': {
      return 'primary';
    }
    case 'sqlserver': {
      return 'danger';
    }
    default: {
      return 'info';
    }
  }
}
</script>

<template>
  <div class="h-full space-y-6">
    <!-- 连接信息 -->
    <div>
      <div class="mb-4 flex items-center justify-between">
        <h3 class="text-base font-semibold">连接信息</h3>
        <ElButton size="small" :loading="testing" @click="testConnection">
          <RotateCw :size="14" :class="{ 'animate-spin': testing }" />
          <span class="ml-1">测试连接</span>
        </ElButton>
      </div>

      <ElDescriptions :column="2" border>
        <ElDescriptionsItem label="连接名称">
          {{ node.label }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="数据库类型">
          <ElTag :type="getDbTypeColor(node.meta?.dbType)">
            {{ node.meta?.dbType?.toUpperCase() }}
          </ElTag>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="连接标识">
          {{ node.meta?.dbName }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="连接状态">
          <ElTag
            v-if="connectionStatus.tested"
            :type="connectionStatus.success ? 'success' : 'danger'"
          >
            {{ connectionStatus.success ? '✓ 连接成功' : '✗ 连接失败' }}
          </ElTag>
          <span v-else class="text-gray-400">未测试</span>
        </ElDescriptionsItem>
      </ElDescriptions>

      <!-- 连接测试结果 -->
      <div v-if="connectionStatus.tested" class="mt-4">
        <div class="mb-2 text-sm font-medium">测试结果：</div>
        <div
          class="rounded-lg border p-3 text-sm"
          :class="
            connectionStatus.success
              ? 'border-green-200 bg-green-50 text-green-700'
              : 'border-red-200 bg-red-50 text-red-700'
          "
        >
          {{ connectionStatus.message }}
        </div>
      </div>
    </div>

    <ElDivider />

    <!-- 使用说明 -->
    <div>
      <h3 class="mb-4 text-base font-semibold">使用说明</h3>
      <div class="space-y-2 text-sm text-gray-600">
        <div><strong>· 展开连接</strong> - 查看该连接下的所有数据库</div>
        <div><strong>· 选择数据库</strong> - 查看数据库详细信息</div>
        <div><strong>· 选择表</strong> - 查看表结构、查询数据、执行SQL</div>
        <div><strong>· 搜索功能</strong> - 在左侧树中快速查找数据库或表</div>
      </div>
    </div>

    <ElDivider />

    <!-- 快捷操作 -->
    <div>
      <h3 class="mb-4 text-base font-semibold">快捷操作</h3>
      <div class="space-y-2">
        <ElButton
          type="primary"
          size="small"
          class="w-full"
          @click="testConnection"
        >
          测试数据库连接
        </ElButton>
        <div class="mt-2 text-xs text-gray-500">
          💡 提示：点击左侧树节点展开查看更多内容
        </div>
      </div>
    </div>
  </div>
</template>
