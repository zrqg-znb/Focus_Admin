<script setup lang="ts">
import type {
  RealtimeStats as RealtimeStatsType,
  ServerMonitorResponse,
} from '#/api/core/server-monitor';

import {
  Network,
} from '@vben/icons';

import {
  ElCard,
  ElDescriptions,
  ElDescriptionsItem,
  ElTag,
} from 'element-plus';

defineOptions({ name: 'NetworkPanel' });

defineProps<{
  serverData: ServerMonitorResponse | null;
  realtimeData: RealtimeStatsType | null;
}>();

// 格式化字节大小
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}

// 格式化速度
function formatSpeed(bytesPerSecond: number): string {
  return `${formatBytes(bytesPerSecond)}/s`;
}
</script>

<template>
  <div class="space-y-4">
    <!-- 网络IO概览 -->
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
      <!-- 上传速度 -->
      <ElCard shadow="hover">
        <div class="mb-3 flex items-center gap-2">
          <div class="rounded-lg bg-blue-100 p-2 dark:bg-blue-900/30">
            <Network :size="20" class="text-blue-600 dark:text-blue-400" />
          </div>
          <span class="text-sm font-medium text-gray-600 dark:text-gray-400"
            >上传速度</span
          >
        </div>
        <div class="mb-2 text-3xl font-bold">
          {{ formatSpeed(realtimeData?.network_io?.upload_speed || 0) }}
        </div>
        <div class="text-sm text-gray-500 dark:text-gray-400">
          当前上传速率
        </div>
      </ElCard>

      <!-- 下载速度 -->
      <ElCard shadow="hover">
        <div class="mb-3 flex items-center gap-2">
          <div class="rounded-lg bg-green-100 p-2 dark:bg-green-900/30">
            <Network :size="20" class="text-green-600 dark:text-green-400" />
          </div>
          <span class="text-sm font-medium text-gray-600 dark:text-gray-400"
            >下载速度</span
          >
        </div>
        <div class="mb-2 text-3xl font-bold">
          {{ formatSpeed(realtimeData?.network_io?.download_speed || 0) }}
        </div>
        <div class="text-sm text-gray-500 dark:text-gray-400">
          当前下载速率
        </div>
      </ElCard>

      <!-- 总发送 -->
      <ElCard shadow="hover">
        <div class="mb-3 flex items-center gap-2">
          <div class="rounded-lg bg-purple-100 p-2 dark:bg-purple-900/30">
            <Network :size="20" class="text-purple-600 dark:text-purple-400" />
          </div>
          <span class="text-sm font-medium text-gray-600 dark:text-gray-400"
            >总发送</span
          >
        </div>
        <div class="mb-2 text-3xl font-bold">
          {{ formatBytes(realtimeData?.network_total?.bytes_sent || 0) }}
        </div>
        <div class="text-sm text-gray-500 dark:text-gray-400">
          累计发送数据
        </div>
      </ElCard>

      <!-- 总接收 -->
      <ElCard shadow="hover">
        <div class="mb-3 flex items-center gap-2">
          <div class="rounded-lg bg-orange-100 p-2 dark:bg-orange-900/30">
            <Network :size="20" class="text-orange-600 dark:text-orange-400" />
          </div>
          <span class="text-sm font-medium text-gray-600 dark:text-gray-400"
            >总接收</span
          >
        </div>
        <div class="mb-2 text-3xl font-bold">
          {{ formatBytes(realtimeData?.network_total?.bytes_recv || 0) }}
        </div>
        <div class="text-sm text-gray-500 dark:text-gray-400">
          累计接收数据
        </div>
      </ElCard>
    </div>

    <!-- 网络接口列表 -->
    <div class="grid grid-cols-1 gap-4">
      <ElCard
        v-for="(interfaceData, interfaceName) in serverData?.network_info?.interfaces || {}"
        :key="interfaceName"
        shadow="hover"
      >
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <Network :size="18" class="text-primary" />
              <span class="font-semibold">{{ interfaceName }}</span>
              <ElTag v-if="interfaceData.stats?.is_up" type="success" size="small">在线</ElTag>
              <ElTag v-else type="info" size="small">离线</ElTag>
            </div>
            <div class="flex items-center gap-2">
              <ElTag type="info" size="small">{{ interfaceData.stats?.speed || 0 }} Mbps</ElTag>
            </div>
          </div>
        </template>

        <ElDescriptions :column="2" border size="small">
          <ElDescriptionsItem label="接口名称">
            {{ interfaceName }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="状态">
            <ElTag v-if="interfaceData.stats?.is_up" type="success">在线</ElTag>
            <ElTag v-else type="info">离线</ElTag>
          </ElDescriptionsItem>
          <ElDescriptionsItem label="速度">
            {{ interfaceData.stats?.speed || 0 }} Mbps
          </ElDescriptionsItem>
          <ElDescriptionsItem label="MTU">
            {{ interfaceData.stats?.mtu || '-' }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="发送字节">
            {{ formatBytes(serverData?.network_info?.per_interface?.[interfaceName]?.bytes_sent || 0) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="接收字节">
            {{ formatBytes(serverData?.network_info?.per_interface?.[interfaceName]?.bytes_recv || 0) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="发送包数">
            {{ (serverData?.network_info?.per_interface?.[interfaceName]?.packets_sent || 0).toLocaleString() }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="接收包数">
            {{ (serverData?.network_info?.per_interface?.[interfaceName]?.packets_recv || 0).toLocaleString() }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="发送错误">
            {{ (serverData?.network_info?.per_interface?.[interfaceName]?.errout || 0).toLocaleString() }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="接收错误">
            {{ (serverData?.network_info?.per_interface?.[interfaceName]?.errin || 0).toLocaleString() }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="发送丢包">
            {{ (serverData?.network_info?.per_interface?.[interfaceName]?.dropout || 0).toLocaleString() }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="接收丢包">
            {{ (serverData?.network_info?.per_interface?.[interfaceName]?.dropin || 0).toLocaleString() }}
          </ElDescriptionsItem>
        </ElDescriptions>
      </ElCard>
    </div>

    <!-- 网络总计统计 -->
    <ElCard shadow="hover">
      <template #header>
        <div class="flex items-center gap-2">
          <Network :size="18" class="text-primary" />
          <span class="font-semibold">网络总计统计</span>
        </div>
      </template>

      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <!-- 发送统计 -->
        <div class="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
          <div class="mb-3 flex items-center gap-2">
            <div class="rounded-lg bg-blue-100 p-2 dark:bg-blue-900/30">
              <Network :size="16" class="text-blue-600 dark:text-blue-400" />
            </div>
            <span class="font-medium">发送统计</span>
          </div>
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400"
                >当前速度:</span
              >
              <span class="font-semibold">{{
                formatSpeed(realtimeData?.network_io?.upload_speed || 0)
              }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400"
                >总发送量:</span
              >
              <span class="font-semibold">{{
                formatBytes(serverData?.network_info?.total?.bytes_sent || 0)
              }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400"
                >发送包数:</span
              >
              <span class="font-semibold">{{
                (serverData?.network_info?.total?.packets_sent || 0).toLocaleString()
              }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400"
                >发送错误:</span
              >
              <span class="font-semibold">{{
                (serverData?.network_info?.total?.errout || 0).toLocaleString()
              }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400"
                >发送丢包:</span
              >
              <span class="font-semibold">{{
                (serverData?.network_info?.total?.dropout || 0).toLocaleString()
              }}</span>
            </div>
          </div>
        </div>

        <!-- 接收统计 -->
        <div class="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
          <div class="mb-3 flex items-center gap-2">
            <div class="rounded-lg bg-green-100 p-2 dark:bg-green-900/30">
              <Network :size="16" class="text-green-600 dark:text-green-400" />
            </div>
            <span class="font-medium">接收统计</span>
          </div>
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400"
                >当前速度:</span
              >
              <span class="font-semibold">{{
                formatSpeed(realtimeData?.network_io?.download_speed || 0)
              }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400"
                >总接收量:</span
              >
              <span class="font-semibold">{{
                formatBytes(serverData?.network_info?.total?.bytes_recv || 0)
              }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400"
                >接收包数:</span
              >
              <span class="font-semibold">{{
                (serverData?.network_info?.total?.packets_recv || 0).toLocaleString()
              }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400"
                >接收错误:</span
              >
              <span class="font-semibold">{{
                (serverData?.network_info?.total?.errin || 0).toLocaleString()
              }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400"
                >接收丢包:</span
              >
              <span class="font-semibold">{{
                (serverData?.network_info?.total?.dropin || 0).toLocaleString()
              }}</span>
            </div>
          </div>
        </div>
      </div>
    </ElCard>

    <!-- 实时网络IO -->
    <ElCard v-if="realtimeData?.network_io" shadow="hover">
      <template #header>
        <div class="flex items-center gap-2">
          <Network :size="18" class="text-primary" />
          <span class="font-semibold">实时网络IO</span>
        </div>
      </template>

      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div class="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
          <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
            上传速度
          </div>
          <div class="mb-2 text-2xl font-bold text-blue-600 dark:text-blue-400">
            {{ formatSpeed(realtimeData.network_io.upload_speed || 0) }}
          </div>
          <div class="text-xs text-gray-500 dark:text-gray-400">
            当前上传速率
          </div>
        </div>

        <div class="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
          <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
            下载速度
          </div>
          <div class="mb-2 text-2xl font-bold text-green-600 dark:text-green-400">
            {{ formatSpeed(realtimeData.network_io.download_speed || 0) }}
          </div>
          <div class="text-xs text-gray-500 dark:text-gray-400">
            当前下载速率
          </div>
        </div>
      </div>
    </ElCard>
  </div>
</template>
