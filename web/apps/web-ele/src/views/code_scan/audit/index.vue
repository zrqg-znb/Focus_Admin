<script setup lang="ts">
import type { ShieldApplicationItem } from '#/api/code_scan';

import { ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  ElButton,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus';

import { auditShieldApi, listApplicationsApi } from '#/api/code_scan';
import { useZqTable } from '#/components/zq-table';

import { useColumns } from './data';

defineOptions({ name: 'CodeScanAudit' });

const activeTab = ref<'my_apply' | 'my_audit'>('my_audit');
const selectedRows = ref<ShieldApplicationItem[]>([]);

const auditVisible = ref(false);
const detailVisible = ref(false);
const currentDetail = ref<null | ShieldApplicationItem>(null);

const auditForm = ref({
  application_ids: [] as string[],
  audit_comment: '',
  status: 'Approved',
});

const [Grid, gridApi] = useZqTable({
  gridOptions: {
    border: true,
    stripe: true,
    columns: useColumns(),
    proxyConfig: {
      autoLoad: true,
      ajax: {
        query: async ({ page }) => {
          const res = await listApplicationsApi(activeTab.value, {
            page: page.currentPage,
            pageSize: page.pageSize,
          });
          return {
            items: res.items || [],
            total: res.total || 0,
          };
        },
      },
    },
    pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [10, 20, 50, 100],
    },
    toolbarConfig: {
      custom: true,
      refresh: true,
      zoom: true,
    },
  },
});

function handleTabChange() {
  selectedRows.value = [];
  gridApi.reload();
}

function handleSelectionChange(rows: ShieldApplicationItem[]) {
  selectedRows.value = rows;
}

function handleAudit(row: ShieldApplicationItem) {
  auditForm.value.application_ids = [row.id];
  auditForm.value.audit_comment = '';
  auditVisible.value = true;
}

function handleBatchAudit() {
  const pendingIds = selectedRows.value
    .filter((item) => item.status === 'Pending')
    .map((item) => item.id);
  if (pendingIds.length === 0) {
    ElMessage.warning('请选择待审批状态的申请');
    return;
  }
  auditForm.value.application_ids = pendingIds;
  auditForm.value.audit_comment = '';
  auditVisible.value = true;
}

function handleDetail(row: ShieldApplicationItem) {
  currentDetail.value = row;
  detailVisible.value = true;
}

async function submitAudit(status: string) {
  try {
    if (auditForm.value.application_ids.length === 0) {
      ElMessage.warning('未选择审批项');
      return;
    }
    auditForm.value.status = status;
    await auditShieldApi(auditForm.value);
    ElMessage.success('处理成功');
    auditVisible.value = false;
    selectedRows.value = [];
    gridApi.reload();
  } catch {
    ElMessage.error('操作失败');
  }
}

function getStatusType(status: string) {
  if (status === 'Approved') return 'success';
  if (status === 'Pending') return 'warning';
  if (status === 'Rejected') return 'danger';
  return 'info';
}
</script>

<template>
  <Page title="屏蔽审批" auto-content-height>
    <div class="flex h-full min-h-0 flex-col">
      <ElTabs v-model="activeTab" class="mb-2" @tab-change="handleTabChange">
        <ElTabPane label="待我审批" name="my_audit" />
        <ElTabPane label="我的申请" name="my_apply" />
      </ElTabs>
      <div class="min-h-0 flex-1">
        <Grid class="h-full" @selection-change="handleSelectionChange">
          <template #toolbar-actions>
            <ElButton
              v-if="activeTab === 'my_audit'"
              type="danger"
              plain
              @click="handleBatchAudit"
            >
              批量审批
            </ElButton>
          </template>

          <template #cell-severity="{ row }">
            <ElTag v-if="row.severity === 'High'" type="danger">High</ElTag>
            <ElTag v-else-if="row.severity === 'Medium'" type="warning">
              Medium
            </ElTag>
            <ElTag v-else type="info">Low</ElTag>
          </template>

          <template #cell-status="{ row }">
            <ElTag :type="getStatusType(row.status)">{{ row.status }}</ElTag>
          </template>

          <template #cell-actions="{ row }">
            <ElButton link type="primary" @click="handleDetail(row)">
              详情
            </ElButton>
            <ElButton
              v-if="activeTab === 'my_audit' && row.status === 'Pending'"
              type="primary"
              link
              @click="handleAudit(row)"
            >
              审批
            </ElButton>
          </template>
        </Grid>
      </div>
    </div>

    <ElDialog v-model="auditVisible" title="屏蔽审批" width="500px">
      <ElForm :model="auditForm" label-width="80px">
        <ElFormItem label="审批数量">
          <span>{{ auditForm.application_ids.length }} 条</span>
        </ElFormItem>
        <ElFormItem label="审批意见">
          <ElInput
            v-model="auditForm.audit_comment"
            type="textarea"
            placeholder="请输入审批意见"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton type="danger" @click="submitAudit('Rejected')">驳回</ElButton>
        <ElButton type="primary" @click="submitAudit('Approved')">
          通过
        </ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="detailVisible" title="缺陷详情" width="800px">
      <ElDescriptions v-if="currentDetail" :column="1" border>
        <ElDescriptionsItem label="工具">
          {{ currentDetail.tool_name }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="严重程度">
          {{ currentDetail.severity }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="文件路径">
          {{ currentDetail.file_path }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="缺陷描述">
          {{ currentDetail.defect_description }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="currentDetail.help_info" label="修复建议">
          {{ currentDetail.help_info }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="申请理由">
          {{ currentDetail.reason }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="currentDetail.code_snippet" label="代码片段">
          <pre
            class="max-h-[300px] overflow-x-auto rounded bg-gray-800 p-2 text-xs text-white"
          >
            {{ currentDetail.code_snippet }}
          </pre>
        </ElDescriptionsItem>
      </ElDescriptions>
    </ElDialog>
  </Page>
</template>
