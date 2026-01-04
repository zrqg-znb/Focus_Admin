<script lang="ts" setup>
import { computed, ref } from 'vue';
import { ElButton, ElDialog, ElForm, ElFormItem, ElInput, ElDatePicker, ElMessage, ElSwitch, ElTable, ElTableColumn, ElScrollbar } from 'element-plus';
import { useVbenForm, z } from '#/adapter/form';

import { createProjectApi } from '#/api/project-manager/project';
import { updateMilestoneApi } from '#/api/project-manager/milestone';
import { createIterationApi } from '#/api/project-manager/iteration';
import { configModuleApi } from '#/api/project-manager/code_quality';

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
const iterationForm = ref({
  name: '',
  code: '',
  start_date: '',
  end_date: '',
  is_current: true,
  is_healthy: true,
});

// 代码质量
const enableQuality = ref(false);
type ModuleRow = { name: string; owner_id?: string };
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
      iterationForm.value.name &&
      iterationForm.value.code &&
      iterationForm.value.start_date &&
      iterationForm.value.end_date
    );
  }
  if (currentStep.value === 3 && enableQuality.value) {
    return moduleRows.value.every((m) => m.name && m.name.trim().length > 0);
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
  iterationForm.value = {
    name: '',
    code: '',
    start_date: '',
    end_date: '',
    is_current: true,
    is_healthy: true,
  };
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
    };
    const project = await createProjectApi(payload);
    const projectId = project.id;

    if (enableMilestone.value) {
      await updateMilestoneApi(projectId, milestoneForm.value);
    }
    if (enableIteration.value) {
      await createIterationApi({
        project_id: projectId,
        name: iterationForm.value.name,
        code: iterationForm.value.code,
        start_date: iterationForm.value.start_date,
        end_date: iterationForm.value.end_date,
        is_current: iterationForm.value.is_current,
        is_healthy: iterationForm.value.is_healthy,
      });
    }
    if (enableQuality.value && moduleRows.value.length) {
      for (const row of moduleRows.value) {
        await configModuleApi({
          project_id: projectId,
          name: row.name,
          owner_id: row.owner_id,
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
      <div v-show="currentStep === 1" class="h-full overflow-hidden p-6">
        <div class="w-[700px]">
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
      <!-- 步骤3：迭代 -->
      <div v-show="currentStep === 2" class="h-full overflow-hidden p-6">
        <div class="w-[700px]">
          <ElForm label-width="120px">
            <ElFormItem label="开启健康迭代统计">
              <ElSwitch v-model="enableIteration" />
            </ElFormItem>
            <div v-if="enableIteration">
              <ElFormItem label="迭代名称"><ElInput v-model="iterationForm.name" /></ElFormItem>
              <ElFormItem label="迭代编号"><ElInput v-model="iterationForm.code" /></ElFormItem>
              <ElFormItem label="开始时间"><ElDatePicker v-model="iterationForm.start_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
              <ElFormItem label="结束时间"><ElDatePicker v-model="iterationForm.end_date" type="date" value-format="YYYY-MM-DD" /></ElFormItem>
            </div>
          </ElForm>
        </div>
      </div>
      <!-- 步骤4：代码质量 -->
      <div v-show="currentStep === 3" class="h-full overflow-hidden p-6">
        <div class="w-[900px]">
          <ElForm label-width="120px">
            <ElFormItem label="开启代码质量统计">
              <ElSwitch v-model="enableQuality" />
            </ElFormItem>
          </ElForm>
          <div v-if="enableQuality">
            <div class="mb-2">
              <ElButton type="primary" @click="moduleRows.push({ name: '', owner_id: '' })">新增模块</ElButton>
            </div>
            <ElTable :data="moduleRows">
              <ElTableColumn label="模块名" width="300">
                <template #default="{ row }">
                  <ElInput v-model="row.name" placeholder="模块名" />
                </template>
              </ElTableColumn>
              <ElTableColumn label="责任人ID" width="300">
                <template #default="{ row }">
                  <ElInput v-model="row.owner_id" placeholder="责任人ID" />
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
  </ElDialog>
</template>
