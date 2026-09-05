import type {
  GovernanceLink,
  GovernanceProject,
  GovernanceResponsibility,
  UserOption,
} from '#/api/agent-tools/code-quality-governance';

export type Section = 'audit' | 'config' | 'dashboard' | 'findings';

export type ConfigTab = 'links' | 'projects' | 'responsibilities' | 'upload';

export type AuditTab = 'my_apply' | 'my_audit';

export interface ProjectFormState {
  branch: string;
  code: string;
  description: string;
  is_active: boolean;
  name: string;
  repository: string;
}

export interface ResponsibilityFormState {
  approver_ids: string[];
  code: string;
  description: string;
  is_active: boolean;
  name: string;
  owner_id: string;
}

export interface LinkFormState {
  is_active: boolean;
  project_id: string;
  remark: string;
  responsibility_id: string;
}

export interface UploadFormState {
  project_id: string;
  responsibility_id: string;
  tool_name: string;
}

export interface FindingFilters {
  keyword: string;
  project_id: string;
  responsibility_id: string;
  severity: string;
  shield_status: string;
  tool_name: string;
}

export interface ScopeOptions {
  links: GovernanceLink[];
  projects: GovernanceProject[];
  responsibilities: GovernanceResponsibility[];
  users: UserOption[];
}
