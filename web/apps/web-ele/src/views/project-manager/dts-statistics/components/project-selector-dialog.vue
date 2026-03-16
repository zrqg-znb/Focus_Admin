<script lang="ts" setup>
import { computed, ref, watch } from 'vue';

import {
  ElButton,
  ElCheckbox,
  ElDialog,
  ElInput,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
  ElTooltip,
} from 'element-plus';

export interface DtsStatisticsProjectOption {
  id: string;
  name: string;
  code: string;
  domain?: null | string;
  type?: null | string;
  enable_dts: boolean;
  version_c?: null | string;
  di_teams?: string[];
  config_complete: boolean;
  reason?: string;
}

interface Props {
  modelValue: boolean;
  loading?: boolean;
  projects: DtsStatisticsProjectOption[];
  selectedProjectIds: string[];
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
});

const emit = defineEmits<{
  (event: 'confirm', value: string[]): void;
  (event: 'update:modelValue', value: boolean): void;
}>();

const EMPTY_OPTION_VALUE = '__EMPTY__';

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
});

const keyword = ref('');
const selectedDomains = ref<string[]>([]);
const selectedTypes = ref<string[]>([]);
const tempSelectedIds = ref<string[]>([]);

function normalizeStringArray(values?: string[]) {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const item of values || []) {
    const text = String(item || '').trim();
    if (!text || seen.has(text)) {
      continue;
    }
    seen.add(text);
    result.push(text);
  }
  return result;
}

function normalizeDimensionValue(value?: null | string) {
  const text = String(value || '').trim();
  return text || EMPTY_OPTION_VALUE;
}

function displayDimensionValue(value?: null | string) {
  const text = String(value || '').trim();
  return text || '未分类';
}

const domainOptions = computed(() => {
  const seen = new Set<string>();
  const result: Array<{ label: string; value: string }> = [];
  props.projects.forEach((item) => {
    const value = normalizeDimensionValue(item.domain);
    if (seen.has(value)) {
      return;
    }
    seen.add(value);
    result.push({ label: displayDimensionValue(item.domain), value });
  });
  return result.sort((left, right) =>
    left.label.localeCompare(right.label, 'zh-CN'),
  );
});

const typeOptions = computed(() => {
  const seen = new Set<string>();
  const result: Array<{ label: string; value: string }> = [];
  props.projects.forEach((item) => {
    const value = normalizeDimensionValue(item.type);
    if (seen.has(value)) {
      return;
    }
    seen.add(value);
    result.push({ label: displayDimensionValue(item.type), value });
  });
  return result.sort((left, right) =>
    left.label.localeCompare(right.label, 'zh-CN'),
  );
});

const filteredProjects = computed(() => {
  const domainSet = new Set(selectedDomains.value);
  const typeSet = new Set(selectedTypes.value);
  const selectedSet = new Set(tempSelectedIds.value);
  const keywordText = keyword.value.trim().toLowerCase();
  return [...props.projects]
    .filter((item) => {
      if (keywordText) {
        const haystack = `${item.name || ''} ${item.code || ''}`.toLowerCase();
        if (!haystack.includes(keywordText)) {
          return false;
        }
      }
      if (
        domainSet.size > 0 &&
        !domainSet.has(normalizeDimensionValue(item.domain))
      ) {
        return false;
      }
      if (
        typeSet.size > 0 &&
        !typeSet.has(normalizeDimensionValue(item.type))
      ) {
        return false;
      }
      return true;
    })
    .sort((left, right) => {
      const leftSelected = selectedSet.has(left.id);
      const rightSelected = selectedSet.has(right.id);
      if (leftSelected !== rightSelected) {
        return leftSelected ? -1 : 1;
      }
      if (left.config_complete !== right.config_complete) {
        return left.config_complete ? -1 : 1;
      }
      return left.name.localeCompare(right.name, 'zh-CN');
    });
});

const selectedSet = computed(() => new Set(tempSelectedIds.value));
const selectableProjectIds = computed(() =>
  filteredProjects.value
    .filter((item) => item.config_complete)
    .map((item) => item.id),
);

function syncFromProps() {
  tempSelectedIds.value = normalizeStringArray(props.selectedProjectIds);
  keyword.value = '';
  selectedDomains.value = [];
  selectedTypes.value = [];
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      syncFromProps();
    }
  },
);

function toggleProject(id: string, checked: boolean) {
  const next = new Set(tempSelectedIds.value);
  if (checked) {
    next.add(id);
  } else {
    next.delete(id);
  }
  tempSelectedIds.value = [...next];
}

function handleSelectAllCurrent() {
  const next = new Set(tempSelectedIds.value);
  selectableProjectIds.value.forEach((item) => next.add(item));
  tempSelectedIds.value = [...next];
}

function handleClearCurrent() {
  const next = new Set(tempSelectedIds.value);
  filteredProjects.value.forEach((item) => next.delete(item.id));
  tempSelectedIds.value = [...next];
}

