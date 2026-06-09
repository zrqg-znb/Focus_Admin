import { normalizeRepositoryType } from '@/shared/utils/projectUtils';

type JsonRecord = Record<string, any>;
type StoragePayload = {
  accessCodes: string[];
  accessToken: null | string;
  raw: JsonRecord | null;
  refreshToken: null | string;
  storage: null | Storage;
  storageKey: null | string;
};

const APP_BASE_URL_RAW = import.meta.env.BASE_URL || '/';
const API_BASE_URL_RAW = import.meta.env.VITE_API_BASE_URL || '/basic-api/api';

export const APP_BASE_URL = APP_BASE_URL_RAW.endsWith('/')
  ? APP_BASE_URL_RAW
  : `${APP_BASE_URL_RAW}/`;

export const APP_BASE_PATH =
  APP_BASE_URL === '/' ? '' : APP_BASE_URL.replace(/\/$/, '');

export const API_BASE_URL = API_BASE_URL_RAW.replace(/\/$/, '');

function safeJsonParse<T>(value: null | string): null | T {
  if (!value) {
    return null;
  }
  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
}

function normalizeAccessCodes(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .filter(
      (item): item is string => typeof item === 'string' && item.length > 0,
    )
    .filter((item, index, array) => array.indexOf(item) === index);
}

function getStorageTokens(storage: Storage): null | {
  accessCodes: string[];
  accessToken?: string;
  raw: JsonRecord | null;
  refreshToken?: string;
  storageKey?: string;
} {
  for (let index = 0; index < storage.length; index += 1) {
    const key = storage.key(index);
    if (!key || !key.includes('core-access')) {
      continue;
    }
    const parsed = safeJsonParse<JsonRecord>(storage.getItem(key));
    if (parsed && typeof parsed.accessToken === 'string') {
      return {
        accessCodes: normalizeAccessCodes(parsed.accessCodes),
        accessToken: parsed.accessToken,
        raw: parsed,
        refreshToken:
          typeof parsed.refreshToken === 'string'
            ? parsed.refreshToken
            : undefined,
        storageKey: key,
      };
    }
  }
  return null;
}

export function getStoredFocusAccess(): StoragePayload {
  const directAccessToken =
    localStorage.getItem('access_token') ||
    sessionStorage.getItem('access_token');
  const directRefreshToken =
    localStorage.getItem('refresh_token') ||
    sessionStorage.getItem('refresh_token');

  const localPayload = getStorageTokens(localStorage);
  if (localPayload) {
    return {
      accessCodes: localPayload.accessCodes,
      accessToken: localPayload.accessToken || directAccessToken || null,
      raw: localPayload.raw,
      refreshToken: localPayload.refreshToken || directRefreshToken || null,
      storage: localStorage,
      storageKey: localPayload.storageKey || 'core-access',
    };
  }

  const sessionPayload = getStorageTokens(sessionStorage);
  if (sessionPayload) {
    return {
      accessCodes: sessionPayload.accessCodes,
      accessToken: sessionPayload.accessToken || directAccessToken || null,
      raw: sessionPayload.raw,
      refreshToken: sessionPayload.refreshToken || directRefreshToken || null,
      storage: sessionStorage,
      storageKey: sessionPayload.storageKey || 'core-access',
    };
  }

  return {
    accessCodes: [],
    accessToken: directAccessToken,
    raw: null,
    refreshToken: directRefreshToken,
    storage: directAccessToken ? sessionStorage : null,
    storageKey: directAccessToken ? 'core-access' : null,
  };
}

export function getStoredToken(): null | string {
  return getStoredFocusAccess().accessToken;
}

export function getStoredRefreshToken(): null | string {
  return getStoredFocusAccess().refreshToken;
}

export function getStoredAccessCodes(): string[] {
  return getStoredFocusAccess().accessCodes;
}

