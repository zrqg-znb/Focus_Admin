export type PermissionRequirement =
  | string
  | {
      allOf?: string[];
      anyOf?: string[];
    };

export const DEEPAUDIT_PAGE_CODES = {
  ACCOUNT: undefined,
  AGENT_AUDIT: 'deepaudit:agent-audit',
  DASHBOARD: 'deepaudit:dashboard',
  INSTANT_ANALYSIS: 'deepaudit:instant-analysis',
  PROJECTS: 'deepaudit:projects',
  PROMPTS: 'deepaudit:prompts',
  RECYCLE_BIN: 'deepaudit:recycle-bin',
  RULES: 'deepaudit:rules',
  SETTINGS: 'deepaudit:settings',
  TASKS: 'deepaudit:tasks',
} as const;

export const DEEPAUDIT_ACTION_CODES = {
  AGENT_TASKS_CANCEL: 'deepaudit:agent-tasks:cancel',
  AGENT_TASKS_CREATE: 'deepaudit:agent-tasks:create',
  ISSUES_UPDATE: 'deepaudit:issues:update',
  PROJECTS_CREATE: 'deepaudit:projects:create',
  PROJECTS_DELETE: 'deepaudit:projects:delete',
  PROJECTS_MEMBERS: 'deepaudit:projects:members',
  PROJECTS_RESTORE: 'deepaudit:projects:restore',
  PROJECTS_UPDATE: 'deepaudit:projects:update',
  PROMPTS_MANAGE: 'deepaudit:prompts:manage',
  REPORTS_EXPORT: 'deepaudit:reports:export',
  RULES_MANAGE: 'deepaudit:rules:manage',
  SETTINGS_SAVE: 'deepaudit:settings:save',
  TASKS_CANCEL: 'deepaudit:tasks:cancel',
  TASKS_CREATE: 'deepaudit:tasks:create',
} as const;

export function hasAllPermissions(accessCodes: string[], requiredCodes: string[]) {
  if (!requiredCodes.length) {
    return true;
  }
  const accessCodeSet = new Set(accessCodes);
  return requiredCodes.every((code) => accessCodeSet.has(code));
}

export function hasAnyPermission(accessCodes: string[], requiredCodes: string[]) {
  if (!requiredCodes.length) {
    return true;
  }
  const accessCodeSet = new Set(accessCodes);
  return requiredCodes.some((code) => accessCodeSet.has(code));
}

export function hasPermission(accessCodes: string[], requirement?: PermissionRequirement) {
  if (!requirement) {
    return true;
  }

  if (typeof requirement === 'string') {
    return accessCodes.includes(requirement);
  }

  const allOf = requirement.allOf || [];
  const anyOf = requirement.anyOf || [];

  if (allOf.length && !hasAllPermissions(accessCodes, allOf)) {
    return false;
  }

  if (anyOf.length) {
    return hasAnyPermission(accessCodes, anyOf);
  }

  return true;
}
