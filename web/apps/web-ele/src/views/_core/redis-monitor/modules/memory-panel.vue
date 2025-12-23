<script setup lang="ts">
import type {
  RedisMonitorOverview,
  RedisRealtimeStats,
} from '#/api/core/redis-monitor';

import { computed, ref, watch } from 'vue';

import { Activity, Database, HardDrive, Settings } from '@vben/icons';

import {
  ElCard,
  ElDescriptions,
  ElDescriptionsItem,
  ElProgress,
  ElTag,
} from 'element-plus';

defineOptions({ name: 'MemoryPanel' });

const props = defineProps<{
  monitorData: RedisMonitorOverview | null;
  realtimeData: RedisRealtimeStats | null;
}>();

// 历史数据点（最多保存60个点，约3分钟数据）
interface MemoryDataPoint {
  timestamp: string;
  usedMemory: number;
  memoryPercent: number;
}

const historyData = ref<MemoryDataPoint[]>([]);
const MAX_HISTORY_POINTS = 60;

// 监听实时数据变化，添加到历史记录
watch(
  () => props.realtimeData,
  (newData) => {
    if (newData) {
      const now = new Date();
      const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
      
      historyData.value.push({
        timestamp: timeStr,
        usedMemory: newData.used_memory,
        memoryPercent: newData.memory_usage_percent,
      });

      // 保持最多60个数据点
      if (historyData.value.length > MAX_HISTORY_POINTS) {
        historyData.value.shift();
      }
    }
  },
  { immediate: true },
);

// 计算图表数据
const chartData = computed(() => {
  if (historyData.value.length === 0) {
    return {
      labels: [],
      values: [],
      hasData: false,
    };
  }

  return {
    labels: historyData.value.map((d) => d.timestamp),
    values: historyData.value.map((d) => d.memoryPercent),
    hasData: true,
  };
});

// 格式化字节大小
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}

// 获取百分比颜色
function getPercentColor(
  percent: number,
): 'danger' | 'info' | 'primary' | 'success' | 'warning' {
  if (percent >= 90) return 'danger';
  if (percent >= 70) return 'warning';
  return 'success';
}

// 获取碎片率状态
function getFragmentationStatus(ratio: number): {
  type: 'danger' | 'info' | 'success' | 'warning';
  text: string;
} {
  if (ratio < 1) {
    return { type: 'danger', text: '内存不足' };
  }
  if (ratio > 1.5) {
    return { type: 'warning', text: '碎片较多' };
  }
  return { type: 'success', text: '正常' };
}
</script>

