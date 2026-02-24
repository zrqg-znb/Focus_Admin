<script lang="ts" setup>
import type {
  HardwarePoint,
  PlatformConfig,
} from '#/api/project-manager/hardware';

import { computed, ref, watch } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import {
  ElButton,
  ElDatePicker,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  configModuleApi,
  getProjectQualityDetailsApi,
} from '#/api/project-manager/code_quality';
import { listHardwareConfigOptionsApi } from '#/api/project-manager/hardware';
import {
  getMilestoneBoardApi,
  updateMilestoneApi,
} from '#/api/project-manager/milestone';
import {
  createProjectApi,
  getProjectApi,
  updateProjectApi,
} from '#/api/project-manager/project';
import UserSelector from '#/components/zq-form/user-selector/user-selector.vue';

import { getProjectFormSchema } from '../data';

const emit = defineEmits<{
  success: [];
}>();

const formData = ref<any>();
const milestoneForm = ref({
  qg1_date: '',
  qg2_date: '',
  qg3_date: '',
  qg4_date: '',
  qg5_date: '',
  qg6_date: '',
  qg7_date: '',
  qg8_date: '',
});
const iterationConfig = ref({
  design_id: '',
  sub_teams: [] as string[],
});
const enableMilestone = ref(false);
const enableIteration = ref(false);
const enableQuality = ref(false);
const enableDts = ref(false);
const enableHardwareConfig = ref(false);
const projectDomain = ref('');
const hardwarePoints = ref<HardwarePoint[]>([]);
const viuPlatforms = ref<PlatformConfig[]>([]);
const cdcPlatforms = ref<PlatformConfig[]>([]);
const smartScreenVersions = ref<PlatformConfig[]>([]);
const viuPlatformId = ref('');
type PhaseConfigFormItem = {
  cdc_platform_id: string;
  id?: string;
  smart_screen_version_id: string;
  stage_name: string;
  stage_range: string[];
  vehicle_hardware: Array<{ board: string; bomid: string; point: string }>;
};
const phaseConfigs = ref<PhaseConfigFormItem[]>([]);
const hardwareLoading = ref(false);
const detailLoading = ref(false);
const activeTab = ref('basic');
const dtsConfig = ref({
  ws_id: '',
  di_teams: [] as string[],
});
const newDiTeam = ref('');
const newSubTeam = ref('');
type ModuleRow = {
  id?: string;
  module: string;
  oem_name: string;
  owner_ids: string[];
};
const moduleRows = ref<ModuleRow[]>([]);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    colon: true,
    componentProps: {
      class: 'w-full',
    },
  },
  handleValuesChange(values, fieldsChanged) {
    if (fieldsChanged.includes('domain')) {
      projectDomain.value = values.domain || '';
    }
  },
  schema: getProjectFormSchema(),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-1 gap-x-4',
});

