import type { VxeTableGridOptions } from '@vben/plugins/vxe-table';

import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn } from '#/adapter/vxe-table';
import type { SchedulerJob, SchedulerLog } from '#/api/core/scheduler';

import { z } from '#/adapter/form';

/**
 * 获取触发器类型选项
 */
export function getTriggerTypeOptions() {
  return [
    { label: 'Cron表达式', value: 'cron' },
    { label: '间隔执行', value: 'interval' },
    { label: '指定时间', value: 'date' },
  ];
}

/**
 * 获取任务状态选项
 */
export function getJobStatusOptions() {
  return [
    { label: '禁用', value: 0 },
    { label: '启用', value: 1 },
    { label: '暂停', value: 2 },
  ];
}

/**
 * 获取日志执行状态选项
 */
export function getLogStatusOptions() {
  return [
    { label: '等待执行', value: 'pending' },
    { label: '执行中', value: 'running' },
    { label: '执行成功', value: 'success' },
    { label: '执行失败', value: 'failed' },
    { label: '执行超时', value: 'timeout' },
    { label: '跳过执行', value: 'skipped' },
  ];
}

/**
 * 获取间隔执行时间单位选项
 */
export function getIntervalUnitOptions() {
  return [
    { label: '秒', value: 'seconds' },
    { label: '分', value: 'minutes' },
    { label: '时', value: 'hours' },
    { label: '天', value: 'days' },
  ];
}

/**
 * 获取状态标签类型
 */
export function getStatusType(
  status: number,
): 'danger' | 'info' | 'success' | 'warning' {
  switch (status) {
    case 1: {
      return 'success';
    } // 启用
    case 2: {
      return 'warning';
    } // 暂停
    default: {
      return 'danger';
    } // 禁用
  }
}

/**
 * 获取日志状态标签类型
 */
export function getLogStatusType(
  status: string,
): 'danger' | 'info' | 'success' | 'warning' {
  switch (status) {
    case 'failed': {
      return 'danger';
    }
    case 'running': {
      return 'info';
    }
    case 'success': {
      return 'success';
    }
    case 'timeout': {
      return 'warning';
    }
    default: {
      return 'info';
    }
  }
}

/**
 * 获取状态显示名称
 */
export function getStatusName(status: number): string {
  const statusMap = {
    0: '禁用',
    1: '启用',
    2: '暂停',
  };
  return statusMap[status as keyof typeof statusMap] || '未知';
}

/**
 * 获取日志状态显示名称
 */
export function getLogStatusName(status: string): string {
  const statusMap: Record<string, string> = {
    pending: '等待执行',
    running: '执行中',
    success: '执行成功',
    failed: '执行失败',
    timeout: '执行超时',
    skipped: '跳过执行',
  };
  return statusMap[status] || '未知';
}

/**
 * 获取创建/编辑任务表单配置
 */
export function useJobFormSchema(): VbenFormSchema[] {
  const formSchema: VbenFormSchema[] = [
    {
      component: 'Input',
      fieldName: 'name',
      label: '任务名称',
      rules: z
        .string()
        .min(1, '任务名称不能为空')
        .max(128, '任务名称长度不能超过128个字符'),
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: '任务编码',
      rules: z
        .string()
        .min(1, '任务编码不能为空')
        .max(128, '任务编码长度不能超过128个字符')
        .regex(/^\w+$/, '任务编码只能包含字母、数字和下划线'),
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '任务分组，默认为default',
      },
      fieldName: 'group',
      label: '任务分组',
    },
    {
      component: 'Select',
      componentProps: {
        options: getTriggerTypeOptions(),
      },
      fieldName: 'trigger_type',
      label: '触发器类型',
      rules: z.string().min(1, '触发器类型不能为空'),
    },
  ];

  // 添加所有字段，通过 dependencies 的 show 控制显示
  formSchema.push(
    // Cron 表达式字段（仅在触发器类型为 cron 时显示）
    {
      component: 'CronSelector',
      componentProps: {
        placeholder: '例如: 0 0 * * *（每天凌晨0点）',
        hideSecond: true,
        hideYear: true,
      },
      fieldName: 'cron_expression',
      label: 'Cron表达式',
      rules: z.string().optional(),
      dependencies: {
        show: (values: any) => values.trigger_type === 'cron',
        triggerFields: ['trigger_type'],
      },
    },
    // 间隔执行时间单位（仅在触发器类型为 interval 时显示）
    {
      component: 'RadioGroup',
      componentProps: {
        options: getIntervalUnitOptions(),
        isButton: true,
      },
      defaultValue: 'seconds',
      fieldName: 'interval_unit',
      label: '时间单位',
      dependencies: {
        show: (values: any) => values.trigger_type === 'interval',
        triggerFields: ['trigger_type'],
      },
    },
    // 间隔时间字段（仅在触发器类型为 interval 时显示）
    {
      component: 'InputNumber',
      componentProps: {
        min: 1,
        placeholder: '间隔时间',
      },
      fieldName: 'interval_seconds',
      label: '间隔时间',
      rules: z.number().positive().optional(),
      dependencies: {
        show: (values: any) => values.trigger_type === 'interval',
        triggerFields: ['trigger_type'],
      },
    },

    // 指定执行时间字段（仅在触发器类型为 date 时显示）
    {
      component: 'DatePicker',
      fieldName: 'run_date',
      label: '指定执行时间',
      rules: z.string().optional(),
      componentProps: {
        placeholder: '指定执行时间',
        type: 'datetime',
        valueFormat: 'YYYY-MM-DD HH:mm:ss',
        showTime: true,
      },
      dependencies: {
        show: (values: any) => values.trigger_type === 'date',
        triggerFields: ['trigger_type'],
      },
    },
    // 任务函数路径
    {
      component: 'Input',
      fieldName: 'task_func',
      label: '任务函数路径',
      rules: z.string().min(1, '任务函数路径不能为空'),
    },
    // 任务位置参数
    {
      component: 'Input',
      componentProps: {
        type: 'textarea',
        autosize: {
          minRows: 2,
          maxRows: 6,
        },
        placeholder: 'JSON数组格式，例如: ["param1", "param2"]',
      },
      fieldName: 'task_args',
      label: '任务位置参数',
    },
    // 任务关键字参数
    {
      component: 'Input',
      componentProps: {
        type: 'textarea',
        autosize: {
          minRows: 2,
          maxRows: 6,
        },
        placeholder: 'JSON对象格式，例如: {"key": "value"}',
      },
      fieldName: 'task_kwargs',
      label: '任务关键字参数',
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: getJobStatusOptions(),
      },
      defaultValue: 1,
      fieldName: 'status',
      label: '任务状态',
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 0,
      },
      defaultValue: 0,
      fieldName: 'priority',
      label: '任务优先级',
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 1,
      },
      defaultValue: 1,
      fieldName: 'max_instances',
      label: '最大实例数',
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 0,
      },
      defaultValue: 0,
      fieldName: 'max_retries',
      label: '错误重试次数',
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 1,
        placeholder: '超时时间（秒）',
      },
      fieldName: 'timeout',
      label: '超时时间',
    },
    {
      component: 'Checkbox',
      defaultValue: true,
      fieldName: 'coalesce',
      label: '是否合并执行',
    },
    {
      component: 'Checkbox',
      defaultValue: false,
      fieldName: 'allow_concurrent',
      label: '是否允许并发执行',
    },
    {
      component: 'Textarea',
      componentProps: {
        placeholder: '备注信息',
        rows: 3,
      },
      fieldName: 'remark',
      label: '备注',
    },
  );

  return formSchema;
}

