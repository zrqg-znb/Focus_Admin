import type {
  GovernanceProject,
  GovernanceResponsibility,
  UserOption,
} from '#/api/agent-tools/code-quality-governance';

export type Section =
  | 'audit'
  | 'findings'
  | 'matrix'
  | 'projects'
  | 'responsibilities'
  | 'scan'
  | 'workbench';

export interface PageOptions {
  projects: GovernanceProject[];
  responsibilities: GovernanceResponsibility[];
  users: UserOption[];
  refreshOptions: () => Promise<void>;
}

export interface FindingFilters {
  keyword: string;
  project_id: string;
  responsibility_id: string;
  severity: string;
  shield_status: string;
  tool_name: string;
}
