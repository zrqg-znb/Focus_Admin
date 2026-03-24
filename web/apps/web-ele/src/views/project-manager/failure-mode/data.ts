import type { Column } from 'element-plus';

import type { VbenFormSchema } from '#/adapter/form';
import type {
  DictOption,
  FailureModeDictOptions,
  FailureModeItem,
  HandlingMeasureItem,
  HuatuoDiagnosisItem,
  InterceptionStrategyItem,
  ObservationMethodItem,
  RelationItem,
  TestCaseItem,
} from '#/api/project-manager/failure_mode';
import type { ZqTableGridOptions } from '#/components/zq-table';

import { z } from '#/adapter/form';

export type MasterResourceKind =
  | 'huatuo'
  | 'interception'
  | 'measure'
  | 'observation'
  | 'testCase';

export type FailureModeTabKey =
  | 'failureMode'
  | 'huatuo'
  | 'interception'
  | 'measure'
  | 'observation'
  | 'testCase';

export const failureModeTabs: Array<{ key: FailureModeTabKey; label: string }> =
  [
    { key: 'failureMode', label: '故障模式' },
    { key: 'interception', label: '产线拦截策略' },
    { key: 'measure', label: '故障处理措施' },
    { key: 'observation', label: '维测手段' },
    { key: 'huatuo', label: '华佗诊断方案' },
    { key: 'testCase', label: '测试用例' },
  ];

export function createEmptyDictOptions(): FailureModeDictOptions {
  return {
    subsystem: [],
    module: [],
    chip: [],
    fault_category: [],
    functional_safety_level: [],
    occurrence_frequency: [],
    detectability: [],
    severity: [],
    status: [],
    measure_category: [],
    monitor_type: [],
  };
}

export function replaceDictOptions(
  target: FailureModeDictOptions,
  next: FailureModeDictOptions,
) {
  (Object.keys(target) as Array<keyof FailureModeDictOptions>).forEach(
    (key) => {
      target[key].splice(0, target[key].length, ...(next[key] || []));
    },
  );
}

export function normalizeStringList(value: unknown): string[] {
  if (Array.isArray(value)) {
    const result: string[] = [];
    const seen = new Set<string>();
    value.forEach((item) => {
      const text = String(item || '').trim();
      if (!text || seen.has(text)) {
        return;
      }
      seen.add(text);
      result.push(text);
    });
    return result;
  }

  const text = String(value || '').trim();
  return text ? [text] : [];
}

export function formatTextList(items?: null | string[]) {
  return normalizeStringList(items).join('、');
}

export function ensureOrderedRelationItems(
  ids: string[] = [],
  items: RelationItem[] = [],
): RelationItem[] {
  const itemMap = new Map(items.map((item) => [item.id, item]));
  return normalizeStringList(ids).map((id) => {
    return itemMap.get(id) || { id, label: id };
  });
}

export function upsertRelationItem(
  items: RelationItem[] = [],
  nextItem: RelationItem,
): RelationItem[] {
  const next = [...items];
  const index = next.findIndex((item) => item.id === nextItem.id);
  if (index === -1) {
    next.push(nextItem);
  } else {
    next[index] = nextItem;
  }
  return next;
}

export function removeRelationItem(
  items: RelationItem[] = [],
  id: string,
): RelationItem[] {
  return items.filter((item) => item.id !== id);
}

export function buildRelationItem(
  kind: MasterResourceKind,
  item:
    | HandlingMeasureItem
    | HuatuoDiagnosisItem
    | InterceptionStrategyItem
    | ObservationMethodItem
    | TestCaseItem,
): RelationItem {
  switch (kind) {
    case 'huatuo': {
      const row = item as HuatuoDiagnosisItem;
      const description = row.description || '';
      return {
        id: row.id,
        label:
          description.length > 60
            ? `${description.slice(0, 60)}...`
            : description || '未命名诊断方案',
      };
    }
    case 'interception': {
      const row = item as InterceptionStrategyItem;
      return {
        id: row.id,
        label: row.interception_item,
        subtitle: row.station || undefined,
      };
    }
    case 'measure': {
      const row = item as HandlingMeasureItem;
      return {
        id: row.id,
        label: row.measure,
        subtitle: row.measure_category || undefined,
      };
    }
    case 'observation': {
      const row = item as ObservationMethodItem;
      return {
        id: row.id,
        label:
          row.log_keyword ||
          row.log_id ||
          row.monitor_type ||
          row.log_path ||
          '未命名维测项',
        subtitle: row.monitor_type || undefined,
      };
    }
    default: {
      const row = item as TestCaseItem;
      return {
        id: row.id,
        label: row.brief,
        subtitle: row.cida_link || undefined,
      };
    }
  }
}

