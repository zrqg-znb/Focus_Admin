<script lang="ts" setup>
import type { PlGroup } from '#/api/core/pl';

import { computed, ref, watch } from 'vue';

import { CaretRight, Search } from '@element-plus/icons-vue';
import {
  ElButton,
  ElDialog,
  ElEmpty,
  ElIcon,
  ElInput,
  ElMessage,
  ElScrollbar,
  ElTag,
} from 'element-plus';

import { getAllPlApi } from '#/api/core/pl';
import UserListPanel from '#/components/user-list-panel/index.vue';

interface Props {
  modelValue?: string[];
  title?: string;
  placeholder?: string;
  disabled?: boolean;
  buttonSize?: 'default' | 'large' | 'small';
}

defineOptions({ name: 'PlUserSelector' });

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  title: '选择用户',
  placeholder: '选择用户',
  disabled: false,
  buttonSize: 'small',
});

const emit = defineEmits<{
  (event: 'update:modelValue', value: string[]): void;
  (event: 'change', value: string[]): void;
}>();

function normalizeUsernames(values?: Iterable<string> | null): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const item of values || []) {
    const text = String(item || '').trim();
    if (!text || seen.has(text)) continue;
    seen.add(text);
    result.push(text);
  }
  return result.sort((a, b) => a.localeCompare(b, 'zh-CN'));
}

const confirmedUsernames = computed(() => normalizeUsernames(props.modelValue));
const confirmedCount = computed(() => confirmedUsernames.value.length);

const dialogVisible = ref(false);

const plKeyword = ref('');

const activePlId = ref<string | null>(null);

const plGroupsLoading = ref(false);
const plGroups = ref<PlGroup[]>([]);

// Dialog-local selection (only committed on confirm).
const tempSelected = ref<Set<string>>(new Set());
const tempSelectedCount = computed(() => tempSelected.value.size);

const buttonLabel = computed(() =>
  confirmedCount.value > 0
    ? `已选（${confirmedCount.value}）`
    : props.placeholder,
);
const buttonType = computed(() =>
  confirmedCount.value > 0 ? 'success' : 'primary',
);

const isDialogOpen = computed(() => dialogVisible.value);

const filteredGroups = computed(() => {
  const kw = plKeyword.value.trim().toLowerCase();
  if (!kw) return plGroups.value;
  return plGroups.value.filter((item) => {
    const name = String(item.name || '').toLowerCase();
    const code = String(item.code || '').toLowerCase();
    return name.includes(kw) || code.includes(kw);
  });
});

async function loadPlGroupsIfNeeded() {
  if (plGroupsLoading.value || plGroups.value.length > 0) {
    if (plGroups.value.length > 0 && !activePlId.value) {
      activePlId.value = plGroups.value[0]?.id || null;
    }
    return;
  }
  plGroupsLoading.value = true;
  try {
    const items = await getAllPlApi();
    plGroups.value = (items || [])
      .filter((item: PlGroup) => item.status)
      .sort((a: PlGroup, b: PlGroup) =>
        String(a.name || '').localeCompare(String(b.name || ''), 'zh-CN'),
      );
    if (plGroups.value.length > 0 && !activePlId.value) {
      activePlId.value = plGroups.value[0]?.id || null;
    }
  } catch (error) {
    console.error('[PlUserSelector] load PL groups failed', error);
    ElMessage.error('加载 PL 组失败');
  } finally {
    plGroupsLoading.value = false;
  }
}

function setTempSelected(next: Set<string>) {
  tempSelected.value = new Set(next);
}

// 存储选中用户的 username，用于展示
const selectedUsernames = ref<Map<string, string>>(new Map());

function openDialog() {
  if (props.disabled) return;
  
  // 初始化时，假设外部传入的 modelValue 就是 username
  // 此时我们没有对应的 userId，所以暂时将 userId 和 username 都设为一样
  // 等后续加载用户列表时再进行匹配更新
  const initialSet = new Set<string>();
  confirmedUsernames.value.forEach(username => {
    initialSet.add(username); // 先用 username 作为 ID 占位
    selectedUsernames.value.set(username, username);
  });
  
  setTempSelected(initialSet);
  plKeyword.value = '';
  dialogVisible.value = true;
  loadPlGroupsIfNeeded();
}

function closeDialog() {
  dialogVisible.value = false;
}

function emitValue(value: string[]) {
  emit('update:modelValue', value);
  emit('change', value);
}

function clearConfirmedSelection() {
  emitValue([]);
}

