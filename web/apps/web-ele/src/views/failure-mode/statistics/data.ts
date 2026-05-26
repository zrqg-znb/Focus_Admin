import type { Column } from 'element-plus';

import type {
  DictOption,
  FailureModeStatisticsChartDatum,
  FailureModeStatisticsSubsystemRow,
  FailureModeStatisticsSummary,
} from '#/api/failure_mode';
import type { ZqTableGridOptions } from '#/components/zq-table';

export type StatisticsTabKey = 'charts' | 'table';

export interface StatisticsPieCard {
  key: string;
  subtitle: string;
  title: string;
  resolveData: (
    summary: FailureModeStatisticsSummary,
  ) => FailureModeStatisticsChartDatum[];
}

export const statisticsTabs: Array<{ key: StatisticsTabKey; label: string }> = [
  { key: 'charts', label: '可视化图表' },
  { key: 'table', label: '数据表格' },
];

function withCenter<T extends Record<string, any>>(
  columns: Column<T>[],
): ZqTableGridOptions<T>['columns'] {
  return columns.map((column) => ({
    align: 'center',
    headerAlign: 'center',
    ...column,
  }));
}

function appendUniqueValue(
  target: string[],
  seen: Set<string>,
  value: unknown,
) {
  const text = String(value || '').trim();
  if (!text || seen.has(text)) {
    return;
  }
  seen.add(text);
  target.push(text);
}

export function resolveOrderedCategoryValues(
  dictOptions: DictOption[] = [],
  extraValues: string[] = [],
) {
  const result: string[] = [];
  const seen = new Set<string>();
  dictOptions.forEach((item) => appendUniqueValue(result, seen, item.value));
  extraValues.forEach((item) => appendUniqueValue(result, seen, item));
  return result;
}

export function buildStatisticsPieCards({
  handlingCategories,
  observationTypes,
}: {
  handlingCategories: string[];
  observationTypes: string[];
}): StatisticsPieCard[] {
  return [
    {
      key: 'interception_status',
      title: '产线拦截策略配置率',
      subtitle: '按故障模式条数统计已配置 / 待补充 / 无需配置。',
      resolveData: (summary) => summary.interception_status || [],
    },
    {
      key: 'huatuo_status',
      title: '华佗诊断配置完成率',
      subtitle: '根据必配开关与实际诊断关联共同判定三态。',
      resolveData: (summary) => summary.huatuo_status || [],
    },
    ...handlingCategories.map((category) => ({
      key: `handling-${category}`,
      title: `故障处理措施-${category}`,
      subtitle: `${category}类措施的配置完成情况。`,
      resolveData: (summary: FailureModeStatisticsSummary) =>
        summary.handling_status_map?.[category] || [],
    })),
    ...observationTypes.map((monitorType) => ({
      key: `observation-${monitorType}`,
      title: `维测手段-${monitorType}`,
      subtitle: `${monitorType}类维测手段的配置完成情况。`,
      resolveData: (summary: FailureModeStatisticsSummary) =>
        summary.observation_status_map?.[monitorType] || [],
    })),
  ];
}

export function createEmptyStatisticsSummary(): FailureModeStatisticsSummary {
  const empty: FailureModeStatisticsChartDatum[] = [];
  return {
    subsystem_counts: empty,
    failure_mode_landing_status: empty,
    interception_status: empty,
    huatuo_status: empty,
    handling_status_map: {},
    observation_status_map: {},
  };
}

function buildCountColumn(
  kind: 'handling' | 'observation',
  category: string,
): Column<FailureModeStatisticsSubsystemRow> {
  const titlePrefix = kind === 'handling' ? '措施' : '维测';
  const dataKey = `${kind}_${category}`;
  return {
    cellRenderer: ({
      rowData,
    }: {
      rowData: FailureModeStatisticsSubsystemRow;
    }) =>
      kind === 'handling'
        ? Number(rowData.handling_relation_counts?.[category] || 0)
        : Number(rowData.observation_relation_counts?.[category] || 0),
    dataKey,
    key: dataKey,
    title: `${titlePrefix}-${category}`,
    width: Math.max(140, category.length * 18 + 72),
  };
}

export function useStatisticsSubsystemColumns({
  handlingCategories,
  observationTypes,
}: {
  handlingCategories: string[];
  observationTypes: string[];
}): ZqTableGridOptions<FailureModeStatisticsSubsystemRow>['columns'] {
  return withCenter<FailureModeStatisticsSubsystemRow>([
    { key: 'subsystem', dataKey: 'subsystem', title: '子系统', width: 180 },
    {
      key: 'failure_mode_count',
      dataKey: 'failure_mode_count',
      title: '故障模式数量',
      width: 140,
    },
    {
      key: 'interception_relation_count',
      dataKey: 'interception_relation_count',
      title: '产线拦截策略数量',
      width: 150,
    },
    ...handlingCategories.map((category) =>
      buildCountColumn('handling', category),
    ),
    ...observationTypes.map((monitorType) =>
      buildCountColumn('observation', monitorType),
    ),
    {
      key: 'huatuo_relation_count',
      dataKey: 'huatuo_relation_count',
      title: '华佗诊断数量',
      width: 140,
    },
    {
      key: 'pending_failure_mode_count',
      dataKey: 'pending_failure_mode_count',
      title: '待补充故障数',
      width: 150,
    },
    {
      key: 'status_light',
      dataKey: 'status_light',
      title: '完成率状态',
      width: 180,
    },
  ]);
}

export function formatPercent(value?: number) {
  const safe = Number(value || 0);
  return `${safe.toFixed(2)}%`;
}

export function resolveStatusLightMeta(statusLight: string) {
  switch (statusLight) {
    case 'red': {
      return {
        color: '#dc2626',
        label: '红灯',
      };
    }
    case 'yellow': {
      return {
        color: '#d97706',
        label: '黄灯',
      };
    }
    default: {
      return {
        color: '#16a34a',
        label: '绿灯',
      };
    }
  }
}
