import type { VbenFormSchema } from '#/adapter/form';
import type { PlGroup } from '#/api/core/pl';
import type { DtsMergedDefect } from '#/api/project-manager/dts-statistics';
import type { ProjectOut } from '#/api/project-manager/project';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { getAllPlApi } from '#/api/core/pl';
import { listProjectsApi } from '#/api/project-manager/project';

type Columns = ZqTableGridOptions<DtsMergedDefect>['columns'];

const YES_NO_OPTIONS = [
  { label: '是', value: '是' },
  { label: '否', value: '否' },
];

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

function pad2(value: number) {
  return String(value).padStart(2, '0');
}

function formatDateTime(date: Date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(
    date.getDate(),
  )} ${pad2(date.getHours())}:${pad2(date.getMinutes())}:${pad2(
    date.getSeconds(),
  )}`;
}

function getTodayStartEnd() {
  const now = new Date();
  const start = new Date(now);
  start.setHours(0, 0, 0, 0);
  const end = new Date(now);
  end.setHours(23, 59, 59, 0);
  return {
    start_time: formatDateTime(start),
    end_time: formatDateTime(end),
  };
}

export function useSearchFormSchema(): VbenFormSchema[] {
  const today = getTodayStartEnd();
  return [
    {
      component: 'ApiSelect',
      fieldName: 'project_ids',
      label: '项目',
      componentProps: {
        api: async () => {
          const res = await listProjectsApi({
            enable_dts: true,
            pageSize: 1000,
          });
          return res.items || [];
        },
        labelField: 'name',
        valueField: 'id',
        multiple: true,
        showSearch: true,
        optionFilterProp: 'label',
        placeholder: '请选择项目（可多选）',
      },
    },
    {
      component: 'Select',
      fieldName: 'column_type',
      label: '单据类型',
      defaultValue: 'openDefects',
      componentProps: {
        clearable: false,
        options: [
          { label: '未关闭', value: 'openDefects' },
          { label: '已关闭', value: 'closeDefects' },
          { label: '全部', value: 'totalDefects' },
        ],
      },
    },
    {
      component: 'DatePicker',
      fieldName: 'start_time',
      label: '开始时间',
      defaultValue: today.start_time,
      componentProps: {
        type: 'datetime',
        valueFormat: 'YYYY-MM-DD HH:mm:ss',
        format: 'YYYY-MM-DD HH:mm:ss',
        placeholder: '选择开始时间',
      },
    },
    {
      component: 'DatePicker',
      fieldName: 'end_time',
      label: '结束时间',
      defaultValue: today.end_time,
      componentProps: {
        type: 'datetime',
        valueFormat: 'YYYY-MM-DD HH:mm:ss',
        format: 'YYYY-MM-DD HH:mm:ss',
        placeholder: '选择结束时间',
      },
    },
  ];
}

export function useColumns(): Columns {
  return withCenterAlign([
    {
      key: 'defectNo',
      dataKey: 'defectNo',
      title: 'DTS单号',
      width: 170,
      fixed: true,
    },
    {
      key: 'brief',
      dataKey: 'brief',
      title: '描述',
      minWidth: 280,
      fixed: true,
      showOverflowTooltip: true,
    },
    { key: 'severity', dataKey: 'severity', title: '级别', width: 90 },
    {
      key: 'currentStatus',
      dataKey: 'currentStatus',
      title: '状态',
      width: 140,
    },
    {
      key: 'currentHandler',
      dataKey: 'currentHandler',
      title: '处理人',
      width: 140,
    },
    {
      key: 'submitTime',
      dataKey: 'submitTime',
      title: '提交时间',
      width: 170,
    },
    {
      key: 'project_names',
      dataKey: 'project_names',
      title: '命中项目',
      minWidth: 220,
    },
    {
      key: 'team_names',
      dataKey: 'team_names',
      title: '命中团队',
      minWidth: 220,
    },
    {
      key: 'qa_category',
      dataKey: 'qa_category',
      title: 'QA大类',
      width: 140,
    },
    {
      key: 'pl_group_name',
      dataKey: 'pl_group_name',
      title: '责任PL组',
      width: 160,
    },
    {
      key: 'dev_owner_name',
      dataKey: 'dev_owner_name',
      title: '开发责任人',
      width: 140,
    },
    {
      key: 'test_owner_name',
      dataKey: 'test_owner_name',
      title: '测试责任人',
      width: 140,
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 190,
      fixed: 'right',
    },
  ]) as Columns;
}

async function fetchPlGroups(): Promise<PlGroup[]> {
  const items = await getAllPlApi();
  return (items || []).filter((item) => item.status);
}

export function useQaFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'qa_category',
      label: '问题大类',
      componentProps: {
        placeholder: '请输入问题大类（后续可接字典）',
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'pl_group_id',
      label: '责任PL组',
      componentProps: {
        api: fetchPlGroups,
        labelField: 'name',
        valueField: 'id',
        showSearch: true,
        optionFilterProp: 'label',
        placeholder: '请选择责任PL组',
      },
    },
    {
      component: 'Select',
      fieldName: 'is_downstream',
      label: '是否下游问题',
      componentProps: {
        clearable: true,
        options: YES_NO_OPTIONS,
        placeholder: '请选择',
      },
    },
    {
      component: 'Input',
      fieldName: 'process_quality_type',
      label: '过程质量分类',
      componentProps: {
        placeholder: '请输入过程质量分类',
      },
    },
    {
      component: 'Select',
      fieldName: 'need_dev_analyze',
      label: '需开发分析',
      componentProps: {
        clearable: true,
        options: YES_NO_OPTIONS,
        placeholder: '请选择',
      },
    },
    {
      component: 'Select',
      fieldName: 'need_test_analyze',
      label: '需测试分析',
      componentProps: {
        clearable: true,
        options: YES_NO_OPTIONS,
        placeholder: '请选择',
      },
    },
    {
      component: 'UserSelector',
      fieldName: 'dev_owner_id',
      label: '开发责任人',
      componentProps: {
        placeholder: '请选择开发责任人',
      },
    },
    {
      component: 'UserSelector',
      fieldName: 'test_owner_id',
      label: '测试责任人',
      componentProps: {
        placeholder: '请选择测试责任人',
      },
    },
    {
      component: 'Select',
      fieldName: 'is_dev_analyzed',
      label: '开发分析完成',
      componentProps: {
        clearable: true,
        options: YES_NO_OPTIONS,
        placeholder: '请选择',
      },
    },
    {
      component: 'Select',
      fieldName: 'is_test_analyzed',
      label: '测试分析完成',
      componentProps: {
        clearable: true,
        options: YES_NO_OPTIONS,
        placeholder: '请选择',
      },
    },
    {
      component: 'Textarea',
      fieldName: 'qa_remark',
      label: '备注',
      componentProps: {
        placeholder: '请输入备注',
        rows: 3,
      },
    },
  ];
}

export function useDevFormSchema(): VbenFormSchema[] {
  const multiSelectProps = {
    multiple: true,
    filterable: true,
    allowCreate: true,
    defaultFirstOption: true,
    placeholder: '可输入并回车新增',
  };
  return [
    {
      component: 'Select',
      fieldName: 'dev_sub_category',
      label: '问题小类',
      componentProps: {
        ...multiSelectProps,
        options: [],
      },
    },
    {
      component: 'Textarea',
      fieldName: 'dev_reason',
      label: '问题原因',
      componentProps: {
        placeholder: '请输入问题原因',
        rows: 3,
      },
    },
    {
      component: 'Textarea',
      fieldName: 'dev_intro_reason',
      label: '引入原因',
      componentProps: {
        placeholder: '请输入引入原因',
        rows: 3,
      },
    },
    {
      component: 'Select',
      fieldName: 'dev_improvements',
      label: '改进措施(开发)',
      componentProps: {
        ...multiSelectProps,
        options: [],
      },
    },
    {
      component: 'Input',
      fieldName: 'dev_non_base_desc',
      label: '非底软说明',
      componentProps: {
        placeholder: '请输入非底软问题说明',
      },
    },
    {
      component: 'Input',
      fieldName: 'dev_asset_link',
      label: '落地资产链接(开发)',
      componentProps: {
        placeholder: '请输入链接',
      },
    },
    {
      component: 'Input',
      fieldName: 'dev_status',
      label: '改进状态(开发)',
      componentProps: {
        placeholder: '请输入状态（后续可接字典）',
      },
    },
  ];
}

export function useTestFormSchema(): VbenFormSchema[] {
  const multiSelectProps = {
    multiple: true,
    filterable: true,
    allowCreate: true,
    defaultFirstOption: true,
    placeholder: '可输入并回车新增',
  };
  return [
    {
      component: 'Input',
      fieldName: 'test_feature',
      label: '特效/功能',
      componentProps: {
        placeholder: '请输入特效/功能',
      },
    },
    {
      component: 'Select',
      fieldName: 'test_miss_reason',
      label: '漏测原因',
      componentProps: {
        ...multiSelectProps,
        options: [],
      },
    },
    {
      component: 'Textarea',
      fieldName: 'test_standard_desc',
      label: '规范问题描述',
      componentProps: {
        placeholder: '请输入规范问题描述',
        rows: 3,
      },
    },
    {
      component: 'Select',
      fieldName: 'test_improvements',
      label: '改进措施(测试)',
      componentProps: {
        ...multiSelectProps,
        options: [],
      },
    },
    {
      component: 'Textarea',
      fieldName: 'test_non_test_desc',
      label: '非测试说明',
      componentProps: {
        placeholder: '请输入非测试问题说明',
        rows: 2,
      },
    },
    {
      component: 'Input',
      fieldName: 'test_asset_link',
      label: '落地资产链接(测试)',
      componentProps: {
        placeholder: '请输入链接',
      },
    },
    {
      component: 'Input',
      fieldName: 'test_status',
      label: '改进状态(测试)',
      componentProps: {
        placeholder: '请输入状态（后续可接字典）',
      },
    },
  ];
}

export function normalizeProjectOptions(items: ProjectOut[]) {
  return (items || [])
    .map((item) => ({
      ...item,
      di_teams: Array.isArray(item.di_teams) ? item.di_teams : [],
      version_c: (item as any).version_c as string | undefined,
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}
