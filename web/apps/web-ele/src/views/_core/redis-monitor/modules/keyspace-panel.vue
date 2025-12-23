<script setup lang="ts">
import type {
  RedisMonitorOverview,
  RedisRealtimeStats,
} from '#/api/core/redis-monitor';

import { computed } from 'vue';

import { Activity, Database, Key } from '@vben/icons';

import { ElCard, ElEmpty, ElProgress, ElTag } from 'element-plus';

defineOptions({ name: 'KeyspacePanel' });

const props = defineProps<{
  monitorData: RedisMonitorOverview | null;
  realtimeData: RedisRealtimeStats | null;
}>();

// 键空间列表
const keyspaces = computed(() => props.monitorData?.keyspace || []);

// 总键数
const totalKeys = computed(() => {
  return keyspaces.value.reduce((sum, db) => sum + db.keys, 0);
});

// 总过期键数
const totalExpires = computed(() => {
  return keyspaces.value.reduce((sum, db) => sum + db.expires, 0);
});

// 平均TTL
const avgTTL = computed(() => {
  if (keyspaces.value.length === 0) return 0;
  const totalTTL = keyspaces.value.reduce((sum, db) => sum + db.avg_ttl, 0);
  return Math.round(totalTTL / keyspaces.value.length);
});

// 格式化时间（毫秒转为可读格式）
function formatTTL(ms: number): string {
  if (ms === 0) return '永久';
  if (ms < 1000) return `${ms}毫秒`;
  if (ms < 60000) return `${Math.floor(ms / 1000)}秒`;
  if (ms < 3600000) return `${Math.floor(ms / 60000)}分钟`;
  if (ms < 86400000) return `${Math.floor(ms / 3600000)}小时`;
  return `${Math.floor(ms / 86400000)}天`;
}

// 获取过期率颜色
function getExpireRateColor(
  expires: number,
  total: number,
): 'danger' | 'info' | 'success' | 'warning' {
  if (total === 0) return 'info';
  const rate = (expires / total) * 100;
  if (rate >= 80) return 'success';
  if (rate >= 50) return 'warning';
  if (rate >= 20) return 'info';
  return 'danger';
}

// 获取数据库使用率
function getDbUsagePercent(keys: number): number {
  // 假设每个数据库最大容量为1000万个键
  const maxKeys = 10000000;
  return Math.min((keys / maxKeys) * 100, 100);
}

// 获取使用率颜色
function getUsageColor(percent: number): 'danger' | 'success' | 'warning' {
  if (percent >= 80) return 'danger';
  if (percent >= 50) return 'warning';
  return 'success';
}
</script>