/**
 * 获取定时任务列表表格列配置
 */
export function useJobTableColumns(
  onActionClick?: OnActionClickFn<SchedulerJob>,
): VxeTableGridOptions<SchedulerJob>['columns'] {
  return [
    {
      type: 'checkbox',
      width: 60,
      align: 'center',
      fixed: 'left',
    },
    {
      field: 'name',
      title: '任务名称',
      minWidth: 150,
    },
    {
      field: 'code',
      title: '任务编码',
      minWidth: 130,
    },
    {
      field: 'group',
      title: '分组',
      minWidth: 100,
    },
    {
      field: 'trigger_type',
      title: '触发器类型',
      minWidth: 110,
      cellRender: {
        name: 'CellDict',
        props: {
          dict: getTriggerTypeOptions(),
        },
      },
    },
    {
      field: 'status',
      title: '状态',
      minWidth: 100,
      cellRender: {
        name: 'CellStatus',
        attrs: {
          dict: getJobStatusOptions(),
        },
      },
    },
    {
      field: 'priority',
      title: '优先级',
      minWidth: 80,
      align: 'center',
    },
    {
      field: 'total_run_count',
      title: '执行次数',
      minWidth: 100,
      align: 'center',
    },
    {
      field: 'success_count',
      title: '成功次数',
      minWidth: 100,
      align: 'center',
    },
    {
      field: 'failure_count',
      title: '失败次数',
      minWidth: 100,
      align: 'center',
    },
    {
      field: 'last_run_time',
      title: '最后执行时间',
      minWidth: 180,
      cellRender: {
        name: 'CellDatetime',
      },
    },
    {
      field: 'next_run_time',
      title: '下次执行时间',
      minWidth: 180,
      cellRender: {
        name: 'CellDatetime',
      },
    },
    {
      align: 'right',
      cellRender: {
        attrs: {
          nameField: 'name',
          nameTitle: '任务名称',
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: ['edit', 'delete'],
      },
      field: 'operation',
      fixed: 'right',
      headerAlign: 'center',
      showOverflow: false,
      title: '操作',
      minWidth: 150,
    },
  ];
}

/**
 * 获取执行日志列表表格列配置
 */
export function useLogTableColumns(): VxeTableGridOptions<SchedulerLog>['columns'] {
  return [
    {
      field: 'job_name',
      title: '任务名称',
      minWidth: 150,
    },
    {
      field: 'job_code',
      title: '任务编码',
      minWidth: 130,
    },
    {
      field: 'status',
      title: '执行状态',
      minWidth: 110,
      cellRender: {
        name: 'CellDict',
        props: {
          dict: getLogStatusOptions(),
        },
      },
    },
    {
      field: 'start_time',
      title: '开始时间',
      minWidth: 180,
      cellRender: {
        name: 'CellDatetime',
      },
    },
    {
      field: 'duration',
      title: '执行耗时（秒）',
      minWidth: 130,
      align: 'center',
    },
    {
      field: 'retry_count',
      title: '重试次数',
      minWidth: 100,
      align: 'center',
    },
    {
      field: 'operation',
      title: '操作',
      minWidth: 100,
      align: 'center',
      fixed: 'right',
      cellRender: {
        name: 'CellOperation',
        options: ['view', 'delete'],
      },
    },
  ];
}

/**
 * 获取搜索表单字段配置
 */
export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: '任务名称',
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: '任务编码',
    },
    {
      component: 'Input',
      fieldName: 'group',
      label: '任务分组',
    },
    {
      component: 'Select',
      componentProps: {
        options: getTriggerTypeOptions(),
      },
      fieldName: 'trigger_type',
      label: '触发器类型',
    },
    {
      component: 'Select',
      componentProps: {
        options: getJobStatusOptions(),
      },
      fieldName: 'status',
      label: '任务状态',
    },
  ];
}
