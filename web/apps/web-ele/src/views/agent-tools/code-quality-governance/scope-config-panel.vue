<!-- eslint-disable vue/html-closing-bracket-newline, vue/multiline-html-element-content-newline -->
<script lang="ts" setup>
import type {
  ConfigTab,
  LinkFormState,
  ProjectFormState,
  ResponsibilityFormState,
  UploadFormState,
} from './types';
import type {
  GovernanceLink,
  GovernanceProject,
  GovernanceResponsibility,
  UserOption,
} from '#/api/agent-tools/code-quality-governance';

import { computed, onMounted, ref } from 'vue';

import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElSelect,
  ElSwitch,
  ElTabPane,
  ElTabs,
  ElTag,
  ElUpload,
} from 'element-plus';

import {
  createLinkApi,
  createProjectApi,
  createResponsibilityApi,
  deleteLinkApi,
  deleteProjectApi,
  deleteResponsibilityApi,
  listLinksApi,
  listProjectsApi,
  listResponsibilitiesApi,
  updateLinkApi,
  updateProjectApi,
  updateResponsibilityApi,
  uploadReportApi,
} from '#/api/agent-tools/code-quality-governance';
import { UserSelector } from '#/components/zq-form/user-selector';
import { useZqTable } from '#/components/zq-table';

defineOptions({ name: 'CodeQualityGovernanceScopeConfig' });

defineProps<{
  projects: GovernanceProject[];
  responsibilities: GovernanceResponsibility[];
  users: UserOption[];
}>();

const emit = defineEmits<{ changed: [] }>();

const configTab = ref<ConfigTab>('projects');
const dialog = ref<'' | 'link' | 'project' | 'responsibility' | 'upload'>('');
const editingId = ref('');
const file = ref<File>();

const projectForm = ref<ProjectFormState>(createProjectForm());
const responsibilityForm = ref<ResponsibilityFormState>(
  createResponsibilityForm(),
);
const linkForm = ref<LinkFormState>(createLinkForm());
const uploadForm = ref<UploadFormState>(createUploadForm());

function createProjectForm(): ProjectFormState {
  return {
    branch: 'master',
    code: '',
    description: '',
    is_active: true,
    name: '',
    repository: '',
  };
}

function createResponsibilityForm(): ResponsibilityFormState {
  return {
    approver_ids: [],
    code: '',
    description: '',
    is_active: true,
    name: '',
    owner_id: '',
  };
}

function createLinkForm(): LinkFormState {
  return {
    is_active: true,
    project_id: '',
    remark: '',
    responsibility_id: '',
  };
}

function createUploadForm(): UploadFormState {
  return { project_id: '', responsibility_id: '', tool_name: '' };
}

function tableOptions() {
  return {
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [10, 20, 50, 100],
    },
    toolbarConfig: {
      custom: true,
      refresh: true,
      search: false,
      zoom: true,
    },
  };
}

const [ProjectGrid, projectGridApi] = useZqTable<GovernanceProject>({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    ...tableOptions(),
    border: true,
    columns: [
      { key: 'name', dataKey: 'name', title: '项目名称', minWidth: 160 },
      { key: 'code', dataKey: 'code', title: '项目编码', width: 140 },
      {
        key: 'repository',
        dataKey: 'repository',
        title: '仓库地址',
        minWidth: 220,
      },
      { key: 'branch', dataKey: 'branch', title: '默认分支', width: 120 },
      {
        key: 'is_active',
        dataKey: 'is_active',
        title: '状态',
        width: 90,
        slots: { default: 'cell-project-status' },
      },
      {
        key: 'actions',
        dataKey: 'actions',
        title: '操作',
        width: 130,
        slots: { default: 'cell-project-actions' },
      },
    ] as any,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({
          page,
        }: {
          page: { currentPage: number; pageSize: number };
        }) =>
          listProjectsApi({ page: page.currentPage, pageSize: page.pageSize }),
      },
    },
    showSelection: false,
    stripe: true,
  },
});

const [ResponsibilityGrid, responsibilityGridApi] =
  useZqTable<GovernanceResponsibility>({
    showSearchForm: false,
    separator: false,
    gridOptions: {
      ...tableOptions(),
      border: true,
      columns: [
        { key: 'name', dataKey: 'name', title: '责任田名称', minWidth: 160 },
        { key: 'code', dataKey: 'code', title: '责任田编码', width: 140 },
        {
          key: 'owner',
          dataKey: 'owner',
          title: '负责人',
          width: 120,
          slots: { default: 'cell-owner' },
        },
        {
          key: 'approvers',
          dataKey: 'approvers',
          title: '审批人员',
          minWidth: 220,
          slots: { default: 'cell-approvers' },
        },
        {
          key: 'is_active',
          dataKey: 'is_active',
          title: '状态',
          width: 90,
          slots: { default: 'cell-responsibility-status' },
        },
        {
          key: 'actions',
          dataKey: 'actions',
          title: '操作',
          width: 130,
          slots: { default: 'cell-responsibility-actions' },
        },
      ] as any,
      proxyConfig: {
        autoLoad: false,
        ajax: {
          query: async ({
            page,
          }: {
            page: { currentPage: number; pageSize: number };
          }) =>
            listResponsibilitiesApi({
              page: page.currentPage,
              pageSize: page.pageSize,
            }),
        },
      },
      showSelection: false,
      stripe: true,
    },
  });