const [Drawer, drawerApi] = useVbenDrawer({
  onConfirm: onSubmit,
  async onOpenChange(isOpen) {
    if (!isOpen) return;

    activeTab.value = 'basic';
    detailLoading.value = true;
    const drawerData = drawerApi.getData<any>();

    try {
      if (drawerData) {
        const data = drawerData.id
          ? await getProjectApi(drawerData.id)
          : drawerData;
        formData.value = data;
        const normalized = {
          ...formData.value,
          manager_ids: Array.isArray(formData.value.managers_info)
            ? formData.value.managers_info.map((m: any) => m.id)
            : [],
        };
        enableMilestone.value = !!data.enable_milestone;
        enableIteration.value = !!data.enable_iteration;
        enableQuality.value = !!data.enable_quality;
        enableDts.value = !!data.enable_dts;
        enableHardwareConfig.value = !!data.enable_hardware_config;
        viuPlatformId.value = data.viu_platform_id || data.viu_platform || '';
        projectDomain.value = data.domain || '';
        iterationConfig.value.design_id = data.design_id || '';
        iterationConfig.value.sub_teams = Array.isArray(data.sub_teams)
          ? data.sub_teams
          : [];
        dtsConfig.value.ws_id = data.ws_id || '';
        dtsConfig.value.di_teams = Array.isArray(data.di_teams)
          ? data.di_teams
          : [];
        normalizePhaseConfigs(data.phase_configs || []);
        milestoneForm.value = {
          qg1_date: '',
          qg2_date: '',
          qg3_date: '',
          qg4_date: '',
          qg5_date: '',
          qg6_date: '',
          qg7_date: '',
          qg8_date: '',
        };

        try {
          const milestones = await getMilestoneBoardApi({ keyword: data.name });
          const current = milestones.find((m) => m.project_id === data.id);
          if (current) {
            milestoneForm.value = {
              qg1_date: current.qg1_date || '',
              qg2_date: current.qg2_date || '',
              qg3_date: current.qg3_date || '',
              qg4_date: current.qg4_date || '',
              qg5_date: current.qg5_date || '',
              qg6_date: current.qg6_date || '',
              qg7_date: current.qg7_date || '',
              qg8_date: current.qg8_date || '',
            };
          }
        } catch (error) {
          console.error('Failed to fetch milestone data', error);
        }

        if (data.enable_quality) {
          try {
            const details = await getProjectQualityDetailsApi(data.id);
            moduleRows.value =
              details && details.length > 0
                ? details.map((d) => ({
                    id: d.id,
                    oem_name: d.oem_name,
                    module: d.module,
                    owner_ids: d.owner_ids || [],
                  }))
                : [];
          } catch (error) {
            console.error('Failed to fetch quality modules', error);
            moduleRows.value = [];
          }
        } else {
          moduleRows.value = [];
        }

        formApi.setValues(normalized);
        await loadHardwarePoints();
        return;
      }

      formData.value = undefined;
      formApi.resetForm();
      iterationConfig.value = { design_id: '', sub_teams: [] };
      dtsConfig.value = { ws_id: '', di_teams: [] };
      moduleRows.value = [];
      milestoneForm.value = {
        qg1_date: '',
        qg2_date: '',
        qg3_date: '',
        qg4_date: '',
        qg5_date: '',
        qg6_date: '',
        qg7_date: '',
        qg8_date: '',
      };
      enableMilestone.value = false;
      enableIteration.value = false;
      enableQuality.value = false;
      enableDts.value = false;
      resetHardwareConfig();
      await loadHardwarePoints();
    } finally {
      detailLoading.value = false;
    }
  },
});

const getDrawerTitle = computed(() =>
  formData.value?.id ? '编辑项目' : '新增项目',
);

const hardwareScenario = computed(() => {
  if (projectDomain.value.includes('座舱')) return 'cockpit';
  if (projectDomain.value.includes('车控')) return 'vehicle';
  return '';
});

const cockpitStageName = '座舱配套版本';

function createEmptyVehiclePhase(): PhaseConfigFormItem {
  return {
    stage_name: '',
    stage_range: [],
    vehicle_hardware: [{ point: '', board: '', bomid: '' }],
    cdc_platform_id: '',
    smart_screen_version_id: '',
  };
}

function createEmptyCockpitConfig(): PhaseConfigFormItem {
  return {
    stage_name: cockpitStageName,
    stage_range: [],
    vehicle_hardware: [{ point: '', board: '', bomid: '' }],
    cdc_platform_id: '',
    smart_screen_version_id: '',
  };
}

function ensureCockpitSingleConfig() {
  if (hardwareScenario.value !== 'cockpit') return;
  if (phaseConfigs.value.length === 0) {
    phaseConfigs.value = [createEmptyCockpitConfig()];
    return;
  }
  const first = phaseConfigs.value[0] ?? createEmptyCockpitConfig();
  phaseConfigs.value = [
    {
      ...createEmptyCockpitConfig(),
      ...first,
      stage_name: cockpitStageName,
      stage_range: [],
    },
  ];
}

