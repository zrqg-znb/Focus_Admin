import type {
  EnvironmentItem,
  TestDeviceItem,
} from '#/api/environment-management';
import type { ZqTableGridOptions } from '#/components/zq-table';

import type { HeaderFilterConfig } from '../components/header-filter';

export const domainOptions = [
  { label: '座舱', value: 'cockpit' },
  { label: '车控', value: 'vehicle' },
];

export const categoryOptions = [
  { label: '开发', value: 'dev' },
  { label: '测试', value: 'test' },
  { label: 'CI', value: 'ci' },
];

export const adminEnvironmentHeaderFilters: HeaderFilterConfig[] = [
  { columnKey: 'ip_address', field: 'ip_address', label: 'IP地址', placeholder: '请输入 IP', type: 'input' },
  { columnKey: 'account', field: 'account', label: '账号', placeholder: '请输入账号', type: 'input' },
  { columnKey: 'bomid', field: 'bomid', label: 'BOMID', placeholder: '请输入 BOMID', type: 'input' },
  { columnKey: 'domain_label', field: 'domains', label: '领域', optionKey: 'domains', type: 'checkbox' },
  { columnKey: 'category_label', field: 'categories', label: '分类', optionKey: 'categories', type: 'checkbox' },
  { columnKey: 'project_name', field: 'project_name', label: '项目名称', placeholder: '请输入项目名称', type: 'input' },
  { columnKey: 'vehicle_model', field: 'vehicle_model', label: '车型', placeholder: '请输入车型', type: 'input' },
  { columnKey: 'device_display', field: 'device_ids', label: '测试设备', optionKey: 'device_options', type: 'cascader' },
  { columnKey: 'config_description', field: 'config_description', label: '配置情况', placeholder: '请输入配置情况', type: 'input' },
  { columnKey: 'asset_number', field: 'asset_number', label: '资产编号', placeholder: '请输入资产编号', type: 'input' },
  { columnKey: 'remark', field: 'remark', label: '备注', placeholder: '请输入备注', type: 'input' },
  { columnKey: 'shelf_location', field: 'shelf_location', label: '货架位置', placeholder: '请输入货架位置', type: 'input' },
  { columnKey: 'status_label', field: 'statuses', label: '状态', optionKey: 'statuses', type: 'checkbox' },
  { columnKey: 'current_user_name', field: 'current_user_name', label: '占用人', placeholder: '请输入占用人', type: 'input' },
  { columnKey: 'sys_update_datetime', endField: 'updated_end', field: 'updated_start', label: '更新时间', type: 'date-range' },
];

export const deviceHeaderFilters: HeaderFilterConfig[] = [
  { columnKey: 'name', field: 'name', label: '设备名称', placeholder: '请输入设备名称', type: 'input' },
  { columnKey: 'device_type_path', field: 'device_type_ids', label: '类型路径', optionKey: 'device_types', type: 'checkbox' },
  { columnKey: 'is_active', field: 'is_active_values', label: '状态', optionKey: 'device_statuses', type: 'checkbox' },
  { columnKey: 'remark', field: 'remark', label: '备注', placeholder: '请输入备注', type: 'input' },
];

const filterHeaderSlot = { header: 'environment-filter-header' };

export function useEnvironmentColumns(): ZqTableGridOptions<EnvironmentItem>['columns'] {
  return [
    { key: 'ip_address', dataKey: 'ip_address', title: 'IP地址', width: 140, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'account', dataKey: 'account', title: '账号', width: 120, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'bomid', dataKey: 'bomid', title: 'BOMID', width: 130, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'domain_label', dataKey: 'domain_label', title: '领域', width: 90, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'category_label', dataKey: 'category_label', title: '分类', width: 90, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'project_name', dataKey: 'project_name', title: '项目名称', width: 150, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'vehicle_model', dataKey: 'vehicle_model', title: '车型', width: 140, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'device_display', dataKey: 'device_display', title: '测试设备', width: 260, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'config_description', dataKey: 'config_description', title: '配置情况', width: 180, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'asset_number', dataKey: 'asset_number', title: '资产编号', width: 140, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'remark', dataKey: 'remark', title: '备注', width: 160, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'shelf_location', dataKey: 'shelf_location', title: '货架位置', width: 150, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'status_label', dataKey: 'status_label', title: '状态', width: 90, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'current_user_name', dataKey: 'current_user_name', title: '占用人', width: 120, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'sys_update_datetime', dataKey: 'sys_update_datetime', title: '更新时间', width: 180, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'actions', dataKey: 'actions', title: '操作', width: 150, align: 'center', headerAlign: 'center', fixed: true, showOverflowTooltip: false },
  ];
}

export function useDeviceColumns(): ZqTableGridOptions<TestDeviceItem>['columns'] {
  return [
    { key: 'name', dataKey: 'name', title: '设备名称', width: 160, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'device_type_path', dataKey: 'device_type_path', title: '类型路径', width: 220, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'is_active', dataKey: 'is_active', title: '状态', width: 90, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'remark', dataKey: 'remark', title: '备注', width: 180, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'actions', dataKey: 'actions', title: '操作', width: 150, align: 'center', headerAlign: 'center', fixed: true, showOverflowTooltip: false },
  ];
}
