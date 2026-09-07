<!-- eslint-disable unicorn/prefer-ternary, vue/html-closing-bracket-newline, vue/multiline-html-element-content-newline -->
<script lang="ts" setup>
import type {
  GovernanceProject,
  GovernanceResponsibility,
  Overview,
} from '#/api/agent-tools/code-quality-governance';

import { computed, onMounted, ref } from 'vue';

import {
  ElButton,
  ElCard,
  ElDialog,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElSkeleton,
  ElSwitch,
  ElTag,
  ElTransfer,
} from 'element-plus';

import {
  createProjectApi,
  deleteLinkApi,
  getProjectOverviewApi,
  listProjectsApi,
  onboardProjectApi,
  updateProjectApi,
} from '#/api/agent-tools/code-quality-governance';

const props = defineProps<{
  refreshOptions: () => Promise<void>;
  responsibilities: GovernanceResponsibility[];
}>();

const emit = defineEmits<{ changed: [] }>();

const rows = ref<GovernanceProject[]>([]);
const selected = ref<GovernanceProject>();
const overview = ref<Overview>();
const keyword = ref('');
const activeOnly = ref(false);
const loading = ref(false);
const detailLoading = ref(false);
const dialog = ref(false);
const onboarding = ref(false);
const editing = ref(false);
const responsibilityIds = ref<string[]>([]);
const form = ref({
  name: '',
  code: '',
  description: '',
  is_active: true,
});

const filtered = computed(() => {
  const value = keyword.value.trim().toLowerCase();
  return rows.value.filter((item) => {
    const matchesKeyword =
      !value || `${item.name}${item.code}`.toLowerCase().includes(value);
    return matchesKeyword && (!activeOnly.value || item.is_active);
  });
});

const responsibilityOptions = computed(() =>
  props.responsibilities.map((item) => ({
    ...item,
    label: `${item.name} · ${item.code}`,
  })),
);

async function load() {
  loading.value = true;
  try {
    const result = await listProjectsApi({ pageSize: 100 });
    rows.value = result.items;
    if (selected.value) {
      const current = rows.value.find((item) => item.id === selected.value?.id);
      if (current) {
        await select(current);
        return;
      }
    }
    const firstProject = rows.value[0];
    if (firstProject) {
      await select(firstProject);
    } else {
      selected.value = undefined;
      overview.value = undefined;
    }
  } finally {
    loading.value = false;
  }
}

async function select(row: GovernanceProject) {
  selected.value = row;
  detailLoading.value = true;
  try {
    overview.value = await getProjectOverviewApi(row.id);
  } finally {
    detailLoading.value = false;
  }
}

function resetForm() {
  form.value = {
    name: '',
    code: '',
    description: '',
    is_active: true,
  };
  responsibilityIds.value = [];
}

function openCreate() {
  editing.value = false;
  resetForm();
  dialog.value = true;
}

function openEdit() {
  if (!selected.value) return;
  editing.value = true;
  form.value = {
    name: selected.value.name,
    code: selected.value.code,
    description: selected.value.description,
    is_active: selected.value.is_active,
  };
  responsibilityIds.value = [];
  dialog.value = true;
}

function openOnboarding() {
  responsibilityIds.value =
    overview.value?.responsibilities
      ?.filter((item) => item.is_active)
      .map((item) => item.responsibility_id) ?? [];
  onboarding.value = true;
}

async function save() {
  if (!form.value.name.trim() || !form.value.code.trim()) {
    ElMessage.warning('请填写项目名称和编码');
    return;
  }

  if (editing.value && selected.value) {
    await updateProjectApi(selected.value.id, form.value);
  } else {
    await createProjectApi({
      ...form.value,
      initial_responsibility_ids: responsibilityIds.value,
    });
  }

  dialog.value = false;
  await props.refreshOptions();
  await load();
  emit('changed');
  ElMessage.success(editing.value ? '项目已更新' : '项目已创建');
}

async function onboard() {
  if (!selected.value || !overview.value) {
    return;
  }

  const currentLinks = overview.value.responsibilities ?? [];
  const selectedIds = new Set(responsibilityIds.value);
  const removedLinks = currentLinks.filter(
    (item) => item.is_active && !selectedIds.has(item.responsibility_id),
  );

  await Promise.all([
    ...removedLinks.map((item) => deleteLinkApi(item.id)),
    responsibilityIds.value.length > 0
      ? onboardProjectApi(selected.value.id, {
          project_ids: [selected.value.id],
          responsibility_ids: responsibilityIds.value,
        })
      : Promise.resolve(),
  ]);
  onboarding.value = false;
  await select(selected.value);
  emit('changed');
  ElMessage.success('治理范围已更新');
}

