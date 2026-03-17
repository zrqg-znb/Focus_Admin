<script lang="ts" setup>
import { computed, ref, watch } from 'vue';

import {
  ElButton,
  ElCheckbox,
  ElDialog,
  ElEmpty,
  ElInput,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

interface TeamOption {
  label: string;
  value: string;
}

interface Props {
  modelValue: boolean;
  loading?: boolean;
  teams: TeamOption[];
  selectedTeamValues: string[];
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
});

const emit = defineEmits<{
  (event: 'confirm', value: string[]): void;
  (event: 'update:modelValue', value: boolean): void;
}>();

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
});

const keyword = ref('');
const tempSelectedValues = ref<string[]>([]);

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

const filteredTeams = computed(() => {
  const keywordText = keyword.value.trim().toLowerCase();
  const selectedSet = new Set(tempSelectedValues.value);
  return [...props.teams]
    .filter((item) => {
      if (!keywordText) {
        return true;
      }
      return item.label.toLowerCase().includes(keywordText);
    })
    .sort((left, right) => {
      const leftSelected = selectedSet.has(left.value);
      const rightSelected = selectedSet.has(right.value);
      if (leftSelected !== rightSelected) {
        return leftSelected ? -1 : 1;
      }
      return left.label.localeCompare(right.label, 'zh-CN');
    });
});

const selectedSet = computed(() => new Set(tempSelectedValues.value));
const selectableTeamValues = computed(() =>
  filteredTeams.value.map((item) => item.value),
);

function syncFromProps() {
  tempSelectedValues.value = normalizeStringArray(props.selectedTeamValues);
  keyword.value = '';
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      syncFromProps();
    }
  },
);

function toggleTeam(value: string, checked: boolean) {
  const next = new Set(tempSelectedValues.value);
  if (checked) {
    next.add(value);
  } else {
    next.delete(value);
  }
  tempSelectedValues.value = [...next];
}

function handleSelectAllCurrent() {
  const next = new Set(tempSelectedValues.value);
  selectableTeamValues.value.forEach((item) => next.add(item));
  tempSelectedValues.value = [...next];
}

function handleClearCurrent() {
  const next = new Set(tempSelectedValues.value);
  filteredTeams.value.forEach((item) => next.delete(item.value));
  tempSelectedValues.value = [...next];
}

function handleClearAll() {
  tempSelectedValues.value = [];
}

function handleConfirm() {
  emit('confirm', normalizeStringArray(tempSelectedValues.value));
  dialogVisible.value = false;
}
</script>

<template>
  <ElDialog
    v-model="dialogVisible"
    title="选择责任团队"
    width="720px"
    class="team-selector-dialog"
    append-to-body
    destroy-on-close
  >
    <div class="team-selector">
      <div class="team-selector__filters">
        <ElInput v-model="keyword" clearable placeholder="按团队名称筛选" />
      </div>

      <div class="team-selector__toolbar">
        <div class="team-selector__summary">
          <ElTag type="primary" effect="light">
            当前筛选 {{ filteredTeams.length }} 个
          </ElTag>
          <ElTag type="success" effect="light">
            已选 {{ tempSelectedValues.length }} 个
          </ElTag>
        </div>
        <div class="team-selector__actions">
          <ElButton @click="handleSelectAllCurrent">全选当前结果</ElButton>
          <ElButton @click="handleClearCurrent">清空当前结果</ElButton>
          <ElButton @click="handleClearAll">清空全部</ElButton>
        </div>
      </div>

      <ElTable
        v-if="filteredTeams.length > 0"
        v-loading="loading"
        :data="filteredTeams"
        row-key="value"
        height="420"
        class="team-selector__table"
      >
        <ElTableColumn label="选择" width="88" align="center">
          <template #default="{ row }">
            <ElCheckbox
              :model-value="selectedSet.has(row.value)"
              @change="(checked) => toggleTeam(row.value, !!checked)"
            />
          </template>
        </ElTableColumn>
        <ElTableColumn prop="label" label="责任团队" min-width="220" />
      </ElTable>

      <div v-else class="team-selector__empty">
        <ElEmpty description="当前项目下暂无可选责任团队" />
      </div>
    </div>

    <template #footer>
      <div class="team-selector__footer">
        <span class="team-selector__footer-hint">
          团队选项根据当前已选项目动态生成并自动去重。
        </span>
        <div class="team-selector__footer-actions">
          <ElButton @click="dialogVisible = false">取消</ElButton>
          <ElButton type="primary" @click="handleConfirm">确认</ElButton>
        </div>
      </div>
    </template>
  </ElDialog>
</template>

<style scoped>
.team-selector {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.team-selector__filters,
.team-selector__summary,
.team-selector__actions,
.team-selector__footer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.team-selector__toolbar,
.team-selector__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.team-selector__table :deep(.el-table__cell) {
  vertical-align: middle;
}

.team-selector__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 280px;
  border: 1px dashed #cbd5e1;
  border-radius: 16px;
}

.team-selector__footer-hint {
  color: #64748b;
  font-size: 12px;
}

@media (max-width: 768px) {
  .team-selector__toolbar,
  .team-selector__footer {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
