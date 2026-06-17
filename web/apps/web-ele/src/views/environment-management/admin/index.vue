<script lang="ts" setup>
import type { FormInstance } from 'element-plus';

import type {
  DeviceOptionNode,
  DeviceTypeItem,
  DeviceTypePayload,
  EnvironmentAnnouncementPayload,
  EnvironmentItem,
  EnvironmentPayload,
  TestDeviceItem,
  TestDevicePayload,
} from '#/api/environment-management';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  ElButton,
  ElCascader,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElSelect,
  ElSwitch,
  ElTabPane,
  ElTabs,
  ElTag,
  ElTree,
} from 'element-plus';

import {
  createDeviceApi,
  createDeviceTypeApi,
  createEnvironmentApi,
  deleteDeviceApi,
  deleteDeviceTypeApi,
  deleteEnvironmentApi,
  getEnvironmentAnnouncementApi,
  listDeviceOptionsApi,
  listDevicesApi,
  listDeviceTypesApi,
  listEnvironmentsApi,
  saveEnvironmentAnnouncementApi,
  updateDeviceApi,
  updateDeviceTypeApi,
  updateEnvironmentApi,
} from '#/api/environment-management';
import { useZqTable } from '#/components/zq-table';
import { RichTextEditor } from '#/components/zq-form/rich-text-editor';

import {
  categoryOptions,
  domainOptions,
  useEnvironmentColumns,
  useEnvironmentSearchSchema,
} from './data';

defineOptions({ name: 'EnvironmentManagementAdmin' });

const activeTab = ref('environments');
const environmentDialogVisible = ref(false);
const environmentDialogMode = ref<'create' | 'edit'>('create');
const environmentDialogSaving = ref(false);
const environmentFormRef = ref<FormInstance>();
const deviceOptions = ref<DeviceOptionNode[]>([]);

const emptyEnvironmentForm = (): EnvironmentPayload & { id?: string } => ({
  ip_address: '',
  account: '',
  password: '',
  domain: 'cockpit',
  category: 'test',
  project_name: '',
  vehicle_model: '',
  device_ids: [],
  config_description: '',
  shelf_location: '',
  remark: '',
  sort: 0,
});

const environmentForm = ref<EnvironmentPayload & { id?: string }>(
  emptyEnvironmentForm(),
);

const cascaderProps = {
  checkStrictly: false,
  emitPath: false,
  multiple: true,
  value: 'value',
  label: 'label',
  children: 'children',
};

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
    wrapperClass: 'grid-cols-5',
  },
});

const deviceTypeTree = ref<DeviceTypeItem[]>([]);
const selectedTypeId = ref('');
const deviceKeyword = ref('');

const typeDialogVisible = ref(false);
const typeDialogMode = ref<'create' | 'edit'>('create');
const typeDialogSaving = ref(false);
const typeFormRef = ref<FormInstance>();
const typeForm = ref<DeviceTypePayload & { id?: string }>({
  parent_id: null,
  name: '',
  sort: 0,
  is_active: true,
});

const deviceDialogVisible = ref(false);
const deviceDialogMode = ref<'create' | 'edit'>('create');
const deviceDialogSaving = ref(false);
const deviceFormRef = ref<FormInstance>();
const deviceForm = ref<TestDevicePayload & { id?: string }>({
  device_type_id: '',
  name: '',
  sort: 0,
  is_active: true,
  remark: '',
});

const announcementSaving = ref(false);
const announcementForm = ref<EnvironmentAnnouncementPayload>({
  title: '',
  content_html: '',
  enabled: false,
});

const [DeviceGrid, deviceGridApi] = useZqTable<TestDeviceItem>({
  tableTitle: '测试设备',
  class: 'device-grid',
  gridOptions: {
    columns: [
      { key: 'name', dataKey: 'name', title: '设备名称', minWidth: 160, align: 'center', headerAlign: 'center' },
      { key: 'device_type_path', dataKey: 'device_type_path', title: '类型路径', minWidth: 220, align: 'center', headerAlign: 'center' },
      { key: 'is_active', dataKey: 'is_active', title: '状态', width: 90, align: 'center', headerAlign: 'center' },
      { key: 'remark', dataKey: 'remark', title: '备注', minWidth: 180, align: 'center', headerAlign: 'center' },
      { key: 'actions', dataKey: 'actions', title: '操作', width: 150, align: 'center', headerAlign: 'center', fixed: true, showOverflowTooltip: false },
    ],
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async () =>
          listDevicesApi({
            device_type_id: selectedTypeId.value || undefined,
            keyword: deviceKeyword.value || undefined,
          }),
      },
    },
    pagerConfig: { enabled: false },
    toolbarConfig: { custom: true, refresh: true, search: false, zoom: true },
  },
});

