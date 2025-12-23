
<script lang="ts" setup>
import type { RoleSelectorProps, RoleSelectorEmits } from './types';
import { computed, ref, watch, useAttrs, onMounted } from 'vue';
import { ElInput, ElButton, ElDialog, ElEmpty, ElTag, ElSelect, ElOption, ElScrollbar, ElSkeleton, ElSkeletonItem } from 'element-plus';
import { $t } from '@vben/locales';
import { Search } from '@vben/icons';
import { getRoleListApi, getRolesByIds } from '#/api/core/role';

defineOptions({
  name: 'RoleSelector',
  inheritAttrs: false,
});

interface Props extends RoleSelectorProps {}

const props = withDefaults(defineProps<Props>(), {
  multiple: false,
  placeholder: () => $t('ui.placeholder.select') || 'Please select',
  disabled: false,
  clearable: true,
  filterable: true,
});

const emit = defineEmits<RoleSelectorEmits>();
const attrs = useAttrs();

const modalVisible = ref(false);
const roles = ref<any[]>([]);
const selectedRoles = ref<Set<string>>(new Set(
  Array.isArray(props.modelValue) ? props.modelValue : (props.modelValue ? [props.modelValue] : [])
));
// 临时选择（用于 modal 中的选择，未确认前）
const tempSelectedRoles = ref<Set<string>>(new Set());
const roleLoading = ref(false);
const searchText = ref('');
// 分页相关
const currentPage = ref(1);
const pageSize = ref(20);
const totalRoles = ref(0);
const isLoadingMore = ref(false);
// 搜索相关
const searchResults = ref<any[]>([]);
const isSearching = ref(false);
// 标记是否已加载过角色数据
const hasLoadedRoles = ref(false);
// 标记是否已加载过完整列表（用于弹窗）
const hasLoadedFullList = ref(false);

// 计算显示值（只显示已确认的值）
const displayValue = computed({
  get() {
    if (!selectedRoles.value.size) return undefined;
    if (props.multiple) {
      return Array.from(selectedRoles.value);
    }
    return Array.from(selectedRoles.value)[0];
  },
  set(_value) {
    // ElSelect 会改变这个值，但我们不需要处理
  },
});

// 获取已选角色的信息
const selectedRolesWithInfo = computed(() => {
  const result = [];
  const seenIds = new Set<string>(); // 用于去重

  for (const roleId of selectedRoles.value) {
    // 避免重复添加
    if (seenIds.has(roleId)) continue;

    const role = roles.value.find(r => r.id === roleId) ||
                 searchResults.value.find(r => r.id === roleId);
    if (role) {
      seenIds.add(roleId);
      result.push({
        id: role.id,
        name: role.name,
        code: role.code,
      });
    }
  }
  return result;
});

// 获取临时选择角色的信息
const tempSelectedRolesWithInfo = computed(() => {
  const result = [];
  const seenIds = new Set<string>(); // 用于去重

  for (const roleId of tempSelectedRoles.value) {
    // 避免重复添加
    if (seenIds.has(roleId)) continue;

    const role = roles.value.find(r => r.id === roleId) ||
                 searchResults.value.find(r => r.id === roleId);
    if (role) {
      seenIds.add(roleId);
      result.push({
        id: role.id,
        name: role.name,
        code: role.code,
      });
    }
  }
  return result;
});

// 加载角色数据（分页）
const loadRoles = async (page: number = 1, append: boolean = false) => {
  try {
    if (page === 1) {
      roleLoading.value = true;
    } else {
      isLoadingMore.value = true;
    }

    const result = await getRoleListApi({
      page,
      pageSize: pageSize.value,
      name: searchText.value || undefined,
    });

    if (result) {
      // 无论是追加还是重新加载，都需要去重
      const existingIds = new Set(roles.value.map(r => r.id));
      const newItems = (result.items || []).filter((item: any) => !existingIds.has(item.id));

      if (append) {
        // 追加数据（触底加载）
        roles.value = [...roles.value, ...newItems];
      } else {
        // 重新加载（首次加载或搜索）
        // 合并已有数据（已选项）和新加载的数据
        roles.value = [...roles.value, ...newItems];
      }

      totalRoles.value = result.total || 0;
      currentPage.value = page;
      hasLoadedRoles.value = true;
      // 标记已加载完整列表
      hasLoadedFullList.value = true;
    }

    roleLoading.value = false;
    isLoadingMore.value = false;
  } catch (error) {
    console.error('Failed to load roles:', error);
    roleLoading.value = false;
    isLoadingMore.value = false;
  }
};

