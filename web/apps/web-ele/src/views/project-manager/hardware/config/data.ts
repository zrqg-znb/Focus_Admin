import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridOptions } from '#/adapter/vxe-table';
import type { HardwarePoint } from '#/api/project-manager/hardware';

export function useSearchFormSchema(): VbenFormSchema[] {
  return [{ component: 'Input', fieldName: 'keyword', label: '关键词' }];
}

export function useColumns(
  onActionClick?: OnActionClickFn<HardwarePoint>,
): VxeTableGridOptions<HardwarePoint>['columns'] {
  return [
    { field: 'code', title: '硬件点位', minWidth: 140 },
    {
      field: 'boards',
      title: '板子列表',
      minWidth: 240,
      formatter: ({ cellValue }) => (cellValue || []).join('、'),
    },
    { field: 'remark', title: '备注', minWidth: 200 },
    { field: 'sys_create_datetime', title: '创建时间', minWidth: 160 },
    {
      align: 'right',
      cellRender: {
        attrs: {
          nameField: 'code',
          nameTitle: '硬件点位',
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: ['edit', 'delete'],
      } as any,
      field: 'operation',
      fixed: 'right',
      headerAlign: 'center',
      showOverflow: false,
      title: '操作',
      minWidth: 140,
    },
  ];
}
