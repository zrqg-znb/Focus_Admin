<script lang="ts" setup>
import type { PropType } from 'vue';

import type { ExtendedZqTableApi, ZqTableProps } from './types';

import {
  computed,
  defineComponent,
  h,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  toRaw,
  useSlots,
  watch,
} from 'vue';

import { usePriorityValues } from '@vben/hooks';
import { EmptyIcon, IconifyIcon } from '@vben/icons';
import { $t } from '@vben/locales';
import { cn, isBoolean, isEqual, mergeWithArrayOverride } from '@vben/utils';

import {
  Download,
  FullScreen,
  Refresh,
  Search,
  Setting,
} from '@element-plus/icons-vue';
import { useResizeObserver } from '@vueuse/core';
import {
  ElButton,
  ElCheckbox,
  ElCheckboxGroup,
  ElDialog,
  ElDivider,
  ElIcon,
  ElInput,
  ElMessage,
  ElPagination,
  ElPopover,
  ElRadioButton,
  ElRadioGroup,
  ElScrollbar,
  ElTable,
  ElTableColumn,
  ElTooltip,
} from 'element-plus';
import draggable from 'vuedraggable';
import * as XLSX from 'xlsx';

import { useTableForm } from './init';
import TableHeaderHelp from './table-header-help.vue';

import './style.css';

interface Props extends ZqTableProps {
  api: ExtendedZqTableApi;
}

interface ColumnState {
  depth: number;
  key: string;
  title: string;
  visible: boolean;
  fixed: 'left' | 'right' | false;
  originalIndex: number;
}

interface HeaderHelpConfig {
  definition?: string;
  editableHint?: string;
  formula?: string;
  placement?:
    | 'bottom'
    | 'bottom-end'
    | 'bottom-start'
    | 'left'
    | 'right'
    | 'top'
    | 'top-end'
    | 'top-start';
  width?: number;
}
type ExportScope = 'all' | 'current';

interface ExportColumnOption {
  key: string;
  label: string;
  prop: string;
}
interface ExportColumnGroup {
  columns: ExportColumnOption[];
  key: string;
  label: string;
}
const props = withDefaults(defineProps<Props>(), {});
const emit = defineEmits([
  'selectionChange',
  'sortChange',
  'filterChange',
  'row-click',
  'row-dblclick',
]);
function getColumnDataKey(col: any): string | undefined {
  const rawKey = col?.key ?? col?.dataKey ?? col?.prop ?? col?.field;
  if (rawKey === undefined || rawKey === null || rawKey === '') {
    return undefined;
  }
  return String(rawKey);
}

function getColumnStateKey(col: any, path: number[]): string {
  const dataKey = getColumnDataKey(col);
  if (dataKey) {
    return dataKey;
  }
  return `__zq_col_${path.join('_')}`;
}

const tableContainerRef = ref<HTMLElement>();
const tableHeight = ref(0);

const isFullscreen = ref(false);
function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value;
}

useResizeObserver(tableContainerRef, (entries) => {
  const entry = entries[0];
  if (!entry) return;
  const { height } = entry.contentRect;
  const nextHeight = Math.max(0, Math.floor(height));
  if (Math.abs(nextHeight - tableHeight.value) >= 1) {
    tableHeight.value = nextHeight;
  }
});

const FORM_SLOT_PREFIX = 'form-';
const CELL_SLOT_PREFIX = 'cell-';
const HEADER_SLOT_PREFIX = 'header-';
const TOOLBAR_ACTIONS = 'toolbar-actions';
const TOOLBAR_TOOLS = 'toolbar-tools';
const TABLE_TITLE = 'table-title';

const state = props.api?.useStore?.();

const {
  gridOptions,
  class: className,
  gridClass,
  formOptions,
  tableTitle,
  showSearchForm,
  separator,
} = usePriorityValues(props, state);
type ResolvedGridOptions = NonNullable<ZqTableProps['gridOptions']>;
type ResolvedFormOptions = NonNullable<ZqTableProps['formOptions']>;
const isSeparator = computed(() => {
  if (
    !formOptions.value ||
    showSearchForm.value === false ||
    separator.value === false
  ) {
    return false;
  }
  if (separator.value === true || separator.value === undefined) {
    return true;
  }
  return separator.value.show !== false;
});

const separatorBg = computed(() => {
  return !separator.value ||
    isBoolean(separator.value) ||
    !separator.value.backgroundColor
    ? undefined
    : separator.value.backgroundColor;
});

const slots = useSlots();
// 防抖定时器
let debounceTimer: null | ReturnType<typeof setTimeout> = null;

// 触发搜索
const triggerSearch = async () => {
  const formValues = await formApi.getValues();
  formApi.setLatestSubmissionValues(toRaw(formValues));
  props.api.reload(formValues);
};

// 防抖搜索
const debouncedSearch = () => {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }
  debounceTimer = setTimeout(() => {
    triggerSearch();
  }, 300);
};

