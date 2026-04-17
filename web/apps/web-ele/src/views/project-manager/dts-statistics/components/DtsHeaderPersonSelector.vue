<script lang="ts" setup>
import type { PlGroup, PlGroupUser } from '#/api/core/pl';

import { computed, ref, watch } from 'vue';

import {
  ElButton,
  ElCheckbox,
  ElEmpty,
  ElInput,
  ElMessage,
  ElScrollbar,
  ElTag,
} from 'element-plus';

import { getAllPlApi, getPlUsersApi } from '#/api/core/pl';

interface Props {
  modelValue?: string[];
  valueMode?: 'name' | 'username';
  visible?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  valueMode: 'username',
  visible: false,
});

const emit = defineEmits<{
  (event: 'update:modelValue', value: string[]): void;
}>();

function normalizeStringArray(values?: Iterable<string> | null): string[] {
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
  return result.sort((left, right) => left.localeCompare(right, 'zh-CN'));
}

function cleanText(value: unknown): string {
  return String(value || '').trim();
}

function resolveSubmitValue(
  user: Partial<PlGroupUser>,
  mode: 'name' | 'username',
) {
  const username = cleanText(user.username);
  const name = cleanText(user.name);
  if (mode === 'name') {
    return name || username;
  }
  return username;
}

function resolveDisplayLabel(user: Partial<PlGroupUser>) {
  const username = cleanText(user.username);
  const name = cleanText(user.name);
  if (name && username && name !== username) {
    return `${name} (${username})`;
  }
  return name || username || '-';
}

let sharedGroupsPromise: null | Promise<PlGroup[]> = null;
const sharedMembersCache = new Map<string, PlGroupUser[]>();

async function loadSharedGroups() {
  if (!sharedGroupsPromise) {
    sharedGroupsPromise = getAllPlApi()
      .then((rows) =>
        (rows || [])
          .filter((item) => item?.status)
          .sort((left, right) =>
            String(left?.name || '').localeCompare(
              String(right?.name || ''),
              'zh-CN',
            ),
          ),
      )
      .catch((error) => {
        sharedGroupsPromise = null;
        throw error;
      });
  }
  return sharedGroupsPromise;
}

async function loadSharedMembers(groupId: string) {
  const key = cleanText(groupId);
  if (!key) {
    return [];
  }
  const cached = sharedMembersCache.get(key);
  if (cached) {
    return cached;
  }
  const response = await getPlUsersApi(key, { page: 1, pageSize: 9999 });
  const items = (response?.items || []).filter((item): item is PlGroupUser =>
    Boolean(cleanText(item?.username)),
  );
  sharedMembersCache.set(key, items);
  return items;
}

const groupsLoading = ref(false);
const membersLoading = ref(false);
const plGroups = ref<PlGroup[]>([]);
const memberCache = ref<Record<string, PlGroupUser[]>>({});

const activeGroupId = ref('');
const groupKeyword = ref('');
const memberKeyword = ref('');
const valueLabelMap = ref<Record<string, string>>({});

const selectedValues = computed(() => normalizeStringArray(props.modelValue));
const selectedSet = computed(() => new Set(selectedValues.value));

const filteredGroups = computed(() => {
  const keyword = cleanText(groupKeyword.value).toLowerCase();
  if (!keyword) {
    return plGroups.value;
  }
  return plGroups.value.filter((item) => {
    const name = cleanText(item.name).toLowerCase();
    const code = cleanText(item.code).toLowerCase();
    return name.includes(keyword) || code.includes(keyword);
  });
});

const currentGroupMembers = computed(() => {
  const groupId = cleanText(activeGroupId.value);
  if (!groupId) {
    return [];
  }
  return memberCache.value[groupId] || [];
});

const filteredMembers = computed(() => {
  const keyword = cleanText(memberKeyword.value).toLowerCase();
  if (!keyword) {
    return currentGroupMembers.value;
  }
  return currentGroupMembers.value.filter((user) => {
    const username = cleanText(user.username).toLowerCase();
    const name = cleanText(user.name).toLowerCase();
    const display = resolveDisplayLabel(user).toLowerCase();
    const submitValue = resolveSubmitValue(user, props.valueMode).toLowerCase();
    return (
      username.includes(keyword) ||
      name.includes(keyword) ||
      display.includes(keyword) ||
      submitValue.includes(keyword)
    );
  });
});