// 根据ID加载特定角色信息（用于编辑时显示已选角色的名称）
const loadRolesByIds = async (ids: string[]) => {
  if (!ids || ids.length === 0) return;

  try {
    roleLoading.value = true;

    // 调用后端API按ID查询角色信息
    const result = await getRolesByIds(ids);

    if (result && result.length > 0) {
      // 合并数据，去重
      const existingIds = new Set(roles.value.map(r => r.id));
      const newRoles = result.filter((r: any) => !existingIds.has(r.id));
      roles.value = [...roles.value, ...newRoles];
      hasLoadedRoles.value = true;
    }

    roleLoading.value = false;
  } catch (error) {
    console.error('Failed to load roles by ids:', error);
    roleLoading.value = false;
  }
};

// 角色列表直接使用 roles
const filteredRoles = computed(() => {
  return roles.value;
});

// 判断是否还有更多数据
const hasMoreData = computed(() => {
  return roles.value.length < totalRoles.value;
});

// 防抖搜索定时器
let searchTimer: ReturnType<typeof setTimeout> | null = null;

// 监听搜索文本变化，执行服务端搜索
watch(searchText, (newVal) => {
  // 清除之前的定时器
  if (searchTimer) {
    clearTimeout(searchTimer);
  }

  // 设置新的防抖定时器
  searchTimer = setTimeout(() => {
    // 重置分页并重新加载
    currentPage.value = 1;
    loadRoles(1, false);
  }, 300);
});

// 处理角色选择
const handleRoleSelect = (roleId: string) => {
  if (props.multiple) {
    if (tempSelectedRoles.value.has(roleId)) {
      tempSelectedRoles.value.delete(roleId);
    } else {
      tempSelectedRoles.value.add(roleId);
    }
  } else {
    // 单选模式
    tempSelectedRoles.value.clear();
    tempSelectedRoles.value.add(roleId);
    // 单选时直接确认并关闭
    handleConfirm();
  }
};

// 打开modal
const openModal = async () => {
  if (props.disabled) return;
  modalVisible.value = true;
};

// 打开modal后加载数据
const handleModalOpened = async () => {
  // 初始化临时选择为已选择的值
  tempSelectedRoles.value = new Set(selectedRoles.value);

  // 只有在未加载过完整列表时才加载第一页数据
  if (!hasLoadedFullList.value) {
    await loadRoles(1, false);
  }
};

// 触底加载更多
const handleScroll = ({ scrollTop, scrollLeft }: { scrollTop: number; scrollLeft: number }) => {
  const scrollbarRef = document.querySelector('.role-selector-list .el-scrollbar__wrap');
  if (!scrollbarRef) return;

  const scrollHeight = scrollbarRef.scrollHeight;
  const clientHeight = scrollbarRef.clientHeight;

  // 当滚动到底部附近 50px 时触发加载
  if (scrollTop + clientHeight >= scrollHeight - 50 && hasMoreData.value && !isLoadingMore.value && !roleLoading.value) {
    loadRoles(currentPage.value + 1, true);
  }
};

// 确认选择
const handleConfirm = () => {
  // 将临时选择的值保存到 selectedRoles（已确认）
  selectedRoles.value = new Set(tempSelectedRoles.value);

  const value = props.multiple
    ? Array.from(selectedRoles.value)
    : (selectedRoles.value.size > 0 ? Array.from(selectedRoles.value)[0] : '');

  emit('update:modelValue', value);
  emit('change', value);
  modalVisible.value = false;
};

// 清除选择
const handleClear = (e?: MouseEvent) => {
  if (e) {
    e.stopPropagation();
  }
  tempSelectedRoles.value.clear();
  selectedRoles.value.clear();
  const emptyValue = props.multiple ? [] : '';
  emit('update:modelValue', emptyValue);
  emit('change', emptyValue);
};

// 删除单个选中项（多选模式下点击标签删除按钮）
const handleRemoveTag = (roleId: string) => {
  selectedRoles.value.delete(roleId);
  const value = props.multiple
    ? Array.from(selectedRoles.value)
    : '';
  emit('update:modelValue', value);
  emit('change', value);
};

