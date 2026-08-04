<script setup lang="ts">
import type {
  DomainDirectoryRule,
  DomainDirectorySetRow,
} from '#/api/integration-report';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { computed, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  ElButton,
  ElDrawer,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElPopconfirm,
  ElSwitch,
  ElTag,
} from 'element-plus';

import {
  createDomainDirectorySetApi,
  deleteDomainDirectorySetApi,
  getDomainDirectorySetApi,
  listDomainDirectorySetsApi,
  updateDomainDirectorySetApi,
} from '#/api/integration-report';
import { useZqTable } from '#/components/zq-table';

import { useColumns, useSearchFormSchema } from './data';

defineOptions({ name: 'IntegrationReportDomainDirectorySets' });

type DrawerMode = 'create' | 'edit';

const drawerVisible = ref(false);
const drawerMode = ref<DrawerMode>('create');
const drawerLoading = ref(false);
const saving = ref(false);
const currentSetId = ref('');
const form = ref({
  name: '',
  description: '',
  enabled: true,
});
const rules = ref<DomainDirectoryRule[]>([]);
const bulkDomainName = ref('');
const bulkDirectoriesText = ref('');

const drawerTitle = computed(() =>
  drawerMode.value === 'create' ? '新建责任田目录配置' : '编辑责任田目录配置',
);

const [Grid, gridApi] = useZqTable<DomainDirectorySetRow>({
  formOptions: {
    schema: useSearchFormSchema(),
    showCollapseButton: false,
  },
  gridOptions: {
    border: true,
    columns: useColumns(),
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
          const res = await listDomainDirectorySetsApi({
            page: page.currentPage,
            page_size: page.pageSize,
            ...form,
          });
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
  } as ZqTableGridOptions<DomainDirectorySetRow>,
});

function resetDrawer() {
  currentSetId.value = '';
  form.value = {
    name: '',
    description: '',
    enabled: true,
  };
  rules.value = [];
  bulkDomainName.value = '';
  bulkDirectoriesText.value = '';
}

function openCreate() {
  drawerMode.value = 'create';
  resetDrawer();
  drawerVisible.value = true;
}

async function openEdit(row: DomainDirectorySetRow) {
  drawerMode.value = 'edit';
  resetDrawer();
  drawerLoading.value = true;
  drawerVisible.value = true;
  try {
    const detail = await getDomainDirectorySetApi(row.id);
    currentSetId.value = detail.id;
    form.value = {
      name: detail.name,
      description: detail.description || '',
      enabled: detail.enabled,
    };
    rules.value = (detail.rules || []).map((rule, index) => ({
      id: rule.id,
      domain_name: rule.domain_name,
      directory: rule.directory,
      sort_order: rule.sort_order ?? index,
      enabled: rule.enabled,
    }));
  } finally {
    drawerLoading.value = false;
  }
}

function addRule() {
  rules.value.push({
    domain_name: '',
    directory: '',
    sort_order: rules.value.length,
    enabled: true,
  });
}

function removeRule(index: number) {
  rules.value.splice(index, 1);
}

function addBulkRules() {
  const domainName = bulkDomainName.value.trim();
  const directories = bulkDirectoriesText.value
    .replaceAll(',', '\n')
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean);
  if (!domainName) {
    ElMessage.warning('请输入责任田领域');
    return;
  }
  if (directories.length === 0) {
    ElMessage.warning('请输入目录字符串');
    return;
  }
  const startIndex = rules.value.length;
  rules.value.push(
    ...directories.map((directory, index) => ({
      domain_name: domainName,
      directory,
      sort_order: startIndex + index,
      enabled: true,
    })),
  );
  bulkDirectoriesText.value = '';
}

function buildPayload() {
  const normalizedRules = rules.value
    .map((rule, index) => ({
      id: rule.id,
      domain_name: rule.domain_name.trim(),
      directory: rule.directory.trim(),
      sort_order: rule.sort_order ?? index,
      enabled: rule.enabled,
    }))
    .filter((rule) => rule.domain_name || rule.directory);
  return {
    name: form.value.name.trim(),
    description: form.value.description.trim(),
    enabled: form.value.enabled,
    rules: normalizedRules,
  };
}

async function submitDrawer() {
  const payload = buildPayload();
  if (!payload.name) {
    ElMessage.warning('请输入配置集名称');
    return;
  }
  const invalidRule = payload.rules.find(
    (rule) => !rule.domain_name || !rule.directory,
  );
  if (invalidRule) {
    ElMessage.warning('规则中的责任田领域和目录均不能为空');
    return;
  }
  saving.value = true;
  try {
    if (drawerMode.value === 'create') {
      await createDomainDirectorySetApi(payload);
      ElMessage.success('创建成功');
    } else {
      await updateDomainDirectorySetApi(currentSetId.value, payload);
      ElMessage.success('更新成功');
    }
    drawerVisible.value = false;
    await gridApi.reload();
  } finally {
    saving.value = false;
  }
}

async function deleteRow(row: DomainDirectorySetRow) {
  await deleteDomainDirectorySetApi(row.id);
  ElMessage.success('删除成功');
  await gridApi.reload();
}
</script>