// Initialize Form
const [Form, formApi] = useTableForm({
  compact: true,
  handleSubmit: async () => {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    await triggerSearch();
  },
  handleReset: async () => {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    const prevValues = await formApi.getValues();
    await formApi.resetForm();
    const formValues = await formApi.getValues();
    formApi.setLatestSubmissionValues(formValues);
    if (isEqual(prevValues, formValues) || !formOptions.value?.submitOnChange) {
      props.api.reload(formValues);
    }
  },
  commonConfig: {
    componentProps: {
      class: 'w-full',
      clearable: true,
    },
  },
  showCollapseButton: true,
  collapseTriggerResize: true, // 自动检测是否需要折叠
  submitOnChange: true, // 默认启用输入时触发搜索
  submitButtonOptions: {
    content: computed(() => $t('common.search')),
  },
  resetButtonOptions: {
    content: computed(() => $t('common.reset')),
    type: undefined, // 覆盖默认的 type="button"，避免 ElButton 警告
  },
  wrapperClass: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
});

// 监听表单值变化，自动触发搜索
watch(
  () => formApi.form?.values,
  (newValues, oldValues) => {
    // 只有当 submitOnChange 为 true 时才自动搜索
    if (
      formOptions.value?.submitOnChange &&
      newValues &&
      oldValues && // 检查值是否真的变化了
      !isEqual(newValues, oldValues)
    ) {
      debouncedSearch();
    }
  },
  { deep: true },
);

// Toolbar logic
const showTableTitle = computed(() => {
  return !!slots[TABLE_TITLE] || tableTitle.value;
});

const showToolbar = computed(() => {
  return (
    !!slots[TOOLBAR_ACTIONS] ||
    !!slots[TOOLBAR_TOOLS] ||
    showTableTitle.value ||
    !!gridOptions.value?.toolbarConfig
  );
});

const delegatedFormSlots = computed(() => {
  const resultSlots: string[] = [];
  for (const key of Object.keys(slots)) {
    if (key.startsWith(FORM_SLOT_PREFIX)) {
      resultSlots.push(key);
    }
  }
  return resultSlots.map((key) => key.replace(FORM_SLOT_PREFIX, ''));
});

// Data & Pagination binding
const tableData = props.api.tableData;
const total = props.api.total;
const loading = props.api.loading;
const pagination = props.api.pagination;

function onPageChange(currentPage: number) {
  props.api.handlePageChange(currentPage, pagination.pageSize);
}

function onPageSizeChange(pageSize: number) {
  props.api.handlePageChange(pagination.currentPage, pageSize);
}

function onSearchBtnClick() {
  props.api.toggleSearchForm();
}

function onRefreshBtnClick() {
  props.api.reload();
}

// Init logic
async function init() {
  await nextTick();
  const defaultGridOptions = mergeWithArrayOverride(
    {},
    toRaw(gridOptions.value),
  ) as ResolvedGridOptions;

  const autoLoad = defaultGridOptions.proxyConfig?.autoLoad;
  if (autoLoad) {
    props.api.reload();
  }
}

// Column Setting State
const columnState = ref<ColumnState[]>([]);

function initColumnState() {
  const cols = gridOptions.value?.columns;
  if (!cols) {
    columnState.value = [];
    return;
  }

  const flattenedState: ColumnState[] = [];
  let leafIndex = 0;

  const visitColumns = (
    sourceColumns: any[],
    path: number[] = [],
    titlePath: string[] = [],
  ) => {
    sourceColumns.forEach((col, index) => {
      const currentPath = [...path, index];
      const currentTitle =
        col?.title ||
        col?.label ||
        getColumnDataKey(col) ||
        `列-${flattenedState.length + 1}`;
      const nextTitlePath = [...titlePath, String(currentTitle)];
      const children = Array.isArray(col?.children) ? col.children : [];

      if (children.length > 0) {
        visitColumns(children, currentPath, nextTitlePath);
        return;
      }

      flattenedState.push({
        key: getColumnStateKey(col, currentPath),
        title: nextTitlePath.join(' / '),
        visible: col.hidden !== true,
        fixed: col.fixed === true ? 'left' : col.fixed || false,
        originalIndex: leafIndex,
        depth: Math.max(0, nextTitlePath.length - 1),
      });
      leafIndex += 1;
    });
  };

  visitColumns(cols as any[]);
  columnState.value = flattenedState;
}

watch(
  () => gridOptions.value?.columns,
  () => {
    initColumnState();
  },
  { immediate: true },
);

function handleResetColumn() {
  initColumnState();
}

function handleToggleFixed(col: ColumnState, type: 'left' | 'right') {
  col.fixed = col.fixed === type ? false : type;
}

watch(
  formOptions,
  () => {
    formApi.setState((prev) => {
      const finalFormOptions = mergeWithArrayOverride(
        {},
        formOptions.value,
        prev,
      ) as ResolvedFormOptions;
      return {
        ...finalFormOptions,
        // 自动检测是否需要折叠按钮
        collapseTriggerResize: finalFormOptions.showCollapseButton ?? true,
        // 默认启用输入时触发搜索，除非明确设置为 false
        submitOnChange: finalFormOptions.submitOnChange ?? true,
      };
    });
  },
  { immediate: true },
);

