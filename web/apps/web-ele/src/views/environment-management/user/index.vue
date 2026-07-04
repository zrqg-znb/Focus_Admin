<script lang="ts" setup>
import type {
  EnvironmentFilterOptions,
  EnvironmentItem,
  EnvironmentRecord,
  QueueItem,
} from '#/api/environment-management';

import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { Clock, IconifyIcon, RefreshCw } from '@vben/icons';
import { useUserStore } from '@vben/stores';

import {
  ElButton,
  ElDialog,
  ElEmpty,
  ElMessage,
  ElMessageBox,
  ElPagination,
  ElSegmented,
  ElTag,
  ElTable,
  ElTableColumn,
} from 'element-plus';

import {
  cancelMyQueueApi,
  favoriteEnvironmentApi,
  getEnvironmentFilterOptionsApi,
  getEnvironmentAnnouncementApi,
  listEnvironmentQueueApi,
  listEnvironmentRecordsApi,
  listEnvironmentsApi,
  occupyEnvironmentApi,
  queueEnvironmentApi,
  releaseEnvironmentApi,
  unfavoriteEnvironmentApi,
} from '#/api/environment-management';
import { useZqTable } from '#/components/zq-table';

import {
  environmentUsageHeaderFilters,
  queueTableColumns,
  recordTableColumns,
  useEnvironmentUsageColumns,
} from './data';
import EnvironmentHeaderFilter from '../components/EnvironmentHeaderFilter.vue';
import {
  buildHeaderFilterParams,
  countActiveHeaderFilters,
  type HeaderFilterConfig,
  type HeaderFilterValues,
} from '../components/header-filter';
import EnvironmentDetailDrawer from './components/EnvironmentDetailDrawer.vue';

const cardLoading = ref(false);
const userStore = useUserStore();
const rows = ref<EnvironmentItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(12);
const viewMode = ref<'card' | 'table'>('table');
const tick = ref(Date.now());
let timer: null | number = null;

const headerFilterValues = ref<HeaderFilterValues>({});
const filterDialogVisible = ref(false);
const filterOptions = ref<EnvironmentFilterOptions>({
  binding_device_assets: [],
  categories: [],
  current_users: [],
  device_statuses: [],
  device_types: [],
  device_options: [],
  devices: [],
  domains: [],
  favorite_states: [],
  projects: [],
  queue_states: [],
  statuses: [],
  vehicle_models: [],
});

const queueDialogVisible = ref(false);
const queueDialogTitle = ref('');
const queueRows = ref<QueueItem[]>([]);
const recordDialogVisible = ref(false);
const recordDialogTitle = ref('');
const recordRows = ref<EnvironmentRecord[]>([]);
const recordLoading = ref(false);
const recordEnvironmentId = ref('');
const recordPage = ref(1);
const recordPageSize = ref(20);
const recordTotal = ref(0);
const detailDrawerVisible = ref(false);
const detailEnvironment = ref<EnvironmentItem | null>(null);

const viewOptions = [
  { label: '列表', value: 'table' },
  { label: '平铺', value: 'card' },
];
const rdpInstallerUrl = '/tools/focus-rdp/install-focus-rdp-protocol.ps1';

const favoriteCount = computed(
  () => rows.value.filter((item) => item.is_favorite).length,
);
const activeFilterCount = computed(() =>
  countActiveHeaderFilters(headerFilterValues.value),
);
const idleCount = computed(
  () => rows.value.filter((item) => item.status === 'idle').length,
);
const occupiedCount = computed(
  () => rows.value.filter((item) => item.status === 'occupied').length,
);

const currentUserId = computed(() => {
  const userInfo = userStore.userInfo as any;
  return String(userInfo?.userId || userInfo?.id || userInfo?.user_id || '');
});

const [Grid, gridApi] = useZqTable<EnvironmentItem>({
  tableTitle: '环境使用',
  class: 'environment-grid',
  gridOptions: {
    columns: useEnvironmentUsageColumns(),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page: tablePage }: any) => {
          const result = await listEnvironmentsApi({
            ...buildHeaderFilterParams(
              environmentUsageHeaderFilters,
              headerFilterValues.value,
            ),
            page: tablePage.currentPage,
            pageSize: tablePage.pageSize,
          });
          rows.value = result.items || [];
          total.value = result.total || 0;
          return result;
        },
      },
    },
    pagerConfig: { enabled: true, pageSize: 20, pageSizes: [12, 20, 40, 80] },
    toolbarConfig: { custom: true, refresh: true, search: false, zoom: true },
  },
});

