<script lang="ts" setup>
import type { FormInstance } from 'element-plus';

import type {
  McuPlatformItem,
  PlatformPayload,
  VehicleItem,
  VehiclePayload,
} from '#/api/auto-test-report';

import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElCheckbox,
  ElCheckboxGroup,
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
import { UserSelector } from '#/components/zq-form/user-selector';
import { useZqTable } from '#/components/zq-table';

import DomainSwitcher from '../components/domain-switcher.vue';
import { setAutoTestReportDailyResultsState } from '../shared/daily-results-state';
import {
  AUTO_TEST_REPORT_VIU_CODES,
  isVehicleControlDomain,
  useAutoTestReportDomain,
} from '../shared/domain';
import { useVehicleColumns, useVehicleSearchSchema } from './data';

defineOptions({ name: 'AutoTestVehicleConfig' });

const { domain, domainMeta } = useAutoTestReportDomain();
const showCdcPlatform = computed(() => !isVehicleControlDomain(domain.value));
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
  domain: domain.value,
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
  viu_codes: [],
  responsible_user_ids: [],
  sort: 0,
  is_active: true,
  remark: '',
});

async function loadPlatforms() {
  platformList.value = (await listPlatformsApi({ domain: domain.value })) || [];
  if (
    !platformList.value.some((item) => item.id === activePlatformId.value) &&
    platformList.value.length > 0
  ) {
    activePlatformId.value = platformList.value[0]?.id || '';
  }
  if (platformList.value.length === 0) {
    activePlatformId.value = '';
  }
}

