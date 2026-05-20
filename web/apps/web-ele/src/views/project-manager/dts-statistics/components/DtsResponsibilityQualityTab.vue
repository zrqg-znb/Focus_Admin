<script lang="ts" setup>
import type {
  DtsResponsibilityQualityMonthOption,
  DtsResponsibilityQualityMonthReport,
  DtsResponsibilityQualityPlGroup,
  DtsResponsibilityQualityReport,
} from '#/api/project-manager/dts-statistics';

import { computed, ref, watch } from 'vue';

import {
  ElCard,
  ElEmpty,
  ElMessage,
  ElOption,
  ElSegmented,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import { getDtsResponsibilityQualityReport } from '#/api/project-manager/dts-statistics';

defineOptions({ name: 'DtsResponsibilityQualityTab' });

const props = withDefaults(
  defineProps<{
    productId?: string;
    productLabel?: string;
  }>(),
  {
    productId: '250539396',
    productLabel: '',
  },
);

const PRODUCT_OPTIONS = [
  { label: '座舱', value: '250539396' },
  { label: '车控', value: '250539397' },
] as const;

type QualityGridRow = Record<string, number | string>;

const report = ref<DtsResponsibilityQualityReport | null>(null);
const activeProductId = ref(resolveInitialProductId(props.productId));
const selectedMonth = ref(getCurrentMonthKey());
const confirmedMonth = ref('');
const loading = ref(false);
const requestSerial = ref(0);

const monthOptions = computed<DtsResponsibilityQualityMonthOption[]>(
  () => report.value?.month_options || [],
);
const plGroups = computed<DtsResponsibilityQualityPlGroup[]>(
  () => report.value?.pl_groups || [],
);
const visibleMonthReport = computed<DtsResponsibilityQualityMonthReport | null>(
  () => report.value?.month_reports?.[0] || null,
);
const scoreItemMap = computed(() => {
  const items = visibleMonthReport.value?.score_items || [];
  return new Map(items.map((item) => [item.label, item] as const));
});
const visibleRows = computed<QualityGridRow[]>(() =>
  flattenRows(visibleMonthReport.value, plGroups.value),
);
const sectionSpanMap = computed(() => buildSectionSpanMap(visibleRows.value));

function resolveInitialProductId(productId?: string) {
  const value = normalizeMonth(productId);
  return (
    PRODUCT_OPTIONS.find((item) => item.value === value)?.value ||
    PRODUCT_OPTIONS[0].value
  );
}

function getCurrentMonthKey() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  return `${year}-${month}`;
}

function normalizeMonth(value: unknown) {
  return String(value || '').trim();
}

function flattenRows(
  monthReport: DtsResponsibilityQualityMonthReport | null,
  groups: DtsResponsibilityQualityPlGroup[],
): QualityGridRow[] {
  if (!monthReport) {
    return [];
  }

  return monthReport.rows.map((row) => {
    const next: QualityGridRow = {
      section: row.section,
      label: row.label,
      formula: row.formula,
    };

    groups.forEach((_, index) => {
      const cell = row.cells[index];
      next[`pl-group-${index}-current`] = Number(cell?.current_value || 0);
      next[`pl-group-${index}-cumulative`] = Number(
        cell?.cumulative_value || 0,
      );
      next[`pl-group-${index}-deduction`] = Number(
        cell?.cumulative_deduction || 0,
      );
    });

    return next;
  });
}

function buildSectionSpanMap(rows: QualityGridRow[]) {
  const map = new Map<number, number>();
  let index = 0;
  while (index < rows.length) {
    const section = String(rows[index]?.section || '');
    let end = index + 1;
    while (end < rows.length && rows[end]?.section === section) {
      end += 1;
    }
    map.set(index, end - index);
    for (let i = index + 1; i < end; i += 1) {
      map.set(i, 0);
    }
    index = end;
  }
  return map;
}

