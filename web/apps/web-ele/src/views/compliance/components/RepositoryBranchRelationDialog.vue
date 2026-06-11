<script lang="ts" setup>
import type {
  BranchItem,
  RepositoryBranchRelation,
} from '#/api/compliance/base';

import { computed, ref, watch } from 'vue';

import {
  ElButton,
  ElDialog,
  ElEmpty,
  ElPagination,
  ElSkeleton,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import { getRepositoryBranchesApi } from '#/api/compliance/base';

const props = defineProps<{
  modelValue: boolean;
  repositoryId?: string;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
}>();

const loading = ref(false);
const relation = ref<RepositoryBranchRelation>();
const branchPage = ref(1);
const branchPageSize = ref(8);
const fishboneFullscreen = ref(false);

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});

const sortedBranches = computed(() => relation.value?.branches || []);
const fishboneBranches = computed(() => sortedBranches.value);
const pagedBranches = computed(() => {
  const start = (branchPage.value - 1) * branchPageSize.value;
  return sortedBranches.value.slice(start, start + branchPageSize.value);
});
// 鱼骨图始终使用全量绑定分支，底部表格才跟随分页变化。
const fishboneWidth = computed(() =>
  Math.max(900, fishboneBranches.value.length * 176 + 96),
);

function branchTone(branch: BranchItem) {
  if (!branch.is_active) return 'archived';
  return branch.branch_type;
}

function formatDate(value?: null | string) {
  return value || '未知时间';
}

function formatPurpose(value?: null | string) {
  return value?.trim() || '暂无用途说明';
}

async function loadRelation() {
  if (!props.modelValue || !props.repositoryId) return;
  loading.value = true;
  try {
    relation.value = await getRepositoryBranchesApi(props.repositoryId);
    branchPage.value = 1;
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.modelValue, props.repositoryId],
  () => {
    if (props.modelValue) {
      loadRelation();
    } else {
      relation.value = undefined;
      branchPage.value = 1;
      fishboneFullscreen.value = false;
    }
  },
);
</script>

<template>
  <ElDialog
    v-model="visible"
    width="1080px"
    destroy-on-close
    class="repository-branch-dialog"
    title="代码库绑定分支"
  >
    <ElSkeleton :loading="loading" animated>
      <template v-if="relation">
        <div class="repo-header">
          <div>
            <div class="repo-title">{{ relation.repository.project_name }}</div>
            <div class="repo-meta">
              {{ relation.repository.project_id }} / {{ relation.repository.organization_name }}
              / {{ relation.repository.domain_label }}
            </div>
          </div>
          <div class="repo-stat">
            <span>绑定分支</span>
            <strong>{{ sortedBranches.length }}</strong>
          </div>
        </div>

        <template v-if="sortedBranches.length">
          <section
            class="fishbone-panel"
            :class="{ 'fishbone-panel-fullscreen': fishboneFullscreen }"
          >
            <div class="panel-title">
              <div>
                <span>分支演进鱼骨图</span>
                <small>按创建时间排序，未知日期置于末尾；展示全部绑定分支，可横向滑动查看</small>
              </div>
              <div class="panel-actions">
                <ElTag size="small" type="primary">{{ fishboneBranches.length }} 条</ElTag>
                <ElButton
                  size="small"
                  plain
                  @click="fishboneFullscreen = !fishboneFullscreen"
                >
                  {{ fishboneFullscreen ? '退出全屏' : '全屏查看' }}
                </ElButton>
              </div>
            </div>
            <div class="fishbone-scroll">
              <div class="fishbone-canvas" :style="{ width: `${fishboneWidth}px` }">
                <div class="fishbone-line" />
                <div class="fishbone-grid">
                  <div
                    v-for="(branch, index) in fishboneBranches"
                    :key="branch.id"
                    class="fishbone-node"
                    :class="[branchTone(branch), index % 2 === 0 ? 'above' : 'below']"
                  >
                    <article class="node-card">
                      <div class="node-card-head">
                        <span class="node-date">{{ formatDate(branch.created_date) }}</span>
                        <ElTag
                          size="small"
                          :type="branch.is_active ? 'success' : 'info'"
                        >
                          {{ branch.is_active ? '活跃' : '已归档' }}
                        </ElTag>
                      </div>
                      <strong :title="branch.branch_name">{{ branch.branch_name }}</strong>
                      <span class="node-kind">{{ branch.branch_type_label }} / {{ branch.domain_label }}</span>
                      <p :title="formatPurpose(branch.purpose)">
                        {{ formatPurpose(branch.purpose) }}
                      </p>
                    </article>
                    <div class="node-stem">
                      <span class="node-dot" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section class="branch-table-panel">
            <div class="panel-title">
              <div>
                <span>绑定分支列表</span>
                <small>归档分支保留绑定关系，但不参与漏合扫描配对</small>
              </div>
              <ElTag size="small" type="info">{{ sortedBranches.length }} 条</ElTag>
            </div>
            <ElTable :data="pagedBranches" border height="320">
              <ElTableColumn label="分支名称" min-width="180">
                <template #default="{ row }">
                  <div :class="{ 'archived-text': !row.is_active }">
                    <strong>{{ row.branch_name }}</strong>
                    <div class="branch-alias">{{ row.alias || '-' }}</div>
                  </div>
                </template>
              </ElTableColumn>
              <ElTableColumn label="类型" prop="branch_type_label" width="100" />
              <ElTableColumn label="创建日期" width="130">
                <template #default="{ row }">{{ formatDate(row.created_date) }}</template>
              </ElTableColumn>
              <ElTableColumn label="状态" width="100">
                <template #default="{ row }">
                  <ElTag :type="row.is_active ? 'success' : 'info'">
                    {{ row.is_active ? '活跃' : '已归档' }}
                  </ElTag>
                </template>
              </ElTableColumn>
              <ElTableColumn label="用途" min-width="220" prop="purpose" show-overflow-tooltip />
            </ElTable>
            <ElPagination
              v-if="sortedBranches.length > branchPageSize"
              v-model:current-page="branchPage"
              v-model:page-size="branchPageSize"
              background
              class="branch-pagination"
              layout="total, prev, pager, next, sizes"
              :page-sizes="[6, 8, 12, 20]"
              :total="sortedBranches.length"
            />
          </section>
        </template>

        <ElEmpty v-else description="该代码库暂未绑定分支" />
      </template>
    </ElSkeleton>
  </ElDialog>
