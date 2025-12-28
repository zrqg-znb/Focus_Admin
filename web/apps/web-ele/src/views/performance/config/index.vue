<script lang="ts" setup>
import { ref, onMounted, reactive, computed } from 'vue';
import { Page } from '@vben/common-ui';
import { useUserStore } from '@vben/stores';
import { ElButton, ElTable, ElTableColumn, ElPagination, ElMessage, ElDialog, ElForm, ElFormItem, ElInput, ElSelect, ElOption, ElInputNumber, ElUpload, ElLink } from 'element-plus';
import { getIndicatorListApi, createIndicatorApi, updateIndicatorApi, deleteIndicatorApi, importIndicatorsApi, type PerformanceIndicator } from '#/api/core/performance';
import { getSimpleUserListApi, searchUserApi } from '#/api/core/user';

defineOptions({ name: 'PerformanceConfig' });

const userStore = useUserStore();
const currentUserId = computed(() => userStore.userInfo?.id);
const isSuperuser = computed(() => userStore.userInfo?.is_superuser || userStore.userInfo?.username === 'admin');

const loading = ref(false);
const tableData = ref<PerformanceIndicator[]>([]);
const total = ref(0);
const queryParams = reactive({
  page: 1,
  pageSize: 10,
  search: '',
  module: '',
  chip_type: '',
  project: ''
});

const dialogVisible = ref(false);
const dialogTitle = ref('新增指标');
const formRef = ref();
const formData = reactive<Partial<PerformanceIndicator>>({
  code: '',
  name: '',
  module: '',
  project: '',
  chip_type: '',
  value_type: 'avg',
  baseline_value: 0,
  baseline_unit: '',
  fluctuation_range: 0,
  fluctuation_direction: 'none',
  owner_id: ''
});

const importDialogVisible = ref(false);
const userOptions = ref<any[]>([]);
const userLoading = ref(false);

const rules = {
  name: [{ required: true, message: '请输入指标名称', trigger: 'blur' }],
  module: [{ required: true, message: '请输入所属模块', trigger: 'blur' }],
  project: [{ required: true, message: '请输入所属项目', trigger: 'blur' }],
  chip_type: [{ required: true, message: '请输入芯片类型', trigger: 'blur' }],
  baseline_value: [{ required: true, message: '请输入基线值', trigger: 'blur' }],
};

async function loadData() {
  loading.value = true;
  try {
    const res = await getIndicatorListApi(queryParams);
    tableData.value = res.items;
    total.value = res.total;
  } finally {
    loading.value = false;
  }
}

async function searchUsers(query: string) {
    if (!query) {
        // userOptions.value = []; // Don't clear options to keep previous selection visible if needed
        return;
    }

    // Check if query meets the minimum length requirements
    // At least 1 Chinese character OR at least 5 English letters
    const hasChinese = /[\u4e00-\u9fa5]/.test(query);
    if (!hasChinese && query.length < 5) {
        return; // Do not trigger search
    }

    userLoading.value = true;
    try {
        const res = await searchUserApi(query);
        userOptions.value = res.items || res; // 兼容分页响应或直接列表
    } finally {
        userLoading.value = false;
    }
}

// Initial load of users (optional, or load on focus)
async function loadAllUsers() {
    const res = await getSimpleUserListApi();
    userOptions.value = res;
}

function handleAdd() {
  dialogTitle.value = '新增指标';
  Object.assign(formData, {
    id: undefined,
    code: '',
    name: '',
    module: '',
    project: '',
    chip_type: '',
    value_type: 'avg',
    baseline_value: 0,
    baseline_unit: '',
    fluctuation_range: 0,
    fluctuation_direction: 'none',
    owner_id: ''
  });
  dialogVisible.value = true;
  loadAllUsers(); // Preload users for better UX
}

// Ensure options are loaded when editing to show the current owner correctly
function handleEdit(row: PerformanceIndicator) {
  dialogTitle.value = '编辑指标';
  Object.assign(formData, row);
  if (!formData.owner_id && (row as any).owner) {
     formData.owner_id = (row as any).owner.id;
  }

  // If owner_id is present, make sure it's in the options or load all options
  // Ideally, we should add the current owner to options if not present, but loading all is simpler for small datasets.
  // Or fetch the specific user details if list is large.
  // For now, loadAllUsers() covers it.

  dialogVisible.value = true;
  loadAllUsers();
}

async function handleDelete(row: PerformanceIndicator) {
  try {
    await deleteIndicatorApi(row.id);
    ElMessage.success('删除成功');
    loadData();
  } catch (error) {
    // Error handled by interceptor usually
  }
}

async function handleSubmit() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid: boolean) => {
    if (valid) {
      try {
        if (formData.id) {
          await updateIndicatorApi(formData.id, formData);
        } else {
          await createIndicatorApi(formData);
        }
        ElMessage.success('保存成功');
        dialogVisible.value = false;
        loadData();
      } catch (error) {
        console.error(error);
      }
    }
  });
}

async function handleImportRequest(options: any) {
  try {
    await importIndicatorsApi(options.file);
    ElMessage.success('导入成功');
    importDialogVisible.value = false;
    loadData();
  } catch (error) {
    ElMessage.error('导入失败');
  }
}

function canEdit(row: PerformanceIndicator) {
    // Permission check: Owner or Superuser
    if (isSuperuser.value) return true;
    return row.owner_id === currentUserId.value;
}