export function getResourceDisplayTitle(
  kind: MasterResourceKind,
  item:
    | HandlingMeasureItem
    | HuatuoDiagnosisItem
    | InterceptionStrategyItem
    | ObservationMethodItem
    | TestCaseItem,
) {
  return buildRelationItem(kind, item).label;
}

export function getResourceDisplaySubtitle(
  kind: MasterResourceKind,
  item:
    | HandlingMeasureItem
    | HuatuoDiagnosisItem
    | InterceptionStrategyItem
    | ObservationMethodItem
    | TestCaseItem,
) {
  if (kind === 'measure') {
    const row = item as HandlingMeasureItem;
    return (
      row.measure_category || `${row.test_case_items?.length || 0} 个测试用例`
    );
  }
  return buildRelationItem(kind, item).subtitle || '';
}

export function useKeywordSearchSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'keyword',
      label: '关键词',
      componentProps: { placeholder: '请输入关键词' },
    },
  ];
}

export function useFailureModeSearchSchema(
  dictOptions: FailureModeDictOptions,
): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'keyword',
      label: '关键词',
      componentProps: { placeholder: 'brief / 关联问题单 / 子系统' },
    },
    {
      component: 'Select',
      fieldName: 'subsystem',
      label: '子系统',
      componentProps: {
        clearable: true,
        options: dictOptions.subsystem,
      },
    },
    {
      component: 'Select',
      fieldName: 'module',
      label: '模块',
      componentProps: {
        clearable: true,
        options: dictOptions.module,
      },
    },
    {
      component: 'Select',
      fieldName: 'status',
      label: '状态',
      componentProps: {
        clearable: true,
        options: dictOptions.status,
      },
    },
  ];
}

function withCenter<T extends Record<string, any>>(
  columns: Column<T>[],
): ZqTableGridOptions<T>['columns'] {
  return columns.map((column) => ({
    align: 'center',
    headerAlign: 'center',
    ...column,
  }));
}

export function useFailureModeColumns(): ZqTableGridOptions<FailureModeItem>['columns'] {
  return withCenter<FailureModeItem>([
    { key: 'brief', dataKey: 'brief', title: '故障模式 brief', width: 220 },
    { key: 'subsystem', dataKey: 'subsystem', title: '子系统', width: 140 },
    { key: 'module', dataKey: 'module', title: '模块', width: 140 },
    { key: 'chips', dataKey: 'chips', title: '芯片', width: 180 },
    {
      key: 'fault_categories',
      dataKey: 'fault_categories',
      title: '故障类别',
      width: 180,
    },
    { key: 'status', dataKey: 'status', title: '状态', width: 120 },
    {
      key: 'author_info',
      dataKey: 'author_info',
      title: '作者',
      width: 180,
    },
    {
      key: 'related_dts_nos',
      dataKey: 'related_dts_nos',
      title: '关联问题单',
      width: 200,
    },
    {
      key: 'handling_measure_items',
      dataKey: 'handling_measure_items',
      title: '处理措施',
      width: 220,
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
      width: 140,
      showOverflowTooltip: false,
    },
  ]);
}

export function useInterceptionColumns(): ZqTableGridOptions<InterceptionStrategyItem>['columns'] {
  return withCenter<InterceptionStrategyItem>([
    {
      key: 'interception_item',
      dataKey: 'interception_item',
      title: '产线拦截项',
      width: 220,
    },
    { key: 'station', dataKey: 'station', title: '工位', width: 140 },
    {
      key: 'owner_info',
      dataKey: 'owner_info',
      title: '设计责任人',
      width: 180,
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
      width: 140,
      showOverflowTooltip: false,
    },
  ]);
}

export function useHandlingMeasureColumns(): ZqTableGridOptions<HandlingMeasureItem>['columns'] {
  return withCenter<HandlingMeasureItem>([
    { key: 'measure', dataKey: 'measure', title: '处理措施', width: 220 },
    {
      key: 'measure_category',
      dataKey: 'measure_category',
      title: '措施类别',
      width: 140,
    },
    {
      key: 'test_case_items',
      dataKey: 'test_case_items',
      title: '测试用例',
      width: 220,
    },
    {
      key: 'owner_info',
      dataKey: 'owner_info',
      title: '设计责任人',
      width: 180,
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
      width: 140,
      showOverflowTooltip: false,
    },
  ]);
}

export function useObservationColumns(): ZqTableGridOptions<ObservationMethodItem>['columns'] {
  return withCenter<ObservationMethodItem>([
    {
      key: 'monitor_type',
      dataKey: 'monitor_type',
      title: '维测类型',
      width: 140,
    },
    { key: 'log_id', dataKey: 'log_id', title: '日志 ID', width: 140 },
    {
      key: 'log_keyword',
      dataKey: 'log_keyword',
      title: '日志关键词',
      width: 220,
    },
    { key: 'log_path', dataKey: 'log_path', title: '日志获取路径', width: 260 },
    {
      key: 'owner_info',
      dataKey: 'owner_info',
      title: '设计责任人',
      width: 180,
    },
    {
      key: 'actions',
      dataKey: 'actions',
      title: '操作',
      width: 140,
      showOverflowTooltip: false,
    },
  ]);
}

