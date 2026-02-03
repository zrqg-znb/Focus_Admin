import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import { z } from '#/adapter/form';

export function getFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: '项目名称',
      rules: z.string().min(1, '请输入项目名称'),
    },
    {
      component: 'Input',
      fieldName: 'repo_url',
      label: '代码仓地址',
      rules: z.string().min(1, '请输入代码仓地址'),
    },
    {
      component: 'Input',
      fieldName: 'branch',
      label: '分支',
      defaultValue: 'master',
    },
    {
      component: 'Input',
      fieldName: 'docker_image',
      label: 'Docker镜像',
      rules: z.string().min(1, '请输入Docker镜像'),
    },
    {
      component: 'Input',
      fieldName: 'build_cmd',
      label: '编译命令',
      componentProps: {
        type: 'textarea',
        placeholder: '例如: make -j4',
      },
      rules: z.string().min(1, '请输入编译命令'),
    },
    {
      component: 'Input',
      fieldName: 'description',
      label: '描述',
      componentProps: {
        type: 'textarea',
      },
    },
  ];
}

export function useColumns(): VxeTableGridOptions<any>['columns'] {
  return [
    { type: 'seq', width: 60 },
    { field: 'name', title: '项目名称', minWidth: 150 },
    { field: 'repo_url', title: '代码仓', minWidth: 250 },
    { field: 'branch', title: '分支', width: 100 },
    { field: 'docker_image', title: '镜像', minWidth: 150 },
    {
        field: 'action',
        title: '操作',
        fixed: 'right',
        width: 150,
        slots: { default: 'action' }
    }
  ];
}