// 监听外部 modelValue 变化
const updateInternalValue = () => {
  selectedRoles.value.clear();
  tempSelectedRoles.value.clear();
  if (Array.isArray(props.modelValue)) {
    props.modelValue.forEach(v => selectedRoles.value.add(v));
  } else if (props.modelValue) {
    selectedRoles.value.add(props.modelValue);
  }
  // 打开 modal 时初始化临时选择
  if (modalVisible.value) {
    tempSelectedRoles.value = new Set(selectedRoles.value);
  }
};

// 监听 modelValue 变化，如果有值且角色数据未加载，则加载
watch(() => props.modelValue, async (newValue) => {
  updateInternalValue();

  // 如果有选中值且角色数据未加载，则加载角色数据
  if ((Array.isArray(newValue) && newValue.length > 0) ||
      (typeof newValue === 'string' && newValue)) {
    if (!hasLoadedRoles.value) {
      const ids = Array.isArray(newValue) ? newValue : [newValue];
      await loadRolesByIds(ids);
    }
  }
}, { immediate: true });

// 组件挂载时，如果有初始值，则加载角色数据
onMounted(async () => {
  if ((Array.isArray(props.modelValue) && props.modelValue.length > 0) ||
      (typeof props.modelValue === 'string' && props.modelValue)) {
    const ids = Array.isArray(props.modelValue) ? props.modelValue : [props.modelValue];
    await loadRolesByIds(ids);
  }
});

defineExpose({
  openModal,
});
</script>

<template>
  <div class="role-selector">
    <!-- 选择框 -->
    <div class="role-selector-input" :class="{ disabled }">
      <ElSelect
        v-bind="attrs"
        v-model="displayValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :clearable="clearable && selectedRoles.size > 0"
        :multiple="multiple"
        readonly
        @click="openModal"
        @clear="() => handleClear()"
        @remove-tag="handleRemoveTag"
      >
        <ElOption
          v-for="item in selectedRolesWithInfo"
          :key="item.id"
          :label="item.name"
          :value="item.id"
        />
      </ElSelect>
    </div>

    <!-- Modal -->
    <ElDialog
      v-model="modalVisible"
      :title="$t('system.user.selectRole') || 'Select Roles'"
      width="45%"
      class="role-selector-modal"
      @opened="handleModalOpened"
    >
      <div class="role-selector-content">
        <!-- 顶部：已选项（左侧）+ 搜索框（右侧） -->
        <div class="role-selector-header-row">
          <div class="header-middle">
            <div v-if="tempSelectedRolesWithInfo.length > 0" class="selected-tags">
              <el-tag
                v-for="item of tempSelectedRolesWithInfo"
                :key="item.id"
                closable
                type="info"
                size="small"
                @close="() => {
                  tempSelectedRoles.delete(item.id);
                }"
              >
                {{ item.name }}
              </el-tag>
            </div>
            <span v-else class="empty-text">-</span>
          </div>

          <!-- 搜索框（右侧） -->
          <div v-if="filterable" class="header-search">
            <ElInput
              v-model="searchText"
              :placeholder="$t('common.search') || 'Search'"
              clearable
              :prefix-icon="Search"
            />
          </div>
        </div>

        <!-- 角色列表 -->
        <el-scrollbar
          class="role-selector-list"
          @scroll="handleScroll"
        >
          <el-skeleton :loading="roleLoading" animated :count="8">
            <template #template>
              <div class="role-selector-list-content">
                <div v-for="i in 8" :key="i" class="role-skeleton-item">
                  <el-skeleton-item variant="text" style="width: 100%; height: 40px; margin: 8px 0" />
                </div>
              </div>
            </template>
            <template #default>
              <div class="role-selector-list-content">
                <ElEmpty
                  v-if="filteredRoles.length === 0 && !roleLoading"
                  :description="$t('common.noData') || 'No Data'"
                />
                <div v-else class="role-list">
                  <div
                    v-for="role in filteredRoles"
                    :key="role.id"
                    class="role-item"
                    :class="[
                      tempSelectedRoles.has(role.id)
                        ? 'bg-primary/15 dark:bg-accent text-primary'
                        : 'hover:bg-[var(--el-fill-color-light)]',
                    ]"
                    @click="handleRoleSelect(role.id)"
                  >
                    <!-- 角色名称 -->
                    <div class="role-name">{{ role.name }}</div>

                    <!-- 角色代码 -->
                    <div v-if="role.code" class="role-code">{{ role.code }}</div>
                  </div>

                  <!-- 加载更多提示 -->
                  <div v-if="isLoadingMore" class="loading-more">
                    <el-skeleton-item variant="text" style="width: 100%; height: 40px;" />
                  </div>

                  <!-- 没有更多数据提示 -->
                  <div v-if="!hasMoreData && filteredRoles.length > 0" class="no-more-data">
                    {{ $t('common.noMoreData') || 'No more data' }}
                  </div>
                </div>
              </div>
            </template>
          </el-skeleton>
        </el-scrollbar>
      </div>

      <template #footer>
        <div class="modal-footer">
          <div class="footer-left">
            <span class="selected-count">
              {{ tempSelectedRoles.size }} {{ $t('common.selected') || 'selected' }}
            </span>
            <ElButton
              v-if="tempSelectedRoles.size > 0"
              link
              type="danger"
              size="small"
              @click="() => tempSelectedRoles.clear()"
            >
              {{ $t('common.clear') || 'Clear' }}
            </ElButton>
          </div>
          <div class="footer-right">
            <ElButton @click="modalVisible = false">
              {{ $t('common.cancel') || 'Cancel' }}
            </ElButton>
            <ElButton type="primary" @click="handleConfirm">
              {{ $t('common.confirm') || 'Confirm' }}
            </ElButton>
          </div>
        </div>
      </template>
    </ElDialog>
  </div>
