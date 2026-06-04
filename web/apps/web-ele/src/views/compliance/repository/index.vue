<script lang="ts" setup>
import type {
  ComplianceBindMode,
  ComplianceDomain,
  ComplianceMode,
  ImportResult,
  OrganizationItem,
  RepositoryItem,
  RepositoryPayload,
} from '#/api/compliance/base';
import type { DictItem } from '#/api/core/dict';
import type { PlGroup } from '#/api/core/pl';
import type {
  FormInstance,
  FormRules,
  UploadRequestOptions,
} from 'element-plus';

import { computed, nextTick, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { Edit, Plus, Search, Trash2, Upload } from '@vben/icons';

import {
  ElButton,
  ElDialog,
  ElDrawer,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElLink,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElRadioButton,
  ElRadioGroup,
  ElSelect,
  ElSkeleton,
  ElSkeletonItem,
  ElTag,
  ElTooltip,
  ElTree,
  ElUpload,
} from 'element-plus';

import {
  bindBranchesToRepositoriesApi,
  createOrganizationApi,
  createRepositoryApi,
  deleteOrganizationApi,
  deleteRepositoryApi,
  downloadOrganizationTemplateApi,
  downloadRepositoryTemplateApi,
  importOrganizationsApi,
  importRepositoriesApi,
  listBranchesApi,
  listOrganizationsApi,
  listRepositoriesApi,
  listValidOrganizationParentsApi,
  updateOrganizationApi,
  updateRepositoryApi,
} from '#/api/compliance/base';
import { getDictItemByCodeApi } from '#/api/core/dict';
import { getAllPlApi } from '#/api/core/pl';
import { useZqTable } from '#/components/zq-table';

import {
  BIND_MODE_OPTIONS,
  DOMAIN_OPTIONS,
  MODE_OPTIONS,
  useRepositoryColumns,
} from './data';

defineOptions({ name: 'ComplianceRepository' });

const REPO_TYPE_DICT_CODE = 'code_compliance_repo_type';

interface OrganizationTreeNode extends OrganizationItem {
  children?: OrganizationTreeNode[];
}

interface OrganizationOption {
  id: string;
  label: string;
  node: OrganizationItem;
}

interface OrganizationFormState {
  domain: ComplianceDomain;
  group_id: string;
  mode: ComplianceMode;
  name: string;
  parent_id: string;
  remark: string;
  sort: number;
}

interface RepositoryFormState extends RepositoryPayload {
  responsibility_group_ids: string[];
}

const organizationTreeRef = ref<InstanceType<typeof ElTree>>();
const organizationFormRef = ref<FormInstance>();
const repositoryFormRef = ref<FormInstance>();

const pageLoading = ref(true);
const treeLoading = ref(false);
const treeExpandAll = ref(true);
const treeRenderKey = ref(0);
const organizationKeyword = ref('');
const organizationTree = ref<OrganizationTreeNode[]>([]);
const selectedOrganizationId = ref('');

const repositoryKeyword = ref('');
const selectedMode = ref('');
const selectedDomain = ref('');
const selectedRepoType = ref('');
const selectedRepositories = ref<RepositoryItem[]>([]);
const repositoryTotal = ref(0);

const repoTypeOptions = ref<DictItem[]>([]);
const plGroupOptions = ref<PlGroup[]>([]);
const parentOptions = ref<OrganizationOption[]>([]);
const branchOptions = ref<any[]>([]);

const importing = ref(false);
const organizationDialogVisible = ref(false);
const organizationDialogTitle = ref('新增组织');
const organizationEditingId = ref('');
const repositoryDrawerVisible = ref(false);
const repositoryDrawerTitle = ref('新增代码库');
const repositoryEditingId = ref('');
const bindDialogVisible = ref(false);
const bindLoading = ref(false);

const organizationForm = reactive<OrganizationFormState>({
  domain: 'cockpit',
  group_id: '',
  mode: 'CR',
  name: '',
  parent_id: '',
  remark: '',
  sort: 0,
});

const repositoryForm = reactive<RepositoryFormState>({
  domain: 'cockpit',
  mode: 'CR',
  organization_id: '',
  project_id: '',
  project_name: '',
  project_url: '',
  remark: '',
  repo_type: '',
  responsibility_group_ids: [],
  sort: 0,
});

const bindForm = reactive<{
  branch_ids: string[];
  mode: ComplianceBindMode;
}>({
  branch_ids: [],
  mode: 'append',
});

const organizationRules: FormRules<OrganizationFormState> = {
  domain: [{ message: '请选择领域', required: true, trigger: 'change' }],
  group_id: [{ message: '请输入组织ID', required: true, trigger: 'blur' }],
  mode: [{ message: '请选择模式', required: true, trigger: 'change' }],
  name: [{ message: '请输入组织名', required: true, trigger: 'blur' }],
};

const repositoryRules: FormRules<RepositoryFormState> = {
  domain: [{ message: '请选择领域', required: true, trigger: 'change' }],
  mode: [{ message: '请选择模式', required: true, trigger: 'change' }],
  organization_id: [
    { message: '请选择所属组织', required: true, trigger: 'change' },
  ],
  project_id: [{ message: '请输入代码库ID', required: true, trigger: 'blur' }],
  project_name: [
    { message: '请输入代码库名', required: true, trigger: 'blur' },
  ],
};

function getSelectedDomain(): ComplianceDomain | undefined {
  return selectedDomain.value
    ? (selectedDomain.value as ComplianceDomain)
    : undefined;
}

const [Grid, gridApi] = useZqTable<RepositoryItem>({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    border: true,
    columns: useRepositoryColumns(),
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [10, 20, 50, 100],
    },
    proxyConfig: {
      autoLoad: false,
      ajax: {
        query: async ({
          page,
        }: {
          page: { currentPage: number; pageSize: number };
        }) => {
          if (!selectedOrganizationId.value) {
            repositoryTotal.value = 0;
            return { items: [], total: 0 };
          }
          const result = await listRepositoriesApi({
            domain: getSelectedDomain(),
            keyword: repositoryKeyword.value || undefined,
            mode: (selectedMode.value as ComplianceMode) || undefined,
            organization_id: selectedOrganizationId.value,
            page: page.currentPage,
            pageSize: page.pageSize,
            repo_type: selectedRepoType.value || undefined,
          });
          repositoryTotal.value = result.total || 0;
          return result;
        },
      },
    },
    showSelection: true,
    stripe: true,
    toolbarConfig: {
      custom: true,
      refresh: true,
      search: false,
      zoom: true,
    },
  },
});

