import { requestClient } from '#/api/request';

export interface DeliveryDomain {
  id: number;
  name: string;
  code: string;
  interface_people: string[];
  interface_people_info: { id: string; name: string }[];
  remark?: string;
  sys_create_datetime: string;
}

export interface ProjectGroup {
  id: number;
  name: string;
  domain: number;
  domain_info: { id: number; name: string };
  managers: string[];
  managers_info: { id: string; name: string }[];
  remark?: string;
}

export interface ProjectComponent {
  id: number;
  name: string;
  group: number;
  group_info: { id: number; name: string };
  managers: string[];
  managers_info: { id: string; name: string }[];
  linked_project: null | number;
  linked_project_info: null | { id: number; name: string };
  milestone_info: any | null;
  remark?: string;
}

export interface DeliveryTreeNode {
  id: string;
  key: string;
  name: string;
  type: 'component' | 'domain' | 'group';
  real_id: number;
  parent_id?: string;
  children?: DeliveryTreeNode[];
  [key: string]: any;
}

// --- Domain ---
export function getDomains() {
  return requestClient.get<DeliveryDomain[]>('/api/delivery-matrix/domains');
}

export function getAllDomains() {
  return requestClient.get<DeliveryDomain[]>(
    '/api/delivery-matrix/domains/all',
  );
}

export function createDomain(data: any) {
  return requestClient.post('/api/delivery-matrix/domains', data);
}

export function updateDomain(id: number, data: any) {
  return requestClient.put(`/api/delivery-matrix/domains/${id}`, data);
}

export function deleteDomain(id: number) {
  return requestClient.delete(`/api/delivery-matrix/domains/${id}`);
}

// --- Group ---
export function getGroups(domain_id?: number) {
  return requestClient.get<ProjectGroup[]>('/api/delivery-matrix/groups', {
    params: { domain_id },
  });
}

export function createGroup(data: any) {
  return requestClient.post('/api/delivery-matrix/groups', data);
}

export function updateGroup(id: number, data: any) {
  return requestClient.put(`/api/delivery-matrix/groups/${id}`, data);
}

export function deleteGroup(id: number) {
  return requestClient.delete(`/api/delivery-matrix/groups/${id}`);
}

// --- Component ---
export function getComponents(group_id?: number) {
  return requestClient.get<ProjectComponent[]>(
    '/api/delivery-matrix/components',
    { params: { group_id } },
  );
}

export function createComponent(data: any) {
  return requestClient.post('/api/delivery-matrix/components', data);
}

export function updateComponent(id: number, data: any) {
  return requestClient.put(`/api/delivery-matrix/components/${id}`, data);
}

export function deleteComponent(id: number) {
  return requestClient.delete(`/api/delivery-matrix/components/${id}`);
}

// --- Dashboard ---
export function getDashboardMatrix() {
  return requestClient.get<any[]>('/api/delivery-matrix/dashboard/matrix');
}

// --- Admin Tree ---
export function getAdminTree() {
  return requestClient.get<DeliveryTreeNode[]>(
    '/api/delivery-matrix/admin/tree',
  );
}