</template>

<style lang="scss" scoped>
.role-selector {
  width: 100%;

  &-input {
    cursor: pointer;

    &.disabled {
      cursor: not-allowed;
      opacity: 0.6;
    }

    :deep(.el-input) {
      &.is-disabled {
        background-color: var(--background-deep, #f5f7fa);
      }
    }
  }

  &-modal {
    :deep(.el-dialog__header) {
      border-bottom: 1px solid var(--border, #ebeef5);
    }

    :deep(.el-dialog__body) {
      padding: 20px;
    }
  }

  &-content {
    display: flex;
    flex-direction: column;
    height: 500px;
    padding: 0;
    gap: 0;
    border: 1px solid hsl(var(--border));
    border-radius: var(--radius);
    overflow: hidden;
    background-color: hsl(var(--background));
    box-shadow: 0 1px 3px hsl(var(--border) / 0.12);
  }

  &-header-row {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid hsl(var(--border));
    gap: 12px;
    background: linear-gradient(90deg, hsl(var(--background)) 0%, hsl(var(--background-deep) / 0.3) 100%);
    flex-shrink: 0;

    .header-middle {
      flex: 1;
      display: flex;
      align-items: center;
      gap: 8px;
      overflow-y: auto;
      min-width: 80px;
      max-height: 40px;

      .selected-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        align-items: center;

        :deep(.el-tag) {
          height: 24px;
          line-height: 22px;
          font-size: 12px;
        }
      }

      .empty-text {
        font-size: 12px;
        color: hsl(var(--muted-foreground));
        white-space: nowrap;
      }
    }

    .header-search {
      flex-shrink: 0;
      width: 160px;

      :deep(.el-input) {
        font-size: 14px;
      }
    }
  }

  &-list {
    flex: 1;
    overflow-y: auto;
    border-top: none;
  }

  &-list-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 8px 10px;
    width: 100%;

    .role-list {
      display: flex;
      flex-direction: column;
    }

    .role-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 42px;
      padding: 0 12px;
      cursor: pointer;
      transition: all 0.2s ease;
      border-radius: 8px;
      margin: 1px 0;

      .role-name {
        flex: 1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        font-size: 14px;
        transition: color 0.2s ease;
      }

      .role-code {
        flex-shrink: 0;
        margin-left: 8px;
        font-size: 12px;
        color: hsl(var(--muted-foreground));
        white-space: nowrap;
        padding: 2px 8px;
        background: hsl(var(--background-deep) / 0.5);
        border-radius: 4px;
      }
    }
  }
}

.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;

  .footer-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .footer-right {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-left: auto;
  }
}

.role-skeleton-item {
  padding: 8px 12px;
  width: 100%;
  display: flex;
  align-items: center;
  box-sizing: border-box;
}

.loading-more {
  padding: 8px 12px;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.no-more-data {
  padding: 12px;
  text-align: center;
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}
</style>

