<script lang="ts" setup>
import { reactive, ref } from 'vue';
import { Page, useVbenDrawer } from '@vben/common-ui';
import { useVbenVxeGrid, type VxeGridProps } from '#/adapter/vxe-table';
import { ElButton, ElMessage, ElSwitch, ElPopconfirm } from 'element-plus';
import {
  getProjectList,
  createProject,
  updateProject,
  deleteProject,
  subscribeProject,
  unsubscribeProject,
  type ProjectConfig
} from '#/api/ci_daily_report';
import { Plus } from '@vben/icons';

defineOptions({ name: 'CIProjectConfig' });

const formOptions = reactive({
  collapsed: false,
  items: [
    {
      component: 'VbenInput',
      fieldName: 'keyword',
      label: '项目名称',
      componentProps: {
        placeholder: '请输入项目名称',
      },
    },
    {
      component: 'VbenInput',
      fieldName: 'category',
      label: '项目分类',
      componentProps: {
        placeholder: '请输入项目分类',
      },
    },
    {
      component: 'VbenInput',
      fieldName: 'owner',
      label: '项目责任人',
      componentProps: {
        placeholder: '请输入责任人',
      },
    },
  ],
});

const gridOptions = reactive<VxeGridProps<ProjectConfig>>({
  columns: [
    { field: 'id', title: 'ID', width: 60 },
    { field: 'name', title: '项目名称', minWidth: 150 },
    { field: 'project_category', title: '分类', width: 120 },
    { field: 'project_owner', title: '责任人', width: 120 },
    { field: 'description', title: '描述', minWidth: 200 },
    { field: 'is_subscribed', title: '订阅', width: 100, slots: { default: 'subscription' } },
    { field: 'created_at', title: '创建时间', width: 160 },
    { title: '操作', width: 180, slots: { default: 'action' } },
  ],
  proxyConfig: {
    ajax: {
      query: async ({ page, form }) => {
        const params = {
          page: page.currentPage,
          size: page.pageSize,
          keyword: form.keyword,
          category: form.category,
          owner: form.owner,
        };
        return await getProjectList(params);
      },
    },
  },
  toolbarConfig: {
    custom: true,
    slots: {
      buttons: 'toolbar_buttons',
    },
  },
});

const [Grid, gridApi] = useVbenVxeGrid({ formOptions, gridOptions });
const [Drawer, drawerApi] = useVbenDrawer({
  onConfirm: async () => {
    try {
      await drawerFormApi.validate();
      const values = await drawerFormApi.getValues() as any;

      // Use setConfirmLoading if available, or cast to any if needed
      if ((drawerApi as any).setLoading) {
        (drawerApi as any).setLoading(true);
      }

      if (isEdit.value && currentId.value) {
        await updateProject(currentId.value, values);
        ElMessage.success('更新成功');
      } else {
        await createProject(values);
        ElMessage.success('创建成功');
      }
      drawerApi.close();
      gridApi.reload();
    } catch (error) {
      console.error(error);
    } finally {
      if ((drawerApi as any).setLoading) {
        (drawerApi as any).setLoading(false);
      }
    }
  },
});

// Drawer Form Configuration
import { useVbenForm } from '@vben/common-ui';
const isEdit = ref(false);
const currentId = ref<number | null>(null);

const [DrawerForm, drawerFormApi] = useVbenForm({
  schema: [
    { component: 'VbenInput', fieldName: 'name', label: '项目名称', rules: 'required' },
    { component: 'VbenInput', fieldName: 'project_category', label: '项目分类' },
    { component: 'VbenInput', fieldName: 'project_owner', label: '项目责任人' },
    { component: 'VbenTextarea', fieldName: 'description', label: '描述' },
    { component: 'VbenInput', fieldName: 'codecheck_id', label: 'CodeCheck ID' },
    { component: 'VbenInput', fieldName: 'binscope_id', label: 'BinScope ID' },
    { component: 'VbenInput', fieldName: 'cooddy_id', label: 'Cooddy ID' },
    { component: 'VbenInput', fieldName: 'compiletion_check_id', label: 'Compilation Check ID' },
    { component: 'VbenInput', fieldName: 'build_check_id', label: 'Build Check ID' },
    { component: 'VbenInput', fieldName: 'build_project_id', label: 'Build Project ID' },
    { component: 'VbenInput', fieldName: 'codecov_id', label: 'CodeCov ID' },
    { component: 'VbenInput', fieldName: 'fossbot_id', label: 'FossBot ID' },
  ],
});

function handleAdd() {
  isEdit.value = false;
  currentId.value = null;
  drawerFormApi.resetForm();
  drawerApi.open();
  (drawerApi as any).setTitle('新增项目配置');
}

function handleEdit(row: ProjectConfig) {
  isEdit.value = true;
  currentId.value = row.id;
  drawerFormApi.setValues(row);
  drawerApi.open();
  (drawerApi as any).setTitle('编辑项目配置');
}

async function handleDelete(row: ProjectConfig) {
  try {
    await deleteProject(row.id);
    ElMessage.success('删除成功');
    gridApi.reload();
  } catch (error) {
    console.error(error);
  }
}

async function handleSubscribeChange(row: ProjectConfig, val: boolean) {
  // val is the new value
  try {
    if (val) {
      await subscribeProject(row.id);
      ElMessage.success(`已订阅 ${row.name}`);
    } else {
      await unsubscribeProject(row.id);
      ElMessage.success(`已取消订阅 ${row.name}`);
    }
    // Update local state to reflect change (though grid might refresh)
    // row.is_subscribed = val;
    // Usually better to reload grid or just trust optimistic UI
    gridApi.reload();
  } catch (error) {
    console.error(error);
    // Revert switch if failed?
    gridApi.reload();
  }
}
</script>

<template>
  <Page title="项目配置管理">
    <Grid>
      <template #toolbar_buttons>
        <ElButton type="primary" @click="handleAdd">
          <Plus class="mr-2 size-4" /> 新增项目
        </ElButton>
      </template>

      <template #subscription="{ row }">
        <ElSwitch
          :model-value="row.is_subscribed"
          :active-value="true"
          :inactive-value="false"
          @change="(val) => handleSubscribeChange(row, !!val)"
        />
      </template>

      <template #action="{ row }">
        <ElButton link type="primary" @click="handleEdit(row)">编辑</ElButton>
        <ElPopconfirm title="确认删除该项目配置吗？" @confirm="handleDelete(row)">
          <template #reference>
            <ElButton link type="danger">删除</ElButton>
          </template>
        </ElPopconfirm>
      </template>
    </Grid>
    <Drawer>
      <DrawerForm />
    </Drawer>
  </Page>
</template>
