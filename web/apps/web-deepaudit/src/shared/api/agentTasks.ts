/**
 * Agent Tasks API
 * Agent 审计任务相关的 API 调用
 */

import {
  getStoredToken,
  normalizeAgentEvent,
  normalizeAgentFinding,
  normalizeAgentTask,
  resolveApiUrl,
} from './focusAdapter';
import { apiClient } from './serverClient';

// ============ Types ============

export interface AgentTask {
  id: string;
  project_id: string;
  name: null | string;
  description: null | string;
  task_type: string;
  status: string;
  current_phase: null | string;
  current_step: null | string;

  // 统计
  total_files: number;
  indexed_files: number;
  analyzed_files: number;
  files_with_findings: number; // 有漏洞发现的文件数
  total_chunks: number;
  findings_count: number;
  verified_count: number;
  false_positive_count: number;

  // Agent 统计
  total_iterations: number;
  tool_calls_count: number;
  tokens_used: number;

  // 严重程度统计
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;

  // 评分
  quality_score: number;
  security_score: null | number;

  // 时间
  created_at: string;
  started_at: null | string;
  completed_at: null | string;
  repository_type?: 'multi' | 'single';
  repository_url?: null | string;
  branch_name?: null | string;
  manifest_xml?: null | string;
  group?: null | string;

  // 进度
  progress_percentage: number;

  // 配置
  audit_scope: null | Record<string, unknown>;
  target_vulnerabilities: null | string[];
  verification_level: null | string;
  exclude_patterns: null | string[];
  target_files: null | string[];
  selected_target_count?: number;
  selected_directory_count?: number;
  resolved_file_count?: number;
  workspace_source?: null | string;

  // 错误信息
  error_message: null | string;
}

export interface AgentFinding {
  id: string;
  task_id: string;
  vulnerability_type: string;
  severity: string;
  title: string;
  description: null | string;

  file_path: null | string;
  line_start: null | number;
  line_end: null | number;
  code_snippet: null | string;

  status: string;
  is_verified: boolean;
  has_poc: boolean;
  poc_code: null | string;

  suggestion: null | string;
  fix_code: null | string;
  ai_explanation: null | string;
  ai_confidence: null | number;

  created_at: string;
}

export interface AgentEvent {
  id: string;
  task_id: string;
  event_type: string;
  phase: null | string;
  message: null | string;
  tool_name: null | string;
  tool_input?: Record<string, unknown>;
  tool_output?: Record<string, unknown>;
  tool_duration_ms: null | number;
  finding_id: null | string;
  tokens_used?: number;
  metadata?: Record<string, unknown>;
  sequence: number;
  timestamp: string;
}

export interface CreateAgentTaskRequest {
  project_id: string;
  name?: string;
  description?: string;
  audit_scope?: Record<string, unknown>;
  target_vulnerabilities?: string[];
  verification_level?: 'analysis_only' | 'generate_poc' | 'sandbox';
  repository_url?: string;
  repository_type?: 'multi' | 'single';
  branch_name?: string;
  manifest_xml?: string;
  group?: string;
  exclude_patterns?: string[];
  target_files?: string[];
  max_iterations?: number;
  token_budget?: number;
  timeout_seconds?: number;
}

export interface AgentTaskSummary {
  task_id: string;
  status: string;
  progress_percentage: number;
  security_score: number;
  quality_score: number;
  statistics: {
    analyzed_files: number;
    false_positive_count: number;
    files_with_findings: number;
    findings_count: number;
    indexed_files: number;
    total_chunks: number;
    total_files: number;
    verified_count: number;
  };
  severity_distribution: {
    critical: number;
    high: number;
    low: number;
    medium: number;
  };
  vulnerability_types: Record<string, { total: number; verified: number }>;
  duration_seconds: null | number;
}

// ============ API Functions ============

/**
 * 创建 Agent 审计任务
 */
export async function createAgentTask(
  data: CreateAgentTaskRequest,
): Promise<AgentTask> {
  const response = await apiClient.post('/agent-tasks/', data);
  return normalizeAgentTask(response.data) as unknown as AgentTask;
}

/**
 * 获取 Agent 任务列表
 */
