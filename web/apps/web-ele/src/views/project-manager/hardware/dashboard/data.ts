import type { VbenFormSchema } from '#/adapter/form';
import type { ZqTableGridOptions } from '#/components/zq-table';

export interface PhaseBoardRow {
  cdc_platform_name?: string;
  domain: string;
  project_code?: string;
  project_id: string;
  project_name: string;
  scenario: 'cockpit' | 'vehicle';
  smart_screen_version_name?: string;
  stage_end?: string;
  stage_name: string;
  stage_start?: string;
  vehicle_hardware?: Array<{ board: string; bomid?: string; point: string }>;
  viu_platform_name?: string;
}

type PhaseBoardColumns = ZqTableGridOptions<PhaseBoardRow>['columns'];

function withCenterAlign(columns: Record<string, any>[]) {
  return columns.map((column) => {
    const nextColumn: Record<string, any> = {
      ...column,
      align: column.align ?? 'center',
      headerAlign: column.headerAlign ?? 'center',
    };
    if (Array.isArray(column.children)) {
      nextColumn.children = withCenterAlign(column.children);
    }
    return nextColumn;
  });
}

export function useVehicleSearchFormSchema(): VbenFormSchema[] {
  return [{ component: 'Input', fieldName: 'keyword', label: '项目/编码' }];
}

export function useCockpitSearchFormSchema(): VbenFormSchema[] {
  return [{ component: 'Input', fieldName: 'keyword', label: '项目/编码' }];
}

export function useVehicleColumns(): PhaseBoardColumns {
  const getPointValue = (row: PhaseBoardRow, point: string) => {
    const item = (row.vehicle_hardware || []).find(
      (hardware) => hardware.point.toLowerCase() === point.toLowerCase(),
    );
    if (!item) return '-';
    if (!item.bomid) return item.board || '-';
    return `${item.board || '-'} / BOMID: ${item.bomid}`;
  };

  return withCenterAlign([
    {
      key: 'project_name',
      dataKey: 'project_name',
      title: '项目',
      minWidth: 180,
    },
    { key: 'stage_name', dataKey: 'stage_name', title: '阶段', minWidth: 140 },
    {
      key: 'stage_start',
      dataKey: 'stage_start',
      title: '阶段起止',
      minWidth: 220,
      formatter: ({ row }: { row: PhaseBoardRow }) => {
        if (!row.stage_start && !row.stage_end) return '-';
        return `${row.stage_start || '-'} ~ ${row.stage_end || '-'}`;
      },
    },
    {
      key: 'viu_platform_name',
      dataKey: 'viu_platform_name',
      title: 'VIU 平台',
      minWidth: 160,
    },
    {
      key: 'viu0',
      dataKey: 'viu0',
      title: 'viu0',
      minWidth: 220,
      formatter: ({ row }: { row: PhaseBoardRow }) =>
        getPointValue(row, 'viu0'),
    },
    {
      key: 'viu1',
      dataKey: 'viu1',
      title: 'viu1',
      minWidth: 220,
      formatter: ({ row }: { row: PhaseBoardRow }) =>
        getPointValue(row, 'viu1'),
    },
    {
      key: 'viu2',
      dataKey: 'viu2',
      title: 'viu2',
      minWidth: 220,
      formatter: ({ row }: { row: PhaseBoardRow }) =>
        getPointValue(row, 'viu2'),
    },
    {
      key: 'viu3',
      dataKey: 'viu3',
      title: 'viu3',
      minWidth: 220,
      formatter: ({ row }: { row: PhaseBoardRow }) =>
        getPointValue(row, 'viu3'),
    },
  ]) as PhaseBoardColumns;
}

export function useCockpitColumns(): PhaseBoardColumns {
  return withCenterAlign([
    {
      key: 'project_name',
      dataKey: 'project_name',
      title: '项目',
      minWidth: 180,
    },
    {
      key: 'cdc_platform_name',
      dataKey: 'cdc_platform_name',
      title: 'CDC 平台版本',
      minWidth: 220,
      formatter: ({ row }: { row: PhaseBoardRow }) =>
        row.cdc_platform_name || '-',
    },
    {
      key: 'smart_screen_version_name',
      dataKey: 'smart_screen_version_name',
      title: '智慧屏版本',
      minWidth: 220,
      formatter: ({ row }: { row: PhaseBoardRow }) =>
        row.smart_screen_version_name || '-',
    },
  ]) as PhaseBoardColumns;
}