const [VehicleGrid, vehicleGridApi] = useZqTable({
  tableTitle: '车型配置',
  gridOptions: {
    columns: useVehicleColumns(domain.value),
    border: true,
    stripe: true,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({ form }: { form?: Record<string, any> }) => {
          const items =
            (await listVehiclesApi({
              domain: domain.value,
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
    domain: domain.value,
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
    domain: row.domain,
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
    platformForm.value.domain = domain.value;
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
    viu_codes: [],
    responsible_user_ids: [],
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
    cdc_platform: showCdcPlatform.value ? row.cdc_platform : '',
    execution_machine: row.execution_machine,
    viu_codes: row.viu_codes || [],
    responsible_user_ids: row.responsible_user_ids || [],
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
    const payload = {
      ...vehicleForm.value,
      cdc_platform: showCdcPlatform.value ? vehicleForm.value.cdc_platform : '',
      viu_codes: isVehicleControlDomain(domain.value)
        ? vehicleForm.value.viu_codes
        : [],
    };
    if (isVehicleControlDomain(domain.value) && payload.viu_codes.length === 0) {
      ElMessage.warning('车控或车控IO车型至少需要选择一个可用 VIU 编号');
      return;
    }
    if (vehicleDialogMode.value === 'create') {
      await createVehicleApi(payload);
      ElMessage.success('车型创建成功');
    } else {
      await updateVehicleApi(vehicleForm.value.id!, payload);
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
  setAutoTestReportDailyResultsState(domain.value, {
    activeView: 'vehicle',
    vehicleId: row.id,
  });
  router.push('/auto-test-report/daily-results');
}

watch(
  domain,
  async () => {
    platformForm.value.domain = domain.value;
    vehicleGridApi.setGridOptions({
      columns: useVehicleColumns(domain.value),
    });
    await loadPlatforms();
    await refreshVehicles();
  },
  { immediate: false },
);

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
  <Page auto-content-height content-class="flex min-w-0 flex-col">
    <div class="mb-4 rounded-lg bg-[var(--el-bg-color)] p-4 shadow-sm">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div class="text-base font-semibold">
            {{ domainMeta.platformPanelTitle }}
          </div>
          <div class="mt-1 text-sm text-gray-500">
            {{ domainMeta.platformPanelHint }}
          </div>
        </div>
        <DomainSwitcher />
      </div>
    </div>

    <div class="flex h-full min-h-0 min-w-0 gap-4 overflow-hidden">
      <div
        class="flex min-h-0 w-[320px] shrink-0 flex-col rounded-lg bg-[var(--el-bg-color)] p-4 shadow-sm"
      >
        <div class="mb-3 flex shrink-0 items-center justify-between">
          <div class="text-base font-semibold">
            {{ domainMeta.platformLabel }}
          </div>
          <ElButton type="primary" @click="openPlatformCreate">
            新增{{ domainMeta.platformLabel }}
          </ElButton>
        </div>
        <div class="min-h-0 flex-1 space-y-2 overflow-y-auto pr-2">
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

      <div class="min-h-0 min-w-0 flex-1">
        <VehicleGrid class="h-full w-full min-w-0">
          <template #cell-responsible_users="{ row }">
            {{
              row.responsible_users.map((user) => user.name).join('、') || '-'
            }}
          </template>
          <template #toolbar-actions>
            <div class="flex items-center gap-2">
              <div class="text-sm text-gray-500">
                当前{{ domainMeta.platformLabel }}：{{
                  activePlatform?.name || '全部'
                }}
              </div>
              <ElButton
                type="primary"
                :disabled="!activePlatformId"
                @click="openVehicleCreate"
              >
                新增{{
                  isVehicleControlDomain(domain)
                    ? domain === 'vehicle_io'
                      ? '车控IO车型'
                      : '车控车型'
                    : domain === 'cockpit_soc'
                      ? '座舱SOC车型'
                      : '座舱MCU车型'
                }}
              </ElButton>
            </div>
          </template>

          <template #cell-name="{ row }">
            <ElButton link type="primary" @click="goDailyResults(row)">
              {{ row.name }}
            </ElButton>
          </template>

          <template #cell-viu_codes="{ row }">
            <span>{{
              row.viu_codes?.length ? row.viu_codes.join(' / ') : '-'
            }}</span>
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
      :title="
        platformDialogMode === 'create'
          ? `新增${domainMeta.platformLabel}`
          : `编辑${domainMeta.platformLabel}`
      "
      width="520px"
    >
      <ElForm ref="platformFormRef" :model="platformForm" label-width="96px">
        <ElFormItem
          :label="`${domainMeta.platformLabel}名称`"
          prop="name"
          required
        >
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
      :title="
        vehicleDialogMode === 'create'
          ? isVehicleControlDomain(domain)
            ? domain === 'vehicle_io'
              ? '新增车控IO车型'
              : '新增车控车型'
            : domain === 'cockpit_soc'
              ? '新增座舱SOC车型'
              : '新增座舱MCU车型'
          : isVehicleControlDomain(domain)
            ? domain === 'vehicle_io'
              ? '编辑车控IO车型'
              : '编辑车控车型'
            : domain === 'cockpit_soc'
              ? '编辑座舱SOC车型'
              : '编辑座舱MCU车型'
      "
      width="560px"
    >
      <ElForm ref="vehicleFormRef" :model="vehicleForm" label-width="110px">
        <ElFormItem label="车型名称" prop="name" required>
          <ElInput v-model="vehicleForm.name" />
        </ElFormItem>
        <ElFormItem label="车型编号" prop="vehicle_code" required>
          <ElInput v-model="vehicleForm.vehicle_code" />
        </ElFormItem>
        <ElFormItem
          v-if="showCdcPlatform"
          label="CDC平台"
          prop="cdc_platform"
          required
        >
          <ElInput v-model="vehicleForm.cdc_platform" />
        </ElFormItem>
        <ElFormItem label="执行机器" prop="execution_machine" required>
          <ElInput v-model="vehicleForm.execution_machine" />
        </ElFormItem>
        <ElFormItem label="责任人">
          <UserSelector
            v-model="vehicleForm.responsible_user_ids"
            multiple
            class="w-full"
            placeholder="请选择责任人"
          />
        </ElFormItem>
        <ElFormItem v-if="isVehicleControlDomain(domain)" label="可用 VIU 编号">
          <ElCheckboxGroup
            v-model="vehicleForm.viu_codes"
            class="flex flex-wrap gap-3"
          >
            <ElCheckbox
              v-for="code in AUTO_TEST_REPORT_VIU_CODES"
              :key="code"
              :label="code"
              :value="code"
            >
              {{ code }}
            </ElCheckbox>
          </ElCheckboxGroup>
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
