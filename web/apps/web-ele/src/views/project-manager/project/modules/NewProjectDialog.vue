<script lang="ts" setup>
import { computed, ref } from 'vue';
import { ElButton, ElDialog, ElForm, ElFormItem, ElInput, ElDatePicker, ElMessage, ElSwitch, ElTable, ElTableColumn, ElScrollbar } from 'element-plus';
import { useVbenForm, z } from '#/adapter/form';

import { createProjectApi } from '#/api/project-manager/project';
import { updateMilestoneApi } from '#/api/project-manager/milestone';
import { createIterationApi } from '#/api/project-manager/iteration';
import { configModuleApi } from '#/api/project-manager/code_quality';
import UserSelector from '#/components/zq-form/user-selector/user-selector.vue';

import { getProjectFormSchema } from '../data';

interface Props {
  modelValue: boolean;
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
type ModuleRow = { oem_name: string; module: string; owner_ids: string[] };
const moduleRows = ref<ModuleRow[]>([]);

const steps = [
  { title: '基本信息', index: 1 },
  { title: '里程碑配置', index: 2 },
  { title: '健康迭代配置', index: 3 },
  { title: '代码质量配置', index: 4 },
];

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
  newSubTeam.value = '';
  moduleRows.value = [];
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
    const payload = {
      ...baseData,
      enable_milestone: enableMilestone.value,
      enable_iteration: enableIteration.value,
      enable_quality: enableQuality.value,
      design_id: enableIteration.value ? iterationConfig.value.design_id : undefined,
      sub_teams: enableIteration.value ? iterationConfig.value.sub_teams : undefined,
    };
    const project = await createProjectApi(payload);
    const projectId = project.id;

    if (enableMilestone.value) {
      // 过滤空字符串日期，只传递有效值
      const milestonePayload = Object.fromEntries(
        Object.entries(milestoneForm.value).filter(([_, v]) => v && v !== '')
      );
      await updateMilestoneApi(projectId, milestonePayload);
    }
    // 迭代数据由后端根据 design_id 和 sub_teams 自动同步，无需前端调用 createIterationApi

    if (enableQuality.value && moduleRows.value.length) {
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
      <div class="bg-background-deep mb-4 flex h-14 w-full items-center justify-between rounded-[8px] px-6 shadow-sm">
        <div class="flex items-center gap-3">
          <span class="text-foreground/70 text-base font-medium">新增项目</span>
        </div>
        <div class="absolute left-1/2 flex -translate-x-1/2 items-center">
          <template v-for="(step, index) in steps" :key="index">
            <div class="flex cursor-pointer items-center px-4 py-1" @click="index < currentStep ? (currentStep = index) : null">
              <div class="flex items-center justify-center rounded-full border px-3 py-1 text-sm transition-all"
                   :class="[
                     index === currentStep
                       ? 'border-primary text-primary bg-primary/10 font-medium'
                       : index < currentStep
                         ? 'border-primary/50 text-primary/80 bg-transparent'
                         : 'border-border text-muted-foreground bg-transparent',
                   ]">
                <span class="mr-2 flex h-5 w-5 items-center justify-center rounded-full text-xs"
                      :class="index === currentStep ? 'bg-primary text-white' : index < currentStep ? 'bg-primary/80 text-white' : 'bg-muted text-muted-foreground'">
                  {{ step.index }}
                </span>
                {{ step.title }}
              </div>
            </div>
            <div v-if="index < steps.length - 1" class="bg-border h-[1px] w-8" :class="{ 'bg-primary/50': index < currentStep }"></div>
          </template>
        </div>
        <div class="flex items-center gap-3">
          <ElButton v-if="canGoPrev" @click="handlePrev">上一步</ElButton>
          <ElButton v-if="!isLastStep" type="primary" :disabled="!canGoNext" :loading="loading" @click="handleNext">下一步</ElButton>
          <ElButton v-if="isLastStep" type="primary" :loading="loading" @click="handleSave">完成</ElButton>
          <ElButton @click="handleClose">关闭</ElButton>
        </div>
      </div>
    </template>

