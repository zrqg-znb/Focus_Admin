<script setup lang="ts">
import type {
  SubscriptionManagementProjectRow,
  SubscriptionSubscriberRow,
} from '#/api/integration-report';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { computed, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  ElButton,
  ElDialog,
  ElDrawer,
  ElMessage,
  ElMessageBox,
  ElNotification,
  ElPopconfirm,
  ElProgress,
  ElTag,
  ElUpload,
  type UploadRequestOptions,
} from 'element-plus';
import * as XLSX from 'xlsx';

import {
  addSubscriptionManagementSubscribersApi,
  batchAddSubscriptionManagementSubscribersApi,
  listSubscriptionManagementProjectsApi,
  listSubscriptionManagementSubscribersApi,
  removeSubscriptionManagementSubscribersApi,
  replaceSubscriptionManagementSubscribersApi,
} from '#/api/integration-report';
import { useZqTable } from '#/components/zq-table';
import UserSelector from '#/components/zq-form/user-selector/user-selector.vue';

import { searchUserApi } from '#/api/core/user';
import {
  useProjectColumns,
  useSearchFormSchema,
  useSubscriberColumns,
  useSubscriberSearchSchema,
} from './data';

defineOptions({ name: 'IntegrationReportSubscriptionManagement' });

const drawerVisible = ref(false);
const currentConfig = ref<SubscriptionManagementProjectRow>();
const selectedUserIds = ref<string[]>([]);
const batchUserIds = ref<string[]>([]);
const selectedProjectRows = ref<SubscriptionManagementProjectRow[]>([]);
const selectedSubscriberRows = ref<SubscriptionSubscriberRow[]>([]);
const saving = ref(false);
const drawerPreparing = ref(false);

const importDialogVisible = ref(false);
const importing = ref(false);
const importPercent = ref(0);
const importMessage = ref('');

const drawerTitle = computed(() => {
  if (!currentConfig.value) return '邮件订阅管理';
  return `${currentConfig.value.name} · 订阅人`;
});

const subscriberSummary = computed(() => {
  const config = currentConfig.value;
  if (!config) return [];
  return [
    { label: '所属项目', value: config.project_name || '-' },
    { label: '负责人', value: config.managers || config.project_managers || '-' },
    { label: '订阅人数', value: `${config.subscriber_count}` },
    { label: '无邮箱', value: `${config.missing_email_count}` },
  ];
});

const selectedProjectLabel = computed(() => {
  const count = selectedProjectRows.value.length;
  return count > 0 ? `已选 ${count} 个项目配置` : '请选择项目配置';
});

const [ProjectGrid, projectGridApi] = useZqTable<SubscriptionManagementProjectRow>({
  formOptions: {
    schema: useSearchFormSchema(),
    showCollapseButton: false,
  },
  gridOptions: {
    border: true,
    columns: useProjectColumns(),
    rowKey: 'id',
    stripe: true,
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [20, 50, 100],
    },
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page, form }) => {
          const params = {
            page: page.currentPage,
            page_size: page.pageSize,
            ...form,
          };
          const res = await listSubscriptionManagementProjectsApi(params);
          return {
            items: res.items,
            total: res.count ?? res.total ?? 0,
          };
        },
      },
    },
    toolbarConfig: {
      custom: true,
      refresh: true,
      search: true,
      zoom: true,
    },
  } as ZqTableGridOptions<SubscriptionManagementProjectRow>,
});

const [SubscriberGrid, subscriberGridApi] = useZqTable<SubscriptionSubscriberRow>({
  formOptions: {
    schema: useSubscriberSearchSchema(),
    showCollapseButton: false,
  },
  gridOptions: {
    border: true,
    columns: useSubscriberColumns(),
    rowKey: 'id',
    stripe: true,
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [20, 50, 100],
    },
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({ page, form }) => {
          if (!currentConfig.value?.id) {
            return {
              items: subscriberGridApi.tableData.value,
              total: subscriberGridApi.total.value,
            };
          }
          const params = {
            page: page.currentPage,
            page_size: page.pageSize,
            ...form,
          };
          const res = await listSubscriptionManagementSubscribersApi(
            currentConfig.value.id,
            params,
          );
          return {
            items: res.items,
            total: res.count ?? res.total ?? 0,
          };
        },
      },
    },
    toolbarConfig: {
      custom: true,
      refresh: true,
      search: true,
    },
  } as ZqTableGridOptions<SubscriptionSubscriberRow>,
});

