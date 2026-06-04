<script lang="ts" setup>
import type {
  BranchItem,
  BranchPayload,
  ComplianceBindMode,
  ComplianceBranchType,
  ComplianceDomain,
  ImportResult,
  RepositoryItem,
} from '#/api/compliance/base';
import type {
  FormInstance,
  FormRules,
  UploadRequestOptions,
} from 'element-plus';

import { onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { Plus, Search, Upload } from '@vben/icons';

import {
  ElButton,
  ElDatePicker,
  ElDialog,
  ElDrawer,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElRadioButton,
  ElRadioGroup,
  ElSelect,
  ElTag,
  ElUpload,
} from 'element-plus';

import {
  bindRepositoriesToBranchesApi,
  createBranchApi,
  deleteBranchApi,
  downloadBranchTemplateApi,
  importBranchesApi,
  listBranchesApi,
  listRepositoriesApi,
  updateBranchApi,
} from '#/api/compliance/base';
import { useZqTable } from '#/components/zq-table';

import {
  BIND_MODE_OPTIONS,
  BRANCH_TYPE_OPTIONS,
  DOMAIN_OPTIONS,
  useBranchColumns,
} from './data';

defineOptions({ name: 'ComplianceBranch' });

interface BranchFormState extends BranchPayload {
  alias: string;
  created_date: null | string;
  purpose: string;
  remark: string;
}

const branchFormRef = ref<FormInstance>();
const keyword = ref('');
const selectedDomain = ref('');
const selectedBranchType = ref('');
const selectedBranches = ref<BranchItem[]>([]);
const repositoryOptions = ref<RepositoryItem[]>([]);

const drawerVisible = ref(false);
const drawerTitle = ref('新增分支');
const editingId = ref('');
const importing = ref(false);
const bindDialogVisible = ref(false);
const bindLoading = ref(false);

const branchForm = reactive<BranchFormState>({
  alias: '',
  branch_name: '',
  branch_type: 'development',
  created_date: null,
  domain: 'cockpit',
  purpose: '',
  remark: '',
  sort: 0,
});

const bindForm = reactive<{
  mode: ComplianceBindMode;
  repository_ids: string[];
}>({
  mode: 'append',
  repository_ids: [],
});

const branchRules: FormRules<BranchFormState> = {
  branch_name: [
    { message: '请输入分支名称', required: true, trigger: 'blur' },
  ],
  branch_type: [
    { message: '请选择分支类型', required: true, trigger: 'change' },
  ],
  domain: [{ message: '请选择领域', required: true, trigger: 'change' }],
};

const [Grid, gridApi] = useZqTable<BranchItem>({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    border: true,
    columns: useBranchColumns(),
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [10, 20, 50, 100],
    },
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: ({
          page,
        }: {
          page: { currentPage: number; pageSize: number };
        }) => {
          return listBranchesApi({
            branch_type:
              (selectedBranchType.value as ComplianceBranchType) || undefined,
            domain: (selectedDomain.value as ComplianceDomain) || undefined,
            keyword: keyword.value || undefined,
            page: page.currentPage,
            pageSize: page.pageSize,
          });
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

function reloadBranches(resetPage = false) {
  // 刷新分支列表时清空选择，避免批量绑定操作使用旧勾选。
  if (resetPage) gridApi.pagination.currentPage = 1;
  selectedBranches.value = [];
  gridApi.clearSelection();
  gridApi.query();
}

function resetForm() {
  Object.assign(branchForm, {
    alias: '',
    branch_name: '',
    branch_type: 'development',
    created_date: null,
    domain: 'cockpit',
    purpose: '',
    remark: '',
    sort: 0,
  });
  branchFormRef.value?.clearValidate();
}

function openCreate() {
  editingId.value = '';
  drawerTitle.value = '新增分支';
  resetForm();
  drawerVisible.value = true;
}

function openEdit(row: BranchItem) {
  editingId.value = row.id;
  drawerTitle.value = '编辑分支';
  Object.assign(branchForm, {
    alias: row.alias || '',
    branch_name: row.branch_name,
    branch_type: row.branch_type,
    created_date: row.created_date || null,
    domain: row.domain,
    purpose: row.purpose || '',
    remark: row.remark || '',
    sort: row.sort || 0,
  });
  drawerVisible.value = true;
}

async function submitBranch() {
  // 日期为空时传 null，后端会保留为未设置创建日期。
  const valid = await branchFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  const payload: BranchPayload = {
    ...branchForm,
    created_date: branchForm.created_date || null,
    remark: branchForm.remark || null,
  };
  if (editingId.value) {
    await updateBranchApi(editingId.value, payload);
    ElMessage.success('分支已更新');
  } else {
    await createBranchApi(payload);
    ElMessage.success('分支已创建');
  }
  drawerVisible.value = false;
  reloadBranches();
}

async function handleDelete(row: BranchItem) {
  await ElMessageBox.confirm(
    `确认删除分支「${row.branch_name}」吗？关联的代码库绑定会同步解除。`,
    '删除分支',
    {
      cancelButtonText: '取消',
      confirmButtonText: '删除',
      type: 'warning',
    },
  );
  await deleteBranchApi(row.id);
  ElMessage.success('分支已删除');
  reloadBranches();
}

function handleSelectionChange(rows: BranchItem[]) {
  selectedBranches.value = rows;
}

async function openBindRepositories() {
  // 从分支侧绑定时，弹窗里只选择目标代码库和绑定模式。
  if (!selectedBranches.value.length) {
    ElMessage.warning('请先选择要绑定代码库的分支');
    return;
  }
  bindForm.mode = 'append';
  bindForm.repository_ids = [];
  const result = await listRepositoriesApi({ page: 1, pageSize: 1000 });
  repositoryOptions.value = result.items || [];
  bindDialogVisible.value = true;
}

async function submitBindRepositories() {
  // append 只追加缺失绑定，replace 会以弹窗选择结果替换所选分支绑定。
  if (!bindForm.repository_ids.length) {
    ElMessage.warning('请选择要绑定的代码库');
    return;
  }
  bindLoading.value = true;
  try {
    const result = await bindRepositoriesToBranchesApi({
      branch_ids: selectedBranches.value.map((item) => item.id),
      mode: bindForm.mode,
      repository_ids: bindForm.repository_ids,
    });
    ElMessage.success(
      `绑定完成：新增${result.created_count}，恢复${result.restored_count}，移除${result.removed_count}`,
    );
    bindDialogVisible.value = false;
    reloadBranches();
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

async function handleImport(options: UploadRequestOptions) {
  if (importing.value) return;
  importing.value = true;
  try {
    const result = await importBranchesApi(options.file);
    showImportResult(result);
    reloadBranches(true);
  } finally {
    importing.value = false;
  }
}

async function downloadTemplate() {
  const data = await downloadBranchTemplateApi();
  saveBlob(data, 'code_compliance_branch_template.xlsx');
}

onMounted(() => {
  gridApi.query();
});
</script>

<template>
  <Page title="分支管理" auto-content-height>
    <div
      class="flex h-full min-h-0 flex-col rounded border border-[var(--el-border-color-light)] bg-[var(--el-bg-color)] p-3"
    >
      <Grid class="h-full" @selection-change="handleSelectionChange">
        <template #toolbar-actions>
          <div class="flex flex-1 flex-wrap items-center gap-2">
            <ElInput
              v-model="keyword"
              class="w-[240px]"
              clearable
              placeholder="搜索分支名/别名/用途"
              :prefix-icon="Search"
              @clear="reloadBranches(true)"
              @keyup.enter="reloadBranches(true)"
            />
            <ElSelect
              v-model="selectedBranchType"
              class="w-[130px]"
              clearable
              placeholder="分支类型"
              @change="reloadBranches(true)"
              @clear="reloadBranches(true)"
            >
              <ElOption
                v-for="item in BRANCH_TYPE_OPTIONS"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </ElSelect>
            <ElSelect
              v-model="selectedDomain"
              class="w-[120px]"
              clearable
              placeholder="领域"
              @change="reloadBranches(true)"
              @clear="reloadBranches(true)"
            >
              <ElOption
                v-for="item in DOMAIN_OPTIONS"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </ElSelect>
            <ElButton @click="reloadBranches(true)">查询</ElButton>
            <div class="flex-1"></div>
            <ElButton
              type="primary"
              plain
              :disabled="selectedBranches.length === 0"
              @click="openBindRepositories"
            >
              绑定代码库
            </ElButton>
            <ElButton @click="downloadTemplate">下载模板</ElButton>
            <ElUpload
              action="#"
              accept=".xlsx"
              :disabled="importing"
              :http-request="handleImport"
              :show-file-list="false"
            >
              <ElButton type="success" :loading="importing">
                <Upload class="mr-1 size-4" /> 批量导入
              </ElButton>
            </ElUpload>
            <ElButton type="primary" @click="openCreate">
              <Plus class="mr-1 size-4" /> 新增分支
            </ElButton>
          </div>
        </template>

        <template #cell-branch_name="{ row }">
          <div class="flex min-w-0 items-center gap-2 text-left">
            <span
              class="inline-flex size-7 shrink-0 items-center justify-center rounded bg-[var(--el-fill-color-light)] text-xs font-semibold text-[var(--el-color-primary)]"
            >
              B
            </span>
            <div class="min-w-0">
              <div class="truncate font-medium" :title="row.branch_name">
                {{ row.branch_name }}
              </div>
              <div class="truncate text-xs text-[var(--el-text-color-secondary)]">
                {{ row.alias || '-' }}
              </div>
            </div>
          </div>
        </template>

        <template #cell-purpose="{ row }">
          <span class="line-clamp-2 text-left">{{ row.purpose || '-' }}</span>
        </template>

        <template #cell-repository_count="{ row }">
          <ElTag type="info" round>{{ row.repository_count }}</ElTag>
        </template>

        <template #cell-actions="{ row }">
          <div class="flex items-center justify-center gap-1">
            <ElButton link type="primary" @click="openEdit(row)">编辑</ElButton>
            <ElButton link type="danger" @click="handleDelete(row)">删除</ElButton>
          </div>
        </template>
      </Grid>
    </div>

    <ElDrawer
      v-model="drawerVisible"
      :title="drawerTitle"
      size="520px"
      destroy-on-close
    >
      <ElForm
        ref="branchFormRef"
        label-width="104px"
        :model="branchForm"
        :rules="branchRules"
      >
        <ElFormItem label="分支名称" prop="branch_name">
          <ElInput v-model="branchForm.branch_name" placeholder="请输入分支名称" />
        </ElFormItem>
        <ElFormItem label="创建日期">
          <ElDatePicker
            v-model="branchForm.created_date"
            class="w-full"
            placeholder="选择创建日期"
            type="date"
            value-format="YYYY-MM-DD"
          />
        </ElFormItem>
        <ElFormItem label="分支类型" prop="branch_type">
          <ElSelect v-model="branchForm.branch_type" class="w-full">
            <ElOption
              v-for="item in BRANCH_TYPE_OPTIONS"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="领域" prop="domain">
          <ElSelect v-model="branchForm.domain" class="w-full">
            <ElOption
              v-for="item in DOMAIN_OPTIONS"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="分支别名">
          <ElInput v-model="branchForm.alias" placeholder="请输入分支别名" />
        </ElFormItem>
        <ElFormItem label="排序">
          <ElInputNumber
            v-model="branchForm.sort"
            class="w-full"
            :min="0"
            controls-position="right"
          />
        </ElFormItem>
        <ElFormItem label="分支用途">
          <ElInput
            v-model="branchForm.purpose"
            :rows="4"
            type="textarea"
            placeholder="描述分支用途"
          />
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput
            v-model="branchForm.remark"
            :rows="3"
            type="textarea"
            placeholder="补充分支维护说明"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="drawerVisible = false">取消</ElButton>
        <ElButton type="primary" @click="submitBranch">保存</ElButton>
      </template>
    </ElDrawer>

    <ElDialog
      v-model="bindDialogVisible"
      title="批量绑定代码库"
      width="560px"
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
        <ElFormItem label="代码库">
          <ElSelect
            v-model="bindForm.repository_ids"
            class="w-full"
            collapse-tags
            collapse-tags-tooltip
            filterable
            multiple
            placeholder="选择要绑定的代码库"
          >
            <ElOption
              v-for="item in repositoryOptions"
              :key="item.id"
              :label="`${item.project_name}（${item.organization_name}）`"
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
          @click="submitBindRepositories"
        >
          确定绑定
        </ElButton>
      </template>
    </ElDialog>
  </Page>
</template>
