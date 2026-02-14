import type { VbenFormSchema } from '#/adapter/form';
import { listProjectsApi } from '#/api/project-manager/project';
import ParentNodeSelect from './admin/modules/ParentNodeSelect.vue';

export function useNodeFormSchema(): VbenFormSchema[] {
  return [
    {
      component: ParentNodeSelect,
      fieldName: 'parent_id',
      label: '上级节点',
      modelPropName: 'modelValue',
      componentProps: {
        placeholder: '请选择上级节点（留空为根节点）',
      },
      help: '留空即为根节点，可搜索或直接点“设为根节点”',
    },
    {
      component: 'Input',
      fieldName: 'name',
      label: '节点名称',
      rules: 'required',
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: '节点编码',
    },
    {
      component: 'InputNumber',
      fieldName: 'sort_order',
      label: '排序',
      componentProps: {
        min: 0,
        precision: 0,
        placeholder: '0',
      },
    },
    {
      component: 'ApiSelect',
      fieldName: 'linked_project_id',
      label: '关联项目',
      componentProps: {
        api: async () => {
          const res = await listProjectsApi({ pageSize: 1000 });
          return res.items;
        },
        labelField: 'name',
        valueField: 'id',
        showSearch: true,
        optionFilterProp: 'label',
        placeholder: '请选择关联项目（可选）',
      },
    },
    {
      component: 'Input',
      fieldName: 'description',
      label: '描述',
      componentProps: {
        placeholder: '请输入节点描述信息',
        type: 'textarea',
        rows: 3,
      },
    },
  ];
}