const filteredOrganizationTree = computed(() => {
  // 搜索时仍保留命中节点的祖先，让组织层级关系清晰可读。
  const keyword = organizationKeyword.value.trim().toLowerCase();
  return keyword
    ? filterOrganizationTree(organizationTree.value, keyword)
    : cloneOrganizationTree(organizationTree.value);
});

const organizationOptions = computed(() =>
  flattenOrganizationOptions(organizationTree.value),
);

const selectedOrganization = computed(() => {
  if (!selectedOrganizationId.value) return undefined;
  return findOrganizationById(
    organizationTree.value,
    selectedOrganizationId.value,
  );
});

const selectedOrganizationPath = computed(() => {
  if (!selectedOrganizationId.value) return '暂无组织';
  const path = findOrganizationPath(
    organizationTree.value,
    selectedOrganizationId.value,
  );
  return path.length > 0 ? path.map((item) => item.name).join(' / ') : '-';
});

function cloneOrganizationTree(
  items: OrganizationTreeNode[],
): OrganizationTreeNode[] {
  // 过滤和渲染会改 children 引用，这里保持原始树数据不被污染。
  return items.map((item) => ({
    ...item,
    children: item.children ? cloneOrganizationTree(item.children) : [],
  }));
}

function filterOrganizationTree(
  items: OrganizationTreeNode[],
  keyword: string,
): OrganizationTreeNode[] {
  // 命中子节点时保留祖先节点，保证搜索结果仍然是一棵可读的树。
  return items
    .map((item) => {
      const children = item.children
        ? filterOrganizationTree(item.children, keyword)
        : [];
      const matched =
        item.name.toLowerCase().includes(keyword) ||
        item.group_id.toLowerCase().includes(keyword);
      if (!matched && children.length === 0) return undefined;
      return { ...item, children };
    })
    .filter(Boolean) as OrganizationTreeNode[];
}

function flattenOrganizationOptions(
  items: OrganizationTreeNode[],
  parents: string[] = [],
): OrganizationOption[] {
  // 下拉框需要完整路径，避免同名组织在不同父节点下难以区分。
  return items.flatMap((item) => {
    const path = [...parents, item.name];
    return [
      { id: item.id, label: path.join(' / '), node: item },
      ...flattenOrganizationOptions(item.children || [], path),
    ];
  });
}

function findOrganizationById(
  items: OrganizationTreeNode[],
  id: string,
): OrganizationTreeNode | undefined {
  for (const item of items) {
    if (item.id === id) return item;
    const child = findOrganizationById(item.children || [], id);
    if (child) return child;
  }
}

function findFirstOrganizationNode(
  items: OrganizationTreeNode[],
): OrganizationTreeNode | undefined {
  // 页面取消虚拟根节点后，进入时按树展示顺序选中第一个真实组织。
  for (const item of items) {
    if (item.id) return item;
    const child = findFirstOrganizationNode(item.children || []);
    if (child) return child;
  }
}