export async function getAgentTasks(params?: {
  limit?: number;
  project_id?: string;
  skip?: number;
  status?: string;
}): Promise<AgentTask[]> {
  const response = await apiClient.get('/agent-tasks/', {
    params: {
      project_id: params?.project_id,
      status: params?.status,
      page:
        params?.skip !== undefined && params?.skip !== null && params?.limit
          ? Math.floor(params.skip / params.limit) + 1
          : undefined,
      pageSize: params?.limit,
    },
  });
  const items = Array.isArray(response.data)
    ? response.data
    : response.data?.items;
  return Array.isArray(items)
    ? items.map((item: any) => normalizeAgentTask(item) as unknown as AgentTask)
    : [];
}

/**
 * 获取 Agent 任务详情
 */
export async function getAgentTask(taskId: string): Promise<AgentTask> {
  const response = await apiClient.get(`/agent-tasks/${taskId}`);
  return normalizeAgentTask(response.data) as unknown as AgentTask;
}

/**
 * 启动 Agent 任务
 */
export async function startAgentTask(
  taskId: string,
): Promise<{ message: string; task_id: string }> {
  const response = await apiClient.post(`/agent-tasks/${taskId}/start`);
  return response.data;
}

/**
 * 取消 Agent 任务
 */
export async function cancelAgentTask(
  taskId: string,
): Promise<{ message: string; task_id: string }> {
  const response = await apiClient.post(`/agent-tasks/${taskId}/cancel`);
  return response.data;
}

/**
 * 获取 Agent 任务事件列表
 */
export async function getAgentEvents(
  taskId: string,
  params?: { after_sequence?: number; limit?: number },
): Promise<AgentEvent[]> {
  const response = await apiClient.get(`/agent-tasks/${taskId}/events/list`, {
    params,
  });
  return Array.isArray(response.data)
    ? response.data.map((item: any) => normalizeAgentEvent(item) as AgentEvent)
    : [];
}

/**
 * 获取 Agent 任务发现列表
 */
export async function getAgentFindings(
  taskId: string,
  params?: {
    is_verified?: boolean;
    severity?: string;
    vulnerability_type?: string;
  },
): Promise<AgentFinding[]> {
  const response = await apiClient.get(`/agent-tasks/${taskId}/findings`, {
    params,
  });
  return Array.isArray(response.data)
    ? response.data.map(
        (item: any) => normalizeAgentFinding(item) as AgentFinding,
      )
    : [];
}

/**
 * 获取单个发现详情
 */
export async function getAgentFinding(
  taskId: string,
  findingId: string,
): Promise<AgentFinding> {
  const response = await apiClient.get(
    `/agent-tasks/${taskId}/findings/${findingId}`,
  );
  return normalizeAgentFinding(response.data) as AgentFinding;
}

/**
 * 更新发现状态
 */
export async function updateAgentFinding(
  taskId: string,
  findingId: string,
  data: { status?: string },
): Promise<AgentFinding> {
  const response = await apiClient.put(
    `/agent-tasks/${taskId}/findings/${findingId}`,
    data,
  );
  return normalizeAgentFinding(response.data) as AgentFinding;
}

/**
 * 获取任务摘要
 */
export async function getAgentTaskSummary(
  taskId: string,
): Promise<AgentTaskSummary> {
  const response = await apiClient.get(`/agent-tasks/${taskId}/summary`);
  const data = response.data || {};
  const severity = data.severity_distribution || {};
  const vulnerabilityTypes = data.vulnerability_types || {};
  return {
    task_id: data.task_id || taskId,
    status: data.status || 'pending',
    progress_percentage: data.progress_percentage || 0,
    security_score: data.security_score || 0,
    quality_score: data.quality_score || 0,
    statistics: {
      total_files: data.statistics?.total_files || 0,
      indexed_files: data.statistics?.indexed_files || 0,
      analyzed_files: data.statistics?.analyzed_files || 0,
      files_with_findings: data.statistics?.files_with_findings || 0,
      total_chunks: data.statistics?.total_chunks || 0,
      findings_count: data.statistics?.findings_count || 0,
      verified_count: data.statistics?.verified_count || 0,
      false_positive_count: data.statistics?.false_positive_count || 0,
    },
    severity_distribution: {
      critical: severity.critical || 0,
      high: severity.high || 0,
      medium: severity.medium || 0,
      low: severity.low || 0,
    },
    vulnerability_types: Object.fromEntries(
      Object.entries(vulnerabilityTypes).map(([key, value]: [string, any]) => [
        key,
        typeof value === 'number' ? { total: value, verified: 0 } : value,
      ]),
    ),
    duration_seconds: data.duration_seconds || null,
  };
}