function formatDuration(seconds: number) {
  const safeSeconds = Math.max(Number(seconds || 0), 0);
  const h = Math.floor(safeSeconds / 3600);
  const m = Math.floor((safeSeconds % 3600) / 60);
  const s = safeSeconds % 60;
  if (h > 0) return `${h}时${m}分`;
  if (m > 0) return `${m}分${s}秒`;
  return `${s}秒`;
}

function occupiedSeconds(row: EnvironmentItem) {
  // 占用时长以后端 occupied_at 为准，本地 tick 只负责让 UI 每秒刷新，不改变真实占用记录。
  if (row.status !== 'occupied' || !row.occupied_at) return 0;
  return Math.max(
    Math.floor((tick.value - new Date(row.occupied_at).getTime()) / 1000),
    row.occupied_seconds || 0,
  );
}

function canOpenRdp(row: EnvironmentItem) {
  // RDP 控制台只给当前占用人展示，避免有使用权限但未占用的人绕过占用流程直接拉起远程桌面。
  if (row.is_current_user_occupying) return true;
  return Boolean(
    row.can_use_environment
      && row.status === 'occupied'
      && row.current_user_id
      && currentUserId.value
      && String(row.current_user_id) === currentUserId.value,
  );
}

function canOccupy(row: EnvironmentItem) {
  // 空闲但存在等待队列时，只有队首用户可以占用；其他用户应继续排队，不能被“空闲”状态误导成可占用。
  return Boolean(
    row.can_use_environment
      && row.status === 'idle'
      && (Number(row.queue_count || 0) === 0 || Number(row.my_queue_position || 0) === 1),
  );
}

function canRelease(row: EnvironmentItem) {
  // 维持既有交互：占用中环境展示释放入口，最终权限仍以后端“占用人或管理员”校验为准。
  return Boolean(row.can_use_environment && row.status === 'occupied');
}

function canQueue(row: EnvironmentItem) {
  // A 释放后环境会变成 idle，但等待队列仍保留。此时非队首用户不能占用，必须仍能看到排队入口。
  return Boolean(
    row.can_use_environment
      && !row.my_queue_id
      && !row.is_current_user_occupying
      && (row.status === 'occupied' || (row.status === 'idle' && Number(row.queue_count || 0) > 0)),
  );
}

function canCancelQueue(row: EnvironmentItem) {
  return Boolean(row.can_use_environment && row.my_queue_id);
}

async function loadCards() {
  cardLoading.value = true;
  try {
    const result = await listEnvironmentsApi({
      ...buildHeaderFilterParams(
        environmentUsageHeaderFilters,
        headerFilterValues.value,
      ),
      page: page.value,
      pageSize: pageSize.value,
    });
    rows.value = result.items || [];
    total.value = result.total || 0;
  } finally {
    cardLoading.value = false;
  }
}

async function loadData() {
  if (viewMode.value === 'table') {
    await gridApi.reload();
  } else {
    await loadCards();
  }
}

function resetPageAndLoad() {
  page.value = 1;
  if (viewMode.value === 'table') {
    gridApi.handlePageChange(1, gridApi.pagination.pageSize);
  } else {
    loadCards();
  }
}

function getHeaderFilterConfig(column: any) {
  const key = String(column?.key || column?.prop || '');
  return environmentUsageHeaderFilters.find((item) => item.columnKey === key);
}

function getHeaderFilterOptions(config?: HeaderFilterConfig) {
  return config?.optionKey ? filterOptions.value[config.optionKey] || [] : [];
}

function applyHeaderFilter(config: HeaderFilterConfig, value: any) {
  headerFilterValues.value = {
    ...headerFilterValues.value,
    [config.columnKey]: value,
  };
  resetPageAndLoad();
}

function clearHeaderFilter(config: HeaderFilterConfig) {
  const nextValues = { ...headerFilterValues.value };
  delete nextValues[config.columnKey];
  headerFilterValues.value = nextValues;
  resetPageAndLoad();
}