function normalizePhaseConfigs(
  source?: Array<{
    cdc_platform_id?: string;
    id?: string;
    smart_screen_version_id?: string;
    stage_end?: string;
    stage_name?: string;
    stage_start?: string;
    vehicle_hardware?: Array<{ board: string; bomid?: string; point: string }>;
  }>,
) {
  if (!source || source.length === 0) {
    phaseConfigs.value =
      hardwareScenario.value === 'cockpit' ? [createEmptyCockpitConfig()] : [];
    return;
  }
  const mapped = source.map((item) => ({
    id: item.id,
    stage_name:
      hardwareScenario.value === 'cockpit'
        ? cockpitStageName
        : item.stage_name || '',
    stage_range:
      hardwareScenario.value === 'vehicle' && item.stage_start && item.stage_end
        ? [item.stage_start, item.stage_end]
        : [],
    vehicle_hardware:
      item.vehicle_hardware && item.vehicle_hardware.length > 0
        ? item.vehicle_hardware.map((pair) => ({
            point: pair.point || '',
            board: pair.board || '',
            bomid: pair.bomid || '',
          }))
        : [{ point: '', board: '', bomid: '' }],
    cdc_platform_id: item.cdc_platform_id || '',
    smart_screen_version_id: item.smart_screen_version_id || '',
  }));
  const firstMapped = mapped[0] ?? createEmptyCockpitConfig();
  phaseConfigs.value =
    hardwareScenario.value === 'cockpit' ? [firstMapped] : mapped;
}

function addPhase() {
  if (hardwareScenario.value === 'cockpit') {
    ensureCockpitSingleConfig();
    return;
  }
  phaseConfigs.value.push(createEmptyVehiclePhase());
}

function removePhase(index: number) {
  if (hardwareScenario.value === 'cockpit') return;
  phaseConfigs.value.splice(index, 1);
}

function addVehicleHardwareRow(phase: PhaseConfigFormItem) {
  phase.vehicle_hardware.push({ point: '', board: '', bomid: '' });
}

function removeVehicleHardwareRow(phase: PhaseConfigFormItem, index: number) {
  phase.vehicle_hardware.splice(index, 1);
}

function getBoardsByPoint(point: string) {
  const currentPoint = hardwarePoints.value.find((item) => item.code === point);
  return currentPoint?.boards || [];
}

function getPhasePayload() {
  if (hardwareScenario.value === 'cockpit') {
    const phase = phaseConfigs.value[0] || createEmptyCockpitConfig();
    return [
      {
        stage_name: cockpitStageName,
        cdc_platform_id: phase.cdc_platform_id || undefined,
        smart_screen_version_id: phase.smart_screen_version_id || undefined,
      },
    ];
  }
  return phaseConfigs.value.map((phase) => {
    const payload: Record<string, any> = {
      stage_name: phase.stage_name.trim(),
      stage_start: phase.stage_range?.[0] || undefined,
      stage_end: phase.stage_range?.[1] || undefined,
    };
    if (hardwareScenario.value === 'vehicle') {
      payload.vehicle_hardware = phase.vehicle_hardware
        .filter((item) => item.point && item.board && item.bomid)
        .map((item) => ({
          point: item.point,
          board: item.board,
          bomid: item.bomid,
        }));
    }
    return payload;
  });
}

