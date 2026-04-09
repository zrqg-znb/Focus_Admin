import type { Column } from 'element-plus';

import type {
  FailureModeStatisticsChartDatum,
  FailureModeStatisticsSubsystemRow,
  FailureModeStatisticsSummary,
} from '#/api/failure_mode';
import type { ZqTableGridOptions } from '#/components/zq-table';

export type StatisticsTabKey = 'charts' | 'table';

export interface StatisticsPieCard {
  key: keyof FailureModeStatisticsSummary;
  title: string;
  subtitle: string;
}

export const statisticsTabs: Array<{ key: StatisticsTabKey; label: string }> = [
  { key: 'charts', label: '可视化图表' },
  { key: 'table', label: '数据表格' },
];

export const statisticsPieCards: StatisticsPieCard[] = [
  {
    key: 'interception_status',
    title: '产线拦截策略配置率',
    subtitle: '按故障模式条数统计已配置 / 待补充 / 无需配置。',
  },
  {
    key: 'huatuo_status',
    title: '华佗诊断配置完成率',
    subtitle: '根据必配开关与实际诊断关联共同判定三态。',
  },
  {
    key: 'handling_detection_status',
    title: '故障处理措施-检测',
    subtitle: '检测类措施的配置完成情况。',
  },
  {
    key: 'handling_prevention_status',
    title: '故障处理措施-预防',
    subtitle: '预防类措施的配置完成情况。',
  },
  {
    key: 'handling_self_heal_status',
    title: '故障处理措施-自愈',
    subtitle: '自愈类措施的配置完成情况。',
  },
  {
    key: 'observation_pipeline_log_status',
    title: '维测手段-流水日志',
    subtitle: '流水日志类维测手段的配置完成情况。',
  },
  {
    key: 'observation_dmd_status',
    title: '维测手段-DMD 点位',
    subtitle: 'DMD 点位类维测手段的配置完成情况。',
  },
  {
    key: 'observation_fmp_status',
    title: '维测手段-FMP 点位',
    subtitle: 'FMP 点位类维测手段的配置完成情况。',
  },
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

export function createEmptyStatisticsSummary(): FailureModeStatisticsSummary {
  const empty: FailureModeStatisticsChartDatum[] = [];
  return {
    subsystem_counts: empty,
    failure_mode_landing_status: empty,
    interception_status: empty,
    huatuo_status: empty,
    handling_detection_status: empty,
    handling_prevention_status: empty,
    handling_self_heal_status: empty,
    observation_pipeline_log_status: empty,
    observation_dmd_status: empty,
    observation_fmp_status: empty,
  };
}

export function useStatisticsSubsystemColumns(): ZqTableGridOptions<FailureModeStatisticsSubsystemRow>['columns'] {
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
    {
      key: 'handling_detection_relation_count',
      dataKey: 'handling_detection_relation_count',
      title: '业务版本检测措施数量',
      width: 170,
    },
    {
      key: 'handling_prevention_relation_count',
      dataKey: 'handling_prevention_relation_count',
      title: '业务版本预防措施数量',
      width: 170,
    },
    {
      key: 'handling_self_heal_relation_count',
      dataKey: 'handling_self_heal_relation_count',
      title: '业务版本自愈措施数量',
      width: 170,
    },
    {
      key: 'observation_pipeline_log_relation_count',
      dataKey: 'observation_pipeline_log_relation_count',
      title: '流水日志数量',
      width: 140,
    },
    {
      key: 'observation_dmd_relation_count',
      dataKey: 'observation_dmd_relation_count',
      title: 'DMD 点位数量',
      width: 140,
    },
    {
      key: 'observation_fmp_relation_count',
      dataKey: 'observation_fmp_relation_count',
      title: 'FMP 点位数量',
      width: 140,
    },
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