const isCompactForm = computed(() => {
  return formApi.getState()?.compact;
});
const pagerPageSizes = computed<number[]>(() => {
  const pageSizes = gridOptions.value?.pagerConfig?.pageSizes;
  if (!Array.isArray(pageSizes) || pageSizes.length === 0) {
    return [10, 20, 50, 100];
  }
  const validPageSizes = pageSizes.filter(
    (size): size is number => typeof size === 'number' && Number.isFinite(size),
  );
  return validPageSizes.length > 0 ? validPageSizes : [10, 20, 50, 100];
});
const pagerLayout = computed(
  () =>
    gridOptions.value?.pagerConfig?.layout ||
    'total, sizes, ->, prev, pager, next, jumper',
);
const pagerBackground = computed(
  () => gridOptions.value?.pagerConfig?.background !== false,
);
const resolvedTableHeight = computed<number | string | undefined>(() => {
  const configuredHeight = gridOptions.value?.height;
  if (
    configuredHeight !== undefined &&
    configuredHeight !== null &&
    configuredHeight !== ''
  ) {
    return configuredHeight;
  }
  return tableHeight.value > 0 ? tableHeight.value : undefined;
});

const tableProps = computed<Record<string, any>>(() => {
  const options = (gridOptions.value || {}) as Record<string, any>;
  const {
    columns: _columns,
    proxyConfig: _proxyConfig,
    pagerConfig: _pagerConfig,
    showIndex: _showIndex,
    showSelection: _showSelection,
    toolbarConfig: _toolbarConfig,
    ...rest
  } = options;
  return rest;
});
const exportLoading = ref(false);
const exportDialogVisible = ref(false);
const exportFilename = ref('');
const exportScope = ref<ExportScope>('current');
const exportColumnKeys = ref<string[]>([]);

function normalizeItems(result: any): Record<string, any>[] {
  if (Array.isArray(result)) {
    return result;
  }
  if (result && typeof result === 'object') {
    if (Array.isArray(result.items)) {
      return result.items;
    }
    if (Array.isArray(result.data)) {
      return result.data;
    }
  }
  return [];
}

function collectExportColumnGroups(cols: any[]): ExportColumnGroup[] {
  const groupMap = new Map<string, ExportColumnGroup>();
  const seenColumnKey = new Set<string>();

  const ensureGroup = (groupKey: string, label: string) => {
    if (!groupMap.has(groupKey)) {
      groupMap.set(groupKey, {
        key: groupKey,
        label,
        columns: [],
      });
    }
    return groupMap.get(groupKey)!;
  };

  const visit = (column: any, ancestors: string[]) => {
    const childColumns = Array.isArray(column.children) ? column.children : [];
    if (childColumns.length > 0) {
      const groupLabel = column.label || column.title;
      const nextAncestors = groupLabel
        ? [...ancestors, String(groupLabel)]
        : ancestors;
      childColumns.forEach((child: any) => visit(child, nextAncestors));
      return;
    }

    if (column.type || !column.prop) return;
    const prop = String(column.prop);
    if (prop === 'actions' || prop === 'operation') return;
    const columnKey = String(column.key || prop);
    if (seenColumnKey.has(columnKey)) return;
    seenColumnKey.add(columnKey);

    const groupKey =
      ancestors.length > 0 ? ancestors.join(' / ') : '__zq_export_base__';
    const groupLabel = ancestors.at(-1) || '基础字段';
    ensureGroup(groupKey, groupLabel).columns.push({
      key: columnKey,
      label: String(column.label || column.title || prop),
      prop,
    });
  };

  cols.forEach((column) => visit(column, []));
  return [...groupMap.values()];
}

