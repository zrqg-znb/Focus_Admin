<script setup lang="ts">
import type {
  DatabaseMonitorOverview,
  DatabaseRealtimeStats,
  DatabaseTableStats,
} from '#/api/core/database-monitor';

import { computed, ref } from 'vue';

import { BarChart, Database, ListTree } from '@vben/icons';

import { ElCard, ElEmpty, ElInput, ElTag } from 'element-plus';

defineOptions({ name: 'TablesPanel' });

const props = defineProps<{
  monitorData: DatabaseMonitorOverview | null;
  realtimeData: DatabaseRealtimeStats | null;
}>();

// 基本信息
const basicInfo = computed(() => props.monitorData?.basic_info);

// 表统计数据
const tableStats = computed(() => props.monitorData?.table_stats || []);

// 搜索关键词
const searchKeyword = ref('');

// 过滤后的表数据
const filteredTables = computed(() => {
  if (!searchKeyword.value) return tableStats.value;
  
  const keyword = searchKeyword.value.toLowerCase();
  return tableStats.value.filter((table) => {
    const tableName = getTableName(table).toLowerCase();
    const schemaName = getSchemaName(table).toLowerCase();
    return tableName.includes(keyword) || schemaName.includes(keyword);
  });
});

// 获取表名
function getTableName(table: DatabaseTableStats): string {
  return table.tablename || table.table_name || '-';
}

// 获取模式名
function getSchemaName(table: DatabaseTableStats): string {
  return table.schemaname || 'public';
}

// 格式化字节大小
function formatBytes(bytes: number | undefined): string {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}

// 格式化大数字
function formatNumber(num: number | undefined): string {
  if (!num) return '0';
  if (num >= 1000000000) return `${(num / 1000000000).toFixed(2)}B`;
  if (num >= 1000000) return `${(num / 1000000).toFixed(2)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(2)}K`;
  return num.toString();
}

// 获取数据库类型
const dbType = computed(() => basicInfo.value?.db_type || '');

// 按大小排序的表
const tablesBySize = computed(() => {
  const tables = [...filteredTables.value];
  return tables.sort((a, b) => {
    const sizeA = getTableSize(a);
    const sizeB = getTableSize(b);
    return sizeB - sizeA;
  }).slice(0, 10); // 只显示前10个
});

// 获取表大小
function getTableSize(table: DatabaseTableStats): number {
  // PostgreSQL: 使用 total_size_bytes
  if (table.total_size_bytes) return table.total_size_bytes;
  // SQL Server: 使用 total_size_kb
  if (table.total_size_kb) return table.total_size_kb * 1024;
  // MySQL: 使用 data_length + index_length
  if (table.data_length) return table.data_length + (table.index_length || 0);
  return 0;
}

// 获取表行数
function getTableRows(table: DatabaseTableStats): number {
  return table.table_rows || table.live_tuples || 0;
}
</script>

