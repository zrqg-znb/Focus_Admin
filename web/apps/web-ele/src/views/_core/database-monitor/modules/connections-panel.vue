<script setup lang="ts">
import type {
  DatabaseMonitorOverview,
  DatabaseRealtimeStats,
} from '#/api/core/database-monitor';

import { computed } from 'vue';

import { Activity, Network, Users } from '@vben/icons';

import { ElCard, ElDescriptions, ElDescriptionsItem, ElProgress, ElTag } from 'element-plus';

defineOptions({ name: 'ConnectionsPanel' });

const props = defineProps<{
  monitorData: DatabaseMonitorOverview | null;
  realtimeData: DatabaseRealtimeStats | null;
}>();

// 连接信息
const connectionInfo = computed(() => props.monitorData?.connection_info);

// 实时连接数据
const realtimeConnections = computed(() => ({
  used: props.realtimeData?.connections_used || 0,
  active: props.realtimeData?.active_connections || 0,
  usagePercent: props.realtimeData?.connection_usage_percent || 0,
}));

// 获取百分比颜色
function getPercentColor(percent: number): string {
  if (percent >= 90) return '#f56c6c';
  if (percent >= 70) return '#e6a23c';
  return '#67c23a';
}

// 获取连接状态
function getConnectionStatus(percent: number): { text: string; type: 'danger' | 'info' | 'success' | 'warning' } {
  if (percent >= 90) return { text: '拥挤', type: 'danger' };
  if (percent >= 70) return { text: '繁忙', type: 'warning' };
  if (percent >= 50) return { text: '正常', type: 'info' };
  return { text: '空闲', type: 'success' };
}
</script>