function isHardwareConfigValid(showMessage = false) {
  if (!enableHardwareConfig.value) return true;
  if (!hardwareScenario.value) {
    if (showMessage) {
      ElMessage.warning('项目领域仅支持车控项目或座舱项目');
    }
    return false;
  }
  if (phaseConfigs.value.length === 0) {
    if (showMessage) {
      ElMessage.warning(
        hardwareScenario.value === 'cockpit'
          ? '请配置座舱配套版本'
          : '请至少配置一个阶段',
      );
    }
    return false;
  }

  if (hardwareScenario.value === 'cockpit' && phaseConfigs.value.length !== 1) {
    if (showMessage) {
      ElMessage.warning('座舱项目仅允许配置一个配套版本');
    }
    return false;
  }

  const stageSet = new Set<string>();
  for (const phase of phaseConfigs.value) {
    if (hardwareScenario.value === 'vehicle') {
      const stageName = phase.stage_name.trim();
      if (!stageName) {
        if (showMessage) {
          ElMessage.warning('阶段名称不能为空');
        }
        return false;
      }
      if (stageSet.has(stageName)) {
        if (showMessage) {
          ElMessage.warning(`阶段名称重复: ${stageName}`);
        }
        return false;
      }
      stageSet.add(stageName);
      if (!viuPlatformId.value) {
        if (showMessage) {
          ElMessage.warning('请选择 VIU 平台');
        }
        return false;
      }
      const hasPartialRow = phase.vehicle_hardware.some((item) => {
        const hasAny = !!(item.point || item.board || item.bomid);
        const hasAll = !!(item.point && item.board && item.bomid);
        return hasAny && !hasAll;
      });
      if (hasPartialRow) {
        if (showMessage) {
          ElMessage.warning(`阶段 ${stageName} 存在未填写完整的硬件组合`);
        }
        return false;
      }
      const validRows = phase.vehicle_hardware.filter(
        (item) => item.point && item.board && item.bomid,
      );
      if (validRows.length === 0) {
        if (showMessage) {
          ElMessage.warning(`阶段 ${stageName} 需要完整填写点位、板子和BOMID`);
        }
        return false;
      }
    }

    if (
      hardwareScenario.value === 'cockpit' &&
      (!phase.cdc_platform_id || !phase.smart_screen_version_id)
    ) {
      if (showMessage) {
        ElMessage.warning('请完整配置 CDC 平台和智慧屏版本');
      }
      return false;
    }
  }
  return true;
}

async function loadHardwarePoints() {
  if (
    (hardwarePoints.value.length > 0 ||
      viuPlatforms.value.length > 0 ||
      cdcPlatforms.value.length > 0 ||
      smartScreenVersions.value.length > 0) &&
    !hardwareLoading.value
  ) {
    return;
  }
  hardwareLoading.value = true;
  try {
    const options = await listHardwareConfigOptionsApi();
    hardwarePoints.value = options.points || [];
    viuPlatforms.value = options.viu_platforms || [];
    cdcPlatforms.value = options.cdc_platforms || [];
    smartScreenVersions.value = options.smart_screen_versions || [];
  } catch (error) {
    console.error(error);
    ElMessage.error('获取典配配置项失败');
  } finally {
    hardwareLoading.value = false;
  }
}

function resetHardwareConfig() {
  enableHardwareConfig.value = false;
  viuPlatformId.value = '';
  phaseConfigs.value = [];
  projectDomain.value = '';
}

watch(
  () => hardwareScenario.value,
  (scenario) => {
    if (!enableHardwareConfig.value) return;
    if (scenario === 'cockpit') {
      ensureCockpitSingleConfig();
    } else if (scenario === 'vehicle' && phaseConfigs.value.length === 0) {
      phaseConfigs.value = [createEmptyVehiclePhase()];
    }
  },
);

watch(
  () => enableHardwareConfig.value,
  (enabled) => {
    if (!enabled) {
      phaseConfigs.value = [];
      viuPlatformId.value = '';
      return;
    }
    if (hardwareScenario.value === 'cockpit') {
      ensureCockpitSingleConfig();
    } else if (
      hardwareScenario.value === 'vehicle' &&
      phaseConfigs.value.length === 0
    ) {
      phaseConfigs.value = [createEmptyVehiclePhase()];
    }
  },
);