</template>

<style scoped lang="less">
.repo-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: linear-gradient(180deg, var(--el-fill-color-extra-light), var(--el-bg-color));
}

.repo-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.repo-meta {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.repo-stat {
  min-width: 96px;
  padding: 9px 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  text-align: right;
  background: var(--el-fill-color-extra-light);
}

.repo-stat span {
  display: block;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.repo-stat strong {
  font-size: 24px;
  line-height: 1.2;
}

.fishbone-panel,
.branch-table-panel {
  margin-top: 14px;
  padding: 14px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-bg-color);
}

.fishbone-panel {
  transition:
    box-shadow 0.18s ease,
    transform 0.18s ease;
}

.fishbone-panel-fullscreen {
  position: fixed;
  inset: 48px 28px 28px;
  z-index: 3000;
  display: flex;
  flex-direction: column;
  margin: 0;
  background: var(--el-bg-color);
  box-shadow: 0 18px 46px rgb(15 23 42 / 22%);
}

.fishbone-panel-fullscreen .fishbone-scroll {
  flex: 1;
  min-height: 0;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  font-weight: 600;
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.panel-title small {
  display: block;
  margin-top: 3px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.fishbone-scroll {
  position: relative;
  min-height: 348px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background:
    linear-gradient(90deg, var(--el-fill-color-extra-light) 1px, transparent 1px) 0 0 / 28px 100%,
    var(--el-fill-color-blank);
  overflow-x: auto;
  overflow-y: visible;
  scrollbar-gutter: stable;
}

.fishbone-canvas {
  position: relative;
  min-height: 348px;
  padding: 16px 28px 18px;
}

.fishbone-line {
  position: absolute;
  top: 174px;
  left: 42px;
  right: 42px;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--el-border-color), transparent);
}

.fishbone-grid {
  position: relative;
  display: grid;
  grid-auto-columns: 168px;
  grid-auto-flow: column;
  column-gap: 8px;
  min-height: 314px;
}

.fishbone-node {
  --node-color: var(--el-color-info);

  display: grid;
  grid-template-rows: 134px 44px 134px;
  min-width: 0;
}

.node-card {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
  min-height: 124px;
  padding: 9px;
  border: 1px solid var(--node-color);
  border-left-width: 3px;
  border-radius: 6px;
  background: var(--el-bg-color);
  box-shadow: 0 6px 14px rgb(15 23 42 / 8%);
}

.above .node-card {
  grid-row: 1;
  align-self: end;
}

.below .node-card {
  grid-row: 3;
  align-self: start;
}

.node-stem {
  position: relative;
  grid-row: 2;
}

.node-stem::before {
  position: absolute;
  left: 50%;
  width: 2px;
  height: 44px;
  content: '';
  background: var(--node-color);
  transform: translateX(-50%);
}

.above .node-stem::before {
  top: 0;
}

.below .node-stem::before {
  bottom: 0;
}

.node-dot {
  position: absolute;
  top: 50%;
  left: 50%;
  z-index: 1;
  width: 12px;
  height: 12px;
  border: 2px solid var(--node-color);
  border-radius: 50%;
  background: var(--el-bg-color);
  transform: translate(-50%, -50%);
}

.node-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.node-date {
  min-width: 0;
  overflow-wrap: anywhere;
  font-size: 11px;
  font-weight: 700;
  color: var(--node-color);
}

.node-card strong {
  display: -webkit-box;
  min-width: 0;
  overflow: hidden;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  font-size: 12px;
  line-height: 1.35;
  color: var(--el-text-color-primary);
  word-break: break-word;
  -webkit-line-clamp: 2;
}

.node-kind {
  overflow: hidden;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-card :deep(.el-tag) {
  height: 20px;
  padding: 0 5px;
  font-size: 11px;
}

.node-card p {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  -webkit-box-orient: vertical;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  line-height: 1.42;
  overflow-wrap: anywhere;
  -webkit-line-clamp: 2;
}

.development {
  --node-color: var(--el-color-primary);
}

.trunk {
  --node-color: var(--el-color-success);
}

.release {
  --node-color: var(--el-color-warning);
}

.other {
  --node-color: var(--el-color-info);
}

.archived {
  --node-color: var(--el-text-color-placeholder);
}

.archived .node-card {
  background: var(--el-fill-color-extra-light);
  box-shadow: none;
}

.archived .node-card strong,
.archived .node-card p,
.archived .node-kind {
  color: var(--el-text-color-secondary);
}

.branch-alias {
  margin-top: 3px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.archived-text {
  color: var(--el-text-color-secondary);
}

.branch-pagination {
  justify-content: flex-end;
  margin-top: 12px;
}

@media (max-width: 900px) {
  .repo-header,
  .panel-title {
    align-items: flex-start;
    flex-direction: column;
  }

  .fishbone-canvas {
    padding: 14px 18px;
  }

  .fishbone-grid {
    grid-auto-columns: 164px;
  }

  .fishbone-panel-fullscreen {
    inset: 18px;
  }
}
</style>
