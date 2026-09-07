<script lang="ts" setup>
import type { MatrixData } from '#/api/agent-tools/code-quality-governance';

import { computed, onMounted, ref } from 'vue';

import {
  ElButton,
  ElCard,
  ElDialog,
  ElEmpty,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElTag,
  ElTransfer,
} from 'element-plus';

import {
  batchCreateLinksApi,
  createLinkApi,
  deleteLinkApi,
  getMatrixApi,
  updateLinkApi,
} from '#/api/agent-tools/code-quality-governance';

type MatrixFilter = 'all' | 'linked' | 'risk' | 'unlinked';

const data = ref<MatrixData>({
  projects: [],
  responsibilities: [],
  cells: [],
});
const loading = ref(false);
const batchLoading = ref(false);
const togglingKey = ref('');
const projectKeyword = ref('');
const responsibilityKeyword = ref('');
const relationFilter = ref<MatrixFilter>('all');
const selectedProjects = ref<string[]>([]);
const selectedResponsibilities = ref<string[]>([]);
const dialog = ref(false);

const cellMap = computed(
  () =>
    new Map(
      data.value.cells.map((item) => [
        `${item.project_id}:${item.responsibility_id}`,
        item,
      ]),
    ),
);

const projectOptions = computed(() =>
  data.value.projects.map((item) => ({
    ...item,
    label: `${item.name} · ${item.code}`,
  })),
);

const responsibilityOptions = computed(() =>
  data.value.responsibilities.map((item) => ({
    ...item,
    label: `${item.name} · ${item.code}`,
  })),
);

const filteredResponsibilities = computed(() => {
  const keyword = responsibilityKeyword.value.trim().toLowerCase();
  return data.value.responsibilities.filter(
    (item) =>
      !keyword || `${item.name}${item.code}`.toLowerCase().includes(keyword),
  );
});

function getCell(projectId: string, responsibilityId: string) {
  return cellMap.value.get(`${projectId}:${responsibilityId}`);
}

function isLinked(projectId: string, responsibilityId: string) {
  return getCell(projectId, responsibilityId)?.is_active === true;
}

function matchesRelationFilter(projectId: string) {
  if (relationFilter.value === 'all') {
    return true;
  }

  // 行筛选只检查当前可见责任田，保证搜索列与风险筛选保持一致。
  return filteredResponsibilities.value.some((responsibility) => {
    const cell = getCell(projectId, responsibility.id);
    const linked = cell?.is_active === true;
    if (relationFilter.value === 'linked') {
      return linked;
    }
    if (relationFilter.value === 'unlinked') {
      return !linked;
    }
    return linked && Boolean(cell?.normal_count);
  });
}

const visibleProjects = computed(() => {
  const keyword = projectKeyword.value.trim().toLowerCase();
  return data.value.projects.filter((project) => {
    const matchesKeyword =
      !keyword ||
      `${project.name}${project.code}`.toLowerCase().includes(keyword);
    return matchesKeyword && matchesRelationFilter(project.id);
  });
});

const visibleActiveLinkCount = computed(() =>
  visibleProjects.value.reduce(
    (count, project) =>
      count +
      filteredResponsibilities.value.filter((responsibility) =>
        isLinked(project.id, responsibility.id),
      ).length,
    0,
  ),
);

const visibleRiskLinkCount = computed(() =>
  visibleProjects.value.reduce(
    (count, project) =>
      count +
      filteredResponsibilities.value.filter(
        (responsibility) =>
          getCell(project.id, responsibility.id)?.is_active &&
          Boolean(getCell(project.id, responsibility.id)?.normal_count),
      ).length,
    0,
  ),
);

const activeLinkCount = computed(
  () => data.value.cells.filter((item) => item.is_active).length,
);

function resetBatchSelection() {
  selectedProjects.value = [];
  selectedResponsibilities.value = [];
}

function openBatchDialog() {
  resetBatchSelection();
  dialog.value = true;
}

async function load() {
  loading.value = true;
  try {
    data.value = await getMatrixApi();
  } finally {
    loading.value = false;
  }
}

async function toggle(projectId: string, responsibilityId: string) {
  const key = `${projectId}:${responsibilityId}`;
  if (togglingKey.value) {
    return;
  }

  const current = getCell(projectId, responsibilityId);
  togglingKey.value = key;
  try {
    if (current?.is_active) {
      await deleteLinkApi(current.id);
      ElMessage.success('治理关系已停用');
    } else if (current) {
      await updateLinkApi(current.id, {
        project_id: projectId,
        responsibility_id: responsibilityId,
        is_active: true,
        remark: current.remark,
      });
      ElMessage.success('治理关系已恢复');
    } else {
      await createLinkApi({
        project_id: projectId,
        responsibility_id: responsibilityId,
        is_active: true,
        remark: '',
      });
      ElMessage.success('治理关系已建立');
    }
    await load();
  } finally {
    togglingKey.value = '';
  }
}

