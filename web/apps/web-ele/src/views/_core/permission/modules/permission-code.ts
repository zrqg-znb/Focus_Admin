const CODE_MAX_LENGTH = 128;

const ACTION_ALIASES: Record<string, string> = {
  bind: 'bind',
  cancel: 'cancel',
  checkpoints: 'checkpoints',
  clear: 'clear',
  close: 'close',
  debug: 'debug',
  detail: 'detail',
  draft: 'draft',
  events: 'events',
  export: 'export',
  failure_modes: 'failure_modes',
  findings: 'findings',
  history: 'history',
  import: 'import',
  issues: 'issues',
  logs: 'logs',
  options: 'options',
  purge: 'purge',
  query: 'query',
  quick_create: 'quick_create',
  reassign: 'reassign',
  rebuild: 'rebuild',
  recall: 'recall',
  reject: 'reject',
  reset: 'reset',
  restore: 'restore',
  resume: 'resume',
  save: 'save',
  search: 'query',
  set_default: 'set_default',
  stats: 'stats',
  status: 'status',
  submit: 'submit',
  summary: 'summary',
  test: 'test',
  toggle: 'toggle',
  tree: 'tree',
  update: 'update',
  upload: 'upload',
  validate: 'validate',
  zip: 'zip',
};

function sanitizeCodeSegment(value: string) {
  let text = String(value || '')
    .trim()
    .toLowerCase();
  if (!text) {
    return '';
  }
  text = text.replaceAll('-', '_').replaceAll('.', '_').replaceAll(' ', '_');
  if (text.startsWith(':')) {
    text = `by_${text.slice(1)}`;
  }
  if (text.startsWith('{') && text.endsWith('}')) {
    text = `by_${text.slice(1, -1)}`;
  }
  text = text.replaceAll(/[^a-z0-9_]+/g, '_');
  text = text.replaceAll(/_+/g, '_').replaceAll(/^_+|_+$/g, '');
  return text;
}

function isPathParameter(segment: string) {
  const text = String(segment || '').trim();
  return text.startsWith(':') || (text.startsWith('{') && text.endsWith('}'));
}

function splitApiPath(path: string) {
  const parts = String(path || '')
    .split('/')
    .filter(Boolean);
  if (parts[0] === 'api') {
    return parts.slice(1);
  }
  return parts;
}

function resolveOperation(path: string, method: string) {
  const parts = splitApiPath(path);
  const staticParts = parts
    .filter((item) => !isPathParameter(item))
    .map((item) => sanitizeCodeSegment(item))
    .filter(Boolean);
  const lastRaw = parts.at(-1) || '';
  const lastStatic = staticParts.at(-1) || '';
  const upperMethod = String(method || 'GET').toUpperCase();

  if (upperMethod === 'GET') {
    if (isPathParameter(lastRaw)) {
      return 'detail';
    }
    return ACTION_ALIASES[lastStatic] || 'read';
  }
  if (upperMethod === 'POST') {
    if (
      parts.length > 0 &&
      !isPathParameter(lastRaw) &&
      staticParts.length > 1
    ) {
      return ACTION_ALIASES[lastStatic] || 'create';
    }
    return 'create';
  }
  if (upperMethod === 'PUT' || upperMethod === 'PATCH') {
    if (
      parts.length > 0 &&
      !isPathParameter(lastRaw) &&
      staticParts.length > 1
    ) {
      const action = ACTION_ALIASES[lastStatic] || lastStatic || 'update';
      return action === 'update' ? 'update' : `update_${action}`;
    }
    return 'update';
  }
  if (upperMethod === 'DELETE') {
    if (
      parts.length > 0 &&
      !isPathParameter(lastRaw) &&
      staticParts.length > 1
    ) {
      const action = ACTION_ALIASES[lastStatic] || lastStatic || 'delete';
      return action === 'delete' ? 'delete' : `delete_${action}`;
    }
    return 'delete';
  }
  return 'access';
}

function shortenCode(code: string, path: string, method: string) {
  if (code.length <= CODE_MAX_LENGTH) {
    return code;
  }

  const parts = splitApiPath(path);
  const staticParts = parts
    .filter((item) => !isPathParameter(item))
    .map((item) => sanitizeCodeSegment(item))
    .filter(Boolean);
  const domain = staticParts[0] || 'api';
  const operation = resolveOperation(path, method);
  const context = staticParts
    .slice(1)
    .map((item) => item.slice(0, 8))
    .join('_');
  const compactCode = [domain, context, operation].filter(Boolean).join(':');
  if (compactCode.length <= CODE_MAX_LENGTH) {
    return compactCode;
  }

  const digestBase = `${method}:${path}`;
  let hash = 0;
  for (const char of digestBase) {
    hash = (hash * 33 + (char.codePointAt(0) || 0)) >>> 0;
  }
  const shortHash = hash.toString(16).slice(0, 8);
  const fallback = [domain, operation, shortHash].filter(Boolean).join(':');
  return fallback.slice(0, CODE_MAX_LENGTH);
}

export function buildPermissionCode(path: string, method: string) {
  const parts = splitApiPath(path);
  const staticParts = parts
    .filter((item) => !isPathParameter(item))
    .map((item) => sanitizeCodeSegment(item))
    .filter(Boolean);
  const domain = staticParts[0] || 'api';
  const operation = resolveOperation(path, method);
  let contextParts = staticParts.slice(1);
  if (
    contextParts.length > 0 &&
    (ACTION_ALIASES[contextParts.at(-1) || ''] || contextParts.at(-1)) ===
      operation
  ) {
    contextParts = contextParts.slice(0, -1);
  }
  const code = [domain, contextParts.join('_'), operation]
    .filter(Boolean)
    .join(':');
  return shortenCode(code, path, method);
}

export function buildPermissionCodeWithHash(path: string, method: string) {
  const baseCode = buildPermissionCode(path, method);
  const digestBase = `${method}:${path}`;
  let hash = 0;
  for (const char of digestBase) {
    hash = (hash * 33 + (char.codePointAt(0) || 0)) >>> 0;
  }
  const shortHash = hash.toString(16).slice(0, 6);
  return shortenCode(`${baseCode}:${shortHash}`, path, method);
}