onMounted(load);
</script>

<!-- eslint-disable vue/html-closing-bracket-newline, vue/multiline-html-element-content-newline -->
<template>
  <section class="center-panel">
    <header class="page-heading">
      <div>
        <span class="eyebrow">PROJECT CENTER</span>
        <h2>项目中心</h2>
        <p>
          从项目上下文查看责任田、问题、扫描与审批，不再在多个配置表之间跳转。
        </p>
      </div>
      <ElButton type="primary" @click="openCreate">新建项目</ElButton>
    </header>

    <div class="center-layout">
      <ElCard v-loading="loading" shadow="never" class="directory">
        <template #header>
          <div class="directory-tools">
            <ElInput
              v-model="keyword"
              clearable
              placeholder="搜索项目名称 / 编码"
            />
            <ElSwitch
              v-model="activeOnly"
              inline-prompt
              active-text="启用"
              inactive-text="全部"
            />
          </div>
        </template>

        <div v-if="filtered.length > 0" class="directory-list">
          <button
            v-for="row in filtered"
            :key="row.id"
            type="button"
            class="directory-item"
            :class="{ active: selected?.id === row.id }"
            @click="select(row)"
          >
            <span>
              <b>{{ row.name }}</b>
              <small>{{ row.code }}</small>
            </span>
            <ElTag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </ElTag>
          </button>
        </div>
        <ElEmpty v-else description="暂无项目" :image-size="48" />
      </ElCard>

      <ElCard v-if="overview || detailLoading" shadow="never" class="detail">
        <template #header>
          <div class="detail-heading">
            <div v-if="overview">
              <b>{{ overview.project?.name }}</b>
              <span>{{ overview.project?.code }}</span>
            </div>
            <ElSkeleton v-else :rows="1" animated />
            <div v-if="overview" class="detail-actions">
              <ElButton @click="openEdit">编辑资料</ElButton>
              <ElButton type="primary" @click="openOnboarding"
                >关联责任田</ElButton
              >
            </div>
          </div>
        </template>

        <div v-loading="detailLoading" class="detail-content">
          <template v-if="overview">
            <div class="detail-metrics">
              <div>
                <small>问题总量</small
                ><strong>{{ overview.finding_count }}</strong>
              </div>
              <div>
                <small>待治理</small
                ><strong class="danger">{{ overview.normal_count }}</strong>
              </div>
              <div>
                <small>待审批</small
                ><strong class="warning">{{
                  overview.pending_application_count
                }}</strong>
              </div>
              <div>
                <small>责任田</small
                ><strong>{{ overview.responsibilities?.length || 0 }}</strong>
              </div>
            </div>

            <h3>治理范围</h3>
            <div v-if="overview.responsibilities?.length" class="scope-list">
              <div
                v-for="link in overview.responsibilities"
                :key="link.id"
                class="scope-row"
              >
                <span
                  ><b>{{ link.responsibility_name }}</b
                  ><small
                    >最近扫描：{{ link.last_scan_at || '暂无' }}</small
                  ></span
                >
                <div>
                  <ElTag
                    size="small"
                    :type="link.normal_count ? 'danger' : 'success'"
                    >待治理 {{ link.normal_count }}</ElTag
                  ><ElTag size="small">问题 {{ link.finding_count }}</ElTag>
                </div>
              </div>
            </div>
            <ElEmpty v-else description="尚未关联责任田" :image-size="48" />

            <h3>最近扫描</h3>
            <div v-if="overview.recent_reports.length > 0" class="report-list">
              <div
                v-for="report in overview.recent_reports"
                :key="String(report.id)"
              >
                <span
                  >{{ report.responsibility_name }} /
                  {{ report.tool_name }}</span
                >
                <ElTag
                  :type="
                    report.complete === false
                      ? 'warning'
                      : report.status === 'failed'
                        ? 'danger'
                        : 'success'
                  "
                >
                  {{
                    report.complete === false
                      ? '未完成'
                      : report.status === 'failed'
                        ? '失败'
                        : '成功'
                  }}
                </ElTag>
              </div>
            </div>
            <ElEmpty v-else description="暂无扫描记录" :image-size="48" />
          </template>
        </div>
      </ElCard>
      <ElEmpty v-else description="请选择一个项目" class="detail empty" />
    </div>

    <ElDialog
      v-model="dialog"
      :title="editing ? '编辑项目' : '新建项目'"
      width="520px"
    >
      <ElForm label-width="90px">
        <ElFormItem label="项目名称" required
          ><ElInput v-model="form.name"
        /></ElFormItem>
        <ElFormItem label="项目编码" required
          ><ElInput v-model="form.code" :disabled="editing"
        /></ElFormItem>
        <ElFormItem label="描述"
          ><ElInput v-model="form.description" type="textarea" :rows="3"
        /></ElFormItem>
        <ElFormItem label="启用状态"
          ><ElSwitch v-model="form.is_active"
        /></ElFormItem>
        <ElFormItem v-if="!editing" label="初始责任田">
          <ElTransfer
            v-model="responsibilityIds"
            :data="responsibilityOptions"
            :titles="['可选责任田', '已选责任田']"
            filterable
            filter-placeholder="搜索责任田名称或编码"
            :props="{ key: 'id', label: 'label' }"
            class="scope-transfer"
          />
          <small class="form-hint">
            可搜索并批量选择，创建后仍可在项目详情中调整治理范围。
          </small>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialog = false">取消</ElButton>
        <ElButton type="primary" @click="save">{{
          editing ? '保存' : '完成创建'
        }}</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="onboarding" title="配置治理责任田" width="780px">
      <ElForm label-width="90px">
        <ElFormItem label="责任田" required>
          <ElTransfer
            v-model="responsibilityIds"
            :data="responsibilityOptions"
            :titles="['未关联责任田', '已关联责任田']"
            filterable
            filter-placeholder="搜索责任田名称或编码"
            :props="{ key: 'id', label: 'label' }"
            class="scope-transfer"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="onboarding = false">取消</ElButton>
        <ElButton type="primary" @click="onboard">保存治理范围</ElButton>
      </template>
    </ElDialog>
  </section>