/**
 * 创建 SSE 事件源
 */
export function createAgentEventSource(
  taskId: string,
  afterSequence = 0,
): EventSource {
  const url = resolveApiUrl(
    `/agent-tasks/${taskId}/events?after_sequence=${afterSequence}`,
  );
  return new EventSource(url, { withCredentials: true });
}

/**
 * 使用 fetch 流式获取事件（支持自定义 headers）
 */
export async function* streamAgentEvents(
  taskId: string,
  afterSequence = 0,
  signal?: AbortSignal,
): AsyncGenerator<AgentEvent, void, unknown> {
  const token = getStoredToken();
  const url = resolveApiUrl(
    `/agent-tasks/${taskId}/events?after_sequence=${afterSequence}`,
  );

  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'text/event-stream',
    },
    signal,
  });

  if (!response.ok) {
    throw new Error(
      `Failed to connect to event stream: ${response.statusText}`,
    );
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // 解析 SSE 格式
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = normalizeAgentEvent(JSON.parse(data)) as AgentEvent;
            yield event;
          } catch {
            // 忽略解析错误
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ============ Agent Tree Types ============

export interface AgentTreeNode {
  id: string;
  agent_id: string;
  agent_name: string;
  agent_type: string;
  parent_agent_id: null | string;
  depth: number;
  task_description: null | string;
  knowledge_modules: null | string[];
  status: 'completed' | 'created' | 'failed' | 'running' | 'waiting';
  result_summary: null | string;
  findings_count: number;
  iterations: number;
  tokens_used: number;
  tool_calls: number;
  duration_ms: null | number;
  children: AgentTreeNode[];
}

export interface AgentTreeResponse {
  task_id: string;
  root_agent_id: null | string;
  total_agents: number;
  running_agents: number;
  completed_agents: number;
  failed_agents: number;
  total_findings: number;
  nodes: AgentTreeNode[];
}

export interface AgentCheckpoint {
  id: string;
  phase: string;
  sequence: number;
  message: null | string;
  timestamp: null | string;
  agent_id: string;
  agent_name: string;
  agent_type: string;
  iteration: number;
  status: string;
  total_tokens: number;
  tool_calls: number;
  findings_count: number;
  checkpoint_type: string;
  checkpoint_name: null | string;
  created_at: null | string;
}

export interface CheckpointDetail extends AgentCheckpoint {
  task_id: string;
  task_status: string;
  progress_percentage: number;
  parent_agent_id: null | string;
  events: Record<string, unknown>[];
  statistics: Record<string, number>;
  state_data: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

// ============ Agent Tree API Functions ============

/**
 * 获取任务的 Agent 树结构
 */
export async function getAgentTree(taskId: string): Promise<AgentTreeResponse> {
  const response = await apiClient.get(`/agent-tasks/${taskId}/tree`);
  const nodes = Array.isArray(response.data) ? response.data : [];
  const normalizedNodes = nodes.map((item: any) => ({
    id: String(item.id || item.agent_id || ''),
    agent_id: String(item.agent_id || item.id || ''),
    agent_name: item.agent_name || item.label || 'Agent',
    agent_type: item.agent_type || item.phase || 'orchestrator',
    parent_agent_id: item.parent_agent_id ? String(item.parent_agent_id) : null,
    depth: Number(item.depth || 0),
    task_description: item.task_description || null,
    knowledge_modules: Array.isArray(item.knowledge_modules)
      ? item.knowledge_modules
      : [],
    status: item.status || 'running',
    result_summary: item.result_summary || null,
    findings_count: Number(item.findings_count || 0),
    iterations: Number(item.iterations || 0),
    tokens_used: Number(item.tokens_used || 0),
    tool_calls: Number(item.tool_calls || 0),
    duration_ms:
      item.duration_ms === null || item.duration_ms === undefined
        ? null
        : Number(item.duration_ms),
    children: [],
  }));
  const rootNode =
    normalizedNodes.find((item) => !item.parent_agent_id) || normalizedNodes[0];
  return {
    task_id: taskId,
    root_agent_id: rootNode?.agent_id || null,
    total_agents: normalizedNodes.length,
    running_agents: normalizedNodes.filter((item) => item.status === 'running')
      .length,
    completed_agents: normalizedNodes.filter(
      (item) => item.status === 'completed',
    ).length,
    failed_agents: normalizedNodes.filter((item) => item.status === 'failed')
      .length,
    total_findings:
      rootNode?.findings_count ||
      Math.max(...normalizedNodes.map((item) => item.findings_count), 0),
    nodes: normalizedNodes,
  };
}

function normalizeAgentCheckpoint(
  item: any,
  fallbackTaskId: string,
  index = 0,
): AgentCheckpoint {
  const fallbackPhase = String(item?.phase || item?.agent_type || 'unknown');
  const fallbackId = `${fallbackTaskId}-${fallbackPhase}-${item?.sequence || index}`;
  return {
    id: String(item?.id || fallbackId),
    phase: fallbackPhase,
    sequence: Number(item?.sequence || index),
    message: item?.message || null,
    timestamp: item?.timestamp || null,
    agent_id: String(item?.agent_id || item?.phase || 'agent'),
    agent_name: String(item?.agent_name || item?.phase || 'Agent'),
    agent_type: String(item?.agent_type || item?.phase || 'agent'),
    iteration: Number(item?.iteration || 0),
    status: String(item?.status || 'pending'),
    total_tokens: Number(item?.total_tokens || 0),
    tool_calls: Number(item?.tool_calls || 0),
    findings_count: Number(item?.findings_count || 0),
    checkpoint_type: String(item?.checkpoint_type || 'auto'),
    checkpoint_name: item?.checkpoint_name || item?.message || null,
    created_at: item?.created_at || item?.timestamp || null,
  };
}

/**
 * 获取任务的检查点列表
 */
export async function getAgentCheckpoints(
  taskId: string,
  params?: { agent_id?: string; limit?: number },
): Promise<AgentCheckpoint[]> {
  const response = await apiClient.get(`/agent-tasks/${taskId}/checkpoints`, {
    params,
  });
  return Array.isArray(response.data)
    ? response.data.map((item: any, index: number) =>
        normalizeAgentCheckpoint(item, taskId, index),
      )
    : [];
}

/**
 * 获取检查点详情
 */
export async function getCheckpointDetail(
  taskId: string,
  checkpointId: string,
): Promise<CheckpointDetail> {
  const response = await apiClient.get(
    `/agent-tasks/${taskId}/checkpoints/${checkpointId}`,
  );
  const base = normalizeAgentCheckpoint(response.data, taskId);
  return {
    ...base,
    task_id: taskId,
    task_status: String(response.data?.task_status || ''),
    progress_percentage: Number(response.data?.progress_percentage || 0),
    parent_agent_id: response.data?.parent_agent_id
      ? String(response.data.parent_agent_id)
      : null,
    events: Array.isArray(response.data?.events) ? response.data.events : [],
    statistics:
      response.data?.statistics && typeof response.data.statistics === 'object'
        ? Object.fromEntries(
            Object.entries(response.data.statistics).map(([key, value]) => [
              key,
              Number(value || 0),
            ]),
          )
        : {},
    state_data:
      response.data?.state_data && typeof response.data.state_data === 'object'
        ? response.data.state_data
        : {},
    metadata:
      response.data?.metadata && typeof response.data.metadata === 'object'
        ? response.data.metadata
        : {},
  };
}

export async function resumeAgentTaskFromCheckpoint(
  taskId: string,
  checkpointId: string,
): Promise<AgentTask> {
  const response = await apiClient.post(
    `/agent-tasks/${taskId}/checkpoints/${checkpointId}/resume`,
  );
  return normalizeAgentTask(response.data) as unknown as AgentTask;
}

/**
 * 下载 Agent 任务报告
 */
export async function downloadAgentReport(
  taskId: string,
  format: 'json' | 'markdown' = 'markdown',
): Promise<void> {
  const response = await apiClient.get(`/agent-tasks/${taskId}/report`, {
    params: { format },
    responseType: 'blob',
  });

  // Create download link
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;

  // Calculate filename
  let filename = `audit-report-${taskId.slice(0, 8)}.${format === 'markdown' ? 'md' : 'json'}`;

  // Try to get filename from header
  const contentDisposition = response.headers['content-disposition'];
  if (contentDisposition) {
    const match = contentDisposition.match(/filename=(.+)/);
    if (match && match[1]) filename = match[1].replaceAll(/['"]/g, ''); // Remove quotes if present
  }

  link.setAttribute('download', filename);
  document.body.append(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
