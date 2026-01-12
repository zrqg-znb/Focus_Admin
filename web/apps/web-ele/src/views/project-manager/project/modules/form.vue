<script lang="ts" setup>
import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import {
  ElButton,
  ElDatePicker,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElSwitch,
  ElTable,
  ElTableColumn,
} from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  configModuleApi,
  getProjectQualityDetailsApi,
} from '#/api/project-manager/code_quality';
import {
  getMilestoneBoardApi,
  updateMilestoneApi,
} from '#/api/project-manager/milestone';
import {
  createProjectApi,
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
  schema: getProjectFormSchema(),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-1 gap-x-4',
});

const [Drawer, drawerApi] = useVbenDrawer({
  onConfirm: onSubmit,
  async onOpenChange(isOpen) {
    if (isOpen) {
      const data = drawerApi.getData<any>();
      if (data) {
        formData.value = data;
        const normalized = {
          ...formData.value,
          manager_ids: Array.isArray(formData.value.managers_info)
            ? formData.value.managers_info.map((m: any) => m.id)
            : [],
        };
        // 初始化开关状态
        enableMilestone.value = !!data.enable_milestone;
        enableIteration.value = !!data.enable_iteration;
        enableQuality.value = !!data.enable_quality;
        enableDts.value = !!data.enable_dts;

        // 回填配置项（无条件回填，确保开关开启时有数据）
        iterationConfig.value.design_id = data.design_id || '';
        iterationConfig.value.sub_teams = Array.isArray(data.sub_teams)
          ? data.sub_teams
          : [];

        dtsConfig.value.ws_id = data.ws_id || '';
        dtsConfig.value.di_teams = Array.isArray(data.di_teams)
          ? data.di_teams
          : [];

        // 回填里程碑数据
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

        // 回填代码质量模块
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
      } else {
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
      }
    }
  },
});

const getDrawerTitle = computed(() =>
  formData.value?.id ? '编辑项目' : '新增项目',
);

async function onSubmit() {
  const { valid } = await formApi.validate();
  if (valid) {
    drawerApi.lock();
    const data = await formApi.getValues<any>();
    try {
      // 前端校验重复模块
      if (data.enable_quality && moduleRows.value.length > 0) {
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
        const project = await createProjectApi(data);
        const projectId = project.id;
        if (data.enable_milestone) {
          await updateMilestoneApi(projectId, milestoneForm.value);
        }
        if (data.enable_iteration) {
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
  <Drawer class="w-full max-w-[700px]" :title="getDrawerTitle">
    <Form class="mx-4" />
    <div class="mx-4 mt-4">
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
    <div class="mx-4 mt-6">
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
              <span
                class="cursor-pointer font-bold text-red-500"
                @click="iterationConfig.sub_teams.splice(index, 1)"
                >×</span>
            </div>
          </div>
        </ElFormItem>
      </ElForm>
    </div>
    <div class="mx-4 mt-6">
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
    <div class="mx-4 mt-6">
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
              <span
                class="cursor-pointer font-bold text-red-500"
                @click="dtsConfig.di_teams.splice(index, 1)"
                >×</span>
            </div>
          </div>
        </ElFormItem>
      </ElForm>
    </div>
  </Drawer>
</template>
