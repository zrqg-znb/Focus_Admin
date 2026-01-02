import type { VbenFormProps } from '@vben/common-ui';
import type { VxeGridProps } from '#/adapter/vxe-table';

export function useColumns() {
  const columns: VxeGridProps['columns'] = [
    {
      field: 'project_name',
      title: '项目名称',
      minWidth: 150,
      fixed: 'left',
    },
    {
      field: 'manager_names',
      title: '项目经理',
      width: 150,
      formatter: ({ cellValue }) => {
        return Array.isArray(cellValue) ? cellValue.join(', ') : cellValue;
      },
    },
    {
      field: 'qg1_date',
      title: 'QG1',
      width: 120,
    },
    {
      field: 'qg2_date',
      title: 'QG2',
      width: 120,
    },
    {
      field: 'qg3_date',
      title: 'QG3',
      width: 120,
    },
    {
      field: 'qg4_date',
      title: 'QG4',
      width: 120,
    },
    {
      field: 'qg5_date',
      title: 'QG5',
      width: 120,
    },
    {
      field: 'qg6_date',
      title: 'QG6',
      width: 120,
    },
    {
      field: 'qg7_date',
      title: 'QG7',
      width: 120,
    },
    {
      field: 'qg8_date',
      title: 'QG8',
      width: 120,
    },
    {
      field: 'action',
      title: '操作',
      width: 100,
      fixed: 'right',
      slots: { default: 'action' },
    },
  ];
  return columns;
}

export function useSearchFormSchema(): VbenFormProps {
  return {
    schema: [
      {
        fieldName: 'keyword',
        label: '关键字',
        component: 'Input',
        componentProps: {
          placeholder: '项目名称',
          clearable: true,
        },
      },
      {
        fieldName: 'project_type',
        label: '类型',
        component: 'Input',
        componentProps: {
          clearable: true,
        },
      },
    ],
  };
}

export function useFormSchema(): VbenFormProps {
  const qgFields = Array.from({ length: 8 }, (_, i) => ({
    fieldName: `qg${i + 1}_date`,
    label: `QG${i + 1} 时间`,
    component: 'DatePicker',
    componentProps: {
      type: 'date',
      valueFormat: 'YYYY-MM-DD',
      placeholder: '选择日期',
      class: 'w-full',
    },
  }));

  return {
    schema: qgFields as any[],
  };
}