async function onSubmit() {
  const { valid } = await formApi.validate();
  if (valid) {
    const data = await formApi.getValues<any>();
    projectDomain.value = data.domain || '';
    if (!isHardwareConfigValid(true)) {
      activeTab.value = 'hardware';
      return;
    }
    drawerApi.lock();
    try {
      // 前端校验重复模块
      if (enableQuality.value && moduleRows.value.length > 0) {
        const seen = new Set();
        for (const row of moduleRows.value) {
          if (!row.oem_name || !row.module) continue;
          const key = `${row.oem_name}|${row.module}`;
          if (seen.has(key)) {
            ElMessage.error(`重复的模块配置: ${row.oem_name} - ${row.module}`);
            return;
          }
          seen.add(key);
        }
      }

      // 准备提交数据
      const payload = {
        ...data,
        enable_milestone: enableMilestone.value,
        enable_iteration: enableIteration.value,
        enable_quality: enableQuality.value,
        enable_dts: enableDts.value,
        enable_hardware_config: enableHardwareConfig.value,
        viu_platform_id:
          enableHardwareConfig.value && hardwareScenario.value === 'vehicle'
            ? viuPlatformId.value || undefined
            : undefined,
        phase_configs: enableHardwareConfig.value
          ? getPhasePayload()
          : undefined,
        design_id: enableIteration.value
          ? iterationConfig.value.design_id
          : undefined,
        sub_teams: enableIteration.value
          ? iterationConfig.value.sub_teams
          : undefined,
        ws_id: enableDts.value ? dtsConfig.value.ws_id : undefined,
        di_teams: enableDts.value ? dtsConfig.value.di_teams : undefined,
      };

      if (formData.value?.id) {
        const projectId = formData.value.id;
        await updateProjectApi(projectId, payload);
        if (enableMilestone.value) {
          // 过滤空日期字符串
          const milestonePayload = Object.fromEntries(
            Object.entries(milestoneForm.value).filter(
              ([_, v]) => v && v !== '',
            ),
          );
          await updateMilestoneApi(projectId, milestonePayload);
        }
        if (enableIteration.value) {
          // 迭代数据仅通过项目属性(design_id, sub_teams)由后端联动更新，无需直接调用 iteration API
        }
        if (enableQuality.value && moduleRows.value.length > 0) {
          for (const row of moduleRows.value) {
            await configModuleApi({
              id: row.id,
              project_id: projectId,
              oem_name: row.oem_name,
              module: row.module,
              owner_ids: row.owner_ids,
            });
          }
        }
        ElMessage.success('更新成功');
      } else {
        const project = await createProjectApi(payload);
        const projectId = project.id;
        if (enableMilestone.value) {
          await updateMilestoneApi(projectId, milestoneForm.value);
        }
        if (enableIteration.value) {
          // 迭代数据仅通过项目属性(design_id, sub_teams)由后端联动更新，无需直接调用 iteration API
        }
        if (enableQuality.value && moduleRows.value.length > 0) {
          for (const row of moduleRows.value) {
            await configModuleApi({
              id: row.id,
              project_id: projectId,
              oem_name: row.oem_name,
              module: row.module,
              owner_ids: row.owner_ids,
            });
          }
        }
        ElMessage.success('创建成功');
      }
      drawerApi.close();
      emit('success');
    } finally {
      drawerApi.unlock();
    }
  }
}
</script>

