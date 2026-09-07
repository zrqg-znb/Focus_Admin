<!-- eslint-disable vue/html-closing-bracket-newline, vue/multiline-html-element-content-newline -->
<script lang="ts" setup>
import type {
  GovernanceLink,
  GovernanceProject,
} from '#/api/agent-tools/code-quality-governance';

import { computed, onMounted, ref } from 'vue';

import {
  ElButton,
  ElCard,
  ElEmpty,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
  ElUpload,
} from 'element-plus';

import {
  listLinksApi,
  listReportsApi,
  uploadReportApi,
} from '#/api/agent-tools/code-quality-governance';

const props = defineProps<{ projects: GovernanceProject[] }>();

const projectId = ref('');
const responsibilityId = ref('');
const toolName = ref('');
const file = ref<File>();
const links = ref<GovernanceLink[]>([]);
const reports = ref<Record<string, unknown>[]>([]);
const loading = ref(false);
const reportsLoading = ref(false);

const availableResponsibilities = computed(() =>
  links.value.filter(
    (item) => item.project_id === projectId.value && item.is_active,
  ),
);

function beforeUpload(rawFile: File) {
  file.value = rawFile;
  return false;
}

async function loadReports() {
  reportsLoading.value = true;
  try {
    const result = await listReportsApi({
      pageSize: 50,
      project_id: projectId.value || undefined,
      responsibility_id: responsibilityId.value || undefined,
    });
    reports.value = result.items;
  } finally {
    reportsLoading.value = false;
  }
}

async function upload() {
  if (
    !projectId.value ||
    !responsibilityId.value ||
    !toolName.value.trim() ||
    !file.value
  ) {
    ElMessage.warning('请选择项目、已关联责任田、工具并上传 JSON');
    return;
  }

  loading.value = true;
  try {
    const form = new FormData();
    form.append('project_id', projectId.value);
    form.append('responsibility_id', responsibilityId.value);
    form.append('tool_name', toolName.value.trim());
    form.append('file', file.value);
    await uploadReportApi(form);
    file.value = undefined;
    await loadReports();
    ElMessage.success('扫描报告已接入');
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  const result = await listLinksApi({ pageSize: 100 });
  links.value = result.items;
  await loadReports();
});
</script>

<!-- eslint-disable vue/html-closing-bracket-newline, vue/multiline-html-element-content-newline -->
<template>
  <section>
    <header class="page-heading">
      <div>
        <span class="eyebrow">SCAN INGESTION</span>
        <h2>扫描接入中心</h2>
        <p>
          扫描结果必须进入已建立的项目 ×
          责任田关系，解析失败会保留报告但不会生成半成品问题。
        </p>
      </div>
    </header>

    <ElCard shadow="never" class="ingest-card">
      <div class="ingest-grid">
        <div>
          <label>项目</label>
          <ElSelect
            v-model="projectId"
            class="full"
            clearable
            @change="responsibilityId = ''"
          >
            <ElOption
              v-for="item in props.projects"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </ElSelect>
        </div>
        <div>
          <label>已关联责任田</label>
          <ElSelect
            v-model="responsibilityId"
            class="full"
            clearable
            :disabled="!projectId"
          >
            <ElOption
              v-for="item in availableResponsibilities"
              :key="item.responsibility_id"
              :label="item.responsibility_name"
              :value="item.responsibility_id"
            />
          </ElSelect>
        </div>
        <div>
          <label>扫描工具</label>
          <ElInput
            v-model="toolName"
            class="full"
            placeholder="例如 third-party-scan"
          />
        </div>
        <div>
          <label>JSON 报告</label>
          <ElUpload
            :before-upload="beforeUpload"
            :limit="1"
            accept=".json"
            :auto-upload="false"
          >
            <ElButton>选择文件</ElButton>
            <template #tip>
              <span class="upload-tip">{{
                file?.name || '仅支持 JSON，项目责任田未关联时不可入库'
              }}</span>
            </template>
          </ElUpload>
        </div>
      </div>
      <div class="ingest-footer">
        <ElTag
          v-if="projectId && availableResponsibilities.length === 0"
          type="warning"
        >
          当前项目暂无有效责任田关系，请先去矩阵建立
        </ElTag>
        <span v-else class="ingest-hint">入库前会校验项目与责任田关系</span>
        <ElButton type="primary" :loading="loading" @click="upload"
          >确认接入</ElButton
        >
      </div>
    </ElCard>

    <ElCard v-loading="reportsLoading" shadow="never" class="report-card">
      <template #header>接入历史</template>
      <ElTable v-if="reports.length > 0" :data="reports" stripe>
        <ElTableColumn prop="project_name" label="项目" min-width="150" />
        <ElTableColumn
          prop="responsibility_name"
          label="责任田"
          min-width="150"
        />
        <ElTableColumn prop="tool_name" label="工具" width="140" />
        <ElTableColumn prop="finding_count" label="问题" width="80" />
        <ElTableColumn label="状态" width="110">
          <template #default="scope">
            <ElTag
              :type="
                scope.row.complete === false
                  ? 'warning'
                  : scope.row.status === 'failed'
                    ? 'danger'
                    : 'success'
              "
            >
              {{
                scope.row.complete === false
                  ? '未完成'
                  : scope.row.status === 'failed'
                    ? '失败'
                    : '成功'
              }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="created_at" label="接入时间" min-width="180" />
      </ElTable>
      <ElEmpty v-else description="暂无扫描报告" />
    </ElCard>
  </section>
</template>

<style scoped>
.page-heading {
  margin-bottom: 16px;
}
.eyebrow {
  color: var(--el-color-primary);
  font-size: 11px;
  letter-spacing: 0.12em;
}
h2 {
  margin: 5px 0 0;
  color: var(--el-text-color-primary);
  font-size: 22px;
}
.page-heading p {
  margin: 6px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.ingest-card,
.report-card {
  margin-bottom: 12px;
  border-color: var(--el-border-color-lighter);
}
.ingest-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.ingest-grid > div {
  display: grid;
  align-content: start;
  gap: 7px;
}
.ingest-grid label {
  color: var(--el-text-color-regular);
  font-size: 12px;
}
.full {
  width: 100%;
}
.upload-tip {
  display: block;
  margin-top: 5px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.ingest-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 20px;
  padding-top: 14px;
  border-top: 1px solid var(--el-border-color-extra-light);
}
.ingest-hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
@media (max-width: 900px) {
  .ingest-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 600px) {
  .ingest-grid {
    grid-template-columns: 1fr;
  }
  .ingest-footer {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