function handleClearAll() {
  tempSelectedIds.value = [];
}

function handleConfirm() {
  emit('confirm', normalizeStringArray(tempSelectedIds.value));
  dialogVisible.value = false;
}
</script>

<template>
  <ElDialog
    v-model="dialogVisible"
    title="选择项目"
    width="1120px"
    class="project-selector-dialog"
    append-to-body
    destroy-on-close
  >
    <div class="project-selector">
      <div class="project-selector__filters">
        <ElInput
          v-model="keyword"
          clearable
          placeholder="按项目名 / 项目编码筛选"
        />
        <ElSelect
          v-model="selectedDomains"
          multiple
          clearable
          collapse-tags
          collapse-tags-tooltip
          placeholder="按项目领域筛选"
        >
          <ElOption
            v-for="item in domainOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </ElSelect>
        <ElSelect
          v-model="selectedTypes"
          multiple
          clearable
          collapse-tags
          collapse-tags-tooltip
          placeholder="按项目类型筛选"
        >
          <ElOption
            v-for="item in typeOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </ElSelect>
      </div>

      <div class="project-selector__toolbar">
        <div class="project-selector__summary">
          <ElTag type="primary" effect="light">
            当前筛选 {{ filteredProjects.length }} 个
          </ElTag>
          <ElTag type="success" effect="light">
            已选 {{ tempSelectedIds.length }} 个
          </ElTag>
          <ElTag type="info" effect="plain">
            可查询 {{ selectableProjectIds.length }} 个
          </ElTag>
        </div>
        <div class="project-selector__actions">
          <ElButton @click="handleSelectAllCurrent">全选当前结果</ElButton>
          <ElButton @click="handleClearCurrent">清空当前结果</ElButton>
          <ElButton @click="handleClearAll">清空全部</ElButton>
        </div>
      </div>

      <ElTable
        v-loading="loading"
        :data="filteredProjects"
        row-key="id"
        height="480"
        class="project-selector__table"
        :row-class-name="
          ({ row }) => (row.config_complete ? '' : 'row-disabled')
        "
      >
        <ElTableColumn label="选择" width="88" align="center">
          <template #default="{ row }">
            <ElCheckbox
              :model-value="selectedSet.has(row.id)"
              :disabled="!row.config_complete"
              @change="(checked) => toggleProject(row.id, !!checked)"
            />
          </template>
        </ElTableColumn>
        <ElTableColumn label="状态" width="110" align="center">
          <template #default="{ row }">
            <ElTag
              :type="row.config_complete ? 'success' : 'info'"
              :effect="row.config_complete ? 'light' : 'plain'"
            >
              {{ row.config_complete ? '可查询' : '不可查询' }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="原因" min-width="200">
          <template #default="{ row }">
            <span v-if="row.config_complete" class="text-slate-400">-</span>
            <ElTooltip v-else :content="row.reason || ''" placement="top-start">
              <span class="text-amber-600">{{
                row.reason || '未完成配置'
              }}</span>
            </ElTooltip>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="name" label="项目名" min-width="220" />
        <ElTableColumn prop="code" label="项目编码" min-width="160" />
        <ElTableColumn label="领域" min-width="140">
          <template #default="{ row }">
            {{ displayDimensionValue(row.domain) }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="类型" min-width="140">
          <template #default="{ row }">
            {{ displayDimensionValue(row.type) }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="version_c" min-width="160">
          <template #default="{ row }">
            <span class="font-mono text-xs text-slate-600">
              {{ row.version_c || '-' }}
            </span>
          </template>
        </ElTableColumn>
        <ElTableColumn label="责任团队" width="100" align="center">
          <template #default="{ row }">
            {{ row.di_teams?.length || 0 }}
          </template>
        </ElTableColumn>
      </ElTable>
    </div>

    <template #footer>
      <div class="project-selector__footer">
        <span class="project-selector__footer-hint">
          仅允许选择已完成 DTS 配置（enable_dts + version_c + di_teams）的项目。
        </span>
        <div class="project-selector__footer-actions">
          <ElButton @click="dialogVisible = false">取消</ElButton>
          <ElButton type="primary" @click="handleConfirm">确认</ElButton>
        </div>
      </div>
    </template>
  </ElDialog>
</template>

<style scoped>
.project-selector {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.project-selector__filters {
  display: grid;
  grid-template-columns: minmax(220px, 1.2fr) repeat(2, minmax(180px, 1fr));
  gap: 12px;
}

.project-selector__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.project-selector__summary,
.project-selector__actions,
.project-selector__footer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.project-selector__table :deep(.el-table__cell) {
  vertical-align: middle;
}

.project-selector__table :deep(.row-disabled) {
  background: #f8fafc;
}

.project-selector__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.project-selector__footer-hint {
  color: #64748b;
  font-size: 12px;
}

@media (max-width: 768px) {
  .project-selector__filters {
    grid-template-columns: 1fr;
  }

  .project-selector__toolbar,
  .project-selector__footer {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
