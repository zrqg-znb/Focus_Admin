<script lang="ts" setup>
import type { FormInstance } from 'element-plus';

import type {
  McuPlatformItem,
  PlatformPayload,
  VehicleItem,
  VehiclePayload,
} from '#/api/auto-test-report';

import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElMessageBox,
  ElSwitch,
  ElTooltip,
} from 'element-plus';

import {
  createPlatformApi,
  createVehicleApi,
  deletePlatformApi,
  deleteVehicleApi,
  listPlatformsApi,
  listVehiclesApi,
  updatePlatformApi,
  updateVehicleApi,
} from '#/api/auto-test-report';
import { useZqTable } from '#/components/zq-table';

import { useVehicleColumns, useVehicleSearchSchema } from './data';

defineOptions({ name: 'AutoTestVehicleConfig' });

const router = useRouter();
const platformList = ref<McuPlatformItem[]>([]);
const activePlatformId = ref('');

const platformDialogVisible = ref(false);
const platformDialogMode = ref<'create' | 'edit'>('create');
const platformDialogSaving = ref(false);
const platformFormRef = ref<FormInstance>();
const platformForm = ref<PlatformPayload & { id?: string }>({
  name: '',
  version_code: '',
  sort: 0,
  is_active: true,
  remark: '',
});

const vehicleDialogVisible = ref(false);
const vehicleDialogMode = ref<'create' | 'edit'>('create');
const vehicleDialogSaving = ref(false);
const vehicleFormRef = ref<FormInstance>();
const vehicleForm = ref<VehiclePayload & { id?: string }>({
  platform_id: '',
  name: '',
  vehicle_code: '',
  cdc_platform: '',
  execution_machine: '',
  sort: 0,
  is_active: true,
  remark: '',
});

async function loadPlatforms() {
  platformList.value = (await listPlatformsApi()) || [];
  if (!activePlatformId.value && platformList.value.length > 0) {
    activePlatformId.value = platformList.value[0]?.id || '';
  }
}

const [VehicleGrid, vehicleGridApi] = useZqTable({
  tableTitle: '车型配置',
  gridOptions: {
    columns: useVehicleColumns(),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({ form }: { form?: Record<string, any> }) => {
          const items =
            (await listVehiclesApi({
              platform_id: activePlatformId.value || undefined,
              keyword: form?.keyword || '',
            })) || [];
          return { items, total: items.length };
        },
      },
    },
    pagerConfig: { enabled: true, pageSize: 20 },
    toolbarConfig: { custom: true, refresh: true, search: true, zoom: true },
  },
  formOptions: {
    schema: useVehicleSearchSchema(),
    showCollapseButton: false,
    submitOnChange: true,
  },
});

const activePlatform = computed(
  () =>
    platformList.value.find((item) => item.id === activePlatformId.value) ||
    null,
);

async function refreshVehicles() {
  await vehicleGridApi.reload();
}

function openPlatformCreate() {
  platformDialogMode.value = 'create';
  platformForm.value = {
    name: '',
    version_code: '',
    sort: 0,
    is_active: true,
    remark: '',
  };
  platformDialogVisible.value = true;
}

function openPlatformEdit(row: McuPlatformItem) {
  platformDialogMode.value = 'edit';
  platformForm.value = {
    id: row.id,
    name: row.name,
    version_code: row.version_code,
    sort: row.sort,
    is_active: row.is_active,
    remark: row.remark || '',
  };
  platformDialogVisible.value = true;
}

async function submitPlatform() {
  await platformFormRef.value?.validate();
  platformDialogSaving.value = true;
  try {
    if (platformDialogMode.value === 'create') {
      await createPlatformApi(platformForm.value);
      ElMessage.success('平台创建成功');
    } else {
      await updatePlatformApi(platformForm.value.id!, platformForm.value);
      ElMessage.success('平台更新成功');
    }
    platformDialogVisible.value = false;
    await loadPlatforms();
    await refreshVehicles();
  } finally {
    platformDialogSaving.value = false;
  }
}

