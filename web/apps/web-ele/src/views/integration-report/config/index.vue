<script setup lang="ts">
import type { VxeGridProps } from '#/adapter/vxe-table';
import type {
  ProjectConfigManageRow,
  ProjectConfigUpsertIn,
} from '#/api/integration-report';

import { ref } from 'vue';

import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';
import { useVbenVxeGrid } from '@vben/plugins/vxe-table';

import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElPopconfirm,
  ElSelect,
  ElSwitch,
} from 'element-plus';

import {
  createIntegrationConfigApi,
  deleteIntegrationConfigApi,
  initIntegrationConfigsApi,
  listIntegrationConfigsApi,
  mockCollectIntegrationApi,
  mockSendIntegrationEmailsApi,
  updateIntegrationConfigApi,
} from '#/api/integration-report';
import { listProjectsApi } from '#/api/project-manager/project';
import UserSelector from '#/components/zq-form/user-selector/user-selector.vue';

import { useColumns, useSearchFormSchema } from './data';

defineOptions({ name: 'DailyIntegrationConfig' });

// Dialog state
const dialogVisible = ref(false);
const dialogMode = ref<'create' | 'edit'>('create');
const dialogSaving = ref(false);
const collectSubmitting = ref(false);
const allProjects = ref<
  Array<{ domain: string; id: string; name: string; type: string }>
>([]);
const formConfigId = ref<string>('');
const valgrindSubModulesText = ref('');
const form = ref<ProjectConfigUpsertIn>({
  project_id: '',
  name: '',
  managers: [],
  enabled: true,
  code_check_task_id: '',
  bin_scope_task_id: '',
  build_check_task_id: '',
  compile_check_task_id: '',
  dt_project_id: '',
  code_scan_project_key: '',
  valgrind_sub_modules: [],
});

// --- Grid Setup ---
const gridOptions: VxeGridProps<ProjectConfigManageRow> = {
  columns: useColumns(),
  checkboxConfig: {
    labelField: 'seq',
    highlight: true,
    range: true,
  },
  pagerConfig: {
    enabled: true,
  },
  height: 'auto',
  keepSource: true,
  proxyConfig: {
    ajax: {
      query: async ({ page }, formValues) => {
        const params = {
          page: page.currentPage,
          page_size: page.pageSize,
          ...formValues,
        };
        const res = await listIntegrationConfigsApi(params);
        return {
          items: res.items,
          total: res.count ?? res.total ?? 0,
        };
      },
    },
  },
  toolbarConfig: {
    slots: {
      buttons: 'toolbar_buttons',
    },
    refresh: true, // VxeGrid built-in refresh
    custom: true,
  },
};

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions,
});

// --- Helper Functions ---

function normalizeValgrindSubModules(rawValue: string) {
  const values = rawValue
    .replaceAll(',', '\n')
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean);
  const normalized: string[] = [];
  const seen = new Set<string>();
  for (const value of values) {
    const lowered = value.toLowerCase();
    if (seen.has(lowered)) {
      continue;
    }
    seen.add(lowered);
    normalized.push(value);
  }
  return normalized;
}

function payloadOf(r: ProjectConfigManageRow): ProjectConfigUpsertIn {
  return {
    project_id: r.project_id,
    name: r.name,
    managers: r.manager_ids || [],
    enabled: r.enabled,
    code_check_task_id: r.code_check_task_id || '',
    bin_scope_task_id: r.bin_scope_task_id || '',
    build_check_task_id: r.build_check_task_id || '',
    compile_check_task_id: r.compile_check_task_id || '',
    dt_project_id: r.dt_project_id || '',
    code_scan_project_key: r.code_scan_project_key || '',
    valgrind_sub_modules: r.valgrind_sub_modules || [],
  };
}

function buildSubmitPayload(): ProjectConfigUpsertIn {
  return {
    ...form.value,
    valgrind_sub_modules: normalizeValgrindSubModules(
      valgrindSubModulesText.value,
    ),
  };
}