    <div class="h-full overflow-hidden">
      <!-- 步骤1：基本信息 -->
      <div v-show="currentStep === 0" class="flex h-full items-center justify-center overflow-y-auto">
        <div class="align-self-center w-[700px] translate-y-[-20%]">
          <div class="border-border bg-card rounded-lg border p-8 shadow-sm">
            <BasicForm class="mx-4" />
          </div>
        </div>
      </div>
      <!-- 步骤2：里程碑 -->
      <div v-show="currentStep === 1" class="flex h-full items-center justify-center overflow-y-auto p-6">
        <div class="align-self-center w-[700px] translate-y-[-20%]">
          <div class="border-border bg-card rounded-lg border p-8 shadow-sm">
            <ElForm label-width="120px">
              <ElFormItem label="开启里程碑统计">
                <ElSwitch v-model="enableMilestone" />
              </ElFormItem>
              <div v-if="enableMilestone">
                <div class="text-sm font-medium mb-2">填写 QG 节点时间</div>
                <div class="grid grid-cols-2 gap-4">
                  <ElFormItem label="QG1"><ElDatePicker v-model="milestoneForm.qg1_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
                  <ElFormItem label="QG2"><ElDatePicker v-model="milestoneForm.qg2_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
                  <ElFormItem label="QG3"><ElDatePicker v-model="milestoneForm.qg3_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
                  <ElFormItem label="QG4"><ElDatePicker v-model="milestoneForm.qg4_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
                  <ElFormItem label="QG5"><ElDatePicker v-model="milestoneForm.qg5_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
                  <ElFormItem label="QG6"><ElDatePicker v-model="milestoneForm.qg6_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
                  <ElFormItem label="QG7"><ElDatePicker v-model="milestoneForm.qg7_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
                  <ElFormItem label="QG8"><ElDatePicker v-model="milestoneForm.qg8_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
                </div>
              </div>
            </ElForm>
          </div>
        </div>
      </div>
      <!-- 步骤3：迭代 -->
      <div v-show="currentStep === 2" class="flex h-full items-center justify-center overflow-y-auto p-6">
        <div class="align-self-center w-[700px] translate-y-[-20%]">
          <div class="border-border bg-card rounded-lg border p-8 shadow-sm">
            <ElForm label-width="120px">
              <ElFormItem label="开启健康迭代统计">
                <ElSwitch v-model="enableIteration" />
              </ElFormItem>
              <div v-if="enableIteration">
                <ElFormItem label="中台配置ID">
                  <ElInput v-model="iterationConfig.design_id" placeholder="请输入迭代中台配置 ID" />
                </ElFormItem>
                <ElFormItem label="迭代责任团队">
                  <div class="flex gap-2 mb-2">
                    <ElInput v-model="newSubTeam" placeholder="输入团队名称" @keyup.enter="() => { if(newSubTeam) { iterationConfig.sub_teams.push(newSubTeam); newSubTeam = ''; } }" />
                    <ElButton @click="() => { if(newSubTeam) { iterationConfig.sub_teams.push(newSubTeam); newSubTeam = ''; } }">添加</ElButton>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <div v-for="(team, index) in iterationConfig.sub_teams" :key="index" class="bg-gray-100 px-2 py-1 rounded flex items-center gap-1">
                      <span>{{ team }}</span>
                      <span class="cursor-pointer text-red-500 font-bold" @click="iterationConfig.sub_teams.splice(index, 1)">×</span>
                    </div>
                  </div>
                </ElFormItem>
              </div>
            </ElForm>
          </div>
        </div>
      </div>
      <!-- 步骤4：代码质量 -->
      <div v-show="currentStep === 3" class="flex h-full items-center justify-center overflow-y-auto p-6">
        <div class="align-self-center w-[900px] translate-y-[-20%]">
          <div class="border-border bg-card rounded-lg border p-8 shadow-sm">
            <ElForm label-width="120px">
              <ElFormItem label="开启代码质量统计">
                <ElSwitch v-model="enableQuality" />
              </ElFormItem>
            </ElForm>
            <div v-if="enableQuality">
              <div class="mb-2">
                <ElButton type="primary" @click="moduleRows.push({ oem_name: '', module: '', owner_ids: [] })">新增模块</ElButton>
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
                    <UserSelector v-model="row.owner_ids" :multiple="true" placeholder="请选择责任人" />
                  </template>
                </ElTableColumn>
                <ElTableColumn label="操作" width="120">
                  <template #default="{ $index }">
                    <ElButton type="danger" link @click="moduleRows.splice($index, 1)">删除</ElButton>
                  </template>
                </ElTableColumn>
              </ElTable>
            </div>
          </div>
        </div>
      </div>
    </div>
  </ElDialog>
</template>