async function removePlatform(row: McuPlatformItem) {
  await ElMessageBox.confirm(`确定删除平台 ${row.name} 吗？`, '提示', {
    type: 'warning',
  });
  await deletePlatformApi(row.id);
  ElMessage.success('平台删除成功');
  if (activePlatformId.value === row.id) {
    activePlatformId.value = '';
  }
  await loadPlatforms();
  await refreshVehicles();
}

function openVehicleCreate() {
  vehicleDialogMode.value = 'create';
  vehicleForm.value = {
    platform_id: activePlatformId.value || '',
    name: '',
    vehicle_code: '',
    cdc_platform: '',
    execution_machine: '',
    sort: 0,
    is_active: true,
    remark: '',
  };
  vehicleDialogVisible.value = true;
}

function openVehicleEdit(row: VehicleItem) {
  vehicleDialogMode.value = 'edit';
  vehicleForm.value = {
    id: row.id,
    platform_id: row.platform_id,
    name: row.name,
    vehicle_code: row.vehicle_code,
    cdc_platform: row.cdc_platform,
    execution_machine: row.execution_machine,
    sort: row.sort,
    is_active: row.is_active,
    remark: row.remark || '',
  };
  vehicleDialogVisible.value = true;
}

async function submitVehicle() {
  await vehicleFormRef.value?.validate();
  vehicleDialogSaving.value = true;
  try {
    if (vehicleDialogMode.value === 'create') {
      await createVehicleApi(vehicleForm.value);
      ElMessage.success('车型创建成功');
    } else {
      await updateVehicleApi(vehicleForm.value.id!, vehicleForm.value);
      ElMessage.success('车型更新成功');
    }
    vehicleDialogVisible.value = false;
    await loadPlatforms();
    await refreshVehicles();
  } finally {
    vehicleDialogSaving.value = false;
  }
}

async function removeVehicle(row: VehicleItem) {
  await ElMessageBox.confirm(`确定删除车型 ${row.name} 吗？`, '提示', {
    type: 'warning',
  });
  await deleteVehicleApi(row.id);
  ElMessage.success('车型删除成功');
  await loadPlatforms();
  await refreshVehicles();
}

function goDailyResults(row: VehicleItem) {
  router.push({
    path: '/auto-test-report/daily-results',
    query: { vehicleId: row.id },
  });
}

onMounted(async () => {
  vehicleGridApi.setLoading(true);
  try {
    await loadPlatforms();
    await refreshVehicles();
  } finally {
    vehicleGridApi.setLoading(false);
  }
});
</script>