async function ensureProjectsLoaded() {
  if (allProjects.value.length > 0) return;
  try {
    const resp = await listProjectsApi({
      page: 1,
      pageSize: 1000,
      is_closed: false,
    });
    allProjects.value = (resp.items || []).map((p) => ({
      id: p.id,
      name: p.name,
      domain: p.domain,
      type: p.type,
    }));
  } catch {
    allProjects.value = [];
    ElMessage.error('获取项目列表失败，请检查权限或接口');
  }
}

// --- Actions ---

function openCreate() {
  dialogMode.value = 'create';
  formConfigId.value = '';
  form.value = {
    project_id: '',
    name: '',
    managers: [],
    enabled: true,
    code_check_task_id: '',
    bin_scope_task_id: '',
    build_check_task_id: '',
    compile_check_task_id: '',
    dt_project_id: '',
    code_scan_project_key: '',
    valgrind_sub_modules: [],
  };
  valgrindSubModulesText.value = '';
  dialogVisible.value = true;
  ensureProjectsLoaded();
}

function openEdit(r: ProjectConfigManageRow) {
  dialogMode.value = 'edit';
  formConfigId.value = r.id;
  form.value = payloadOf(r);
  valgrindSubModulesText.value = (r.valgrind_sub_modules || []).join('\n');
  dialogVisible.value = true;
  ensureProjectsLoaded();
}

async function saveRow(r: ProjectConfigManageRow) {
  try {
    await updateIntegrationConfigApi(r.id, payloadOf(r));
    ElMessage.success('状态更新成功');
  } catch {
    ElMessage.error('更新失败');
  }
}

async function submitDialog() {
  if (!form.value.name) {
    ElMessage.warning('请输入配置名称');
    return;
  }
  try {
    dialogSaving.value = true;
    const payload = buildSubmitPayload();
    if (dialogMode.value === 'create') {
      await createIntegrationConfigApi(payload);
      ElMessage.success('创建成功');
    } else {
      await updateIntegrationConfigApi(formConfigId.value, payload);
      ElMessage.success('更新成功');
    }
    dialogVisible.value = false;
    gridApi.reload(); // Refresh grid
  } finally {
    dialogSaving.value = false;
  }
}

async function initRows() {
  try {
    const created = await initIntegrationConfigsApi();
    ElMessage.success(`初始化完成，新增 ${created} 条配置`);
    gridApi.reload();
  } catch {
    ElMessage.error('初始化失败');
  }
}

async function deleteRow(r: ProjectConfigManageRow) {
  try {
    await deleteIntegrationConfigApi(r.id);
    ElMessage.success('删除成功');
    gridApi.reload();
  } catch {
    ElMessage.error('删除失败');
  }
}

