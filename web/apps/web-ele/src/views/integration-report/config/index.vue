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
  ElDivider,
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
  listDomainDirectorySetOptionsApi,
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
const dtFuzzBranchesText = ref('');
const codeCheckTaskIdsText = ref('');
const dtBinTaskIdsText = ref('');
const cooddyCheckTaskIdsText = ref('');
const binScopeTaskIdsText = ref('');
const domainDirectoryOptions = ref<Array<{ id: string; name: string }>>([]);
const form = ref<ProjectConfigUpsertIn>({
  project_id: '',
  name: '',
  managers: [],
  enabled: true,
  code_check_task_id: '',
  dt_bin_task_id: '',
  cooddy_check_task_id: '',
  bin_scope_task_id: '',
  enable_domain_metrics: false,
  domain_directory_set_id: '',
  code_check_task_ids: [],
  dt_bin_task_ids: [],
  cooddy_check_task_ids: [],
  bin_scope_task_ids: [],
  build_check_task_id: '',
  compile_check_task_id: '',
  dt_project_id: '',
  code_scan_project_key: '',
  valgrind_sub_modules: [],
  enable_dt_fuzz: false,
  dt_fuzz_version_name: '',
  dt_fuzz_branches: [],
  dt_fuzz_pbi_id: '',
  dt_fuzz_domain_id: '',
  dt_fuzz_project_id: '',
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

function normalizeDtFuzzBranches(rawValue: string) {
  return normalizeValgrindSubModules(rawValue);
}

function normalizeTaskIds(rawValue: string) {
  return normalizeValgrindSubModules(rawValue);
}

function payloadOf(r: ProjectConfigManageRow): ProjectConfigUpsertIn {
  return {
    project_id: r.project_id,
    name: r.name,
    managers: r.manager_ids || [],
    enabled: r.enabled,
    code_check_task_id: r.code_check_task_id || '',
    dt_bin_task_id: r.dt_bin_task_id || '',
    cooddy_check_task_id: r.cooddy_check_task_id || '',
    bin_scope_task_id: r.bin_scope_task_id || '',
    enable_domain_metrics: r.enable_domain_metrics || false,
    domain_directory_set_id: r.domain_directory_set_id || '',
    code_check_task_ids: r.code_check_task_ids || [],
    dt_bin_task_ids: r.dt_bin_task_ids || [],
    cooddy_check_task_ids: r.cooddy_check_task_ids || [],
    bin_scope_task_ids: r.bin_scope_task_ids || [],
    build_check_task_id: r.build_check_task_id || '',
    compile_check_task_id: r.compile_check_task_id || '',
    dt_project_id: r.dt_project_id || '',
    code_scan_project_key: r.code_scan_project_key || '',
    valgrind_sub_modules: r.valgrind_sub_modules || [],
    enable_dt_fuzz: r.enable_dt_fuzz || false,
    dt_fuzz_version_name: r.dt_fuzz_version_name || '',
    dt_fuzz_branches: r.dt_fuzz_branches || [],
    dt_fuzz_pbi_id: r.dt_fuzz_pbi_id || '',
    dt_fuzz_domain_id: r.dt_fuzz_domain_id || '',
    dt_fuzz_project_id: r.dt_fuzz_project_id || '',
  };
}

function buildSubmitPayload(): ProjectConfigUpsertIn {
  const enableDomainMetrics = form.value.enable_domain_metrics;
  return {
    ...form.value,
    code_check_task_id: enableDomainMetrics
      ? ''
      : form.value.code_check_task_id,
    dt_bin_task_id: enableDomainMetrics ? '' : form.value.dt_bin_task_id,
    cooddy_check_task_id: enableDomainMetrics
      ? ''
      : form.value.cooddy_check_task_id,
    bin_scope_task_id: enableDomainMetrics ? '' : form.value.bin_scope_task_id,
    domain_directory_set_id: enableDomainMetrics
      ? form.value.domain_directory_set_id
      : '',
    code_check_task_ids: enableDomainMetrics
      ? normalizeTaskIds(codeCheckTaskIdsText.value)
      : [],
    dt_bin_task_ids: enableDomainMetrics
      ? normalizeTaskIds(dtBinTaskIdsText.value)
      : [],
    cooddy_check_task_ids: enableDomainMetrics
      ? normalizeTaskIds(cooddyCheckTaskIdsText.value)
      : [],
    bin_scope_task_ids: enableDomainMetrics
      ? normalizeTaskIds(binScopeTaskIdsText.value)
      : [],
    valgrind_sub_modules: normalizeValgrindSubModules(
      valgrindSubModulesText.value,
    ),
    dt_fuzz_branches: normalizeDtFuzzBranches(dtFuzzBranchesText.value),
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

async function ensureDomainDirectoryOptionsLoaded() {
  try {
    domainDirectoryOptions.value = await listDomainDirectorySetOptionsApi();
  } catch {
    domainDirectoryOptions.value = [];
    ElMessage.error('获取责任田目录配置失败，请检查权限或接口');
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
    dt_bin_task_id: '',
    cooddy_check_task_id: '',
    bin_scope_task_id: '',
    enable_domain_metrics: false,
    domain_directory_set_id: '',
    code_check_task_ids: [],
    dt_bin_task_ids: [],
    cooddy_check_task_ids: [],
    bin_scope_task_ids: [],
    build_check_task_id: '',
    compile_check_task_id: '',
    dt_project_id: '',
    code_scan_project_key: '',
    valgrind_sub_modules: [],
    enable_dt_fuzz: false,
    dt_fuzz_version_name: '',
    dt_fuzz_branches: [],
    dt_fuzz_pbi_id: '',
    dt_fuzz_domain_id: '',
    dt_fuzz_project_id: '',
  };
  valgrindSubModulesText.value = '';
  dtFuzzBranchesText.value = '';
  codeCheckTaskIdsText.value = '';
  dtBinTaskIdsText.value = '';
  cooddyCheckTaskIdsText.value = '';
  binScopeTaskIdsText.value = '';
  dialogVisible.value = true;
  ensureProjectsLoaded();
  ensureDomainDirectoryOptionsLoaded();
}

function openEdit(r: ProjectConfigManageRow) {
  dialogMode.value = 'edit';
  formConfigId.value = r.id;
  form.value = payloadOf(r);
  valgrindSubModulesText.value = (r.valgrind_sub_modules || []).join('\n');
  dtFuzzBranchesText.value = (r.dt_fuzz_branches || []).join('\n');
  codeCheckTaskIdsText.value = (r.code_check_task_ids || []).join('\n');
  dtBinTaskIdsText.value = (r.dt_bin_task_ids || []).join('\n');
  cooddyCheckTaskIdsText.value = (r.cooddy_check_task_ids || []).join('\n');
  binScopeTaskIdsText.value = (r.bin_scope_task_ids || []).join('\n');
  dialogVisible.value = true;
  ensureProjectsLoaded();
  ensureDomainDirectoryOptionsLoaded();
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
  const payload = buildSubmitPayload();
  if (payload.enable_domain_metrics && !payload.domain_directory_set_id) {
    ElMessage.warning('启用按领域获取时请选择责任田目录配置');
    return;
  }
  const missingDtFuzzConfig =
    !payload.dt_fuzz_version_name.trim() ||
    payload.dt_fuzz_branches.length === 0 ||
    !payload.dt_fuzz_pbi_id.trim() ||
    !payload.dt_fuzz_domain_id.trim() ||
    !payload.dt_fuzz_project_id.trim();
  if (payload.enable_dt_fuzz && missingDtFuzzConfig) {
    ElMessage.warning(
      '启用 DT_FUZZ 时请完整填写 versionName、分支、pbiId、domian-id、project-id',
    );
    return;
  }
  try {
    dialogSaving.value = true;
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

        <template v-if="!form.enable_domain_metrics">
          <ElFormItem label="CodeCheck ID">
            <ElInput v-model="form.code_check_task_id" placeholder="Task ID" />
          </ElFormItem>
          <ElFormItem label="DT_Bin ID">
            <ElInput v-model="form.dt_bin_task_id" placeholder="Task ID" />
          </ElFormItem>
          <ElFormItem label="Cooddy Check ID">
            <ElInput
              v-model="form.cooddy_check_task_id"
              placeholder="Task ID"
            />
          </ElFormItem>
          <ElFormItem label="BinScope ID">
            <ElInput v-model="form.bin_scope_task_id" placeholder="Task ID" />
          </ElFormItem>
        </template>

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

        <ElDivider content-position="left">DT_FUZZ 数据湖配置</ElDivider>
        <ElFormItem label="启用 DT_FUZZ">
          <ElSwitch v-model="form.enable_dt_fuzz" />
        </ElFormItem>
        <template v-if="form.enable_dt_fuzz">
          <ElFormItem label="versionName" required>
            <ElInput
              v-model="form.dt_fuzz_version_name"
              placeholder="例如 HarmonySpace 510 1.0.0"
            />
          </ElFormItem>
          <ElFormItem label="branch" required>
            <ElInput
              v-model="dtFuzzBranchesText"
              :rows="4"
              type="textarea"
              placeholder="每行一个分支，例如：&#10;master&#10;release/1.0"
            />
          </ElFormItem>
          <ElFormItem label="pbiId" required>
            <ElInput v-model="form.dt_fuzz_pbi_id" placeholder="pbiId" />
          </ElFormItem>
          <ElFormItem label="domian-id" required>
            <ElInput
              v-model="form.dt_fuzz_domain_id"
              placeholder="数据湖字段 domian-id"
            />
          </ElFormItem>
          <ElFormItem label="project-id" required>
            <ElInput
              v-model="form.dt_fuzz_project_id"
              placeholder="数据湖字段 project-id"
            />
          </ElFormItem>
        </template>

        <ElDivider content-position="left">责任田领域采集配置</ElDivider>
        <ElFormItem label="按领域获取">
          <ElSwitch v-model="form.enable_domain_metrics" />
        </ElFormItem>
        <template v-if="form.enable_domain_metrics">
          <ElFormItem label="责任田目录配置" required>
            <ElSelect
              v-model="form.domain_directory_set_id"
              filterable
              placeholder="请选择可复用的责任田目录配置"
              style="width: 100%"
            >
              <ElOption
                v-for="item in domainDirectoryOptions"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="CodeCheck ID列表">
            <ElInput
              v-model="codeCheckTaskIdsText"
              :rows="3"
              type="textarea"
              placeholder="每行一个 task id，采集时分别请求后累加"
            />
          </ElFormItem>
          <ElFormItem label="DT_Bin ID列表">
            <ElInput
              v-model="dtBinTaskIdsText"
              :rows="3"
              type="textarea"
              placeholder="每行一个 task id，采集时分别请求后累加"
            />
          </ElFormItem>
          <ElFormItem label="Cooddy Check ID列表">
            <ElInput
              v-model="cooddyCheckTaskIdsText"
              :rows="3"
              type="textarea"
              placeholder="每行一个 task id，采集时分别请求后累加"
            />
          </ElFormItem>
          <ElFormItem label="BinScope ID列表">
            <ElInput
              v-model="binScopeTaskIdsText"
              :rows="3"
              type="textarea"
              placeholder="每行一个 task id，采集时分别请求后累加"
            />
          </ElFormItem>
        </template>
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
