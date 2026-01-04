<script lang="ts" setup>
import type { ProjectCreatePayload } from '#/api/project-manager/project';

import { reactive, ref } from 'vue';

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
  ElStep,
  ElSteps,
  ElSwitch,
  ElTable,
  ElTableColumn,
} from 'element-plus';

import { configModuleApi } from '#/api/project-manager/code_quality';
import { createIterationApi } from '#/api/project-manager/iteration';
import { updateMilestoneApi } from '#/api/project-manager/milestone';
import { createProjectApi } from '#/api/project-manager/project';

defineOptions({ name: 'ProjectCreateWizard' });

const emit = defineEmits<{ (e: 'created'): void }>();
const modelValue = defineModel<boolean>({ default: false });
const activeStep = ref(0);

const baseForm = reactive<ProjectCreatePayload>({
  name: '',
  domain: '',
  type: '',
  code: '',
  manager_ids: [],
  is_closed: false,
  repo_url: '',
  remark: '',
  enable_milestone: true,
  enable_iteration: true,
  enable_quality: true,
});

const milestoneForm = reactive({
  qg1_date: '',
  qg2_date: '',
  qg3_date: '',
  qg4_date: '',
  qg5_date: '',
  qg6_date: '',
  qg7_date: '',
  qg8_date: '',
});

const iterationForm = reactive({
  name: '',
  code: '',
  start_date: '',
  end_date: '',
  is_current: true,
  is_healthy: true,
});

type ModuleRow = { name: string; owner_id?: string };
const moduleRows = ref<ModuleRow[]>([]);

const submitting = ref(false);
const createdProjectId = ref<string>('');

function resetAll() {
  activeStep.value = 0;
  Object.assign(baseForm, {
    name: '',
    domain: '',
    type: '',
    code: '',
    manager_ids: [],
    is_closed: false,
    repo_url: '',
    remark: '',
    enable_milestone: true,
    enable_iteration: true,
    enable_quality: true,
  });
  Object.keys(milestoneForm).forEach(
    (k) => (milestoneForm[k as keyof typeof milestoneForm] = ''),
  );
  Object.assign(iterationForm, {
    name: '',
    code: '',
    start_date: '',
    end_date: '',
    is_current: true,
    is_healthy: true,
  });
  moduleRows.value = [];
  createdProjectId.value = '';
}

async function submitAll() {
  if (submitting.value) return;
  submitting.value = true;
  try {
    const resp = await createProjectApi(baseForm);
    const project = resp.data as any;
    createdProjectId.value = project.id;
    if (baseForm.enable_milestone) {
      await updateMilestoneApi(project.id, milestoneForm);
    }
    if (
      baseForm.enable_iteration &&
      iterationForm.name &&
      iterationForm.code &&
      iterationForm.start_date &&
      iterationForm.end_date
    ) {
      await createIterationApi({
        project_id: project.id,
        name: iterationForm.name,
        code: iterationForm.code,
        start_date: iterationForm.start_date,
        end_date: iterationForm.end_date,
        is_current: iterationForm.is_current,
        is_healthy: iterationForm.is_healthy,
      });
    }
    if (baseForm.enable_quality && moduleRows.value.length > 0) {
      for (const row of moduleRows.value) {
        await configModuleApi({
          project_id: project.id,
          name: row.name,
          owner_id: row.owner_id,
        });
      }
    }
    ElMessage.success('创建成功');
    emit('created');
    modelValue.value = false;
    resetAll();
  } finally {
    submitting.value = false;
  }
}

function addModuleRow() {
  moduleRows.value.push({ name: '', owner_id: '' });
}

function removeModuleRow(index: number) {
  moduleRows.value.splice(index, 1);
}
</script>

