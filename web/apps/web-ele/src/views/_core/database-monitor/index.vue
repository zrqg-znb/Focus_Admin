<script setup lang="ts">
import type {
  DatabaseConfig,
  DatabaseMonitorOverview,
  DatabaseRealtimeStats,
} from '#/api/core/database-monitor';
import type { CardListItem, CardListOptions } from '#/components/card-list';

import { computed, onMounted, onUnmounted, ref } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';

import { Page } from '@vben/common-ui';
import {
  BarChart,
  Database,
  LayoutDashboard,
  ListTree,
  Network,
} from '@vben/icons';

import {
  ElCard,
  ElMessage,
  ElOption,
  ElScrollbar,
  ElSelect,
  ElTag,
} from 'element-plus';

import {
  getDatabaseMonitorConfigsApi,
  getDatabaseMonitorOverviewApi,
  getDatabaseRealtimeStatsApi,
} from '#/api/core/database-monitor';
import { CardList } from '#/components/card-list';

import ConnectionsPanel from './modules/connections-panel.vue';
import OverviewPanel from './modules/overview-panel.vue';
import PerformancePanel from './modules/performance-panel.vue';
import TablesPanel from './modules/tables-panel.vue';

defineOptions({ name: 'DatabaseMonitor' });

// 菜单项类型
interface MonitorMenuItem extends CardListItem {
  id: string;
  name: string;
  key: 'connections' | 'overview' | 'performance' | 'tables';
  icon?: string;
}

// 菜单项数据
const menuItems = ref<MonitorMenuItem[]>([
  { id: 'overview', name: '概览信息', key: 'overview' },
  { id: 'connections', name: '连接信息', key: 'connections' },
  { id: 'performance', name: '性能统计', key: 'performance' },
  { id: 'tables', name: '表统计', key: 'tables' },
]);

// 图标映射
const iconMap: Record<string, any> = {
  overview: LayoutDashboard,
  connections: Network,
  performance: BarChart,
  tables: ListTree,
};

const selectedMenuId = ref<string>('overview');

// CardList 配置
const cardListOptions: CardListOptions<MonitorMenuItem> = {
  searchFields: [{ field: 'name' }],
  displayMode: 'center',
  titleField: 'name',
};

// 数据库配置列表
const databaseConfigs = ref<DatabaseConfig[]>([]);
const selectedDatabase = ref<string>('');
const loading = ref(false);

// 监控数据
const monitorData = ref<DatabaseMonitorOverview | null>(null);
const realtimeData = ref<DatabaseRealtimeStats | null>(null);

// 自动刷新
const autoRefresh = ref(true);
const refreshInterval = ref<null | number>(null);

// 获取当前图标组件
const currentIcon = computed(() => {
  return iconMap[selectedMenuId.value] || LayoutDashboard;
});

// 获取当前标题
const currentTitle = computed(() => {
  const item = menuItems.value.find((m) => m.id === selectedMenuId.value);
  return item?.name || '概览信息';
});

// 获取数据库配置列表
async function loadDatabaseConfigs() {
  try {
    const configs = await getDatabaseMonitorConfigsApi();
    databaseConfigs.value = configs;

    // 默认选择第一个数据库
    if (configs.length > 0 && !selectedDatabase.value) {
      // 使用 db_name 字段作为标识（Django配置的key）
      selectedDatabase.value = configs[0].db_name;
      // 自动加载该数据库的监控数据
      await loadMonitorData();
    }
  } catch (error) {
    console.error('Failed to load database configs:', error);
    ElMessage.error('加载数据库配置失败');
  }
}

// 加载监控数据
async function loadMonitorData(showMessage = false) {
  if (!selectedDatabase.value) return;

  // 获取当前数据库名称用于显示
  const currentDbConfig = databaseConfigs.value.find(
    (config) => config.db_name === selectedDatabase.value,
  );
  const dbDisplayName = currentDbConfig?.name || selectedDatabase.value;

  // 显示加载提示
  if (showMessage) {
    ElMessage.warning(`正在加载 ${dbDisplayName}...`);
  }

  loading.value = true;
  try {
    const [overview, realtime] = await Promise.all([
      getDatabaseMonitorOverviewApi(selectedDatabase.value),
      getDatabaseRealtimeStatsApi(selectedDatabase.value),
    ]);

    monitorData.value = overview;
    realtimeData.value = realtime;

    // 显示成功提示
    if (showMessage) {
      ElMessage.success(`${dbDisplayName} 加载成功`);
    }
  } catch (error) {
    console.error('Failed to load monitor data:', error);
    ElMessage.error(`加载 ${dbDisplayName} 失败`);
  } finally {
    loading.value = false;
  }
}

// 切换数据库
function handleDatabaseChange(dbName: string) {
  selectedDatabase.value = dbName;
  loadMonitorData(true); // 切换数据库时显示加载提示
}

// 菜单选择
function handleMenuSelect(menuId: string | undefined) {
  if (menuId) {
    selectedMenuId.value = menuId;
  }
}