async function loadEnabledSubscriberIds(configId: string) {
  const res = await listSubscriptionManagementSubscribersApi(configId, {
    enabled: true,
    page: 1,
    page_size: 5000,
  });
  selectedUserIds.value = (res.items || []).map((item) => item.user_id);
}

async function refreshCurrentData() {
  selectedSubscriberRows.value = [];
  await Promise.all([subscriberGridApi.reload(), projectGridApi.reload()]);
  if (currentConfig.value?.id) {
    await loadEnabledSubscriberIds(currentConfig.value.id);
    const latestConfig = projectGridApi.tableData.value.find(
      (item) => item.id === currentConfig.value?.id,
    );
    if (latestConfig) {
      currentConfig.value = latestConfig;
    }
  }
}

async function openDrawer(row: SubscriptionManagementProjectRow) {
  drawerPreparing.value = true;
  currentConfig.value = row;
  selectedSubscriberRows.value = [];
  try {
    await Promise.all([loadEnabledSubscriberIds(row.id), subscriberGridApi.reload()]);
    drawerVisible.value = true;
  } finally {
    drawerPreparing.value = false;
  }
}

async function confirmAddSelectedUsers(userIds: string | string[]) {
  if (!currentConfig.value) return Promise.reject(new Error('no config'));
  const ids = Array.isArray(userIds) ? userIds : [userIds];

  if (ids.length === 0) {
    ElMessage.warning('请先选择订阅人');
    return Promise.reject(new Error('no user selected'));
  }

  const existingIds = subscriberGridApi.tableData.value.map(row => row.user_id);
  const newIds = ids.filter(id => !existingIds.includes(id));

  if (newIds.length === 0) {
    ElMessage.warning('所选用户均已在订阅列表中');
    return Promise.reject(new Error('all duplicated'));
  }

  saving.value = true;
  try {
    const res = await addSubscriptionManagementSubscribersApi(
      currentConfig.value.id,
      newIds,
    );
    ElMessage.success(`追加完成，成功新增 ${res.changed_count} 人（已自动去重）`);
    await refreshCurrentData();
  } catch (error) {
    throw error;
  } finally {
    saving.value = false;
  }
}

