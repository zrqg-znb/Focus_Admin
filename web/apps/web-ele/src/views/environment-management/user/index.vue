<script lang="ts" setup>
import type {
  EnvironmentItem,
  EnvironmentRecord,
  QueueItem,
} from '#/api/environment-management';

import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import {
  Clock,
  IconifyIcon,
  RefreshCw,
} from '@vben/icons';

import {
  ElButton,
  ElDialog,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElPagination,
  ElSegmented,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import {
  cancelMyQueueApi,
  favoriteEnvironmentApi,
  jumpQueueEnvironmentApi,
  listEnvironmentQueueApi,
  listEnvironmentRecordsApi,
  listEnvironmentsApi,
  occupyEnvironmentApi,
  queueEnvironmentApi,
  releaseEnvironmentApi,
  unfavoriteEnvironmentApi,
} from '#/api/environment-management';

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

const loading = ref(false);
const rows = ref<EnvironmentItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const viewMode = ref<'card' | 'table'>('table');
const scopeMode = ref<'all' | 'favorite'>('all');
const tick = ref(Date.now());
let timer: any = null;

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
  // 占用时长以后端 occupied_at 为准，本地 tick 只负责让 UI 每秒刷新。
  if (row.status !== 'occupied' || !row.occupied_at) return 0;
  return Math.max(
    Math.floor((tick.value - new Date(row.occupied_at).getTime()) / 1000),
    row.occupied_seconds || 0,
  );
}

async function loadData() {
  loading.value = true;
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
    loading.value = false;
  }
}

function resetPageAndLoad() {
  page.value = 1;
  loadData();
}

async function toggleFavorite(row: EnvironmentItem) {
  const updated = row.is_favorite
    ? await unfavoriteEnvironmentApi(row.id)
    : await favoriteEnvironmentApi(row.id);
  Object.assign(row, updated);
  rows.value.sort((a, b) => Number(b.is_favorite) - Number(a.is_favorite));
}

async function occupy(row: EnvironmentItem) {
  const result = await occupyEnvironmentApi(row.id);
  ElMessage.success(result.message);
  Object.assign(row, result.environment);
  // Web 页面不能携带账号密码启动 mstsc；这里只跳转自定义协议，Windows 端负责协议处理。
  window.location.href = result.environment.rdp_url;
}

async function release(row: EnvironmentItem) {
  const result = await releaseEnvironmentApi(row.id);
  ElMessage.success(result.message);
  Object.assign(row, result.environment);
}

async function queue(row: EnvironmentItem) {
  Object.assign(row, await queueEnvironmentApi(row.id));
  ElMessage.success('排队成功');
}