<template>
  <div class="space-y-4">
    <!-- 统计概览 -->
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
      <!-- 总表数 -->
      <ElCard shadow="hover">
        <div class="flex items-center justify-between">
          <div>
            <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
              总表数
            </div>
            <div class="text-3xl font-bold">
              {{ tableStats.length }}
            </div>
          </div>
          <div class="rounded-lg bg-blue-100 p-3 dark:bg-blue-900/30">
            <ListTree :size="32" class="text-blue-600 dark:text-blue-400" />
          </div>
        </div>
      </ElCard>

      <!-- 总行数 -->
      <ElCard shadow="hover">
        <div class="flex items-center justify-between">
          <div>
            <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
              总行数
            </div>
            <div class="text-3xl font-bold">
              {{ formatNumber(tableStats.reduce((sum, t) => sum + getTableRows(t), 0)) }}
            </div>
          </div>
          <div class="rounded-lg bg-green-100 p-3 dark:bg-green-900/30">
            <BarChart :size="32" class="text-green-600 dark:text-green-400" />
          </div>
        </div>
      </ElCard>

      <!-- 总大小 -->
      <ElCard shadow="hover">
        <div class="flex items-center justify-between">
          <div>
            <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
              总大小
            </div>
            <div class="text-3xl font-bold">
              {{ formatBytes(tableStats.reduce((sum, t) => sum + getTableSize(t), 0)) }}
            </div>
          </div>
          <div class="rounded-lg bg-purple-100 p-3 dark:bg-purple-900/30">
            <Database :size="32" class="text-purple-600 dark:text-purple-400" />
          </div>
        </div>
      </ElCard>

      <!-- 搜索框 -->
      <ElCard shadow="hover">
        <div class="flex h-full flex-col justify-center">
          <div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
            搜索表
          </div>
          <ElInput
            v-model="searchKeyword"
            placeholder="输入表名搜索..."
            clearable
          />
        </div>
      </ElCard>
    </div>

    <!-- Top 10 最大的表 -->
    <ElCard shadow="hover">
      <template #header>
        <div class="flex items-center gap-2">
          <Database :size="18" class="text-primary" />
          <span class="font-semibold">Top 10 最大的表</span>
        </div>
      </template>

      <div v-if="tablesBySize.length === 0" class="py-12">
        <ElEmpty description="暂无表数据" />
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th class="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">
                排名
              </th>
              <th v-if="dbType === 'POSTGRESQL'" class="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">
                模式
              </th>
              <th class="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">
                表名
              </th>
              <th class="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-400">
                行数
              </th>
              <th class="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-400">
                大小
              </th>
              <th v-if="dbType === 'MYSQL'" class="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-400">
                数据大小
              </th>
              <th v-if="dbType === 'MYSQL'" class="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-400">
                索引大小
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr
              v-for="(table, index) in tablesBySize"
              :key="index"
              class="hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              <td class="px-4 py-3">
                <ElTag
                  :type="index === 0 ? 'danger' : index === 1 ? 'warning' : index === 2 ? 'success' : 'info'"
                  size="small"
                >
                  #{{ index + 1 }}
                </ElTag>
              </td>
              <td v-if="dbType === 'POSTGRESQL'" class="px-4 py-3 text-gray-600 dark:text-gray-400">
                {{ getSchemaName(table) }}
              </td>
              <td class="px-4 py-3 font-mono font-medium">
                {{ getTableName(table) }}
              </td>
              <td class="px-4 py-3 text-right font-mono">
                {{ formatNumber(getTableRows(table)) }}
              </td>
              <td class="px-4 py-3 text-right font-mono font-semibold">
                {{ formatBytes(getTableSize(table)) }}
              </td>
              <td v-if="dbType === 'MYSQL'" class="px-4 py-3 text-right font-mono text-sm text-gray-600">
                {{ formatBytes(table.data_length) }}
              </td>
              <td v-if="dbType === 'MYSQL'" class="px-4 py-3 text-right font-mono text-sm text-gray-600">
                {{ formatBytes(table.index_length) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </ElCard>

    <!-- 所有表列表 -->
    <ElCard shadow="hover">
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <ListTree :size="18" class="text-primary" />
            <span class="font-semibold">所有表列表</span>
            <ElTag type="info" size="small">{{ filteredTables.length }} 个表</ElTag>
          </div>
        </div>
      </template>

      <div v-if="filteredTables.length === 0" class="py-12">
        <ElEmpty :description="searchKeyword ? '未找到匹配的表' : '暂无表数据'" />
      </div>

      <div v-else class="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
        <div
          v-for="(table, index) in filteredTables"
          :key="index"
          class="rounded-lg border border-gray-200 p-4 transition-all hover:border-primary hover:shadow-md dark:border-gray-700"
        >
          <!-- 表头 -->
          <div class="mb-3 flex items-start justify-between">
            <div class="flex-1">
              <div v-if="dbType === 'POSTGRESQL'" class="mb-1 text-xs text-gray-500">
                {{ getSchemaName(table) }}
              </div>
              <div class="font-mono font-semibold text-gray-900 dark:text-gray-100">
                {{ getTableName(table) }}
              </div>
            </div>
            <Database :size="20" class="text-gray-400" />
          </div>

          <!-- 统计信息 -->
          <div class="space-y-2">
            <div class="flex items-center justify-between text-sm">
              <span class="text-gray-600 dark:text-gray-400">行数</span>
              <span class="font-mono text-600">{{ formatNumber(getTableRows(table)) }}</span>
            </div>
            <div class="flex items-center justify-between text-sm">
              <span class="text-gray-600 dark:text-gray-400">大小</span>
              <span class="font-mono text-600">{{ formatBytes(getTableSize(table)) }}</span>
            </div>

            <!-- PostgreSQL 特有 -->
            <template v-if="dbType === 'POSTGRESQL'">
              <div v-if="table.inserts !== undefined" class="flex items-center justify-between text-sm">
                <span class="text-gray-600 dark:text-gray-400">插入</span>
                <span class="font-mono text-green-600">{{ formatNumber(table.inserts) }}</span>
              </div>
              <div v-if="table.updates !== undefined" class="flex items-center justify-between text-sm">
                <span class="text-gray-600 dark:text-gray-400">更新</span>
                <span class="font-mono text-blue-600">{{ formatNumber(table.updates) }}</span>
              </div>
              <div v-if="table.deletes !== undefined" class="flex items-center justify-between text-sm">
                <span class="text-gray-600 dark:text-gray-400">删除</span>
                <span class="font-mono text-red-600">{{ formatNumber(table.deletes) }}</span>
              </div>
              <div v-if="table.dead_tuples !== undefined && table.dead_tuples > 0" class="flex items-center justify-between text-sm">
                <span class="text-gray-600 dark:text-gray-400">死元组</span>
                <span class="font-mono text-orange-600">{{ formatNumber(table.dead_tuples) }}</span>
              </div>
            </template>

            <!-- MySQL 特有 -->
            <template v-if="dbType === 'MYSQL'">
              <div v-if="table.data_length !== undefined" class="flex items-center justify-between text-sm">
                <span class="text-gray-600 dark:text-gray-400">数据大小</span>
                <span class="font-mono text-sm">{{ formatBytes(table.data_length) }}</span>
              </div>
              <div v-if="table.index_length !== undefined" class="flex items-center justify-between text-sm">
                <span class="text-gray-600 dark:text-gray-400">索引大小</span>
                <span class="font-mono text-sm">{{ formatBytes(table.index_length) }}</span>
              </div>
              <div v-if="table.auto_increment !== undefined" class="flex items-center justify-between text-sm">
                <span class="text-gray-600 dark:text-gray-400">自增值</span>
                <span class="font-mono text-sm">{{ formatNumber(table.auto_increment) }}</span>
              </div>
            </template>

            <!-- SQL Server 特有 -->
            <template v-if="dbType === 'SQLSERVER'">
              <div v-if="table.used_size_kb !== undefined" class="flex items-center justify-between text-sm">
                <span class="text-gray-600 dark:text-gray-400">已用大小</span>
                <span class="font-mono text-sm">{{ formatBytes(table.used_size_kb * 1024) }}</span>
              </div>
              <div v-if="table.data_size_kb !== undefined" class="flex items-center justify-between text-sm">
                <span class="text-gray-600 dark:text-gray-400">数据大小</span>
                <span class="font-mono text-sm">{{ formatBytes(table.data_size_kb * 1024) }}</span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </ElCard>

    <!-- 表统计说明 -->
    <ElCard shadow="hover">
      <template #header>
        <div class="flex items-center gap-2">
          <BarChart :size="18" class="text-primary" />
          <span class="font-semibold">表统计说明</span>
        </div>
      </template>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">表大小</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            表占用的磁盘空间，包括数据和索引
          </div>
        </div>
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
          <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">行数</div>
          <div class="text-sm text-gray-600 dark:text-gray-400">
            表中的数据行总数
          </div>
        </div>
        
        <!-- PostgreSQL 说明 -->
        <template v-if="dbType === 'POSTGRESQL'">
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">死元组</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              已删除但未清理的行，需要VACUUM清理
            </div>
          </div>
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">插入/更新/删除</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              表的增删改操作统计
            </div>
          </div>
        </template>

        <!-- MySQL 说明 -->
        <template v-if="dbType === 'MYSQL'">
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">数据大小</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              表数据占用的空间
            </div>
          </div>
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">索引大小</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              表索引占用的空间
            </div>
          </div>
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">自增值</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              自增主键的当前值
            </div>
          </div>
        </template>

        <!-- SQL Server 说明 -->
        <template v-if="dbType === 'SQLSERVER'">
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">已用大小</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              表实际使用的空间
            </div>
          </div>
          <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <div class="mb-1 font-medium text-gray-700 dark:text-gray-300">数据大小</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              表数据占用的空间
            </div>
          </div>
        </template>
      </div>
    </ElCard>
  </div>
</template>
