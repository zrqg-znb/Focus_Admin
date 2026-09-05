<!-- eslint-disable vue/html-closing-bracket-newline, vue/multiline-html-element-content-newline -->
<script lang="ts" setup>
import type { AuditTab } from './types';
import type {
  Application,
  UserOption,
} from '#/api/agent-tools/code-quality-governance';

import { onMounted, ref } from 'vue';

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
  ElTabPane,
  ElTag,
  ElTabs,
} from 'element-plus';

import {
  approveApplicationApi,
  getApplicationLogsApi,
  listApplicationsApi,
  rejectApplicationApi,
} from '#/api/agent-tools/code-quality-governance';
import { useZqTable } from '#/components/zq-table';

import GovernanceHeaderFilter from './header-filter.vue';

defineOptions({ name: 'CodeQualityGovernanceAudit' });

interface AuditLog {
  action?: string;
  comment?: string;
  created_at?: string;
  from_status?: string;
  id?: string;
  operator?: UserOption;
  to_status?: string;
}

const auditTab = ref<AuditTab>('my_audit');
const statusFilter = ref('');
const auditVisible = ref(false);
const detailVisible = ref(false);
const currentApplication = ref<Application>();
const auditComment = ref('');
const auditLogs = ref<AuditLog[]>([]);

const statusOptions = [
  { label: '待审批', value: 'Pending' },
  { label: '已通过', value: 'Approved' },
  { label: '已驳回', value: 'Rejected' },
];

function statusType(status: string) {
  if (status === 'Approved') return 'success';
  if (status === 'Rejected') return 'danger';
  return 'warning';
}

function applyStatusFilter(value: string) {
  statusFilter.value = value;
  void applicationGridApi.reload();
}

const [ApplicationGrid, applicationGridApi] = useZqTable<Application>({
  showSearchForm: false,
  separator: false,
  gridOptions: {
    border: true,
    columns: [
      {
        key: 'project_name',
        dataKey: 'project_name',
        title: '项目',
        minWidth: 150,
      },
      {
        key: 'responsibility_name',
        dataKey: 'responsibility_name',
        title: '责任田',
        minWidth: 150,
      },
      {
        key: 'severity',
        dataKey: 'severity',
        title: '级别',
        width: 100,
        slots: { default: 'cell-severity' },
      },
      { key: 'file_path', dataKey: 'file_path', title: '文件', minWidth: 220 },
      {
        key: 'applicant',
        dataKey: 'applicant',
        title: '申请人',
        width: 110,
        slots: { default: 'cell-applicant' },
      },
      {
        key: 'approver',
        dataKey: 'approver',
        title: '审批人',
        width: 110,
        slots: { default: 'cell-approver' },
      },
      { key: 'reason', dataKey: 'reason', title: '申请理由', minWidth: 240 },
      {
        key: 'status',
        dataKey: 'status',
        title: '状态',
        width: 100,
        slots: { default: 'cell-status', header: 'header-status' },
      },
      {
        key: 'actions',
        dataKey: 'actions',
        title: '操作',
        width: 120,
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
          listApplicationsApi({
            mode: auditTab.value,
            page: page.currentPage,
            pageSize: page.pageSize,
            status: statusFilter.value || undefined,
          }),
      },
    },
    stripe: true,
    toolbarConfig: {
      custom: true,
      refresh: true,
      search: false,
      zoom: true,
    },
  },
});

function changeTab() {
  void applicationGridApi.reload();
}

function openAudit(row: Application) {
  currentApplication.value = row;
  auditComment.value = '';
  auditVisible.value = true;
}

async function openDetail(row: Application) {
  currentApplication.value = row;
  auditLogs.value = (await getApplicationLogsApi(row.id)) as AuditLog[];
  detailVisible.value = true;
}

async function submitAudit(action: 'approve' | 'reject') {
  if (!currentApplication.value) return;
  await (action === 'approve'
    ? approveApplicationApi(currentApplication.value.id, auditComment.value)
    : rejectApplicationApi(currentApplication.value.id, auditComment.value));
  auditVisible.value = false;
  void applicationGridApi.reload();
  ElMessage.success(action === 'approve' ? '已通过屏蔽申请' : '已驳回屏蔽申请');
}

onMounted(() => {
  void applicationGridApi.reload();
});
</script>