export function persistStoredFocusAccess(
  patch: Partial<
    Pick<StoragePayload, 'accessCodes' | 'accessToken' | 'refreshToken'>
  >,
) {
  const current = getStoredFocusAccess();
  const storage = current.storage || localStorage;
  const storageKey = current.storageKey || 'core-access';
  const nextRaw = {
    ...current.raw,
    accessCodes: patch.accessCodes ?? current.accessCodes,
    accessToken: patch.accessToken ?? current.accessToken,
    refreshToken: patch.refreshToken ?? current.refreshToken,
  };
  storage.setItem(storageKey, JSON.stringify(nextRaw));

  const nextAccessToken = patch.accessToken ?? current.accessToken;
  const nextRefreshToken = patch.refreshToken ?? current.refreshToken;

  if (nextAccessToken) {
    storage.setItem('access_token', nextAccessToken);
  } else {
    localStorage.removeItem('access_token');
    sessionStorage.removeItem('access_token');
  }

  if (nextRefreshToken) {
    storage.setItem('refresh_token', nextRefreshToken);
  } else {
    localStorage.removeItem('refresh_token');
    sessionStorage.removeItem('refresh_token');
  }
}

export function clearStoredFocusAccess() {
  for (const storage of [localStorage, sessionStorage]) {
    const keysToRemove: string[] = [];
    for (let index = 0; index < storage.length; index += 1) {
      const key = storage.key(index);
      if (!key) {
        continue;
      }
      if (
        key.includes('core-access') ||
        key === 'access_token' ||
        key === 'refresh_token'
      ) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach((key) => storage.removeItem(key));
  }
}

export function buildAppUrl(path: string) {
  if (!path || path === '/') {
    return APP_BASE_URL;
  }
  const normalized = path.startsWith('/') ? path.slice(1) : path;
  return `${APP_BASE_URL}${normalized}`;
}

export function getCurrentAppPath() {
  if (typeof window === 'undefined') {
    return APP_BASE_URL;
  }

  const { hash, pathname, search } = window.location;
  const currentPath = `${pathname}${search}${hash}`;
  if (currentPath.startsWith(APP_BASE_PATH)) {
    return currentPath;
  }
  return buildAppUrl('/');
}

export function buildAssetUrl(asset: string) {
  return buildAppUrl(asset.startsWith('/') ? asset.slice(1) : asset);
}

function mapProjectPath(pathname: string) {
  if (/^\/projects\/deleted\/?$/.test(pathname)) {
    return '/deepaudit/projects/recycle-bin';
  }
  const purgeMatch = pathname.match(/^\/projects\/([^/]+)\/permanent\/?$/);
  if (purgeMatch) {
    return `/deepaudit/projects/${purgeMatch[1]}/purge`;
  }
  return `/deepaudit${pathname.replace(/\/$/, '') || '/projects'}`;
}

function mapTaskPath(pathname: string) {
  const reportMatch = pathname.match(/^\/tasks\/([^/]+)\/report\/pdf\/?$/);
  if (reportMatch) {
    return `/deepaudit/reports/tasks/${reportMatch[1]}/pdf`;
  }
  return `/deepaudit${pathname.replace(/\/$/, '') || '/tasks'}`;
}

function mapInstantPath(pathname: string) {
  const reportMatch = pathname.match(
    /^\/scan\/instant\/history\/([^/]+)\/report\/pdf\/?$/,
  );
  if (reportMatch) {
    return `/deepaudit/reports/instant/${reportMatch[1]}/pdf`;
  }
  return `/deepaudit${pathname.replace(/\/$/, '') || '/scan'}`;
}

function mapAgentTaskPath(pathname: string) {
  const reportMatch = pathname.match(/^\/agent-tasks\/([^/]+)\/report\/?$/);
  if (reportMatch) {
    return `/deepaudit/agent-tasks/${reportMatch[1]}/report`;
  }
  if (/^\/agent-tasks\/[^/]+\/events\/list\/?$/.test(pathname)) {
    return pathname
      .replace(/^\/agent-tasks/, '/deepaudit/agent-tasks')
      .replace(/\/events\/list\/?$/, '/events');
  }
  if (/^\/agent-tasks\/[^/]+\/agent-tree\/?$/.test(pathname)) {
    return pathname
      .replace(/^\/agent-tasks/, '/deepaudit/agent-tasks')
      .replace(/\/agent-tree\/?$/, '/tree');
  }
  return `/deepaudit${pathname.replace(/\/$/, '') || '/agent-tasks'}`;
}

function mapConfigPath(pathname: string) {
  if (pathname === '/config/me') {
    return '/deepaudit/settings/me';
  }
  if (pathname === '/config/defaults') {
    return pathname;
  }
  if (pathname === '/config/llm-providers') {
    return '/deepaudit/settings/me';
  }
  if (pathname === '/config/test-llm') {
    return '/deepaudit/settings/test-llm';
  }
  return pathname;
}

function normalizeOptionalTimestamp(value: unknown): null | number {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const timestamp = Number(value);
  return Number.isFinite(timestamp) && timestamp > 0 ? timestamp : null;
}

function mapDatabasePath(pathname: string) {
  if (/^\/database\/health\/?$/.test(pathname)) {
    return '/deepaudit/data-tools/health';
  }
  if (/^\/database\/stats\/?$/.test(pathname)) {
    return '/deepaudit/data-tools/stats';
  }
  if (/^\/database\/export\/?$/.test(pathname)) {
    return '/deepaudit/data-tools/export';
  }
  if (/^\/database\/import\/?$/.test(pathname)) {
    return '/deepaudit/data-tools/import';
  }
  if (/^\/database\/clear\/?$/.test(pathname)) {
    return '/deepaudit/data-tools/clear';
  }
  return pathname;
}

export function mapApiPath(path: string) {
  if (!path) {
    return path;
  }
  const [pathname, query = ''] = path.split('?');
  let mappedPath = pathname;

  switch (pathname) {
    case '/auth/login': {
      mappedPath = '/core/login';

      break;
    }
    case '/user/change-password': {
      mappedPath = '/core/user/change-password';

      break;
    }
    case '/users/me': {
      mappedPath = '/core/user/profile/me';

      break;
    }
    default: {
      if (pathname.startsWith('/projects')) {
        mappedPath = mapProjectPath(pathname);
      } else if (pathname.startsWith('/tasks')) {
        mappedPath = mapTaskPath(pathname);
      } else if (pathname.startsWith('/scan')) {
        mappedPath = mapInstantPath(pathname);
      } else if (pathname.startsWith('/agent-tasks')) {
        mappedPath = mapAgentTaskPath(pathname);
      } else if (pathname.startsWith('/rules')) {
        mappedPath = `/deepaudit${pathname.replace(/\/$/, '') || '/rules'}`;
      } else if (pathname.startsWith('/prompts')) {
        mappedPath = `/deepaudit${pathname.replace(/\/$/, '') || '/prompts'}`;
      } else if (pathname.startsWith('/scenarios')) {
        mappedPath = `/deepaudit${pathname.replace(/\/$/, '') || '/scenarios'}`;
      } else if (pathname.startsWith('/embedding')) {
        mappedPath = `/deepaudit${pathname.replace(/\/$/, '')}`;
      } else if (pathname.startsWith('/ssh-keys')) {
        mappedPath = `/deepaudit${pathname.replace(/\/$/, '')}`;
      } else if (pathname.startsWith('/config')) {
        mappedPath = mapConfigPath(pathname);
      } else if (pathname.startsWith('/database')) {
        mappedPath = mapDatabasePath(pathname);
      } else if (pathname === '/dashboard/overview') {
        mappedPath = '/deepaudit/dashboard/overview';
      }
    }
  }

  return query ? `${mappedPath}?${query}` : mappedPath;
}

export function resolveApiUrl(path: string) {
  const mapped = mapApiPath(path);
  const normalized = mapped.startsWith('/') ? mapped : `/${mapped}`;
  return `${API_BASE_URL}${normalized}`;
}

function normalizeName(raw: JsonRecord) {
  return raw.full_name || raw.name || raw.realName || raw.username || '';
}

export function normalizeProfile(raw: JsonRecord | null | undefined) {
  if (!raw) {
    return null;
  }
  const roles = Array.isArray(raw.roles) ? raw.roles : [];
  const role =
    raw.role ||
    raw.user_role ||
    (raw.is_superuser || roles.includes('admin') || roles.includes('superadmin')
      ? 'admin'
      : 'member');
  return {
    id: String(raw.id || ''),
    username: raw.username || '',
    email: raw.email || '',
    phone: raw.phone || raw.mobile || '',
    full_name: normalizeName(raw),
    avatar_url: raw.avatar_url || raw.avatar || '',
    role,
    github_username: raw.github_username || '',
    gitlab_username: raw.gitlab_username || '',
    created_at: raw.created_at || raw.sys_create_datetime || '',
    updated_at: raw.updated_at || raw.sys_update_datetime || '',
  };
}

function normalizeLanguages(value: any) {
  if (Array.isArray(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = safeJsonParse<string[]>(value);
    if (Array.isArray(parsed)) {
      return parsed;
    }
  }
  return [];
}

export function normalizeProject(raw: JsonRecord | null | undefined) {
  if (!raw) {
    return null;
  }
  const languages = normalizeLanguages(raw.programming_languages);
  const repositoryType = normalizeRepositoryType(raw.repository_type);
  return {
    id: String(raw.id || ''),
    name: raw.name || '',
    description: raw.description || '',
    source_type: raw.source_type || 'repository',
    repository_url: raw.repository_url || '',
    repository_type: repositoryType,
    default_branch: raw.default_branch || 'main',
    manifest_xml: raw.manifest_xml || '',
    group: raw.group || '',
    programming_languages: JSON.stringify(languages),
    owner_id: raw.owner_id || raw.owner?.id || '',
    is_active: raw.is_active !== false,
    created_at: raw.created_at || raw.sys_create_datetime || '',
    updated_at: raw.updated_at || raw.sys_update_datetime || '',
    owner: raw.owner
      ? {
          ...normalizeProfile(raw.owner),
          id: String(raw.owner.id || ''),
          full_name: raw.owner.name || raw.owner.username || '',
        }
      : undefined,
    members_count: raw.members_count || raw.members?.length || 0,
    zip_meta: raw.zip_meta ? normalizeZipMeta(raw.zip_meta) : undefined,
  };
}

export function normalizeZipMeta(raw: JsonRecord | null | undefined) {
  if (!raw) {
    return { has_file: false };
  }
  return {
    has_file: Boolean(raw.has_file),
    original_filename: raw.original_filename || raw.display_name || '',
    file_size: raw.file_size ?? raw.size ?? 0,
    uploaded_at: raw.uploaded_at || '',
  };
}

export function normalizeAuditTask(raw: JsonRecord | null | undefined) {
  if (!raw) {
    return null;
  }
  const repositoryType = normalizeRepositoryType(
    raw.repository_type || raw.project?.repository_type,
  );
  const project = raw.project
    ? normalizeProject(raw.project)
    : {
        id: String(raw.project_id || ''),
        name: raw.project_name || '',
        description: '',
        source_type: 'repository',
        repository_url: '',
        repository_type: repositoryType,
        default_branch: raw.branch_name || 'main',
        manifest_xml: raw.manifest_xml || '',
        group: raw.group || '',
        programming_languages: JSON.stringify([]),
        owner_id: '',
        is_active: true,
        created_at: '',
        updated_at: '',
      };
  return {
    id: String(raw.id || ''),
    project_id: String(raw.project_id || ''),
    task_type: raw.task_type || 'repository',
    status: raw.status || 'pending',
    repository_url: raw.repository_url || raw.project?.repository_url || '',
    repository_type: repositoryType,
    repository_signature: raw.repository_signature || '',
    branch_name: raw.branch_name || 'main',
    manifest_xml: raw.manifest_xml || '',
    group: raw.group || '',
    exclude_patterns: JSON.stringify(raw.exclude_patterns || []),
    scan_config: JSON.stringify(raw.scan_config || {}),
    total_files: raw.total_files || 0,
    scanned_files: raw.scanned_files || 0,
    total_lines: raw.total_lines || 0,
    issues_count: raw.issues_count || 0,
    quality_score: raw.quality_score || 0,
    selected_target_count: raw.selected_target_count || 0,
    selected_directory_count: raw.selected_directory_count || 0,
    resolved_file_count: raw.resolved_file_count || 0,
    inventory_report:
      raw.inventory_report && typeof raw.inventory_report === 'object'
        ? raw.inventory_report
        : {},
    inventory_items_count: Number(raw.inventory_items_count || 0),
    workspace_source: raw.workspace_source || '',
    started_at: raw.started_at || null,
    completed_at: raw.completed_at || null,
    created_by: raw.created_by || '',
    created_at: raw.created_at || raw.sys_create_datetime || '',
    project,
    creator: undefined,
  };
}

export function normalizeAuditIssue(raw: JsonRecord | null | undefined) {
  if (!raw) {
    return null;
  }
  const aiExplanation =
    typeof raw.ai_explanation === 'string'
      ? raw.ai_explanation
      : JSON.stringify(raw.ai_explanation || {});
  return {
    id: String(raw.id || ''),
    task_id: String(raw.task_id || ''),
    file_path: raw.file_path || '',
    line_number: raw.line_number ?? null,
    column_number: raw.column_number ?? null,
    issue_type: raw.issue_type || 'security',
    severity: raw.severity || 'medium',
    title: raw.title || '',
    description: raw.description || raw.message || '',
    suggestion: raw.suggestion || '',
    code_snippet: raw.code_snippet || '',
    ai_explanation: aiExplanation,
    status: raw.status || 'open',
    resolved_by: raw.resolved_by || null,
    resolved_at: raw.resolved_at || null,
    created_at: raw.created_at || raw.sys_create_datetime || '',
  };
}

export function normalizeInstantRecord(raw: JsonRecord | null | undefined) {
  if (!raw) {
    return null;
  }
  const analysisResult = raw.analysis_result || {};
  return {
    id: String(raw.id || ''),
    user_id: String(raw.user_id || ''),
    language: raw.language || 'python',
    code_content: raw.code_content || '',
    analysis_result: JSON.stringify(analysisResult),
    issues_count: raw.issues_count || 0,
    quality_score: raw.quality_score || 0,
    analysis_time: raw.analysis_time || 0,
    created_at: raw.created_at || raw.sys_create_datetime || '',
  };
}

export function normalizeCodeAnalysisResult(
  raw: JsonRecord | null | undefined,
) {
  if (!raw) {
    return {
      analysis_id: null,
      analysis_time: 0,
      issues: [],
      quality_score: 0,
    };
  }
  const result = raw.analysis_result || raw;
  const issues = Array.isArray(result.issues)
    ? result.issues.map((issue: JsonRecord) => {
        const issueType =
          issue.issue_type ||
          issue.type ||
          issue.vulnerability_type ||
          'security';
        return {
          ...issue,
          type: issue.type || issueType,
          issue_type: issue.issue_type || issueType,
          cwe_id:
            issue.cwe_id ||
            issue.ai_explanation?.cwe_id ||
            issue.ai_explanation?.verification?.cwe_id,
          verification_status:
            issue.verification_status ||
            issue.ai_explanation?.verification_status,
        };
      })
    : [];
  return {
    ...result,
    analysis_id: raw.id || result.analysis_id || null,
    analysis_time: raw.analysis_time || result.analysis_time || 0,
    issues,
    quality_score: result.quality_score || raw.quality_score || 0,
    analysis_profile: result.analysis_profile || {},
  };
}

export function normalizeAgentTask(raw: JsonRecord | null | undefined) {
  if (!raw) {
    return null;
  }
  const repositoryType = normalizeRepositoryType(
    raw.repository_type || raw.project?.repository_type,
  );
  return {
    ...raw,
    id: String(raw.id || ''),
    project_id: String(raw.project_id || ''),
    project_name: raw.project_name || '',
    created_at: raw.created_at || raw.sys_create_datetime || '',
    updated_at: raw.updated_at || raw.sys_update_datetime || '',
    started_at: raw.started_at || null,
    completed_at: raw.completed_at || null,
    branch_name: raw.branch_name || raw.project?.default_branch || 'main',
    repository_signature: raw.repository_signature || '',
    manifest_xml: raw.manifest_xml || raw.project?.manifest_xml || '',
    group: raw.group || raw.project?.group || '',
    selected_target_count: raw.selected_target_count || 0,
    selected_directory_count: raw.selected_directory_count || 0,
    resolved_file_count: raw.resolved_file_count || 0,
    workspace_source: raw.workspace_source || '',
    workspace_path: raw.workspace_path || raw.workspace || '',
    cache_repo: raw.cache_repo || raw.cache_path || '',
    last_synced_at: normalizeOptionalTimestamp(raw.last_synced_at),
    project: {
      id: String(raw.project_id || ''),
      name: raw.project_name || '',
      description: '',
      source_type: 'repository',
      repository_url: '',
      repository_type: repositoryType,
      default_branch: raw.branch_name || 'main',
      manifest_xml: raw.manifest_xml || '',
      group: raw.group || '',
      programming_languages: JSON.stringify([]),
      owner_id: '',
      is_active: true,
      created_at: '',
      updated_at: '',
    },
  };
}

export function normalizeAgentFinding(raw: JsonRecord | null | undefined) {
  if (!raw) {
    return null;
  }
  return {
    ...raw,
    id: String(raw.id || ''),
    task_id: String(raw.task_id || ''),
    created_at: raw.created_at || raw.sys_create_datetime || '',
    poc_code: raw.poc?.code || null,
    has_poc: Boolean(raw.poc?.code),
    ai_confidence: raw.ai_confidence || 0,
  };
}

export function normalizeAgentEvent(raw: JsonRecord | null | undefined) {
  if (!raw) {
    return null;
  }
  return {
    ...raw,
    id: String(raw.id || ''),
    task_id: String(raw.task_id || ''),
    metadata: raw.metadata || raw.event_metadata || {},
    timestamp: raw.timestamp || raw.sys_create_datetime || '',
  };
}

export function normalizeUserConfig(raw: JsonRecord | null | undefined) {
  const payload = raw || {};
  const llm = payload.llmConfig || payload.llm_config || {};
  const other = payload.otherConfig || payload.other_config || {};
  const scanConfig = other.scanConfig || other.scan_config || {};
  return {
    id: payload.id || payload.user_id || 'me',
    user_id: payload.user_id || '',
    llmConfig: {
      llmProvider: llm.llmProvider || llm.provider || 'openai',
      llmApiKey: llm.llmApiKey || llm.apiKey || llm.api_key || '',
      llmModel: llm.llmModel || llm.model || '',
      llmBaseUrl: llm.llmBaseUrl || llm.baseUrl || llm.base_url || '',
      llmTimeout: (llm.llmTimeout || llm.timeout || 150) * 1000,
      llmTemperature: llm.llmTemperature ?? llm.temperature ?? 0.1,
      llmMaxTokens: llm.llmMaxTokens || llm.maxTokens || llm.max_tokens || 4096,
      llmFirstTokenTimeout:
        llm.llmFirstTokenTimeout ||
        llm.firstTokenTimeout ||
        llm.first_token_timeout ||
        90,
      llmStreamTimeout:
        llm.llmStreamTimeout || llm.streamTimeout || llm.stream_timeout || 60,
      toolTimeout: llm.toolTimeout || llm.tool_timeout || 60,
      subAgentTimeout: llm.subAgentTimeout || llm.sub_agent_timeout || 600,
      agentTimeout: llm.agentTimeout || llm.agent_timeout || 1800,
    },
    otherConfig: {
      codehubToken:
        other.codehubToken ||
        other.codehub_token ||
        other.githubToken ||
        other.github_token ||
        other.gitlabToken ||
        other.gitlab_token ||
        other.giteaToken ||
        other.gitea_token ||
        '',
      maxAnalyzeFiles:
        scanConfig.maxAnalyzeFiles ?? scanConfig.max_analyze_files ?? 0,
      llmConcurrency:
        scanConfig.llmConcurrency || scanConfig.llm_concurrency || 3,
      llmGapMs: scanConfig.llmGapMs || scanConfig.llm_gap_ms || 500,
      outputLanguage: other.outputLanguage || other.output_language || 'zh-CN',
    },
    created_at: payload.created_at || payload.sys_create_datetime || '',
    updated_at: payload.updated_at || payload.sys_update_datetime || '',
  };
}