const selectedTypeName = computed(() => {
  const target = findTypeNode(deviceTypeTree.value, selectedTypeId.value);
  return target?.name || '全部类型';
});

async function loadDeviceOptions() {
  // 类型节点只作为级联路径容器，真正保存前会过滤 type: 前缀并由后端再次校验。
  deviceOptions.value = await listDeviceOptionsApi();
}

function findTypeNode(nodes: DeviceTypeItem[], id: string): DeviceTypeItem | null {
  // 设备类型是多级树，递归查找用于左侧树选中态和右侧标题回显。
  for (const node of nodes) {
    if (node.id === id) return node;
    const found = findTypeNode(node.children || [], id);
    if (found) return found;
  }
  return null;
}

async function loadDeviceTypes() {
  deviceTypeTree.value = await listDeviceTypesApi();
}

async function loadDevices() {
  await deviceGridApi.reload();
}

function handleTypeNodeClick(row: DeviceTypeItem) {
  selectedTypeId.value = row.id;
  loadDevices();
}

function openEnvironmentCreate() {
  environmentDialogMode.value = 'create';
  environmentForm.value = emptyEnvironmentForm();
  environmentDialogVisible.value = true;
}

function openEnvironmentEdit(row: EnvironmentItem) {
  environmentDialogMode.value = 'edit';
  environmentForm.value = {
    id: row.id,
    ip_address: row.ip_address,
    account: row.can_view_secret ? row.account : '',
    password: '',
    domain: row.domain,
    category: row.category,
    project_name: row.project_name,
    vehicle_model: row.vehicle_model,
    device_ids: row.device_ids || [],
    config_description: row.config_description || '',
    shelf_location: row.shelf_location,
    remark: row.remark || '',
    sort: row.sort,
  };
  environmentDialogVisible.value = true;
}

