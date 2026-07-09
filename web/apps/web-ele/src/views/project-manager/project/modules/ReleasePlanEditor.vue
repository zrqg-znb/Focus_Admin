<script lang="ts" setup>
import type { PlatformConfig } from '#/api/project-manager/hardware';
import type { ProjectReleasePlan } from '#/api/project-manager/project';

import { computed, ref, watch } from 'vue';

import {
  ElButton,
  ElDatePicker,
  ElEmpty,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

const props = withDefaults(
  defineProps<{
    cdcPlatforms?: PlatformConfig[];
    idvpPlatforms?: PlatformConfig[];
    modelValue?: ProjectReleasePlan[];
    scenario?: '' | 'cockpit' | 'vehicle';
  }>(),
  {
    cdcPlatforms: () => [],
    idvpPlatforms: () => [],
    modelValue: () => [],
    scenario: '',
  },
);

const emit = defineEmits<{
  'update:modelValue': [value: ProjectReleasePlan[]];
}>();

type ReleasePlanRow = ProjectReleasePlan & { _key: string };
type ReleaseBranchGroup = {
  branch_name: string;
  rows: ReleasePlanRow[];
};

const VERSION_TYPE_OPTIONS = [
  { label: 'Alpha', value: 'Alpha' },
  { label: 'Beta', value: 'Beta' },
  { label: 'RC', value: 'RC' },
  { label: 'Release', value: 'Release' },
  { label: 'Hotfix', value: 'Hotfix' },
];

const groups = ref<ReleaseBranchGroup[]>([]);
let syncingFromProps = false;

const scenarioLabel = computed(() => {
  if (props.scenario === 'vehicle') return '车控发布：选择 IDVP 平台';
  if (props.scenario === 'cockpit') return '座舱发布：选择 CDC 平台';
  return '请先在基础信息中填写车控或座舱项目领域';
});

function createKey() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function normalizeRows(source: ProjectReleasePlan[]) {
  const nextGroups: ReleaseBranchGroup[] = [];
  const groupMap = new Map<string, ReleaseBranchGroup>();
  for (const item of source || []) {
    const branchName = String(item.branch_name || '').trim() || '未命名分支';
    if (!groupMap.has(branchName)) {
      const group = { branch_name: branchName, rows: [] };
      groupMap.set(branchName, group);
      nextGroups.push(group);
    }
    groupMap.get(branchName)!.rows.push({
      ...item,
      branch_name: branchName,
      release_vehicles: Array.isArray(item.release_vehicles)
        ? item.release_vehicles
        : [],
      _key: item.id || createKey(),
    });
  }
  groups.value = nextGroups;
}

function flattenGroups() {
  return groups.value.flatMap((group, groupIndex) =>
    group.rows.map((row, rowIndex) => ({
      branch_name: group.branch_name.trim(),
      release_date: row.release_date,
      version_type: row.version_type,
      idvp_platform_id:
        props.scenario === 'vehicle' ? row.idvp_platform_id || undefined : null,
      cdc_platform_id:
        props.scenario === 'cockpit' ? row.cdc_platform_id || undefined : null,
      release_vehicles: (row.release_vehicles || [])
        .map((item) => String(item || '').trim())
        .filter(Boolean),
      order: groupIndex * 100 + rowIndex,
    })),
  );
}

function emitChange() {
  if (syncingFromProps) return;
  emit('update:modelValue', flattenGroups());
}

function addBranch() {
  groups.value.push({
    branch_name: `release-${groups.value.length + 1}`,
    rows: [createEmptyRow()],
  });
  emitChange();
}

function removeBranch(index: number) {
  groups.value.splice(index, 1);
  emitChange();
}

function createEmptyRow(): ReleasePlanRow {
  return {
    _key: createKey(),
    branch_name: '',
    release_date: '',
    release_vehicles: [],
    version_type: 'Release',
    idvp_platform_id: '',
    cdc_platform_id: '',
  };
}

function addPlan(group: ReleaseBranchGroup) {
  group.rows.push(createEmptyRow());
  emitChange();
}

function removePlan(group: ReleaseBranchGroup, index: number) {
  group.rows.splice(index, 1);
  emitChange();
}

function validate(showMessage = true) {
  if (groups.value.length === 0) return true;
  if (!props.scenario) {
    if (showMessage) ElMessage.warning('请先填写车控或座舱项目领域');
    return false;
  }
  for (const group of groups.value) {
    const branchName = group.branch_name.trim();
    if (!branchName) {
      if (showMessage) ElMessage.warning('发布计划分支名不能为空');
      return false;
    }
    if (group.rows.length === 0) {
      if (showMessage) ElMessage.warning(`分支 ${branchName} 至少需要一条计划`);
      return false;
    }
    for (const row of group.rows) {
      if (!row.release_date || !row.version_type) {
        if (showMessage)
          ElMessage.warning(`请完善分支 ${branchName} 的发布日期和版本类型`);
        return false;
      }
      if (props.scenario === 'vehicle' && !row.idvp_platform_id) {
        if (showMessage)
          ElMessage.warning(`请为分支 ${branchName} 选择 IDVP 平台`);
        return false;
      }
      if (props.scenario === 'cockpit' && !row.cdc_platform_id) {
        if (showMessage)
          ElMessage.warning(`请为分支 ${branchName} 选择 CDC 平台`);
        return false;
      }
      if (!row.release_vehicles || row.release_vehicles.length === 0) {
        if (showMessage)
          ElMessage.warning(`请为分支 ${branchName} 配置发布车型`);
        return false;
      }
    }
  }
  return true;
}

watch(
  () => props.modelValue,
  (value) => {
    syncingFromProps = true;
    normalizeRows(value || []);
    syncingFromProps = false;
  },
  { immediate: true },
);

watch(
  () => props.scenario,
  () => {
    for (const group of groups.value) {
      for (const row of group.rows) {
        if (props.scenario === 'vehicle') {
          row.cdc_platform_id = '';
        } else if (props.scenario === 'cockpit') {
          row.idvp_platform_id = '';
        }
      }
    }
    emitChange();
  },
);

defineExpose({ validate });
</script>

<template>
  <div class="release-plan-editor">
    <div class="release-plan-editor__toolbar">
      <div>
        <div class="text-sm font-medium">发布计划</div>
        <div class="text-muted-foreground mt-1 text-xs">
          {{ scenarioLabel }}
        </div>
      </div>
      <ElButton type="primary" @click="addBranch">新增分支</ElButton>
    </div>

    <ElEmpty v-if="groups.length === 0" description="暂无发布计划" />

    <div
      v-for="(group, groupIndex) in groups"
      :key="groupIndex"
      class="release-branch"
    >
      <div class="release-branch__header">
        <div class="flex min-w-0 items-center gap-2">
          <ElTag type="primary">分支 {{ groupIndex + 1 }}</ElTag>
          <ElInput
            v-model="group.branch_name"
            class="max-w-[360px]"
            placeholder="输入分支名，如 release/1.0"
            @change="emitChange"
          />
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <ElButton link type="primary" @click="addPlan(group)">
            新增计划
          </ElButton>
          <ElButton link type="danger" @click="removeBranch(groupIndex)">
            删除分支
          </ElButton>
        </div>
      </div>

      <ElTable :data="group.rows" size="small" class="release-branch__table">
        <ElTableColumn label="发布日期" min-width="160">
          <template #default="{ row }">
            <ElDatePicker
              v-model="row.release_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择日期"
              class="w-full"
              @change="emitChange"
            />
          </template>
        </ElTableColumn>
        <ElTableColumn label="版本类型" min-width="170">
          <template #default="{ row }">
            <ElSelect
              v-model="row.version_type"
              allow-create
              class="w-full"
              default-first-option
              filterable
              placeholder="选择或输入版本类型"
              @change="emitChange"
            >
              <ElOption
                v-for="item in VERSION_TYPE_OPTIONS"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </ElSelect>
          </template>
        </ElTableColumn>
        <ElTableColumn label="发布平台" min-width="220">
          <template #default="{ row }">
            <ElSelect
              v-if="scenario === 'vehicle'"
              v-model="row.idvp_platform_id"
              class="w-full"
              clearable
              placeholder="选择 IDVP 平台"
              @change="emitChange"
            >
              <ElOption
                v-for="platform in idvpPlatforms"
                :key="platform.id"
                :label="platform.name"
                :value="platform.id"
              />
            </ElSelect>
            <ElSelect
              v-else-if="scenario === 'cockpit'"
              v-model="row.cdc_platform_id"
              class="w-full"
              clearable
              placeholder="选择 CDC 平台"
              @change="emitChange"
            >
              <ElOption
                v-for="platform in cdcPlatforms"
                :key="platform.id"
                :label="platform.name"
                :value="platform.id"
              />
            </ElSelect>
            <ElTag v-else type="info">待选择项目领域</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="发布车型" min-width="260">
          <template #default="{ row }">
            <ElSelect
              v-model="row.release_vehicles"
              allow-create
              class="w-full"
              collapse-tags
              collapse-tags-tooltip
              default-first-option
              filterable
              multiple
              placeholder="输入车型后回车"
              @change="emitChange"
            />
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="100" align="center">
          <template #default="{ $index }">
            <ElButton link type="danger" @click="removePlan(group, $index)">
              删除
            </ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </div>
  </div>
</template>

<style scoped>
.release-plan-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.release-plan-editor__toolbar,
.release-branch__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.release-branch {
  border: 1px solid hsl(var(--border));
  border-radius: 8px;
  background: hsl(var(--card));
  padding: 12px;
}

.release-branch__table {
  margin-top: 12px;
}
</style>