function findOrganizationPath(
  items: OrganizationTreeNode[],
  id: string,
  parents: OrganizationTreeNode[] = [],
): OrganizationTreeNode[] {
  for (const item of items) {
    const path = [...parents, item];
    if (item.id === id) return path;
    const childPath = findOrganizationPath(item.children || [], id, path);
    if (childPath.length > 0) return childPath;
  }
  return [];
}

function resetOrganizationForm(parentId = '') {
  Object.assign(organizationForm, {
    domain: selectedOrganization.value?.domain || 'cockpit',
    group_id: '',
    mode: selectedOrganization.value?.mode || 'CR',
    name: '',
    parent_id: parentId,
    remark: '',
    sort: 0,
  });
  organizationFormRef.value?.clearValidate();
}

function resetRepositoryForm() {
  Object.assign(repositoryForm, {
    domain: selectedOrganization.value?.domain || 'cockpit',
    mode: selectedOrganization.value?.mode || 'CR',
    organization_id: selectedOrganization.value?.id || '',
    project_id: '',
    project_name: '',
    project_url: '',
    remark: '',
    repo_type: '',
    responsibility_group_ids: [],
    sort: 0,
  });
  repositoryFormRef.value?.clearValidate();
}

async function loadOrganizations() {
  // 组织树刷新后尽量保留当前选中节点，不存在时选中第一个真实组织。
  treeLoading.value = true;
  try {
    organizationTree.value = await listOrganizationsApi();
    const current = selectedOrganizationId.value
      ? findOrganizationById(
          organizationTree.value,
          selectedOrganizationId.value,
        )
      : undefined;
    if (!current) {
      selectedOrganizationId.value =
        findFirstOrganizationNode(organizationTree.value)?.id || '';
    }
    await nextTick();
    if (selectedOrganizationId.value) {
      organizationTreeRef.value?.setCurrentKey(selectedOrganizationId.value);
    }
  } finally {
    treeLoading.value = false;
  }
}

async function loadOptions() {
  const [repoTypes, plGroups] = await Promise.all([
    getDictItemByCodeApi(REPO_TYPE_DICT_CODE).catch(() => []),
    getAllPlApi().catch(() => []),
  ]);
  repoTypeOptions.value = repoTypes.filter((item) => item.status);
  plGroupOptions.value = plGroups.filter((item) => item.status);
}

function reloadRepositories(resetPage = false) {
  // 切换组织或筛选时清空勾选，避免批量绑定误作用到旧列表行。
  if (resetPage) gridApi.pagination.currentPage = 1;
  selectedRepositories.value = [];
  gridApi.clearSelection();
  gridApi.query();
}

function handleOrganizationClick(data: OrganizationTreeNode) {
  selectedOrganizationId.value = data.id;
  reloadRepositories(true);
}

function setTreeExpandAll(value: boolean) {
  treeExpandAll.value = value;
  treeRenderKey.value += 1;
  nextTick(() => {
    organizationTreeRef.value?.setCurrentKey(selectedOrganizationId.value);
  });
}

async function loadParentOptions(excludeId?: string) {
  const tree = await listValidOrganizationParentsApi(excludeId);
  parentOptions.value = flattenOrganizationOptions(tree);
}

async function openCreateOrganization(parent?: OrganizationTreeNode) {
  // 从节点操作新增时，默认把当前节点作为父组织。
  organizationEditingId.value = '';
  organizationDialogTitle.value = parent ? '新增子组织' : '新增组织';
  await loadParentOptions();
  resetOrganizationForm(parent?.id || '');
  organizationDialogVisible.value = true;
}

async function openEditOrganization(row: OrganizationTreeNode) {
  organizationEditingId.value = row.id;
  organizationDialogTitle.value = '编辑组织';
  await loadParentOptions(row.id);
  Object.assign(organizationForm, {
    domain: row.domain,
    group_id: row.group_id,
    mode: row.mode,
    name: row.name,
    parent_id: row.parent_id || '',
    remark: row.remark || '',
    sort: row.sort || 0,
  });
  organizationDialogVisible.value = true;
}

async function submitOrganization() {
  // 空字符串父组织归一成 null，后端按根组织处理。
  const valid = await organizationFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  const payload = {
    ...organizationForm,
    parent_id: organizationForm.parent_id || null,
    remark: organizationForm.remark || null,
  };
  if (organizationEditingId.value) {
    await updateOrganizationApi(organizationEditingId.value, payload);
    ElMessage.success('组织已更新');
  } else {
    await createOrganizationApi(payload);
    ElMessage.success('组织已创建');
  }
  organizationDialogVisible.value = false;
  await loadOrganizations();
  reloadRepositories();
}

