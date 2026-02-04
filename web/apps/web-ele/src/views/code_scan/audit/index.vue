<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Page } from '@vben/common-ui';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { listApplicationsApi, auditShieldApi } from '#/api/code_scan';
import { ElButton, ElTag, ElMessage, ElTabs, ElTabPane, ElDialog, ElForm, ElFormItem, ElInput } from 'element-plus';

const activeTab = ref<'my_audit' | 'my_apply'>('my_audit');

const auditVisible = ref(false);
const auditForm = ref({
  application_id: '',
  status: 'Approved',
  audit_comment: '',
});

const gridOptions: any = {
  columns: [
    { type: 'seq', width: 60 },
    { field: 'applicant_name', title: '申请人', width: 120 },
    { field: 'approver_name', title: '审批人', width: 120 },
    { field: 'reason', title: '申请理由', minWidth: 200 },
    { field: 'status', title: '状态', width: 100, slots: { default: 'status' } },
    { field: 'sys_create_datetime', title: '申请时间', width: 180 },
    { field: 'action', title: '操作', width: 120, slots: { default: 'action' } },
  ],
  proxyConfig: {
    ajax: {
      query: async () => {
        const res = await listApplicationsApi(activeTab.value);
        return { items: res };
      },
    },
  },
};

const [Grid, gridApi] = useVbenVxeGrid({ gridOptions });

function handleTabChange() {
  gridApi.reload();
}

function handleAudit(row: any) {
  auditForm.value.application_id = row.id;
  auditVisible.value = true;
}

async function submitAudit(status: string) {
  try {
    auditForm.value.status = status;
    await auditShieldApi(auditForm.value);
    ElMessage.success('处理成功');
    auditVisible.value = false;
    gridApi.reload();
  } catch (error) {
    ElMessage.error('操作失败');
  }
}

const getStatusType = (status: string) => {
  if (status === 'Approved') return 'success';
  if (status === 'Pending') return 'warning';
  if (status === 'Rejected') return 'danger';
  return 'info';
};
</script>

<template>
  <Page title="屏蔽审批中心">
    <ElTabs v-model="activeTab" @tab-change="handleTabChange" class="bg-white p-4 rounded shadow">
      <ElTabPane label="待我审批" name="my_audit" />
      <ElTabPane label="我的申请" name="my_apply" />
    </ElTabs>

    <Grid class="mt-4">
      <template #status="{ row }">
        <ElTag :type="getStatusType(row.status)">{{ row.status }}</ElTag>
      </template>
      <template #action="{ row }">
        <ElButton v-if="activeTab === 'my_audit' && row.status === 'Pending'" type="primary" link @click="handleAudit(row)">审批</ElButton>
      </template>
    </Grid>

    <ElDialog v-model="auditVisible" title="屏蔽审批" width="500px">
      <ElForm :model="auditForm" label-width="80px">
        <ElFormItem label="审批意见">
          <ElInput v-model="auditForm.audit_comment" type="textarea" placeholder="请输入审批意见" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton type="danger" @click="submitAudit('Rejected')">驳回</ElButton>
        <ElButton type="primary" @click="submitAudit('Approved')">通过</ElButton>
      </template>
    </ElDialog>
  </Page>
</template>