<template>
  <Drawer class="w-full max-w-[1100px]" :title="getDrawerTitle">
    <div
      v-loading="detailLoading"
      class="min-h-[420px]"
      element-loading-text="正在加载项目配置..."
    >
      <ElTabs v-model="activeTab" class="px-4">
      <ElTabPane label="基础信息" name="basic">
        <Form class="mt-2" />
      </ElTabPane>
      <ElTabPane label="里程碑配置" name="milestone">
        <div class="mt-4">
          <div class="mb-2 flex items-center gap-2">
            <div class="text-sm font-medium">里程碑配置</div>
            <ElSwitch
              v-model="enableMilestone"
              inline-prompt
              active-text="开"
              inactive-text="关"
            />
          </div>
          <ElForm label-width="120px" v-if="enableMilestone">
            <ElFormItem label="QG1">
              <ElDatePicker
                v-model="milestoneForm.qg1_date"
                type="date"
                value-format="YYYY-MM-DD"
              />
            </ElFormItem>
            <ElFormItem label="QG2">
              <ElDatePicker
                v-model="milestoneForm.qg2_date"
                type="date"
                value-format="YYYY-MM-DD"
              />
            </ElFormItem>
            <ElFormItem label="QG3">
              <ElDatePicker
                v-model="milestoneForm.qg3_date"
                type="date"
                value-format="YYYY-MM-DD"
              />
            </ElFormItem>
            <ElFormItem label="QG4">
              <ElDatePicker
                v-model="milestoneForm.qg4_date"
                type="date"
                value-format="YYYY-MM-DD"
              />
            </ElFormItem>
            <ElFormItem label="QG5">
              <ElDatePicker
                v-model="milestoneForm.qg5_date"
                type="date"
                value-format="YYYY-MM-DD"
              />
            </ElFormItem>
            <ElFormItem label="QG6">
              <ElDatePicker
                v-model="milestoneForm.qg6_date"
                type="date"
                value-format="YYYY-MM-DD"
              />
            </ElFormItem>
            <ElFormItem label="QG7">
              <ElDatePicker
                v-model="milestoneForm.qg7_date"
                type="date"
                value-format="YYYY-MM-DD"
              />
            </ElFormItem>
            <ElFormItem label="QG8">
              <ElDatePicker
                v-model="milestoneForm.qg8_date"
                type="date"
                value-format="YYYY-MM-DD"
              />
            </ElFormItem>
          </ElForm>
        </div>
      </ElTabPane>
      <ElTabPane label="健康迭代配置" name="iteration">
        <div class="mt-4">
          <div class="mb-2 flex items-center gap-2">
            <div class="text-sm font-medium">健康迭代配置</div>
            <ElSwitch
              v-model="enableIteration"
              inline-prompt
              active-text="开"
              inactive-text="关"
            />
          </div>
          <ElForm label-width="120px" v-if="enableIteration">
            <ElFormItem label="中台配置ID">
              <ElInput
                v-model="iterationConfig.design_id"
                placeholder="请输入迭代中台配置 ID"
              />
            </ElFormItem>
            <ElFormItem label="迭代责任团队">
              <div class="mb-2 flex gap-2">
                <ElInput
                  v-model="newSubTeam"
                  placeholder="输入团队名称"
                  @keyup.enter="
                    () => {
                      if (newSubTeam) {
                        iterationConfig.sub_teams.push(newSubTeam);
                        newSubTeam = '';
                      }
                    }
                  "
                />
                <ElButton
                  @click="
                    () => {
                      if (newSubTeam) {
                        iterationConfig.sub_teams.push(newSubTeam);
                        newSubTeam = '';
                      }
                    }
                  "
                >
                  添加
                </ElButton>
              </div>
              <div class="flex flex-wrap gap-2">
                <div
                  v-for="(team, index) in iterationConfig.sub_teams"
                  :key="index"
                  class="flex items-center gap-1 rounded bg-gray-100 px-2 py-1"
                >
                  <span>{{ team }}</span>
                  <ElButton
                    link
                    type="danger"
                    @click="iterationConfig.sub_teams.splice(index, 1)"
                  >
                    删除
                  </ElButton>
                </div>
              </div>
            </ElFormItem>
          </ElForm>
        </div>
      </ElTabPane>
      <ElTabPane label="代码质量配置" name="quality">
        <div class="mt-4">
          <div class="mb-2 flex items-center gap-2">
            <div class="text-sm font-medium">代码质量模块配置</div>
            <ElSwitch
              v-model="enableQuality"
              inline-prompt
              active-text="开"
              inactive-text="关"
            />
          </div>
          <div v-if="enableQuality">
            <div class="mb-2">
              <ElButton
                type="primary"
                @click="
                  moduleRows.push({ oem_name: '', module: '', owner_ids: [] })
                "
              >
                新增模块
              </ElButton>
            </div>
            <ElTable :data="moduleRows">
              <ElTableColumn label="OEM名称" width="200">
                <template #default="{ row }">
                  <ElInput v-model="row.oem_name" placeholder="OEM名称" />
                </template>
              </ElTableColumn>
              <ElTableColumn label="模块名" width="200">
                <template #default="{ row }">
                  <ElInput v-model="row.module" placeholder="模块名" />
                </template>
              </ElTableColumn>
              <ElTableColumn label="责任人" width="200">
                <template #default="{ row }">
                  <UserSelector
                    v-model="row.owner_ids"
                    :multiple="true"
                    placeholder="请选择责任人"
                  />
                </template>
              </ElTableColumn>
              <ElTableColumn label="操作" width="120">
                <template #default="{ $index }">
                  <ElButton
                    type="danger"
                    link
                    @click="moduleRows.splice($index, 1)"
                  >
                    删除
                  </ElButton>
                </template>
              </ElTableColumn>
            </ElTable>
          </div>
        </div>
      </ElTabPane>
      <ElTabPane label="问题单配置" name="dts">
        <div class="mt-4">
          <div class="mb-2 flex items-center gap-2">
            <div class="text-sm font-medium">问题单统计配置</div>
            <ElSwitch
              v-model="enableDts"
              inline-prompt
              active-text="开"
              inactive-text="关"
            />
          </div>
          <ElForm label-width="120px" v-if="enableDts">
            <ElFormItem label="中台配置ID">
              <ElInput
                v-model="dtsConfig.ws_id"
                placeholder="请输入数据中台配置 ID"
              />
            </ElFormItem>
            <ElFormItem label="问题单责任团队">
              <div class="mb-2 flex gap-2">
                <ElInput
                  v-model="newDiTeam"
                  placeholder="输入团队名称"
                  @keyup.enter="
                    () => {
                      if (newDiTeam) {
                        dtsConfig.di_teams.push(newDiTeam);
                        newDiTeam = '';
                      }
                    }
                  "
                />
                <ElButton
                  @click="
                    () => {
                      if (newDiTeam) {
                        dtsConfig.di_teams.push(newDiTeam);
                        newDiTeam = '';
                      }
                    }
                  "
                >
                  添加
                </ElButton>
              </div>
              <div class="flex flex-wrap gap-2">
                <div
                  v-for="(team, index) in dtsConfig.di_teams"
                  :key="index"
                  class="flex items-center gap-1 rounded bg-gray-100 px-2 py-1"
                >
                  <span>{{ team }}</span>
                  <ElButton
                    link
                    type="danger"
                    @click="dtsConfig.di_teams.splice(index, 1)"
                  >
                    删除
                  </ElButton>
                </div>
              </div>
            </ElFormItem>
          </ElForm>
        </div>
      </ElTabPane>
      <ElTabPane label="典配配置" name="hardware">
        <div class="mt-4">
          <div class="mb-2 flex items-center gap-2">
            <div class="text-sm font-medium">典配配置</div>
            <ElSwitch
              v-model="enableHardwareConfig"
              inline-prompt
              active-text="开"
              inactive-text="关"
            />
          </div>
          <ElForm label-width="120px" v-if="enableHardwareConfig">
            <ElFormItem label="领域类型">
              <ElTag v-if="hardwareScenario === 'vehicle'" type="success">
                车控项目：配置点位硬件组合
              </ElTag>
              <ElTag v-else-if="hardwareScenario === 'cockpit'" type="warning">
                座舱项目：配置 CDC 平台 + 智慧屏版本
              </ElTag>
              <span v-else class="text-muted-foreground text-sm">
                当前项目领域不是车控/座舱，请先在基础信息里填写正确领域。
              </span>
            </ElFormItem>
            <ElFormItem v-if="hardwareScenario === 'vehicle'" label="VIU 平台">
              <ElSelect
                v-model="viuPlatformId"
                placeholder="选择 VIU 平台"
                clearable
                class="w-full"
              >
                <ElOption
                  v-for="platform in viuPlatforms"
                  :key="platform.id"
                  :label="platform.name"
                  :value="platform.id"
                />
              </ElSelect>
            </ElFormItem>
            <ElFormItem
              :label="
                hardwareScenario === 'cockpit' ? '配套版本配置' : '阶段配置'
              "
            >
              <div class="w-full">
                <div v-if="hardwareScenario === 'vehicle'" class="mb-3">
                  <ElButton type="primary" @click="addPhase">新增阶段</ElButton>
                </div>
                <div
                  v-if="phaseConfigs.length === 0"
                  class="text-muted-foreground text-sm"
                >
                  {{
                    hardwareScenario === 'cockpit'
                      ? '暂无配套版本配置'
                      : '暂无阶段配置'
                  }}
                </div>
                <div
                  v-for="(phase, phaseIndex) in phaseConfigs"
                  :key="phase.id || phaseIndex"
                  class="mb-4 rounded border p-3"
                >
                  <div
                    v-if="hardwareScenario === 'vehicle'"
                    class="mb-2 flex items-center justify-between"
                  >
                    <div class="text-foreground text-sm font-medium">
                      阶段 {{ phaseIndex + 1 }}
                    </div>
                    <ElButton
                      type="danger"
                      link
                      size="small"
                      @click="removePhase(phaseIndex)"
                    >
                      删除阶段
                    </ElButton>
                  </div>
                  <div
                    v-if="hardwareScenario === 'vehicle'"
                    class="mb-3 grid grid-cols-1 gap-3 md:grid-cols-2"
                  >
                    <ElInput
                      v-model="phase.stage_name"
                      placeholder="阶段名称，如：SOP"
                    />
                    <ElDatePicker
                      v-model="phase.stage_range"
                      type="daterange"
                      value-format="YYYY-MM-DD"
                      start-placeholder="开始日期"
                      end-placeholder="结束日期"
                    />
                  </div>

                  <div v-if="hardwareScenario === 'vehicle'">
                    <ElTable :data="phase.vehicle_hardware" size="small">
                      <ElTableColumn label="硬件点位" min-width="180">
                        <template #default="{ row }">
                          <ElSelect
                            v-model="row.point"
                            placeholder="选择点位"
                            clearable
                            class="w-full"
                          >
                            <ElOption
                              v-for="point in hardwarePoints"
                              :key="point.code"
                              :label="point.code"
                              :value="point.code"
                            />
                          </ElSelect>
                        </template>
                      </ElTableColumn>
                      <ElTableColumn label="板子型号" min-width="220">
                        <template #default="{ row }">
                          <ElSelect
                            v-model="row.board"
                            placeholder="选择板子"
                            clearable
                            class="w-full"
                          >
                            <ElOption
                              v-for="board in getBoardsByPoint(row.point)"
                              :key="board"
                              :label="board"
                              :value="board"
                            />
                          </ElSelect>
                        </template>
                      </ElTableColumn>
                      <ElTableColumn label="BOMID" min-width="200">
                        <template #default="{ row }">
                          <ElInput
                            v-model="row.bomid"
                            placeholder="请输入 BOMID"
                          />
                        </template>
                      </ElTableColumn>
                      <ElTableColumn label="操作" width="120">
                        <template #default="{ $index }">
                          <ElButton
                            type="danger"
                            link
                            @click="removeVehicleHardwareRow(phase, $index)"
                          >
                            删除
                          </ElButton>
                        </template>
                      </ElTableColumn>
                    </ElTable>
                    <div class="mt-2">
                      <ElButton
                        link
                        type="primary"
                        @click="addVehicleHardwareRow(phase)"
                      >
                        新增硬件组合
                      </ElButton>
                    </div>
                  </div>

                  <div
                    v-else-if="hardwareScenario === 'cockpit'"
                    class="grid grid-cols-1 gap-3 md:grid-cols-2"
                  >
                    <ElSelect
                      v-model="phase.cdc_platform_id"
                      placeholder="选择 CDC 平台"
                      clearable
                    >
                      <ElOption
                        v-for="platform in cdcPlatforms"
                        :key="platform.id"
                        :label="platform.name"
                        :value="platform.id"
                      />
                    </ElSelect>
                    <ElSelect
                      v-model="phase.smart_screen_version_id"
                      placeholder="选择智慧屏版本"
                      clearable
                    >
                      <ElOption
                        v-for="version in smartScreenVersions"
                        :key="version.id"
                        :label="version.name"
                        :value="version.id"
                      />
                    </ElSelect>
                  </div>
                </div>
              </div>
            </ElFormItem>
          </ElForm>
        </div>
      </ElTabPane>
      </ElTabs>
    </div>
  </Drawer>
</template>