const [LinkGrid, linkGridApi] = useZqTable<GovernanceLink>({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    ...tableOptions(),
    border: true,
    columns: [
      {
        key: 'project_name',
        dataKey: 'project_name',
        title: '项目',
        minWidth: 180,
      },
      {
        key: 'responsibility_name',
        dataKey: 'responsibility_name',
        title: '责任田',
        minWidth: 180,
      },
      { key: 'remark', dataKey: 'remark', title: '关联备注', minWidth: 240 },
      {
        key: 'is_active',
        dataKey: 'is_active',
        title: '状态',
        width: 90,
        slots: { default: 'cell-link-status' },
      },
      {
        key: 'actions',
        dataKey: 'actions',
        title: '操作',
        width: 130,
        slots: { default: 'cell-link-actions' },
      },
    ] as any,
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({
          page,
        }: {
          page: { currentPage: number; pageSize: number };
        }) => listLinksApi({ page: page.currentPage, pageSize: page.pageSize }),
      },
    },
    showSelection: false,
    stripe: true,
  },
});

const dialogVisible = computed({
  get: () => Boolean(dialog.value),
  set: (visible: boolean) => {
    if (!visible) dialog.value = '';
  },
});

const dialogTitle = computed(() => {
  if (dialog.value === 'project')
    return editingId.value ? '编辑项目' : '新建项目';
  if (dialog.value === 'responsibility') {
    return editingId.value ? '编辑责任田' : '新建责任田';
  }
  if (dialog.value === 'link') return editingId.value ? '编辑关联' : '新增关联';
  return '上传扫描报告';
});

function refreshTables() {
  void projectGridApi.reload();
  void responsibilityGridApi.reload();
  void linkGridApi.reload();
}

function openCreate(type: 'link' | 'project' | 'responsibility' | 'upload') {
  editingId.value = '';
  dialog.value = type;
  if (type === 'project') projectForm.value = createProjectForm();
  if (type === 'responsibility') {
    responsibilityForm.value = createResponsibilityForm();
  }
  if (type === 'link') linkForm.value = createLinkForm();
  if (type === 'upload') {
    uploadForm.value = createUploadForm();
    file.value = undefined;
  }
}

function editProject(row: GovernanceProject) {
  editingId.value = row.id;
  projectForm.value = { ...row };
  dialog.value = 'project';
}

function editResponsibility(row: GovernanceResponsibility) {
  editingId.value = row.id;
  responsibilityForm.value = {
    approver_ids: row.approvers.map((item) => item.id),
    code: row.code,
    description: row.description,
    is_active: row.is_active,
    name: row.name,
    owner_id: row.owner?.id || '',
  };
  dialog.value = 'responsibility';
}

function editLink(row: GovernanceLink) {
  editingId.value = row.id;
  linkForm.value = {
    is_active: row.is_active,
    project_id: row.project_id,
    remark: row.remark,
    responsibility_id: row.responsibility_id,
  };
  dialog.value = 'link';
}

async function saveDialog() {
  switch (dialog.value) {
    case 'link':
      await (editingId.value
        ? updateLinkApi(editingId.value, linkForm.value)
        : createLinkApi(linkForm.value));
      break;
    case 'project':
      await (editingId.value
        ? updateProjectApi(editingId.value, projectForm.value)
        : createProjectApi(projectForm.value));
      break;
    case 'responsibility':
      await (editingId.value
        ? updateResponsibilityApi(editingId.value, responsibilityForm.value)
        : createResponsibilityApi(responsibilityForm.value));
      break;
    default:
      return;
  }
  dialog.value = '';
  refreshTables();
  emit('changed');
  ElMessage.success('保存成功');
}

async function remove(type: 'link' | 'project' | 'responsibility', id: string) {
  try {
    await ElMessageBox.confirm(
      '删除后将停止新的数据接入，历史报告仍会保留，确认继续？',
      '确认删除',
      { type: 'warning' },
    );
    if (type === 'project') await deleteProjectApi(id);
    if (type === 'responsibility') await deleteResponsibilityApi(id);
    if (type === 'link') await deleteLinkApi(id);
    refreshTables();
    emit('changed');
    ElMessage.success('删除成功');
  } catch {
    // 用户取消确认时不提示错误。
  }
}