</template>

<style scoped>
.center-panel {
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
}
.page-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
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
  max-width: 620px;
  margin: 6px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.center-layout {
  display: grid;
  grid-template-columns: clamp(280px, 20vw, 360px) minmax(0, 1fr);
  gap: 12px;
  flex: 1;
  min-height: 600px;
}
.directory,
.detail {
  border-color: var(--el-border-color-lighter);
}
.directory-tools {
  display: grid;
  gap: 10px;
}
.directory-list {
  display: grid;
  gap: 2px;
}
.directory-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 11px 4px;
  border: 0;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  background: transparent;
  text-align: left;
  cursor: pointer;
}
.directory-item.active {
  padding-left: 9px;
  border-left: 3px solid var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.directory-item span,
.detail-heading > div:first-child,
.scope-row > span {
  display: grid;
  gap: 4px;
}
.directory-item b,
.detail-heading b,
.scope-row b {
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 500;
}
.directory-item small,
.detail-heading span,
.scope-row small {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.detail {
  height: 100%;
  min-height: 600px;
}
.detail-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.detail-actions {
  display: flex;
  gap: 8px;
}
.detail-content {
  min-height: 500px;
}
.detail-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
.detail-metrics div {
  padding: 13px;
  background: var(--el-fill-color-light);
}
.detail-metrics small,
.detail-metrics strong {
  display: block;
}
.detail-metrics small {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.detail-metrics strong {
  margin-top: 8px;
  color: var(--el-text-color-primary);
  font-size: 22px;
}
.danger {
  color: var(--el-color-danger) !important;
}
.warning {
  color: var(--el-color-warning-dark) !important;
}
h3 {
  margin: 22px 0 8px;
  color: var(--el-text-color-primary);
  font-size: 14px;
}
.scope-row,
.report-list > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 0;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}
.scope-row > div {
  display: flex;
  gap: 6px;
}
.report-list > div > span {
  color: var(--el-text-color-regular);
  font-size: 13px;
}
.scope-transfer {
  width: 100%;
}
.scope-transfer :deep(.el-transfer-panel) {
  width: 300px;
}
.form-hint {
  display: block;
  margin-top: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.empty {
  height: 100%;
}
@media (max-width: 760px) {
  .center-layout {
    flex: initial;
    grid-template-columns: 1fr;
  }
  .detail-metrics {
    grid-template-columns: repeat(2, 1fr);
  }
  .detail-heading {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
