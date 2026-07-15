import type { SkillRun } from '#/api/tools/agent-skills';
import type { ZqTableGridOptions } from '#/components/zq-table';

export function useRunColumns(): ZqTableGridOptions<SkillRun>['columns'] {
  return [
    { key: 'skill_name', dataKey: 'skill_name', title: '技能', minWidth: 180 },
    {
      key: 'provider_name',
      dataKey: 'provider_name',
      title: '模型档案',
      width: 160,
    },
    {
      key: 'provider_model',
      dataKey: 'provider_model',
      title: '模型',
      width: 160,
    },
    { key: 'status', dataKey: 'status', title: '状态', width: 110 },
    {
      key: 'baseline_score',
      dataKey: 'baseline_score',
      title: '基线',
      width: 100,
    },
    { key: 'final_score', dataKey: 'final_score', title: '最终', width: 100 },
    {
      key: 'sys_creator_name',
      dataKey: 'sys_creator_name',
      title: '创建人',
      width: 110,
    },
    {
      key: 'sys_create_datetime',
      dataKey: 'sys_create_datetime',
      title: '创建时间',
      width: 180,
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 100,
      fixed: 'right',
    },
  ].map((item) => ({ align: 'center', headerAlign: 'center', ...item }));
}
