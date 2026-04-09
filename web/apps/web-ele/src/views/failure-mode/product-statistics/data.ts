import type {
  FailureModeProductStatisticsSubsystemRow,
  FailureModeProductStatisticsSummary,
} from '#/api/failure_mode';
import type { ZqTableGridOptions } from '#/components/zq-table';

import {
  createEmptyStatisticsSummary,
  formatPercent,
  resolveStatusLightMeta,
} from '../statistics/data';

export type ProductStatisticsTabKey = 'charts' | 'table';

export interface ProductStatisticsPieCard {
  key: keyof FailureModeProductStatisticsSummary;
  title: string;
  subtitle: string;
}

export const productStatisticsTabs: Array<{
  key: ProductStatisticsTabKey;
  label: string;
}> = [
  { key: 'charts', label: '可视化图表' },
  { key: 'table', label: '数据表格' },
];

export const productStatisticsPieCards: ProductStatisticsPieCard[] = [
  {
    key: 'failure_mode_landing_status',
    title: '故障模式落地情况',
    subtitle: '按当前产品基线中的故障模式本身是否已落地统计。',
  },
  {
    key: 'interception_status',
    title: '产线拦截策略落地情况',
    subtitle: '必配时要求当前绑定的全部拦截策略都已落地。',
  },
  {
    key: 'huatuo_status',
    title: '华佗诊断落地情况',
    subtitle: '必配时要求当前绑定的全部诊断方案都已落地。',
  },
  {
    key: 'handling_detection_status',
    title: '故障处理措施-检测',
    subtitle: '检测类措施按当前产品子系统显式落地状态汇总。',
  },
  {
    key: 'handling_prevention_status',
    title: '故障处理措施-预防',
    subtitle: '预防类措施按当前产品子系统显式落地状态汇总。',
  },
  {
    key: 'handling_self_heal_status',
    title: '故障处理措施-自愈',
    subtitle: '自愈类措施按当前产品子系统显式落地状态汇总。',
  },
  {
    key: 'observation_pipeline_log_status',
    title: '维测手段-流水日志',
    subtitle: '流水日志类维测手段按显式落地状态汇总。',
  },
  {
    key: 'observation_dmd_status',
    title: '维测手段-DMD 点位',
    subtitle: 'DMD 点位类维测手段按显式落地状态汇总。',
  },
  {
    key: 'observation_fmp_status',
    title: '维测手段-FMP 点位',
    subtitle: 'FMP 点位类维测手段按显式落地状态汇总。',
  },
];

export function createEmptyProductStatisticsSummary(): FailureModeProductStatisticsSummary {
  return createEmptyStatisticsSummary();
}

export function useProductStatisticsSubsystemColumns(): ZqTableGridOptions<FailureModeProductStatisticsSubsystemRow>['columns'] {
  return [
    {
      align: 'center',
      dataKey: 'subsystem',
      headerAlign: 'center',
      key: 'subsystem',
      title: '子系统',
      width: 180,
    },
    {
      align: 'center',
      dataKey: 'baseline_failure_mode_count',
      headerAlign: 'center',
      key: 'baseline_failure_mode_count',
      title: '基线故障模式数',
      width: 170,
    },
    {
      align: 'center',
      dataKey: 'landed_failure_mode_count',
      headerAlign: 'center',
      key: 'landed_failure_mode_count',
      title: '已落地故障数',
      width: 160,
    },
    {
      align: 'center',
      dataKey: 'pending_failure_mode_count',
      headerAlign: 'center',
      key: 'pending_failure_mode_count',
      title: '待开展故障数',
      width: 160,
    },
    {
      align: 'center',
      dataKey: 'pending_rate',
      headerAlign: 'center',
      key: 'pending_rate',
      title: '待开展率',
      width: 140,
    },
    {
      align: 'center',
      dataKey: 'status_light',
      headerAlign: 'center',
      key: 'status_light',
      title: '状态灯',
      width: 180,
    },
  ];
}

export { formatPercent, resolveStatusLightMeta };
