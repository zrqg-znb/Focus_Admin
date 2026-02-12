<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Page } from '@vben/common-ui';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { listApplicationsApi, auditShieldApi } from '#/api/code_scan';
import { ElButton, ElTag, ElMessage, ElTabs, ElTabPane, ElDialog, ElForm, ElFormItem, ElInput, ElDescriptions, ElDescriptionsItem } from 'element-plus';

const activeTab = ref<'my_audit' | 'my_apply'>('my_audit');

const auditVisible = ref(false);
const detailVisible = ref(false);
const currentDetail = ref<any>(null);

const auditForm = ref({
  application_id: '',
  status: 'Approved',
  audit_comment: '',
});

const gridOptions: any = {
  columns: [
    { type: 'seq', width: 60 },
    { field: 'applicant_name', title: '申请人', width: 100 },
    { field: 'tool_name', title: '工具', width: 100 },
    { field: 'severity', title: '严重程度', width: 100, slots: { default: 'severity' } },
    { field: 'file_path', title: '文件路径', minWidth: 200, showOverflow: true },
    { field: 'defect_description', title: '缺陷描述', minWidth: 200, showOverflow: true },
    { field: 'reason', title: '申请理由', minWidth: 200, showOverflow: true },
    { field: 'status', title: '状态', width: 100, slots: { default: 'status' } },
    { field: 'sys_create_datetime', title: '申请时间', width: 160 },
    { field: 'action', title: '操作', width: 150, slots: { default: 'action' } },
  ],
  height: '100%',
  pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [10, 20, 50, 100],
  },
  proxyConfig: {
    ajax: {
      query: async ({ page }) => {
        const res = await listApplicationsApi(activeTab.value, {
            page: page.currentPage,
            pageSize: page.pageSize
        });
        return { items: res.items, total: res.total };
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

function handleDetail(row: any) {
    currentDetail.value = row;
    detailVisible.value = true;
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
  <Page title="屏蔽审批" auto-content-height>
    <div class="h-full flex flex-col">
      <ElTabs v-model="activeTab" @tab-change="handleTabChange" class="mb-2">
        <ElTabPane label="待我审批" name="my_audit" />
        <ElTabPane label="我的申请" name="my_apply" />
      </ElTabs>
      <div class="flex-1 min-h-0 overflow-hidden">
        <Grid>
          <template #severity="{ row }">
             <ElTag v-if="row.severity === 'High'" type="danger">High</ElTag>
             <ElTag v-else-if="row.severity === 'Medium'" type="warning">Medium</ElTag>
             <ElTag v-else type="info">Low</ElTag>
          </template>
          <template #status="{ row }">
            <ElTag :type="getStatusType(row.status)">{{ row.status }}</ElTag>
          </template>
          <template #action="{ row }">
            <ElButton link type="primary" @click="handleDetail(row)">详情</ElButton>
            <ElButton v-if="activeTab === 'my_audit' && row.status === 'Pending'" type="primary" link @click="handleAudit(row)">审批</ElButton>
          </template>
        </Grid>
      </div>
    </div>

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

    <ElDialog v-model="detailVisible" title="缺陷详情" width="800px">
        <ElDescriptions :column="1" border v-if="currentDetail">
            <ElDescriptionsItem label="工具">{{ currentDetail.tool_name }}</ElDescriptionsItem>
            <ElDescriptionsItem label="严重程度">{{ currentDetail.severity }}</ElDescriptionsItem>
            <ElDescriptionsItem label="文件路径">{{ currentDetail.file_path }}</ElDescriptionsItem>
            <ElDescriptionsItem label="缺陷描述">{{ currentDetail.defect_description }}</ElDescriptionsItem>
            <ElDescriptionsItem label="修复建议" v-if="currentDetail.help_info">{{ currentDetail.help_info }}</ElDescriptionsItem>
            <ElDescriptionsItem label="申请理由">{{ currentDetail.reason }}</ElDescriptionsItem>
            <ElDescriptionsItem label="代码片段" v-if="currentDetail.code_snippet">
                <pre class="bg-gray-800 text-white p-2 rounded text-xs overflow-x-auto max-h-[300px]">{{ currentDetail.code_snippet }}</pre>
            </ElDescriptionsItem>
        </ElDescriptions>
    </ElDialog>
  </Page>
</template>