function spanMethod({
  columnIndex,
  rowIndex,
}: {
  columnIndex: number;
  rowIndex: number;
}) {
  if (columnIndex !== 0) {
    return { rowspan: 1, colspan: 1 };
  }
  const rowspan = sectionSpanMap.value.get(rowIndex) || 0;
  if (rowspan <= 0) {
    return { rowspan: 0, colspan: 0 };
  }
  return { rowspan, colspan: 1 };
}

function cellClassName({
  row,
  column,
}: {
  column: { prop?: string; property?: string };
  row: QualityGridRow;
}) {
  const property = String(column.property || column.prop || '');
  if (property.endsWith('-deduction') && Number(row[property] || 0) !== 0) {
    return 'dts-quality-grid__deduction-cell';
  }
  return '';
}

function getGroupScore(label: string) {
  return scoreItemMap.value.get(label)?.score ?? null;
}

function formatGroupScore(score: null | number) {
  return score === null ? '--' : score.toFixed(1);
}

async function loadReport(month: string) {
  const requestedMonth = normalizeMonth(month);
  const serial = requestSerial.value + 1;
  requestSerial.value = serial;
  loading.value = true;

  const fallbackMonth =
    confirmedMonth.value || requestedMonth || getCurrentMonthKey();

  try {
    const response = await getDtsResponsibilityQualityReport({
      productId: activeProductId.value,
      month: requestedMonth,
    });

    if (serial !== requestSerial.value) {
      return;
    }

    report.value = response;
    const resolvedMonth =
      response.month_reports?.[0]?.month ||
      requestedMonth ||
      response.month_options?.[0]?.value ||
      '';
    selectedMonth.value = resolvedMonth;
    confirmedMonth.value = resolvedMonth;
  } catch (error) {
    if (serial !== requestSerial.value) {
      return;
    }

    selectedMonth.value = fallbackMonth;
    ElMessage.error('责任田领域质量报表加载失败');
    console.error(error);
  } finally {
    if (serial === requestSerial.value) {
      loading.value = false;
    }
  }
}

function handleMonthChange(value: number | string | undefined) {
  void loadReport(normalizeMonth(value));
}

watch(
  activeProductId,
  () => {
    report.value = null;
    confirmedMonth.value = '';
    void loadReport(selectedMonth.value);
  },
  { immediate: true },
);
</script>

<template>
  <div class="dts-quality-tab" v-loading="loading">
    <ElCard shadow="never" class="dts-quality-table-card">
      <template #header>
        <div class="dts-quality-table-title">
          <div>
            <div class="dts-quality-table-title__title">责任田领域质量</div>
          </div>

          <div class="dts-quality-table-title__controls">
            <div class="dts-quality-table-title__field">
              <span class="dts-quality-table-title__label">产品</span>
              <ElSegmented
                v-model="activeProductId"
                class="dts-quality-table-title__segmented"
                :options="PRODUCT_OPTIONS"
                size="small"
              />
            </div>
            <div class="dts-quality-table-title__field">
              <span class="dts-quality-table-title__label">月份</span>
              <ElSelect
                v-model="selectedMonth"
                size="small"
                class="dts-quality-table-title__select"
                placeholder="选择月份"
                :disabled="monthOptions.length === 0"
                @change="handleMonthChange"
              >
                <ElOption
                  v-for="item in monthOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </ElSelect>
            </div>
          </div>
        </div>
      </template>

      <div class="dts-quality-table-shell">
        <ElTable
          v-if="visibleRows.length > 0"
          :key="visibleMonthReport?.month || selectedMonth"
          class="dts-quality-grid"
          :data="visibleRows"
          border
          :cell-class-name="cellClassName"
          stripe
          table-layout="fixed"
          :span-method="spanMethod"
        >
          <ElTableColumn
            prop="section"
            label="要素"
            width="128"
            fixed="left"
            align="center"
            header-align="center"
          />
          <ElTableColumn
            prop="label"
            label="指标名称"
            min-width="220"
            fixed="left"
            align="left"
            header-align="center"
            show-overflow-tooltip
          />
          <ElTableColumn
            prop="formula"
            label="扣分算法"
            width="120"
            fixed="left"
            align="center"
            header-align="center"
            show-overflow-tooltip
          />
          <ElTableColumn
            v-for="(group, index) in plGroups"
            :key="group.id || index"
            align="center"
            header-align="center"
            :min-width="300"
          >
            <template #header>
              <div class="dts-quality-group-header">
                <div class="dts-quality-group-header__title">
                  {{ group.label }}
                </div>
                <div class="dts-quality-group-header__meta">
                  <span>{{ group.owner_name || '未填写' }}</span>
                  <ElTag type="success" effect="plain" size="small">
                    得分 {{ formatGroupScore(getGroupScore(group.label)) }}
                  </ElTag>
                </div>
              </div>
            </template>
            <ElTableColumn
              :prop="`pl-group-${index}-current`"
              label="当月值"
              width="88"
              align="center"
              header-align="center"
            />
            <ElTableColumn
              :prop="`pl-group-${index}-cumulative`"
              label="累计值"
              width="88"
              align="center"
              header-align="center"
            />
            <ElTableColumn
              :prop="`pl-group-${index}-deduction`"
              label="累计扣分"
              width="96"
              align="center"
              header-align="center"
            />
          </ElTableColumn>
        </ElTable>

        <ElEmpty
          v-else
          description="当前月份没有可展示的责任田领域质量数据"
          :image-size="120"
        />
      </div>
    </ElCard>
  </div>
