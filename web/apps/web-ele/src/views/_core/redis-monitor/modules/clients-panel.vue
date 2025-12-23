<script setup lang="ts">
import type {
  RedisMonitorOverview,
  RedisRealtimeStats,
} from '#/api/core/redis-monitor';

import { computed } from 'vue';

import { Activity, Network, Users } from '@vben/icons';

import { ElCard, ElEmpty, ElTag } from 'element-plus';

defineOptions({ name: 'ClientsPanel' });

const props = defineProps<{
  monitorData: RedisMonitorOverview | null;
  realtimeData: RedisRealtimeStats | null;
}>();

// 客户端列表
const clients = computed(() => props.monitorData?.clients || []);

// 格式化时间（秒转为可读格式）
function formatTime(seconds: number): string {
  if (seconds < 60) return `${seconds}秒`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时`;
  return `${Math.floor(seconds / 86400)}天`;
}

// 格式化字节大小
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}

// 获取客户端状态颜色
function getClientStatusColor(flags: string): 'danger' | 'info' | 'success' | 'warning' {
  if (flags.includes('M')) return 'danger'; // Master
  if (flags.includes('S')) return 'warning'; // Slave
  if (flags.includes('b')) return 'info'; // Blocked
  return 'success'; // Normal
}

// 获取客户端状态文本
function getClientStatusText(flags: string): string {
  if (flags.includes('M')) return '主节点';
  if (flags.includes('S')) return '从节点';
  if (flags.includes('b')) return '阻塞中';
  if (flags.includes('N')) return '普通';
  return '活跃';
}
</script>

<template>
  <div class="space-y-4">
    <!-- 客户端统计卡片 -->
    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <!-- 连接客户端数 -->
      <ElCard shadow="hover">
        <div class="flex items-center justify-between">
          <div>
            <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
              连接客户端
            </div>
            <div class="text-3xl font-bold">
              {{ clients.length }}
            </div>
          </div>
          <div class="rounded-lg bg-blue-100 p-3 dark:bg-blue-900/30">
            <Users :size="32" class="text-blue-600 dark:text-blue-400" />
          </div>
        </div>
      </ElCard>

      <!-- 阻塞客户端数 -->
      <ElCard shadow="hover">
        <div class="flex items-center justify-between">
          <div>
            <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
              阻塞客户端
            </div>
            <div class="text-3xl font-bold">
              {{ monitorData?.info?.blocked_clients || 0 }}
            </div>
          </div>
          <div class="rounded-lg bg-orange-100 p-3 dark:bg-orange-900/30">
            <Activity :size="32" class="text-orange-600 dark:text-orange-400" />
          </div>
        </div>
      </ElCard>

      <!-- 总连接数 -->
      <ElCard shadow="hover">
        <div class="flex items-center justify-between">
          <div>
            <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
              总连接数
            </div>
            <div class="text-3xl font-bold">
              {{ monitorData?.stats?.total_connections_received || 0 }}
            </div>
          </div>
          <div class="rounded-lg bg-green-100 p-3 dark:bg-green-900/30">
            <Network :size="32" class="text-green-600 dark:text-green-400" />
          </div>
        </div>
      </ElCard>
    </div>

    <!-- 客户端列表 -->
    <ElCard shadow="hover">
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Users :size="18" class="text-primary" />
            <span class="font-semibold">客户端列表</span>
          </div>
          <div class="text-sm text-gray-500 dark:text-gray-400">
            共 {{ clients.length }} 个客户端
          </div>
        </div>
      </template>

      <div v-if="clients.length === 0">
        <ElEmpty description="暂无客户端连接" />
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th class="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">
                客户端ID
              </th>
              <th class="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">
                地址
              </th>
              <th class="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">
                名称
              </th>
              <th class="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">
                数据库
              </th>
              <th class="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">
                状态
              </th>
              <th class="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">
                连接时长
              </th>
              <th class="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">
                空闲时长
              </th>
              <th class="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">
                输出缓冲
              </th>
              <th class="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">
                最后命令
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr
              v-for="client in clients"
              :key="client.id"
              class="hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              <td class="px-4 py-3 font-mono text-xs">
                {{ client.id }}
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-1">
                  <Network :size="14" class="text-gray-400" />
                  <span class="font-mono text-xs">{{ client.addr }}</span>
                </div>
              </td>
              <td class="px-4 py-3">
                <span v-if="client.name" class="font-medium">{{ client.name }}</span>
                <span v-else class="text-gray-400">-</span>
              </td>
              <td class="px-4 py-3">
                <ElTag size="small" type="info">
                  DB{{ client.db }}
                </ElTag>
              </td>
              <td class="px-4 py-3">
                <ElTag size="small" :type="getClientStatusColor(client.flags)">
                  {{ getClientStatusText(client.flags) }}
                </ElTag>
              </td>
              <td class="px-4 py-3 text-gray-600 dark:text-gray-400">
                {{ formatTime(client.age) }}
              </td>
              <td class="px-4 py-3 text-gray-600 dark:text-gray-400">
                {{ formatTime(client.idle) }}
              </td>
              <td class="px-4 py-3">
                <div class="text-xs">
                  <div>使用: {{ formatBytes(client.omem) }}</div>
                  <div class="text-gray-500">队列: {{ client.obl + client.oll }}</div>
                </div>
              </td>
              <td class="px-4 py-3">
                <span v-if="client.cmd" class="rounded bg-gray-100 px-2 py-1 font-mono text-xs dark:bg-gray-700">
                  {{ client.cmd }}
                </span>
                <span v-else class="text-gray-400">-</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </ElCard>

    <!-- 客户端详细信息说明 -->
    <ElCard shadow="hover">
      <template #header>
        <div class="flex items-center gap-2">
          <Activity :size="18" class="text-primary" />
          <span class="font-semibold">字段说明</span>
        </div>
      </template>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">客户端ID</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            Redis分配的唯一客户端标识符
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">地址</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            客户端的IP地址和端口号
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">名称</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            通过CLIENT SETNAME设置的客户端名称
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">连接时长</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            客户端连接的总时长
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">空闲时长</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            客户端空闲的时长（未发送命令）
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">输出缓冲</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            输出缓冲区使用的内存和队列长度
          </div>
        </div>
      </div>
    </ElCard>
  </div>
</template>
