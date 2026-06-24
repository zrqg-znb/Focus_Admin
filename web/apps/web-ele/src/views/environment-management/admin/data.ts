import type { VbenFormSchema } from '#/adapter/form';
import type {
  EnvironmentItem,
  TestDeviceItem,
} from '#/api/environment-management';
import type { ZqTableGridOptions } from '#/components/zq-table';

export const domainOptions = [
  { label: '座舱', value: 'cockpit' },
  { label: '车控', value: 'vehicle' },
];

export const categoryOptions = [
  { label: '开发', value: 'dev' },
  { label: '测试', value: 'test' },
  { label: 'CI', value: 'ci' },
];

export function useEnvironmentColumns(): ZqTableGridOptions<EnvironmentItem>['columns'] {
  return [
    { key: 'ip_address', dataKey: 'ip_address', title: 'IP地址', width: 140, align: 'center', headerAlign: 'center' },
    { key: 'account', dataKey: 'account', title: '账号', width: 120, align: 'center', headerAlign: 'center' },
    { key: 'bomid', dataKey: 'bomid', title: 'BOMID', width: 130, align: 'center', headerAlign: 'center' },
    { key: 'domain_label', dataKey: 'domain_label', title: '领域', width: 90, align: 'center', headerAlign: 'center' },
    { key: 'category_label', dataKey: 'category_label', title: '分类', width: 90, align: 'center', headerAlign: 'center' },
    { key: 'project_name', dataKey: 'project_name', title: '项目名称', width: 150, align: 'center', headerAlign: 'center' },
    { key: 'vehicle_model', dataKey: 'vehicle_model', title: '车型', width: 140, align: 'center', headerAlign: 'center' },
    { key: 'device_display', dataKey: 'device_display', title: '测试设备', width: 260, align: 'center', headerAlign: 'center' },
    { key: 'config_description', dataKey: 'config_description', title: '配置情况', width: 180, align: 'center', headerAlign: 'center' },
    { key: 'asset_number', dataKey: 'asset_number', title: '资产编号', width: 140, align: 'center', headerAlign: 'center' },
    { key: 'remark', dataKey: 'remark', title: '备注', width: 160, align: 'center', headerAlign: 'center' },
    { key: 'shelf_location', dataKey: 'shelf_location', title: '货架位置', width: 150, align: 'center', headerAlign: 'center' },
    { key: 'status_label', dataKey: 'status_label', title: '状态', width: 90, align: 'center', headerAlign: 'center' },
    { key: 'current_user_name', dataKey: 'current_user_name', title: '占用人', width: 120, align: 'center', headerAlign: 'center' },
    { key: 'sys_update_datetime', dataKey: 'sys_update_datetime', title: '更新时间', width: 180, align: 'center', headerAlign: 'center' },
    { key: 'actions', dataKey: 'actions', title: '操作', width: 150, align: 'center', headerAlign: 'center', fixed: true, showOverflowTooltip: false },
  ];
}

export function useDeviceColumns(): ZqTableGridOptions<TestDeviceItem>['columns'] {
  return [
    { key: 'name', dataKey: 'name', title: '设备名称', width: 160, align: 'center', headerAlign: 'center' },
    { key: 'device_type_path', dataKey: 'device_type_path', title: '类型路径', width: 220, align: 'center', headerAlign: 'center' },
    { key: 'is_active', dataKey: 'is_active', title: '状态', width: 90, align: 'center', headerAlign: 'center' },
    { key: 'remark', dataKey: 'remark', title: '备注', width: 180, align: 'center', headerAlign: 'center' },
    { key: 'actions', dataKey: 'actions', title: '操作', width: 150, align: 'center', headerAlign: 'center', fixed: true, showOverflowTooltip: false },
  ];
}

export function useEnvironmentSearchSchema(): VbenFormSchema[] {
  return [
    { component: 'Input', fieldName: 'keyword', label: '关键词' },
    { component: 'Select', componentProps: { options: domainOptions, clearable: true }, fieldName: 'domain', label: '领域' },
    { component: 'Select', componentProps: { options: categoryOptions, clearable: true }, fieldName: 'category', label: '分类' },
  ];
}