<template>
  <div class="space-y-4">
    <!-- 键空间统计卡片 -->
    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <!-- 总键数 -->
      <ElCard shadow="hover">
        <div class="flex items-center justify-between">
          <div>
            <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
              总键数
            </div>
            <div class="text-3xl font-bold">
              {{ totalKeys.toLocaleString() }}
            </div>
          </div>
          <div class="rounded-lg bg-blue-100 p-3 dark:bg-blue-900/30">
            <Key :size="32" class="text-blue-600 dark:text-blue-400" />
          </div>
        </div>
      </ElCard>

      <!-- 过期键数 -->
      <ElCard shadow="hover">
        <div class="flex items-center justify-between">
          <div>
            <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
              过期键数
            </div>
            <div class="text-3xl font-bold">
              {{ totalExpires.toLocaleString() }}
            </div>
            <div class="mt-1 text-xs text-gray-500">
              占比: {{ totalKeys > 0 ? ((totalExpires / totalKeys) * 100).toFixed(1) : 0 }}%
            </div>
          </div>
          <div class="rounded-lg bg-orange-100 p-3 dark:bg-orange-900/30">
            <Activity :size="32" class="text-orange-600 dark:text-orange-400" />
          </div>
        </div>
      </ElCard>

      <!-- 平均TTL -->
      <ElCard shadow="hover">
        <div class="flex items-center justify-between">
          <div>
            <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
              平均TTL
            </div>
            <div class="text-3xl font-bold">
              {{ formatTTL(avgTTL) }}
            </div>
          </div>
          <div class="rounded-lg bg-green-100 p-3 dark:bg-green-900/30">
            <Database :size="32" class="text-green-600 dark:text-green-400" />
          </div>
        </div>
      </ElCard>
    </div>

    <!-- 数据库列表 -->
    <ElCard shadow="hover">
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Database :size="18" class="text-primary" />
            <span class="font-semibold">数据库列表</span>
          </div>
          <div class="text-sm text-gray-500 dark:text-gray-400">
            共 {{ keyspaces.length }} 个数据库
          </div>
        </div>
      </template>

      <div v-if="keyspaces.length === 0">
        <ElEmpty description="暂无数据库信息" />
      </div>

      <div v-else class="space-y-4">
        <div
          v-for="db in keyspaces"
          :key="db.db_id"
          class="rounded-lg border border-gray-200 p-4 dark:border-gray-700"
        >
          <!-- 数据库头部 -->
          <div class="mb-4 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/30">
                <Database :size="24" class="text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <div class="text-lg font-semibold">
                  DB{{ db.db_id }}
                </div>
                <div class="text-sm text-gray-500 dark:text-gray-400">
                  数据库 {{ db.db_id }}
                </div>
              </div>
            </div>
            <ElTag :type="db.keys > 0 ? 'success' : 'info'" size="large">
              {{ db.keys > 0 ? '活跃' : '空闲' }}
            </ElTag>
          </div>

          <!-- 数据库统计 -->
          <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
            <!-- 键数量 -->
            <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
              <div class="mb-2 flex items-center justify-between">
                <span class="text-sm text-gray-600 dark:text-gray-400">键数量</span>
                <Key :size="16" class="text-gray-400" />
              </div>
              <div class="text-2xl font-bold">
                {{ db.keys.toLocaleString() }}
              </div>
              <div class="mt-2">
                <ElProgress
                  :percentage="getDbUsagePercent(db.keys)"
                  :color="getUsageColor(getDbUsagePercent(db.keys))"
                  :show-text="false"
                />
              </div>
            </div>

            <!-- 过期键 -->
            <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
              <div class="mb-2 flex items-center justify-between">
                <span class="text-sm text-gray-600 dark:text-gray-400">过期键</span>
                <Activity :size="16" class="text-gray-400" />
              </div>
              <div class="text-2xl font-bold">
                {{ db.expires.toLocaleString() }}
              </div>
              <div class="mt-2 flex items-center gap-2">
                <ElTag
                  :type="getExpireRateColor(db.expires, db.keys)"
                  size="small"
                >
                  {{ db.keys > 0 ? ((db.expires / db.keys) * 100).toFixed(1) : 0 }}%
                </ElTag>
                <span class="text-xs text-gray-500">过期率</span>
              </div>
            </div>

            <!-- 平均TTL -->
            <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
              <div class="mb-2 flex items-center justify-between">
                <span class="text-sm text-gray-600 dark:text-gray-400">平均TTL</span>
                <Database :size="16" class="text-gray-400" />
              </div>
              <div class="text-2xl font-bold">
                {{ formatTTL(db.avg_ttl) }}
              </div>
              <div class="mt-2 text-xs text-gray-500">
                {{ db.avg_ttl > 0 ? `${db.avg_ttl.toLocaleString()}ms` : '无过期时间' }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </ElCard>

    <!-- 键空间说明 -->
    <ElCard shadow="hover">
      <template #header>
        <div class="flex items-center gap-2">
          <Activity :size="18" class="text-primary" />
          <span class="font-semibold">字段说明</span>
        </div>
      </template>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">键数量</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            数据库中存储的键的总数量
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">过期键</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            设置了过期时间的键的数量
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">平均TTL</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            所有过期键的平均存活时间（毫秒）
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">过期率</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            过期键占总键数的百分比
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">数据库编号</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            Redis数据库编号（0-15）
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">使用率</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            数据库键数量相对于最大容量的占比
          </div>
        </div>
      </div>
    </ElCard>
  </div>
</template>