async function handleDeleteOrganization(row: OrganizationTreeNode) {
  // 前端先做直接依赖提示，后端仍会做最终约束校验。
  if (row.children?.length) {
    ElMessage.warning('该组织存在子组织，请先调整或删除子组织');
    return;
  }
  if (row.repository_count > 0) {
    ElMessage.warning('该组织下存在代码库，请先迁移或删除代码库');
    return;
  }
  await ElMessageBox.confirm(`确认删除组织「${row.name}」吗？`, '删除组织', {
    cancelButtonText: '取消',
    confirmButtonText: '删除',
    type: 'warning',
  });
  await deleteOrganizationApi(row.id);
  ElMessage.success('组织已删除');
  if (selectedOrganizationId.value === row.id) {
    selectedOrganizationId.value = '';
  }
  await loadOrganizations();
  reloadRepositories(true);
}

function openCreateRepository() {
  // 代码库必须归属到真实组织，未选中组织时不允许创建。
  if (!selectedOrganization.value) {
    ElMessage.warning('请先创建组织，再维护代码库');
    return;
  }
  repositoryEditingId.value = '';
  repositoryDrawerTitle.value = '新增代码库';
  resetRepositoryForm();
  repositoryDrawerVisible.value = true;
}

function openEditRepository(row: RepositoryItem) {
  repositoryEditingId.value = row.id;
  repositoryDrawerTitle.value = '编辑代码库';
  Object.assign(repositoryForm, {
    domain: row.domain,
    mode: row.mode,
    organization_id: row.organization_id,
    project_id: row.project_id,
    project_name: row.project_name,
    project_url: row.project_url || '',
    remark: row.remark || '',
    repo_type: row.repo_type || '',
    responsibility_group_ids: [...(row.responsibility_group_ids || [])],
    sort: row.sort || 0,
  });
  repositoryDrawerVisible.value = true;
}

async function submitRepository() {
  const valid = await repositoryFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  const payload: RepositoryPayload = {
    ...repositoryForm,
    project_url: repositoryForm.project_url || '',
    remark: repositoryForm.remark || null,
  };
  if (repositoryEditingId.value) {
    await updateRepositoryApi(repositoryEditingId.value, payload);
    ElMessage.success('代码库已更新');
  } else {
    await createRepositoryApi(payload);
    ElMessage.success('代码库已创建');
  }
  repositoryDrawerVisible.value = false;
  await loadOrganizations();
  reloadRepositories();
}

async function handleDeleteRepository(row: RepositoryItem) {
  await ElMessageBox.confirm(
    `确认删除代码库「${row.project_name}」吗？关联的分支绑定会同步解除。`,
    '删除代码库',
    {
      cancelButtonText: '取消',
      confirmButtonText: '删除',
      type: 'warning',
    },
  );
  await deleteRepositoryApi(row.id);
  ElMessage.success('代码库已删除');
  await loadOrganizations();
  reloadRepositories();
}

function handleSelectionChange(rows: RepositoryItem[]) {
  selectedRepositories.value = rows;
}

async function openBindBranches() {
  // 绑定从当前表格勾选的代码库出发，弹窗中只选择目标分支。
  if (!selectedRepositories.value.length) {
    ElMessage.warning('请先选择要绑定分支的代码库');
    return;
  }
  bindForm.branch_ids = [];
  bindForm.mode = 'append';
  const result = await listBranchesApi({ page: 1, pageSize: 1000 });
  branchOptions.value = result.items || [];
  bindDialogVisible.value = true;
}

async function submitBindBranches() {
  // append 只追加缺失绑定，replace 会以弹窗选择结果替换所选代码库绑定。
  if (!bindForm.branch_ids.length) {
    ElMessage.warning('请选择要绑定的分支');
    return;
  }
  bindLoading.value = true;
  try {
    const result = await bindBranchesToRepositoriesApi({
      branch_ids: bindForm.branch_ids,
      mode: bindForm.mode,
      repository_ids: selectedRepositories.value.map((item) => item.id),
    });
    ElMessage.success(
      `绑定完成：新增${result.created_count}，恢复${result.restored_count}，移除${result.removed_count}`,
    );
    bindDialogVisible.value = false;
    reloadRepositories();
  } finally {
    bindLoading.value = false;
  }
}

