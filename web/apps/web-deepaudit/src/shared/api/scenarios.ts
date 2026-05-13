import { apiClient } from './serverClient';

export type ScenarioObjectiveType = 'audit' | 'inventory';

export interface ScenarioProfile {
  id: string;
  scenario_key: string;
  name: string;
  description?: string;
  objective_type: ScenarioObjectiveType;
  prompt_template_id?: string | null;
  prompt_template_name?: string | null;
  rule_set_id?: string | null;
  rule_set_name?: string | null;
  knowledge_modules: string[];
  knowledge_modules_count: number;
  target_vulnerabilities: string[];
  focus_keywords: string[];
  tool_policy: Record<string, unknown>;
  is_default: boolean;
  is_system: boolean;
  is_active: boolean;
  created_by?: string | null;
  sys_create_datetime?: string | null;
  sys_update_datetime?: string | null;
}

export interface ScenarioProfileListResponse {
  items: ScenarioProfile[];
  total: number;
}

export interface ScenarioProfileCreate {
  scenario_key: string;
  name: string;
  description?: string;
  objective_type: ScenarioObjectiveType;
  prompt_template_id?: string | null;
  rule_set_id?: string | null;
  knowledge_modules?: string[];
  is_active?: boolean;
}

export interface ScenarioProfileUpdate {
  name?: string;
  description?: string;
  objective_type?: ScenarioObjectiveType;
  prompt_template_id?: string | null;
  rule_set_id?: string | null;
  knowledge_modules?: string[];
  is_active?: boolean;
  is_default?: boolean;
}

export interface ScenarioProfileCopyPayload {
  scenario_key?: string;
  name?: string;
  description?: string;
}

export const BUILTIN_SCENARIO_FALLBACKS: ScenarioProfile[] = [
  {
    id: 'builtin-general',
    scenario_key: 'general',
    name: '通用审计',
    description: '使用通用安全审计逻辑，输出漏洞发现与修复建议。',
    objective_type: 'audit',
    prompt_template_id: null,
    prompt_template_name: '默认代码审计',
    rule_set_id: null,
    rule_set_name: '内置安全规则集',
    knowledge_modules: [],
    knowledge_modules_count: 0,
    target_vulnerabilities: [],
    focus_keywords: [],
    tool_policy: {},
    is_default: true,
    is_system: true,
    is_active: true,
    created_by: null,
    sys_create_datetime: null,
    sys_update_datetime: null,
  },
  {
    id: 'builtin-concurrency',
    scenario_key: 'concurrency',
    name: '并发资源代码梳理',
    description: '聚焦锁、信号量、共享状态、ISR/DMA 等并发资源相关代码。',
    objective_type: 'inventory',
    prompt_template_id: null,
    prompt_template_name: '场景 A - 并发资源代码梳理',
    rule_set_id: null,
    rule_set_name: '场景 A - 并发资源访问规则集',
    knowledge_modules: ['race_condition', 'deadlock', 'embedded_concurrency'],
    knowledge_modules_count: 3,
    target_vulnerabilities: ['race_condition', 'deadlock', 'embedded_concurrency'],
    focus_keywords: ['pthread_', 'mutex', 'sem_', 'critical', 'ISR', 'DMA'],
    tool_policy: {},
    is_default: false,
    is_system: true,
    is_active: true,
    created_by: null,
    sys_create_datetime: null,
    sys_update_datetime: null,
  },
  {
    id: 'builtin-api-chain',
    scenario_key: 'api_chain',
    name: '高危 API 调用链梳理',
    description: '聚焦 strcpy/malloc/free/printf 等高危 API 相关调用链。',
    objective_type: 'inventory',
    prompt_template_id: null,
    prompt_template_name: '场景 B - 高危 API 调用链梳理',
    rule_set_id: null,
    rule_set_name: '场景 B - 高危 API 调用链规则集',
    knowledge_modules: ['buffer_overflow', 'use_after_free', 'resource_leak', 'format_string'],
    knowledge_modules_count: 4,
    target_vulnerabilities: ['buffer_overflow', 'use_after_free', 'resource_leak', 'format_string'],
    focus_keywords: ['strcpy', 'sprintf', 'memcpy', 'malloc', 'free', 'printf'],
    tool_policy: {},
    is_default: false,
    is_system: true,
    is_active: true,
    created_by: null,
    sys_create_datetime: null,
    sys_update_datetime: null,
  },
];

