<script setup lang="ts">
import type { RedisKey } from '#/api/core/redis-manager';

import { onMounted, ref, watch } from 'vue';

import { Edit, Trash2 } from '@vben/icons';

import {
  ElButton,
  ElEmpty,
  ElMessage,
  ElMessageBox,
  ElPagination,
  ElScrollbar,
  ElTag,
} from 'element-plus';

import {
  batchDeleteRedisKeysApi,
  deleteRedisKeyApi,
  searchRedisKeysApi,
} from '#/api/core/redis-manager';

interface Props {
  dbIndex: number;
  selectedKey?: string;
  searchPattern?: string;
  keyType?: string;
}

interface Emits {
  (e: 'select-key', key: string): void;
  (e: 'edit-key', key: string): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

// 搜索参数
const page = ref(1);
const pageSize = ref(20);

// 数据
const keys = ref<RedisKey[]>([]);
const total = ref(0);
const loading = ref(false);
const refreshing = ref(false);

// 选中的键（用于批量操作）
const selectedKeys = ref<string[]>([]);

// 刷新键列表
async function handleRefresh() {
  refreshing.value = true;
  try {
    await searchKeys();
  } finally {
    // 延迟一点时间，让动画更明显
    setTimeout(() => {
      refreshing.value = false;
    }, 500);
  }
}

// 搜索键
async function searchKeys() {
  try {
    loading.value = true;
    const response = await searchRedisKeysApi(props.dbIndex, {
      pattern: props.searchPattern || '*',
      key_type: props.keyType || undefined,
      page: page.value,
      page_size: pageSize.value,
    });
    keys.value = response.keys;
    total.value = response.total;
  } catch (error) {
    console.error('Failed to search keys:', error);
    ElMessage.error('搜索键失败');
  } finally {
    loading.value = false;
  }
}

// 选择键
function handleSelectKey(key: string) {
  emit('select-key', key);
}

// 编辑键
function handleEditKey(key: string) {
  emit('edit-key', key);
}

// 删除键
async function handleDeleteKey(key: string) {
  try {
    await ElMessageBox.confirm(`确定要删除键 "${key}" 吗？`, '确认删除', {
      type: 'warning',
    });

    await deleteRedisKeyApi(props.dbIndex, key);
    ElMessage.success('删除成功');
    searchKeys();
    
    // 如果删除的是当前选中的键，清空选中
    if (props.selectedKey === key) {
      emit('select-key', '');
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to delete key:', error);
      ElMessage.error('删除失败');
    }
  }
}

// 批量删除
async function handleBatchDelete() {
  if (selectedKeys.value.length === 0) {
    ElMessage.warning('请先选择要删除的键');
    return;
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedKeys.value.length} 个键吗？`,
      '确认批量删除',
      {
        type: 'warning',
      },
    );

    await batchDeleteRedisKeysApi(props.dbIndex, {
      keys: selectedKeys.value,
    });
    ElMessage.success('批量删除成功');
    selectedKeys.value = [];
    searchKeys();
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to batch delete keys:', error);
      ElMessage.error('批量删除失败');
    }
  }
}

// 格式化TTL
function formatTTL(ttl: number): string {
  if (ttl === -1) return '永不过期';
  if (ttl === -2) return '已过期';
  if (ttl < 60) return `${ttl}秒`;
  if (ttl < 3600) return `${Math.floor(ttl / 60)}分钟`;
  if (ttl < 86400) return `${Math.floor(ttl / 3600)}小时`;
  return `${Math.floor(ttl / 86400)}天`;
}

// 获取类型标签颜色
function getTypeTagColor(type: string): string {
  const colorMap: Record<string, string> = {
    string: 'success',
    list: 'warning',
    set: 'danger',
    zset: 'info',
    hash: 'primary',
  };
  return colorMap[type] || 'info';
}

// 监听数据库变化
watch(
  () => props.dbIndex,
  () => {
    page.value = 1;
    searchKeys();
  },
);

// 监听搜索条件变化
watch([() => props.searchPattern, () => props.keyType], () => {
  page.value = 1;
  searchKeys();
});

// 监听分页变化
watch([page, pageSize], () => {
  searchKeys();
});

onMounted(() => {
  searchKeys();
});

// 暴露给父组件
defineExpose({
  handleRefresh,
  refreshing,
});
</script>

<template>
  <div class="flex h-full flex-col">
    <!-- 批量操作 -->
    <div v-if="selectedKeys.length > 0" class="border-b p-3">
      <div class="flex items-center justify-between">
        <span class="text-sm text-gray-600">
          已选择 {{ selectedKeys.length }} 个键
        </span>
        <ElButton size="small" type="danger" @click="handleBatchDelete">
          批量删除
        </ElButton>
      </div>
    </div>

    <!-- 键列表 -->
    <ElScrollbar class="flex-1">
      <div v-if="loading" class="flex h-64 items-center justify-center">
        <span class="text-gray-400">加载中...</span>
      </div>

      <ElEmpty v-else-if="keys.length === 0" description="暂无数据" />

      <div v-else class="p-3">
        <div
          v-for="key in keys"
          :key="key.key"
          class="mb-2 cursor-pointer rounded-lg border p-3 transition-all hover:border-primary hover:shadow-sm"
          :class="
            selectedKey === key.key
              ? 'border-primary bg-primary/5'
              : 'border-gray-200 dark:border-gray-700'
          "
          @click="handleSelectKey(key.key)"
        >
          <div class="mb-2 flex items-start justify-between">
            <div class="flex-1">
              <div class="mb-1 flex items-center gap-2">
                <input
                  v-model="selectedKeys"
                  type="checkbox"
                  :value="key.key"
                  class="cursor-pointer"
                  @click.stop
                />
                <span class="font-mono text-sm font-semibold">{{ key.key }}</span>
              </div>
              <div class="flex items-center gap-2 text-xs text-gray-500">
                <ElTag :type="getTypeTagColor(key.type)" size="small">
                  {{ key.type }}
                </ElTag>
                <span>TTL: {{ formatTTL(key.ttl) }}</span>
                <span v-if="key.length">长度: {{ key.length }}</span>
                <span v-if="key.size">大小: {{ key.size }}B</span>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="flex gap-1">
              <button
                class="rounded p-1 text-blue-500 transition-colors hover:bg-blue-50"
                title="编辑"
                @click.stop="handleEditKey(key.key)"
              >
                <Edit :size="16" />
              </button>
              <button
                class="rounded p-1 text-red-500 transition-colors hover:bg-red-50"
                title="删除"
                @click.stop="handleDeleteKey(key.key)"
              >
                <Trash2 :size="16" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </ElScrollbar>

    <!-- 分页 -->
    <div v-if="total > 0" class="border-t p-4">
      <ElPagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        small
      />
    </div>
  </div>
</template>

<style scoped>
/* 自定义样式 */
</style>