export function useHuatuoColumns(): ZqTableGridOptions<HuatuoDiagnosisItem>['columns'] {
  return withCenter<HuatuoDiagnosisItem>([
    {
      key: 'description',
      dataKey: 'description',
      title: '诊断方案描述',
      width: 420,
    },
    {
      key: 'owner_info',
      dataKey: 'owner_info',
      title: '设计责任人',
      width: 180,
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
      width: 140,
      showOverflowTooltip: false,
    },
  ]);
}

export function useTestCaseColumns(): ZqTableGridOptions<TestCaseItem>['columns'] {
  return withCenter<TestCaseItem>([
    { key: 'brief', dataKey: 'brief', title: '测试用例 brief', width: 220 },
    { key: 'cida_link', dataKey: 'cida_link', title: 'CIDA 链接', width: 260 },
    {
      key: 'owner_info',
      dataKey: 'owner_info',
      title: '设计责任人',
      width: 180,
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
      width: 140,
      showOverflowTooltip: false,
    },
  ]);
}

function mapDictOptions(options: DictOption[]) {
  return options.map((item) => ({ label: item.label, value: item.value }));
}

export function useFailureModeFormSchema(
  dictOptions: FailureModeDictOptions,
): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'brief',
      label: '故障模式 brief',
      formItemClass: 'md:col-span-2',
      rules: z.string().min(1, '请输入故障模式 brief'),
    },
    {
      component: 'Select',
      fieldName: 'subsystem',
      label: '子系统',
      componentProps: {
        clearable: true,
        options: mapDictOptions(dictOptions.subsystem),
      },
    },
    {
      component: 'Select',
      fieldName: 'module',
      label: '模块',
      componentProps: {
        clearable: true,
        options: mapDictOptions(dictOptions.module),
      },
    },
    {
      component: 'Select',
      fieldName: 'chips',
      label: '芯片',
      componentProps: {
        clearable: true,
        multiple: true,
        collapseTags: true,
        collapseTagsTooltip: true,
        options: mapDictOptions(dictOptions.chip),
      },
      defaultValue: [],
    },
    {
      component: 'Select',
      fieldName: 'fault_categories',
      label: '故障类别',
      componentProps: {
        clearable: true,
        multiple: true,
        collapseTags: true,
        collapseTagsTooltip: true,
        options: mapDictOptions(dictOptions.fault_category),
      },
      defaultValue: [],
    },
    {
      component: 'Select',
      fieldName: 'functional_safety_level',
      label: '功能安全等级',
      componentProps: {
        clearable: true,
        options: mapDictOptions(dictOptions.functional_safety_level),
      },
    },
    {
      component: 'Select',
      fieldName: 'occurrence_frequency',
      label: '故障发生频度',
      componentProps: {
        clearable: true,
        options: mapDictOptions(dictOptions.occurrence_frequency),
      },
    },
    {
      component: 'Select',
      fieldName: 'detectability',
      label: '故障可探测度',
      componentProps: {
        clearable: true,
        options: mapDictOptions(dictOptions.detectability),
      },
    },
    {
      component: 'Select',
      fieldName: 'severity',
      label: '严重程度',
      componentProps: {
        clearable: true,
        options: mapDictOptions(dictOptions.severity),
      },
    },
    {
      component: 'UserSelector',
      fieldName: 'author_ids',
      label: '作者',
      componentProps: {
        multiple: true,
        placeholder: '请选择作者',
      },
      defaultValue: [],
    },
    {
      component: 'Select',
      fieldName: 'status',
      label: '状态',
      componentProps: {
        clearable: true,
        options: mapDictOptions(dictOptions.status),
      },
    },
    {
      component: 'RichTextEditor',
      fieldName: 'effect_html',
      label: '故障影响',
      formItemClass: 'md:col-span-2',
      defaultValue: '',
      componentProps: {
        minHeight: 220,
        maxHeight: 420,
      },
    },
    {
      component: 'RichTextEditor',
      fieldName: 'root_cause_html',
      label: '故障根因',
      formItemClass: 'md:col-span-2',
      defaultValue: '',
      componentProps: {
        minHeight: 220,
        maxHeight: 420,
      },
    },
  ];
}

