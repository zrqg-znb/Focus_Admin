<script setup lang="ts">
import type {
  DatabaseMonitorOverview,
  DatabaseRealtimeStats,
} from '#/api/core/database-monitor';

import { computed } from 'vue';

import {
  Activity,
  BarChart,
  TrendingUp,
  Zap,
} from '@vben/icons';

import {
  ElCard,
  ElDescriptions,
  ElDescriptionsItem,
  ElProgress,
  ElTag,
} from 'element-plus';

defineOptions({ name: 'PerformancePanel' });

const props = defineProps<{
  monitorData: DatabaseMonitorOverview | null;
  realtimeData: DatabaseRealtimeStats | null;
}>();

// 基本信息
const basicInfo = computed(() => props.monitorData?.basic_info);

// 性能统计
const performanceStats = computed(() => props.monitorData?.performance_stats);

// 缓存命中率
const cacheHitRatio = computed(() => {
  return props.realtimeData?.cache_hit_ratio || 0;
});

// 格式化大数字
function formatNumber(num: number): string {
  if (num >= 1000000000) return `${(num / 1000000000).toFixed(2)}B`;
  if (num >= 1000000) return `${(num / 1000000).toFixed(2)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(2)}K`;
  return num.toString();
}

// 格式化字节
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}

// 获取百分比颜色
function getPercentColor(percent: number): string {
  if (percent >= 90) return '#67c23a';
  if (percent >= 70) return '#e6a23c';
  return '#f56c6c';
}

// 获取数据库类型
const dbType = computed(() => basicInfo.value?.db_type || '');
</script>

