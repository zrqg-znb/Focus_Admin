import { requestClient } from '#/api/request';

export interface PositionStaff {
  id?: string;
  name: string;
  users_info: { id: string; name: string; avatar?: string }[];
}

export interface OrgNode {
  id: string;
  name: string;
  code?: string;
  description?: string;
  parent_id?: string;
  linked_project_id?: string;
  linked_project_info?: { id: string; name: string };
  sys_create_datetime?: string;
  sort_order?: number;
  children?: OrgNode[];
  positions: PositionStaff[];
  milestone_info?: any;
}

export interface OrgNodeCreate {
  name: string;
  code?: string;
  description?: string;
  parent_id?: string;
  linked_project_id?: string;
  positions: { name: string; user_ids: string[] }[];
}

export interface OrgNodeUpdate {
  name?: string;
  code?: string;
  description?: string;
  parent_id?: string;
  linked_project_id?: string;
  sort_order?: number;
}

// --- Nodes ---
export function getTree() {
  return requestClient.get<OrgNode[]>('/api/delivery-matrix/tree');
}

export function createNode(data: OrgNodeCreate) {
  return requestClient.post<OrgNode>('/api/delivery-matrix/nodes', data);
}

export function updateNode(id: string, data: OrgNodeUpdate) {
  return requestClient.put<OrgNode>(`/api/delivery-matrix/nodes/${id}`, data);
}

export function deleteNode(id: string) {
  return requestClient.delete(`/api/delivery-matrix/nodes/${id}`);
}

export function updateNodePositions(id: string, positions: { name: string; user_ids: string[] }[]) {
  return requestClient.put<PositionStaff[]>(`/api/delivery-matrix/nodes/${id}/positions`, positions);
}