function clearAllTemp() {
  setTempSelected(new Set());
}

function selectPlGroup(plId: string) {
  activePlId.value = plId;
}

function handleConfirm() {
  // 提交时，我们需要返回的是 username 数组，而不是内部用于维护状态的 userId
  const usernamesToSubmit = Array.from(tempSelected.value)
    .map(id => selectedUsernames.value.get(id) || id);
    
  const value = normalizeUsernames(usernamesToSubmit);
  emitValue(value);
  closeDialog();
}

function removeSelectedUser(id: string) {
  const next = new Set(tempSelected.value);
  next.delete(id);
  selectedUsernames.value.delete(id);
  setTempSelected(next);
}

function handleUserSelect(userId: string, user: any) {
  // Use user.id instead of user.username to match UserListPanel's expected format
  // UserListPanel internally uses user.id for selection state checking:
  // :selected="selectable && tempSelectedUsers.has(user.id)"
  const next = new Set(tempSelected.value);
  const identifier = user.id || userId;
  
  if (next.has(identifier)) {
    next.delete(identifier);
    selectedUsernames.value.delete(identifier);
  } else {
    next.add(identifier);
    // 保存 userId 到 username 的映射
    if (user.username) {
      selectedUsernames.value.set(identifier, user.username);
    }
    
    // 清理可能存在的以 username 为 key 的旧记录（当外部传入的初始化数据被匹配上时）
    if (user.username && next.has(user.username)) {
      next.delete(user.username);
      selectedUsernames.value.delete(user.username);
    }
  }
  
  setTempSelected(next);
}
</script>

<template>
  <div class="pl-user-selector">
    <ElButton
      :type="buttonType"
      plain
      :size="buttonSize"
      :disabled="disabled"
      class="pl-user-selector__trigger"
      :class="{ 'is-open': isDialogOpen }"
      @click.stop="openDialog"
    >
      <span class="pl-user-selector__trigger-text">{{ buttonLabel }}</span>
      <ElIcon class="pl-user-selector__trigger-icon">
        <CaretRight />
      </ElIcon>
    </ElButton>
    <ElButton
      v-if="confirmedCount > 0"
      link
      type="danger"
      :size="buttonSize"
      :disabled="disabled"
      class="pl-user-selector__clear"
      @click.stop="clearConfirmedSelection"
    >
      清空
    </ElButton>

    <ElDialog
      v-model="dialogVisible"
      :title="title"
      width="min(1080px, 96vw)"
      append-to-body
      destroy-on-close
      class="pl-user-selector-dialog"
      top="8vh"
    >
      <div class="selector-container">
        <!-- Selected Users Area -->
        <div class="selector-header">
          <div class="selector-header__left">
            <span class="selector-header__title">已选成员 ({{ tempSelectedCount }})</span>
            <div class="selector-header__tags" v-if="tempSelectedCount > 0">
              <ElScrollbar>
                <div class="selector-header__tags-inner">
                  <ElTag
                    v-for="id in tempSelected"
                    :key="id"
                    closable
                    effect="light"
                    type="primary"
                    @close="removeSelectedUser(id)"
                    class="user-tag"
                  >
                    {{ selectedUsernames.get(id) || id }}
                  </ElTag>
                </div>
              </ElScrollbar>
            </div>
            <div v-else class="selector-header__empty">
              暂未选择任何成员
            </div>
          </div>
          <div class="selector-header__right">
            <ElButton
              type="danger"
              plain
              size="small"
              :disabled="tempSelectedCount === 0"
              @click="clearAllTemp"
            >
              清空全部
            </ElButton>
          </div>
        </div>

        <!-- Main Layout -->
        <div class="selector-body">
          <!-- Left: PL Groups -->
          <div class="selector-sidebar" v-loading="plGroupsLoading">
            <div class="selector-sidebar__search">
              <ElInput
                v-model="plKeyword"
                clearable
                placeholder="搜索 PL 组"
                :prefix-icon="Search"
              />
            </div>
            <div class="selector-sidebar__list">
              <ElEmpty v-if="!plGroupsLoading && filteredGroups.length === 0" description="无匹配组" :image-size="60" />
              <ElScrollbar v-else>
                <div
                  v-for="pl in filteredGroups"
                  :key="pl.id"
                  class="pl-list-item"
                  :class="{ 'is-active': activePlId === pl.id }"
                  @click="selectPlGroup(pl.id)"
                >
                  <div class="pl-list-item__main">
                    <div class="pl-list-item__name">{{ pl.name }}</div>
                    <div class="pl-list-item__code" v-if="pl.code">{{ pl.code }}</div>
                  </div>
                  <div class="pl-list-item__meta">
                    <span class="pl-list-item__count">{{ pl.member_count || 0 }} 人</span>
                  </div>
                </div>
              </ElScrollbar>
            </div>
          </div>

          <!-- Right: Users -->
          <div class="selector-content">
            <template v-if="activePlId">
              <UserListPanel
                :data-source="'pl'"
                :source-id="activePlId"
                :temp-selected-users="tempSelected"
                :filterable="true"
                :multiple="true"
                :selectable="true"
                :show-border="false"
                :auto-load="true"
                :show-selected-tags="false"
                @user-select="handleUserSelect"
                @remove-user="removeSelectedUser"
              />
            </template>
            <div v-else class="selector-content__empty">
              <ElEmpty description="请在左侧选择一个 PL 组" />
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="pl-user-selector__footer">
          <ElButton @click="closeDialog">取消</ElButton>
          <ElButton type="primary" @click="handleConfirm">确认选择</ElButton>
        </div>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.pl-user-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-width: 0;
}

