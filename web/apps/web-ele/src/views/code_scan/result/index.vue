<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { Page } from '@vben/common-ui';
import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { listProjectOverviewApi, listLatestResultsApi, applyShieldApi, listResultShieldRecordsApi } from '#/api/code_scan';
import { useSummaryColumns, useDetailColumns } from './data';
import { ElButton, ElTag, ElMessage, ElDialog, ElInput, ElForm, ElFormItem, ElDescriptions, ElDescriptionsItem, ElTabs, ElTabPane, ElTable, ElTableColumn } from 'element-plus';
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

const tools = ref<string[]>([]);
const activeTool = ref('');

const summaryGridOptions: any = {
  columns: useSummaryColumns([]),
  height: '100%',
  pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [10, 20, 50, 100],
  },
  proxyConfig: {
    ajax: {
      query: async ({ page }) => {
        const res = (await listProjectOverviewApi({
            page: page.currentPage,
            pageSize: page.pageSize
        })) || { items: [], total: 0 };
        
        // Handle paginated response
        const itemsData = res.items || [];
        const total = res.total || 0;

        const toolSet = new Set<string>();
        // Ensure tscan and cppcheck are always present if needed, 
        // or just let them be dynamic. 
        // If we want to force columns, we can add them here.
        // But dynamic is usually better. 
        // If 'cppcheck' exists in data, it should appear.
        for (const row of itemsData) {
          const keys = Object.keys(row.tool_counts || {});
          for (const k of keys) toolSet.add(k);
        }
        // Explicitly include tscan and cppcheck if they are missing but expected to be shown as 0
        if (!toolSet.has('tscan')) toolSet.add('tscan');
        if (!toolSet.has('cppcheck')) toolSet.add('cppcheck');
        if (!toolSet.has('weggli')) toolSet.add('weggli');

        const toolNames = Array.from(toolSet).sort();
        
        // Reload columns explicitly
        summaryGridApi.setGridOptions({
            columns: useSummaryColumns(toolNames)
        });

        const items = itemsData.map((row: any) => ({ ...row, ...(row.tool_counts || {}) }));
        return { items, total };
      },
    },
  },
};

const detailGridOptions: any = {
  columns: useDetailColumns(),
  height: '100%',
  pagerConfig: {
      enabled: true,
      pageSize: 20,
      pageSizes: [10, 20, 50, 100],
  },
  proxyConfig: {
    autoLoad: false, // 手动触发加载，确保 activeTool 已设置
    ajax: {
      query: async ({ page }: any) => {
        if (!projectId.value || !activeTool.value) return { items: [], total: 0 };
        try {
            const res = await listLatestResultsApi(projectId.value, {
                tool_name: activeTool.value,
                page: page.currentPage,
                pageSize: page.pageSize
            });
            // Debug info
            // console.log('Scan Results:', res);
            
            // 兼容可能被拦截器处理过的数据结构
            const items = res.items || res.data?.items || [];
            const total = res.total || res.data?.total || 0;
            
            return { items, total };
        } catch (e) {
            console.error(e);
            return { items: [], total: 0 };
        }
      },
    },
  },
};

const [SummaryGrid, summaryGridApi] = useVbenVxeGrid({ gridOptions: summaryGridOptions });
const [DetailGrid, detailGridApi] = useVbenVxeGrid({ gridOptions: detailGridOptions });

async function loadTools() {
    if (!projectId.value) return;
    try {
        const res: any = await listProjectOverviewApi();
        const items = res.items || res; // 兼容分页返回结构 {items: [], total: N} 和数组返回
        const project = Array.isArray(items) ? items.find((p: any) => p.project_id === projectId.value) : null;
        
        if (project && project.tool_counts) {
            tools.value = Object.keys(project.tool_counts).sort();
            if (tools.value.length > 0) {
                // If activeTool is not in the list (e.g. initial load), set to first
                if (!activeTool.value || !tools.value.includes(activeTool.value)) {
                    activeTool.value = tools.value[0] || '';
                }
            }
        }
    } catch (e) {
        console.error(e);
    }
}

function handleTabChange() {
    detailGridApi.reload();
}

onMounted(async () => {
  if (isDetail.value) {
    await loadTools();
    detailGridApi.reload();
  } else {
    summaryGridApi.reload();
  }
});

