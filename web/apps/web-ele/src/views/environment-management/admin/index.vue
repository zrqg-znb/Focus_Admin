<script lang="ts" setup>
import type { FormInstance } from 'element-plus';

import type {
  EnvironmentItem,
  EnvironmentPayload,
} from '#/api/environment-management';

import { ref } from 'vue';

import { Page } from '@vben/common-ui';
import { Edit, Plus, Trash2 } from '@vben/icons';

import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElSelect,
} from 'element-plus';

import {
  createEnvironmentApi,
  deleteEnvironmentApi,
  listEnvironmentsApi,
  updateEnvironmentApi,
} from '#/api/environment-management';
import { useZqTable } from '#/components/zq-table';

import {
  categoryOptions,
  domainOptions,
  useEnvironmentColumns,
  useEnvironmentSearchSchema,
} from './data';

defineOptions({ name: 'EnvironmentManagementAdmin' });

const dialogVisible = ref(false);
const dialogMode = ref<'create' | 'edit'>('create');
const dialogSaving = ref(false);
const formRef = ref<FormInstance>();
const configText = ref('{}');

const emptyForm = (): EnvironmentPayload & { id?: string } => ({
  ip_address: '',
  account: '',
  password: '',
  domain: 'cockpit',
  category: 'test',
  project_name: '',
  vehicle_model: '',
  device_material: '',
  asset_number: '',
  config: {},
  shelf_location: '',
  sort: 0,
});

const form = ref<EnvironmentPayload & { id?: string }>(emptyForm());

const [Grid, gridApi] = useZqTable({
  tableTitle: '环境配置',
  gridOptions: {
    columns: useEnvironmentColumns(),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ form, page }: any) =>
          listEnvironmentsApi({
            ...form,
            page: page.currentPage,
            pageSize: page.pageSize,
          }),
      },
    },
    pagerConfig: { enabled: true, pageSize: 20 },
    toolbarConfig: { custom: true, refresh: true, search: true, zoom: true },
  },
  formOptions: {
    schema: useEnvironmentSearchSchema(),
    showCollapseButton: false,
    submitOnChange: true,
  },
});

function parseConfigText() {
  try {
    const parsed = JSON.parse(configText.value || '{}');
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
      ElMessage.warning('配置情况必须是 JSON 对象');
      return null;
    }
    return parsed;
  } catch {
    ElMessage.warning('配置情况不是合法 JSON');
    return null;
  }
}

function openCreate() {
  dialogMode.value = 'create';
  form.value = emptyForm();
  configText.value = '{}';
  dialogVisible.value = true;
}

function openEdit(row: EnvironmentItem) {
  dialogMode.value = 'edit';
  form.value = {
    id: row.id,
    ip_address: row.ip_address,
    account: row.can_view_secret ? row.account : '',
    password: '',
    domain: row.domain,
    category: row.category,
    project_name: row.project_name,
    vehicle_model: row.vehicle_model,
    device_material: row.device_material,
    asset_number: row.asset_number,
    config: row.config || {},
    shelf_location: row.shelf_location,
    sort: row.sort,
  };
  configText.value = JSON.stringify(row.config || {}, null, 2);
  dialogVisible.value = true;
}

async function submitForm() {
  await formRef.value?.validate();
  const config = parseConfigText();
  if (!config) return;

  dialogSaving.value = true;
  try {
    const payload: EnvironmentPayload = {
      ...form.value,
      config,
      password: form.value.password || undefined,
    };
    if (dialogMode.value === 'create') {
      await createEnvironmentApi(payload);
      ElMessage.success('环境创建成功');
    } else {
      await updateEnvironmentApi(form.value.id!, payload);
      ElMessage.success('环境更新成功');
    }
    dialogVisible.value = false;
    await gridApi.reload();
  } finally {
    dialogSaving.value = false;
  }
}

async function removeEnvironment(row: EnvironmentItem) {
  await ElMessageBox.confirm(`确定删除环境 ${row.ip_address} 吗？`, '提示', {
    type: 'warning',
  });
  await deleteEnvironmentApi(row.id);
  ElMessage.success('环境删除成功');
  await gridApi.reload();
}
</script>

<template>
  <Page auto-content-height>
    <Grid>
      <template #toolbar-tools>
        <ElButton type="primary" @click="openCreate">
          <Plus class="mr-1 size-4" />
          新建环境
        </ElButton>
      </template>
      <template #actions="{ row }">
        <div class="flex items-center justify-center gap-2">
          <ElButton link type="primary" @click="openEdit(row)">
            <Edit class="mr-1 size-4" />
            编辑
          </ElButton>
          <ElButton link type="danger" @click="removeEnvironment(row)">
            <Trash2 class="mr-1 size-4" />
            删除
          </ElButton>
        </div>
      </template>
    </Grid>

    <ElDialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建环境' : '编辑环境'"
      width="760px"
    >
      <ElForm ref="formRef" :model="form" label-width="108px">
        <div class="grid grid-cols-2 gap-x-4">
          <ElFormItem label="IP地址" prop="ip_address" required>
            <ElInput v-model="form.ip_address" placeholder="请输入 IP 地址" />
          </ElFormItem>
          <ElFormItem label="账号" prop="account">
            <ElInput v-model="form.account" placeholder="请输入账号" />
          </ElFormItem>
          <ElFormItem label="密码" prop="password">
            <ElInput
              v-model="form.password"
              placeholder="编辑时留空表示不修改"
              show-password
              type="password"
            />
          </ElFormItem>
          <ElFormItem label="领域" prop="domain" required>
            <ElSelect v-model="form.domain" class="w-full">
              <ElOption
                v-for="item in domainOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="环境分类" prop="category" required>
            <ElSelect v-model="form.category" class="w-full">
              <ElOption
                v-for="item in categoryOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="项目名称" prop="project_name">
            <ElInput v-model="form.project_name" />
          </ElFormItem>
          <ElFormItem label="车型" prop="vehicle_model">
            <ElInput v-model="form.vehicle_model" />
          </ElFormItem>
          <ElFormItem label="设备物料" prop="device_material">
            <ElInput v-model="form.device_material" />
          </ElFormItem>
          <ElFormItem label="资产编号" prop="asset_number">
            <ElInput v-model="form.asset_number" />
          </ElFormItem>
          <ElFormItem label="货架位置" prop="shelf_location">
            <ElInput v-model="form.shelf_location" />
          </ElFormItem>
          <ElFormItem label="排序" prop="sort">
            <ElInputNumber v-model="form.sort" class="w-full" />
          </ElFormItem>
        </div>
        <ElFormItem label="配置情况">
          <ElInput
            v-model="configText"
            :rows="7"
            placeholder='例如 {"系统版本":"v1.0","刷写状态":"已完成"}'
            type="textarea"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton :loading="dialogSaving" type="primary" @click="submitForm">
          保存
        </ElButton>
      </template>
    </ElDialog>
  </Page>
</template>
