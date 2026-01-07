export interface MilestoneConfig {
  key: string;
  label: string;
  color: string;
}

export interface GanttColumn {
  field: string;
  title: string;
  width: number;
  slot?: string;
}
