import type { ReleasePlanItem } from '#/api/project-manager/release-plan';
import type { ZqTableGridOptions } from '#/components/zq-table';

type ReleasePlanColumns = ZqTableGridOptions<ReleasePlanItem>['columns'];

export const VERSION_TYPE_OPTIONS = [
  { label: 'Alpha', value: 'Alpha' },
  { label: 'Beta', value: 'Beta' },
  { label: 'RC', value: 'RC' },
  { label: 'Release', value: 'Release' },
  { label: 'Hotfix', value: 'Hotfix' },
];

export function useReleasePlanColumns(): ReleasePlanColumns {
  return [
    {
      key: 'project_name',
      dataKey: 'project_name',
      title: '项目/编码',
      minWidth: 220,
      slots: { header: 'header-project_name' },
    },
    {
      key: 'branch_name',
      dataKey: 'branch_name',
      title: '分支',
      minWidth: 170,
      slots: { header: 'header-branch_name' },
    },
    {
      key: 'release_date',
      dataKey: 'release_date',
      title: '发布日期',
      width: 118,
      slots: { header: 'header-release_date' },
    },
    {
      key: 'version_type_label',
      dataKey: 'version_type_label',
      title: '版本类型',
      width: 110,
      slots: { header: 'header-version_type' },
    },
    {
      key: 'platform_name',
      dataKey: 'platform_name',
      title: '发布平台',
      minWidth: 150,
      slots: { header: 'header-platform_name' },
    },
    {
      key: 'release_vehicles',
      dataKey: 'release_vehicles',
      title: '发布车型',
      minWidth: 220,
      slots: { header: 'header-release_vehicles' },
    },
    {
      key: 'manager_names',
      dataKey: 'manager_names',
      title: '项目经理',
      width: 130,
    },
  ].map((column) => ({
    align: 'center',
    headerAlign: 'center',
    showOverflowTooltip: true,
    ...column,
  })) as ReleasePlanColumns;
}