<template>
  <div class="space-y-4">
    <!-- 内存使用概览卡片 -->
    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <!-- 内存使用率 -->
      <ElCard shadow="hover">
        <div class="mb-3 flex items-center gap-2">
          <div class="rounded-lg bg-blue-100 p-2 dark:bg-blue-900/30">
            <Database :size="20" class="text-blue-600 dark:text-blue-400" />
          </div>
          <span class="text-sm font-medium text-gray-600 dark:text-gray-400"
            >内存使用率</span
          >
        </div>
        <div class="mb-2 text-3xl font-bold">
          {{ realtimeData?.memory_usage_percent?.toFixed(1) || '0.0' }}%
        </div>
        <ElProgress
          :percentage="Number(realtimeData?.memory_usage_percent?.toFixed(1) || 0)"
          :color="getPercentColor(realtimeData?.memory_usage_percent || 0)"
          :stroke-width="8"
        />
        <div class="mt-2 text-sm text-gray-500 dark:text-gray-400">
          {{ monitorData?.memory?.used_memory_human || '-' }} /
          {{ monitorData?.memory?.total_system_memory_human || '-' }}
        </div>
      </ElCard>

      <!-- 内存峰值 -->
      <ElCard shadow="hover">
        <div class="mb-3 flex items-center gap-2">
          <div class="rounded-lg bg-orange-100 p-2 dark:bg-orange-900/30">
            <Activity :size="20" class="text-orange-600 dark:text-orange-400" />
          </div>
          <span class="text-sm font-medium text-gray-600 dark:text-gray-400"
            >内存峰值</span
          >
        </div>
        <div class="mb-2 text-3xl font-bold">
          {{ monitorData?.memory?.used_memory_peak_human || '-' }}
        </div>
        <div class="text-sm text-gray-500 dark:text-gray-400">
          历史最高使用量
        </div>
      </ElCard>

      <!-- 内存碎片率 -->
      <ElCard shadow="hover">
        <div class="mb-3 flex items-center gap-2">
          <div class="rounded-lg bg-purple-100 p-2 dark:bg-purple-900/30">
            <HardDrive :size="20" class="text-purple-600 dark:text-purple-400" />
          </div>
          <span class="text-sm font-medium text-gray-600 dark:text-gray-400"
            >内存碎片率</span
          >
        </div>
        <div class="mb-2 text-3xl font-bold">
          {{ monitorData?.memory?.mem_fragmentation_ratio?.toFixed(2) || '0.00' }}
        </div>
        <ElTag
          :type="
            getFragmentationStatus(
              monitorData?.memory?.mem_fragmentation_ratio || 0,
            ).type
          "
        >
          {{
            getFragmentationStatus(
              monitorData?.memory?.mem_fragmentation_ratio || 0,
            ).text
          }}
        </ElTag>
      </ElCard>
    </div>

    <!-- 内存使用详情 -->
    <ElCard shadow="hover">
      <template #header>
        <div class="flex items-center gap-2">
          <Database :size="18" class="text-primary" />
          <span class="font-semibold">内存使用详情</span>
        </div>
      </template>

      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <ElDescriptions :column="1" border size="default">
            <ElDescriptionsItem label="已使用内存">
              <div class="flex items-center justify-between">
                <span>{{ monitorData?.memory?.used_memory_human || '-' }}</span>
                <ElTag type="primary" size="small">
                  {{ formatBytes(monitorData?.memory?.used_memory || 0) }}
                </ElTag>
              </div>
            </ElDescriptionsItem>
            <ElDescriptionsItem label="RSS内存">
              <div class="flex items-center justify-between">
                <span>{{ formatBytes(monitorData?.memory?.used_memory_rss || 0) }}</span>
                <ElTag type="info" size="small">物理内存</ElTag>
              </div>
            </ElDescriptionsItem>
            <ElDescriptionsItem label="内存峰值">
              <div class="flex items-center justify-between">
                <span>{{ monitorData?.memory?.used_memory_peak_human || '-' }}</span>
                <ElTag type="warning" size="small">
                  {{ formatBytes(monitorData?.memory?.used_memory_peak || 0) }}
                </ElTag>
              </div>
            </ElDescriptionsItem>
            <ElDescriptionsItem label="系统总内存">
              <div class="flex items-center justify-between">
                <span>{{
                  monitorData?.memory?.total_system_memory_human || '-'
                }}</span>
                <ElTag type="success" size="small">系统</ElTag>
              </div>
            </ElDescriptionsItem>
          </ElDescriptions>
        </div>

        <div>
          <ElDescriptions :column="1" border size="default">
            <ElDescriptionsItem label="数据集内存">
              <div class="flex items-center justify-between">
                <span>{{
                  formatBytes(monitorData?.memory?.used_memory_dataset || 0)
                }}</span>
                <ElTag type="primary" size="small">
                  {{ monitorData?.memory?.used_memory_dataset_perc || '-' }}
                </ElTag>
              </div>
            </ElDescriptionsItem>
            <ElDescriptionsItem label="分配器已分配">
              <div class="flex items-center justify-between">
                <span>{{
                  formatBytes(monitorData?.memory?.allocator_allocated || 0)
                }}</span>
                <ElTag type="info" size="small">Allocator</ElTag>
              </div>
            </ElDescriptionsItem>
            <ElDescriptionsItem label="分配器活跃">
              <div class="flex items-center justify-between">
                <span>{{
                  formatBytes(monitorData?.memory?.allocator_active || 0)
                }}</span>
                <ElTag type="info" size="small">Active</ElTag>
              </div>
            </ElDescriptionsItem>
            <ElDescriptionsItem label="内存碎片率">
              <div class="flex items-center justify-between">
                <span>{{
                  monitorData?.memory?.mem_fragmentation_ratio?.toFixed(2) || '0.00'
                }}</span>
                <ElTag
                  :type="
                    getFragmentationStatus(
                      monitorData?.memory?.mem_fragmentation_ratio || 0,
                    ).type
                  "
                  size="small"
                >
                  {{
                    getFragmentationStatus(
                      monitorData?.memory?.mem_fragmentation_ratio || 0,
                    ).text
                  }}
                </ElTag>
              </div>
            </ElDescriptionsItem>
          </ElDescriptions>
        </div>
      </div>
    </ElCard>

    <!-- 内存策略配置 -->
    <ElCard shadow="hover">
      <template #header>
        <div class="flex items-center gap-2">
          <Settings :size="18" class="text-primary" />
          <span class="font-semibold">内存策略配置</span>
        </div>
      </template>

      <ElDescriptions :column="2" border size="default">
        <ElDescriptionsItem label="最大内存限制">
          <div class="flex items-center gap-2">
            <span>{{ monitorData?.memory?.maxmemory_human || '无限制' }}</span>
            <ElTag
              v-if="monitorData?.memory?.maxmemory && monitorData.memory.maxmemory > 0"
              type="warning"
              size="small"
            >
              已设置
            </ElTag>
            <ElTag v-else type="info" size="small">未限制</ElTag>
          </div>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="内存淘汰策略">
          <ElTag type="primary">{{
            monitorData?.memory?.maxmemory_policy || '-'
          }}</ElTag>
        </ElDescriptionsItem>
      </ElDescriptions>

      <div class="mt-4 rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
        <div class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
          💡 内存淘汰策略说明
        </div>
        <div class="space-y-1 text-xs text-gray-600 dark:text-gray-400">
          <div>
            <span class="font-semibold">noeviction:</span> 不淘汰，内存满时返回错误
          </div>
          <div>
            <span class="font-semibold">allkeys-lru:</span>
            从所有键中淘汰最近最少使用的键
          </div>
          <div>
            <span class="font-semibold">volatile-lru:</span>
            从设置了过期时间的键中淘汰最近最少使用的键
          </div>
          <div>
            <span class="font-semibold">allkeys-random:</span> 从所有键中随机淘汰
          </div>
          <div>
            <span class="font-semibold">volatile-random:</span>
            从设置了过期时间的键中随机淘汰
          </div>
          <div>
            <span class="font-semibold">volatile-ttl:</span>
            淘汰即将过期的键（TTL最小）
          </div>
        </div>
      </div>
    </ElCard>

    <!-- 内存使用趋势图表 -->
    <ElCard shadow="hover">
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Activity :size="18" class="text-primary" />
            <span class="font-semibold">内存使用趋势</span>
          </div>
          <div class="text-sm text-gray-500 dark:text-gray-400">
            最近 {{ historyData.length }} 个数据点
          </div>
        </div>
      </template>

      <div v-if="!chartData.hasData" class="flex h-64 items-center justify-center text-gray-400">
        <div class="text-center">
          <Activity :size="48" class="mx-auto mb-4" />
          <p class="text-lg">等待数据中...</p>
          <p class="mt-2 text-sm">正在收集内存使用数据</p>
        </div>
      </div>

      <div v-else class="relative h-64 p-4">
        <!-- Y轴标签 -->
        <div class="absolute left-0 top-0 flex h-full flex-col justify-between py-4 text-xs text-gray-500">
          <span>100%</span>
          <span>75%</span>
          <span>50%</span>
          <span>25%</span>
          <span>0%</span>
        </div>

        <!-- 图表区域 -->
        <div class="ml-12 h-full">
          <svg class="h-full w-full" viewBox="0 0 800 200" preserveAspectRatio="none">
            <!-- 网格线 -->
            <line
              v-for="i in 5"
              :key="`grid-${i}`"
              :x1="0"
              :y1="(i - 1) * 50"
              :x2="800"
              :y2="(i - 1) * 50"
              stroke="currentColor"
              stroke-width="0.5"
              class="text-gray-200 dark:text-gray-700"
              stroke-dasharray="5,5"
            />

            <!-- 折线图 -->
            <polyline
              :points="
                chartData.values
                  .map((val, idx) => {
                    const x = (idx / (chartData.values.length - 1 || 1)) * 800;
                    const y = 200 - (val / 100) * 200;
                    return `${x},${y}`;
                  })
                  .join(' ')
              "
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              class="text-blue-500"
            />

            <!-- 填充区域 -->
            <polygon
              :points="
                [
                  '0,200',
                  ...chartData.values.map((val, idx) => {
                    const x = (idx / (chartData.values.length - 1 || 1)) * 800;
                    const y = 200 - (val / 100) * 200;
                    return `${x},${y}`;
                  }),
                  '800,200',
                ].join(' ')
              "
              fill="currentColor"
              class="text-blue-500 opacity-10"
            />

            <!-- 数据点 -->
            <circle
              v-for="(val, idx) in chartData.values"
              :key="`point-${idx}`"
              :cx="(idx / (chartData.values.length - 1 || 1)) * 800"
              :cy="200 - (val / 100) * 200"
              r="3"
              fill="currentColor"
              class="text-blue-600"
            />
          </svg>
        </div>

        <!-- X轴时间标签 -->
        <div class="ml-12 mt-2 flex justify-between text-xs text-gray-500">
          <span>{{ chartData.labels[0] || '-' }}</span>
          <span>{{
            chartData.labels[Math.floor(chartData.labels.length / 2)] || '-'
          }}</span>
          <span>{{ chartData.labels[chartData.labels.length - 1] || '-' }}</span>
        </div>

        <!-- 当前值显示 -->
        <div class="mt-4 flex items-center justify-center gap-4 text-sm">
          <div class="flex items-center gap-2">
            <div class="h-3 w-3 rounded-full bg-blue-500"></div>
            <span class="text-gray-600 dark:text-gray-400">当前使用率:</span>
            <span class="font-semibold">{{
              chartData.values[chartData.values.length - 1]?.toFixed(1) || '0.0'
            }}%</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-gray-600 dark:text-gray-400">平均:</span>
            <span class="font-semibold">{{
              (
                chartData.values.reduce((a, b) => a + b, 0) / chartData.values.length
              ).toFixed(1)
            }}%</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-gray-600 dark:text-gray-400">最高:</span>
            <span class="font-semibold text-orange-600">{{
              Math.max(...chartData.values).toFixed(1)
            }}%</span>
          </div>
        </div>
      </div>
    </ElCard>
  </div>
</template>
