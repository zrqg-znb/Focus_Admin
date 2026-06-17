<script lang="ts" setup>
import type {
  EnvironmentItem,
  EnvironmentRecord,
  QueueItem,
} from '#/api/environment-management';

import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { Clock, IconifyIcon, RefreshCw } from '@vben/icons';

import {
  ElButton,
  ElDialog,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPagination,
  ElSegmented,
  ElSelect,
  ElTag,
  ElTable,
  ElTableColumn,
} from 'element-plus';

import {
  cancelMyQueueApi,
  favoriteEnvironmentApi,
  getEnvironmentAnnouncementApi,
  jumpQueueEnvironmentApi,
  listEnvironmentQueueApi,
  listEnvironmentRecordsApi,
  listEnvironmentsApi,
  occupyEnvironmentApi,
  queueEnvironmentApi,
  releaseEnvironmentApi,
  unfavoriteEnvironmentApi,
} from '#/api/environment-management';
import { useZqTable } from '#/components/zq-table';

const domainOptions = [
  { label: '全部领域', value: '' },
  { label: '座舱', value: 'cockpit' },
  { label: '车控', value: 'vehicle' },
];
const categoryOptions = [
  { label: '全部分类', value: '' },
  { label: '开发', value: 'dev' },
  { label: '测试', value: 'test' },
  { label: 'CI', value: 'ci' },
];

const cardLoading = ref(false);
const rows = ref<EnvironmentItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(12);
const viewMode = ref<'card' | 'table'>('table');
const scopeMode = ref<'all' | 'favorite'>('all');
const tick = ref(Date.now());
let timer: null | number = null;

const filters = ref({
  category: '',
  domain: '',
  keyword: '',
  project_name: '',
  vehicle_model: '',
});

const queueDialogVisible = ref(false);
const queueDialogTitle = ref('');
const queueRows = ref<QueueItem[]>([]);
const recordDialogVisible = ref(false);
const recordDialogTitle = ref('');
const recordRows = ref<EnvironmentRecord[]>([]);

const viewOptions = [
  { label: '列表', value: 'table' },
  { label: '平铺', value: 'card' },
];
const scopeOptions = [
  { label: '全部', value: 'all' },
  { label: '收藏', value: 'favorite' },
];

const favoriteCount = computed(
  () => rows.value.filter((item) => item.is_favorite).length,
);

