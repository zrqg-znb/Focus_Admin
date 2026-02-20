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
  vehicle_hardware?: Array<{ point: string; board: string; bomid?: string }>;
  cdc_platform_name?: string;
  smart_screen_version_name?: string;
}

export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    { component: 'Input', fieldName: 'keyword', label: '项目/编码' },
    { component: 'Input', fieldName: 'domain', label: '领域' },
    { component: 'Input', fieldName: 'stage', label: '阶段' },
  ];
}

export function useColumns(): VxeTableGridOptions<PhaseBoardRow>['columns'] {
  return [
    { field: 'project_name', title: '项目', minWidth: 180 },
    { field: 'domain', title: '领域', minWidth: 120 },
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
    {
      field: 'scenario',
      title: '配套类型',
      minWidth: 120,
      formatter: ({ cellValue }) =>
        cellValue === 'cockpit' ? '座舱配套' : '车控典配',
    },
    {
      field: 'combo',
      title: '配套详情',
      minWidth: 320,
      slots: { default: 'config_combo' },
    },
  ];
}