async function jumpQueue(row: EnvironmentItem) {
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

function configEntries(row: EnvironmentItem) {
  // 配置情况是 JSON 对象，用户端统一按 Tag 展示非空键值。
  return Object.entries(row.config || {}).filter(([, value]) => value !== '');
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
      <div class="toolbar">
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
              <ElOption
                v-for="item in domainOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="分类">
            <ElSelect v-model="filters.category" class="filter-select" @change="resetPageAndLoad">
              <ElOption
                v-for="item in categoryOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
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
          <ElSegmented v-model="viewMode" :options="viewOptions" />
        </div>
      </div>

      <div class="summary-line">
        <span>共 {{ total }} 个环境</span>
        <span>当前页收藏 {{ favoriteCount }} 个</span>
        <span>密码策略：仅环境用户和环境管理员可见明文</span>
      </div>

      <ElTable
        v-if="viewMode === 'table'"
        v-loading="loading"
        :data="rows"
        border
        stripe
        class="environment-table"
      >
        <ElTableColumn width="56">
          <template #default="{ row }">
            <ElButton
              v-if="row.can_use_environment"
              link
              type="warning"
              @click="toggleFavorite(row)"
            >
              <IconifyIcon :class="['size-4', row.is_favorite ? 'favorite-on' : '']" icon="lucide:star" />
            </ElButton>
          </template>
        </ElTableColumn>
        <ElTableColumn label="IP地址" min-width="132" prop="ip_address" />
        <ElTableColumn label="账号密码" min-width="150">
          <template #default="{ row }">
            <div>{{ row.account || '-' }}</div>
            <div class="muted">{{ row.password || '-' }}</div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="领域/分类" min-width="120">
          <template #default="{ row }">
            <ElTag size="small">{{ row.domain_label }}</ElTag>
            <ElTag class="ml-1" size="small" type="info">{{ row.category_label }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="项目/车型" min-width="150">
          <template #default="{ row }">
            <div>{{ row.project_name || '-' }}</div>
            <div class="muted">{{ row.vehicle_model || '-' }}</div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="测试设备" min-width="170" prop="device_display" />
        <ElTableColumn label="配置情况" min-width="220">
          <template #default="{ row }">
            <div class="tag-wrap">
              <ElTag
                v-for="[key, value] in configEntries(row)"
                :key="key"
                size="small"
                type="success"
              >
                {{ key }}: {{ value }}
              </ElTag>
              <span v-if="configEntries(row).length === 0" class="muted">-</span>
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="占用情况" min-width="140">
          <template #default="{ row }">
            <ElTag :type="row.status === 'idle' ? 'success' : 'danger'">
              {{ row.status_label }}
            </ElTag>
            <div class="muted">
              {{ row.current_user_name || '无人占用' }}
            </div>
            <div v-if="row.status === 'occupied'" class="muted">
              {{ formatDuration(occupiedSeconds(row)) }}
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="排队" min-width="130">
          <template #default="{ row }">
            <ElButton link type="primary" @click="openQueue(row)">
              {{ row.queue_count }} 人
            </ElButton>
            <div v-if="row.my_queue_position" class="muted">
              我的位置 {{ row.my_queue_position }}
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="货架位置" min-width="130" prop="shelf_location" />
        <ElTableColumn fixed="right" label="操作" min-width="250">
          <template #default="{ row }">
            <div class="action-group">
              <ElButton
                v-if="row.can_use_environment && row.status === 'idle'"
                size="small"
                type="primary"
                @click="occupy(row)"
              >
                占用
              </ElButton>
              <ElButton
                v-else-if="row.can_use_environment"
                size="small"
                type="warning"
                @click="release(row)"
              >
                释放
              </ElButton>
              <ElButton v-if="row.can_use_environment" size="small" @click="openRdp(row)">
                <IconifyIcon class="mr-1 size-4" icon="lucide:monitor-up" />
                RDP
              </ElButton>
              <ElButton
                v-if="row.can_use_environment && row.my_queue_id"
                size="small"
                @click="cancelQueue(row)"
              >
                取消排队
              </ElButton>
              <template v-else-if="row.can_use_environment">
                <ElButton size="small" @click="queue(row)">排队</ElButton>
                <ElButton size="small" type="danger" @click="jumpQueue(row)">
                  插队
                </ElButton>
              </template>
              <ElButton link type="primary" @click="openRecords(row)">
                记录
              </ElButton>
            </div>
          </template>
        </ElTableColumn>
      </ElTable>

      <div v-else v-loading="loading" class="card-grid">
        <article v-for="row in rows" :key="row.id" class="env-card">
          <header>
            <div>
              <div class="card-title">
                {{ row.ip_address }}
                <ElTag :type="row.status === 'idle' ? 'success' : 'danger'" size="small">
                  {{ row.status_label }}
                </ElTag>
              </div>
              <div class="muted">{{ row.project_name || '-' }} / {{ row.vehicle_model || '-' }}</div>
            </div>
            <ElButton
              v-if="row.can_use_environment"
              link
              type="warning"
              @click="toggleFavorite(row)"
            >
              <IconifyIcon :class="['size-5', row.is_favorite ? 'favorite-on' : '']" icon="lucide:star" />
            </ElButton>
          </header>
          <div class="card-meta">
            <ElTag size="small">{{ row.domain_label }}</ElTag>
            <ElTag size="small" type="info">{{ row.category_label }}</ElTag>
            <span>{{ row.device_display || '未配置设备' }}</span>
            <span>{{ row.shelf_location || '未配置货架' }}</span>
          </div>
          <div class="card-secret">
            <span>账号 {{ row.account || '-' }}</span>
            <span>密码 {{ row.password || '-' }}</span>
          </div>
          <div class="tag-wrap">
            <ElTag
              v-for="[key, value] in configEntries(row)"
              :key="key"
              size="small"
              type="success"
            >
              {{ key }}: {{ value }}
            </ElTag>
          </div>
          <footer>
            <span>
              <Clock class="mr-1 size-4" />
              {{ row.current_user_name || '无人占用' }}
              <template v-if="row.status === 'occupied'">
                · {{ formatDuration(occupiedSeconds(row)) }}
              </template>
            </span>
            <span>排队 {{ row.queue_count }} 人</span>
          </footer>
          <div class="card-actions">
            <ElButton
              v-if="row.can_use_environment && row.status === 'idle'"
              size="small"
              type="primary"
              @click="occupy(row)"
            >
              占用
            </ElButton>
            <ElButton v-else-if="row.can_use_environment" size="small" type="warning" @click="release(row)">
              释放
            </ElButton>
            <ElButton v-if="row.can_use_environment" size="small" @click="openRdp(row)">RDP</ElButton>
            <ElButton v-if="row.can_use_environment && row.my_queue_id" size="small" @click="cancelQueue(row)">
              取消排队
            </ElButton>
            <template v-else-if="row.can_use_environment">
              <ElButton size="small" @click="queue(row)">排队</ElButton>
              <ElButton size="small" type="danger" @click="jumpQueue(row)">
                插队
              </ElButton>
            </template>
            <ElButton size="small" @click="openQueue(row)">队列</ElButton>
            <ElButton size="small" @click="openRecords(row)">记录</ElButton>
          </div>
        </article>
        <ElEmpty v-if="rows.length === 0" description="暂无环境" />
      </div>

      <div class="pager">
        <ElPagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[12, 20, 40, 80]"
          :total="total"
          background
          layout="total, sizes, prev, pager, next"
          @current-change="loadData"
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
  min-height: 100%;
}

.toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  background: var(--el-bg-color);
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

.environment-table {
  width: 100%;
}

.muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.tag-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.action-group,
.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.favorite-on {
  fill: currentColor;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 12px;
}

.env-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
}

.env-card header,
.env-card footer {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 17px;
  font-weight: 650;
}

.card-meta,
.card-secret {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding: 8px 0;
}

@media (max-width: 900px) {
  .toolbar {
    flex-direction: column;
  }

  .toolbar-actions {
    width: 100%;
  }

  .card-grid {
    grid-template-columns: 1fr;
  }
}
</style>
