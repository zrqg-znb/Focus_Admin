<!-- eslint-disable vue/html-closing-bracket-newline, vue/multiline-html-element-content-newline -->
<script lang="ts" setup>
import type { FindingFilters } from './types';
import type {
  Finding,
  GovernanceProject,
  GovernanceResponsibility,
  UserOption,
} from '#/api/agent-tools/code-quality-governance';

import { computed, onMounted, reactive, ref } from 'vue';

import {
  ElButton,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElTag,
} from 'element-plus';

import {
  createApplicationApi,
  getFindingApi,
  listFindingsApi,
} from '#/api/agent-tools/code-quality-governance';
import { useZqTable } from '#/components/zq-table';

import GovernanceHeaderFilter from './header-filter.vue';

defineOptions({ name: 'CodeQualityGovernanceFindings' });

const props = defineProps<{
  projects: GovernanceProject[];
  responsibilities: GovernanceResponsibility[];
}>();

const severityOptions = ['blocker', 'critical', 'major', 'minor', 'info'].map(
  (value) => ({ label: value, value }),
);
const statusOptions = [
  { label: '正常', value: 'Normal' },
  { label: '申请中', value: 'Pending' },
  { label: '已屏蔽', value: 'Shielded' },
  { label: '已驳回', value: 'Rejected' },
];
const filters = reactive<FindingFilters>({
  keyword: '',
  project_id: '',
  responsibility_id: '',
  severity: '',
  shield_status: '',
  tool_name: '',
});
const selectedRows = ref<Finding[]>([]);
const applyVisible = ref(false);
const detailVisible = ref(false);
const detail = ref<Finding>();
const applyForm = ref({ approver_id: '', reason: '' });

const selectedResponsibility = computed(() => {
  const firstRow = selectedRows.value[0];
  if (!firstRow) return undefined;
  return props.responsibilities.find(
    (item) => item.name === firstRow.responsibility_name,
  );
});

const applyApprovers = computed<UserOption[]>(
  () => selectedResponsibility.value?.approvers || [],
);

function statusType(status: string) {
  if (status === 'Shielded') return 'success';
  if (status === 'Pending') return 'warning';
  if (status === 'Rejected') return 'danger';
  return 'info';
}

function severityType(severity: string) {
  return severity === 'blocker' || severity === 'critical'
    ? 'danger'
    : 'warning';
}

function headerFilterOptions(items: { id: string; name: string }[]) {
  return items.map((item) => ({ label: item.name, value: item.id }));
}

function reloadFindings() {
  void findingGridApi.reload();
}

function applyHeaderFilter(key: keyof FindingFilters, value: string) {
  filters[key] = value;
  reloadFindings();
}

const [FindingGrid, findingGridApi] = useZqTable<Finding>({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    border: true,
    columns: [
      { type: 'selection', width: 48, fixed: 'left' },
      {
        key: 'project_name',
        dataKey: 'project_name',
        title: '项目',
        minWidth: 150,
        slots: { header: 'header-project' },
      },
      {
        key: 'responsibility_name',
        dataKey: 'responsibility_name',
        title: '责任田',
        minWidth: 150,
        slots: { header: 'header-responsibility' },
      },
      {
        key: 'severity',
        dataKey: 'severity',
        title: '严重级别',
        width: 120,
        slots: { default: 'cell-severity', header: 'header-severity' },
      },
      {
        key: 'latest_tool_name',
        dataKey: 'latest_tool_name',
        title: '扫描工具',
        width: 130,
        slots: { header: 'header-tool' },
      },
      { key: 'rule_id', dataKey: 'rule_id', title: '规则', minWidth: 180 },
      {
        key: 'latest_file_path',
        dataKey: 'latest_file_path',
        title: '文件路径',
        minWidth: 220,
      },
      { key: 'latest_line', dataKey: 'latest_line', title: '行号', width: 80 },
      {
        key: 'latest_message',
        dataKey: 'latest_message',
        title: '问题描述',
        minWidth: 280,
      },
      {
        key: 'shield_status',
        dataKey: 'shield_status',
        title: '屏蔽状态',
        width: 110,
        slots: { default: 'cell-status', header: 'header-status' },
      },
      {
        key: 'actions',
        dataKey: 'actions',
        title: '操作',
        width: 80,
        slots: { default: 'cell-actions' },
      },
    ] as any,
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
        }) =>
          listFindingsApi({
            ...filters,
            page: page.currentPage,
            pageSize: page.pageSize,
          }),
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

function handleSelection(rows: Finding[]) {
  selectedRows.value = rows;
}

function openApply() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请选择需要申请屏蔽的问题');
    return;
  }
  const responsibilityNames = new Set(
    selectedRows.value.map((item) => item.responsibility_name),
  );
  if (responsibilityNames.size > 1) {
    ElMessage.warning('一次只能提交同一责任田的问题');
    return;
  }
  const approver = applyApprovers.value[0];
  if (!approver) {
    ElMessage.warning('当前责任田未配置审批人员');
    return;
  }
  applyForm.value = { approver_id: approver.id, reason: '' };
  applyVisible.value = true;
}

async function submitApply() {
  if (!applyForm.value.approver_id || !applyForm.value.reason.trim()) {
    ElMessage.warning('请选择审批人并填写申请理由');
    return;
  }
  await createApplicationApi({
    approver_id: applyForm.value.approver_id,
    finding_ids: selectedRows.value.map((item) => item.id),
    reason: applyForm.value.reason.trim(),
  });
  applyVisible.value = false;
  selectedRows.value = [];
  reloadFindings();
  ElMessage.success('屏蔽申请已提交');
}