</template>

<style scoped>
.dts-quality-tab {
  min-width: 0;
}

.dts-quality-table-card {
  border: 1px solid #dbe5f1;
  border-radius: 20px;
  box-shadow: 0 14px 32px rgb(15 23 42 / 4%);
}

.dts-quality-table-card :deep(.el-card__header) {
  padding: 18px 20px 14px;
}

.dts-quality-table-card :deep(.el-card__body) {
  padding: 0 20px 20px;
}

.dts-quality-table-title {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 16px;
  align-items: flex-end;
  justify-content: space-between;
  width: 100%;
}

.dts-quality-table-title__title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.dts-quality-table-title__controls {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.dts-quality-table-title__field {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dts-quality-table-title__label {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
}

.dts-quality-table-title__select {
  width: 160px;
}

.dts-quality-table-title__segmented {
  min-width: 156px;
}

.dts-quality-table-shell {
  min-width: 0;
  overflow-x: auto;
  overflow-y: visible;
}

.dts-quality-grid {
  min-width: 0;
}

.dts-quality-group-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  padding: 2px 0;
}

.dts-quality-group-header__title {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.dts-quality-group-header__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #64748b;
}

.dts-quality-grid :deep(.el-table__header .cell) {
  white-space: pre-line;
  line-height: 1.35;
}

.dts-quality-grid :deep(.el-table__body .cell) {
  word-break: break-word;
  line-height: 1.45;
}

.dts-quality-grid :deep(.el-table__header th.el-table__cell) {
  background: linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
}

.dts-quality-grid :deep(.el-table__row td.el-table__cell) {
  vertical-align: middle;
}

.dts-quality-grid :deep(.el-table__row td.el-table__cell:first-child) {
  font-weight: 700;
  color: #0f172a;
}

.dts-quality-grid :deep(.el-table__row td.el-table__cell:nth-child(2)) {
  color: #1e293b;
}

.dts-quality-grid :deep(.el-table__row td.el-table__cell:nth-child(3)) {
  color: #475569;
}

.dts-quality-grid :deep(.el-table__row td.el-table__cell:nth-child(n + 4)) {
  font-variant-numeric: tabular-nums;
}

.dts-quality-grid :deep(.dts-quality-grid__deduction-cell) {
  color: #dc2626;
  font-weight: 700;
}

@media (max-width: 1200px) {
  .dts-quality-table-card :deep(.el-card__header) {
    padding: 16px 16px 12px;
  }

  .dts-quality-table-card :deep(.el-card__body) {
    padding: 0 16px 16px;
  }

  .dts-quality-table-title {
    align-items: flex-start;
  }

  .dts-quality-table-title__segmented {
    min-width: 140px;
  }

  .dts-quality-table-title__select {
    width: 140px;
  }
}
</style>