function downloadTemplate() {
    const csvContent = "Code,Name,Module,Project,Chip Type,Value Type,Baseline Value,Baseline Unit,Fluctuation Range,Fluctuation Direction,Owner\nTEST_001,示例指标1,load,ProjA,ChipA,avg,100,ms,10,down,UserA";
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", "performance_indicator_template.csv");
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

onMounted(() => {
  loadData();
});
</script>

<template>
  <Page auto-content-height>
    <div class="p-4">
      <div class="mb-4 flex justify-between">
        <div class="flex gap-2">
          <ElInput v-model="queryParams.search" placeholder="指标名称" style="width: 150px" @keyup.enter="loadData" clearable />
          <ElInput v-model="queryParams.module" placeholder="所属模块" style="width: 150px" @keyup.enter="loadData" clearable />
          <ElInput v-model="queryParams.chip_type" placeholder="芯片类型" style="width: 150px" @keyup.enter="loadData" clearable />
          <ElInput v-model="queryParams.project" placeholder="所属项目" style="width: 150px" @keyup.enter="loadData" clearable />
          <ElButton type="primary" @click="loadData">查询</ElButton>
        </div>
        <div class="flex gap-2">
           <ElButton type="success" @click="importDialogVisible = true">导入 Excel</ElButton>
           <ElButton type="primary" @click="handleAdd">新增指标</ElButton>
        </div>
      </div>

      <ElTable v-loading="loading" :data="tableData" border style="width: 100%">
        <ElTableColumn prop="code" label="Code" width="150" />
        <ElTableColumn prop="name" label="名称" min-width="150" />
        <ElTableColumn prop="project" label="项目" width="120" />
        <ElTableColumn prop="module" label="模块" width="120" />
        <ElTableColumn prop="chip_type" label="芯片" width="100" />
        <ElTableColumn prop="baseline_value" label="基线值" width="100">
          <template #default="{ row }">
            {{ row.baseline_value }} {{ row.baseline_unit }}
          </template>
        </ElTableColumn>
        <ElTableColumn prop="fluctuation_range" label="允许浮动" width="100" />
        <ElTableColumn prop="fluctuation_direction" label="方向" width="100">
            <template #default="{ row }">
                {{ row.fluctuation_direction === 'up' ? '越大越好' : (row.fluctuation_direction === 'down' ? '越小越好' : '-') }}
            </template>
        </ElTableColumn>
        <ElTableColumn prop="owner_name" label="责任人" width="120" />
        <ElTableColumn label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <div class="flex justify-center gap-2">
                <ElButton :disabled="!canEdit(row)" type="primary" size="small" @click="handleEdit(row)">编辑</ElButton>
                <ElButton :disabled="!canEdit(row)" type="danger" size="small" @click="handleDelete(row)">删除</ElButton>
            </div>
          </template>
        </ElTableColumn>
      </ElTable>

      <div class="mt-4 flex justify-end">
        <ElPagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadData"
        />
      </div>

      <!-- Edit Dialog -->
      <ElDialog v-model="dialogVisible" :title="dialogTitle" width="600px">
        <ElForm ref="formRef" :model="formData" :rules="rules" label-width="100px">
          <ElFormItem label="Code" prop="code">
            <ElInput v-model="formData.code" />
          </ElFormItem>
          <ElFormItem label="名称" prop="name">
            <ElInput v-model="formData.name" />
          </ElFormItem>
          <ElFormItem label="项目" prop="project">
            <ElInput v-model="formData.project" />
          </ElFormItem>
          <ElFormItem label="模块" prop="module">
            <ElInput v-model="formData.module" />
          </ElFormItem>
          <ElFormItem label="芯片类型" prop="chip_type">
            <ElInput v-model="formData.chip_type" />
          </ElFormItem>
          <ElFormItem label="基线值" prop="baseline_value">
            <ElInputNumber v-model="formData.baseline_value" />
          </ElFormItem>
          <ElFormItem label="单位" prop="baseline_unit">
            <ElInput v-model="formData.baseline_unit" />
          </ElFormItem>
           <ElFormItem label="允许浮动" prop="fluctuation_range">
            <ElInputNumber v-model="formData.fluctuation_range" />
          </ElFormItem>
           <ElFormItem label="浮动方向" prop="fluctuation_direction">
            <ElSelect v-model="formData.fluctuation_direction">
                <ElOption label="越大越好" value="up" />
                <ElOption label="越小越好" value="down" />
                <ElOption label="无方向" value="none" />
            </ElSelect>
          </ElFormItem>
           <ElFormItem label="责任人" prop="owner_id">
             <ElSelect
                v-model="formData.owner_id"
                filterable
                remote
                placeholder="请输入用户名或姓名搜索"
                :remote-method="searchUsers"
                :loading="userLoading"
                clearable
             >
                <ElOption
                    v-for="item in userOptions"
                    :key="item.id"
                    :label="`${item.name} (${item.username})`"
                    :value="item.id"
                />
             </ElSelect>
          </ElFormItem>
        </ElForm>
        <template #footer>
          <ElButton @click="dialogVisible = false">取消</ElButton>
          <ElButton type="primary" @click="handleSubmit">确定</ElButton>
        </template>
      </ElDialog>

      <!-- Import Dialog -->
      <ElDialog v-model="importDialogVisible" title="导入指标" width="400px">
        <div class="mb-4 text-right">
            <ElLink type="primary" :underline="false" @click="downloadTemplate">下载模板 CSV</ElLink>
        </div>
        <ElUpload
          class="upload-demo"
          drag
          action="#"
          :http-request="handleImportRequest"
          :show-file-list="false"
        >
          <div class="el-upload__text">
            Drop file here or <em>click to upload</em>
          </div>
        </ElUpload>
      </ElDialog>
    </div>
  </Page>
</template>
