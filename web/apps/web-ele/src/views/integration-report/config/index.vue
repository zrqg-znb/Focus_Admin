<script setup lang="ts">
import type { ProjectConfigManageRow, ProjectConfigUpsertIn } from '#/api/integration-report';
import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';
import {
  ElButton,
  ElDatePicker,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElPopconfirm,
  ElSelect,
  ElSkeleton,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import {
  initIntegrationConfigsApi,
  listIntegrationConfigsApi,
  mockCollectIntegrationApi,
  mockSendIntegrationEmailsApi,
  upsertIntegrationConfigApi,
} from '#/api/integration-report';
import { listProjectsApi } from '#/api/project-manager/project';

defineOptions({ name: 'DailyIntegrationConfig' });

const loading = ref(false);
const savingId = ref<string | null>(null);
const rows = ref<ProjectConfigManageRow[]>([]);
const keyword = ref('');

const recordDate = ref<Date>(new Date());

const dialogVisible = ref(false);
const dialogMode = ref<'create' | 'edit'>('create');
const dialogSaving = ref(false);

const allProjects = ref<Array<{ id: string; name: string; domain: string; type: string }>>([]);
const formProjectId = ref<string>('');
const form = ref<ProjectConfigUpsertIn>({
  enabled: true,
  code_check_task_id: '',
  bin_scope_task_id: '',
  build_check_task_id: '',
  compile_check_task_id: '',
  dt_project_id: '',
});

const filteredRows = computed(() => {
  const k = keyword.value.trim().toLowerCase();
  if (!k) return rows.value;
  return rows.value.filter((r) => r.project_name.toLowerCase().includes(k));
});

const configuredProjectIds = computed(() => new Set(rows.value.map((r) => r.project_id)));

function dateStr() {
  const d = recordDate.value;
  return d.toISOString().slice(0, 10);
}

async function ensureProjectsLoaded() {
  if (allProjects.value.length) return;
  try {
    const resp = await listProjectsApi({ page: 1, pageSize: 1000, is_closed: false });
    allProjects.value = (resp.items || []).map((p) => ({
      id: p.id,
      name: p.name,
      domain: p.domain,
      type: p.type,
    }));
  } catch (e) {
    allProjects.value = [];
    ElMessage.error('获取项目列表失败，请检查权限或接口');
  }
}

async function reload() {
  try {
    loading.value = true;
    rows.value = await listIntegrationConfigsApi();
  } finally {
    loading.value = false;
  }
}

async function initRows() {
  try {
    loading.value = true;
    const created = await initIntegrationConfigsApi();
    ElMessage.success(`初始化完成，新增 ${created} 条配置`);
    await reload();
  } finally {
    loading.value = false;
  }
}

function payloadOf(r: ProjectConfigManageRow): ProjectConfigUpsertIn {
  return {
    enabled: r.enabled,
    code_check_task_id: r.code_check_task_id || '',
    bin_scope_task_id: r.bin_scope_task_id || '',
    build_check_task_id: r.build_check_task_id || '',
    compile_check_task_id: r.compile_check_task_id || '',
    dt_project_id: r.dt_project_id || '',
  };
}

async function saveRow(r: ProjectConfigManageRow) {
  try {
    savingId.value = r.project_id;
    await upsertIntegrationConfigApi(r.project_id, payloadOf(r));
    ElMessage.success('保存成功');
  } finally {
    savingId.value = null;
  }
}

function openCreate() {
  dialogMode.value = 'create';
  formProjectId.value = '';
  form.value = {
    enabled: true,
    code_check_task_id: '',
    bin_scope_task_id: '',
    build_check_task_id: '',
    compile_check_task_id: '',
    dt_project_id: '',
  };
  dialogVisible.value = true;
  ensureProjectsLoaded();
}

function openEdit(r: ProjectConfigManageRow) {
  dialogMode.value = 'edit';
  formProjectId.value = r.project_id;
  form.value = payloadOf(r);
  dialogVisible.value = true;
  ensureProjectsLoaded();
}

function isConfigured(projectId: string) {
  return configuredProjectIds.value.has(projectId);
}

async function submitDialog() {
  if (!formProjectId.value) {
    ElMessage.warning('请选择项目');
    return;
  }
  try {
    dialogSaving.value = true;
    await upsertIntegrationConfigApi(formProjectId.value, form.value);
    ElMessage.success(dialogMode.value === 'create' ? '创建成功' : '更新成功');
    dialogVisible.value = false;
    await reload();
  } finally {
    dialogSaving.value = false;
  }
}

async function mockCollect() {
  try {
    loading.value = true;
    await mockCollectIntegrationApi(dateStr());
    ElMessage.success('Mock 采集完成');
    await reload();
  } finally {
    loading.value = false;
  }
}

async function mockSendEmails() {
  try {
    loading.value = true;
    const sent = await mockSendIntegrationEmailsApi(dateStr());
    ElMessage.success(`Mock 邮件发送完成：${sent} 封`);
  } finally {
    loading.value = false;
  }
}

function idTag(id: string) {
  if (!id) return '未配置';
  return id.length > 14 ? `${id.slice(0, 6)}...${id.slice(-6)}` : id;
}

onMounted(() => {
  reload();
});
</script>

<template>
  <Page auto-content-height>
    <div class="p-4 space-y-4">
      <div class="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-2">
            <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-gray-50 border border-gray-200 dark:bg-gray-900/30 dark:border-gray-800">
              <IconifyIcon icon="lucide:settings-2" class="text-xl text-gray-700 dark:text-gray-200" />
            </div>
            <div>
              <div class="text-base font-bold text-gray-900 dark:text-white">每日集成报告 · 配置维护</div>
              <div class="text-xs text-gray-400">维护各项目 task_id，并支持一键 Mock</div>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <ElInput v-model="keyword" placeholder="搜索项目名" clearable size="small" style="width: 220px" />
            <ElDatePicker v-model="recordDate" type="date" size="small" />

            <ElButton size="small" plain type="primary" :loading="loading" @click="openCreate">
              <template #icon><IconifyIcon icon="lucide:plus" /></template>
              新建项目配置
            </ElButton>

            <ElPopconfirm title="将为所有项目初始化一行配置，继续？" @confirm="initRows">
              <template #reference>
                <ElButton size="small" plain :loading="loading">
                  <template #icon><IconifyIcon icon="lucide:wand-2" /></template>
                  初始化配置行
                </ElButton>
              </template>
            </ElPopconfirm>

            <ElButton size="small" plain type="primary" :loading="loading" @click="mockCollect">
              <template #icon><IconifyIcon icon="lucide:database" /></template>
              一键 Mock 采集
            </ElButton>

            <ElButton size="small" plain type="success" :loading="loading" @click="mockSendEmails">
              <template #icon><IconifyIcon icon="lucide:mail" /></template>
              一键 Mock 发邮件
            </ElButton>

            <ElButton size="small" plain :loading="loading" @click="reload">
              <template #icon><IconifyIcon icon="lucide:refresh-cw" /></template>
              刷新
            </ElButton>
          </div>
        </div>
      </div>

      <ElSkeleton :loading="loading" animated>
        <template #default>
          <div class="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-[#151515]">
            <div class="mb-3 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="h-4 w-1 rounded-full bg-indigo-500" />
                <span class="font-bold text-gray-900 dark:text-white">项目配置表</span>
              </div>
              <ElTag type="info" size="small">Mock 日期：{{ dateStr() }}</ElTag>
            </div>

            <ElTable :data="filteredRows" size="small" stripe height="calc(100vh - 300px)">
              <ElTableColumn prop="project_name" label="项目" min-width="180" fixed="left" />
              <ElTableColumn label="启用" width="90">
                <template #default="{ row }">
                  <ElSwitch v-model="row.enabled" @change="() => saveRow(row)" />
                </template>
              </ElTableColumn>

              <ElTableColumn label="CodeCheck task_id" min-width="220">
                <template #default="{ row }">
                  <span class="text-gray-700 dark:text-gray-200">{{ idTag(row.code_check_task_id) }}</span>
                </template>
              </ElTableColumn>
              <ElTableColumn label="BinScope task_id" min-width="220">
                <template #default="{ row }">
                  <span class="text-gray-700 dark:text-gray-200">{{ idTag(row.bin_scope_task_id) }}</span>
                </template>
              </ElTableColumn>
              <ElTableColumn label="BuildCheck task_id" min-width="220">
                <template #default="{ row }">
                  <span class="text-gray-700 dark:text-gray-200">{{ idTag(row.build_check_task_id) }}</span>
                </template>
              </ElTableColumn>
              <ElTableColumn label="CompileCheck task_id" min-width="220">
                <template #default="{ row }">
                  <span class="text-gray-700 dark:text-gray-200">{{ idTag(row.compile_check_task_id) }}</span>
                </template>
              </ElTableColumn>
              <ElTableColumn label="DT project_id" min-width="220">
                <template #default="{ row }">
                  <span class="text-gray-700 dark:text-gray-200">{{ idTag(row.dt_project_id) }}</span>
                </template>
              </ElTableColumn>

              <ElTableColumn label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <ElButton
                    size="small"
                    type="primary"
                    plain
                    @click="openEdit(row)"
                  >
                    编辑
                  </ElButton>
                </template>
              </ElTableColumn>
            </ElTable>
          </div>
        </template>
      </ElSkeleton>
    </div>

    <ElDialog v-model="dialogVisible" :title="dialogMode === 'create' ? '新建项目配置' : '编辑项目配置'" width="640">
      <ElForm label-width="140px">
        <ElFormItem label="关联项目" required>
          <ElSelect
            v-model="formProjectId"
            filterable
            placeholder="请选择项目"
            style="width: 100%"
            :disabled="dialogMode === 'edit'"
          >
            <ElOption
              v-for="p in allProjects"
              :key="p.id"
              :disabled="dialogMode === 'create' && isConfigured(p.id)"
              :label="`${p.name}（${p.domain || '-'} / ${p.type || '-'}）${dialogMode === 'create' && isConfigured(p.id) ? '（已配置）' : ''}`"
              :value="p.id"
            />
          </ElSelect>
        </ElFormItem>

        <ElFormItem label="启用">
          <ElSwitch v-model="form.enabled" />
        </ElFormItem>

        <ElFormItem label="code_check_task_id">
          <ElInput v-model="form.code_check_task_id" placeholder="code_check_task_id" />
        </ElFormItem>
        <ElFormItem label="bin_scope_task_id">
          <ElInput v-model="form.bin_scope_task_id" placeholder="bin_scope_task_id" />
        </ElFormItem>
        <ElFormItem label="build_check_task_id">
          <ElInput v-model="form.build_check_task_id" placeholder="build_check_task_id" />
        </ElFormItem>
        <ElFormItem label="compile_check_task_id">
          <ElInput v-model="form.compile_check_task_id" placeholder="compile_check_task_id" />
        </ElFormItem>
        <ElFormItem label="dt_project_id">
          <ElInput v-model="form.dt_project_id" placeholder="dt_project_id" />
        </ElFormItem>
      </ElForm>

      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="dialogVisible = false">取消</ElButton>
          <ElButton type="primary" :loading="dialogSaving" @click="submitDialog">保存</ElButton>
        </div>
      </template>
    </ElDialog>
  </Page>
</template>
