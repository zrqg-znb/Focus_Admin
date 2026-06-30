export interface RequirementHeaderFilterOption {
  disabled?: boolean;
  label: string;
  value: string;
}

export type RequirementHeaderFilterType =
  | 'checkbox'
  | 'date-range'
  | 'input'
  | 'radio';

export interface RequirementHeaderFilterConfig {
  columnKey: string;
  field: string;
  label: string;
  placeholder?: string;
  type: RequirementHeaderFilterType;
}

export function hasRequirementHeaderFilterValue(value: any) {
  if (Array.isArray(value)) return value.length > 0;
  return value !== undefined && value !== null && String(value).trim() !== '';
}