export function useMasterFormSchema(
  kind: MasterResourceKind,
  dictOptions: FailureModeDictOptions,
): VbenFormSchema[] {
  switch (kind) {
    case 'huatuo': {
      return [
        {
          component: 'Textarea',
          fieldName: 'description',
          label: '诊断方案描述',
          formItemClass: 'md:col-span-2',
          componentProps: { rows: 6, placeholder: '请输入诊断方案描述' },
          rules: z.string().min(1, '请输入诊断方案描述'),
        },
        {
          component: 'UserSelector',
          fieldName: 'owner_ids',
          label: '设计责任人',
          componentProps: { multiple: true, placeholder: '请选择设计责任人' },
          defaultValue: [],
        },
      ];
    }
    case 'interception': {
      return [
        {
          component: 'Input',
          fieldName: 'interception_item',
          label: '产线拦截项',
          rules: z.string().min(1, '请输入产线拦截项'),
        },
        {
          component: 'RichTextEditor',
          fieldName: 'version_detection_html',
          label: '产线版本检测方案',
          formItemClass: 'md:col-span-2',
          defaultValue: '',
          componentProps: { minHeight: 220, maxHeight: 420 },
        },
        {
          component: 'Input',
          fieldName: 'station',
          label: '工位',
        },
        {
          component: 'UserSelector',
          fieldName: 'owner_ids',
          label: '设计责任人',
          componentProps: { multiple: true, placeholder: '请选择设计责任人' },
          defaultValue: [],
        },
      ];
    }
    case 'measure': {
      return [
        {
          component: 'Select',
          fieldName: 'measure_category',
          label: '措施类别',
          componentProps: {
            clearable: true,
            options: mapDictOptions(dictOptions.measure_category),
          },
        },
        {
          component: 'Input',
          fieldName: 'measure',
          label: '处理措施',
          rules: z.string().min(1, '请输入处理措施'),
        },
        {
          component: 'RichTextEditor',
          fieldName: 'measure_detail_html',
          label: '处理措施详情',
          formItemClass: 'md:col-span-2',
          defaultValue: '',
          componentProps: { minHeight: 220, maxHeight: 420 },
        },
        {
          component: 'Textarea',
          fieldName: 'measure_effect',
          label: '措施影响',
          formItemClass: 'md:col-span-2',
          componentProps: { rows: 3, placeholder: '请输入措施影响' },
        },
        {
          component: 'UserSelector',
          fieldName: 'owner_ids',
          label: '设计责任人',
          componentProps: { multiple: true, placeholder: '请选择设计责任人' },
          defaultValue: [],
        },
      ];
    }
    case 'observation': {
      return [
        {
          component: 'Select',
          fieldName: 'monitor_type',
          label: '维测类型',
          componentProps: {
            clearable: true,
            options: mapDictOptions(dictOptions.monitor_type),
          },
        },
        { component: 'Input', fieldName: 'log_id', label: '日志 ID' },
        { component: 'Input', fieldName: 'log_keyword', label: '日志关键词' },
        {
          component: 'Input',
          fieldName: 'log_path',
          label: '日志获取路径',
          formItemClass: 'md:col-span-2',
        },
        {
          component: 'UserSelector',
          fieldName: 'owner_ids',
          label: '设计责任人',
          componentProps: { multiple: true, placeholder: '请选择设计责任人' },
          defaultValue: [],
        },
      ];
    }
    default: {
      return [
        {
          component: 'Input',
          fieldName: 'brief',
          label: '测试用例 brief',
          rules: z.string().min(1, '请输入测试用例 brief'),
        },
        {
          component: 'RichTextEditor',
          fieldName: 'detail_html',
          label: '测试用例详情',
          formItemClass: 'md:col-span-2',
          defaultValue: '',
          componentProps: { minHeight: 220, maxHeight: 420 },
        },
        {
          component: 'Input',
          fieldName: 'cida_link',
          label: 'CIDA 链接',
          formItemClass: 'md:col-span-2',
        },
        {
          component: 'UserSelector',
          fieldName: 'owner_ids',
          label: '设计责任人',
          componentProps: { multiple: true, placeholder: '请选择设计责任人' },
          defaultValue: [],
        },
      ];
    }
  }
}

export function getMasterResourceLabel(kind: MasterResourceKind) {
  switch (kind) {
    case 'huatuo': {
      return '华佗诊断方案';
    }
    case 'interception': {
      return '产线拦截策略';
    }
    case 'measure': {
      return '故障处理措施';
    }
    case 'observation': {
      return '维测手段';
    }
    default: {
      return '测试用例';
    }
  }
}

export function formatUserNames(
  items?: Array<{ name?: null | string; username: string }>,
) {
  return (items || []).map((item) => item.name || item.username).join('、');
}

export function formatRelationLabels(items?: RelationLike[]) {
  return (items || []).map((item) => item.label).join('、');
}

export interface RelationLike {
  id: string;
  label: string;
}
