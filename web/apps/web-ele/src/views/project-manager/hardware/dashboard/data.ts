import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';

export interface PhaseBoardRow {
  project_id: string;
  project_name: string;
  project_code?: string;
  domain: string;
  stage_name: string;
  stage_start?: string;
  stage_end?: string;
  scenario: 'cockpit' | 'vehicle';
  viu_platform_name?: string;
  vehicle_hardware?: Array<{ board: string; bomid?: string; point: string }>;
  cdc_platform_name?: string;
  smart_screen_version_name?: string;
}

export function useVehicleSearchFormSchema(): VbenFormSchema[] {
  return [{ component: 'Input', fieldName: 'keyword', label: '项目/编码' }];
}

export function useCockpitSearchFormSchema(): VbenFormSchema[] {
  return [{ component: 'Input', fieldName: 'keyword', label: '项目/编码' }];
}

export function useVehicleColumns(): VxeTableGridOptions<PhaseBoardRow>['columns'] {
  const getPointValue = (row: PhaseBoardRow, point: string) => {
    const item = (row.vehicle_hardware || []).find(
      (hardware) => hardware.point.toLowerCase() === point.toLowerCase(),
    );
    if (!item) return '-';
    if (!item.bomid) return item.board || '-';
    return `${item.board || '-'} / BOMID: ${item.bomid}`;
  };

  return [
    { field: 'project_name', title: '项目', minWidth: 180 },
    { field: 'stage_name', title: '阶段', minWidth: 140 },
    {
      field: 'stage_start',
      title: '阶段起止',
      minWidth: 220,
      formatter: ({ row }) => {
        if (!row.stage_start && !row.stage_end) return '-';
        return `${row.stage_start || '-'} ~ ${row.stage_end || '-'}`;
      },
    },
    // {
    //   field: 'scenario',
    //   title: '配套类型',
    //   minWidth: 120,
    //   formatter: ({ cellValue }) =>
    //     cellValue === 'cockpit' ? '座舱配套' : '车控典配',
    // },
    { field: 'viu_platform_name', title: 'VIU 平台', minWidth: 160 },
    {
      field: 'viu0',
      title: 'viu0',
      minWidth: 220,
      formatter: ({ row }) => getPointValue(row, 'viu0'),
    },
    {
      field: 'viu1',
      title: 'viu1',
      minWidth: 220,
      formatter: ({ row }) => getPointValue(row, 'viu1'),
    },
    {
      field: 'viu2',
      title: 'viu2',
      minWidth: 220,
      formatter: ({ row }) => getPointValue(row, 'viu2'),
    },
    {
      field: 'viu3',
      title: 'viu3',
      minWidth: 220,
      formatter: ({ row }) => getPointValue(row, 'viu3'),
    },
  ];
}

export function useCockpitColumns(): VxeTableGridOptions<PhaseBoardRow>['columns'] {
  return [
    { field: 'project_name', title: '项目', minWidth: 180 },
    {
      field: 'cdc_platform_name',
      title: 'CDC 平台版本',
      minWidth: 220,
      formatter: ({ row }) => row.cdc_platform_name || '-',
    },
    {
      field: 'smart_screen_version_name',
      title: '智慧屏版本',
      minWidth: 220,
      formatter: ({ row }) => row.smart_screen_version_name || '-',
    },
  ];
}
