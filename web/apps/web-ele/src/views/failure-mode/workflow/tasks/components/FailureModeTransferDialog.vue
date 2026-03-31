<script lang="ts" setup>
import { ref, computed, nextTick } from 'vue';
import {
  ElDialog,
  ElInput,
  ElButton,
  ElTable,
  ElTableColumn,
  ElPagination,
  ElScrollbar,
  ElEmpty,
  ElMessage
} from 'element-plus';
import { Search, Delete, Plus } from '@element-plus/icons-vue';
import { listFailureModesApi } from '#/api/failure_mode';
import type { FailureModeItem } from '#/api/failure_mode';

const emit = defineEmits<{
  confirm: [payload: { ids: string[]; items: FailureModeItem[] }];
}>();

const visible = ref(false);
const loading = ref(false);
const keyword = ref('');
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const rows = ref<FailureModeItem[]>([]);
const tableRef = ref<InstanceType<typeof ElTable>>();

const selectedIds = ref<string[]>([]);
const selectedItems = ref<FailureModeItem[]>([]);
const syncingSelection = ref(false);

const extraFilters = ref<Record<string, any>>({});

async function loadList() {
  loading.value = true;
  try {
    const response = await listFailureModesApi({
      ...extraFilters.value,
      keyword: keyword.value.trim() || undefined,
      page: page.value,
      pageSize: pageSize.value,
    });
    rows.value = response.items || [];
    total.value = response.total || 0;
    await syncTableSelection();
  } finally {
    loading.value = false;
  }
}

async function syncTableSelection() {
  await nextTick();
  syncingSelection.value = true;
  tableRef.value?.clearSelection();
  const selectedSet = new Set(selectedIds.value);
  rows.value.forEach((row) => {
    if (selectedSet.has(row.id)) {
      updateSelectedItem(row, true);
      tableRef.value?.toggleRowSelection(row, true);
    }
  });
  syncingSelection.value = false;
}

function updateSelectedItem(nextItem: FailureModeItem, shouldSelect = true) {
  const nextIds = [...selectedIds.value];
  const idIndex = nextIds.indexOf(nextItem.id);
  if (shouldSelect && idIndex === -1) {
    nextIds.push(nextItem.id);
  }
  if (!shouldSelect && idIndex !== -1) {
    nextIds.splice(idIndex, 1);
  }
  selectedIds.value = nextIds;

  const nextItems = [...selectedItems.value];
  const itemIndex = nextItems.findIndex((item) => item.id === nextItem.id);
  if (shouldSelect) {
    if (itemIndex === -1) {
      nextItems.push(nextItem);
    } else {
      nextItems[itemIndex] = nextItem;
    }
  } else if (itemIndex !== -1) {
    nextItems.splice(itemIndex, 1);
  }
  selectedItems.value = nextItems;
}

function handleSelect(selection: FailureModeItem[], row: FailureModeItem) {
  if (syncingSelection.value) return;
  const isSelected = selection.some((item) => item.id === row.id);
  if (isSelected) {
    updateSelectedItem(row, true);
  } else {
    updateSelectedItem(row, false);
  }
}

function handleSelectAll(selection: FailureModeItem[]) {
  if (syncingSelection.value) return;
  const isAllSelected = selection.length > 0;
  if (isAllSelected) {
    rows.value.forEach((row) => updateSelectedItem(row, true));
  } else {
    rows.value.forEach((row) => updateSelectedItem(row, false));
  }
}

function removeSelected(id: string) {
  const row = selectedItems.value.find((item) => item.id === id);
  if (row) {
    updateSelectedItem(row, false);
    const tableRow = rows.value.find((item) => item.id === id);
    if (tableRow) {
      tableRef.value?.toggleRowSelection(tableRow, false);
    }
  }
}

function clearSelected() {
  selectedIds.value = [];
  selectedItems.value = [];
  tableRef.value?.clearSelection();
}

function handleSearch() {
  page.value = 1;
  loadList();
}

