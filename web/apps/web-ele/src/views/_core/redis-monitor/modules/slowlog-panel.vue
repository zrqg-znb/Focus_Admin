<script setup lang="ts">
import type {
  RedisMonitorOverview,
  RedisRealtimeStats,
} from '#/api/core/redis-monitor';

import { computed } from 'vue';

import { Activity, Clock, Database, Network, Timer } from '@vben/icons';

import { ElCard, ElEmpty, ElTag } from 'element-plus';

defineOptions({ name: 'SlowlogPanel' });

const props = defineProps<{
  monitorData: RedisMonitorOverview | null;
  realtimeData: RedisRealtimeStats | null;
}>();

// 慢日志列表
const slowLogs = computed(() => props.monitorData?.slow_log || []);

// 统计信息
const totalSlowLogs = computed(() => slowLogs.value.length);
const avgDuration = computed(() => {
  if (slowLogs.value.length === 0) return 0;
  const total = slowLogs.value.reduce((sum, log) => sum + log.duration, 0);
  return total / slowLogs.value.length;
});
const maxDuration = computed(() => {
  if (slowLogs.value.length === 0) return 0;
  return Math.max(...slowLogs.value.map(log => log.duration));
});

// 格式化时间戳
function formatTimestamp(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

// 格式化持续时间（微秒）
function formatDuration(microseconds: number): string {
  if (microseconds < 1000) return `${microseconds}μs`;
  if (microseconds < 1000000) return `${(microseconds / 1000).toFixed(2)}ms`;
  return `${(microseconds / 1000000).toFixed(2)}s`;
}

// 获取持续时间颜色
function getDurationColor(microseconds: number): 'danger' | 'info' | 'success' | 'warning' {
  if (microseconds >= 1000000) return 'danger'; // >= 1s
  if (microseconds >= 100000) return 'warning'; // >= 100ms
  if (microseconds >= 10000) return 'info'; // >= 10ms
  return 'success';
}

// 获取持续时间进度条百分比
function getDurationPercent(duration: number): number {
  if (maxDuration.value === 0) return 0;
  return (duration / maxDuration.value) * 100;
}

// 截取命令显示
function truncateCommand(command: string, maxLength: number = 100): string {
  if (command.length <= maxLength) return command;
  return command.substring(0, maxLength) + '...';
}
</script>

<template>
  <div class="space-y-4">
    <!-- 慢日志统计卡片 -->
    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <!-- 慢日志总数 -->
      <ElCard shadow="hover">
        <div class="flex items-center justify-between">
          <div>
            <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
              慢日志总数
            </div>
            <div class="text-3xl font-bold">
              {{ totalSlowLogs }}
            </div>
          </div>
          <div class="rounded-lg bg-blue-100 p-3 dark:bg-blue-900/30">
            <Timer :size="32" class="text-blue-600 dark:text-blue-400" />
          </div>
        </div>
      </ElCard>

      <!-- 平均耗时 -->
      <ElCard shadow="hover">
        <div class="flex items-center justify-between">
          <div>
            <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
              平均耗时
            </div>
            <div class="text-3xl font-bold">
              {{ formatDuration(avgDuration) }}
            </div>
            <div class="mt-1 text-xs text-gray-500">
              {{ avgDuration.toFixed(0) }} μs
            </div>
          </div>
          <div class="rounded-lg bg-orange-100 p-3 dark:bg-orange-900/30">
            <Clock :size="32" class="text-orange-600 dark:text-orange-400" />
          </div>
        </div>
      </ElCard>

      <!-- 最大耗时 -->
      <ElCard shadow="hover">
        <div class="flex items-center justify-between">
          <div>
            <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
              最大耗时
            </div>
            <div class="text-3xl font-bold text-red-600">
              {{ formatDuration(maxDuration) }}
            </div>
            <div class="mt-1 text-xs text-gray-500">
              {{ maxDuration.toFixed(0) }} μs
            </div>
          </div>
          <div class="rounded-lg bg-red-100 p-3 dark:bg-red-900/30">
            <Activity :size="32" class="text-red-600 dark:text-red-400" />
          </div>
        </div>
      </ElCard>
    </div>

    <!-- 慢日志列表 -->
    <ElCard shadow="hover">
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Timer :size="18" class="text-primary" />
            <span class="font-semibold">慢日志列表</span>
          </div>
          <div class="text-sm text-gray-500 dark:text-gray-400">
            最近 {{ slowLogs.length }} 条记录
          </div>
        </div>
      </template>

      <div v-if="slowLogs.length === 0">
        <ElEmpty description="暂无慢日志记录">
          <template #image>
            <Database :size="64" class="text-gray-300" />
          </template>
        </ElEmpty>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="(log, index) in slowLogs"
          :key="log.id"
          class="rounded-lg border border-gray-200 p-4 transition-all hover:border-primary hover:shadow-md dark:border-gray-700"
        >
          <!-- 日志头部 -->
          <div class="mb-3 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-800">
                <span class="font-mono text-sm font-semibold text-gray-600 dark:text-gray-400">
                  #{{ index + 1 }}
                </span>
              </div>
              <div>
                <div class="flex items-center gap-2">
                  <span class="text-sm text-gray-500 dark:text-gray-400">ID:</span>
                  <span class="font-mono text-sm font-semibold">{{ log.id }}</span>
                </div>
                <div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                  <Clock :size="12" />
                  <span>{{ formatTimestamp(log.timestamp) }}</span>
                </div>
              </div>
            </div>
            <ElTag :type="getDurationColor(log.duration)" size="large">
              {{ formatDuration(log.duration) }}
            </ElTag>
          </div>

          <!-- 命令内容 -->
          <div class="mb-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <div class="mb-1 text-xs text-gray-500 dark:text-gray-400">命令:</div>
            <div class="font-mono text-sm break-all">
              {{ truncateCommand(log.command) }}
            </div>
          </div>

          <!-- 客户端信息和耗时进度 -->
          <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
            <!-- 客户端信息 -->
            <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
              <div class="mb-2 flex items-center gap-2">
                <Network :size="14" class="text-gray-400" />
                <span class="text-xs text-gray-500 dark:text-gray-400">客户端信息</span>
              </div>
              <div class="space-y-1">
                <div class="flex items-center justify-between text-sm">
                  <span class="text-gray-600 dark:text-gray-400">IP:</span>
                  <span class="font-mono">{{ log.client_ip || '-' }}</span>
                </div>
                <div class="flex items-center justify-between text-sm">
                  <span class="text-gray-600 dark:text-gray-400">名称:</span>
                  <span class="font-mono">{{ log.client_name || '未命名' }}</span>
                </div>
              </div>
            </div>

            <!-- 耗时进度 -->
            <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
              <div class="mb-2 flex items-center gap-2">
                <Activity :size="14" class="text-gray-400" />
                <span class="text-xs text-gray-500 dark:text-gray-400">耗时占比</span>
              </div>
              <div class="space-y-2">
                <div class="flex items-center justify-between text-sm">
                  <span class="text-gray-600 dark:text-gray-400">相对最大值:</span>
                  <span class="font-semibold">{{ getDurationPercent(log.duration).toFixed(1) }}%</span>
                </div>
                <div class="h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                  <div
                    class="h-full transition-all"
                    :class="{
                      'bg-red-500': getDurationColor(log.duration) === 'danger',
                      'bg-yellow-500': getDurationColor(log.duration) === 'warning',
                      'bg-blue-500': getDurationColor(log.duration) === 'info',
                      'bg-green-500': getDurationColor(log.duration) === 'success',
                    }"
                    :style="{ width: `${getDurationPercent(log.duration)}%` }"
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </ElCard>

    <!-- 慢日志说明 -->
    <ElCard shadow="hover">
      <template #header>
        <div class="flex items-center gap-2">
          <Activity :size="18" class="text-primary" />
          <span class="font-semibold">慢日志说明</span>
        </div>
      </template>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">慢日志阈值</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            超过配置阈值的命令会被记录到慢日志
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">执行时间</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            命令从开始到结束的总耗时（微秒）
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">客户端信息</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            执行命令的客户端IP和名称
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">性能优化</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            分析慢日志可以帮助优化Redis性能
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">时间单位</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            μs(微秒) = 0.001ms，ms(毫秒) = 0.001s
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">颜色标识</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            红色(≥1s) > 黄色(≥100ms) > 蓝色(≥10ms) > 绿色
          </div>
        </div>
      </div>
    </ElCard>
  </div>
</template>