const selectedTags = computed(() =>
  selectedValues.value.map((value) => ({
    value,
    label: cleanText(valueLabelMap.value[value]) || value,
  })),
);

function updateLabelMapWithMembers(members: PlGroupUser[]) {
  if (!members || members.length === 0) {
    return;
  }
  const next = { ...valueLabelMap.value };
  members.forEach((user) => {
    const submitValue = resolveSubmitValue(user, props.valueMode);
    if (!submitValue) {
      return;
    }
    next[submitValue] = resolveDisplayLabel(user);
  });
  valueLabelMap.value = next;
}

async function ensureGroupsLoaded() {
  if (groupsLoading.value || plGroups.value.length > 0) {
    if (!activeGroupId.value && plGroups.value.length > 0) {
      activeGroupId.value = cleanText(plGroups.value[0]?.id);
      if (activeGroupId.value) {
        void ensureMembersLoaded(activeGroupId.value);
      }
    }
    return;
  }
  groupsLoading.value = true;
  try {
    plGroups.value = await loadSharedGroups();
    if (!activeGroupId.value && plGroups.value.length > 0) {
      activeGroupId.value = cleanText(plGroups.value[0]?.id);
    }
    if (activeGroupId.value) {
      await ensureMembersLoaded(activeGroupId.value);
    }
  } catch (error) {
    console.error(error);
    ElMessage.error('加载 PL 组失败');
  } finally {
    groupsLoading.value = false;
  }
}

async function ensureMembersLoaded(groupId: string) {
  const key = cleanText(groupId);
  if (!key) {
    return;
  }
  if (memberCache.value[key]) {
    updateLabelMapWithMembers(memberCache.value[key]);
    return;
  }
  membersLoading.value = true;
  try {
    const members = await loadSharedMembers(key);
    memberCache.value = {
      ...memberCache.value,
      [key]: members,
    };
    updateLabelMapWithMembers(members);
  } catch (error) {
    console.error(error);
    ElMessage.error('加载 PL 成员失败');
  } finally {
    membersLoading.value = false;
  }
}

function setSelected(nextValues: Iterable<string>) {
  emit('update:modelValue', normalizeStringArray(nextValues));
}

function toggleMember(user: PlGroupUser, checked: boolean) {
  const submitValue = resolveSubmitValue(user, props.valueMode);
  if (!submitValue) {
    return;
  }
  const next = new Set(selectedValues.value);
  if (checked) {
    next.add(submitValue);
  } else {
    next.delete(submitValue);
  }
  setSelected(next);
}

async function toggleGroup(groupId: string, checked: boolean) {
  await ensureMembersLoaded(groupId);
  const members = memberCache.value[groupId] || [];
  if (members.length === 0) {
    return;
  }
  const next = new Set(selectedValues.value);
  members.forEach((user) => {
    const submitValue = resolveSubmitValue(user, props.valueMode);
    if (!submitValue) {
      return;
    }
    if (checked) {
      next.add(submitValue);
    } else {
      next.delete(submitValue);
    }
  });
  setSelected(next);
}

function isGroupChecked(groupId: string) {
  const members = memberCache.value[groupId] || [];
  if (members.length === 0) {
    return false;
  }
  return members.every((user) =>
    selectedSet.value.has(resolveSubmitValue(user, props.valueMode)),
  );
}

function isGroupIndeterminate(groupId: string) {
  const members = memberCache.value[groupId] || [];
  if (members.length === 0) {
    return false;
  }
  let selectedCount = 0;
  members.forEach((user) => {
    if (selectedSet.value.has(resolveSubmitValue(user, props.valueMode))) {
      selectedCount += 1;
    }
  });
  return selectedCount > 0 && selectedCount < members.length;
}

function handleGroupClick(groupId: string) {
  activeGroupId.value = groupId;
  void ensureMembersLoaded(groupId);
}

function removeSelectedValue(value: string) {
  const next = new Set(selectedValues.value);
  next.delete(value);
  setSelected(next);
}

function clearAllSelected() {
  setSelected([]);
}

watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      return;
    }
    groupKeyword.value = '';
    memberKeyword.value = '';
    void ensureGroupsLoaded();
  },
);
</script>

