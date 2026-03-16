import type { VbenFormSchema } from '#/adapter/form';
import type { PlGroup } from '#/api/core/pl';
import type { DtsMergedDefect } from '#/api/project-manager/dts-statistics';
import type { ProjectOut } from '#/api/project-manager/project';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { getAllPlApi } from '#/api/core/pl';

type Columns = ZqTableGridOptions<DtsMergedDefect>['columns'];

const YES_NO_OPTIONS = [
  { label: '是', value: '是' },
  { label: '否', value: '否' },
];

export interface SeverityMeta {
  label: string;
  type: 'danger' | 'info' | 'success' | 'warning';
  tip: string;
}

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

export function formatDateTime(date: Date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(
    date.getDate(),
  )} ${pad2(date.getHours())}:${pad2(date.getMinutes())}:${pad2(
    date.getSeconds(),
  )}`;
}

export function getTodayDateRange(): [Date, Date] {
  const now = new Date();
  const start = new Date(now);
  start.setHours(0, 0, 0, 0);
  const end = new Date(now);
  end.setHours(23, 59, 59, 0);
  return [start, end];
}

export function useColumns(): Columns {
  return withCenterAlign([
    {
      key: 'defectNo',
      dataKey: 'defectNo',
      title: 'DTS单号',
      width: 170,
      fixed: 'left',
    },
    {
      key: 'project_name',
      dataKey: 'project_name',
      title: '项目',
      width: 220,
      fixed: 'left',
    },
    {
      key: 'team_name',
      dataKey: 'team_name',
      title: '团队',
      width: 200,
      fixed: 'left',
    },
    {
      key: 'severity',
      dataKey: 'severity',
      title: '级别',
      width: 90,
    },
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
      key: 'process_days',
      dataKey: 'process_days',
      title: '处理天数',
      width: 110,
    },
    {
      key: 'brief',
      dataKey: 'brief',
      title: '描述',
      minWidth: 260,
      showOverflowTooltip: true,
    },
    {
      key: 'currentStage',
      dataKey: 'currentStage',
      title: '阶段',
      width: 140,
    },
    {
      key: 'closeType',
      dataKey: 'closeType',
      title: '关闭类型',
      width: 140,
    },
    {
      key: 'qa_group',
      title: 'QA填报',
      children: [
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
          key: 'is_downstream',
          dataKey: 'is_downstream',
          title: '是否下游',
          width: 110,
        },
        {
          key: 'process_quality_type',
          dataKey: 'process_quality_type',
          title: '过程质量分类',
          minWidth: 160,
        },
        {
          key: 'need_dev_analyze',
          dataKey: 'need_dev_analyze',
          title: '需开发分析',
          width: 120,
        },
        {
          key: 'need_test_analyze',
          dataKey: 'need_test_analyze',
          title: '需测试分析',
          width: 120,
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
          key: 'is_dev_analyzed',
          dataKey: 'is_dev_analyzed',
          title: '开发分析完成',
          width: 140,
        },
        {
          key: 'is_test_analyzed',
          dataKey: 'is_test_analyzed',
          title: '测试分析完成',
          width: 140,
        },
        {
          key: 'qa_remark',
          dataKey: 'qa_remark',
          title: 'QA备注',
          minWidth: 200,
        },
      ],
    },
    {
      key: 'dev_group',
      title: '开发填报',
      children: [
        {
          key: 'dev_sub_category',
          dataKey: 'dev_sub_category',
          title: '问题小类',
          minWidth: 180,
        },
        {
          key: 'dev_reason',
          dataKey: 'dev_reason',
          title: '问题原因',
          minWidth: 180,
        },
        {
          key: 'dev_intro_reason',
          dataKey: 'dev_intro_reason',
          title: '引入原因',
          minWidth: 180,
        },
        {
          key: 'dev_improvements',
          dataKey: 'dev_improvements',
          title: '改进措施',
          minWidth: 200,
        },
        {
          key: 'dev_non_base_desc',
          dataKey: 'dev_non_base_desc',
          title: '非底软说明',
          width: 160,
        },
        {
          key: 'dev_asset_link',
          dataKey: 'dev_asset_link',
          title: '落地资产链接',
          minWidth: 200,
        },
        {
          key: 'dev_status',
          dataKey: 'dev_status',
          title: '改进状态',
          width: 140,
        },
      ],
    },
    {
      key: 'test_group',
      title: '测试填报',
      children: [
        {
          key: 'test_feature',
          dataKey: 'test_feature',
          title: '特效/功能',
          width: 160,
        },
        {
          key: 'test_miss_reason',
          dataKey: 'test_miss_reason',
          title: '漏测原因',
          minWidth: 180,
        },
        {
          key: 'test_standard_desc',
          dataKey: 'test_standard_desc',
          title: '规范问题描述',
          minWidth: 200,
        },
        {
          key: 'test_improvements',
          dataKey: 'test_improvements',
          title: '改进措施',
          minWidth: 200,
        },
        {
          key: 'test_non_test_desc',
          dataKey: 'test_non_test_desc',
          title: '非测试说明',
          minWidth: 180,
        },
        {
          key: 'test_asset_link',
          dataKey: 'test_asset_link',
          title: '落地资产链接',
          minWidth: 200,
        },
        {
          key: 'test_status',
          dataKey: 'test_status',
          title: '改进状态',
          width: 140,
        },
      ],
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 130,
      fixed: 'right',
    },
  ]) as Columns;
}

export function resolveSeverityMeta(raw?: null | string): SeverityMeta {
  const text = String(raw || '').trim();
  const normalized = text.toLowerCase().replaceAll(/\s+/g, '');

  const has = (pattern: string) => normalized.includes(pattern);
  const equals = (pattern: string) => normalized === pattern;

  if (
    has('关键') ||
    has('致命') ||
    has('fatal') ||
    has('critical') ||
    equals('s0') ||
    equals('p0') ||
    has('blocker')
  ) {
    return {
      label: text || '关键',
      type: 'danger',
      tip: '最高优先级/影响范围最大',
    };
  }
  if (
    has('严重') ||
    has('high') ||
    has('major') ||
    equals('s1') ||
    equals('p1')
  ) {
    return { label: text || '严重', type: 'warning', tip: '高优先级/影响较大' };
  }
  if (
    has('一般') ||
    has('medium') ||
    has('normal') ||
    equals('s2') ||
    equals('p2')
  ) {
    return { label: text || '一般', type: 'info', tip: '中等优先级' };
  }
  if (
    has('提示') ||
    has('low') ||
    has('minor') ||
    equals('s3') ||
    equals('p3')
  ) {
    return { label: text || '提示', type: 'success', tip: '低优先级/提示类' };
  }

  return {
    label: text || '-',
    type: 'info',
    tip: '未识别的级别，按默认样式展示',
  };
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
  return [
    {
      component: 'Textarea',
      fieldName: 'dev_sub_category',
      label: '问题小类',
      componentProps: {
        placeholder: '一行一条（保存时自动拆分）',
        rows: 3,
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
      component: 'Textarea',
      fieldName: 'dev_improvements',
      label: '改进措施(开发)',
      componentProps: {
        placeholder: '一行一条（保存时自动拆分）',
        rows: 3,
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
      component: 'Textarea',
      fieldName: 'test_miss_reason',
      label: '漏测原因',
      componentProps: {
        placeholder: '一行一条（保存时自动拆分）',
        rows: 3,
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
      component: 'Textarea',
      fieldName: 'test_improvements',
      label: '改进措施(测试)',
      componentProps: {
        placeholder: '一行一条（保存时自动拆分）',
        rows: 3,
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