function normalizeScenarioProfile(item: any): ScenarioProfile {
  return {
    id: String(item?.id || ''),
    scenario_key: String(item?.scenario_key || ''),
    name: String(item?.name || ''),
    description: item?.description ? String(item.description) : '',
    objective_type: item?.objective_type === 'inventory' ? 'inventory' : 'audit',
    prompt_template_id: item?.prompt_template_id ? String(item.prompt_template_id) : null,
    prompt_template_name: item?.prompt_template_name ? String(item.prompt_template_name) : null,
    rule_set_id: item?.rule_set_id ? String(item.rule_set_id) : null,
    rule_set_name: item?.rule_set_name ? String(item.rule_set_name) : null,
    knowledge_modules: Array.isArray(item?.knowledge_modules)
      ? item.knowledge_modules.map((entry: unknown) => String(entry))
      : [],
    knowledge_modules_count: Number(item?.knowledge_modules_count || 0),
    target_vulnerabilities: Array.isArray(item?.target_vulnerabilities)
      ? item.target_vulnerabilities.map((entry: unknown) => String(entry))
      : [],
    focus_keywords: Array.isArray(item?.focus_keywords)
      ? item.focus_keywords.map((entry: unknown) => String(entry))
      : [],
    tool_policy:
      item?.tool_policy && typeof item.tool_policy === 'object'
        ? item.tool_policy
        : {},
    is_default: Boolean(item?.is_default),
    is_system: Boolean(item?.is_system),
    is_active: Boolean(item?.is_active),
    created_by: item?.created_by ? String(item.created_by) : null,
    sys_create_datetime: item?.sys_create_datetime
      ? String(item.sys_create_datetime)
      : null,
    sys_update_datetime: item?.sys_update_datetime
      ? String(item.sys_update_datetime)
      : null,
  };
}

export async function getScenarioProfiles(params?: {
  keyword?: string;
  objective_type?: ScenarioObjectiveType;
  is_active?: boolean;
  page?: number;
  pageSize?: number;
}): Promise<ScenarioProfileListResponse> {
  const response = await apiClient.get('/scenarios', { params });
  const items = Array.isArray(response.data?.items) ? response.data.items : [];
  return {
    items: items.map(normalizeScenarioProfile),
    total: Number(response.data?.total || items.length),
  };
}

export async function getScenarioProfile(id: string): Promise<ScenarioProfile> {
  const response = await apiClient.get(`/scenarios/${id}`);
  return normalizeScenarioProfile(response.data);
}

export async function createScenarioProfile(
  payload: ScenarioProfileCreate,
): Promise<ScenarioProfile> {
  const response = await apiClient.post('/scenarios', payload);
  return normalizeScenarioProfile(response.data);
}

export async function updateScenarioProfile(
  id: string,
  payload: ScenarioProfileUpdate,
): Promise<ScenarioProfile> {
  const response = await apiClient.put(`/scenarios/${id}`, payload);
  return normalizeScenarioProfile(response.data);
}

export async function copyScenarioProfile(
  id: string,
  payload: ScenarioProfileCopyPayload,
): Promise<ScenarioProfile> {
  const response = await apiClient.post(`/scenarios/${id}/copy`, payload);
  return normalizeScenarioProfile(response.data);
}

export async function deleteScenarioProfile(id: string): Promise<void> {
  await apiClient.delete(`/scenarios/${id}`);
}

export async function setDefaultScenarioProfile(id: string): Promise<void> {
  await apiClient.post(`/scenarios/${id}/set-default`);
}
