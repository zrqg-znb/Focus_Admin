import type {
  FailureModeProductStatisticsSubsystemRow,
  FailureModeProductStatisticsSummary,
} from '#/api/failure_mode';
import type { ZqTableGridOptions } from '#/components/zq-table';

import {
  createEmptyStatisticsSummary,
  formatPercent,
  resolveStatusLightMeta,
  statisticsPieCards,
  statisticsTabs,
  useStatisticsSubsystemColumns,
} from '../statistics/data';

export type ProductStatisticsTabKey = 'charts' | 'table';

export const productStatisticsTabs = statisticsTabs;
export const productStatisticsPieCards = statisticsPieCards;

export function createEmptyProductStatisticsSummary(): FailureModeProductStatisticsSummary {
  return createEmptyStatisticsSummary();
}

export function useProductStatisticsSubsystemColumns(): ZqTableGridOptions<FailureModeProductStatisticsSubsystemRow>['columns'] {
  return useStatisticsSubsystemColumns() as ZqTableGridOptions<FailureModeProductStatisticsSubsystemRow>['columns'];
}

export { formatPercent, resolveStatusLightMeta };