<template>
  <section class="audit-panel">
    <div class="panel-heading">
      <div>
        <h2>屏蔽审核</h2>
        <p>处理责任田范围内的屏蔽申请，并保留完整审批历史</p>
      </div>
    </div>

    <ElTabs v-model="auditTab" class="audit-tabs" @tab-change="changeTab">
      <ElTabPane label="待我审批" name="my_audit" />
      <ElTabPane label="我的申请" name="my_apply" />
    </ElTabs>

    <ApplicationGrid class="audit-grid">
      <template #header-status>
        <GovernanceHeaderFilter
          label="状态"
          :model-value="statusFilter"
          :options="statusOptions"
          @apply="applyStatusFilter"
          @clear="applyStatusFilter('')"
        />
      </template>
      <template #cell-severity="{ row }">
        <ElTag
          :type="
            row.severity === 'blocker' || row.severity === 'critical'
              ? 'danger'
              : 'warning'
          "
          size="small"
        >
          {{ row.severity }}
        </ElTag>
      </template>
      <template #cell-applicant="{ row }">{{
        row.applicant?.name || '-'
      }}</template>
      <template #cell-approver="{ row }">{{
        row.approver?.name || '-'
      }}</template>
      <template #cell-status="{ row }">
        <ElTag :type="statusType(row.status)" size="small">{{
          row.status
        }}</ElTag>
      </template>
      <template #cell-actions="{ row }">
        <ElButton link type="primary" @click="openDetail(row)">详情</ElButton>
        <ElButton
          v-if="auditTab === 'my_audit' && row.status === 'Pending'"
          link
          type="primary"
          @click="openAudit(row)"
        >
          审批
        </ElButton>
      </template>
    </ApplicationGrid>

    <ElDialog v-model="auditVisible" title="审批屏蔽申请" width="520px">
      <ElForm label-width="80px">
        <ElFormItem label="申请理由">{{
          currentApplication?.reason || '-'
        }}</ElFormItem>
        <ElFormItem label="审批意见">
          <ElInput
            v-model="auditComment"
            type="textarea"
            :rows="4"
            placeholder="请输入审批意见"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="auditVisible = false">取消</ElButton>
        <ElButton type="danger" @click="submitAudit('reject')">驳回</ElButton>
        <ElButton type="primary" @click="submitAudit('approve')">通过</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="detailVisible" title="申请详情" width="820px">
      <ElDescriptions v-if="currentApplication" :column="2" border>
        <ElDescriptionsItem label="项目">{{
          currentApplication.project_name
        }}</ElDescriptionsItem>
        <ElDescriptionsItem label="责任田">{{
          currentApplication.responsibility_name
        }}</ElDescriptionsItem>
        <ElDescriptionsItem label="申请人">{{
          currentApplication.applicant?.name || '-'
        }}</ElDescriptionsItem>
        <ElDescriptionsItem label="审批人">{{
          currentApplication.approver?.name || '-'
        }}</ElDescriptionsItem>
        <ElDescriptionsItem label="规则">{{
          currentApplication.rule_id
        }}</ElDescriptionsItem>
        <ElDescriptionsItem label="文件">{{
          currentApplication.file_path
        }}</ElDescriptionsItem>
        <ElDescriptionsItem label="申请理由" :span="2">{{
          currentApplication.reason
        }}</ElDescriptionsItem>
        <ElDescriptionsItem label="审批意见" :span="2">{{
          currentApplication.audit_comment || '-'
        }}</ElDescriptionsItem>
      </ElDescriptions>
      <div class="audit-history">
        <div class="audit-history__title">审批历史</div>
        <div v-if="auditLogs.length > 0" class="audit-history__list">
          <div
            v-for="log in auditLogs"
            :key="log.id"
            class="audit-history__item"
          >
            <span>{{ log.operator?.name || '-' }}</span>
            <span
              >{{ log.from_status || '-' }} → {{ log.to_status || '-' }}</span
            >
            <span>{{ log.comment || '-' }}</span>
            <time>{{ log.created_at || '-' }}</time>
          </div>
        </div>
        <ElEmpty v-else description="暂无审批记录" :image-size="48" />
      </div>
    </ElDialog>
  </section>
</template>

<style scoped>
.audit-panel {
  display: flex;
  min-height: 100%;
  flex-direction: column;
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

.audit-tabs {
  margin: 12px 0 2px;
}

.audit-grid {
  min-height: 560px;
  flex: 1;
}

.audit-history {
  margin-top: 20px;
}

.audit-history__title {
  margin-bottom: 8px;
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 600;
}

.audit-history__list {
  border-top: 1px solid var(--el-border-color-lighter);
}

.audit-history__item {
  display: grid;
  grid-template-columns: 100px 150px 1fr 160px;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.audit-history__item time {
  color: var(--el-text-color-secondary);
  text-align: right;
}

@media (max-width: 760px) {
  .audit-history__item {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .audit-history__item time {
    text-align: left;
  }
}
</style>
