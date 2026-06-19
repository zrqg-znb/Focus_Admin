import type { EnvironmentItem } from '#/api/environment-management';
import type { ZqTableGridOptions } from '#/components/zq-table';

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

export function useEnvironmentUsageColumns(): ZqTableGridOptions<EnvironmentItem>['columns'] {
  return [
    { key: 'favorite', dataKey: 'favorite', title: '收藏', width: 64, align: 'center', headerAlign: 'center', showOverflowTooltip: false },
    { key: 'ip_address', dataKey: 'ip_address', title: 'IP地址', width: 140, align: 'center', headerAlign: 'center' },
    { key: 'secret', dataKey: 'secret', title: '账号密码', width: 160, align: 'center', headerAlign: 'center', showOverflowTooltip: false },
    { key: 'domain', dataKey: 'domain', title: '领域', width: 90, align: 'center', headerAlign: 'center', showOverflowTooltip: false },
    { key: 'category', dataKey: 'category', title: '分类', width: 90, align: 'center', headerAlign: 'center', showOverflowTooltip: false },
    { key: 'project_name', dataKey: 'project_name', title: '项目', width: 120, align: 'center', headerAlign: 'center', showOverflowTooltip: false },
    { key: 'vehicle_model', dataKey: 'vehicle_model', title: '车型', width: 120, align: 'center', headerAlign: 'center', showOverflowTooltip: false },
    { key: 'device_display', dataKey: 'device_display', title: '测试设备', width: 240, align: 'center', headerAlign: 'center', showOverflowTooltip: false },
    { key: 'config_description', dataKey: 'config_description', title: '配置情况', width: 220, align: 'center', headerAlign: 'center' },
    { key: 'occupy_state', dataKey: 'occupy_state', title: '占用情况', width: 150, align: 'center', headerAlign: 'center', showOverflowTooltip: false },
    { key: 'queue_state', dataKey: 'queue_state', title: '排队', width: 130, align: 'center', headerAlign: 'center', showOverflowTooltip: false },
    { key: 'shelf_location', dataKey: 'shelf_location', title: '货架位置', width: 130, align: 'center', headerAlign: 'center' },
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