<template>
  <div class="space-y-4">
    <!-- 核心性能指标 -->
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      <!-- 缓存命中率 -->
      <ElCard shadow="hover">
        <div class="mb-3 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="rounded-lg bg-green-100 p-2 dark:bg-green-900/30">
              <Zap :size="20" class="text-green-600 dark:text-green-400" />
            </div>
            <span class="text-sm font-medium text-gray-600 dark:text-gray-400"
              >缓存命中率</span
            >
          </div>
        </div>
        <div class="mb-2 text-3xl font-bold">
          {{ cacheHitRatio.toFixed(2) }}%
        </div>
        <ElProgress
          :percentage="Number(cacheHitRatio.toFixed(1))"
          :color="getPercentColor(cacheHitRatio)"
          :stroke-width="8"
        />
        <div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
          实时缓存命中率
        </div>
      </ElCard>

      <!-- PostgreSQL: 事务提交 -->
      <ElCard v-if="dbType === 'POSTGRESQL'" shadow="hover">
        <div class="mb-3 flex items-center gap-2">
          <div class="rounded-lg bg-blue-100 p-2 dark:bg-blue-900/30">
            <TrendingUp :size="20" class="text-blue-600 dark:text-blue-400" />
          </div>
          <span class="text-sm font-medium text-gray-600 dark:text-gray-400"
            >事务提交</span
          >
        </div>
        <div class="mb-2 text-3xl font-bold">
          {{ formatNumber(performanceStats?.transactions_commit || 0) }}
        </div>
        <div class="text-sm text-gray-500 dark:text-gray-400">
          累计提交事务数
        </div>
      </ElCard>

      <!-- PostgreSQL: 事务回滚 -->
      <ElCard v-if="dbType === 'POSTGRESQL'" shadow="hover">
        <div class="mb-3 flex items-center gap-2">
          <div class="rounded-lg bg-orange-100 p-2 dark:bg-orange-900/30">
            <Activity :size="20" class="text-orange-600 dark:text-orange-400" />
          </div>
          <span class="text-sm font-medium text-gray-600 dark:text-gray-400"
            >事务回滚</span
          >
        </div>
        <div class="mb-2 text-3xl font-bold">
          {{ formatNumber(performanceStats?.transactions_rollback || 0) }}
        </div>
        <div class="text-sm text-gray-500 dark:text-gray-400">
          累计回滚事务数
        </div>
      </ElCard>

      <!-- MySQL: 总查询数 -->
      <ElCard v-if="dbType === 'MYSQL'" shadow="hover">
        <div class="mb-3 flex items-center gap-2">
          <div class="rounded-lg bg-blue-100 p-2 dark:bg-blue-900/30">
            <BarChart :size="20" class="text-blue-600 dark:text-blue-400" />
          </div>
          <span class="text-sm font-medium text-gray-600 dark:text-gray-400"
            >总查询数</span
          >
        </div>
        <div class="mb-2 text-3xl font-bold">
          {{ formatNumber(performanceStats?.total_queries || 0) }}
        </div>
        <div class="text-sm text-gray-500 dark:text-gray-400">
          累计查询次数
        </div>
      </ElCard>

      <!-- MySQL: 慢查询 -->
      <ElCard v-if="dbType === 'MYSQL'" shadow="hover">
        <div class="mb-3 flex items-center gap-2">
          <div class="rounded-lg bg-red-100 p-2 dark:bg-red-900/30">
            <Activity :size="20" class="text-red-600 dark:text-red-400" />
          </div>
          <span class="text-sm font-medium text-gray-600 dark:text-gray-400"
            >慢查询</span
          >
        </div>
        <div class="mb-2 text-3xl font-bold" :class="(performanceStats?.slow_queries || 0) > 0 ? 'text-red-600' : ''">
          {{ formatNumber(performanceStats?.slow_queries || 0) }}
        </div>
        <div class="text-sm text-gray-500 dark:text-gray-400">
          需要优化的查询
        </div>
      </ElCard>

      <!-- SQL Server: 批处理请求 -->
      <ElCard v-if="dbType === 'SQLSERVER'" shadow="hover">
        <div class="mb-3 flex items-center gap-2">
          <div class="rounded-lg bg-purple-100 p-2 dark:bg-purple-900/30">
            <Zap :size="20" class="text-purple-600 dark:text-purple-400" />
          </div>
          <span class="text-sm font-medium text-gray-600 dark:text-gray-400"
            >批处理请求/秒</span
          >
        </div>
        <div class="mb-2 text-3xl font-bold">
          {{ performanceStats?.batch_requests_per_sec || 0 }}
        </div>
        <div class="text-sm text-gray-500 dark:text-gray-400">
          每秒批处理请求数
        </div>
      </ElCard>
    </div>

    <!-- PostgreSQL 性能详情 -->
    <div v-if="dbType === 'POSTGRESQL'" class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <!-- 事务统计 -->
      <ElCard shadow="hover">
        <template #header>
          <div class="flex items-center gap-2">
            <TrendingUp :size="18" class="text-primary" />
            <span class="font-semibold">事务统计</span>
          </div>
        </template>
        <ElDescriptions :column="1" border size="small">
          <ElDescriptionsItem label="事务提交">
            <span class="font-mono">{{ formatNumber(performanceStats?.transactions_commit || 0) }}</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="事务回滚">
            <span class="font-mono">{{ formatNumber(performanceStats?.transactions_rollback || 0) }}</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="提交率">
            <div class="flex items-center gap-2">
              <ElProgress
                :percentage="Number((((performanceStats?.transactions_commit || 0) / ((performanceStats?.transactions_commit || 0) + (performanceStats?.transactions_rollback || 1))) * 100).toFixed(1))"
                :color="getPercentColor(((performanceStats?.transactions_commit || 0) / ((performanceStats?.transactions_commit || 0) + (performanceStats?.transactions_rollback || 1))) * 100)"
                class="flex-1"
              />
              <span class="font-semibold">
                {{ (((performanceStats?.transactions_commit || 0) / ((performanceStats?.transactions_commit || 0) + (performanceStats?.transactions_rollback || 1))) * 100).toFixed(1) }}%
              </span>
            </div>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="缓存命中率">
            <div class="flex items-center gap-2">
              <ElProgress
                :percentage="Number(performanceStats?.cache_hit_ratio?.toFixed(1) || 0)"
                :color="getPercentColor(performanceStats?.cache_hit_ratio || 0)"
                class="flex-1"
              />
              <span class="font-semibold">
                {{ performanceStats?.cache_hit_ratio?.toFixed(2) || 0 }}%
              </span>
            </div>
          </ElDescriptionsItem>
        </ElDescriptions>
      </ElCard>

      <!-- 元组操作统计 -->
      <ElCard shadow="hover">
        <template #header>
          <div class="flex items-center gap-2">
            <BarChart :size="18" class="text-primary" />
            <span class="font-semibold">元组操作统计</span>
          </div>
        </template>
        <ElDescriptions :column="1" border size="small">
          <ElDescriptionsItem label="元组返回">
            <span class="font-mono">{{ formatNumber(performanceStats?.tuples_returned || 0) }}</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="元组获取">
            <span class="font-mono">{{ formatNumber(performanceStats?.tuples_fetched || 0) }}</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="元组插入">
            <span class="font-mono text-green-600">{{ formatNumber(performanceStats?.tuples_inserted || 0) }}</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="元组更新">
            <span class="font-mono text-blue-600">{{ formatNumber(performanceStats?.tuples_updated || 0) }}</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="元组删除">
            <span class="font-mono text-red-600">{{ formatNumber(performanceStats?.tuples_deleted || 0) }}</span>
          </ElDescriptionsItem>
        </ElDescriptions>
      </ElCard>
    </div>

    <!-- MySQL 性能详情 -->
    <div v-if="dbType === 'MYSQL'" class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <!-- 查询统计 -->
      <ElCard shadow="hover">
        <template #header>
          <div class="flex items-center gap-2">
            <BarChart :size="18" class="text-primary" />
            <span class="font-semibold">查询统计</span>
          </div>
        </template>
        <ElDescriptions :column="1" border size="small">
          <ElDescriptionsItem label="总查询数">
            <span class="font-mono">{{ formatNumber(performanceStats?.total_queries || 0) }}</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="总连接数">
            <span class="font-mono">{{ formatNumber(performanceStats?.total_connections || 0) }}</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="慢查询">
            <div class="flex items-center gap-2">
              <span class="font-mono" :class="(performanceStats?.slow_queries || 0) > 0 ? 'text-red-600' : ''">
                {{ formatNumber(performanceStats?.slow_queries || 0) }}
              </span>
              <ElTag v-if="(performanceStats?.slow_queries || 0) > 0" type="danger" size="small">
                需优化
              </ElTag>
            </div>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="缓存命中率">
            <div class="flex items-center gap-2">
              <ElProgress
                :percentage="Number(performanceStats?.cache_hit_ratio?.toFixed(1) || 0)"
                :color="getPercentColor(performanceStats?.cache_hit_ratio || 0)"
                class="flex-1"
              />
              <span class="font-semibold">
                {{ performanceStats?.cache_hit_ratio?.toFixed(2) || 0 }}%
              </span>
            </div>
          </ElDescriptionsItem>
        </ElDescriptions>
      </ElCard>

      <!-- 网络流量 -->
      <ElCard shadow="hover">
        <template #header>
          <div class="flex items-center gap-2">
            <Activity :size="18" class="text-primary" />
            <span class="font-semibold">网络流量</span>
          </div>
        </template>
        <ElDescriptions :column="1" border size="small">
          <ElDescriptionsItem label="接收字节">
            <span class="font-mono">{{ formatBytes(performanceStats?.bytes_received || 0) }}</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="发送字节">
            <span class="font-mono">{{ formatBytes(performanceStats?.bytes_sent || 0) }}</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="总流量">
            <span class="font-mono font-semibold">
              {{ formatBytes((performanceStats?.bytes_received || 0) + (performanceStats?.bytes_sent || 0)) }}
            </span>
          </ElDescriptionsItem>
        </ElDescriptions>
      </ElCard>
    </div>

    <!-- SQL Server 性能详情 -->
    <div v-if="dbType === 'SQLSERVER'" class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <!-- 批处理统计 -->
      <ElCard shadow="hover">
        <template #header>
          <div class="flex items-center gap-2">
            <Zap :size="18" class="text-primary" />
            <span class="font-semibold">批处理统计</span>
          </div>
        </template>
        <ElDescriptions :column="1" border size="small">
          <ElDescriptionsItem label="批处理请求/秒">
            <span class="font-mono">{{ performanceStats?.batch_requests_per_sec || 0 }}</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="页面生命期望">
            <span class="font-mono">{{ performanceStats?.page_life_expectancy || 0 }}</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="缓冲区命中率">
            <div class="flex items-center gap-2">
              <ElProgress
                :percentage="Number(performanceStats?.buffer_cache_hit_ratio?.toFixed(1) || 0)"
                :color="getPercentColor(performanceStats?.buffer_cache_hit_ratio || 0)"
                class="flex-1"
              />
              <span class="font-semibold">
                {{ performanceStats?.buffer_cache_hit_ratio?.toFixed(2) || 0 }}%
              </span>
            </div>
          </ElDescriptionsItem>
        </ElDescriptions>
      </ElCard>

      <!-- 缓存统计 -->
      <ElCard shadow="hover">
        <template #header>
          <div class="flex items-center gap-2">
            <Activity :size="18" class="text-primary" />
            <span class="font-semibold">缓存统计</span>
          </div>
        </template>
        <ElDescriptions :column="1" border size="small">
          <ElDescriptionsItem label="缓存命中率">
            <div class="flex items-center gap-2">
              <ElProgress
                :percentage="Number(performanceStats?.cache_hit_ratio?.toFixed(1) || 0)"
                :color="getPercentColor(performanceStats?.cache_hit_ratio || 0)"
                class="flex-1"
              />
              <span class="font-semibold">
                {{ performanceStats?.cache_hit_ratio?.toFixed(2) || 0 }}%
              </span>
            </div>
          </ElDescriptionsItem>
        </ElDescriptions>
      </ElCard>
    </div>

    <!-- 性能说明 -->
    <ElCard shadow="hover">
      <template #header>
        <div class="flex items-center gap-2">
          <Activity :size="18" class="text-primary" />
          <span class="font-semibold">性能指标说明</span>
        </div>
      </template>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">缓存命中率</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            从缓存中读取数据的比例，越高性能越好
          </div>
        </div>
        
        <!-- PostgreSQL 说明 -->
        <template v-if="dbType === 'POSTGRESQL'">
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">事务提交</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              成功提交的事务总数
            </div>
          </div>
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">事务回滚</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              回滚的事务总数，过高可能表示有问题
            </div>
          </div>
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">元组操作</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              数据行的增删改查操作统计
            </div>
          </div>
        </template>

        <!-- MySQL 说明 -->
        <template v-if="dbType === 'MYSQL'">
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">总查询数</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              数据库执行的所有查询总数
            </div>
          </div>
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">慢查询</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              执行时间超过阈值的查询，需要优化
            </div>
          </div>
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">网络流量</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              数据库接收和发送的字节数
            </div>
          </div>
        </template>

        <!-- SQL Server 说明 -->
        <template v-if="dbType === 'SQLSERVER'">
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">批处理请求</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              每秒处理的批处理请求数
            </div>
          </div>
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">页面生命期望</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              页面在缓冲池中停留的平均秒数
            </div>
          </div>
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">缓冲区命中率</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              从缓冲区读取页面的比例
            </div>
          </div>
        </template>
      </div>
    </ElCard>
  </div>
</template>