function saveBlob(data: any, filename: string) {
  // 下载接口返回 blob，手动创建临时链接触发浏览器保存。
  const blob = data instanceof Blob ? data : new Blob([data]);
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function showImportResult(result: ImportResult) {
  // 成功行给 toast；存在错误行时用弹窗展示前几条，避免通知内容被截断。
  const summary = `新增${result.created_count}条，更新${result.updated_count}条，忽略${result.ignored_count}条`;
  if (!result.errors.length) {
    ElMessage.success(`导入完成：${summary}`);
    return;
  }
  const details = result.errors
    .slice(0, 8)
    .map((item) => `第${item.row_no}行：${item.message}`)
    .join('\n');
  ElMessageBox.alert(`${summary}\n\n失败明细：\n${details}`, '导入完成', {
    confirmButtonText: '知道了',
    type: 'warning',
  });
}

async function handleOrganizationImport(options: UploadRequestOptions) {
  if (importing.value) return;
  importing.value = true;
  try {
    const result = await importOrganizationsApi(options.file);
    showImportResult(result);
    await loadOrganizations();
    reloadRepositories();
  } finally {
    importing.value = false;
  }
}

async function handleRepositoryImport(options: UploadRequestOptions) {
  if (importing.value) return;
  importing.value = true;
  try {
    const result = await importRepositoriesApi(options.file);
    showImportResult(result);
    await loadOrganizations();
    reloadRepositories();
  } finally {
    importing.value = false;
  }
}

async function downloadOrganizationTemplate() {
  const data = await downloadOrganizationTemplateApi();
  saveBlob(data, 'code_compliance_organization_template.xlsx');
}

async function downloadRepositoryTemplate() {
  const data = await downloadRepositoryTemplateApi();
  saveBlob(data, 'code_compliance_repository_template.xlsx');
}

function formatGroupNames(row: RepositoryItem) {
  return row.responsibility_group_names?.length
    ? row.responsibility_group_names.join('、')
    : '-';
}

onMounted(async () => {
  await Promise.all([loadOptions(), loadOrganizations()]);
  await gridApi.query();
  pageLoading.value = false;
});
</script>

<template>
  <Page auto-content-height>
    <ElSkeleton :loading="pageLoading" animated>
      <template #template>
        <div class="flex h-full gap-3">
          <div class="w-[320px] rounded bg-[var(--el-bg-color)] p-3">
            <ElSkeletonItem variant="rect" class="mb-3 h-8 w-full" />
            <ElSkeletonItem
              v-for="item in 10"
              :key="item"
              variant="text"
              class="mb-2 h-7 w-full"
            />
          </div>
          <div class="min-w-0 flex-1 rounded bg-[var(--el-bg-color)] p-3">
            <ElSkeletonItem variant="rect" class="mb-4 h-12 w-full" />
            <ElSkeletonItem
              v-for="item in 10"
              :key="item"
              variant="rect"
              class="mb-2 h-9 w-full"
            />
          </div>
        </div>
      </template>

      <template #default>
        <div class="flex h-full min-h-0 gap-3">
          <aside
            class="repository-sidebar flex shrink-0 flex-col rounded border border-[var(--el-border-color-light)] bg-[var(--el-bg-color)]"
          >
            <div class="border-b border-[var(--el-border-color-light)] p-3">
              <div class="mb-3 flex items-center justify-between gap-2">
                <div class="text-sm font-semibold">组织树</div>
                <div class="flex items-center gap-1">
                  <ElTooltip content="新增根组织" placement="top">
                    <ElButton
                      circle
                      size="small"
                      type="primary"
                      @click="openCreateOrganization()"
                    >
                      <Plus class="size-4" />
                    </ElButton>
                  </ElTooltip>
                  <ElButton size="small" @click="setTreeExpandAll(true)">
                    展开
                  </ElButton>
                  <ElButton size="small" @click="setTreeExpandAll(false)">
                    收起
                  </ElButton>
                </div>
              </div>
              <ElInput
                v-model="organizationKeyword"
                clearable
                placeholder="搜索组织名或组织ID"
                :prefix-icon="Search"
              />
            </div>

            <div
              class="min-h-0 flex-1 overflow-auto p-2"
              v-loading="treeLoading"
            >
              <ElTree
                :key="treeRenderKey"
                ref="organizationTreeRef"
                :data="filteredOrganizationTree"
                :default-expand-all="treeExpandAll"
                :expand-on-click-node="false"
                highlight-current
                node-key="id"
                :props="{ children: 'children', label: 'name' }"
                @node-click="handleOrganizationClick"
              >
                <template #default="{ data }">
                  <div class="org-tree-node">
                    <div class="flex min-w-0 items-center gap-2">
                      <span class="truncate text-sm" :title="data.name">
                        {{ data.name }}
                      </span>
                      <ElTag size="small" round>
                        {{ data.repository_count }}
                      </ElTag>
                    </div>
                    <div class="org-tree-actions" @click.stop>
                      <ElTooltip content="新增子组织" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="primary"
                          @click="openCreateOrganization(data)"
                        >
                          <Plus class="size-3.5" />
                        </ElButton>
                      </ElTooltip>
                      <ElTooltip content="编辑组织" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="primary"
                          @click="openEditOrganization(data)"
                        >
                          <Edit class="size-3.5" />
                        </ElButton>
                      </ElTooltip>
                      <ElTooltip content="删除组织" placement="top">
                        <ElButton
                          circle
                          link
                          size="small"
                          type="danger"
                          @click="handleDeleteOrganization(data)"
                        >
                          <Trash2 class="size-3.5" />
                        </ElButton>
                      </ElTooltip>
                    </div>
                  </div>
                </template>
              </ElTree>
            </div>
          </aside>

          <section
            class="flex min-w-0 flex-1 flex-col rounded border border-[var(--el-border-color-light)] bg-[var(--el-bg-color)]"
          >
            <div class="border-b border-[var(--el-border-color-light)] p-3">
              <div class="flex flex-wrap items-center gap-3">
                <div class="min-w-0 flex-1">
                  <div
                    class="truncate text-sm font-semibold"
                    :title="selectedOrganizationPath"
                  >
                    {{ selectedOrganizationPath }}
                  </div>
                  <div
                    class="mt-1 flex flex-wrap items-center gap-2 text-xs text-[var(--el-text-color-secondary)]"
                  >
                    <span>
                      {{
                        selectedOrganization
                          ? `组织ID：${selectedOrganization.group_id}`
                          : '暂无组织，请先新增组织'
                      }}
                    </span>
                    <span v-if="selectedOrganization">
                      {{ selectedOrganization.mode_label }} /
                      {{ selectedOrganization.domain_label }}
                    </span>
                    <span>当前列表 {{ repositoryTotal }} 个代码库</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="min-h-0 flex-1 p-3">
              <Grid class="h-full" @selection-change="handleSelectionChange">
                <template #toolbar-actions>
                  <div class="toolbar-stack">
                    <!-- 工具栏拆成筛选区和操作区，避免窄屏下输入框挤压按钮。 -->
                    <div class="toolbar-row">
                      <ElInput
                        v-model="repositoryKeyword"
                        class="toolbar-keyword"
                        clearable
                        placeholder="搜索代码库名/ID/URL"
                        :prefix-icon="Search"
                        @clear="reloadRepositories(true)"
                        @keyup.enter="reloadRepositories(true)"
                      />
                      <ElSelect
                        v-model="selectedMode"
                        class="toolbar-select-sm"
                        clearable
                        placeholder="模式"
                        @change="reloadRepositories(true)"
                        @clear="reloadRepositories(true)"
                      >
                        <ElOption
                          v-for="item in MODE_OPTIONS"
                          :key="item.value"
                          :label="item.label"
                          :value="item.value"
                        />
                      </ElSelect>
                      <ElSelect
                        v-model="selectedDomain"
                        class="toolbar-select-sm"
                        clearable
                        placeholder="领域"
                        @change="reloadRepositories(true)"
                        @clear="reloadRepositories(true)"
                      >
                        <ElOption
                          v-for="item in DOMAIN_OPTIONS"
                          :key="item.value"
                          :label="item.label"
                          :value="item.value"
                        />
                      </ElSelect>
                      <ElSelect
                        v-model="selectedRepoType"
                        class="toolbar-select-md"
                        clearable
                        placeholder="仓库类型"
                        @change="reloadRepositories(true)"
                        @clear="reloadRepositories(true)"
                      >
                        <ElOption
                          v-for="item in repoTypeOptions"
                          :key="item.id"
                          :label="item.label || item.value"
                          :value="item.value || ''"
                        />
                      </ElSelect>
                      <ElButton @click="reloadRepositories(true)"
                        >查询</ElButton
                      >
                    </div>
                    <div class="toolbar-row toolbar-row-actions">
                      <ElButton
                        type="primary"
                        plain
                        :disabled="selectedRepositories.length === 0"
                        @click="openBindBranches"
                      >
                        绑定分支
                      </ElButton>
                      <ElButton @click="downloadOrganizationTemplate">
                        组织模板
                      </ElButton>
                      <ElUpload
                        action="#"
                        accept=".xlsx"
                        :disabled="importing"
                        :http-request="handleOrganizationImport"
                        :show-file-list="false"
                      >
                        <ElButton :loading="importing">
                          <Upload class="mr-1 size-4" /> 组织导入
                        </ElButton>
                      </ElUpload>
                      <ElButton @click="downloadRepositoryTemplate">
                        仓库模板
                      </ElButton>
                      <ElUpload
                        action="#"
                        accept=".xlsx"
                        :disabled="importing"
                        :http-request="handleRepositoryImport"
                        :show-file-list="false"
                      >
                        <ElButton type="success" :loading="importing">
                          <Upload class="mr-1 size-4" /> 仓库导入
                        </ElButton>
                      </ElUpload>
                      <ElButton type="primary" @click="openCreateRepository">
                        <Plus class="mr-1 size-4" /> 新增代码库
                      </ElButton>
                    </div>
                  </div>
                </template>

                <template #cell-project_name="{ row }">
                  <div class="flex min-w-0 items-center gap-2 text-left">
                    <span
                      class="inline-flex size-7 shrink-0 items-center justify-center rounded bg-[var(--el-fill-color-light)] text-xs font-semibold text-[var(--el-color-primary)]"
                    >
                      R
                    </span>
                    <div class="min-w-0">
                      <div
                        class="truncate font-medium"
                        :title="row.project_name"
                      >
                        {{ row.project_name }}
                      </div>
                      <div
                        class="truncate text-xs text-[var(--el-text-color-secondary)]"
                      >
                        {{ row.project_id }}
                      </div>
                    </div>
                  </div>
                </template>

                <template #cell-responsibility_group_names="{ row }">
                  <span class="line-clamp-2 text-left">
                    {{ formatGroupNames(row) }}
                  </span>
                </template>

                <template #cell-branch_count="{ row }">
                  <ElTag type="info" round>{{ row.branch_count }}</ElTag>
                </template>

                <template #cell-project_url="{ row }">
                  <ElLink
                    v-if="row.project_url"
                    :href="row.project_url"
                    target="_blank"
                    type="primary"
                    class="max-w-full"
                  >
                    <span class="truncate">{{ row.project_url }}</span>
                  </ElLink>
                  <span v-else>-</span>
                </template>

                <template #cell-actions="{ row }">
                  <div class="flex items-center justify-center gap-1">
                    <ElButton
                      link
                      type="primary"
                      @click="openEditRepository(row)"
                    >
                      编辑
                    </ElButton>
                    <ElButton
                      link
                      type="danger"
                      @click="handleDeleteRepository(row)"
                    >
                      删除
                    </ElButton>
                  </div>
                </template>
              </Grid>
            </div>
          </section>
        </div>
      </template>
    </ElSkeleton>

    <ElDialog
      v-model="organizationDialogVisible"
      :title="organizationDialogTitle"
      width="520px"
      destroy-on-close
    >
      <ElForm
        ref="organizationFormRef"
        label-width="96px"
        :model="organizationForm"
        :rules="organizationRules"
      >
        <ElFormItem label="组织ID" prop="group_id">
          <ElInput
            v-model="organizationForm.group_id"
            placeholder="公司代码库系统组织ID"
          />
        </ElFormItem>
        <ElFormItem label="组织名" prop="name">
          <ElInput v-model="organizationForm.name" placeholder="请输入组织名" />
        </ElFormItem>
        <ElFormItem label="父组织">
          <ElSelect
            v-model="organizationForm.parent_id"
            class="w-full"
            clearable
            filterable
            placeholder="不选择则为根组织"
          >
            <ElOption
              v-for="item in parentOptions"
              :key="item.id"
              :label="item.label"
              :value="item.id"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="模式" prop="mode">
          <ElRadioGroup v-model="organizationForm.mode">
            <ElRadioButton
              v-for="item in MODE_OPTIONS"
              :key="item.value"
              :label="item.value"
            >
              {{ item.label }}
            </ElRadioButton>
          </ElRadioGroup>
        </ElFormItem>
        <ElFormItem label="领域" prop="domain">
          <ElSelect v-model="organizationForm.domain" class="w-full">
            <ElOption
              v-for="item in DOMAIN_OPTIONS"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="排序">
          <ElInputNumber
            v-model="organizationForm.sort"
            class="w-full"
            :min="0"
            controls-position="right"
          />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput
            v-model="organizationForm.remark"
            :rows="3"
            type="textarea"
            placeholder="补充组织维护说明"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="organizationDialogVisible = false">取消</ElButton>
        <ElButton type="primary" @click="submitOrganization">确定</ElButton>
      </template>
    </ElDialog>

    <ElDrawer
      v-model="repositoryDrawerVisible"
      :title="repositoryDrawerTitle"
      size="560px"
      destroy-on-close
    >
      <ElForm
        ref="repositoryFormRef"
        label-width="116px"
        :model="repositoryForm"
        :rules="repositoryRules"
      >
        <ElFormItem label="代码库ID" prop="project_id">
          <ElInput
            v-model="repositoryForm.project_id"
            placeholder="公司代码库系统 project_id"
          />
        </ElFormItem>
        <ElFormItem label="代码库名" prop="project_name">
          <ElInput
            v-model="repositoryForm.project_name"
            placeholder="请输入代码库名"
          />
        </ElFormItem>
        <ElFormItem label="代码库URL">
          <ElInput
            v-model="repositoryForm.project_url"
            placeholder="请输入代码库 URL"
          />
        </ElFormItem>
        <ElFormItem label="所属组织" prop="organization_id">
          <ElSelect
            v-model="repositoryForm.organization_id"
            class="w-full"
            filterable
            placeholder="请选择所属组织"
          >
            <ElOption
              v-for="item in organizationOptions"
              :key="item.id"
              :label="item.label"
              :value="item.id"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="模式" prop="mode">
          <ElRadioGroup v-model="repositoryForm.mode">
            <ElRadioButton
              v-for="item in MODE_OPTIONS"
              :key="item.value"
              :label="item.value"
            >
              {{ item.label }}
            </ElRadioButton>
          </ElRadioGroup>
        </ElFormItem>
        <ElFormItem label="领域" prop="domain">
          <ElSelect v-model="repositoryForm.domain" class="w-full">
            <ElOption
              v-for="item in DOMAIN_OPTIONS"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="代码仓类型">
          <ElSelect
            v-model="repositoryForm.repo_type"
            class="w-full"
            clearable
            filterable
            placeholder="来自系统字典 code_compliance_repo_type"
          >
            <ElOption
              v-for="item in repoTypeOptions"
              :key="item.id"
              :label="item.label || item.value"
              :value="item.value || ''"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="责任PL组">
          <ElSelect
            v-model="repositoryForm.responsibility_group_ids"
            class="w-full"
            collapse-tags
            collapse-tags-tooltip
            filterable
            multiple
            placeholder="可多选责任PL资源组"
          >
            <ElOption
              v-for="item in plGroupOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="排序">
          <ElInputNumber
            v-model="repositoryForm.sort"
            class="w-full"
            :min="0"
            controls-position="right"
          />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput
            v-model="repositoryForm.remark"
            :rows="4"
            type="textarea"
            placeholder="补充代码库维护说明"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="repositoryDrawerVisible = false">取消</ElButton>
        <ElButton type="primary" @click="submitRepository">保存</ElButton>
      </template>
    </ElDrawer>

    <ElDialog
      v-model="bindDialogVisible"
      title="批量绑定分支"
      width="520px"
      destroy-on-close
    >
      <ElForm label-width="92px">
        <ElFormItem label="绑定方式">
          <ElRadioGroup v-model="bindForm.mode">
            <ElRadioButton
              v-for="item in BIND_MODE_OPTIONS"
              :key="item.value"
              :label="item.value"
            >
              {{ item.label }}
            </ElRadioButton>
          </ElRadioGroup>
        </ElFormItem>
        <ElFormItem label="分支">
          <ElSelect
            v-model="bindForm.branch_ids"
            class="w-full"
            collapse-tags
            collapse-tags-tooltip
            filterable
            multiple
            placeholder="选择要绑定的分支"
          >
            <ElOption
              v-for="item in branchOptions"
              :key="item.id"
              :label="`${item.branch_name}（${item.domain_label}）`"
              :value="item.id"
            />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="bindDialogVisible = false">取消</ElButton>
        <ElButton
          type="primary"
          :loading="bindLoading"
          @click="submitBindBranches"
        >
          确定绑定
        </ElButton>
      </template>
    </ElDialog>
  </Page>
</template>

<style scoped lang="less">
.repository-sidebar {
  // 原生 resize 只在 overflow 非 visible 时生效，内部树区域继续负责滚动。
  width: 320px;
  min-width: 260px;
  max-width: 520px;
  overflow: hidden;
  resize: horizontal;
}

.toolbar-stack {
  flex: 1;
  width: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toolbar-row {
  // 筛选条件独占一行且允许换行，避免输入框和按钮横向互相挤压。
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  width: 100%;
  min-width: 0;
  gap: 8px;
}

.toolbar-row-actions {
  justify-content: flex-end;
}

.toolbar-keyword {
  width: 260px;
  max-width: 100%;
}

.toolbar-select-sm {
  width: 120px;
}

.toolbar-select-md {
  width: 160px;
}

.org-tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  width: 100%;
  gap: 8px;
  padding-right: 6px;
}

.org-tree-actions {
  display: none;
  align-items: center;
  flex-shrink: 0;
  gap: 1px;
}

:deep(.el-tree-node__content) {
  height: 34px;
  border-radius: 6px;
  margin-bottom: 3px;
}

:deep(.el-tree-node__content:hover) {
  background-color: var(--el-fill-color-light);

  .org-tree-actions {
    display: inline-flex;
  }
}

:deep(.el-tree-node.is-current > .el-tree-node__content) {
  color: var(--el-color-primary);
  background-color: var(--el-color-primary-light-9);
}

:deep(.el-tree-node.is-current > .el-tree-node__content .org-tree-actions) {
  display: inline-flex;
}

@media (max-width: 768px) {
  .repository-sidebar {
    width: 280px;
    min-width: 240px;
  }

  .toolbar-keyword,
  .toolbar-select-md,
  .toolbar-select-sm {
    width: 100%;
  }

  .toolbar-row-actions {
    justify-content: flex-start;
  }
}
</style>
