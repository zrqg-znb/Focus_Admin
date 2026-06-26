import type { EnvironmentItem } from '#/api/environment-management';
import type { ZqTableGridOptions } from '#/components/zq-table';

import type { HeaderFilterConfig } from '../components/header-filter';

interface ElementTableColumn {
  key: string;
  label: string;
  minWidth?: number;
  prop?: string;
  width?: number;
}

export const domainOptions = [
  { label: '全部领域', value: '' },
  { label: '座舱', value: 'cockpit' },
  { label: '车控', value: 'vehicle' },
];

export const categoryOptions = [
  { label: '全部分类', value: '' },
  { label: '开发', value: 'dev' },
  { label: '测试', value: 'test' },
  { label: 'CI', value: 'ci' },
];

export const environmentUsageHeaderFilters: HeaderFilterConfig[] = [
  { columnKey: 'favorite', field: 'favorite_state', label: '收藏', optionKey: 'favorite_states', type: 'checkbox' },
  { columnKey: 'ip_address', field: 'ip_address', label: 'IP地址', placeholder: '请输入 IP', type: 'input' },
  { columnKey: 'account', field: 'account', label: '账号', placeholder: '请输入账号', type: 'input' },
  { columnKey: 'bomid', field: 'bomid', label: 'BOMID', placeholder: '请输入 BOMID', type: 'input' },
  { columnKey: 'domain', field: 'domains', label: '领域', optionKey: 'domains', type: 'checkbox' },
  { columnKey: 'category', field: 'categories', label: '分类', optionKey: 'categories', type: 'checkbox' },
  { columnKey: 'project_name', field: 'project_name', label: '项目', placeholder: '请输入项目', type: 'input' },
  { columnKey: 'vehicle_model', field: 'vehicle_model', label: '车型', placeholder: '请输入车型', type: 'input' },
  { columnKey: 'device_display', field: 'device_ids', label: '测试设备', optionKey: 'device_options', type: 'cascader' },
  { columnKey: 'occupy_state', field: 'statuses', label: '占用情况', optionKey: 'statuses', type: 'checkbox' },
  { columnKey: 'current_user_name', field: 'current_user_name', label: '占用人', placeholder: '请输入占用人', type: 'input' },
  { columnKey: 'queue_state', field: 'queue_state', label: '排队', optionKey: 'queue_states', type: 'checkbox' },
];

const filterHeaderSlot = { header: 'environment-filter-header' };

export function useEnvironmentUsageColumns(): ZqTableGridOptions<EnvironmentItem>['columns'] {
  return [
    { key: 'favorite', dataKey: 'favorite', title: '收藏', width: 64, align: 'center', headerAlign: 'center', showOverflowTooltip: false, slots: filterHeaderSlot },
    { key: 'ip_address', dataKey: 'ip_address', title: 'IP地址', width: 140, align: 'center', headerAlign: 'center', slots: filterHeaderSlot },
    { key: 'account', dataKey: 'account', title: '账号', width: 120, align: 'center', headerAlign: 'center', showOverflowTooltip: false, slots: filterHeaderSlot },
    { key: 'bomid', dataKey: 'bomid', title: 'BOMID', width: 130, align: 'center', headerAlign: 'center', showOverflowTooltip: false, slots: filterHeaderSlot },
    { key: 'domain', dataKey: 'domain', title: '领域', width: 90, align: 'center', headerAlign: 'center', showOverflowTooltip: false, slots: filterHeaderSlot },
    { key: 'category', dataKey: 'category', title: '分类', width: 90, align: 'center', headerAlign: 'center', showOverflowTooltip: false, slots: filterHeaderSlot },
    { key: 'project_name', dataKey: 'project_name', title: '项目', width: 120, align: 'center', headerAlign: 'center', showOverflowTooltip: false, slots: filterHeaderSlot },
    { key: 'vehicle_model', dataKey: 'vehicle_model', title: '车型', width: 120, align: 'center', headerAlign: 'center', showOverflowTooltip: false, slots: filterHeaderSlot },
    { key: 'device_display', dataKey: 'device_display', title: '测试设备', width: 220, align: 'center', headerAlign: 'center', showOverflowTooltip: false, slots: filterHeaderSlot },
    { key: 'occupy_state', dataKey: 'occupy_state', title: '占用情况', width: 150, align: 'center', headerAlign: 'center', showOverflowTooltip: false, slots: filterHeaderSlot },
    { key: 'current_user_name', dataKey: 'current_user_name', title: '占用人', width: 120, align: 'center', headerAlign: 'center', showOverflowTooltip: false, slots: filterHeaderSlot },
    { key: 'queue_state', dataKey: 'queue_state', title: '排队', width: 130, align: 'center', headerAlign: 'center', showOverflowTooltip: false, slots: filterHeaderSlot },
    { key: 'actions', dataKey: 'actions', title: '操作', width: 320, align: 'center', headerAlign: 'center', fixed: true, showOverflowTooltip: false },
  ];
}

export const queueTableColumns: ElementTableColumn[] = [
  { key: 'position', label: '位置', prop: 'position', width: 80 },
  { key: 'user_name', label: '用户', prop: 'user_name' },
  { key: 'queue_type_label', label: '类型', prop: 'queue_type_label', width: 100 },
  { key: 'requested_at', label: '申请时间', prop: 'requested_at', width: 180 },
];

export const recordTableColumns: ElementTableColumn[] = [
  { key: 'sys_create_datetime', label: '时间', prop: 'sys_create_datetime', width: 180 },
  { key: 'operator_name', label: '操作人', prop: 'operator_name', width: 120 },
  { key: 'action_label', label: '动作', prop: 'action_label', width: 100 },
  { key: 'message', label: '说明', prop: 'message', minWidth: 220 },
  { key: 'duration', label: '时长', width: 100 },
];

export const detailDeviceColumns: ElementTableColumn[] = [
  { key: 'device_type_path', label: '设备类型', prop: 'device_type_path', minWidth: 180 },
  { key: 'device_name', label: '设备名称', prop: 'device_name', width: 140 },
  { key: 'asset_number', label: '资产编号', prop: 'asset_number', width: 150 },
  { key: 'remark', label: '备注', prop: 'remark', minWidth: 180 },
];