<template>
  <ElDialog v-model="modelValue" title="新增项目" fullscreen destroy-on-close>
    <div class="mb-4">
      <ElSteps :active="activeStep" align-center>
        <ElStep title="基本信息" />
        <ElStep title="里程碑配置" />
        <ElStep title="健康迭代配置" />
        <ElStep title="代码质量配置" />
      </ElSteps>
    </div>

    <div v-show="activeStep === 0">
      <ElForm label-width="120px">
        <ElFormItem label="项目名">
          <ElInput v-model="baseForm.name" />
        </ElFormItem>
        <ElFormItem label="项目领域">
          <ElInput v-model="baseForm.domain" />
        </ElFormItem>
        <ElFormItem label="项目类型">
          <ElInput v-model="baseForm.type" />
        </ElFormItem>
        <ElFormItem label="项目编码">
          <ElInput v-model="baseForm.code" />
        </ElFormItem>
        <ElFormItem label="项目经理ID">
          <ElSelect
            v-model="baseForm.manager_ids"
            multiple
            placeholder="输入或选择ID"
          >
            <ElOption
              v-for="id in baseForm.manager_ids"
              :key="id"
              :label="id"
              :value="id"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="是否结项">
          <ElSwitch v-model="baseForm.is_closed" />
        </ElFormItem>
        <ElFormItem label="制品仓号">
          <ElInput v-model="baseForm.repo_url" />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput type="textarea" v-model="baseForm.remark" />
        </ElFormItem>
        <ElFormItem label="统计里程碑">
          <ElSwitch v-model="baseForm.enable_milestone" />
        </ElFormItem>
        <ElFormItem label="统计迭代数据">
          <ElSwitch v-model="baseForm.enable_iteration" />
        </ElFormItem>
        <ElFormItem label="统计代码质量">
          <ElSwitch v-model="baseForm.enable_quality" />
        </ElFormItem>
      </ElForm>
    </div>

    <div v-show="activeStep === 1">
      <div class="mb-2">
        <ElSwitch v-model="baseForm.enable_milestone" />
        <span class="ml-2">开启里程碑统计</span>
      </div>
      <ElForm v-if="baseForm.enable_milestone" label-width="120px">
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

    <div v-show="activeStep === 2">
      <div class="mb-2">
        <ElSwitch v-model="baseForm.enable_iteration" />
        <span class="ml-2">开启健康迭代统计</span>
      </div>
      <ElForm v-if="baseForm.enable_iteration" label-width="120px">
        <ElFormItem label="迭代名称">
          <ElInput v-model="iterationForm.name" />
        </ElFormItem>
        <ElFormItem label="迭代编号">
          <ElInput v-model="iterationForm.code" />
        </ElFormItem>
        <ElFormItem label="开始时间">
          <ElDatePicker
            v-model="iterationForm.start_date"
            type="date"
            value-format="YYYY-MM-DD"
          />
        </ElFormItem>
        <ElFormItem label="结束时间">
          <ElDatePicker
            v-model="iterationForm.end_date"
            type="date"
            value-format="YYYY-MM-DD"
          />
        </ElFormItem>
        <ElFormItem label="是否当前迭代">
          <ElSwitch v-model="iterationForm.is_current" />
        </ElFormItem>
        <ElFormItem label="是否健康">
          <ElSwitch v-model="iterationForm.is_healthy" />
        </ElFormItem>
      </ElForm>
    </div>

    <div v-show="activeStep === 3">
      <div class="mb-2">
        <ElSwitch v-model="baseForm.enable_quality" />
        <span class="ml-2">开启代码质量统计</span>
      </div>
      <div v-if="baseForm.enable_quality">
        <div class="mb-2">
          <ElButton type="primary" @click="addModuleRow">新增模块</ElButton>
        </div>
        <ElTable :data="moduleRows">
          <ElTableColumn label="模块名">
            <template #default="{ row }">
              <ElInput v-model="row.name" placeholder="模块名" />
            </template>
          </ElTableColumn>
          <ElTableColumn label="责任人ID">
            <template #default="{ row }">
              <ElInput v-model="row.owner_id" placeholder="责任人ID" />
            </template>
          </ElTableColumn>
          <ElTableColumn label="操作" width="120">
            <template #default="{ $index }">
              <ElButton type="danger" link @click="removeModuleRow($index)">
                删除
              </ElButton>
            </template>
          </ElTableColumn>
        </ElTable>
      </div>
    </div>

    <template #footer>
      <div class="flex w-full justify-between">
        <div>
          <ElButton @click="modelValue = false">取消</ElButton>
        </div>
        <div>
          <ElButton :disabled="activeStep === 0" @click="activeStep--">
            上一步
          </ElButton>
          <ElButton v-if="activeStep < 3" type="primary" @click="activeStep++">
            下一步
          </ElButton>
          <ElButton
            v-else
            type="success"
            :loading="submitting"
            @click="submitAll"
          >
            完成
          </ElButton>
        </div>
      </div>
    </template>
  </ElDialog>
</template>
