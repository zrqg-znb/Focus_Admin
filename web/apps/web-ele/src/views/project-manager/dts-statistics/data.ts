import type { VbenFormProps } from '#/adapter/form';
import type { VxeGridProps } from '#/adapter/vxe-table';

export const columns: VxeGridProps['columns'] = [
  { type: 'seq', width: 60, fixed: 'left' },
  { field: 'defectNo', title: 'DTS单号', width: 160, fixed: 'left' },
  { field: 'brief', title: '描述', minWidth: 200, fixed: 'left' },
  { field: 'severity', title: '级别', width: 100 },
  { field: 'currentStatus', title: '当前状态', width: 120 },
  { field: 'currentHandler', title: '当前处理人', width: 120 },

  // QA 识别
  {
    title: 'QA 识别',
    children: [
      { field: 'qa_category', title: '问题大类', width: 150 },
      { field: 'pl_group', title: '责任PL组', width: 150 },
      { field: 'is_downstream', title: '下游问题', width: 100 },
      { field: 'is_dev_analyzed', title: '开发分析完', width: 100 },
    ],
  },

  // 开发填写
  {
    title: '开发分析',
    children: [
      { field: 'dev_sub_category', title: '问题小类', width: 150 },
      { field: 'dev_status', title: '状态', width: 100 },
    ],
  },

  // 测试填写
  {
    title: '测试分析',
    children: [
      { field: 'test_miss_reason', title: '漏测原因', width: 150 },
      { field: 'test_status', title: '状态', width: 100 },
    ],
  },

  { title: '操作', width: 220, slots: { default: 'action' }, fixed: 'right' },
];

export const searchFormProps: VbenFormProps = {
  schema: [
    {
      component: 'ApiSelect',
      fieldName: 'project_ids',
      label: '项目',
      componentProps: {
        api: '/project_manager/projects/list', // 假设有这个接口
        params: { enable_dts: true },
        multiple: true,
        labelField: 'name',
        valueField: 'id',
      },
    },
    {
      component: 'Select',
      fieldName: 'column_type',
      label: '单据类型',
      defaultValue: 'openDefects',
      componentProps: {
        options: [
          { label: '未关闭', value: 'openDefects' },
          { label: '已关闭', value: 'closeDefects' },
          { label: '全部', value: 'totalDefects' },
        ],
      },
    },
    {
      component: 'RangePicker',
      fieldName: 'timeRange',
      label: '时间区间',
    },
  ],
};

export const qaFormSchema: VbenFormProps = {
  schema: [
    {
      component: 'DictSelect', // 假设有字典组件
      fieldName: 'qa_category',
      label: '问题大类',
      componentProps: { dictCode: 'dts_qa_category' },
    },
    {
      component: 'Input',
      fieldName: 'pl_group',
      label: '责任PL组',
    },
    {
      component: 'Select',
      fieldName: 'is_downstream',
      label: '下游问题',
      componentProps: {
        options: [
          { label: '是', value: '是' },
          { label: '否', value: '否' },
        ],
      },
    },
    {
      component: 'Input',
      fieldName: 'process_quality_type',
      label: '产品过程质量分类',
    },
    {
      component: 'Textarea',
      fieldName: 'qa_remark',
      label: '备注',
    },
  ],
};
