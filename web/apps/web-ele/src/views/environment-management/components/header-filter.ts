export interface HeaderFilterOption {
  children?: HeaderFilterOption[];
  disabled?: boolean;
  label: string;
  value: string;
}

export type HeaderFilterType = 'cascader' | 'checkbox' | 'date-range' | 'input' | 'radio';

export interface HeaderFilterConfig {
  columnKey: string;
  endField?: string;
  field: string;
  label: string;
  optionKey?: keyof EnvironmentFilterOptions;
  placeholder?: string;
  type: HeaderFilterType;
}

export interface EnvironmentFilterOptions {
  binding_device_assets: HeaderFilterOption[];
  categories: HeaderFilterOption[];
  current_users: HeaderFilterOption[];
  device_statuses: HeaderFilterOption[];
  device_types: HeaderFilterOption[];
  device_options: HeaderFilterOption[];
  devices: HeaderFilterOption[];
  domains: HeaderFilterOption[];
  favorite_states: HeaderFilterOption[];
  projects: HeaderFilterOption[];
  queue_states: HeaderFilterOption[];
  statuses: HeaderFilterOption[];
  vehicle_models: HeaderFilterOption[];
}

export type HeaderFilterValues = Record<string, any>;

export function hasHeaderFilterValue(value: any) {
  if (Array.isArray(value)) return value.length > 0;
  return value !== undefined && value !== null && String(value).trim() !== '';
}

export function countActiveHeaderFilters(values: HeaderFilterValues) {
  return Object.values(values).filter(hasHeaderFilterValue).length;
}

export function buildHeaderFilterParams(
  configs: HeaderFilterConfig[],
  values: HeaderFilterValues,
) {
  const params: Record<string, any> = {};
  for (const config of configs) {
    const value = values[config.columnKey];
    if (!hasHeaderFilterValue(value)) continue;
    if (config.type === 'date-range') {
      const [start, end] = Array.isArray(value) ? value : [];
      if (start) params[config.field] = start;
      if (end && config.endField) params[config.endField] = end;
      continue;
    }
    params[config.field] = Array.isArray(value) ? value.join(',') : value;
  }
  return params;
}
