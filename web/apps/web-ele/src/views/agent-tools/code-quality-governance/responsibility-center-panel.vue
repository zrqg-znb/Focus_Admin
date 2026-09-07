<!-- eslint-disable unicorn/prefer-ternary, vue/html-closing-bracket-newline, vue/multiline-html-element-content-newline -->
<script lang="ts" setup>
import type {
  GovernanceProject,
  GovernanceResponsibility,
  Overview,
  UserOption,
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
  ElOption,
  ElSelect,
  ElSwitch,
  ElTag,
  ElTransfer,
} from 'element-plus';

import {
  addCaretakerApi,
  batchCreateLinksApi,
  createResponsibilityApi,
  deleteLinkApi,
  getResponsibilityOverviewApi,
  listResponsibilitiesApi,
  removeCaretakerApi,
  updateResponsibilityApi,
} from '#/api/agent-tools/code-quality-governance';

const props = defineProps<{
  projects: GovernanceProject[];
  refreshOptions: () => Promise<void>;
  users: UserOption[];
}>();

const emit = defineEmits<{ changed: [] }>();

const rows = ref<GovernanceResponsibility[]>([]);
const selected = ref<GovernanceResponsibility>();
const overview = ref<Overview>();
const keyword = ref('');
const loading = ref(false);
const detailLoading = ref(false);
const dialog = ref(false);
const caretakerDialog = ref(false);
const projectBindingDialog = ref(false);
const editing = ref(false);
const caretakerId = ref('');
const projectIds = ref<string[]>([]);
const form = ref({
  name: '',
  code: '',
  description: '',
  is_active: true,
  caretaker_ids: [] as string[],
});

const filtered = computed(() => {
  const value = keyword.value.trim().toLowerCase();
  return rows.value.filter(
    (item) =>
      !value || `${item.name}${item.code}`.toLowerCase().includes(value),
  );
});

const projectOptions = computed(() =>
  props.projects.map((item) => ({
    ...item,
    label: `${item.name} · ${item.code}`,
  })),
);

async function load() {
  loading.value = true;
  try {
    const result = await listResponsibilitiesApi({ pageSize: 100 });
    rows.value = result.items;
    if (selected.value) {
      const current = rows.value.find((item) => item.id === selected.value?.id);
      if (current) {
        await select(current);
        return;
      }
    }
    const firstResponsibility = rows.value[0];
    if (firstResponsibility) {
      await select(firstResponsibility);
    } else {
      selected.value = undefined;
      overview.value = undefined;
    }
  } finally {
    loading.value = false;
  }
}

async function select(row: GovernanceResponsibility) {
  selected.value = row;
  detailLoading.value = true;
  try {
    overview.value = await getResponsibilityOverviewApi(row.id);
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
    caretaker_ids: [],
  };
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
    caretaker_ids: selected.value.caretakers.map((item) => item.id),
  };
  dialog.value = true;
}

async function save() {
  if (!form.value.name.trim() || !form.value.code.trim()) {
    ElMessage.warning('请填写责任田名称和编码');
    return;
  }

  const payload = {
    ...form.value,
    caretaker_ids: form.value.caretaker_ids,
  };
  if (editing.value && selected.value) {
    await updateResponsibilityApi(selected.value.id, payload);
  } else {
    await createResponsibilityApi(payload);
  }

  dialog.value = false;
  await load();
  await props.refreshOptions();
  emit('changed');
  ElMessage.success(editing.value ? '责任田已更新' : '责任田已创建');
}

function openProjectBinding() {
  projectIds.value =
    overview.value?.projects
      ?.filter((item) => item.is_active)
      .map((item) => item.project_id) ?? [];
  projectBindingDialog.value = true;
}

async function bindProjects() {
  if (!selected.value || !overview.value) {
    return;
  }

  const currentLinks = overview.value.projects ?? [];
  const selectedIds = new Set(projectIds.value);
  const removedLinks = currentLinks.filter(
    (item) => item.is_active && !selectedIds.has(item.project_id),
  );

  await Promise.all([
    ...removedLinks.map((item) => deleteLinkApi(item.id)),
    projectIds.value.length > 0
      ? batchCreateLinksApi({
          project_ids: projectIds.value,
          responsibility_ids: [selected.value.id],
        })
      : Promise.resolve(),
  ]);

  projectBindingDialog.value = false;
  await select(selected.value);
  await props.refreshOptions();
  emit('changed');
  ElMessage.success('关联项目已更新');
}

async function addCaretaker() {
  if (!selected.value || !caretakerId.value) {
    ElMessage.warning('请选择系统用户');
    return;
  }

  await addCaretakerApi(selected.value.id, { user_id: caretakerId.value });
  caretakerDialog.value = false;
  caretakerId.value = '';
  await load();
  ElMessage.success('看护人已添加');
}

async function removeCaretaker(userId: string) {
  if (!selected.value) return;
  await removeCaretakerApi(selected.value.id, userId);
  await load();
  ElMessage.success('看护人已移除');
}

onMounted(load);
</script>