function formatLocalDate(d: Date) {
  const year = d.getFullYear();
  const month = `${d.getMonth() + 1}`.padStart(2, '0');
  const day = `${d.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
}

async function batchMockCollect() {
  const records = gridApi.grid?.getCheckboxRecords() || [];
  const ids = records.map((r: any) => r.id);
  const isBatch = ids.length > 0;
  try {
    collectSubmitting.value = true;
    const todayStr = formatLocalDate(new Date());
    await mockCollectIntegrationApi(todayStr, isBatch ? ids : undefined);
    ElMessage.success(
      isBatch
        ? `已提交后台刷新任务（${ids.length} 条配置）`
        : '已提交后台刷新任务（全部配置）',
    );
  } catch {
    ElMessage.error('提交后台刷新任务失败');
  } finally {
    collectSubmitting.value = false;
  }
}

async function mockSendEmails() {
  try {
    const todayStr = formatLocalDate(new Date());
    const sent = await mockSendIntegrationEmailsApi(todayStr);
    ElMessage.success(`Mock 邮件发送完成：${sent} 封`);
  } catch {
    ElMessage.error('发送失败');
  }
}
</script>

<template>
  <Page auto-content-height>
    <Grid>
      <!-- Toolbar Buttons -->
      <template #toolbar_buttons>
        <div class="flex items-center gap-2">
          <ElButton size="small" type="primary" plain @click="openCreate">
            <template #icon><IconifyIcon icon="lucide:plus" /></template>
            新建配置
          </ElButton>
          <ElPopconfirm
            title="初始化配置将为无配置的项目创建默认记录，继续？"
            @confirm="initRows"
          >
            <template #reference>
              <ElButton size="small" plain>
                <template #icon><IconifyIcon icon="lucide:wand-2" /></template>
                初始化
              </ElButton>
            </template>
          </ElPopconfirm>
          <ElButton
            :loading="collectSubmitting"
            size="small"
            type="primary"
            plain
            @click="batchMockCollect"
          >
            <template #icon><IconifyIcon icon="lucide:database" /></template>
            刷新数据 (Mock)
          </ElButton>
          <ElButton size="small" type="success" plain @click="mockSendEmails">
            <template #icon><IconifyIcon icon="lucide:mail" /></template>
            Mock 发送邮件
          </ElButton>
        </div>
      </template>

      <!-- Enabled Switch -->
      <template #enabled_default="{ row }">
        <ElSwitch
          v-model="row.enabled"
          size="small"
          @change="() => saveRow(row)"
        />
      </template>

      <!-- Actions -->
      <template #action_default="{ row }">
        <ElButton size="small" type="primary" link @click="openEdit(row)">
          编辑
        </ElButton>
        <ElPopconfirm
          title="删除后该配置将不再参与统计和邮件，确认删除？"
          @confirm="() => deleteRow(row)"
        >
          <template #reference>
            <ElButton size="small" type="danger" link> 删除 </ElButton>
          </template>
        </ElPopconfirm>
      </template>
    </Grid>

    <!-- Dialog -->
    <ElDialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建项目配置' : '编辑项目配置'"
      width="640px"
      append-to-body
    >
      <ElForm label-width="160px">
        <ElFormItem label="关联项目">
          <ElSelect
            v-model="form.project_id"
            filterable
            placeholder="可不关联项目"
            style="width: 100%"
          >
            <ElOption label="不关联项目" value="" />
            <ElOption
              v-for="p in allProjects"
              :key="p.id"
              :label="`${p.name}（${p.domain || '-'} / ${p.type || '-'}）`"
              :value="p.id"
            />
          </ElSelect>
        </ElFormItem>

        <ElFormItem label="配置名称" required>
          <ElInput v-model="form.name" placeholder="邮件/报表中显示的名称" />
        </ElFormItem>

        <ElFormItem label="负责人">
          <UserSelector
            v-model="form.managers"
            :multiple="true"
            placeholder="请选择责任人"
          />
        </ElFormItem>

        <ElFormItem label="启用">
          <ElSwitch v-model="form.enabled" />
        </ElFormItem>

        <ElFormItem label="CodeCheck ID">
          <ElInput v-model="form.code_check_task_id" placeholder="Task ID" />
        </ElFormItem>
        <ElFormItem label="BinScope ID">
          <ElInput v-model="form.bin_scope_task_id" placeholder="Task ID" />
        </ElFormItem>
        <ElFormItem label="BuildCheck ID">
          <ElInput v-model="form.build_check_task_id" placeholder="Task ID" />
        </ElFormItem>
        <ElFormItem label="CompileCheck ID">
          <ElInput v-model="form.compile_check_task_id" placeholder="Task ID" />
        </ElFormItem>
        <ElFormItem label="CodeScan ProjectKey">
          <ElInput
            v-model="form.code_scan_project_key"
            placeholder="项目管理中的 project_key"
          />
        </ElFormItem>
        <ElFormItem label="TSan / Valgrind 子模块">
          <ElInput
            v-model="valgrindSubModulesText"
            :rows="4"
            type="textarea"
            placeholder="每行一个子模块，TSan 与 Valgrind 共用，例如：&#10;platform-core&#10;customer-a"
          />
        </ElFormItem>
        <ElFormItem label="DT Project ID">
          <ElInput v-model="form.dt_project_id" placeholder="Project ID" />
        </ElFormItem>
      </ElForm>

      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="dialogVisible = false">取消</ElButton>
          <ElButton
            type="primary"
            :loading="dialogSaving"
            @click="submitDialog"
          >
            保存
          </ElButton>
        </div>
      </template>
    </ElDialog>
  </Page>
</template>