async function submitEnvironmentForm() {
  await environmentFormRef.value?.validate();
  environmentDialogSaving.value = true;
  try {
    // 级联类型节点的 value 使用 type: 前缀，只允许真实设备 ID 提交，后端也会做同样校验。
    const deviceIds = (environmentForm.value.device_ids || []).filter(
      (id) => !String(id).startsWith('type:'),
    );
    // 编辑时密码留空代表不修改；这里转成 undefined，避免把旧密码误清空。
    const payload: EnvironmentPayload = {
      ...environmentForm.value,
      device_ids: deviceIds,
      password: environmentForm.value.password || undefined,
    };
    if (environmentDialogMode.value === 'create') {
      await createEnvironmentApi(payload);
      ElMessage.success('环境创建成功');
    } else {
      await updateEnvironmentApi(environmentForm.value.id!, payload);
      ElMessage.success('环境更新成功');
    }
    environmentDialogVisible.value = false;
    await gridApi.reload();
  } finally {
    environmentDialogSaving.value = false;
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

function openTypeCreate(parentId?: string) {
  typeDialogMode.value = 'create';
  typeForm.value = {
    parent_id: parentId || selectedTypeId.value || null,
    name: '',
    sort: 0,
    is_active: true,
  };
  typeDialogVisible.value = true;
}

function openTypeEdit(row: DeviceTypeItem) {
  typeDialogMode.value = 'edit';
  typeForm.value = {
    id: row.id,
    parent_id: row.parent_id || null,
    name: row.name,
    sort: row.sort,
    is_active: row.is_active,
  };
  typeDialogVisible.value = true;
}

async function submitTypeForm() {
  await typeFormRef.value?.validate();
  typeDialogSaving.value = true;
  try {
    // 类型树变化会影响设备级联路径，保存后同步刷新树和环境表单的级联选项。
    if (typeDialogMode.value === 'create') {
      deviceTypeTree.value = await createDeviceTypeApi(typeForm.value);
      ElMessage.success('类型创建成功');
    } else {
      deviceTypeTree.value = await updateDeviceTypeApi(
        typeForm.value.id!,
        typeForm.value,
      );
      ElMessage.success('类型更新成功');
    }
    typeDialogVisible.value = false;
    await loadDeviceOptions();
  } finally {
    typeDialogSaving.value = false;
  }
}

async function removeType(row: DeviceTypeItem) {
  await ElMessageBox.confirm(`确定删除设备类型 ${row.name} 吗？`, '提示', {
    type: 'warning',
  });
  await deleteDeviceTypeApi(row.id);
  if (selectedTypeId.value === row.id) selectedTypeId.value = '';
  await loadDeviceTypes();
  await loadDeviceOptions();
  await loadDevices();
  ElMessage.success('类型删除成功');
}

function openDeviceCreate() {
  if (!selectedTypeId.value) {
    ElMessage.warning('请先选择一个设备类型');
    return;
  }
  deviceDialogMode.value = 'create';
  deviceForm.value = {
    device_type_id: selectedTypeId.value,
    name: '',
    sort: 0,
    is_active: true,
    remark: '',
  };
  deviceDialogVisible.value = true;
}

function openDeviceEdit(row: TestDeviceItem) {
  deviceDialogMode.value = 'edit';
  deviceForm.value = {
    id: row.id,
    device_type_id: row.device_type_id,
    name: row.name,
    sort: row.sort,
    is_active: row.is_active,
    remark: row.remark || '',
  };
  deviceDialogVisible.value = true;
}

async function submitDeviceForm() {
  await deviceFormRef.value?.validate();
  deviceDialogSaving.value = true;
  try {
    // 设备主数据会被环境列表直接展示，保存后同时刷新设备表、级联选项和环境表格。
    if (deviceDialogMode.value === 'create') {
      await createDeviceApi(deviceForm.value);
      ElMessage.success('设备创建成功');
    } else {
      await updateDeviceApi(deviceForm.value.id!, deviceForm.value);
      ElMessage.success('设备更新成功');
    }
    deviceDialogVisible.value = false;
    await loadDevices();
    await loadDeviceOptions();
    await gridApi.reload();
  } finally {
    deviceDialogSaving.value = false;
  }
}

async function removeDevice(row: TestDeviceItem) {
  await ElMessageBox.confirm(`确定删除测试设备 ${row.name} 吗？`, '提示', {
    type: 'warning',
  });
  await deleteDeviceApi(row.id);
  await loadDevices();
  await loadDeviceOptions();
  await gridApi.reload();
  ElMessage.success('设备删除成功');
}

async function loadAnnouncement() {
  const data = await getEnvironmentAnnouncementApi();
  announcementForm.value = {
    title: data.title || '',
    content_html: data.content_html || '',
    enabled: data.enabled,
  };
}

async function submitAnnouncement() {
  announcementSaving.value = true;
  try {
    await saveEnvironmentAnnouncementApi(announcementForm.value);
    ElMessage.success('公告配置已保存');
  } finally {
    announcementSaving.value = false;
  }
}

onMounted(async () => {
  await Promise.all([loadDeviceTypes(), loadDeviceOptions(), loadDevices(), loadAnnouncement()]);
});
</script>

<template>
  <Page auto-content-height content-class="flex h-full min-h-0 flex-col">
    <ElTabs v-model="activeTab" class="environment-admin-tabs">
      <ElTabPane label="环境管理" name="environments">
        <Grid>
          <template #toolbar-tools>
            <ElButton type="primary" @click="openEnvironmentCreate">
              新建环境
            </ElButton>
          </template>
          <template #cell-device_display="{ row }">
            <div class="tag-wrap">
              <ElTag
                v-for="device in row.devices"
                :key="device.id"
                size="small"
                type="success"
              >
                {{ device.display_name }}
              </ElTag>
              <span v-if="!row.devices?.length" class="muted">-</span>
            </div>
          </template>
          <template #cell-actions="{ row }">
            <div class="flex items-center justify-center gap-2">
              <ElButton link type="primary" @click="openEnvironmentEdit(row)">
                编辑
              </ElButton>
              <ElButton link type="danger" @click="removeEnvironment(row)">
                删除
              </ElButton>
            </div>
          </template>
        </Grid>
      </ElTabPane>

      <ElTabPane label="测试设备管理" name="devices">
        <div class="device-workbench">
          <aside class="device-tree-panel">
            <div class="panel-header">
              <div class="header-title">
                <IconifyIcon icon="lucide:network" class="mr-2 size-4" />
                <span>设备类型</span>
              </div>
              <ElButton link type="primary" @click="openTypeCreate()">
                <IconifyIcon icon="lucide:plus" class="mr-1" /> 新建
              </ElButton>
            </div>
            <div class="tree-container">
              <ElTree
                :data="deviceTypeTree"
                :expand-on-click-node="false"
                default-expand-all
                node-key="id"
                @node-click="handleTypeNodeClick"
              >
                <template #default="{ node, data }">
                  <div class="tree-node" :class="{ 'is-active': selectedTypeId === data.id }">
                    <div class="node-content">
                      <IconifyIcon :icon="node.expanded ? 'lucide:folder-open' : 'lucide:folder'" class="node-icon" />
                      <span class="node-label">{{ data.name }}</span>
                    </div>
                    <span class="tree-actions" @click.stop>
                      <ElButton link type="primary" @click="openTypeCreate(data.id)" title="添加子级">
                        <IconifyIcon icon="lucide:plus" class="size-4" />
                      </ElButton>
                      <ElButton link type="primary" @click="openTypeEdit(data)" title="编辑">
                        <IconifyIcon icon="lucide:edit" class="size-4" />
                      </ElButton>
                      <ElButton link type="danger" @click="removeType(data)" title="删除">
                        <IconifyIcon icon="lucide:trash-2" class="size-4" />
                      </ElButton>
                    </span>
                  </div>
                </template>
              </ElTree>
            </div>
          </aside>

          <section class="device-list-panel">
            <div class="list-panel-header">
              <div class="header-title">
                <IconifyIcon icon="lucide:monitor" class="mr-2 size-4" />
                <strong>{{ selectedTypeName }}</strong>
                <span class="muted ml-2 font-normal">测试设备</span>
              </div>
              <div class="device-actions">
                <ElInput
                  v-model="deviceKeyword"
                  clearable
                  placeholder="搜索设备名称/备注"
                  style="width: 220px"
                  @keyup.enter="loadDevices"
                >
                  <template #prefix>
                    <IconifyIcon icon="lucide:search" />
                  </template>
                </ElInput>
                <ElButton @click="loadDevices">查询</ElButton>
                <ElButton type="primary" @click="openDeviceCreate">
                  <IconifyIcon icon="lucide:plus" class="mr-1" /> 新建设备
                </ElButton>
              </div>
            </div>
            <DeviceGrid>
              <template #cell-is_active="{ row }">
                <div class="flex justify-center">
                  <ElTag :type="row.is_active ? 'success' : 'info'">
                    {{ row.is_active ? '启用' : '禁用' }}
                  </ElTag>
                </div>
              </template>
              <template #cell-actions="{ row }">
                <div class="flex items-center justify-center gap-2">
                  <ElButton link type="primary" @click="openDeviceEdit(row)">编辑</ElButton>
                  <ElButton link type="danger" @click="removeDevice(row)">删除</ElButton>
                </div>
              </template>
            </DeviceGrid>
          </section>
        </div>
      </ElTabPane>

      <ElTabPane label="公告配置" name="announcement">
        <section class="announcement-panel">
          <div class="panel-header">
            <div>
              <strong>占用/排队操作公告</strong>
              <span class="muted ml-2">用户点击占用、排队、插队前展示</span>
            </div>
            <ElSwitch
              v-model="announcementForm.enabled"
              active-text="启用"
              inactive-text="停用"
            />
          </div>
          <ElForm label-width="96px">
            <ElFormItem label="公告标题">
              <ElInput v-model="announcementForm.title" maxlength="200" show-word-limit />
            </ElFormItem>
            <ElFormItem label="公告内容">
              <RichTextEditor
                v-model="announcementForm.content_html"
                class="announcement-editor"
                placeholder="请输入占用、排队、插队前需要用户确认的说明"
              />
            </ElFormItem>
            <ElFormItem>
              <ElButton
                :loading="announcementSaving"
                type="primary"
                @click="submitAnnouncement"
              >
                保存公告
              </ElButton>
            </ElFormItem>
          </ElForm>
        </section>
      </ElTabPane>
    </ElTabs>

    <ElDialog
      v-model="environmentDialogVisible"
      :title="environmentDialogMode === 'create' ? '新建环境' : '编辑环境'"
      width="780px"
    >
      <ElForm ref="environmentFormRef" :model="environmentForm" label-width="108px">
        <div class="grid grid-cols-2 gap-x-4">
          <ElFormItem label="IP地址" prop="ip_address" required>
            <ElInput v-model="environmentForm.ip_address" placeholder="请输入 IP 地址" />
          </ElFormItem>
          <ElFormItem label="账号" prop="account">
            <ElInput v-model="environmentForm.account" placeholder="请输入账号" />
          </ElFormItem>
          <ElFormItem label="密码" prop="password">
            <ElInput
              v-model="environmentForm.password"
              placeholder="编辑时留空表示不修改"
              show-password
              type="password"
            />
          </ElFormItem>
          <ElFormItem label="领域" prop="domain" required>
            <ElSelect v-model="environmentForm.domain" class="w-full">
              <ElOption
                v-for="item in domainOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="环境分类" prop="category" required>
            <ElSelect v-model="environmentForm.category" class="w-full">
              <ElOption
                v-for="item in categoryOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="项目名称" prop="project_name">
            <ElInput v-model="environmentForm.project_name" />
          </ElFormItem>
          <ElFormItem label="车型" prop="vehicle_model">
            <ElInput v-model="environmentForm.vehicle_model" />
          </ElFormItem>
          <ElFormItem label="货架位置" prop="shelf_location">
            <ElInput v-model="environmentForm.shelf_location" />
          </ElFormItem>
          <ElFormItem label="排序" prop="sort">
            <ElInputNumber v-model="environmentForm.sort" class="w-full" />
          </ElFormItem>
        </div>
        <ElFormItem label="测试设备">
          <ElCascader
            v-model="environmentForm.device_ids"
            :options="deviceOptions"
            :props="cascaderProps"
            class="w-full"
            clearable
            collapse-tags
            collapse-tags-tooltip
            filterable
            placeholder="请选择测试设备"
          />
        </ElFormItem>
        <ElFormItem label="配置情况">
          <ElInput
            v-model="environmentForm.config_description"
            :rows="4"
            placeholder="请输入环境配置描述"
            type="textarea"
          />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput
            v-model="environmentForm.remark"
            :rows="3"
            placeholder="请输入备注"
            type="textarea"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="environmentDialogVisible = false">取消</ElButton>
        <ElButton
          :loading="environmentDialogSaving"
          type="primary"
          @click="submitEnvironmentForm"
        >
          保存
        </ElButton>
      </template>
    </ElDialog>

    <ElDialog
      v-model="typeDialogVisible"
      :title="typeDialogMode === 'create' ? '新建设备类型' : '编辑设备类型'"
      width="520px"
    >
      <ElForm ref="typeFormRef" :model="typeForm" label-width="96px">
        <ElFormItem label="类型名称" prop="name" required>
          <ElInput v-model="typeForm.name" />
        </ElFormItem>
        <ElFormItem label="父级类型">
          <ElCascader
            v-model="typeForm.parent_id"
            :options="deviceTypeTree"
            :props="{ value: 'id', label: 'name', children: 'children', emitPath: false, checkStrictly: true }"
            class="w-full"
            clearable
            placeholder="不选择则为顶级类型"
          />
        </ElFormItem>
        <ElFormItem label="排序">
          <ElInputNumber v-model="typeForm.sort" class="w-full" />
        </ElFormItem>
        <ElFormItem label="启用">
          <ElSwitch v-model="typeForm.is_active" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="typeDialogVisible = false">取消</ElButton>
        <ElButton :loading="typeDialogSaving" type="primary" @click="submitTypeForm">
          保存
        </ElButton>
      </template>
    </ElDialog>

    <ElDialog
      v-model="deviceDialogVisible"
      :title="deviceDialogMode === 'create' ? '新建测试设备' : '编辑测试设备'"
      width="560px"
    >
      <ElForm ref="deviceFormRef" :model="deviceForm" label-width="96px">
        <ElFormItem label="设备类型" prop="device_type_id" required>
          <ElCascader
            v-model="deviceForm.device_type_id"
            :options="deviceTypeTree"
            :props="{ value: 'id', label: 'name', children: 'children', emitPath: false, checkStrictly: true }"
            class="w-full"
            clearable
            placeholder="请选择设备类型"
          />
        </ElFormItem>
        <ElFormItem label="设备名称" prop="name" required>
          <ElInput v-model="deviceForm.name" />
        </ElFormItem>
        <ElFormItem label="排序">
          <ElInputNumber v-model="deviceForm.sort" class="w-full" />
        </ElFormItem>
        <ElFormItem label="启用">
          <ElSwitch v-model="deviceForm.is_active" />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput v-model="deviceForm.remark" :rows="3" type="textarea" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="deviceDialogVisible = false">取消</ElButton>
        <ElButton :loading="deviceDialogSaving" type="primary" @click="submitDeviceForm">
          保存
        </ElButton>
      </template>
    </ElDialog>
  </Page>
</template>

<style scoped>
.environment-admin-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* 现代分段控制器风格 Tabs */
.environment-admin-tabs > :deep(.el-tabs__header) {
  margin: 0 0 16px 0;
}

.environment-admin-tabs > :deep(.el-tabs__header .el-tabs__nav-wrap) {
  display: inline-block;
  background-color: var(--el-fill-color-light);
  padding: 4px;
  border-radius: 8px;
}

.environment-admin-tabs > :deep(.el-tabs__header .el-tabs__nav-wrap::after) {
  display: none;
}

.environment-admin-tabs > :deep(.el-tabs__header .el-tabs__active-bar) {
  display: none;
}

.environment-admin-tabs > :deep(.el-tabs__header .el-tabs__nav-scroll) {
  overflow: visible;
}

.environment-admin-tabs > :deep(.el-tabs__header .el-tabs__item) {
  height: 32px;
  line-height: 32px;
  padding: 0 20px !important;
  border-radius: 6px;
  font-weight: 500;
  color: var(--el-text-color-regular);
  transition: all 0.3s cubic-bezier(0.645, 0.045, 0.355, 1);
}

.environment-admin-tabs > :deep(.el-tabs__header .el-tabs__item:hover) {
  color: var(--el-text-color-primary);
}

.environment-admin-tabs > :deep(.el-tabs__header .el-tabs__item.is-active) {
  background-color: var(--el-bg-color);
  color: var(--el-color-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  font-weight: 600;
}

.environment-admin-tabs :deep(.el-tabs__content),
.environment-admin-tabs :deep(.el-tab-pane) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.environment-admin-tabs :deep(.zq-table),
.environment-admin-tabs :deep(.bg-card.flex.h-full) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* --- 测试设备管理 Workbench --- */
.device-workbench {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.device-tree-panel {
  display: flex;
  flex-direction: column;
  background-color: var(--el-bg-color);
  border: 1px solid var(--el-border-color-extra-light);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.02);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  background-color: var(--el-fill-color-light);
}

.header-title {
  display: flex;
  align-items: center;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.tree-container {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px;
}

/* ElTree overrides for modern look */
.tree-container :deep(.el-tree-node__content) {
  height: 38px;
  border-radius: 8px;
  margin-bottom: 4px;
  transition: background-color 0.2s;
}

.tree-container :deep(.el-tree-node__content:hover) {
  background-color: var(--el-fill-color);
}

.tree-container :deep(.el-tree-node:focus > .el-tree-node__content) {
  background-color: transparent;
}

.tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 8px;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.tree-node.is-active .node-label {
  color: var(--el-color-primary);
  font-weight: 600;
}

.tree-node.is-active .node-icon {
  color: var(--el-color-primary);
}

.node-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-icon {
  font-size: 16px;
  color: var(--el-text-color-secondary);
  transition: color 0.2s;
}

.tree-actions {
  display: none;
  align-items: center;
  gap: 4px;
}

.tree-node:hover .tree-actions {
  display: flex;
}

.tree-actions :deep(.el-button) {
  padding: 4px;
  height: auto;
}

.device-list-panel {
  display: flex;
  flex-direction: column;
  background-color: var(--el-bg-color);
  border: 1px solid var(--el-border-color-extra-light);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.02);
}

.list-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}

.device-grid {
  flex: 1;
  min-height: 0;
}

.device-actions {
  display: flex;
  gap: 12px;
}

.tag-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.announcement-panel {
  min-height: calc(100vh - 180px);
  padding: 16px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
}

.announcement-editor {
  width: 100%;
}

@media (max-width: 960px) {
  .device-workbench {
    grid-template-columns: 1fr;
  }
}
</style>