function clearAllHeaderFilters() {
  headerFilterValues.value = {};
  resetPageAndLoad();
}

async function requireOperationAnnouncement(actionName: string) {
  const announcement = await getEnvironmentAnnouncementApi();
  if (announcement.enabled) {
    await ElMessageBox.confirm(
      `<div class="environment-announcement-content">${announcement.content_html || ''}</div>`,
      announcement.title || '公告',
      {
        confirmButtonText: '我已了解并继续',
        cancelButtonText: '取消',
        dangerouslyUseHTMLString: true,
        customClass: 'environment-announcement-dialog',
        type: 'warning',
      },
    );
  } else {
    await ElMessageBox.confirm(`确定要${actionName}该环境吗？`, '操作确认', {
      type: 'warning',
    });
  }
  return true;
}

async function toggleFavorite(row: EnvironmentItem) {
  const isCurrentlyFavorite = row.is_favorite;
  const updated = isCurrentlyFavorite
    ? await unfavoriteEnvironmentApi(row.id)
    : await favoriteEnvironmentApi(row.id);
  Object.assign(row, updated);
  rows.value.sort((a, b) => Number(b.is_favorite) - Number(a.is_favorite));

  if (!isCurrentlyFavorite) {
    ElMessage({
      message: `已将 ${row.ip_address} 加入收藏`,
      type: 'success',
      duration: 2000,
    });
  } else {
    ElMessage({
      message: `已取消收藏 ${row.ip_address}`,
      type: 'info',
      duration: 2000,
    });
  }
}

async function occupy(row: EnvironmentItem) {
  await requireOperationAnnouncement('占用');
  const result = await occupyEnvironmentApi(row.id);
  ElMessage.success(result.message);
  Object.assign(row, result.environment);
  openRdp(result.environment);
}

async function release(row: EnvironmentItem) {
  await ElMessageBox.confirm(`确定要释放该环境吗？`, '操作确认', { type: 'warning' });
  const result = await releaseEnvironmentApi(row.id);
  ElMessage.success(result.message);
  Object.assign(row, result.environment);
}

async function queue(row: EnvironmentItem) {
  await requireOperationAnnouncement('排队');
  Object.assign(row, await queueEnvironmentApi(row.id));
  ElMessage.success('排队成功');
}

async function cancelQueue(row: EnvironmentItem) {
  Object.assign(row, await cancelMyQueueApi(row.id));
  ElMessage.success('已取消排队');
}

function openDetail(row: EnvironmentItem) {
  detailEnvironment.value = row;
  detailDrawerVisible.value = true;
}

function showRdpInstallGuide() {
  ElMessageBox.alert(
    [
      '<div class="rdp-install-guide">',
      '<p>当前 Windows 没有注册 Focus RDP 启动器，浏览器无法直接启动远程桌面。</p>',
      '<p>请先在本机下载并运行一次安装脚本，安装后再次点击 RDP 控制台即可直接打开 mstsc。</p>',
      `<p><a href="${rdpInstallerUrl}" download>下载 Focus RDP 启动器安装脚本</a></p>`,
      '</div>',
    ].join(''),
    '需要安装 RDP 启动器',
    {
      confirmButtonText: '知道了',
      dangerouslyUseHTMLString: true,
      type: 'warning',
    },
  );
}

function openRdp(row: EnvironmentItem) {
  const launcherUrl = row.rdp_launcher_url;
  if (!launcherUrl) {
    ElMessage.warning('该环境未返回 Focus RDP 启动地址，请刷新页面后重试');
    return;
  }

  try {
    // 自定义协议是否真的拉起 mstsc 由浏览器和 Windows 决定；这里只捕获协议未注册等浏览器同步异常。
    window.location.href = launcherUrl;
  } catch {
    showRdpInstallGuide();
  }
}

async function openQueue(row: EnvironmentItem) {
  queueDialogTitle.value = `${row.ip_address} 排队情况`;
  queueRows.value = await listEnvironmentQueueApi(row.id);
  queueDialogVisible.value = true;
}

async function openRecords(row: EnvironmentItem) {
  recordEnvironmentId.value = row.id;
  recordDialogTitle.value = `${row.ip_address} 占用记录`;
  recordPage.value = 1;
  recordDialogVisible.value = true;
  await loadRecords();
}