function handleConfirm() {
  emit('confirm', {
    ids: [...selectedIds.value],
    items: [...selectedItems.value],
  });
  visible.value = false;
}

function open(options?: { selectedIds?: string[]; selectedItems?: FailureModeItem[]; extraFilters?: Record<string, any> }) {
  keyword.value = '';
  page.value = 1;
  selectedIds.value = [...(options?.selectedIds || [])];
  selectedItems.value = [...(options?.selectedItems || [])];
  extraFilters.value = options?.extraFilters || {};
  visible.value = true;
  loadList();
}

defineExpose({ open });
</script>

<template>
  <ElDialog
    v-model="visible"
    title="选择故障模式"
    width="80%"
    top="5vh"
    destroy-on-close
    :close-on-click-modal="false"
  >
    <div class="flex h-[600px] gap-4">
      <div class="flex flex-1 flex-col overflow-hidden border rounded-lg">
        <div class="flex items-center justify-between p-3 border-b bg-gray-50">
          <span class="font-medium text-gray-700">故障模式列表</span>
          <div class="flex w-64 items-center gap-2">
            <ElInput
              v-model="keyword"
              placeholder="搜索简述/子系统..."
              clearable
              @keyup.enter="handleSearch"
            >
              <template #prefix>
                <ElIcon><Search /></ElIcon>
              </template>
            </ElInput>
          </div>
        </div>
        <div class="flex-1 overflow-hidden p-2">
          <ElTable
            ref="tableRef"
            v-loading="loading"
            :data="rows"
            height="100%"
            border
            row-key="id"
            @select="handleSelect"
            @select-all="handleSelectAll"
          >
            <ElTableColumn type="selection" width="50" align="center" />
            <ElTableColumn prop="brief" label="故障模式简述" min-width="200" show-overflow-tooltip />
            <ElTableColumn prop="subsystem" label="子系统" width="120" show-overflow-tooltip />
            <ElTableColumn prop="module" label="模块" width="120" show-overflow-tooltip />
            <ElTableColumn prop="status" label="状态" width="100" />
          </ElTable>
        </div>
        <div class="flex items-center justify-end p-2 border-t">
          <ElPagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :total="total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            small
            @current-change="loadList"
            @size-change="loadList"
          />
        </div>
      </div>

      <div class="flex w-[350px] flex-col overflow-hidden border rounded-lg bg-gray-50">
        <div class="flex items-center justify-between p-3 border-b bg-white">
          <span class="font-medium text-gray-700">已选 ({{ selectedItems.length }})</span>
          <ElButton v-if="selectedItems.length" type="danger" link @click="clearSelected">
            清空
          </ElButton>
        </div>
        <div class="flex-1 overflow-hidden p-2">
          <ElScrollbar v-if="selectedItems.length > 0">
            <div class="space-y-2">
              <div
                v-for="item in selectedItems"
                :key="item.id"
                class="group flex items-center justify-between rounded border bg-white p-2 text-sm shadow-sm transition-colors hover:border-primary"
              >
                <div class="flex flex-1 flex-col overflow-hidden">
                  <span class="truncate font-medium" :title="item.brief">{{ item.brief }}</span>
                  <span class="text-xs text-gray-500 truncate" v-if="item.subsystem">
                    {{ item.subsystem }}
                  </span>
                </div>
                <ElButton
                  type="danger"
                  link
                  class="ml-2 opacity-0 transition-opacity group-hover:opacity-100"
                  @click="removeSelected(item.id)"
                >
                  <ElIcon><Delete /></ElIcon>
                </ElButton>
              </div>
            </div>
          </ElScrollbar>
          <ElEmpty v-else description="暂无选中项" :image-size="60" />
        </div>
      </div>
    </div>
    <template #footer>
      <div class="flex items-center justify-end">
        <ElButton @click="visible = false">取消</ElButton>
        <ElButton type="primary" :loading="loading" @click="handleConfirm">确定绑定</ElButton>
      </div>
    </template>
  </ElDialog>
</template>

<style scoped>
</style>
