<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { Page } from '@vben/common-ui';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { listProjectOverviewApi, listLatestResultsApi, applyShieldApi } from '#/api/code_scan';
import { useSummaryColumns, useDetailColumns } from './data';
import { ElButton, ElTag, ElMessage, ElDialog, ElInput, ElForm, ElFormItem, ElDescriptions, ElDescriptionsItem } from 'element-plus';
import { useRoute, useRouter } from 'vue-router';
import { UserSelector } from '#/components/zq-form/user-selector';

const route = useRoute();
const router = useRouter();
const projectId = computed(() => route.query.projectId as string | undefined);
const isDetail = computed(() => Boolean(projectId.value));

const shieldVisible = ref(false);
const shieldForm = ref({
  result_ids: [] as string[],
  approver_id: '',
  reason: '',
});

const summaryGridOptions: any = {
  columns: useSummaryColumns([]),
  height: '100%',
  proxyConfig: {
    ajax: {
      query: async () => {
        const res = (await listProjectOverviewApi()) || [];
        const toolSet = new Set<string>();
        for (const row of res) {
          const keys = Object.keys(row.tool_counts || {});
          for (const k of keys) toolSet.add(k);
        }
        const toolNames = Array.from(toolSet).sort();
        summaryGridOptions.columns = useSummaryColumns(toolNames);
        const items = res.map((row: any) => ({ ...row, ...(row.tool_counts || {}) }));
        return { items };
      },
    },
  },
};

const detailGridOptions: any = {
  columns: useDetailColumns(),
  height: '100%',
  proxyConfig: {
    ajax: {
      query: async () => {
        if (!projectId.value) return { items: [] };
        const res = await listLatestResultsApi(projectId.value);
        return { items: res || [] };
      },
    },
  },
};

const [SummaryGrid, summaryGridApi] = useVbenVxeGrid({ gridOptions: summaryGridOptions });
const [DetailGrid, detailGridApi] = useVbenVxeGrid({ gridOptions: detailGridOptions });

onMounted(async () => {
  if (isDetail.value) {
    detailGridApi.reload();
  } else {
    summaryGridApi.reload();
  }
});

watch(
  () => route.query.projectId,
  () => {
    if (isDetail.value) {
      detailGridApi.reload();
    } else {
      summaryGridApi.reload();
    }
  },
);

function openProject(row: any) {
  router.push({ path: route.path, query: { projectId: row.project_id } });
}

function backToSummary() {
  router.push({ path: route.path, query: {} });
}

function handleApplyShield() {
  const selected = detailGridApi.grid?.getCheckboxRecords();
  if (!selected || selected.length === 0) {
    ElMessage.warning('请选择要屏蔽的缺陷');
    return;
  }
  shieldForm.value.result_ids = selected.map((item: any) => item.id);
  shieldVisible.value = true;
}

async function submitShield() {
  try {
    await applyShieldApi(shieldForm.value);
    ElMessage.success('申请已提交');
    shieldVisible.value = false;
    detailGridApi.reload();
  } catch (error) {
    ElMessage.error('提交失败');
  }
}

const getSeverityType = (severity: string) => {
  if (severity === 'High') return 'danger';
  if (severity === 'Medium') return 'warning';
  return 'info';
};

const getStatusType = (status: string) => {
  if (status === 'Shielded') return 'success';
  if (status === 'Pending') return 'warning';
  if (status === 'Rejected') return 'danger';
  return 'info';
};
</script>

<template>
  <Page title="扫描结果" auto-content-height>
    <template #extra>
      <div v-if="isDetail" class="flex items-center gap-3">
        <ElButton @click="backToSummary">返回</ElButton>
        <ElButton type="warning" @click="handleApplyShield">申请屏蔽</ElButton>
      </div>
    </template>

    <div class="h-full">
      <SummaryGrid v-if="!isDetail">
        <template #project_name="{ row }">
          <ElButton link type="primary" @click="openProject(row)">{{ row.project_name }}</ElButton>
        </template>
      </SummaryGrid>

      <DetailGrid v-else>
        <template #expand_content="{ row }">
          <div class="p-4 bg-gray-50">
            <ElDescriptions title="详细信息" :column="1" border>
              <ElDescriptionsItem label="缺陷描述">{{ row.description }}</ElDescriptionsItem>
              <ElDescriptionsItem label="文件路径">{{ row.file_path }} : {{ row.line_number }}</ElDescriptionsItem>
              <ElDescriptionsItem label="修复建议" v-if="row.help_info">{{ row.help_info }}</ElDescriptionsItem>
              <ElDescriptionsItem label="代码片段" v-if="row.code_snippet">
                <pre class="bg-gray-800 text-white p-2 rounded text-xs overflow-x-auto">{{ row.code_snippet }}</pre>
              </ElDescriptionsItem>
            </ElDescriptions>
          </div>
        </template>
        <template #severity="{ row }">
          <ElTag :type="getSeverityType(row.severity)">{{ row.severity }}</ElTag>
        </template>
        <template #shield_status="{ row }">
          <ElTag :type="getStatusType(row.shield_status)">{{ row.shield_status }}</ElTag>
        </template>
      </DetailGrid>
    </div>

    <ElDialog v-model="shieldVisible" title="申请屏蔽" width="500px">
      <ElForm :model="shieldForm" label-width="100px">
        <ElFormItem label="审批人" required>
          <UserSelector v-model="shieldForm.approver_id" placeholder="请选择审批人" />
        </ElFormItem>
        <ElFormItem label="屏蔽理由" required>
          <ElInput v-model="shieldForm.reason" type="textarea" placeholder="请输入理由" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="shieldVisible = false">取消</ElButton>
        <ElButton type="primary" @click="submitShield">提交</ElButton>
      </template>
    </ElDialog>
  </Page>
</template>