function normalizeCellValue(value: any): number | string {
  if (value === null || value === undefined) {
    return '';
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return value;
}

const exportConfig = computed(() => gridOptions.value?.toolbarConfig?.export);
const exportConfigObject = computed<
  | undefined
  | {
      all?: boolean;
      allowAll?: boolean;
      defaultColumns?: string[];
      defaultScope?: ExportScope;
      filename?: string;
      maxAutoPages?: number;
      pagedFallback?: boolean;
    }
>(() => {
  const currentExportConfig = exportConfig.value;
  if (!currentExportConfig || typeof currentExportConfig !== 'object') {
    return undefined;
  }
  return currentExportConfig;
});
const allowExportAll = computed(() => {
  const current = exportConfigObject.value;
  if (!current) {
    return true;
  }
  if (typeof current.allowAll === 'boolean') {
    return current.allowAll;
  }
  if (typeof current.all === 'boolean') {
    return current.all;
  }
  return true;
});
const allowPagedFallback = computed(() => {
  const current = exportConfigObject.value;
  if (!current) return true;
  return current.pagedFallback !== false;
});
const maxAutoExportPages = computed(() => {
  const configured = Number(exportConfigObject.value?.maxAutoPages ?? 200);
  if (!Number.isFinite(configured) || configured <= 0) {
    return 200;
  }
  return Math.floor(configured);
});
const exportColumnGroups = computed<ExportColumnGroup[]>(() => {
  return collectExportColumnGroups(columns.value);
});
const exportColumnOptions = computed<ExportColumnOption[]>(() => {
  return exportColumnGroups.value.flatMap((group) => group.columns);
});
const exportColumnOptionKeys = computed<string[]>(() => {
  return exportColumnOptions.value.map((column) => column.key);
});
const isAllExportColumnsChecked = computed(() => {
  if (exportColumnOptionKeys.value.length === 0) {
    return false;
  }
  return exportColumnKeys.value.length === exportColumnOptionKeys.value.length;
});
const isExportColumnsIndeterminate = computed(() => {
  return (
    exportColumnKeys.value.length > 0 &&
    exportColumnKeys.value.length < exportColumnOptionKeys.value.length
  );
});

function getExportBaseName() {
  const currentExportConfig = exportConfigObject.value;
  if (currentExportConfig?.filename) {
    return currentExportConfig.filename;
  }
  if (tableTitle.value) {
    return String(tableTitle.value);
  }
  return 'table-export';
}

function getDefaultExportScope(): ExportScope {
  if (!allowExportAll.value) {
    return 'current';
  }
  const currentExportConfig = exportConfigObject.value;
  if (currentExportConfig) {
    if (currentExportConfig.defaultScope === 'all' && allowExportAll.value) {
      return 'all';
    }
    if (currentExportConfig.defaultScope === 'current') {
      return 'current';
    }
    if (currentExportConfig.all) {
      return 'all';
    }
  }
  return 'current';
}

function getDefaultExportColumns(): string[] {
  const currentExportConfig = exportConfigObject.value;
  if (
    currentExportConfig &&
    Array.isArray(currentExportConfig.defaultColumns)
  ) {
    return currentExportConfig.defaultColumns.map(String);
  }
  return [];
}

async function getExportRowsByScope(scope: ExportScope) {
  if (scope === 'current') {
    return tableData.value;
  }
  if (!allowExportAll.value) {
    return tableData.value;
  }

  let formData: Record<string, any> = {};
  try {
    formData = await formApi.getValues();
  } catch {
    formData = {};
  }

  const queryAll = gridOptions.value?.proxyConfig?.ajax?.queryAll as
    | ((params: {
        form: Record<string, any>;
        sort: Record<string, any>;
      }) => Promise<any>)
    | undefined;
  if (typeof queryAll === 'function') {
    const result = await queryAll({
      form: formData,
      sort: {},
    });
    const items = normalizeItems(result);
    if (items.length > 0) {
      return items;
    }
  }
  if (!allowPagedFallback.value) {
    throw new Error('未配置 queryAll，且已禁用分页回退导出');
  }

  const query = gridOptions.value?.proxyConfig?.ajax?.query as
    | ((params: {
        form: Record<string, any>;
        page: {
          currentPage: number;
          pageSize: number;
          total: number;
        };
        sort: Record<string, any>;
      }) => Promise<any>)
    | undefined;
  if (typeof query !== 'function') {
    return tableData.value;
  }

  const pageSize = Math.max(Number(pagination.pageSize || 20), 200);
  const firstResult = await query({
    form: formData,
    page: {
      currentPage: 1,
      pageSize,
      total: 0,
    },
    sort: {},
  });
  if (Array.isArray(firstResult)) {
    return firstResult;
  }

  const firstItems = normalizeItems(firstResult);
  const total =
    typeof firstResult?.total === 'number' && Number.isFinite(firstResult.total)
      ? firstResult.total
      : firstItems.length;
  if (total <= firstItems.length) {
    return firstItems.length > 0 ? firstItems : tableData.value;
  }

  const mergedItems = [...firstItems];
  const totalPages = Math.ceil(total / pageSize);
  if (totalPages > maxAutoExportPages.value) {
    throw new Error(
      `全量导出页数(${totalPages})超过上限(${maxAutoExportPages.value})`,
    );
  }
  for (let page = 2; page <= totalPages; page++) {
    const pageResult = await query({
      form: formData,
      page: {
        currentPage: page,
        pageSize,
        total,
      },
      sort: {},
    });
    const pageItems = normalizeItems(pageResult);
    if (pageItems.length === 0) {
      break;
    }
    mergedItems.push(...pageItems);
    if (mergedItems.length >= total) {
      break;
    }
  }
  return mergedItems.length > 0 ? mergedItems : tableData.value;
}

function handleExportCheckAll(checked: any) {
  exportColumnKeys.value =
    checked === true ? [...exportColumnOptionKeys.value] : [];
}

function isGroupChecked(group: ExportColumnGroup) {
  if (group.columns.length === 0) return false;
  const selectedKeys = new Set(exportColumnKeys.value);
  return group.columns.every((column) => selectedKeys.has(column.key));
}

function isGroupIndeterminate(group: ExportColumnGroup) {
  if (group.columns.length === 0) return false;
  const selectedKeys = new Set(exportColumnKeys.value);
  const selectedCount = group.columns.filter((column) =>
    selectedKeys.has(column.key),
  ).length;
  return selectedCount > 0 && selectedCount < group.columns.length;
}

function handleGroupCheck(group: ExportColumnGroup, checked: boolean) {
  const selectedKeys = new Set(exportColumnKeys.value);
  if (checked) {
    group.columns.forEach((column) => {
      selectedKeys.add(column.key);
    });
  } else {
    group.columns.forEach((column) => {
      selectedKeys.delete(column.key);
    });
  }
  exportColumnKeys.value = [...selectedKeys];
}

function openExportDialog() {
  if (exportColumnOptions.value.length === 0) {
    ElMessage.warning('暂无可导出的列');
    return;
  }

  exportFilename.value = getExportBaseName();
  const preferredScope = getDefaultExportScope();
  exportScope.value =
    preferredScope === 'all' && !allowExportAll.value
      ? 'current'
      : preferredScope;

  const allowedKeys = new Set(exportColumnOptionKeys.value);
  const preferredColumns = getDefaultExportColumns().filter((key) =>
    allowedKeys.has(key),
  );
  exportColumnKeys.value =
    preferredColumns.length > 0
      ? preferredColumns
      : [...exportColumnOptionKeys.value];

  exportDialogVisible.value = true;
}

async function onExportBtnClick() {
  if (exportLoading.value) {
    return;
  }
  openExportDialog();
}

async function handleExportConfirm() {
  if (exportColumnKeys.value.length === 0) {
    ElMessage.warning('请至少选择一列进行导出');
    return;
  }

  const filename = exportFilename.value.trim() || getExportBaseName();
  const selectedKeySet = new Set(exportColumnKeys.value);
  const selectedColumns = exportColumnOptions.value.filter((column) =>
    selectedKeySet.has(column.key),
  );
  if (selectedColumns.length === 0) {
    ElMessage.warning('请至少选择一列进行导出');
    return;
  }

  exportLoading.value = true;
  try {
    const xlsx = (XLSX as any)?.utils ? (XLSX as any) : (XLSX as any)?.default;
    if (!xlsx?.utils) {
      throw new TypeError('xlsx utils unavailable');
    }
    const writeFile = xlsx.writeFileXLSX || xlsx.writeFile;
    if (typeof writeFile !== 'function') {
      throw new TypeError('xlsx writeFile unavailable');
    }
    const rows = await getExportRowsByScope(exportScope.value);
    if (rows.length === 0) {
      ElMessage.warning('暂无可导出数据');
      return;
    }
    const exportRows = rows.map((row) => {
      const line: Record<string, any> = {};
      selectedColumns.forEach((column) => {
        line[column.label] = normalizeCellValue(row[column.prop]);
      });
      return line;
    });

    const worksheet = xlsx.utils.json_to_sheet(exportRows);
    const workbook = xlsx.utils.book_new();
    xlsx.utils.book_append_sheet(workbook, worksheet, 'Sheet1');
    const stamp = new Date().toISOString().slice(0, 10);
    writeFile(workbook, `${filename}-${stamp}.xlsx`);
    exportDialogVisible.value = false;
    ElMessage.success('导出成功');
  } catch (error) {
    console.error('[zq-table export failed]', error);
    const message =
      error instanceof Error && error.message
        ? `导出失败：${error.message}`
        : '导出失败，请检查依赖或数据格式';
    ElMessage.error(message);
  } finally {
    exportLoading.value = false;
  }
}

onMounted(() => {
  props.api.mount(formApi);
  init();
});

onUnmounted(() => {
  props.api.unmount();
});

// 获取单元格插槽名称列表
const cellSlotNames = computed(() => {
  const result: Record<string, string> = {};
  for (const key of Object.keys(slots)) {
    if (key.startsWith(CELL_SLOT_PREFIX)) {
      const colKey = key.replace(CELL_SLOT_PREFIX, '');
      result[colKey] = key;
    }
  }
  return result;
});
const headerSlotNames = computed(() => {
  const result: Record<string, string> = {};
  for (const key of Object.keys(slots)) {
    if (key.startsWith(HEADER_SLOT_PREFIX)) {
      const colKey = key.replace(HEADER_SLOT_PREFIX, '');
      result[colKey] = key;
    }
  }
  return result;
});

const TableColumnRenderer = defineComponent({
  name: 'ZqTableColumnRenderer',
  props: {
    column: {
      type: Object as PropType<Record<string, any>>,
      required: true,
    },
  },
  setup(componentProps) {
    const renderColumn = (
      column: Record<string, any>,
      columnIndex = 0,
    ): ReturnType<typeof h> => {
      const childColumns = Array.isArray(column.children)
        ? column.children
        : [];
      const hasChildren = childColumns.length > 0;
      const columnProps = { ...column };
      delete columnProps.children;
      delete columnProps.slotName;
      delete columnProps.headerSlotName;
      if (hasChildren) {
        delete columnProps.prop;
        delete columnProps.field;
        delete columnProps.dataKey;
      }

      const columnSlots: Record<string, (scope?: any) => any> = {};

      if (column.headerSlotName && slots[column.headerSlotName]) {
        columnSlots.header = (scope: any) =>
          slots[column.headerSlotName]?.({ ...scope, column });
      } else if (column.headerHelp && !column.type) {
        const headerHelp = (column.headerHelp || {}) as HeaderHelpConfig;
        const headerLabel = column.label || column.title || column.prop || '';
        columnSlots.header = () =>
          h(TableHeaderHelp, {
            ...headerHelp,
            label: String(headerLabel),
          });
      }

      if (hasChildren) {
        columnSlots.default = () =>
          childColumns.map((child, childIndex) =>
            renderColumn(child, childIndex),
          );
      } else if (
        column.type === 'expand' &&
        column.slotName &&
        slots[column.slotName]
      ) {
        columnSlots.default = (scope: any) =>
          slots[column.slotName]?.({
            row: scope.row,
            $index: scope.$index,
            column,
          });
      } else if (!column.type) {
        columnSlots.default = (scope: any) => {
          if (column.slotName && slots[column.slotName]) {
            return slots[column.slotName]?.({
              row: scope.row,
              $index: scope.$index,
              column,
            });
          }

          if (typeof column.cellRenderer === 'function') {
            return column.cellRenderer({
              cellData: scope.row[column.prop],
              rowData: scope.row,
              rowIndex: scope.$index,
              column,
            });
          }

          return h('span', scope.row[column.prop]);
        };
      }

      return h(
        ElTableColumn,
        {
          ...columnProps,
          key:
            column?.prop ||
            column?.key ||
            column?.field ||
            column?.type ||
            columnIndex,
        },
        columnSlots,
      );
    };

    return () => {
      return renderColumn(componentProps.column);
    };
  },
});

// 设置弹性列（最后一个非固定、非特殊列），移除其 width 让它自动填充剩余空间
function setFlexColumn(cols: any[]) {
  // 从后往前找第一个非固定、非 type（selection/index）、非 actions 的列
  for (let i = cols.length - 1; i >= 0; i--) {
    const col = cols[i];
    if (
      !col.type &&
      !col.fixed &&
      !Array.isArray(col.children) &&
      col.prop !== 'actions' &&
      col.key !== 'actions' &&
      col.field !== 'actions' &&
      col.prop !== 'operation' &&
      col.key !== 'operation' &&
      col.field !== 'operation'
    ) {
      // 移除 width，保留 minWidth
      delete col.width;
      if (!col.minWidth) {
        col.minWidth = 100;
      }
      break;
    }
  }
  return cols;
}

// Table Columns
const columns = computed(() => {
  const cols = (gridOptions.value?.columns || []) as any[];
  const stateMap = new Map(columnState.value.map((item) => [item.key, item]));
  const orderMap = new Map(
    columnState.value.map((item, index) => [item.key, index]),
  );

  const processCol = (column: any, path: number[]): any | null => {
    const colKey = getColumnDataKey(column);
    const stateKey = getColumnStateKey(column, path);
    const stateItem = stateMap.get(stateKey);
    if (stateItem && !stateItem.visible) {
      return null;
    }

    const customCellSlotName = column?.slots?.default;
    const customHeaderSlotName = column?.slots?.header;
    const slotName =
      (customCellSlotName && slots[customCellSlotName]
        ? customCellSlotName
        : undefined) || (colKey ? cellSlotNames.value[colKey] : undefined);
    const headerSlotName =
      (customHeaderSlotName && slots[customHeaderSlotName]
        ? customHeaderSlotName
        : undefined) || (colKey ? headerSlotNames.value[colKey] : undefined);

    const rawChildren = Array.isArray(column.children) ? column.children : [];
    const children = rawChildren
      .map((child: any, index: number) => processCol(child, [...path, index]))
      .filter(Boolean);
    const hasChildren = children.length > 0;

    if (!hasChildren && rawChildren.length > 0) {
      return null;
    }

    const columnProps = { ...column };
    delete columnProps.children;
    delete columnProps.slotName;
    delete columnProps.headerSlotName;
    if (hasChildren) {
      delete columnProps.prop;
      delete columnProps.field;
      delete columnProps.dataKey;
    }

    return {
      ...columnProps,
      fixed: stateItem?.fixed ?? columnProps.fixed,
      prop: hasChildren ? undefined : colKey, // group column must not set prop
      label: column.title || column.label, // el-table uses label
      slotName: slotName && slots[slotName] ? slotName : undefined,
      headerSlotName:
        headerSlotName && slots[headerSlotName] ? headerSlotName : undefined,
      resizable: column.resizable ?? true,
      showOverflowTooltip: column.showOverflowTooltip ?? true, // 默认开启溢出提示
      children,
      __order: hasChildren
        ? Math.min(
            ...children.map((item: any) =>
              Number.isFinite(item?.__order)
                ? item.__order
                : Number.MAX_SAFE_INTEGER,
            ),
          )
        : (orderMap.get(stateKey) ??
          stateItem?.originalIndex ??
          Number.MAX_SAFE_INTEGER),
    };
  };

  const stripOrderField = (column: any): any => {
    const { __order, children, ...rest } = column;
    if (Array.isArray(children) && children.length > 0) {
      return {
        ...rest,
        children: [...children]
          .sort((a: any, b: any) => (a.__order ?? 0) - (b.__order ?? 0))
          .map((item: any) => stripOrderField(item)),
      };
    }
    return rest;
  };

  // 如果没有初始化 columnState，直接返回所有列
  if (columnState.value.length === 0) {
    const processedCols = cols
      .map((column, index) => processCol(column, [index]))
      .filter(Boolean) as any[];

    // 处理 Selection 和 Index
    const prefixCols: any[] = [];
    if (gridOptions.value?.showSelection) {
      prefixCols.push({
        type: 'selection',
        width: 50,
        fixed: 'left',
        align: 'center',
      });
    }
    if (gridOptions.value?.showIndex) {
      prefixCols.push({
        type: 'index',
        width: 60,
        label: '#',
        fixed: 'left',
        align: 'center',
      });
    }

    const final = [
      ...prefixCols,
      ...processedCols.map((item: any) => stripOrderField(item)),
    ];

    // 强制 actions 列在最后且固定右侧
    const actionIndex = final.findIndex(
      (c: any) =>
        c.prop === 'actions' || c.key === 'actions' || c.field === 'actions',
    );
    if (actionIndex !== -1) {
      const actionCol = final.splice(actionIndex, 1)[0];
      actionCol.fixed = 'right';
      final.push(actionCol);
    }
    return setFlexColumn(final);
  }

  const finalCols: any[] = [];

  // 处理 Selection 和 Index
  if (gridOptions.value?.showSelection) {
    finalCols.push({
      type: 'selection',
      width: 50,
      fixed: 'left',
      align: 'center',
    });
  }
  if (gridOptions.value?.showIndex) {
    finalCols.push({
      type: 'index',
      width: 60,
      label: '#',
      fixed: 'left',
      align: 'center',
    });
  }

  const processedCols = cols
    .map((column, index) => processCol(column, [index]))
    .filter(Boolean) as any[];
  processedCols
    .sort((a: any, b: any) => (a.__order ?? 0) - (b.__order ?? 0))
    .map((item: any) => stripOrderField(item))
    .forEach((col) => finalCols.push(col));

  // 强制 actions 列在最后且固定右侧
  const actionIndex = finalCols.findIndex(
    (c: any) =>
      c.prop === 'actions' || c.key === 'actions' || c.field === 'actions',
  );
  if (actionIndex !== -1) {
    const actionCol = finalCols.splice(actionIndex, 1)[0];
    actionCol.fixed = 'right';
    finalCols.push(actionCol);
  }

  return setFlexColumn(finalCols);
});

function handleSelectionChange(val: any[]) {
  emit('selectionChange', val);
}

function handleSortChange(data: any) {
  emit('sortChange', data);
}

function handleFilterChange(data: Record<string, any[]>) {
  emit('filterChange', data);
}
</script>

<template>
  <div
    :class="
      cn('bg-card flex h-full flex-col rounded-md', className, {
        'zq-table-fullscreen': isFullscreen,
      })
    "
  >
    <!-- Form -->
    <div
      v-if="formOptions"
      v-show="showSearchForm !== false"
      :class="
        cn(
          'relative rounded p-4',
          isCompactForm
            ? isSeparator
              ? 'pb-8'
              : 'pb-4'
            : isSeparator
              ? 'pb-4'
              : 'pb-0',
        )
      "
    >
      <slot name="form">
        <Form>
          <template
            v-for="slotName in delegatedFormSlots"
            :key="slotName"
            #[slotName]="slotProps"
          >
            <slot
              :name="`${FORM_SLOT_PREFIX}${slotName}`"
              v-bind="slotProps"
            ></slot>
          </template>
        </Form>
      </slot>
      <div
        v-if="isSeparator"
        :style="{
          ...(separatorBg ? { backgroundColor: separatorBg } : undefined),
        }"
        class="bg-background-deep z-100 absolute -left-2 bottom-1 h-2 w-[calc(100%+8px)] overflow-hidden md:bottom-2 md:h-3"
      ></div>
    </div>

    <!-- Toolbar -->
    <div
      v-if="showToolbar"
      class="flex items-center justify-between px-4 pb-4 pt-2"
    >
      <!-- Left: Title / Actions -->
      <div class="flex items-center">
        <slot v-if="showTableTitle" name="table-title">
          <div class="mr-1 pl-1 text-[1rem] font-medium">
            {{ tableTitle }}
          </div>
        </slot>
        <slot name="toolbar-actions"></slot>
      </div>

      <!-- Right: Tools -->
      <div class="flex items-center">
        <slot name="toolbar-tools"></slot>

        <!-- Default Tools -->
        <ElButton
          v-if="gridOptions?.toolbarConfig?.search && !!formOptions"
          circle
          :type="showSearchForm ? 'primary' : ''"
          :icon="Search"
          @click="onSearchBtnClick"
          :title="$t('common.search')"
        />
        <ElButton
          v-if="gridOptions?.toolbarConfig?.refresh !== false"
          circle
          @click="onRefreshBtnClick"
          :title="$t('common.refresh')"
        >
          <ElIcon :class="{ 'zq-spin': loading }">
            <Refresh />
          </ElIcon>
        </ElButton>
        <ElButton
          v-if="gridOptions?.toolbarConfig?.export"
          circle
          :icon="Download"
          :loading="exportLoading"
          @click="onExportBtnClick"
          title="导出 XLSX"
        />
        <ElButton
          v-if="gridOptions?.toolbarConfig?.zoom !== false"
          circle
          :type="isFullscreen ? 'primary' : ''"
          :icon="FullScreen"
          @click="toggleFullscreen"
          :title="
            isFullscreen ? $t('common.exitFullscreen') : $t('common.fullscreen')
          "
        />
        <ElPopover
          v-if="gridOptions?.toolbarConfig?.custom !== false"
          placement="bottom-end"
          :width="280"
          trigger="click"
        >
          <template #reference>
            <ElButton circle :icon="Setting" :title="$t('common.setting')" />
          </template>
          <div class="p-2">
            <div class="mb-2 flex items-center justify-between">
              <span class="font-bold">{{ $t('common.columnSetting') }}</span>
              <ElButton link size="small" @click="handleResetColumn">
                <IconifyIcon
                  icon="lucide:rotate-ccw"
                  class="mr-1 h-3.5 w-3.5"
                />
                {{ $t('common.reset') }}
              </ElButton>
            </div>
            <ElDivider class="!my-2" />
            <ElScrollbar max-height="300px">
              <draggable
                v-model="columnState"
                item-key="key"
                handle=".drag-handle"
                :animation="200"
              >
                <template #item="{ element }">
                  <div
                    class="hover:bg-accent/50 group mb-1 flex items-center rounded p-1"
                    :style="{
                      paddingLeft: `${Math.min(element.depth || 0, 4) * 10 + 4}px`,
                    }"
                  >
                    <IconifyIcon
                      icon="lucide:grip-vertical"
                      class="text-muted-foreground drag-handle mr-2 h-4 w-4 cursor-move opacity-0 group-hover:opacity-100"
                    />
                    <ElCheckbox
                      v-model="element.visible"
                      class="mr-2 !h-6 flex-1 truncate"
                      :label="element.title"
                      :title="element.title"
                    />

                    <div
                      class="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100"
                    >
                      <ElTooltip content="固定到左侧" placement="top">
                        <IconifyIcon
                          icon="lucide:pin"
                          class="h-3.5 w-3.5 cursor-pointer"
                          :class="
                            element.fixed === 'left'
                              ? 'text-primary rotate-[-45deg]'
                              : 'text-muted-foreground hover:text-foreground'
                          "
                          @click="handleToggleFixed(element, 'left')"
                        />
                      </ElTooltip>
                      <ElTooltip content="固定到右侧" placement="top">
                        <IconifyIcon
                          icon="lucide:pin"
                          class="h-3.5 w-3.5 scale-x-[-1] cursor-pointer"
                          :class="
                            element.fixed === 'right'
                              ? 'text-primary rotate-[-45deg]'
                              : 'text-muted-foreground hover:text-foreground'
                          "
                          @click="handleToggleFixed(element, 'right')"
                        />
                      </ElTooltip>
                    </div>
                  </div>
                </template>
              </draggable>
            </ElScrollbar>
          </div>
        </ElPopover>
      </div>
    </div>

    <!-- Table Body -->
    <div
      class="relative flex-1 overflow-hidden px-3"
      :class="gridClass"
      v-loading="loading"
    >
      <div class="h-full w-full" ref="tableContainerRef">
        <ElTable
          v-bind="tableProps"
          :data="tableData"
          :height="resolvedTableHeight"
          :style="{ width: '100%' }"
          header-row-class-name="zq-table-header"
          @selection-change="handleSelectionChange"
          @sort-change="handleSortChange"
          @filter-change="handleFilterChange"
        >
          <TableColumnRenderer
            v-for="(col, colIndex) in columns"
            :key="col.prop || col.key || col.type || col.field || colIndex"
            :column="col"
          />

          <template #empty>
            <slot name="empty">
              <div
                class="text-muted-foreground flex h-full flex-col items-center justify-center"
              >
                <EmptyIcon class="mx-auto" />
                <div class="mt-2">{{ $t('common.noData') }}</div>
              </div>
            </slot>
          </template>
        </ElTable>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="gridOptions?.pagerConfig?.enabled !== false" class="p-4">
      <ElPagination
        v-model:current-page="pagination.currentPage"
        v-model:page-size="pagination.pageSize"
        :total="total"
        :page-sizes="pagerPageSizes"
        :layout="pagerLayout"
        :background="pagerBackground"
        class="w-full"
        size="small"
        @current-change="onPageChange"
        @size-change="onPageSizeChange"
      />
    </div>

    <ElDialog
      v-model="exportDialogVisible"
      width="640px"
      destroy-on-close
      title="导出配置"
    >
      <div class="flex flex-col gap-4">
        <div>
          <div class="mb-2 text-sm font-medium">导出文件名</div>
          <ElInput
            v-model="exportFilename"
            clearable
            maxlength="80"
            placeholder="请输入文件名（不含后缀）"
          />
        </div>

        <div>
          <div class="mb-2 text-sm font-medium">数据范围</div>
          <ElRadioGroup v-model="exportScope">
            <ElRadioButton label="current">本页数据</ElRadioButton>
            <ElRadioButton v-if="allowExportAll" label="all">
              全量数据
            </ElRadioButton>
          </ElRadioGroup>
        </div>

        <div>
          <div class="mb-2 flex items-center justify-between">
            <span class="text-sm font-medium">导出列</span>
            <ElCheckbox
              :model-value="isAllExportColumnsChecked"
              :indeterminate="isExportColumnsIndeterminate"
              @change="handleExportCheckAll"
            >
              全选
            </ElCheckbox>
          </div>

          <ElScrollbar max-height="260px" wrap-class="pr-1">
            <div class="flex flex-col gap-3">
              <div
                v-for="group in exportColumnGroups"
                :key="group.key"
                class="bg-muted/20 rounded-md border p-3"
              >
                <div class="mb-2 flex items-center justify-between">
                  <div class="text-sm font-medium">{{ group.label }}</div>
                  <ElCheckbox
                    :model-value="isGroupChecked(group)"
                    :indeterminate="isGroupIndeterminate(group)"
                    @change="(checked) => handleGroupCheck(group, !!checked)"
                  >
                    本组全选
                  </ElCheckbox>
                </div>
                <ElCheckboxGroup
                  v-model="exportColumnKeys"
                  class="grid grid-cols-2 gap-2"
                >
                  <ElCheckbox
                    v-for="exportColumn in group.columns"
                    :key="exportColumn.key"
                    :label="exportColumn.key"
                  >
                    {{ exportColumn.label }}
                  </ElCheckbox>
                </ElCheckboxGroup>
              </div>
            </div>
          </ElScrollbar>
        </div>
      </div>

      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="exportDialogVisible = false">取消</ElButton>
          <ElButton
            type="primary"
            :loading="exportLoading"
            @click="handleExportConfirm"
          >
            导出
          </ElButton>
        </div>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped></style>
