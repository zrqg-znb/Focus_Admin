<script lang="ts" setup>
import type {
  HardwarePoint,
  PlatformConfig,
} from '#/api/project-manager/hardware';

import { computed, ref, watch } from 'vue';

import {
  ElButton,
  ElDatePicker,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { configModuleApi } from '#/api/project-manager/code_quality';
import { listHardwareConfigOptionsApi } from '#/api/project-manager/hardware';
import { updateMilestoneApi } from '#/api/project-manager/milestone';
import { createProjectApi } from '#/api/project-manager/project';
import UserSelector from '#/components/zq-form/user-selector/user-selector.vue';

import { getProjectFormSchema } from '../data';

interface Props {
  modelValue?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
});

const emit = defineEmits<{
  (e: 'created'): void;
  (e: 'update:modelValue', value: boolean): void;
}>();

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});

const currentStep = ref(0);
const loading = ref(false);

const [BasicForm, basicFormApi] = useVbenForm({
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

// 里程碑
const enableMilestone = ref(false);
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

// 迭代
const enableIteration = ref(false);
const iterationConfig = ref({
  design_id: '',
  sub_teams: [] as string[],
});
// 临时输入框，用于添加团队
const newSubTeam = ref('');

// 代码质量
const enableQuality = ref(false);
type ModuleRow = { module: string; oem_name: string; owner_ids: string[] };
const moduleRows = ref<ModuleRow[]>([]);

// 问题单 DTS
const enableDts = ref(false);
const dtsConfig = ref({
  ws_id: '',
  di_teams: [] as string[],
});
const newDiTeam = ref('');

// 典配配置
const enableHardwareConfig = ref(false);
const projectDomain = ref('');
const hardwarePoints = ref<HardwarePoint[]>([]);
const viuPlatforms = ref<PlatformConfig[]>([]);
const cdcPlatforms = ref<PlatformConfig[]>([]);
const smartScreenVersions = ref<PlatformConfig[]>([]);
const viuPlatformId = ref('');
type PhaseConfigFormItem = {
  cdc_platform_id: string;
  smart_screen_version_id: string;
  stage_name: string;
  stage_range: string[];
  vehicle_hardware: Array<{ board: string; bomid: string; point: string }>;
};
const phaseConfigs = ref<PhaseConfigFormItem[]>([]);
const hardwareLoading = ref(false);

const steps = [
  { title: '基本信息', index: 1 },
  { title: '里程碑配置', index: 2 },
  { title: '健康迭代配置', index: 3 },
  { title: '代码质量配置', index: 4 },
  { title: '问题单配置', index: 5 },
  { title: '典配配置', index: 6 },
];

const hardwareStepIndex = steps.length - 1;

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
  const first = phaseConfigs.value[0];
  phaseConfigs.value = [
    {
      ...first,
      stage_name: cockpitStageName,
      stage_range: [],
    },
  ];
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

async function ensureHardwarePointsLoaded() {
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

watch(
  () => dialogVisible.value,
  (visible) => {
    if (visible) {
      ensureHardwarePointsLoaded();
    }
  },
);

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

const canGoNext = computed(() => {
  if (currentStep.value === 0) {
    return true;
  }
  if (currentStep.value === 2 && enableIteration.value) {
    return (
      iterationConfig.value.design_id &&
      iterationConfig.value.sub_teams.length > 0
    );
  }
  if (currentStep.value === 3 && enableQuality.value) {
    return moduleRows.value.every((row) => row.oem_name && row.module);
  }
  if (currentStep.value === 4 && enableDts.value) {
    return dtsConfig.value.ws_id && dtsConfig.value.di_teams.length > 0;
  }
  return true;
});

const isLastStep = computed(() => currentStep.value === steps.length - 1);
const canGoPrev = computed(() => currentStep.value > 0);

async function handleNext() {
  if (!canGoNext.value) {
    ElMessage.warning('请完成当前步骤的必填项');
    return;
  }
  currentStep.value++;
}

function handlePrev() {
  if (currentStep.value > 0) currentStep.value--;
}

function resetAll() {
  currentStep.value = 0;
  enableMilestone.value = false;
  enableIteration.value = false;
  enableQuality.value = false;
  enableDts.value = false;
  enableHardwareConfig.value = false;
  projectDomain.value = '';
  viuPlatformId.value = '';
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
  iterationConfig.value = {
    design_id: '',
    sub_teams: [],
  };
  dtsConfig.value = {
    ws_id: '',
    di_teams: [],
  };
  newSubTeam.value = '';
  newDiTeam.value = '';
  moduleRows.value = [];
  phaseConfigs.value = [];
}

async function handleSave() {
  const { valid } = await basicFormApi.validate();
  if (!valid) {
    ElMessage.warning('请先完成基本信息');
    currentStep.value = 0;
    return;
  }
  loading.value = true;
  try {
    const baseData = await basicFormApi.getValues<any>();
    projectDomain.value = baseData.domain || '';
    if (!isHardwareConfigValid(true)) {
      currentStep.value = hardwareStepIndex;
      return;
    }
    const payload = {
      ...baseData,
      enable_milestone: enableMilestone.value,
      enable_iteration: enableIteration.value,
      enable_quality: enableQuality.value,
      enable_dts: enableDts.value,
      enable_hardware_config: enableHardwareConfig.value,
      viu_platform_id:
        enableHardwareConfig.value && hardwareScenario.value === 'vehicle'
          ? viuPlatformId.value || undefined
          : undefined,
      phase_configs: enableHardwareConfig.value ? getPhasePayload() : undefined,
      design_id: enableIteration.value
        ? iterationConfig.value.design_id
        : undefined,
      sub_teams: enableIteration.value
        ? iterationConfig.value.sub_teams
        : undefined,
      ws_id: enableDts.value ? dtsConfig.value.ws_id : undefined,
      di_teams: enableDts.value ? dtsConfig.value.di_teams : undefined,
    };
    const project = await createProjectApi(payload);
    const projectId = project.id;

    if (enableMilestone.value) {
      // 过滤空字符串日期，只传递有效值
      const milestonePayload = Object.fromEntries(
        Object.entries(milestoneForm.value).filter(([_, v]) => v && v !== ''),
      );
      await updateMilestoneApi(projectId, milestonePayload);
    }
    // 迭代数据由后端根据 design_id 和 sub_teams 自动同步，无需前端调用 createIterationApi

    if (enableQuality.value && moduleRows.value.length > 0) {
      for (const row of moduleRows.value) {
        await configModuleApi({
          project_id: projectId,
          oem_name: row.oem_name,
          module: row.module,
          owner_ids: row.owner_ids,
        });
      }
    }
    ElMessage.success('创建成功');
    emit('created');
    handleClose();
  } finally {
    loading.value = false;
  }
}

function handleClose() {
  dialogVisible.value = false;
  resetAll();
  basicFormApi.resetForm();
}
</script>

<template>
  <ElDialog
    v-model="dialogVisible"
    :show-close="false"
    fullscreen
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    body-class="h-[calc(100vh-106px)]"
    header-class="!pb-0"
  >
    <template #header>
      <div
        class="bg-background-deep mb-4 w-full rounded-[8px] px-4 py-3 shadow-sm"
      >
        <div class="mb-3 flex items-center justify-between gap-3">
          <div class="flex min-w-0 items-center gap-3">
            <span class="text-foreground/80 font-medium">新增项目</span>
            <ElTag type="primary">
              步骤 {{ currentStep + 1 }} / {{ steps.length }}
            </ElTag>
            <span class="text-muted-foreground truncate text-sm">
              {{ steps[currentStep]?.title }}
            </span>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <ElButton v-if="canGoPrev" @click="handlePrev">上一步</ElButton>
            <ElButton
              v-if="!isLastStep"
              type="primary"
              :disabled="!canGoNext"
              :loading="loading"
              @click="handleNext"
            >
              下一步
            </ElButton>
            <ElButton
              v-if="isLastStep"
              type="primary"
              :loading="loading"
              @click="handleSave"
            >
              完成
            </ElButton>
            <ElButton @click="handleClose">关闭</ElButton>
          </div>
        </div>

        <div class="overflow-x-auto pb-1">
          <div class="flex justify-center">
            <div class="mx-auto flex w-max items-center gap-2 px-2">
              <template v-for="(step, index) in steps" :key="index">
                <button
                  type="button"
                  class="flex w-36 shrink-0 cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-left transition-all"
                  :class="[
                    index === currentStep
                      ? 'border-primary/40 bg-primary/10'
                      : index < currentStep
                        ? 'border-primary/30 bg-primary/5'
                        : 'border-border bg-background',
                  ]"
                  @click="index < currentStep ? (currentStep = index) : null"
                >
                  <div
                    class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-medium"
                    :class="[
                      index === currentStep
                        ? 'bg-primary text-white'
                        : index < currentStep
                          ? 'bg-primary/80 text-white'
                          : 'bg-muted text-muted-foreground',
                    ]"
                  >
                    {{ step.index }}
                  </div>
                  <div
                    class="text-xs leading-4"
                    :class="
                      index <= currentStep
                        ? 'text-foreground'
                        : 'text-muted-foreground'
                    "
                  >
                    {{ step.title }}
                  </div>
                </button>
                <div
                  v-if="index < steps.length - 1"
                  class="bg-border h-[1px] w-6 shrink-0"
                  :class="{ 'bg-primary/50': index < currentStep }"
                ></div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div class="h-full overflow-hidden">
      <!-- 步骤1：基本信息 -->
      <div
        v-show="currentStep === 0"
        class="flex h-full items-center justify-center overflow-y-auto"
      >
        <div class="align-self-center w-[700px] translate-y-[-20%]">
          <div class="border-border bg-card rounded-lg border p-8 shadow-sm">
            <BasicForm class="mx-4" />
          </div>
        </div>
      </div>
      <!-- 步骤2：里程碑 -->
      <div
        v-show="currentStep === 1"
        class="flex h-full items-center justify-center overflow-y-auto p-6"
      >
        <div class="align-self-center w-[700px] translate-y-[-20%]">
          <div class="border-border bg-card rounded-lg border p-8 shadow-sm">
            <ElForm label-width="120px">
              <ElFormItem label="开启里程碑统计">
                <ElSwitch v-model="enableMilestone" />
              </ElFormItem>
              <div v-if="enableMilestone">
                <div class="mb-2 text-sm font-medium">填写 QG 节点时间</div>
                <div class="grid grid-cols-2 gap-4">
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
                </div>
              </div>
            </ElForm>
          </div>
        </div>
      </div>
      <!-- 步骤3：迭代 -->
      <div
        v-show="currentStep === 2"
        class="flex h-full items-center justify-center overflow-y-auto p-6"
      >
        <div class="align-self-center w-[700px] translate-y-[-20%]">
          <div class="border-border bg-card rounded-lg border p-8 shadow-sm">
            <ElForm label-width="120px">
              <ElFormItem label="开启健康迭代统计">
                <ElSwitch v-model="enableIteration" />
              </ElFormItem>
              <div v-if="enableIteration">
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
              </div>
            </ElForm>
          </div>
        </div>
      </div>
      <!-- 步骤4：代码质量 -->
      <div
        v-show="currentStep === 3"
        class="flex h-full items-center justify-center overflow-y-auto p-6"
      >
        <div class="align-self-center w-[900px] translate-y-[-20%]">
          <div class="border-border bg-card rounded-lg border p-8 shadow-sm">
            <ElForm label-width="120px">
              <ElFormItem label="开启代码质量统计">
                <ElSwitch v-model="enableQuality" />
              </ElFormItem>
            </ElForm>
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
        </div>
      </div>
      <!-- 步骤5：问题单配置 -->
      <div
        v-show="currentStep === 4"
        class="flex h-full items-center justify-center overflow-y-auto p-6"
      >
        <div class="align-self-center w-[700px] translate-y-[-20%]">
          <div class="border-border bg-card rounded-lg border p-8 shadow-sm">
            <ElForm label-width="120px">
              <ElFormItem label="开启问题单统计">
                <ElSwitch v-model="enableDts" />
              </ElFormItem>
              <div v-if="enableDts">
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
              </div>
            </ElForm>
          </div>
        </div>
      </div>
      <!-- 步骤6：典配配置 -->
      <div
        v-show="currentStep === 5"
        class="flex h-full items-center justify-center overflow-y-auto p-6"
      >
        <div class="align-self-center w-[900px] translate-y-[-20%]">
          <div class="border-border bg-card rounded-lg border p-8 shadow-sm">
            <ElForm label-width="120px">
              <ElFormItem label="开启典配">
                <ElSwitch v-model="enableHardwareConfig" />
              </ElFormItem>
              <div v-if="enableHardwareConfig">
                <ElFormItem label="领域类型">
                  <ElTag v-if="hardwareScenario === 'vehicle'" type="success">
                    车控项目：配置点位硬件组合
                  </ElTag>
                  <ElTag
                    v-else-if="hardwareScenario === 'cockpit'"
                    type="warning"
                  >
                    座舱项目：配置 CDC 平台 + 智慧屏版本
                  </ElTag>
                  <span v-else class="text-muted-foreground text-sm">
                    当前项目领域不是车控/座舱，请先在基本信息里填写正确领域。
                  </span>
                </ElFormItem>
                <ElFormItem
                  v-if="hardwareScenario === 'vehicle'"
                  label="VIU 平台"
                >
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
                      <ElButton type="primary" @click="addPhase">
                        新增阶段
                      </ElButton>
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
                      :key="phaseIndex"
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
              </div>
            </ElForm>
          </div>
        </div>
      </div>
    </div>
  </ElDialog>
</template>
