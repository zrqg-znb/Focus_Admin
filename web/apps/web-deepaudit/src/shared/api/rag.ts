import { apiClient } from "./serverClient";

const RAG_PREFIX = "/deepaudit/rag";

export interface KnowledgeStats {
  total: number;
  by_category: Record<string, number>;
  by_severity: Record<string, number>;
}

export interface KnowledgeStatus {
  enabled: boolean;
  chunk_count: number;
  document_count: number;
  stats: KnowledgeStats;
}

export interface KnowledgeDocument {
  id: string;
  title: string;
  content: string;
  category: string;
  tags: string[];
  severity: null | string;
  cwe_ids: string[];
  owasp_ids: string[];
  metadata: Record<string, unknown>;
  score?: null | number;
  file_path?: null | string;
}

export interface KnowledgeListResponse {
  total: number;
  items: KnowledgeDocument[];
}

export interface KnowledgeSavePayload {
  id?: string;
  title: string;
  content: string;
  category?: string;
  tags?: string[];
  severity?: null | string;
  cwe_ids?: string[];
  owasp_ids?: string[];
  metadata?: Record<string, unknown>;
}

export interface KnowledgeUploadPayload {
  file: File;
  documentId?: string;
  title?: string;
  category?: string;
  tags?: string[];
  severity?: string;
  cweIds?: string[];
  owaspIds?: string[];
}

function toRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : {};
}

function normalizeKnowledgeDocument(item: unknown): KnowledgeDocument {
  const record = toRecord(item);
  return {
    id: String(record.id || ""),
    title: String(record.title || record.id || ""),
    content: String(record.content || ""),
    category: String(record.category || "best_practice"),
    tags: Array.isArray(record.tags) ? record.tags.map((tag) => String(tag)) : [],
    severity: record.severity ? String(record.severity) : null,
    cwe_ids: Array.isArray(record.cwe_ids) ? record.cwe_ids.map((value) => String(value)) : [],
    owasp_ids: Array.isArray(record.owasp_ids) ? record.owasp_ids.map((value) => String(value)) : [],
    metadata: toRecord(record.metadata),
    score: record.score == null ? null : Number(record.score),
    file_path: record.file_path ? String(record.file_path) : null,
  };
}

function normalizeKnowledgeStatus(data: unknown): KnowledgeStatus {
  const record = toRecord(data);
  const stats = toRecord(record.stats);
  const byCategory = toRecord(stats.by_category);
  const bySeverity = toRecord(stats.by_severity);
  return {
    enabled: Boolean(record.enabled),
    chunk_count: Number(record.chunk_count || 0),
    document_count: Number(record.document_count || 0),
    stats: {
      total: Number(stats.total || 0),
      by_category:
        Object.keys(byCategory).length > 0
          ? Object.fromEntries(
              Object.entries(byCategory).map(([key, value]) => [key, Number(value || 0)]),
            )
          : {},
      by_severity:
        Object.keys(bySeverity).length > 0
          ? Object.fromEntries(
              Object.entries(bySeverity).map(([key, value]) => [key, Number(value || 0)]),
            )
          : {},
    },
  };
}

export async function getKnowledgeStatus(): Promise<KnowledgeStatus> {
  const response = await apiClient.get(`${RAG_PREFIX}/knowledge/status`);
  return normalizeKnowledgeStatus(response.data);
}

export async function listKnowledgeDocuments(params?: {
  category?: string;
  keyword?: string;
  tag?: string;
}): Promise<KnowledgeListResponse> {
  const response = await apiClient.get(`${RAG_PREFIX}/knowledge/modules`, { params });
  const items = Array.isArray(response.data?.items) ? response.data.items : [];
  return {
    total: Number(response.data?.total || items.length),
    items: items.map(normalizeKnowledgeDocument),
  };
}

export async function searchKnowledgeDocuments(payload: {
  query: string;
  category?: string;
  top_k?: number;
}): Promise<KnowledgeListResponse> {
  const response = await apiClient.post(`${RAG_PREFIX}/knowledge/search`, payload);
  const items = Array.isArray(response.data?.items) ? response.data.items : [];
  return {
    total: Number(response.data?.total || items.length),
    items: items.map(normalizeKnowledgeDocument),
  };
}

export async function getKnowledgeDocument(documentId: string): Promise<KnowledgeDocument> {
  const response = await apiClient.get(`${RAG_PREFIX}/knowledge/modules/${documentId}`);
  return normalizeKnowledgeDocument(response.data);
}

export async function saveKnowledgeDocument(payload: KnowledgeSavePayload): Promise<KnowledgeDocument> {
  const response = await apiClient.post(`${RAG_PREFIX}/knowledge/modules`, payload);
  return normalizeKnowledgeDocument(response.data?.document || response.data);
}

export async function uploadKnowledgeDocument(payload: KnowledgeUploadPayload): Promise<KnowledgeDocument> {
  const formData = new FormData();
  formData.append("file", payload.file);
  if (payload.documentId) {
    formData.append("document_id", payload.documentId);
  }
  if (payload.title) {
    formData.append("title", payload.title);
  }
  if (payload.category) {
    formData.append("category", payload.category);
  }
  if (payload.severity) {
    formData.append("severity", payload.severity);
  }
  (payload.tags || []).forEach((item) => {
    formData.append("tags", item);
  });
  (payload.cweIds || []).forEach((item) => {
    formData.append("cwe_ids", item);
  });
  (payload.owaspIds || []).forEach((item) => {
    formData.append("owasp_ids", item);
  });

  const response = await apiClient.post(`${RAG_PREFIX}/knowledge/upload`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return normalizeKnowledgeDocument(response.data?.document || response.data);
}

export async function deleteKnowledgeDocument(documentId: string): Promise<boolean> {
  const response = await apiClient.delete(`${RAG_PREFIX}/knowledge/modules/${documentId}`);
  return Boolean(response.data?.success ?? response.data);
}

export async function rebuildKnowledgeIndex(): Promise<KnowledgeStatus> {
  const response = await apiClient.post(`${RAG_PREFIX}/knowledge/rebuild`);
  return normalizeKnowledgeStatus(response.data);
}

export async function validateKnowledgeModules(modules: string[]): Promise<{
  valid: string[];
  invalid: string[];
}> {
  const response = await apiClient.post(`${RAG_PREFIX}/knowledge/validate`, { modules });
  return {
    valid: Array.isArray(response.data?.valid) ? response.data.valid.map((item: unknown) => String(item)) : [],
    invalid: Array.isArray(response.data?.invalid) ? response.data.invalid.map((item: unknown) => String(item)) : [],
  };
}