async function batch() {
  if (
    selectedProjects.value.length === 0 ||
    selectedResponsibilities.value.length === 0
  ) {
    ElMessage.warning('请选择项目和责任田');
    return;
  }

  batchLoading.value = true;
  try {
    await batchCreateLinksApi({
      project_ids: selectedProjects.value,
      responsibility_ids: selectedResponsibilities.value,
    });
    dialog.value = false;
    resetBatchSelection();
    await load();
    ElMessage.success('批量关联完成');
  } finally {
    batchLoading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section>
    <header class="page-heading">
      <div>
        <span class="eyebrow">SCOPE MATRIX</span>
        <h2>治理范围矩阵</h2>
        <p>
          面向几十个项目和责任田的横向治理视图，支持搜索定位、风险筛选和批量建立关系。
        </p>
      </div>
      <ElButton type="primary" @click="openBatchDialog">批量关联</ElButton>
    </header>

    <ElCard v-loading="loading" shadow="never" class="matrix-card">
      <div class="matrix-toolbar">
        <ElInput
          v-model="projectKeyword"
          clearable
          placeholder="搜索项目名称 / 编码"
          class="toolbar-input"
        />
        <ElInput
          v-model="responsibilityKeyword"
          clearable
          placeholder="搜索责任田名称 / 编码"
          class="toolbar-input"
        />
        <ElSelect v-model="relationFilter" class="toolbar-select">
          <ElOption label="全部关系" value="all" />
          <ElOption label="只看已关联" value="linked" />
          <ElOption label="只看未关联" value="unlinked" />
          <ElOption label="只看有风险" value="risk" />
        </ElSelect>
      </div>

      <div class="matrix-summary" aria-label="矩阵统计">
        <div>
          <span>项目</span>
          <strong>{{ visibleProjects.length }}</strong>
          <small>/ {{ data.projects.length }} 个</small>
        </div>
        <div>
          <span>责任田</span>
          <strong>{{ filteredResponsibilities.length }}</strong>
          <small>/ {{ data.responsibilities.length }} 个</small>
        </div>
        <div>
          <span>已建立关系</span>
          <strong>{{ visibleActiveLinkCount }}</strong>
          <small>/ {{ activeLinkCount }} 个</small>
        </div>
        <div>
          <span>当前风险关系</span>
          <strong class="risk-number">{{ visibleRiskLinkCount }}</strong>
          <small>待治理大于 0</small>
        </div>
      </div>

      <div
        v-if="data.projects.length > 0 && data.responsibilities.length > 0"
        class="matrix-wrap"
      >
        <table
          v-if="
            visibleProjects.length > 0 && filteredResponsibilities.length > 0
          "
          class="matrix"
        >
          <thead>
            <tr>
              <th class="project-column">项目 / 责任田</th>
              <th
                v-for="item in filteredResponsibilities"
                :key="item.id"
                class="responsibility-column"
              >
                <span>{{ item.name }}</span>
                <small>{{ item.code }}</small>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="project in visibleProjects" :key="project.id">
              <th class="project-name">
                <b>{{ project.name }}</b>
                <small>{{ project.code }}</small>
              </th>
              <td
                v-for="item in filteredResponsibilities"
                :key="item.id"
                class="matrix-cell-wrapper"
              >
                <button
                  type="button"
                  class="matrix-cell"
                  :class="{
                    linked: isLinked(project.id, item.id),
                    risk: Boolean(getCell(project.id, item.id)?.normal_count),
                  }"
                  :disabled="togglingKey === `${project.id}:${item.id}`"
                  @click="toggle(project.id, item.id)"
                >
                  <template v-if="getCell(project.id, item.id)?.is_active">
                    <strong>
                      {{ getCell(project.id, item.id)?.finding_count }}
                    </strong>
                    <span>
                      待治理 {{ getCell(project.id, item.id)?.normal_count }}
                    </span>
                    <small>
                      {{
                        getCell(project.id, item.id)?.last_scan_at
                          ? '已扫描'
                          : '未扫描'
                      }}
                    </small>
                  </template>
                  <span v-else class="not-linked">未关联</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <ElEmpty
          v-else
          description="没有匹配当前筛选条件的关系"
          :image-size="56"
        />
      </div>
      <ElEmpty v-else description="请先创建项目和责任田" :image-size="64" />
    </ElCard>

    <ElDialog v-model="dialog" title="批量建立治理关系" width="780px">
      <div class="batch-intro">
        <span>一次选择多个项目和责任田，系统会建立所有交叉关系。</span>
        <ElTag type="info">适合批量初始化治理范围</ElTag>
      </div>
      <div class="batch-transfer">
        <div>
          <label>选择项目</label>
          <ElTransfer
            v-model="selectedProjects"
            :data="projectOptions"
            :titles="['可选项目', '已选项目']"
            filterable
            filter-placeholder="搜索项目名称或编码"
            :props="{ key: 'id', label: 'label' }"
          />
        </div>
        <div>
          <label>选择责任田</label>
          <ElTransfer
            v-model="selectedResponsibilities"
            :data="responsibilityOptions"
            :titles="['可选责任田', '已选责任田']"
            filterable
            filter-placeholder="搜索责任田名称或编码"
            :props="{ key: 'id', label: 'label' }"
          />
        </div>
      </div>
      <template #footer>
        <ElButton @click="dialog = false">取消</ElButton>
        <ElButton type="primary" :loading="batchLoading" @click="batch">
          确认关联
        </ElButton>
      </template>
    </ElDialog>
  </section>
</template>

<style scoped>
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
  max-width: 680px;
  margin: 6px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.matrix-card {
  border-color: var(--el-border-color-lighter);
}
.matrix-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}
.toolbar-input {
  width: 220px;
}
.toolbar-select {
  width: 150px;
}
.matrix-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  padding: 14px 0;
}
.matrix-summary div {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 10px 12px;
  background: var(--el-fill-color-light);
}
.matrix-summary span,
.matrix-summary small {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.matrix-summary strong {
  color: var(--el-text-color-primary);
  font-size: 20px;
  font-weight: 600;
}
.matrix-summary .risk-number {
  color: var(--el-color-danger);
}
.matrix-wrap {
  min-height: 320px;
  max-height: min(620px, calc(100vh - 370px));
  overflow: auto;
  border: 1px solid var(--el-border-color-lighter);
}
.matrix {
  min-width: max-content;
  border-collapse: separate;
  border-spacing: 0;
}
.matrix th,
.matrix td {
  border-right: 1px solid var(--el-border-color-lighter);
  border-bottom: 1px solid var(--el-border-color-lighter);
  text-align: center;
}
.matrix thead th {
  position: sticky;
  top: 0;
  z-index: 3;
  height: 58px;
  min-width: 126px;
  padding: 8px 10px;
  color: var(--el-text-color-primary);
  background: var(--el-fill-color-light);
  font-size: 12px;
  font-weight: 600;
}
.matrix thead th span,
.matrix thead small,
.project-name b,
.project-name small {
  display: block;
}
.matrix thead small,
.project-name small {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  font-weight: 400;
}
.project-column {
  position: sticky !important;
  left: 0;
  z-index: 5 !important;
  width: 190px;
  min-width: 190px !important;
  text-align: left !important;
}
.project-name {
  position: sticky;
  left: 0;
  z-index: 2;
  width: 190px;
  min-width: 190px;
  padding: 10px 12px;
  background: var(--el-fill-color-lighter);
  text-align: left !important;
}
.project-name b {
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 500;
}
.matrix-cell-wrapper {
  width: 126px;
  min-width: 126px;
  padding: 4px;
  background: var(--el-bg-color);
}
.matrix-cell {
  display: grid;
  place-items: center;
  gap: 3px;
  width: 100%;
  min-height: 72px;
  padding: 8px;
  border: 1px solid transparent;
  border-radius: 4px;
  background: transparent;
  cursor: pointer;
}
.matrix-cell:hover:not(:disabled) {
  border-color: var(--el-color-primary-light-5);
  background: var(--el-color-primary-light-9);
}
.matrix-cell:disabled {
  cursor: wait;
  opacity: 0.6;
}
.matrix-cell.linked {
  background: var(--el-color-success-light-9);
}
.matrix-cell.risk {
  background: var(--el-color-danger-light-9);
}
.matrix-cell strong {
  color: var(--el-text-color-primary);
  font-size: 18px;
}
.matrix-cell span,
.matrix-cell small {
  color: var(--el-text-color-secondary);
  font-size: 11px;
}
.not-linked {
  color: var(--el-text-color-placeholder) !important;
}
.batch-intro {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.batch-transfer {
  display: grid;
  gap: 18px;
}
.batch-transfer > div {
  display: grid;
  gap: 8px;
}
.batch-transfer label {
  color: var(--el-text-color-regular);
  font-size: 13px;
  font-weight: 500;
}
.batch-transfer :deep(.el-transfer) {
  width: 100%;
}
.batch-transfer :deep(.el-transfer-panel) {
  width: calc(50% - 32px);
}
@media (max-width: 820px) {
  .page-heading,
  .matrix-toolbar,
  .batch-intro {
    align-items: stretch;
    flex-direction: column;
  }
  .toolbar-input,
  .toolbar-select {
    width: 100%;
  }
  .matrix-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