watch(
  () => route.query.projectId,
  async () => {
    if (isDetail.value) {
      await loadTools();
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

const getShieldRecordStatusType = (status: string) => {
  if (status === 'Approved') return 'success';
  if (status === 'Pending') return 'warning';
  if (status === 'Rejected') return 'danger';
  return 'info';
};

const expandTabMap = ref<Record<string, string>>({});
const shieldRecordsMap = ref<Record<string, any[]>>({});
const shieldRecordsLoadingMap = ref<Record<string, boolean>>({});

function getExpandTab(resultId: string) {
  return expandTabMap.value[resultId] || 'detail';
}

function isShieldRecordsLoading(resultId: string) {
  return Boolean(shieldRecordsLoadingMap.value[resultId]);
}

async function ensureShieldRecordsLoaded(resultId: string) {
  if (shieldRecordsMap.value[resultId]) return;
  shieldRecordsLoadingMap.value[resultId] = true;
  try {
    const res: any = await listResultShieldRecordsApi(resultId);
    const items = res?.data ?? res ?? [];
    shieldRecordsMap.value[resultId] = Array.isArray(items) ? items : [];
  } catch (e) {
    shieldRecordsMap.value[resultId] = [];
  } finally {
    shieldRecordsLoadingMap.value[resultId] = false;
  }
}

async function handleExpandTabChange(resultId: string, name: any) {
  const tabName = String(name);
  expandTabMap.value[resultId] = tabName;
  if (tabName === 'shield') {
    await ensureShieldRecordsLoaded(resultId);
  }
}
</script>

<template>
  <Page title="扫描结果" auto-content-height>
    <template #extra>
      <div v-if="isDetail" class="flex items-center gap-3">
        <ElButton @click="backToSummary">返回</ElButton>
        <ElButton type="warning" @click="handleApplyShield">申请屏蔽</ElButton>
      </div>
    </template>

    <div class="h-full flex flex-col">
      <SummaryGrid v-if="!isDetail">
        <template #project_name="{ row }">
          <ElButton link type="primary" @click="openProject(row)">{{ row.project_name }}</ElButton>
        </template>
      </SummaryGrid>

      <div v-else class="h-full flex flex-col">
          <ElTabs v-model="activeTool" @tab-change="handleTabChange" class="mb-2">
              <ElTabPane v-for="tool in tools" :key="tool" :label="tool" :name="tool" />
          </ElTabs>
          <div class="flex-1 min-h-0 overflow-hidden">
              <DetailGrid>
                <template #expand_content="{ row }">
                  <div class="p-4 bg-gray-50">
                    <ElTabs
                      :model-value="getExpandTab(row.id)"
                      @tab-change="(name) => handleExpandTabChange(row.id, name)"
                    >
                      <ElTabPane label="缺陷详情" name="detail">
                        <ElDescriptions title="详细信息" :column="1" border>
                          <ElDescriptionsItem label="缺陷描述">{{ row.description }}</ElDescriptionsItem>
                          <ElDescriptionsItem label="文件路径">{{ row.file_path }} : {{ row.line_number }}</ElDescriptionsItem>
                          <ElDescriptionsItem label="修复建议" v-if="row.help_info">{{ row.help_info }}</ElDescriptionsItem>
                          <ElDescriptionsItem label="代码片段" v-if="row.code_snippet">
                            <pre class="bg-gray-800 text-white p-2 rounded text-xs overflow-x-auto">{{ row.code_snippet }}</pre>
                          </ElDescriptionsItem>
                        </ElDescriptions>
                      </ElTabPane>
                      <ElTabPane label="屏蔽记录" name="shield">
                        <ElTable
                          v-loading="isShieldRecordsLoading(row.id)"
                          :data="shieldRecordsMap[row.id] || []"
                          size="small"
                          border
                          style="width: 100%"
                        >
                          <ElTableColumn prop="sys_create_datetime" label="时间" width="180" />
                          <ElTableColumn label="状态" width="120">
                            <template #default="{ row: srow }">
                              <ElTag :type="getShieldRecordStatusType(srow.status)">{{ srow.status }}</ElTag>
                            </template>
                          </ElTableColumn>
                          <ElTableColumn prop="applicant_name" label="申请人" width="120" />
                          <ElTableColumn prop="approver_name" label="审批人" width="120" />
                          <ElTableColumn prop="reason" label="理由" min-width="220" />
                          <ElTableColumn prop="audit_comment" label="审批意见" min-width="220" />
                        </ElTable>
                        <div
                          v-if="!isShieldRecordsLoading(row.id) && (shieldRecordsMap[row.id]?.length || 0) === 0"
                          class="py-3 text-center text-gray-400"
                        >
                          暂无屏蔽记录
                        </div>
                      </ElTabPane>
                    </ElTabs>
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
      </div>
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