.pl-user-selector__trigger {
  display: flex;
  flex: 1;
  min-width: 0;
  justify-content: space-between;
  border-radius: 12px;
  transition:
    transform 0.12s ease,
    box-shadow 0.18s ease;
}

.pl-user-selector__trigger:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgb(15 23 42 / 0.08);
}

.pl-user-selector__trigger.is-open {
  box-shadow: 0 14px 30px rgb(15 23 42 / 0.12);
}

.pl-user-selector__trigger-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pl-user-selector__trigger-icon {
  transition: transform 0.18s ease;
  transform: rotate(90deg);
  opacity: 0.65;
}

.pl-user-selector__trigger.is-open .pl-user-selector__trigger-icon {
  transform: rotate(180deg);
  opacity: 0.9;
}

.pl-user-selector__clear {
  flex-shrink: 0;
}

.pl-user-selector__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

:deep(.pl-user-selector-dialog .el-dialog__header) {
  border-bottom: 1px solid rgb(226 232 240 / 0.9);
  margin-right: 0;
  padding-bottom: 16px;
}

:deep(.pl-user-selector-dialog .el-dialog__body) {
  padding: 16px 20px 20px;
  background: #fcfcfd;
}

:deep(.pl-user-selector-dialog .el-dialog__footer) {
  border-top: 1px solid rgb(226 232 240 / 0.9);
  padding: 12px 20px 14px;
}

.selector-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: clamp(500px, 65vh, 800px);
}

.selector-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgb(15 23 42 / 0.02);
}

.selector-header__left {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.selector-header__title {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}

.selector-header__tags {
  width: 100%;
}

.selector-header__tags-inner {
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  padding-bottom: 4px;
}

.user-tag {
  flex-shrink: 0;
}

.selector-header__empty {
  font-size: 13px;
  color: #94a3b8;
  padding: 4px 0;
}

.selector-header__right {
  flex-shrink: 0;
}

.selector-body {
  display: flex;
  flex: 1;
  min-height: 0;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  background: #ffffff;
  box-shadow: 0 8px 24px rgb(15 23 42 / 0.03);
}

.selector-sidebar {
  width: 280px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e2e8f0;
  background: #f8fafc;
}

.selector-sidebar__search {
  padding: 12px;
  border-bottom: 1px solid #e2e8f0;
  background: #ffffff;
}

.selector-sidebar__list {
  flex: 1;
  min-height: 0;
}

.pl-list-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f1f5f9;
  transition: all 0.2s ease;
}

.pl-list-item:hover {
  background: #f1f5f9;
}

.pl-list-item.is-active {
  background: #eff6ff;
  border-left: 3px solid #3b82f6;
  padding-left: 13px;
}

.pl-list-item__main {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pl-list-item__name {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.pl-list-item__code {
  font-size: 12px;
  color: #64748b;
  background: #e2e8f0;
  padding: 2px 6px;
  border-radius: 4px;
}

.pl-list-item__meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.pl-list-item__count {
  color: #64748b;
}

.selector-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #ffffff;
  overflow: hidden;
}

.selector-content__empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 768px) {
  .selector-body {
    flex-direction: column;
  }
  .selector-sidebar {
    width: 100%;
    height: 40%;
    border-right: none;
    border-bottom: 1px solid #e2e8f0;
  }
  .selector-content {
    height: 60%;
  }
}
</style>