<template>
  <Page auto-content-height content-class="flex h-full min-h-0 flex-col">
    <Grid class="h-full">
      <template #table-title>
        <ElButton size="small" type="primary" plain @click="openCreate">
          <template #icon>
            <IconifyIcon icon="lucide:plus" />
          </template>
          新建配置
        </ElButton>
      </template>

      <template #description_default="{ row }">
        <span class="domain-directory-muted">{{ row.description || '-' }}</span>
      </template>

      <template #enabled_default="{ row }">
        <ElTag v-if="row.enabled" size="small" type="success">启用</ElTag>
        <ElTag v-else size="small" type="info">停用</ElTag>
      </template>

      <template #updated_default="{ row }">
        {{ row.sys_update_datetime || '-' }}
      </template>

      <template #action_default="{ row }">
        <ElButton size="small" type="primary" link @click="openEdit(row)">
          编辑
        </ElButton>
        <ElPopconfirm
          title="删除后项目配置将无法继续选择该目录配置，确认删除？"
          @confirm="() => deleteRow(row)"
        >
          <template #reference>
            <ElButton size="small" type="danger" link>删除</ElButton>
          </template>
        </ElPopconfirm>
      </template>
    </Grid>

    <ElDrawer
      v-model="drawerVisible"
      :title="drawerTitle"
      size="720px"
      append-to-body
      :close-on-click-modal="false"
    >
      <div v-loading="drawerLoading" class="domain-directory-drawer">
        <ElForm label-width="110px">
          <ElFormItem label="配置集名称" required>
            <ElInput v-model="form.name" placeholder="例如：座舱平台目录配置" />
          </ElFormItem>
          <ElFormItem label="说明">
            <ElInput
              v-model="form.description"
              :rows="2"
              type="textarea"
              placeholder="可填写适用项目或维护说明"
            />
          </ElFormItem>
          <ElFormItem label="启用">
            <ElSwitch v-model="form.enabled" />
          </ElFormItem>
        </ElForm>

        <div class="domain-directory-bulk">
          <ElInput
            v-model="bulkDomainName"
            class="domain-directory-bulk__domain"
            placeholder="责任田领域"
          />
          <ElInput
            v-model="bulkDirectoriesText"
            :rows="3"
            type="textarea"
            placeholder="批量粘贴目录，每行一个；目录按准确字符串保存"
          />
          <ElButton type="primary" plain @click="addBulkRules">
            <template #icon>
              <IconifyIcon icon="lucide:list-plus" />
            </template>
            批量追加目录
          </ElButton>
        </div>

        <div class="domain-directory-rules">
          <div class="domain-directory-rules__head">
            <span>领域目录规则</span>
            <ElButton size="small" plain @click="addRule">
              <template #icon>
                <IconifyIcon icon="lucide:plus" />
              </template>
              添加规则
            </ElButton>
          </div>

          <div
            v-for="(rule, index) in rules"
            :key="`${rule.id || 'new'}-${index}`"
            class="domain-directory-rule"
          >
            <ElInput
              v-model="rule.domain_name"
              class="domain-directory-rule__domain"
              placeholder="责任田领域"
            />
            <ElInput
              v-model="rule.directory"
              class="domain-directory-rule__directory"
              placeholder="目录字符串"
            />
            <ElInputNumber
              v-model="rule.sort_order"
              :min="0"
              controls-position="right"
              class="domain-directory-rule__sort"
            />
            <ElSwitch v-model="rule.enabled" />
            <ElButton
              size="small"
              type="danger"
              link
              @click="removeRule(index)"
            >
              删除
            </ElButton>
          </div>

          <div v-if="rules.length === 0" class="domain-directory-empty">
            暂无规则，可手动添加或批量粘贴目录
          </div>
        </div>

        <div class="domain-directory-footer">
          <ElButton @click="drawerVisible = false">取消</ElButton>
          <ElButton :loading="saving" type="primary" @click="submitDrawer">
            保存配置
          </ElButton>
        </div>
      </div>
    </ElDrawer>
  </Page>
</template>

<style scoped>
.domain-directory-muted {
  color: var(--el-text-color-secondary);
}

.domain-directory-drawer {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  gap: 14px;
}

.domain-directory-bulk {
  display: grid;
  grid-template-columns: 160px minmax(0, 1fr) 126px;
  gap: 10px;
  align-items: start;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  padding: 12px;
}

.domain-directory-bulk__domain {
  width: 160px;
}

.domain-directory-rules {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
  gap: 8px;
}

.domain-directory-rules__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 600;
}

.domain-directory-rule {
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr) 96px 64px 44px;
  gap: 8px;
  align-items: center;
}

.domain-directory-rule__domain {
  width: 150px;
}

.domain-directory-rule__sort {
  width: 96px;
}

.domain-directory-empty {
  display: grid;
  min-height: 120px;
  place-items: center;
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  color: var(--el-text-color-placeholder);
  font-size: 13px;
}

.domain-directory-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 12px;
}
</style>