<template>
  <Page auto-content-height content-class="flex flex-col">
    <div class="flex h-full min-h-0 gap-4">
      <div
        class="w-[320px] shrink-0 flex flex-col rounded-lg bg-[var(--el-bg-color)] p-4 shadow-sm min-h-0"
      >
        <div class="mb-3 flex shrink-0 items-center justify-between">
          <div class="text-base font-semibold">MCU平台</div>
          <ElButton type="primary" @click="openPlatformCreate">
            新增平台
          </ElButton>
        </div>
        <div class="space-y-2 overflow-y-auto flex-1 min-h-0 pr-2">
          <div
            v-for="item in platformList"
            :key="item.id"
            class="cursor-pointer rounded-md border p-3 transition-all hover:shadow-sm"
            :class="
              activePlatformId === item.id
                ? 'border-primary bg-[var(--el-color-primary-light-9)]'
                : 'border-[var(--el-border-color-light)] hover:border-[var(--el-border-color)]'
            "
            @click="
              activePlatformId = item.id;
              refreshVehicles();
            "
          >
            <div class="flex items-center justify-between gap-2">
              <div>
                <div class="font-medium">{{ item.name }}</div>
                <div class="text-xs text-gray-500">{{ item.version_code }}</div>
              </div>
              <div class="text-xs text-gray-500">
                {{ item.vehicle_count }} 车型
              </div>
            </div>
            <div class="mt-2 flex justify-end gap-2">
              <ElButton
                link
                type="primary"
                @click.stop="openPlatformEdit(item)"
              >
                编辑
              </ElButton>
              <ElButton link type="danger" @click.stop="removePlatform(item)">
                删除
              </ElButton>
            </div>
          </div>
        </div>
      </div>

      <div class="min-h-0 flex-1">
        <VehicleGrid class="h-full">
          <template #toolbar-actions>
            <div class="flex items-center gap-2">
              <div class="text-sm text-gray-500">
                当前平台：{{ activePlatform?.name || '全部' }}
              </div>
              <ElButton
                type="primary"
                :disabled="!activePlatformId"
                @click="openVehicleCreate"
              >
                新增车型
              </ElButton>
            </div>
          </template>

          <template #cell-name="{ row }">
            <ElButton link type="primary" @click="goDailyResults(row)">
              {{ row.name }}
            </ElButton>
          </template>

          <template #cell-actions="{ row }">
            <div class="flex items-center justify-center gap-1">
              <ElTooltip content="查看测试记录">
                <ElButton link type="success" @click="goDailyResults(row)">
                  测试记录
                </ElButton>
              </ElTooltip>
              <ElTooltip content="编辑">
                <ElButton link type="primary" @click="openVehicleEdit(row)">
                  编辑
                </ElButton>
              </ElTooltip>
              <ElTooltip content="删除">
                <ElButton link type="danger" @click="removeVehicle(row)">
                  删除
                </ElButton>
              </ElTooltip>
            </div>
          </template>
        </VehicleGrid>
      </div>
    </div>

    <ElDialog
      v-model="platformDialogVisible"
      :title="platformDialogMode === 'create' ? '新增平台' : '编辑平台'"
      width="520px"
    >
      <ElForm ref="platformFormRef" :model="platformForm" label-width="96px">
        <ElFormItem label="平台名称" prop="name" required>
          <ElInput v-model="platformForm.name" />
        </ElFormItem>
        <ElFormItem label="版本标识" prop="version_code" required>
          <ElInput v-model="platformForm.version_code" />
        </ElFormItem>
        <ElFormItem label="排序">
          <ElInputNumber v-model="platformForm.sort" class="w-full" />
        </ElFormItem>
        <ElFormItem label="是否启用">
          <ElSwitch v-model="platformForm.is_active" />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput v-model="platformForm.remark" type="textarea" :rows="3" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="platformDialogVisible = false">取消</ElButton>
        <ElButton
          type="primary"
          :loading="platformDialogSaving"
          @click="submitPlatform"
        >
          保存
        </ElButton>
      </template>
    </ElDialog>

    <ElDialog
      v-model="vehicleDialogVisible"
      :title="vehicleDialogMode === 'create' ? '新增车型' : '编辑车型'"
      width="560px"
    >
      <ElForm ref="vehicleFormRef" :model="vehicleForm" label-width="110px">
        <ElFormItem label="车型名称" prop="name" required>
          <ElInput v-model="vehicleForm.name" />
        </ElFormItem>
        <ElFormItem label="车型编号" prop="vehicle_code" required>
          <ElInput v-model="vehicleForm.vehicle_code" />
        </ElFormItem>
        <ElFormItem label="CDC平台" prop="cdc_platform" required>
          <ElInput v-model="vehicleForm.cdc_platform" />
        </ElFormItem>
        <ElFormItem label="执行机器" prop="execution_machine" required>
          <ElInput v-model="vehicleForm.execution_machine" />
        </ElFormItem>
        <ElFormItem label="排序">
          <ElInputNumber v-model="vehicleForm.sort" class="w-full" />
        </ElFormItem>
        <ElFormItem label="是否启用">
          <ElSwitch v-model="vehicleForm.is_active" />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput v-model="vehicleForm.remark" type="textarea" :rows="3" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="vehicleDialogVisible = false">取消</ElButton>
        <ElButton
          type="primary"
          :loading="vehicleDialogSaving"
          @click="submitVehicle"
        >
          保存
        </ElButton>
      </template>
    </ElDialog>
  </Page>
</template>