async function confirmBatchAddUsers(userIds: string | string[]) {
  const ids = Array.isArray(userIds) ? userIds : [userIds];
  const configIds = selectedProjectRows.value.map((row) => row.id);

  if (configIds.length === 0) {
    ElMessage.warning('请先勾选项目配置');
    return Promise.reject(new Error('no project selected'));
  }
  if (ids.length === 0) {
    ElMessage.warning('请先选择要批量订阅的用户');
    return Promise.reject(new Error('no user selected'));
  }

  try {
    await ElMessageBox.confirm(
      `确认将选中的 ${ids.length} 个用户批量追加订阅到 ${configIds.length} 个项目中吗？`,
      '批量订阅确认',
      {
        confirmButtonText: '确认订阅',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );
  } catch {
    return Promise.reject(new Error('user cancelled'));
  }

  const notification = ElNotification({
    title: '批量订阅中',
    message: `正在处理 ${ids.length} 个用户的订阅请求，请稍候...`,
    duration: 0,
    type: 'info',
  });

  saving.value = true;
  try {
    const res = await batchAddSubscriptionManagementSubscribersApi(
      configIds,
      ids,
    );
    notification.close();
    ElNotification({
      title: '批量订阅完成',
      message: `成功为 ${configIds.length} 个项目配置变更了 ${res.changed_count} 条订阅关系。`,
      type: 'success',
    });
    projectGridApi.clearSelection();
    selectedProjectRows.value = [];
    batchUserIds.value = [];
    await projectGridApi.reload();
  } catch (error) {
    notification.close();
    throw error;
  } finally {
    saving.value = false;
  }
}

function handleProjectSelectionChange(records: SubscriptionManagementProjectRow[]) {
  selectedProjectRows.value = records || [];
}

function handleSubscriberSelectionChange(records: SubscriptionSubscriberRow[]) {
  selectedSubscriberRows.value = records || [];
}

async function removeCheckedUsers() {
  if (!currentConfig.value) return;
  const userIds = selectedSubscriberRows.value.map((row) => row.user_id);
  if (userIds.length === 0) {
    ElMessage.warning('请先勾选要移除的订阅人');
    return;
  }
  saving.value = true;
  try {
    const res = await removeSubscriptionManagementSubscribersApi(
      currentConfig.value.id,
      userIds,
    );
    selectedUserIds.value = selectedUserIds.value.filter(
      (userId) => !userIds.includes(userId),
    );
    ElMessage.success(`移除完成，变更 ${res.changed_count} 人`);
    await refreshCurrentData();
  } finally {
    saving.value = false;
  }
}

async function removeSingleUser(row: SubscriptionSubscriberRow) {
  if (!currentConfig.value) return;
  saving.value = true;
  try {
    const res = await removeSubscriptionManagementSubscribersApi(
      currentConfig.value.id,
      [row.user_id],
    );
    selectedUserIds.value = selectedUserIds.value.filter(
      (userId) => userId !== row.user_id,
    );
    ElMessage.success(`移除完成，变更 ${res.changed_count} 人`);
    await refreshCurrentData();
  } finally {
    saving.value = false;
  }
}

function downloadTemplate() {
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.aoa_to_sheet([
    ['用户名', '姓名', '邮箱（可选）'],
    ['zhangsan', '张三', 'zhangsan@example.com'],
    ['lisi', '李四', ''],
  ]);
  XLSX.utils.book_append_sheet(wb, ws, '导入模板');
  XLSX.writeFile(wb, '批量导入订阅人模板.xlsx');
}

async function handleImportRequest(options: UploadRequestOptions) {
  if (!currentConfig.value) return;
  importing.value = true;
  importPercent.value = 10;
  importMessage.value = '正在解析文件...';
  
  try {
    const file = options.file;
    const data = await file.arrayBuffer();
    const wb = XLSX.read(data);
    const ws = wb.Sheets[wb.SheetNames[0] as string];
    if (!ws) throw new Error('Excel文件为空');
    
    const rows = XLSX.utils.sheet_to_json<any>(ws, { defval: '' });
    if (rows.length === 0) throw new Error('Excel文件内容为空');
    
    importPercent.value = 30;
    importMessage.value = '正在校验并匹配用户...';
    
    const validUsernames: string[] = [];
    rows.forEach((row, idx) => {
      const username = (row['用户名'] || '').toString().trim();
      const email = (row['邮箱'] || row['邮箱（可选）'] || '').toString().trim();
      if (!username && !email) {
        // ignore empty rows
      } else {
        validUsernames.push(username || email);
      }
    });
    
    if (validUsernames.length === 0) {
      throw new Error('未找到有效的用户名或邮箱');
    }
    
    // remove duplicates from file
    const uniqueUsernames = [...new Set(validUsernames)];
    
    const matchedUserIds: string[] = [];
    const unmatched: string[] = [];
    
    for (let i = 0; i < uniqueUsernames.length; i++) {
      const keyword = uniqueUsernames[i] as string;
      importPercent.value = 30 + Math.floor((i / uniqueUsernames.length) * 40);
      importMessage.value = `匹配用户进度 ${i + 1}/${uniqueUsernames.length}`;
      
      const res = await searchUserApi(keyword);
      // find exact match if possible
      const exactMatch = res.items.find(u => u.username === keyword || u.email === keyword || u.name === keyword);
      if (exactMatch) {
        matchedUserIds.push(exactMatch.id);
      } else if (res.items.length > 0) {
        matchedUserIds.push(res.items[0].id); // fuzzy match
      } else {
        unmatched.push(keyword);
      }
    }
    
    importPercent.value = 80;
    importMessage.value = '正在追加订阅人...';
    
    const existingIds = subscriberGridApi.tableData.value.map(row => row.user_id);
    const newIds = matchedUserIds.filter(id => !existingIds.includes(id));
    
    if (newIds.length === 0) {
      if (unmatched.length > 0) {
        throw new Error(`所选用户均已在订阅列表中，另外有 ${unmatched.length} 个用户未匹配到：${unmatched.slice(0, 3).join(', ')}...`);
      } else {
        throw new Error('所选用户均已在订阅列表中');
      }
    }
    
    const res = await addSubscriptionManagementSubscribersApi(currentConfig.value.id, newIds);
    importPercent.value = 100;
    importMessage.value = '导入成功！';
    
    let successMsg = `追加完成，成功新增 ${res.changed_count} 人。`;
    if (unmatched.length > 0) {
      successMsg += ` 但有 ${unmatched.length} 个用户未找到：${unmatched.slice(0, 3).join(', ')}...`;
      ElMessage.warning(successMsg);
    } else {
      ElMessage.success(successMsg);
    }
    
    importDialogVisible.value = false;
    await refreshCurrentData();
  } catch (error: any) {
    ElMessage.error(error.message || '导入失败');
  } finally {
    importing.value = false;
  }
}

async function saveSubscribers() {
  if (!currentConfig.value) return;
  saving.value = true;
  try {
    const res = await replaceSubscriptionManagementSubscribersApi(
      currentConfig.value.id,
      selectedUserIds.value,
    );
    ElMessage.success(`保存完成，变更 ${res.changed_count} 人`);
    await refreshCurrentData();
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <Page auto-content-height>
    <ProjectGrid class="h-full" @selection-change="handleProjectSelectionChange">
      <template #table-title>
        <div class="subscription-batch-toolbar">
          <span class="subscription-batch-toolbar__label">
            {{ selectedProjectLabel }}
          </span>
          <UserSelector
            v-model="batchUserIds"
            :multiple="true"
            display-mode="button"
            class="subscription-batch-toolbar__selector"
            placeholder="批量订阅选定项目"
            :disabled="selectedProjectRows.length === 0"
            :on-confirm="confirmBatchAddUsers"
          />
        </div>
      </template>

      <template #enabled_default="{ row }">
        <ElTag v-if="row.enabled" type="success" size="small">
          报告启用
        </ElTag>
        <ElTag v-else type="warning" size="small">报告停用</ElTag>
      </template>

      <template #managers_default="{ row }">
        {{ row.managers || row.project_managers || '-' }}
      </template>

      <template #subscriber_count_default="{ row }">
        <span class="subscription-count">{{ row.subscriber_count }}</span>
      </template>

      <template #missing_email_count_default="{ row }">
        <ElTag
          v-if="row.missing_email_count > 0"
          type="danger"
          size="small"
        >
          {{ row.missing_email_count }}
        </ElTag>
        <span v-else class="text-gray-400">0</span>
      </template>

      <template #updated_default="{ row }">
        {{ row.sys_update_datetime || '-' }}
      </template>

      <template #action_default="{ row }">
        <ElButton
          :loading="drawerPreparing && currentConfig?.id === row.id"
          size="small"
          type="primary"
          link
          @click="openDrawer(row)"
        >
          <template #icon>
            <IconifyIcon icon="lucide:users-round" />
          </template>
          管理订阅
        </ElButton>
      </template>
    </ProjectGrid>

    <ElDrawer
      v-model="drawerVisible"
      :title="drawerTitle"
      size="72%"
      append-to-body
      class="subscription-management-drawer"
    >
      <div class="subscription-drawer">
        <div class="subscription-drawer__summary">
          <div
            v-for="item in subscriberSummary"
            :key="item.label"
            class="subscription-drawer__summary-item"
          >
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>

        <div class="subscription-drawer__toolbar">
          <UserSelector
            v-model="selectedUserIds"
            :multiple="true"
            display-mode="button"
            placeholder="从组织架构选人"
            :on-confirm="confirmAddSelectedUsers"
          />
          <ElButton :loading="saving" type="success" plain @click="importDialogVisible = true">
            <template #icon>
              <IconifyIcon icon="lucide:upload" />
            </template>
            批量导入
          </ElButton>
          <ElPopconfirm
            title="确认移除勾选的订阅人？移除后不会再收到该项目邮件。"
            @confirm="removeCheckedUsers"
          >
            <template #reference>
              <ElButton :loading="saving" type="danger" plain>
                <template #icon>
                  <IconifyIcon icon="lucide:user-minus" />
                </template>
                移除选中
              </ElButton>
            </template>
          </ElPopconfirm>
          <ElButton :loading="saving" type="primary" @click="saveSubscribers">
            <template #icon>
              <IconifyIcon icon="lucide:save" />
            </template>
            全量保存
          </ElButton>
        </div>

        <div class="subscription-drawer__table">
          <SubscriberGrid
            class="h-full"
            @selection-change="handleSubscriberSelectionChange"
          >
            <template #subscriber_name_default="{ row }">
              {{ row.name || row.username }}
            </template>

            <template #subscriber_email_default="{ row }">
              {{ row.email || '-' }}
            </template>

            <template #subscriber_enabled_default="{ row }">
              <ElTag v-if="row.enabled" type="success" size="small">
                已订阅
              </ElTag>
              <ElTag v-else type="info" size="small">停用</ElTag>
            </template>

            <template #subscriber_updated_default="{ row }">
              {{ row.sys_update_datetime || '-' }}
            </template>
          </SubscriberGrid>
        </div>
      </div>
    </ElDrawer>

    <ElDialog
      v-model="importDialogVisible"
      title="批量导入订阅人"
      width="500px"
      append-to-body
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="!importing"
    >
      <div class="mb-4 text-right">
        <ElButton type="primary" link @click="downloadTemplate">
          <template #icon>
            <IconifyIcon icon="lucide:download" />
          </template>
          下载模板 Excel
        </ElButton>
      </div>
      <div v-if="importing" class="mb-3">
        <div class="mb-2 text-sm text-[var(--el-text-color-secondary)]">
          {{ importMessage }}
        </div>
        <ElProgress :percentage="importPercent" :stroke-width="10" />
      </div>
      <ElUpload
        v-else
        class="upload-demo"
        drag
        action="#"
        :http-request="handleImportRequest"
        :show-file-list="false"
        accept=".xlsx,.csv"
      >
        <div class="el-upload__text">将文件拖到此处，或 <em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip text-gray-400 mt-2">支持 .xlsx 或 .csv 文件，请先下载模板填写</div>
        </template>
      </ElUpload>
    </ElDialog>
  </Page>
</template>

<style scoped>
.subscription-count {
  font-weight: 600;
  color: var(--el-color-primary);
}

.subscription-batch-toolbar {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
}

.subscription-batch-toolbar__label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  white-space: nowrap;
}

.subscription-batch-toolbar__selector {
  /* remove fixed width for button mode */
}

.subscription-drawer {
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  gap: 12px;
}

.subscription-drawer__summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.subscription-drawer__summary-item {
  min-width: 0;
  border-left: 3px solid var(--el-color-primary);
  background: var(--el-fill-color-lighter);
  padding: 10px 12px;
}

.subscription-drawer__summary-item span {
  display: block;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 18px;
}

.subscription-drawer__summary-item strong {
  display: block;
  overflow: hidden;
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 600;
  line-height: 22px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.subscription-drawer__toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.subscription-drawer__selector {
  min-width: 320px;
  max-width: 520px;
  flex: 1;
}

.subscription-drawer__table {
  min-height: 0;
  flex: 1;
}

:deep(.subscription-management-drawer .el-drawer__body) {
  display: flex;
  min-height: 0;
  flex-direction: column;
}

@media (max-width: 900px) {
  .subscription-batch-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .subscription-batch-toolbar__selector {
    width: 100%;
  }

  .subscription-drawer__summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .subscription-drawer__toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .subscription-drawer__selector {
    width: 100%;
    max-width: none;
  }
}
</style>