const [Grid, gridApi] = useZqTable<EnvironmentItem>({
  tableTitle: '环境使用',
  class: 'environment-grid',
  gridOptions: {
    columns: [
      { key: 'favorite', dataKey: 'favorite', title: '收藏', width: 64, align: 'center', headerAlign: 'center', showOverflowTooltip: false },
      { key: 'ip_address', dataKey: 'ip_address', title: 'IP地址', width: 140, align: 'center', headerAlign: 'center' },
      { key: 'secret', dataKey: 'secret', title: '账号密码', width: 160, align: 'center', headerAlign: 'center', showOverflowTooltip: false },
      { key: 'domain_category', dataKey: 'domain_category', title: '领域/分类', width: 128, align: 'center', headerAlign: 'center', showOverflowTooltip: false },
      { key: 'project_vehicle', dataKey: 'project_vehicle', title: '项目/车型', minWidth: 160, align: 'center', headerAlign: 'center', showOverflowTooltip: false },
      { key: 'device_display', dataKey: 'device_display', title: '测试设备', minWidth: 240, align: 'center', headerAlign: 'center', showOverflowTooltip: false },
      { key: 'config_description', dataKey: 'config_description', title: '配置情况', minWidth: 220, align: 'center', headerAlign: 'center' },
      { key: 'occupy_state', dataKey: 'occupy_state', title: '占用情况', width: 150, align: 'center', headerAlign: 'center', showOverflowTooltip: false },
      { key: 'queue_state', dataKey: 'queue_state', title: '排队', width: 130, align: 'center', headerAlign: 'center', showOverflowTooltip: false },
      { key: 'shelf_location', dataKey: 'shelf_location', title: '货架位置', width: 130, align: 'center', headerAlign: 'center' },
      { key: 'actions', dataKey: 'actions', title: '操作', width: 270, align: 'center', headerAlign: 'center', fixed: true, showOverflowTooltip: false },
    ],
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page: tablePage }: any) => {
          const result = await listEnvironmentsApi({
            ...filters.value,
            favorite_only: scopeMode.value === 'favorite',
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

async function loadCards() {
  cardLoading.value = true;
  try {
    const result = await listEnvironmentsApi({
      ...filters.value,
      favorite_only: scopeMode.value === 'favorite',
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
  loadData();
}

async function requireOperationAnnouncement() {
  const announcement = await getEnvironmentAnnouncementApi();
  if (!announcement.enabled) return true;
  await ElMessageBox.confirm(
    `<div class="environment-announcement-content">${announcement.content_html || '请确认已了解本次操作说明。'}</div>`,
    announcement.title || '环境操作确认',
    {
      confirmButtonText: '我已了解，继续',
      cancelButtonText: '取消',
      dangerouslyUseHTMLString: true,
      customClass: 'environment-announcement-dialog',
      type: 'warning',
    },
  );
  return true;
}

async function toggleFavorite(row: EnvironmentItem) {
  const updated = row.is_favorite
    ? await unfavoriteEnvironmentApi(row.id)
    : await favoriteEnvironmentApi(row.id);
  Object.assign(row, updated);
  rows.value.sort((a, b) => Number(b.is_favorite) - Number(a.is_favorite));
}

async function occupy(row: EnvironmentItem) {
  // 占用会打开 RDP，先弹管理员公告，用户取消时不触发后端占用接口。
  await requireOperationAnnouncement();
  const result = await occupyEnvironmentApi(row.id);
  ElMessage.success(result.message);
  Object.assign(row, result.environment);
  window.location.href = result.environment.rdp_url;
}

async function release(row: EnvironmentItem) {
  const result = await releaseEnvironmentApi(row.id);
  ElMessage.success(result.message);
  Object.assign(row, result.environment);
}

async function queue(row: EnvironmentItem) {
  await requireOperationAnnouncement();
  Object.assign(row, await queueEnvironmentApi(row.id));
  ElMessage.success('排队成功');
}

async function jumpQueue(row: EnvironmentItem) {
  await requireOperationAnnouncement();
  Object.assign(row, await jumpQueueEnvironmentApi(row.id));
  ElMessage.success('插队成功');
}

async function cancelQueue(row: EnvironmentItem) {
  Object.assign(row, await cancelMyQueueApi(row.id));
  ElMessage.success('已取消排队');
}

function openRdp(row: EnvironmentItem) {
  window.location.href = row.rdp_url;
}

async function openQueue(row: EnvironmentItem) {
  queueDialogTitle.value = `${row.ip_address} 排队情况`;
  queueRows.value = await listEnvironmentQueueApi(row.id);
  queueDialogVisible.value = true;
}

async function openRecords(row: EnvironmentItem) {
  recordDialogTitle.value = `${row.ip_address} 占用记录`;
  const result = await listEnvironmentRecordsApi(row.id, {
    page: 1,
    pageSize: 30,
  });
  recordRows.value = result.items || [];
  recordDialogVisible.value = true;
}

onMounted(() => {
  loadData();
  timer = window.setInterval(() => {
    tick.value = Date.now();
  }, 1000);
});

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer);
});
</script>

<template>
  <Page auto-content-height>
    <div class="environment-user-page">
      <section class="environment-command-bar">
        <ElForm :inline="true" :model="filters" class="toolbar-form">
          <ElFormItem label="关键词">
            <ElInput
              v-model="filters.keyword"
              clearable
              placeholder="IP / 项目 / 设备 / 货架"
              @keyup.enter="resetPageAndLoad"
            />
          </ElFormItem>
          <ElFormItem label="领域">
            <ElSelect v-model="filters.domain" class="filter-select" @change="resetPageAndLoad">
              <ElOption v-for="item in domainOptions" :key="item.value" :label="item.label" :value="item.value" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="分类">
            <ElSelect v-model="filters.category" class="filter-select" @change="resetPageAndLoad">
              <ElOption v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="项目">
            <ElInput v-model="filters.project_name" clearable @keyup.enter="resetPageAndLoad" />
          </ElFormItem>
          <ElFormItem label="车型">
            <ElInput v-model="filters.vehicle_model" clearable @keyup.enter="resetPageAndLoad" />
          </ElFormItem>
          <ElFormItem>
            <ElButton type="primary" @click="resetPageAndLoad">查询</ElButton>
            <ElButton @click="loadData">
              <RefreshCw class="mr-1 size-4" />
              刷新
            </ElButton>
          </ElFormItem>
        </ElForm>
        <div class="toolbar-actions">
          <ElSegmented v-model="scopeMode" :options="scopeOptions" @change="resetPageAndLoad" />
          <ElSegmented v-model="viewMode" :options="viewOptions" @change="resetPageAndLoad" />
        </div>
      </section>

      <div class="summary-line">
        <span>共 {{ total }} 个环境</span>
        <span>当前页收藏 {{ favoriteCount }} 个</span>
        <span>密码策略：仅环境用户和环境管理员可见明文</span>
      </div>

      <Grid v-if="viewMode === 'table'">
        <template #cell-favorite="{ row }">
          <ElButton v-if="row.can_use_environment" link type="warning" @click="toggleFavorite(row)">
            <IconifyIcon :class="['size-4', row.is_favorite ? 'favorite-on' : '']" icon="lucide:star" />
          </ElButton>
        </template>
        <template #cell-secret="{ row }">
          <div>{{ row.account || '-' }}</div>
          <div class="muted">{{ row.password || '-' }}</div>
        </template>
        <template #cell-domain_category="{ row }">
          <ElTag size="small">{{ row.domain_label }}</ElTag>
          <ElTag class="ml-1" size="small" type="info">{{ row.category_label }}</ElTag>
        </template>
        <template #cell-project_vehicle="{ row }">
          <div>{{ row.project_name || '-' }}</div>
          <div class="muted">{{ row.vehicle_model || '-' }}</div>
        </template>
        <template #cell-device_display="{ row }">
          <div class="tag-wrap">
            <ElTag v-for="device in row.devices" :key="device.id" size="small" type="success">
              {{ device.display_name }}
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
            <ElButton v-if="row.can_use_environment && row.status === 'idle'" size="small" type="primary" @click="occupy(row)">占用</ElButton>
            <ElButton v-else-if="row.can_use_environment" size="small" type="warning" @click="release(row)">释放</ElButton>
            <ElButton v-if="row.can_use_environment" size="small" @click="openRdp(row)">RDP</ElButton>
            <ElButton v-if="row.can_use_environment && row.my_queue_id" size="small" @click="cancelQueue(row)">取消排队</ElButton>
            <template v-else-if="row.can_use_environment">
              <ElButton size="small" @click="queue(row)">排队</ElButton>
              <ElButton size="small" type="danger" @click="jumpQueue(row)">插队</ElButton>
            </template>
            <ElButton link type="primary" @click="openRecords(row)">记录</ElButton>
          </div>
        </template>
      </Grid>

      <div v-else v-loading="cardLoading" class="card-grid">
        <article v-for="row in rows" :key="row.id" class="env-card" :class="{ 'is-idle': row.status === 'idle' }">
          <header>
            <div>
              <div class="card-title">
                <span>{{ row.ip_address }}</span>
                <ElTag :type="row.status === 'idle' ? 'success' : 'danger'" size="small">{{ row.status_label }}</ElTag>
              </div>
              <div class="card-subtitle">{{ row.project_name || '未配置项目' }} / {{ row.vehicle_model || '未配置车型' }}</div>
            </div>
            <ElButton v-if="row.can_use_environment" link type="warning" @click="toggleFavorite(row)">
              <IconifyIcon :class="['size-5', row.is_favorite ? 'favorite-on' : '']" icon="lucide:star" />
            </ElButton>
          </header>

          <div class="card-dashboard">
            <div>
              <span class="metric-label">占用人</span>
              <strong>{{ row.current_user_name || '无人占用' }}</strong>
            </div>
            <div>
              <span class="metric-label">已占用</span>
              <strong>{{ row.status === 'occupied' ? formatDuration(occupiedSeconds(row)) : '-' }}</strong>
            </div>
            <div>
              <span class="metric-label">排队</span>
              <strong>{{ row.queue_count }} 人</strong>
            </div>
          </div>

          <div class="card-tags">
            <ElTag size="small">{{ row.domain_label }}</ElTag>
            <ElTag size="small" type="info">{{ row.category_label }}</ElTag>
            <ElTag v-if="row.shelf_location" size="small" type="warning">{{ row.shelf_location }}</ElTag>
          </div>

          <div class="device-strip">
            <ElTag v-for="device in row.devices.slice(0, 3)" :key="device.id" size="small" type="success">
              {{ device.display_name }}
            </ElTag>
            <span v-if="row.devices.length > 3" class="muted">+{{ row.devices.length - 3 }} 个设备</span>
            <span v-if="!row.devices.length" class="muted">未绑定测试设备</span>
          </div>

          <footer>
            <span>
              <Clock class="mr-1 size-4" />
              {{ row.first_queue_user_name ? `队首：${row.first_queue_user_name}` : '暂无等待队列' }}
            </span>
            <div class="card-actions">
              <ElButton v-if="row.can_use_environment && row.status === 'idle'" size="small" type="primary" @click="occupy(row)">占用</ElButton>
              <ElButton v-else-if="row.can_use_environment" size="small" type="warning" @click="release(row)">释放</ElButton>
              <ElButton v-if="row.can_use_environment && row.my_queue_id" size="small" @click="cancelQueue(row)">取消排队</ElButton>
              <template v-else-if="row.can_use_environment">
                <ElButton size="small" @click="queue(row)">排队</ElButton>
                <ElButton size="small" type="danger" @click="jumpQueue(row)">插队</ElButton>
              </template>
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
        <ElTableColumn label="位置" prop="position" width="80" />
        <ElTableColumn label="用户" prop="user_name" />
        <ElTableColumn label="类型" prop="queue_type_label" width="100" />
        <ElTableColumn label="申请时间" prop="requested_at" width="180" />
      </ElTable>
    </ElDialog>

    <ElDialog v-model="recordDialogVisible" :title="recordDialogTitle" width="760px">
      <ElTable :data="recordRows" border>
        <ElTableColumn label="时间" prop="sys_create_datetime" width="180" />
        <ElTableColumn label="操作人" prop="operator_name" width="120" />
        <ElTableColumn label="动作" prop="action_label" width="100" />
        <ElTableColumn label="说明" prop="message" min-width="220" />
        <ElTableColumn label="时长" width="100">
          <template #default="{ row }">
            {{ row.duration_seconds ? formatDuration(row.duration_seconds) : '-' }}
          </template>
        </ElTableColumn>
      </ElTable>
    </ElDialog>
  </Page>
</template>

<style scoped>
.environment-user-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: calc(100vh - 120px);
}

.environment-command-bar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  background: linear-gradient(180deg, var(--el-bg-color), var(--el-fill-color-extra-light));
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
}

.toolbar-form {
  flex: 1;
}

.toolbar-actions {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
}

.filter-select {
  width: 120px;
}

.summary-line {
  display: flex;
  gap: 18px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.environment-grid {
  flex: 1;
  min-height: calc(100vh - 250px);
}

.environment-grid :deep(.bg-card.flex.h-full) {
  min-height: calc(100vh - 250px);
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

.favorite-on {
  fill: currentColor;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 14px;
}

.env-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 260px;
  padding: 16px;
  overflow: hidden;
  background: linear-gradient(145deg, var(--el-bg-color), var(--el-fill-color-extra-light));
  border: 1px solid var(--el-border-color-light);
  border-left: 4px solid var(--el-color-danger);
  border-radius: 6px;
  box-shadow: 0 12px 30px rgb(15 23 42 / 6%);
}

.env-card.is-idle {
  border-left-color: var(--el-color-success);
}

.env-card header,
.env-card footer {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.env-card footer {
  align-items: center;
  margin-top: auto;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0;
}

.card-subtitle {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.card-dashboard {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.card-dashboard > div {
  min-height: 64px;
  padding: 10px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}

.metric-label {
  display: block;
  margin-bottom: 6px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.card-dashboard strong {
  color: var(--el-text-color-primary);
  font-size: 15px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding: 8px 0;
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
