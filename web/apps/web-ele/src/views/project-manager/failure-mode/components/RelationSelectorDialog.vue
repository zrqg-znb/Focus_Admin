<script lang="ts" setup>
import type { MasterResourceKind } from '../data';

import type {
  HandlingMeasureItem,
  HuatuoDiagnosisItem,
  InterceptionStrategyItem,
  ObservationMethodItem,
  RelationItem,
  TestCaseItem,
} from '#/api/project-manager/failure_mode';

import { computed, nextTick, ref } from 'vue';

import { Edit, Plus, Search } from '@element-plus/icons-vue';
import {
  ElButton,
  ElDialog,
  ElEmpty,
  ElInput,
  ElPagination,
  ElScrollbar,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import {
  listHandlingMeasuresApi,
  listHuatuoDiagnosesApi,
  listInterceptionStrategiesApi,
  listObservationMethodsApi,
  listTestCasesApi,
} from '#/api/project-manager/failure_mode';

import {
  buildRelationItem,
  ensureOrderedRelationItems,
  getMasterResourceLabel,
  getResourceDisplaySubtitle,
  getResourceDisplayTitle,
  normalizeStringList,
} from '../data';

defineOptions({ name: 'RelationSelectorDialog' });

const emit = defineEmits<{
  confirm: [
    payload: { ids: string[]; items: RelationItem[]; kind: MasterResourceKind },
  ];
  quickCreate: [kind: MasterResourceKind];
  quickEdit: [payload: { id: string; kind: MasterResourceKind }];
}>();

type ResourceRow =
  | HandlingMeasureItem
  | HuatuoDiagnosisItem
  | InterceptionStrategyItem
  | ObservationMethodItem
  | TestCaseItem;

interface SelectorOpenOptions {
  kind: MasterResourceKind;
  selectedIds?: string[];
  selectedItems?: RelationItem[];
}

const visible = ref(false);
const loading = ref(false);
const keyword = ref('');
const currentKind = ref<MasterResourceKind>('interception');
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const rows = ref<ResourceRow[]>([]);
const tableRef = ref<InstanceType<typeof ElTable>>();
const selectedIds = ref<string[]>([]);
const selectedItems = ref<RelationItem[]>([]);
const syncingSelection = ref(false);

const dialogTitle = computed(
  () => `选择${getMasterResourceLabel(currentKind.value)}`,
);
const selectedItemsInOrder = computed(() =>
  ensureOrderedRelationItems(selectedIds.value, selectedItems.value),
);

function getListApi(kind: MasterResourceKind) {
  switch (kind) {
    case 'huatuo': {
      return listHuatuoDiagnosesApi;
    }
    case 'interception': {
      return listInterceptionStrategiesApi;
    }
    case 'measure': {
      return listHandlingMeasuresApi;
    }
    case 'observation': {
      return listObservationMethodsApi;
    }
    default: {
      return listTestCasesApi;
    }
  }
}

function updateSelectedItem(nextItem: RelationItem, shouldSelect = true) {
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

function removeSelected(id: string) {
  selectedIds.value = selectedIds.value.filter((item) => item !== id);
  selectedItems.value = selectedItems.value.filter((item) => item.id !== id);
  const row = rows.value.find((item) => item.id === id);
  if (row) {
    tableRef.value?.toggleRowSelection(row, false, false);
  }
}

function clearSelected() {
  selectedIds.value = [];
  selectedItems.value = [];
  tableRef.value?.clearSelection();
}

async function syncTableSelection() {
  await nextTick();
  syncingSelection.value = true;
  tableRef.value?.clearSelection();
  const selectedSet = new Set(selectedIds.value);
  rows.value.forEach((row) => {
    if (selectedSet.has(row.id)) {
      tableRef.value?.toggleRowSelection(row, true, false);
    }
  });
  syncingSelection.value = false;
}

async function loadList() {
  loading.value = true;
  try {
    const api = getListApi(currentKind.value);
    const response = await api({
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

function handleSelectionChange(selection: ResourceRow[]) {
  if (syncingSelection.value) {
    return;
  }
  const visibleIds = new Set(rows.value.map((item) => item.id));
  const selectedOnPage = new Set(selection.map((item) => item.id));

  visibleIds.forEach((id) => {
    if (!selectedOnPage.has(id)) {
      removeSelected(id);
    }
  });

  selection.forEach((row) => {
    updateSelectedItem(buildRelationItem(currentKind.value, row), true);
  });
}

function handleSearch() {
  page.value = 1;
  void loadList();
}

function handleOpen(options: SelectorOpenOptions) {
  currentKind.value = options.kind;
  keyword.value = '';
  page.value = 1;
  pageSize.value = 10;
  selectedIds.value = normalizeStringList(options.selectedIds || []);
  selectedItems.value = ensureOrderedRelationItems(
    selectedIds.value,
    options.selectedItems || [],
  );
  visible.value = true;
  void loadList();
}

function handleConfirm() {
  emit('confirm', {
    ids: [...selectedIds.value],
    items: ensureOrderedRelationItems(selectedIds.value, selectedItems.value),
    kind: currentKind.value,
  });
  visible.value = false;
}

function handleQuickCreate() {
  emit('quickCreate', currentKind.value);
}

function handleQuickEdit(id: string) {
  emit('quickEdit', { id, kind: currentKind.value });
}

function upsertSelection(nextItem: RelationItem, shouldSelect = true) {
  updateSelectedItem(nextItem, shouldSelect);
  const row = rows.value.find((item) => item.id === nextItem.id);
  if (row) {
    tableRef.value?.toggleRowSelection(row, shouldSelect, false);
  }
}

function getRowTitle(row: ResourceRow) {
  return getResourceDisplayTitle(currentKind.value, row);
}

function getRowSubtitle(row: ResourceRow) {
  return getResourceDisplaySubtitle(currentKind.value, row);
}

defineExpose({
  open: handleOpen,
  reload: loadList,
  upsertSelection,
});
</script>

<template>
  <ElDialog
    v-model="visible"
    :title="dialogTitle"
    append-to-body
    :destroy-on-close="false"
    top="6vh"
    width="1120px"
  >
    <div class="grid gap-4 lg:grid-cols-[1fr_300px]">
      <div class="space-y-4">
        <div
          class="flex flex-wrap items-center gap-3 rounded-xl border border-[var(--el-border-color-light)] bg-[var(--el-fill-color-light)] p-4"
        >
          <ElInput
            v-model="keyword"
            class="max-w-[360px]"
            clearable
            placeholder="请输入关键词搜索"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <Search class="h-4 w-4" />
            </template>
          </ElInput>
          <ElButton type="primary" @click="handleSearch">搜索</ElButton>
          <ElButton
            :icon="Plus"
            plain
            type="success"
            @click="handleQuickCreate"
          >
            快速新增
          </ElButton>
        </div>

        <div class="rounded-xl border border-[var(--el-border-color-light)]">
          <ElTable
            ref="tableRef"
            v-loading="loading"
            :data="rows"
            border
            height="460"
            row-key="id"
            @selection-change="handleSelectionChange"
          >
            <ElTableColumn type="selection" width="56" />
            <ElTableColumn label="主数据" min-width="320">
              <template #default="{ row }">
                <div class="py-1">
                  <div class="font-medium text-[var(--el-text-color-primary)]">
                    {{ getRowTitle(row) }}
                  </div>
                  <div
                    v-if="getRowSubtitle(row)"
                    class="mt-1 text-xs text-[var(--el-text-color-secondary)]"
                  >
                    {{ getRowSubtitle(row) }}
                  </div>
                </div>
              </template>
            </ElTableColumn>
            <ElTableColumn label="责任人" min-width="180">
              <template #default="{ row }">
                {{
                  (row.owner_info || [])
                    .map((item: any) => item.name || item.username)
                    .join('、') || '-'
                }}
              </template>
            </ElTableColumn>
            <ElTableColumn label="操作" width="100">
              <template #default="{ row }">
                <ElButton
                  :icon="Edit"
                  link
                  type="primary"
                  @click="handleQuickEdit(row.id)"
                >
                  快编
                </ElButton>
              </template>
            </ElTableColumn>
          </ElTable>

          <div
            class="flex justify-end border-t border-[var(--el-border-color-light)] px-4 py-3"
          >
            <ElPagination
              :current-page="page"
              :page-size="pageSize"
              :page-sizes="[10, 20, 50]"
              :total="total"
              background
              layout="total, sizes, prev, pager, next"
              @current-change="
                (value) => {
                  page = value;
                  loadList();
                }
              "
              @size-change="
                (value) => {
                  page = 1;
                  pageSize = value;
                  loadList();
                }
              "
            />
          </div>
        </div>
      </div>

      <div
        class="rounded-xl border border-[var(--el-border-color-light)] bg-[var(--el-fill-color-blank)]"
      >
        <div
          class="flex items-center justify-between border-b border-[var(--el-border-color-light)] px-4 py-3"
        >
          <div>
            <div
              class="text-sm font-semibold text-[var(--el-text-color-primary)]"
            >
              已选 {{ getMasterResourceLabel(currentKind) }}
            </div>
            <div class="mt-1 text-xs text-[var(--el-text-color-secondary)]">
              共 {{ selectedIds.length }} 项，支持跨搜索结果保留选择
            </div>
          </div>
          <ElButton link type="danger" @click="clearSelected">清空</ElButton>
        </div>

        <ElScrollbar height="518px">
          <div class="space-y-3 p-4">
            <template v-if="selectedItemsInOrder.length > 0">
              <div
                v-for="item in selectedItemsInOrder"
                :key="item.id"
                class="rounded-lg border border-[var(--el-border-color-lighter)] bg-[var(--el-fill-color-light)] px-3 py-3"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0 flex-1">
                    <div
                      class="truncate text-sm font-medium text-[var(--el-text-color-primary)]"
                    >
                      {{ item.label }}
                    </div>
                    <div
                      v-if="item.subtitle"
                      class="mt-1 text-xs text-[var(--el-text-color-secondary)]"
                    >
                      {{ item.subtitle }}
                    </div>
                  </div>
                  <ElTag
                    closable
                    size="small"
                    type="info"
                    @close="removeSelected(item.id)"
                  >
                    已选
                  </ElTag>
                </div>
              </div>
            </template>
            <ElEmpty v-else description="暂未选择任何主数据" :image-size="72" />
          </div>
        </ElScrollbar>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <ElButton @click="visible = false">取消</ElButton>
        <ElButton type="primary" @click="handleConfirm">确认选择</ElButton>
      </div>
    </template>
  </ElDialog>
</template>