<template>
  <div class="space-y-4">
    <!-- 连接统计卡片 -->
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
      <!-- 总连接数 -->
      <ElCard shadow="hover">
        <div class="flex items-center justify-between">
          <div>
            <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
              总连接数
            </div>
            <div class="text-3xl font-bold">
              {{ connectionInfo?.total_connections || 0 }}
            </div>
          </div>
          <div class="rounded-lg bg-blue-100 p-3 dark:bg-blue-900/30">
            <Network :size="32" class="text-blue-600 dark:text-blue-400" />
          </div>
        </div>
      </ElCard>

      <!-- 最大连接数 -->
      <ElCard shadow="hover">
        <div class="flex items-center justify-between">
          <div>
            <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
              最大连接数
            </div>
            <div class="text-3xl font-bold">
              {{ connectionInfo?.max_connections || 0 }}
            </div>
          </div>
          <div class="rounded-lg bg-purple-100 p-3 dark:bg-purple-900/30">
            <Network :size="32" class="text-purple-600 dark:text-purple-400" />
          </div>
        </div>
      </ElCard>

      <!-- 活动连接 -->
      <ElCard shadow="hover">
        <div class="flex items-center justify-between">
          <div>
            <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
              活动连接
            </div>
            <div class="text-3xl font-bold text-green-600">
              {{ realtimeConnections.active }}
            </div>
            <div class="mt-1 text-xs text-gray-500">
              实时活动连接数
            </div>
          </div>
          <div class="rounded-lg bg-green-100 p-3 dark:bg-green-900/30">
            <Activity :size="32" class="text-green-600 dark:text-green-400" />
          </div>
        </div>
      </ElCard>

      <!-- 空闲连接 -->
      <ElCard shadow="hover">
        <div class="flex items-center justify-between">
          <div>
            <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
              空闲连接
            </div>
            <div class="text-3xl font-bold text-gray-600">
              {{ connectionInfo?.idle_connections || 0 }}
            </div>
            <div class="mt-1 text-xs text-gray-500">
              当前空闲连接数
            </div>
          </div>
          <div class="rounded-lg bg-gray-100 p-3 dark:bg-gray-800">
            <Users :size="32" class="text-gray-600 dark:text-gray-400" />
          </div>
        </div>
      </ElCard>
    </div>

    <!-- 连接使用情况 -->
    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <!-- 连接池状态 -->
      <ElCard shadow="hover">
        <template #header>
          <div class="flex items-center gap-2">
            <Network :size="18" class="text-primary" />
            <span class="font-semibold">连接池状态</span>
          </div>
        </template>

        <div class="space-y-4">
          <!-- 连接使用率 -->
          <div>
            <div class="mb-2 flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400">连接使用率</span>
              <div class="flex items-center gap-2">
                <ElTag :type="getConnectionStatus(realtimeConnections.usagePercent).type" size="small">
                  {{ getConnectionStatus(realtimeConnections.usagePercent).text }}
                </ElTag>
                <span class="font-mono text-sm font-semibold">
                  {{ realtimeConnections.usagePercent.toFixed(1) }}%
                </span>
              </div>
            </div>
            <ElProgress
              :percentage="Number(realtimeConnections.usagePercent.toFixed(1))"
              :color="getPercentColor(realtimeConnections.usagePercent)"
              :stroke-width="12"
            />
          </div>

          <!-- 连接分布 -->
          <div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
            <div class="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">
              连接分布
            </div>
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <div class="h-3 w-3 rounded-full bg-green-500"></div>
                  <span class="text-sm text-gray-600 dark:text-gray-400">活动连接</span>
                </div>
                <span class="font-mono font-semibold">{{ realtimeConnections.active }}</span>
              </div>
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <div class="h-3 w-3 rounded-full bg-gray-400"></div>
                  <span class="text-sm text-gray-600 dark:text-gray-400">空闲连接</span>
                </div>
                <span class="font-mono font-semibold">{{ connectionInfo?.idle_connections || 0 }}</span>
              </div>
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <div class="h-3 w-3 rounded-full bg-blue-500"></div>
                  <span class="text-sm text-gray-600 dark:text-gray-400">总连接数</span>
                </div>
                <span class="font-mono font-semibold">{{ connectionInfo?.total_connections || 0 }}</span>
              </div>
            </div>
          </div>

          <!-- 连接池容量 -->
          <div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
            <div class="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">
              连接池容量
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400">
                已使用 / 最大连接数
              </span>
              <span class="font-mono text-lg font-semibold">
                {{ realtimeConnections.used }} / {{ connectionInfo?.max_connections || 0 }}
              </span>
            </div>
            <div class="mt-2">
              <ElProgress
                :percentage="Number(((realtimeConnections.used / (connectionInfo?.max_connections || 1)) * 100).toFixed(1))"
                :color="getPercentColor((realtimeConnections.used / (connectionInfo?.max_connections || 1)) * 100)"
                :show-text="false"
              />
            </div>
          </div>
        </div>
      </ElCard>

      <!-- 连接详细信息 -->
      <ElCard shadow="hover">
        <template #header>
          <div class="flex items-center gap-2">
            <Activity :size="18" class="text-primary" />
            <span class="font-semibold">连接详细信息</span>
          </div>
        </template>

        <ElDescriptions :column="1" border size="small">
          <ElDescriptionsItem label="总连接数">
            <span class="font-mono">{{ connectionInfo?.total_connections || 0 }}</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="最大连接数">
            <span class="font-mono">{{ connectionInfo?.max_connections || 0 }}</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="活动连接">
            <div class="flex items-center gap-2">
              <span class="font-mono font-semibold text-green-600">
                {{ realtimeConnections.active }}
              </span>
              <ElTag type="success" size="small">实时</ElTag>
            </div>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="空闲连接">
            <span class="font-mono text-gray-600">
              {{ connectionInfo?.idle_connections || 0 }}
            </span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="已使用连接">
            <span class="font-mono">{{ realtimeConnections.used }}</span>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="连接使用率">
            <div class="flex items-center gap-2">
              <ElProgress
                :percentage="Number(realtimeConnections.usagePercent.toFixed(1))"
                :color="getPercentColor(realtimeConnections.usagePercent)"
                class="flex-1"
              />
              <span class="font-semibold">
                {{ realtimeConnections.usagePercent.toFixed(1) }}%
              </span>
            </div>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="可用连接">
            <span class="font-mono">
              {{ (connectionInfo?.max_connections || 0) - realtimeConnections.used }}
            </span>
          </ElDescriptionsItem>
        </ElDescriptions>
      </ElCard>
    </div>

    <!-- 连接说明 -->
    <ElCard shadow="hover">
      <template #header>
        <div class="flex items-center gap-2">
          <Activity :size="18" class="text-primary" />
          <span class="font-semibold">连接说明</span>
        </div>
      </template>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">总连接数</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            数据库当前建立的所有连接总数
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">最大连接数</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            数据库配置的最大允许连接数
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">活动连接</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            正在执行查询或事务的连接数
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">空闲连接</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            已建立但未在使用的连接数
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">连接使用率</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            当前连接数占最大连接数的百分比
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">连接状态</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            空闲(&lt;50%) / 正常(50-70%) / 繁忙(70-90%) / 拥挤(≥90%)
          </div>
        </div>
      </div>
    </ElCard>
  </div>
</template>