<!-- eslint-disable vue/html-closing-bracket-newline, vue/multiline-html-element-content-newline -->
<template>
  <section class="center-panel">
    <header class="page-heading">
      <div>
        <span class="eyebrow">RESPONSIBILITY CENTER</span>
        <h2>责任田中心</h2>
        <p>以长期责任域为中心管理看护人、项目范围和横向问题负载。</p>
      </div>
      <ElButton type="primary" @click="openCreate">新建责任田</ElButton>
    </header>

    <div class="center-layout">
      <ElCard v-loading="loading" shadow="never" class="directory">
        <template #header>
          <ElInput
            v-model="keyword"
            clearable
            placeholder="搜索责任田名称 / 编码"
          />
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
              <small>{{ row.code }} · {{ row.caretaker_count }} 名看护人</small>
            </span>
            <ElTag size="small" :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '停用' }}
            </ElTag>
          </button>
        </div>
        <ElEmpty v-else description="暂无责任田" :image-size="48" />
      </ElCard>

      <ElCard
        v-if="overview"
        v-loading="detailLoading"
        shadow="never"
        class="detail"
      >
        <template #header>
          <div class="detail-heading">
            <div>
              <b>{{ overview.responsibility?.name }}</b>
              <span>{{ overview.responsibility?.code }}</span>
            </div>
            <div class="detail-actions">
              <ElButton @click="openEdit">编辑资料</ElButton>
              <ElButton @click="openProjectBinding">关联项目</ElButton>
              <ElButton type="primary" @click="caretakerDialog = true">
                添加看护人
              </ElButton>
            </div>
          </div>
        </template>

        <div class="detail-content">
          <div class="detail-metrics">
            <div>
              <small>关联项目</small
              ><strong>{{ overview.projects?.length || 0 }}</strong>
            </div>
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
          </div>

          <h3>看护人</h3>
          <div
            v-if="overview.responsibility?.caretakers.length"
            class="caretaker-list"
          >
            <div
              v-for="person in overview.responsibility.caretakers"
              :key="person.id"
              class="caretaker"
            >
              <span
                ><b>{{ person.name }}</b
                ><small>{{ person.username }}</small></span
              >
              <ElButton link type="danger" @click="removeCaretaker(person.id)"
                >移除</ElButton
              >
            </div>
          </div>
          <ElEmpty v-else description="暂未配置看护人" :image-size="48" />

          <div class="section-heading">
            <h3>关联项目负载</h3>
            <ElButton link type="primary" @click="openProjectBinding">
              管理关联项目
            </ElButton>
          </div>
          <div v-if="overview.projects?.length" class="scope-list">
            <div
              v-for="link in overview.projects"
              :key="link.id"
              class="scope-row"
            >
              <span
                ><b>{{ link.project_name }}</b
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
          <ElEmpty v-else description="尚未关联项目" :image-size="48" />
        </div>
      </ElCard>
      <ElEmpty v-else description="请选择一个责任田" class="detail empty" />
    </div>

    <ElDialog
      v-model="dialog"
      :title="editing ? '编辑责任田' : '新建责任田'"
      width="520px"
    >
      <ElForm label-width="90px">
        <ElFormItem label="责任田名称" required
          ><ElInput v-model="form.name"
        /></ElFormItem>
        <ElFormItem label="责任田编码" required
          ><ElInput v-model="form.code" :disabled="editing"
        /></ElFormItem>
        <ElFormItem label="描述"
          ><ElInput v-model="form.description" type="textarea" :rows="3"
        /></ElFormItem>
        <ElFormItem label="启用状态"
          ><ElSwitch v-model="form.is_active"
        /></ElFormItem>
        <ElFormItem label="看护人">
          <ElSelect
            v-model="form.caretaker_ids"
            multiple
            class="full"
            placeholder="可选，后续可继续添加"
          >
            <ElOption
              v-for="item in props.users"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialog = false">取消</ElButton>
        <ElButton type="primary" @click="save">{{
          editing ? '保存' : '完成创建'
        }}</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="caretakerDialog" title="添加看护人" width="420px">
      <ElSelect v-model="caretakerId" class="full" placeholder="选择系统用户">
        <ElOption
          v-for="item in props.users"
          :key="item.id"
          :label="item.name"
          :value="item.id"
        />
      </ElSelect>
      <template #footer>
        <ElButton @click="caretakerDialog = false">取消</ElButton>
        <ElButton type="primary" @click="addCaretaker">添加</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="projectBindingDialog" title="配置关联项目" width="780px">
      <div class="binding-intro">
        <b>为 {{ overview?.responsibility?.name }} 配置治理范围</b>
        <span>支持搜索项目名称或编码，并在一次操作中批量调整关联关系。</span>
      </div>
      <ElTransfer
        v-model="projectIds"
        :data="projectOptions"
        :titles="['未关联项目', '已关联项目']"
        filterable
        filter-placeholder="搜索项目名称或编码"
        :props="{ key: 'id', label: 'label' }"
        class="scope-transfer"
      />
      <template #footer>
        <ElButton @click="projectBindingDialog = false">取消</ElButton>
        <ElButton type="primary" @click="bindProjects">保存关联范围</ElButton>
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
.caretaker > span,
.scope-row > span {
  display: grid;
  gap: 4px;
}
.directory-item b,
.detail-heading b,
.caretaker b,
.scope-row b {
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 500;
}
.directory-item small,
.detail-heading span,
.caretaker small,
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
.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.section-heading h3 {
  margin-bottom: 8px;
}
.caretaker,
.scope-row {
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
.full {
  width: 100%;
}
.binding-intro {
  display: grid;
  gap: 6px;
  margin-bottom: 16px;
}
.binding-intro b {
  color: var(--el-text-color-primary);
  font-size: 14px;
}
.binding-intro span {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.scope-transfer {
  width: 100%;
}
.scope-transfer :deep(.el-transfer-panel) {
  width: 300px;
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