<template>
  <div class="dts-header-person-selector">
    <div class="dts-header-person-selector__toolbar">
      <ElInput
        v-model="groupKeyword"
        size="small"
        clearable
        placeholder="搜索 PL 组"
      />
      <ElInput
        v-model="memberKeyword"
        size="small"
        clearable
        placeholder="搜索成员（姓名/工号）"
      />
    </div>

    <div class="dts-header-person-selector__selected">
      <div class="dts-header-person-selector__selected-head">
        <span>已选 {{ selectedValues.length }} 项</span>
        <ElButton
          link
          type="danger"
          size="small"
          :disabled="selectedValues.length === 0"
          @click="clearAllSelected"
        >
          清空
        </ElButton>
      </div>
      <ElScrollbar max-height="84px">
        <div
          v-if="selectedTags.length > 0"
          class="dts-header-person-selector__selected-tags"
        >
          <ElTag
            v-for="item in selectedTags"
            :key="item.value"
            closable
            size="small"
            effect="light"
            type="primary"
            @close="removeSelectedValue(item.value)"
          >
            {{ item.label }}
          </ElTag>
        </div>
        <div v-else class="dts-header-person-selector__selected-empty">
          暂未选择成员
        </div>
      </ElScrollbar>
    </div>

    <div class="dts-header-person-selector__content">
      <div class="dts-header-person-selector__groups">
        <ElEmpty
          v-if="!groupsLoading && filteredGroups.length === 0"
          description="暂无 PL 组"
          :image-size="52"
        />
        <ElScrollbar v-else max-height="240px">
          <div
            v-for="group in filteredGroups"
            :key="group.id"
            class="dts-header-person-selector__group-item"
            :class="{ 'is-active': activeGroupId === group.id }"
            @click="handleGroupClick(group.id)"
          >
            <ElCheckbox
              :model-value="isGroupChecked(group.id)"
              :indeterminate="isGroupIndeterminate(group.id)"
              @click.stop
              @change="(checked) => toggleGroup(group.id, !!checked)"
            />
            <div class="dts-header-person-selector__group-main">
              <div class="dts-header-person-selector__group-name">
                {{ group.name }}
              </div>
              <div class="dts-header-person-selector__group-meta">
                {{ group.member_count || 0 }} 人
              </div>
            </div>
          </div>
        </ElScrollbar>
      </div>

      <div class="dts-header-person-selector__members">
        <ElEmpty
          v-if="
            !membersLoading &&
            (activeGroupId ? filteredMembers.length === 0 : true)
          "
          :description="activeGroupId ? '当前组暂无匹配成员' : '请先选择 PL 组'"
          :image-size="52"
        />
        <ElScrollbar v-else max-height="240px">
          <div
            v-for="user in filteredMembers"
            :key="`${activeGroupId}-${user.id || user.username}`"
            class="dts-header-person-selector__member-item"
          >
            <ElCheckbox
              :model-value="
                selectedSet.has(resolveSubmitValue(user, props.valueMode))
              "
              @change="(checked) => toggleMember(user, !!checked)"
            />
            <div class="dts-header-person-selector__member-main">
              {{ resolveDisplayLabel(user) }}
            </div>
          </div>
        </ElScrollbar>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dts-header-person-selector {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dts-header-person-selector__toolbar {
  display: grid;
  gap: 8px;
  grid-template-columns: 1fr 1fr;
}

.dts-header-person-selector__selected {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px;
}

.dts-header-person-selector__selected-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #64748b;
  font-size: 12px;
  margin-bottom: 6px;
}

.dts-header-person-selector__selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.dts-header-person-selector__selected-empty {
  color: #94a3b8;
  font-size: 12px;
  padding: 2px 0;
}

.dts-header-person-selector__content {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  display: grid;
  grid-template-columns: 220px 1fr;
  min-height: 240px;
}

.dts-header-person-selector__groups {
  border-right: 1px solid #e2e8f0;
  background: #f8fafc;
}

.dts-header-person-selector__group-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  cursor: pointer;
  border-bottom: 1px solid #eef2f7;
}

.dts-header-person-selector__group-item:hover {
  background: #f1f5f9;
}

.dts-header-person-selector__group-item.is-active {
  background: #eff6ff;
}

.dts-header-person-selector__group-main {
  min-width: 0;
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.dts-header-person-selector__group-name {
  color: #0f172a;
  font-size: 12px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dts-header-person-selector__group-meta {
  color: #64748b;
  font-size: 12px;
  white-space: nowrap;
}

.dts-header-person-selector__members {
  background: #ffffff;
}

.dts-header-person-selector__member-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid #f1f5f9;
}

.dts-header-person-selector__member-main {
  color: #334155;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