// 手动刷新
function handleRefresh() {
  loadMonitorData();
}

// 切换自动刷新
function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value;
  if (autoRefresh.value) {
    startAutoRefresh();
  } else {
    stopAutoRefresh();
  }
}

// 开始自动刷新
function startAutoRefresh() {
  if (refreshInterval.value) return;

  refreshInterval.value = window.setInterval(() => {
    if (selectedDatabase.value) {
      loadMonitorData();
    }
  }, 3000); // 每3秒刷新一次
}

// 停止自动刷新
function stopAutoRefresh() {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value);
    refreshInterval.value = null;
  }
}

onMounted(async () => {
  await loadDatabaseConfigs();
  // loadDatabaseConfigs 会自动加载第一个数据库的数据
  if (autoRefresh.value) {
    startAutoRefresh();
  }
});

onUnmounted(() => {
  stopAutoRefresh();
});

// 路由离开时停止轮询
onBeforeRouteLeave(() => {
  stopAutoRefresh();
  return true;
});
</script>

<template>
  <Page auto-content-height>
    <!-- 主内容区域 -->
    <div class="flex h-full">
      <!-- 左侧菜单 -->
      <div class="w-1/6 flex-shrink-0">
        <CardList
          :items="menuItems"
          :selected-id="selectedMenuId"
          :options="cardListOptions"
          :loading="false"
          class="database-monitor-menu"
          @select="handleMenuSelect"
        >
          <template #item="{ item }">
            <div class="flex items-center gap-2">
              <component :is="iconMap[item.id]" :size="16" />
              <span class="text-sm font-medium">{{ item.name }}</span>
            </div>
          </template>
        </CardList>
      </div>

      <!-- 右侧内容 -->
      <div class="flex-1">
        <!-- 概览信息 -->
        <ElCard
          v-if="selectedMenuId === 'overview'"
          class="flex h-full flex-col"
          style="border: none"
          shadow="never"
          :body-style="{
            display: 'flex',
            flexDirection: 'column',
            flex: 1,
            minHeight: 0,
            padding: 0,
            overflow: 'hidden',
          }"
        >
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <component :is="currentIcon" :size="20" class="text-primary" />
                <span class="font-semibold">{{ currentTitle }}</span>
              </div>
              <div class="flex items-center gap-3">
                <!-- 数据库选择器 -->
                <ElSelect
                  v-model="selectedDatabase"
                  placeholder="请选择数据库"
                  style="width: 240px"
                  @change="handleDatabaseChange"
                >
                  <ElOption
                    v-for="config in databaseConfigs"
                    :key="config.db_name"
                    :label="config.name"
                    :value="config.db_name"
                  >
                    <div class="flex items-center justify-between">
                      <span>{{ config.name }}</span>
                      <ElTag size="small" type="info">
                        {{ config.db_type }}
                      </ElTag>
                    </div>
                  </ElOption>
                </ElSelect>

                <!-- 状态标签 -->
                <ElTag :type="autoRefresh ? 'success' : 'info'">
                  {{ autoRefresh ? '自动刷新中' : '已暂停' }}
                </ElTag>
                <ElTag
                  v-if="monitorData"
                  :type="
                    monitorData.status === 'connected' ? 'success' : 'danger'
                  "
                >
                  {{ monitorData.status === 'connected' ? '已连接' : '未连接' }}
                </ElTag>
              </div>
            </div>
          </template>

          <ElScrollbar class="monitor-scrollbar">
            <div class="p-4">
              <OverviewPanel
                :monitor-data="monitorData"
                :realtime-data="realtimeData"
              />
            </div>
          </ElScrollbar>
        </ElCard>

        <!-- 连接信息 -->
        <ElCard
          v-else-if="selectedMenuId === 'connections'"
          class="flex h-full flex-col"
          style="border: none"
          shadow="never"
          :body-style="{
            display: 'flex',
            flexDirection: 'column',
            flex: 1,
            minHeight: 0,
            padding: 0,
            overflow: 'hidden',
          }"
        >
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <component :is="currentIcon" :size="20" class="text-primary" />
                <span class="font-semibold">{{ currentTitle }}</span>
              </div>
              <div class="flex items-center gap-3">
                <!-- 数据库选择器 -->
                <ElSelect
                  v-model="selectedDatabase"
                  placeholder="请选择数据库"
                  style="width: 240px"
                  @change="handleDatabaseChange"
                >
                  <ElOption
                    v-for="config in databaseConfigs"
                    :key="config.db_name"
                    :label="config.name"
                    :value="config.db_name"
                  >
                    <div class="flex items-center justify-between">
                      <span>{{ config.name }}</span>
                      <ElTag size="small" type="info">
                        {{ config.db_type }}
                      </ElTag>
                    </div>
                  </ElOption>
                </ElSelect>

                <!-- 状态标签 -->
                <ElTag :type="autoRefresh ? 'success' : 'info'">
                  {{ autoRefresh ? '自动刷新中' : '已暂停' }}
                </ElTag>
                <ElTag
                  v-if="monitorData"
                  :type="
                    monitorData.status === 'connected' ? 'success' : 'danger'
                  "
                >
                  {{ monitorData.status === 'connected' ? '已连接' : '未连接' }}
                </ElTag>
              </div>
            </div>
          </template>

          <ElScrollbar class="monitor-scrollbar">
            <div class="p-4">
              <ConnectionsPanel
                :monitor-data="monitorData"
                :realtime-data="realtimeData"
              />
            </div>
          </ElScrollbar>
        </ElCard>

        <!-- 性能统计 -->
        <ElCard
          v-else-if="selectedMenuId === 'performance'"
          class="flex h-full flex-col"
          style="border: none"
          shadow="never"
          :body-style="{
            display: 'flex',
            flexDirection: 'column',
            flex: 1,
            minHeight: 0,
            padding: 0,
            overflow: 'hidden',
          }"
        >
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <component :is="currentIcon" :size="20" class="text-primary" />
                <span class="font-semibold">{{ currentTitle }}</span>
              </div>
              <div class="flex items-center gap-3">
                <!-- 数据库选择器 -->
                <ElSelect
                  v-model="selectedDatabase"
                  placeholder="请选择数据库"
                  style="width: 240px"
                  @change="handleDatabaseChange"
                >
                  <ElOption
                    v-for="config in databaseConfigs"
                    :key="config.db_name"
                    :label="config.name"
                    :value="config.db_name"
                  >
                    <div class="flex items-center justify-between">
                      <span>{{ config.name }}</span>
                      <ElTag size="small" type="info">
                        {{ config.db_type }}
                      </ElTag>
                    </div>
                  </ElOption>
                </ElSelect>

                <!-- 状态标签 -->
                <ElTag :type="autoRefresh ? 'success' : 'info'">
                  {{ autoRefresh ? '自动刷新中' : '已暂停' }}
                </ElTag>
                <ElTag
                  v-if="monitorData"
                  :type="
                    monitorData.status === 'connected' ? 'success' : 'danger'
                  "
                >
                  {{ monitorData.status === 'connected' ? '已连接' : '未连接' }}
                </ElTag>
              </div>
            </div>
          </template>

          <ElScrollbar class="monitor-scrollbar">
            <div class="p-4">
              <PerformancePanel
                :monitor-data="monitorData"
                :realtime-data="realtimeData"
              />
            </div>
          </ElScrollbar>
        </ElCard>

        <!-- 表统计 -->
        <ElCard
          v-else-if="selectedMenuId === 'tables'"
          class="flex h-full flex-col"
          style="border: none"
          shadow="never"
          :body-style="{
            display: 'flex',
            flexDirection: 'column',
            flex: 1,
            minHeight: 0,
            padding: 0,
            overflow: 'hidden',
          }"
        >
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <component :is="currentIcon" :size="20" class="text-primary" />
                <span class="font-semibold">{{ currentTitle }}</span>
              </div>
              <div class="flex items-center gap-3">
                <!-- 数据库选择器 -->
                <ElSelect
                  v-model="selectedDatabase"
                  placeholder="请选择数据库"
                  style="width: 240px"
                  @change="handleDatabaseChange"
                >
                  <ElOption
                    v-for="config in databaseConfigs"
                    :key="config.db_name"
                    :label="config.name"
                    :value="config.db_name"
                  >
                    <div class="flex items-center justify-between">
                      <span>{{ config.name }}</span>
                      <ElTag size="small" type="info">
                        {{ config.db_type }}
                      </ElTag>
                    </div>
                  </ElOption>
                </ElSelect>

                <!-- 状态标签 -->
                <ElTag :type="autoRefresh ? 'success' : 'info'">
                  {{ autoRefresh ? '自动刷新中' : '已暂停' }}
                </ElTag>
                <ElTag
                  v-if="monitorData"
                  :type="
                    monitorData.status === 'connected' ? 'success' : 'danger'
                  "
                >
                  {{ monitorData.status === 'connected' ? '已连接' : '未连接' }}
                </ElTag>
              </div>
            </div>
          </template>

          <ElScrollbar class="monitor-scrollbar">
            <div class="p-4">
              <TablesPanel
                :monitor-data="monitorData"
                :realtime-data="realtimeData"
              />
            </div>
          </ElScrollbar>
        </ElCard>

        <!-- 其他菜单内容占位 -->
        <ElCard v-else class="h-full" shadow="never">
          <div class="flex h-full items-center justify-center text-gray-400">
            <div class="text-center">
              <component :is="currentIcon" :size="48" class="mx-auto mb-4" />
              <p class="text-lg">{{ currentTitle }}</p>
              <p class="mt-2 text-sm">功能开发中...</p>
            </div>
          </div>
        </ElCard>
      </div>
    </div>
  </Page>
</template>

<style scoped>
.monitor-scrollbar {
  flex: 1;
  min-height: 0;
}
</style>