async function showDetail(row: Finding) {
  detail.value = await getFindingApi(row.id);
  detailVisible.value = true;
}

onMounted(() => {
  reloadFindings();
});
</script>

<template>
  <section class="findings-panel">
    <div class="panel-heading">
      <div>
        <h2>问题明细</h2>
        <p>按表头条件筛选问题，选择后批量提交屏蔽申请</p>
      </div>
      <div class="panel-actions">
        <ElInput
          v-model="filters.keyword"
          clearable
          class="keyword-input"
          placeholder="搜索规则、文件或问题描述"
          @keyup.enter="reloadFindings"
          @clear="reloadFindings"
        />
        <ElButton type="primary" @click="openApply">申请屏蔽</ElButton>
      </div>
    </div>

    <FindingGrid class="findings-grid" @selection-change="handleSelection">
      <template #header-project>
        <GovernanceHeaderFilter
          label="项目"
          :model-value="filters.project_id"
          :options="headerFilterOptions(projects)"
          @apply="(value) => applyHeaderFilter('project_id', value)"
          @clear="applyHeaderFilter('project_id', '')"
        />
      </template>
      <template #header-responsibility>
        <GovernanceHeaderFilter
          label="责任田"
          :model-value="filters.responsibility_id"
          :options="headerFilterOptions(responsibilities)"
          @apply="(value) => applyHeaderFilter('responsibility_id', value)"
          @clear="applyHeaderFilter('responsibility_id', '')"
        />
      </template>
      <template #header-severity>
        <GovernanceHeaderFilter
          label="严重级别"
          :model-value="filters.severity"
          :options="severityOptions"
          @apply="(value) => applyHeaderFilter('severity', value)"
          @clear="applyHeaderFilter('severity', '')"
        />
      </template>
      <template #header-tool>
        <GovernanceHeaderFilter
          v-model="filters.tool_name"
          label="扫描工具"
          placeholder="请输入工具名称"
          @apply="(value) => applyHeaderFilter('tool_name', value)"
          @clear="applyHeaderFilter('tool_name', '')"
        />
      </template>
      <template #header-status>
        <GovernanceHeaderFilter
          label="屏蔽状态"
          :model-value="filters.shield_status"
          :options="statusOptions"
          @apply="(value) => applyHeaderFilter('shield_status', value)"
          @clear="applyHeaderFilter('shield_status', '')"
        />
      </template>
      <template #cell-severity="{ row }">
        <ElTag :type="severityType(row.severity)" size="small">{{
          row.severity
        }}</ElTag>
      </template>
      <template #cell-status="{ row }">
        <ElTag :type="statusType(row.shield_status)" size="small">
          {{ row.shield_status }}
        </ElTag>
      </template>
      <template #cell-actions="{ row }">
        <ElButton link type="primary" @click="showDetail(row)">详情</ElButton>
      </template>
    </FindingGrid>

    <ElDialog v-model="applyVisible" title="申请屏蔽" width="520px">
      <ElForm :model="applyForm" label-width="80px">
        <ElFormItem label="审批人" required>
          <ElSelect
            v-model="applyForm.approver_id"
            class="w-full"
            placeholder="请选择审批人"
          >
            <ElOption
              v-for="item in applyApprovers"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="申请理由" required>
          <ElInput
            v-model="applyForm.reason"
            type="textarea"
            :rows="4"
            placeholder="请说明屏蔽原因和有效范围"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="applyVisible = false">取消</ElButton>
        <ElButton type="primary" @click="submitApply">提交申请</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="detailVisible" title="问题详情" width="820px">
      <ElDescriptions v-if="detail" :column="1" border>
        <ElDescriptionsItem label="稳定身份">{{
          detail.identity_key
        }}</ElDescriptionsItem>
        <ElDescriptionsItem label="Issue Key">{{
          detail.issue_key || '-'
        }}</ElDescriptionsItem>
        <ElDescriptionsItem label="规则"
          >{{ detail.rule_id }} / {{ detail.severity }}</ElDescriptionsItem
        >
        <ElDescriptionsItem label="文件位置"
          >{{ detail.file_path || detail.latest_file_path }}：{{
            detail.start_line || detail.latest_line
          }}-{{ detail.end_line || detail.latest_line }}</ElDescriptionsItem
        >
        <ElDescriptionsItem label="问题描述">{{
          detail.message || detail.latest_message
        }}</ElDescriptionsItem>
        <ElDescriptionsItem label="Identity">
          <pre>{{ JSON.stringify(detail.identity, null, 2) }}</pre>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="Evidence">
          <pre>{{ JSON.stringify(detail.evidence, null, 2) }}</pre>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="原始 Finding">
          <pre>{{ JSON.stringify(detail.raw_finding, null, 2) }}</pre>
        </ElDescriptionsItem>
      </ElDescriptions>
      <ElEmpty v-else description="暂无问题详情" />
    </ElDialog>
  </section>
</template>

<style scoped>
.findings-panel {
  display: flex;
  min-height: 100%;
  flex-direction: column;
}

.panel-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
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

.panel-actions {
  display: flex;
  gap: 10px;
}

.keyword-input {
  width: 260px;
}

.findings-grid {
  min-height: 560px;
  flex: 1;
}

pre {
  max-height: 220px;
  margin: 0;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 700px) {
  .panel-heading,
  .panel-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .keyword-input {
    width: 100%;
  }
}
</style>