async function loadRecords() {
  if (!recordEnvironmentId.value) return;
  recordLoading.value = true;
  try {
    // 记录数据可能持续增长，弹窗内翻页始终走后端分页，避免一次性拉取大量历史操作。
    const result = await listEnvironmentRecordsApi(recordEnvironmentId.value, {
      page: recordPage.value,
      pageSize: recordPageSize.value,
    });
    recordRows.value = result.items || [];
    recordTotal.value = result.total || 0;
  } finally {
    recordLoading.value = false;
  }
}

function handleRecordSizeChange() {
  recordPage.value = 1;
  loadRecords();
}

onMounted(async () => {
  filterOptions.value = await getEnvironmentFilterOptionsApi();
  await loadData();
  timer = window.setInterval(() => {
    tick.value = Date.now();
  }, 1000);
});

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer);
});
</script>

<template>
  <Page auto-content-height content-class="flex h-full min-h-0 flex-col">
    <div class="environment-user-page">
      <section class="environment-command-bar">
        <div class="command-main">
          <div class="command-title-block">
            <div class="command-title">环境使用</div>
            <div class="command-subtitle">
              共 {{ total }} 个环境，当前页 {{ rows.length }} 个
            </div>
          </div>
          <div class="command-metrics">
            <span class="metric-pill is-idle">空闲 {{ idleCount }}</span>
            <span class="metric-pill is-occupied">占用 {{ occupiedCount }}</span>
            <span class="metric-pill">收藏 {{ favoriteCount }}</span>
            <span v-if="activeFilterCount > 0" class="metric-pill is-filter">
              筛选 {{ activeFilterCount }}
            </span>
          </div>
        </div>
        <div class="toolbar-actions">
          <ElButton v-if="activeFilterCount > 0" @click="clearAllHeaderFilters">
            清空筛选
          </ElButton>
          <ElButton v-if="viewMode === 'card'" @click="filterDialogVisible = true">
            筛选
            <span v-if="activeFilterCount">({{ activeFilterCount }})</span>
          </ElButton>
          <ElSegmented v-model="viewMode" :options="viewOptions" @change="resetPageAndLoad" />
          <ElButton @click="loadData">
            <RefreshCw class="mr-1 size-4" />
            刷新
          </ElButton>
        </div>
      </section>

      <Grid v-if="viewMode === 'table'">
        <template #environment-filter-header="{ column }">
          <EnvironmentHeaderFilter
            v-if="getHeaderFilterConfig(column)"
            :config="getHeaderFilterConfig(column)!"
            :model-value="headerFilterValues[getHeaderFilterConfig(column)!.columnKey]"
            :options="getHeaderFilterOptions(getHeaderFilterConfig(column))"
            @apply="(value) => applyHeaderFilter(getHeaderFilterConfig(column)!, value)"
            @clear="clearHeaderFilter(getHeaderFilterConfig(column)!)"
          />
        </template>
        <template #cell-favorite="{ row }">
          <ElButton v-if="row.can_use_environment" link class="favorite-btn" @click="toggleFavorite(row)">
            <IconifyIcon :class="['size-5', row.is_favorite ? 'favorite-on' : 'favorite-off']" icon="svg:my-favorite" />
          </ElButton>
        </template>
        <template #cell-account="{ row }">
          <div>{{ row.account || '-' }}</div>
        </template>
        <template #cell-domain="{ row }">
          <ElTag size="small">{{ row.domain_label }}</ElTag>
        </template>
        <template #cell-category="{ row }">
          <ElTag size="small" type="info">{{ row.category_label }}</ElTag>
        </template>
        <template #cell-project_name="{ row }">
          <div>{{ row.project_name || '-' }}</div>
        </template>
        <template #cell-vehicle_model="{ row }">
          <div>{{ row.vehicle_model || '-' }}</div>
        </template>
        <template #cell-device_display="{ row }">
          <div class="tag-wrap">
            <ElTag v-for="device in row.devices" :key="device.id" size="small" type="success">
              {{ device.device_name }}
            </ElTag>
            <span v-if="!row.devices?.length" class="muted">-</span>
          </div>
        </template>
        <template #cell-occupy_state="{ row }">
          <ElTag :type="row.status === 'idle' ? 'success' : 'danger'">
            {{ row.status_label }}
          </ElTag>
          <div class="muted">{{ row.current_user_name || '无人占用' }}</div>
          <div v-if="row.status === 'occupied'" class="muted">
            {{ formatDuration(occupiedSeconds(row)) }}
          </div>
        </template>
        <template #cell-queue_state="{ row }">
          <ElButton link type="primary" @click="openQueue(row)">{{ row.queue_count }} 人</ElButton>
          <div v-if="row.my_queue_position" class="muted">我的位置 {{ row.my_queue_position }}</div>
        </template>
        <template #cell-actions="{ row }">
          <div class="action-group">
            <ElButton v-if="canOccupy(row)" size="small" type="primary" @click="occupy(row)">占用</ElButton>
            <ElButton v-else-if="canRelease(row)" size="small" type="warning" @click="release(row)">释放</ElButton>
            <ElButton v-if="canOpenRdp(row)" size="small" type="success" @click="openRdp(row)">RDP 控制台</ElButton>
            <ElButton v-if="canCancelQueue(row)" size="small" @click="cancelQueue(row)">取消排队</ElButton>
            <ElButton v-else-if="canQueue(row)" size="small" @click="queue(row)">排队</ElButton>
            <ElButton link type="primary" @click="openDetail(row)">详情</ElButton>
            <ElButton link type="primary" @click="openRecords(row)">记录</ElButton>
          </div>
        </template>
      </Grid>

      <div v-else v-loading="cardLoading" class="card-grid">
        <article v-for="row in rows" :key="row.id" class="env-card">
          <header class="card-header">
            <div class="card-header-left">
              <span class="status-dot" :class="row.status === 'idle' ? 'is-idle' : 'is-occupied'"></span>
              <span class="card-title">{{ row.ip_address }}</span>
              <ElTag :type="row.status === 'idle' ? 'success' : 'danger'" size="small" effect="plain" class="status-tag">
                {{ row.status_label }}
              </ElTag>
            </div>
            <div class="card-header-right">
              <ElButton v-if="row.can_use_environment" link class="favorite-btn" @click="toggleFavorite(row)">
                <IconifyIcon :class="['size-5', row.is_favorite ? 'favorite-on' : 'favorite-off']" icon="svg:my-favorite" />
              </ElButton>
            </div>
          </header>

          <div class="card-body">
            <div class="card-meta">
              <span class="meta-item" title="项目">
                <IconifyIcon icon="lucide:folder" class="meta-icon" />
                {{ row.project_name || '未配置项目' }}
              </span>
              <span class="meta-divider"></span>
              <span class="meta-item" title="车型">
                <IconifyIcon icon="lucide:car" class="meta-icon" />
                {{ row.vehicle_model || '未配置车型' }}
              </span>
            </div>

            <div class="card-metrics">
              <div class="metric-block">
                <span class="metric-label">占用人</span>
                <span class="metric-value" :class="{'is-active': row.current_user_name}">
                  {{ row.current_user_name || '无人占用' }}
                </span>
              </div>
              <div class="metric-divider"></div>
              <div class="metric-block">
                <span class="metric-label">已占用</span>
                <span class="metric-value">{{ row.status === 'occupied' ? formatDuration(occupiedSeconds(row)) : '-' }}</span>
              </div>
              <div class="metric-divider"></div>
              <div class="metric-block">
                <span class="metric-label">排队人数</span>
                <span class="metric-value">{{ row.queue_count }} 人</span>
              </div>
            </div>

            <div class="card-tags">
              <ElTag size="small" effect="plain" round>{{ row.domain_label }}</ElTag>
              <ElTag size="small" type="info" effect="plain" round>{{ row.category_label }}</ElTag>
              <ElTag v-if="row.bomid" size="small" type="warning" effect="plain" round>BOMID: {{ row.bomid }}</ElTag>
            </div>

            <div class="device-strip" v-if="row.devices.length">
              <ElTag v-for="device in row.devices.slice(0, 3)" :key="device.id" size="small" type="success" effect="light" class="device-tag">
                {{ device.device_name }}
              </ElTag>
              <span v-if="row.devices.length > 3" class="device-more">+{{ row.devices.length - 3 }}</span>
            </div>
            <div class="device-strip empty" v-else>
              <span class="device-more">未绑定测试设备</span>
            </div>
          </div>

          <footer class="card-footer">
            <span class="footer-queue-info">
              <Clock class="mr-1 size-4" />
              {{ row.first_queue_user_name ? `队首：${row.first_queue_user_name}` : '暂无等待队列' }}
            </span>
            <div class="card-actions">
              <ElButton v-if="canOccupy(row)" size="small" type="primary" @click="occupy(row)">占用</ElButton>
              <ElButton v-else-if="canRelease(row)" size="small" type="warning" @click="release(row)">释放</ElButton>
              <ElButton v-if="canOpenRdp(row)" size="small" type="success" @click="openRdp(row)">RDP 控制台</ElButton>
              <ElButton v-if="canCancelQueue(row)" size="small" @click="cancelQueue(row)">取消排队</ElButton>
              <ElButton v-else-if="canQueue(row)" size="small" @click="queue(row)">排队</ElButton>
              <ElButton size="small" @click="openDetail(row)">详情</ElButton>
              <ElButton size="small" @click="openQueue(row)">队列</ElButton>
              <ElButton size="small" @click="openRecords(row)">记录</ElButton>
            </div>
          </footer>
        </article>
        <ElEmpty v-if="rows.length === 0" description="暂无环境" />
      </div>

      <div v-if="viewMode === 'card'" class="pager">
        <ElPagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[12, 20, 40, 80]"
          :total="total"
          background
          layout="total, sizes, prev, pager, next"
          @current-change="loadCards"
          @size-change="resetPageAndLoad"
        />
      </div>
    </div>

    <ElDialog v-model="queueDialogVisible" :title="queueDialogTitle" width="560px">
      <ElTable :data="queueRows" border>
        <ElTableColumn
          v-for="column in queueTableColumns"
          :key="column.key"
          :label="column.label"
          :min-width="column.minWidth"
          :prop="column.prop"
          :width="column.width"
        />
      </ElTable>
    </ElDialog>

    <ElDialog v-model="recordDialogVisible" :title="recordDialogTitle" width="760px">
      <ElTable v-loading="recordLoading" :data="recordRows" border>
        <ElTableColumn
          v-for="column in recordTableColumns"
          :key="column.key"
          :label="column.label"
          :min-width="column.minWidth"
          :prop="column.prop"
          :width="column.width"
        >
          <template v-if="column.key === 'duration'" #default="{ row }">
            {{ row.duration_seconds ? formatDuration(row.duration_seconds) : '-' }}
          </template>
        </ElTableColumn>
      </ElTable>
      <div class="record-pager">
        <ElPagination
          v-model:current-page="recordPage"
          v-model:page-size="recordPageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="recordTotal"
          background
          layout="total, sizes, prev, pager, next"
          @current-change="loadRecords"
          @size-change="handleRecordSizeChange"
        />
      </div>
    </ElDialog>

    <ElDialog v-model="filterDialogVisible" title="环境筛选" width="420px">
      <div class="card-filter-panel">
        <EnvironmentHeaderFilter
          v-for="config in environmentUsageHeaderFilters"
          :key="config.columnKey"
          :config="config"
          :model-value="headerFilterValues[config.columnKey]"
          :options="getHeaderFilterOptions(config)"
          @apply="(value) => applyHeaderFilter(config, value)"
          @clear="clearHeaderFilter(config)"
        />
      </div>
      <template #footer>
        <ElButton @click="clearAllHeaderFilters">清空全部</ElButton>
        <ElButton type="primary" @click="filterDialogVisible = false">完成</ElButton>
      </template>
    </ElDialog>

    <EnvironmentDetailDrawer
      v-model="detailDrawerVisible"
      :environment="detailEnvironment"
    />
  </Page>