function beforeUpload(rawFile: File) {
  file.value = rawFile;
  return false;
}

async function submitUpload() {
  if (!uploadForm.value.project_id || !uploadForm.value.responsibility_id) {
    ElMessage.warning('请选择项目和责任田');
    return;
  }
  if (!uploadForm.value.tool_name.trim()) {
    ElMessage.warning('请输入扫描工具名称');
    return;
  }
  if (!file.value) {
    ElMessage.warning('请选择 JSON 文件');
    return;
  }
  const data = new FormData();
  data.append('file', file.value);
  data.append('project_id', uploadForm.value.project_id);
  data.append('responsibility_id', uploadForm.value.responsibility_id);
  data.append('tool_name', uploadForm.value.tool_name.trim());
  await uploadReportApi(data);
  dialog.value = '';
  refreshTables();
  emit('changed');
  ElMessage.success('扫描报告解析完成');
}

function formatApprovers(items: UserOption[]) {
  return items.map((item) => item.name).join('、') || '-';
}

function loadTables() {
  void projectGridApi.reload();
  void responsibilityGridApi.reload();
  void linkGridApi.reload();
}

onMounted(loadTables);
</script>

<template>
  <section class="scope-panel">
    <div class="panel-heading">
      <div>
        <h2>项目与责任田</h2>
        <p>维护治理范围、审批人员和扫描结果接入配置</p>
      </div>
    </div>

    <ElTabs v-model="configTab" class="scope-tabs">
      <ElTabPane label="项目" name="projects" />
      <ElTabPane label="责任田" name="responsibilities" />
      <ElTabPane label="项目 × 责任田" name="links" />
      <ElTabPane label="接入扫描" name="upload" />
    </ElTabs>

    <div v-if="configTab === 'projects'" class="table-section">
      <div class="table-toolbar">
        <span>项目列表</span>
        <ElButton type="primary" @click="openCreate('project')"
          >新建项目</ElButton
        >
      </div>
      <ProjectGrid class="config-grid">
        <template #cell-project-status="{ row }">
          <ElTag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '停用' }}
          </ElTag>
        </template>
        <template #cell-project-actions="{ row }">
          <ElButton link type="primary" @click="editProject(row)"
            >编辑</ElButton
          >
          <ElButton link type="danger" @click="remove('project', row.id)"
            >删除</ElButton
          >
        </template>
      </ProjectGrid>
    </div>

    <div v-else-if="configTab === 'responsibilities'" class="table-section">
      <div class="table-toolbar">
        <span>责任田列表</span>
        <ElButton type="primary" @click="openCreate('responsibility')"
          >新建责任田</ElButton
        >
      </div>
      <ResponsibilityGrid class="config-grid">
        <template #cell-owner="{ row }">{{ row.owner?.name || '-' }}</template>
        <template #cell-approvers="{ row }">{{
          formatApprovers(row.approvers)
        }}</template>
        <template #cell-responsibility-status="{ row }">
          <ElTag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '停用' }}
          </ElTag>
        </template>
        <template #cell-responsibility-actions="{ row }">
          <ElButton link type="primary" @click="editResponsibility(row)"
            >编辑</ElButton
          >
          <ElButton link type="danger" @click="remove('responsibility', row.id)"
            >删除</ElButton
          >
        </template>
      </ResponsibilityGrid>
    </div>

    <div v-else-if="configTab === 'links'" class="table-section">
      <div class="table-toolbar">
        <span>项目 × 责任田关联</span>
        <ElButton type="primary" @click="openCreate('link')">新增关联</ElButton>
      </div>
      <LinkGrid class="config-grid">
        <template #cell-link-status="{ row }">
          <ElTag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '停用' }}
          </ElTag>
        </template>
        <template #cell-link-actions="{ row }">
          <ElButton link type="primary" @click="editLink(row)">编辑</ElButton>
          <ElButton link type="danger" @click="remove('link', row.id)"
            >删除</ElButton
          >
        </template>
      </LinkGrid>
    </div>

    <div v-else class="upload-guide">
      <div class="upload-guide__copy">
        <h3>接入第三方扫描 JSON</h3>
        <p>
          支持 summary、findings、location、evidence、identity 和
          legacy_fingerprints 字段。
        </p>
        <p>complete=false 的报告仍会入库，并在看板标记为扫描未完成。</p>
      </div>
      <ElButton type="primary" @click="openCreate('upload')"
        >上传 JSON 报告</ElButton
      >
    </div>

    <ElDialog v-model="dialogVisible" :title="dialogTitle" width="560px">
      <ElForm
        v-if="dialog === 'project'"
        :model="projectForm"
        label-width="94px"
      >
        <ElFormItem label="项目名称" required
          ><ElInput v-model="projectForm.name"
        /></ElFormItem>
        <ElFormItem label="项目编码" required
          ><ElInput v-model="projectForm.code"
        /></ElFormItem>
        <ElFormItem label="仓库地址"
          ><ElInput v-model="projectForm.repository"
        /></ElFormItem>
        <ElFormItem label="默认分支"
          ><ElInput v-model="projectForm.branch"
        /></ElFormItem>
        <ElFormItem label="描述"
          ><ElInput v-model="projectForm.description" type="textarea"
        /></ElFormItem>
        <ElFormItem label="启用状态"
          ><ElSwitch v-model="projectForm.is_active"
        /></ElFormItem>
      </ElForm>

      <ElForm
        v-else-if="dialog === 'responsibility'"
        :model="responsibilityForm"
        label-width="94px"
      >
        <ElFormItem label="责任田名称" required
          ><ElInput v-model="responsibilityForm.name"
        /></ElFormItem>
        <ElFormItem label="责任田编码" required
          ><ElInput v-model="responsibilityForm.code"
        /></ElFormItem>
        <ElFormItem label="负责人">
          <UserSelector
            v-model="responsibilityForm.owner_id"
            placeholder="请选择负责人"
          />
        </ElFormItem>
        <ElFormItem label="审批人员">
          <UserSelector
            v-model="responsibilityForm.approver_ids"
            multiple
            placeholder="请选择审批人员"
          />
        </ElFormItem>
        <ElFormItem label="描述"
          ><ElInput v-model="responsibilityForm.description" type="textarea"
        /></ElFormItem>
        <ElFormItem label="启用状态"
          ><ElSwitch v-model="responsibilityForm.is_active"
        /></ElFormItem>
      </ElForm>

      <ElForm
        v-else-if="dialog === 'link'"
        :model="linkForm"
        label-width="94px"
      >
        <ElFormItem label="项目" required>
          <ElSelect
            v-model="linkForm.project_id"
            class="w-full"
            placeholder="请选择项目"
          >
            <ElOption
              v-for="item in projects"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="责任田" required>
          <ElSelect
            v-model="linkForm.responsibility_id"
            class="w-full"
            placeholder="请选择责任田"
          >
            <ElOption
              v-for="item in responsibilities"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="备注"
          ><ElInput v-model="linkForm.remark"
        /></ElFormItem>
        <ElFormItem label="启用状态"
          ><ElSwitch v-model="linkForm.is_active"
        /></ElFormItem>
      </ElForm>

      <ElForm
        v-else-if="dialog === 'upload'"
        :model="uploadForm"
        label-width="94px"
      >
        <ElFormItem label="项目" required>
          <ElSelect
            v-model="uploadForm.project_id"
            class="w-full"
            placeholder="请选择项目"
          >
            <ElOption
              v-for="item in projects"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="责任田" required>
          <ElSelect
            v-model="uploadForm.responsibility_id"
            class="w-full"
            placeholder="请选择责任田"
          >
            <ElOption
              v-for="item in responsibilities"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="扫描工具" required
          ><ElInput v-model="uploadForm.tool_name" placeholder="例如：CodeQL"
        /></ElFormItem>
        <ElUpload
          accept=".json,application/json"
          :auto-upload="false"
          :before-upload="beforeUpload"
        >
          <ElButton>选择 JSON 文件</ElButton>
        </ElUpload>
      </ElForm>

      <template #footer>
        <ElButton @click="dialog = ''">取消</ElButton>
        <ElButton
          v-if="dialog === 'upload'"
          type="primary"
          @click="submitUpload"
          >上传</ElButton
        >
        <ElButton v-else type="primary" @click="saveDialog">保存</ElButton>
      </template>
    </ElDialog>
  </section>
</template>

<style scoped>
.scope-panel {
  display: flex;
  min-height: 100%;
  flex-direction: column;
}

.panel-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 12px;
}

.panel-heading h2 {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 18px;
  font-weight: 600;
}

.panel-heading p {
  margin: 6px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.scope-tabs {
  margin-bottom: 2px;
}

.table-section {
  display: flex;
  min-height: 500px;
  flex: 1;
  flex-direction: column;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 42px;
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 500;
}

.config-grid {
  min-height: 0;
  flex: 1;
}

.upload-guide {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 24px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-fill-color-lighter);
}

.upload-guide__copy h3 {
  margin: 0 0 10px;
  color: var(--el-text-color-primary);
  font-size: 15px;
  font-weight: 600;
}

.upload-guide__copy p {
  margin: 6px 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

@media (max-width: 640px) {
  .upload-guide {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
