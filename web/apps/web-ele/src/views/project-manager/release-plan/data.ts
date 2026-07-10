import type { ReleasePlanProjectGroup } from '#/api/project-manager/release-plan';
import type { ZqTableGridOptions } from '#/components/zq-table';

type ReleasePlanColumns = ZqTableGridOptions<ReleasePlanProjectGroup>['columns'];

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
      key: 'expand',
      type: 'expand',
      width: 42,
      fixed: 'left',
      slots: { default: 'expand_content' },
    },
    {
      key: 'project_name',
      dataKey: 'project_name',
      title: '项目/编码',
      fixed: 'left',
      minWidth: 250,
      slots: { header: 'header-project_name' },
    },
    {
      key: 'manager_names',
      dataKey: 'manager_names',
      title: '项目经理',
      width: 116,
    },
    {
      key: 'branch_count',
      dataKey: 'branch_count',
      title: '分支数',
      width: 86,
      slots: { header: 'header-branch_names' },
    },
    {
      key: 'plan_count',
      dataKey: 'plan_count',
      title: '计划数',
      width: 82,
    },
    {
      key: 'next_release_date',
      dataKey: 'next_release_date',
      title: '最近发布',
      width: 120,
      slots: { header: 'header-next_release_date' },
    },
    {
      key: 'version_types',
      dataKey: 'version_types',
      title: '版本类型',
      minWidth: 160,
      slots: { header: 'header-version_type' },
    },
    {
      key: 'platform_names',
      dataKey: 'platform_names',
      title: '发布平台',
      minWidth: 170,
      slots: { header: 'header-platform_name' },
    },
    {
      key: 'release_vehicles',
      dataKey: 'release_vehicles',
      title: '车型摘要',
      minWidth: 210,
      slots: { header: 'header-release_vehicles' },
    },
  ].map((column) => ({
    align: 'center',
    headerAlign: 'center',
    showOverflowTooltip: true,
    ...column,
  })) as ReleasePlanColumns;
}