</template>

<style scoped>
.environment-user-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

.environment-command-bar {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  background:
    linear-gradient(180deg, var(--el-fill-color-extra-light), var(--el-bg-color));
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  flex-shrink: 0;
}

.command-main {
  display: flex;
  min-width: 0;
  flex: 1;
  align-items: center;
  gap: 18px;
}

.command-title-block {
  min-width: 180px;
}

.command-title {
  color: var(--el-text-color-primary);
  font-size: 16px;
  font-weight: 650;
  line-height: 1.4;
}

.command-subtitle {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.command-metrics {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  gap: 8px;
}

.metric-pill {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 10px;
  color: var(--el-text-color-regular);
  font-size: 12px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 999px;
  white-space: nowrap;
}

.metric-pill.is-idle {
  color: var(--el-color-success);
  background: var(--el-color-success-light-9);
  border-color: var(--el-color-success-light-7);
}

.metric-pill.is-occupied {
  color: var(--el-color-danger);
  background: var(--el-color-danger-light-9);
  border-color: var(--el-color-danger-light-7);
}

.metric-pill.is-filter {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-7);
}

.toolbar-actions {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
  align-items: center;
}

.environment-grid {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.environment-grid :deep(.bg-card.flex.h-full) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.tag-wrap,
.action-group,
.card-actions,
.card-tags,
.device-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.favorite-btn {
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  padding: 4px;
}

.favorite-btn:active {
  transform: scale(0.7);
}

.favorite-btn .size-5 {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.favorite-on {
  fill: #eab308;
  color: #eab308;
  filter: drop-shadow(0 0 6px rgba(234, 179, 8, 0.6));
  animation: favorite-pop 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.favorite-off {
  color: var(--el-text-color-placeholder);
}

.favorite-btn:hover .favorite-off {
  color: var(--el-text-color-secondary);
  transform: scale(1.1);
}

@keyframes favorite-pop {
  0% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  50% {
    transform: scale(1.3);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 16px;
}

.env-card {
  position: relative;
  display: flex;
  flex-direction: column;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-extra-light);
  border-radius: 12px;
  box-shadow: 0 4px 24px -4px rgba(0, 0, 0, 0.03);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.env-card:hover {
  box-shadow: 0 12px 32px -8px rgba(0, 0, 0, 0.08);
  transform: translateY(-4px);
  border-color: var(--el-border-color-light);
}

.card-header {
  padding: 20px 24px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.card-header-right {
  display: flex;
  align-items: center;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.is-idle {
  background-color: var(--el-color-success);
  box-shadow: 0 0 0 3px var(--el-color-success-light-8);
}

.status-dot.is-occupied {
  background-color: var(--el-color-danger);
  box-shadow: 0 0 0 3px var(--el-color-danger-light-8);
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.2;
}

.status-tag {
  border-radius: 4px;
}

.card-body {
  padding: 0 24px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-meta {
  display: flex;
  align-items: center;
  color: var(--el-text-color-regular);
  font-size: 13px;
  gap: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.meta-icon {
  color: var(--el-text-color-secondary);
  font-size: 15px;
}

.meta-divider {
  width: 1px;
  height: 12px;
  background-color: var(--el-border-color-lighter);
}

.card-metrics {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  border-top: 1px solid var(--el-border-color-extra-light);
  border-bottom: 1px solid var(--el-border-color-extra-light);
}

.metric-block {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.metric-divider {
  width: 1px;
  height: 32px;
  background-color: var(--el-border-color-extra-light);
  margin: 0 16px;
}

.metric-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.metric-value {
  color: var(--el-text-color-primary);
  font-size: 15px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.metric-value.is-active {
  color: var(--el-color-primary);
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.device-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  align-items: center;
}

.device-tag {
  border: none;
  background-color: var(--el-color-success-light-9);
}

.device-more {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  background-color: var(--el-fill-color-light);
  padding: 2px 8px;
  border-radius: 10px;
}

.card-footer {
  margin-top: auto;
  padding: 16px 24px;
  background: var(--el-fill-color-blank);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.footer-queue-info {
  display: flex;
  align-items: center;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding: 8px 0;
}

.record-pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}

.card-filter-panel {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.card-filter-panel :deep(.environment-header-filter) {
  justify-content: space-between;
  padding: 8px 10px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-blank);
}

:global(.environment-announcement-dialog .environment-announcement-content) {
  max-height: 360px;
  overflow: auto;
  line-height: 1.7;
}

:global(.environment-announcement-dialog .environment-announcement-content p) {
  margin: 0 0 8px;
}

@media (max-width: 900px) {
  .environment-command-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .command-main {
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
  }

  .toolbar-actions {
    width: 100%;
  }

  .card-grid {
    grid-template-columns: 1fr;
  }

  .card-dashboard {
    grid-template-columns: 1fr;
  }
}
</style>
