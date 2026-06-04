import { requestClient } from '#/api/request';

export type ComplianceDomain = 'cockpit' | 'vehicle';
export type ComplianceMode = 'CR' | 'MR';
export type ComplianceBindMode = 'append' | 'replace';
export type ComplianceBranchType =
  | 'development'
  | 'other'
  | 'release'
  | 'trunk';

export interface ImportErrorRow {
  message: string;
  row_no: number;
}

export interface ImportResult {
  created_count: number;
  errors: ImportErrorRow[];
  ignored_count: number;
  updated_count: number;
}

export interface BindResult {
  created_count: number;
  ignored_count: number;
  removed_count: number;
  restored_count: number;
}

export interface OrganizationItem {
  children?: OrganizationItem[];
  domain: ComplianceDomain;
  domain_label: string;
  group_id: string;
  id: string;
  mode: ComplianceMode;
  mode_label: string;
  name: string;
  parent_id?: null | string;
  parent_name?: null | string;
  remark?: null | string;
  repository_count: number;
  sort: number;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface OrganizationPayload {
  domain: ComplianceDomain;
  group_id: string;
  mode: ComplianceMode;
  name: string;
  parent_id?: null | string;
  remark?: null | string;
  sort?: number;
}

export interface RepositoryItem {
  branch_count: number;
  domain: ComplianceDomain;
  domain_label: string;
  id: string;
  mode: ComplianceMode;
  mode_label: string;
  organization_group_id: string;
  organization_id: string;
  organization_name: string;
  project_id: string;
  project_name: string;
  project_url: string;
  remark?: null | string;
  repo_type: string;
  repo_type_label: string;
  responsibility_group_ids: string[];
  responsibility_group_names: string[];
  sort: number;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface RepositoryPayload {
  domain: ComplianceDomain;
  mode: ComplianceMode;
  organization_id: string;
  project_id: string;
  project_name: string;
  project_url?: string;
  remark?: null | string;
  repo_type?: string;
  responsibility_group_ids?: string[];
  sort?: number;
}

export interface RepositoryListParams {
  domain?: ComplianceDomain;
  keyword?: string;
  mode?: ComplianceMode;
  organization_id?: string;
  page?: number;
  pageSize?: number;
  repo_type?: string;
}

export interface BranchItem {
  alias: string;
  branch_name: string;
  branch_type: ComplianceBranchType;
  branch_type_label: string;
  created_date?: null | string;
  domain: ComplianceDomain;
  domain_label: string;
  id: string;
  purpose: string;
  remark?: null | string;
  repository_count: number;
  sort: number;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface BranchPayload {
  alias?: string;
  branch_name: string;
  branch_type: ComplianceBranchType;
  created_date?: null | string;
  domain: ComplianceDomain;
  purpose?: string;
  remark?: null | string;
  sort?: number;
}

export interface BranchListParams {
  branch_type?: ComplianceBranchType;
  domain?: ComplianceDomain;
  keyword?: string;
  page?: number;
  pageSize?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

const base = '/api/code-compliance/base';

const multipartOptions = {
  headers: { 'Content-Type': 'multipart/form-data' },
};

export function listOrganizationsApi() {
  return requestClient.get<OrganizationItem[]>(`${base}/organizations/tree`);
}

export function listValidOrganizationParentsApi(exclude_id?: string) {
  return requestClient.get<OrganizationItem[]>(
    `${base}/organizations/valid-parents`,
    { params: { exclude_id } },
  );
}

export function createOrganizationApi(data: OrganizationPayload) {
  return requestClient.post<OrganizationItem>(`${base}/organizations`, data);
}

export function updateOrganizationApi(
  id: string,
  data: Partial<OrganizationPayload>,
) {
  return requestClient.put<OrganizationItem>(
    `${base}/organizations/${id}`,
    data,
  );
}

export function deleteOrganizationApi(id: string) {
  return requestClient.delete(`${base}/organizations/${id}`);
}

export function importOrganizationsApi(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  return requestClient.post<ImportResult>(
    `${base}/organizations/import`,
    formData,
    multipartOptions,
  );
}

export function downloadOrganizationTemplateApi() {
  return requestClient.get(`${base}/organizations/template`, {
    responseType: 'blob',
  });
}

export function listRepositoriesApi(params?: RepositoryListParams) {
  return requestClient.get<PaginatedResponse<RepositoryItem>>(
    `${base}/repositories`,
    { params },
  );
}

export function createRepositoryApi(data: RepositoryPayload) {
  return requestClient.post<RepositoryItem>(`${base}/repositories`, data);
}

export function updateRepositoryApi(
  id: string,
  data: Partial<RepositoryPayload>,
) {
  return requestClient.put<RepositoryItem>(`${base}/repositories/${id}`, data);
}

export function deleteRepositoryApi(id: string) {
  return requestClient.delete(`${base}/repositories/${id}`);
}

export function importRepositoriesApi(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  return requestClient.post<ImportResult>(
    `${base}/repositories/import`,
    formData,
    multipartOptions,
  );
}

export function downloadRepositoryTemplateApi() {
  return requestClient.get(`${base}/repositories/template`, {
    responseType: 'blob',
  });
}

export function bindBranchesToRepositoriesApi(data: {
  branch_ids: string[];
  mode: ComplianceBindMode;
  repository_ids: string[];
}) {
  return requestClient.post<BindResult>(
    `${base}/repositories/batch-bind-branches`,
    data,
  );
}

export function listBranchesApi(params?: BranchListParams) {
  return requestClient.get<PaginatedResponse<BranchItem>>(`${base}/branches`, {
    params,
  });
}

export function createBranchApi(data: BranchPayload) {
  return requestClient.post<BranchItem>(`${base}/branches`, data);
}

export function updateBranchApi(id: string, data: Partial<BranchPayload>) {
  return requestClient.put<BranchItem>(`${base}/branches/${id}`, data);
}

export function deleteBranchApi(id: string) {
  return requestClient.delete(`${base}/branches/${id}`);
}

export function importBranchesApi(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  return requestClient.post<ImportResult>(
    `${base}/branches/import`,
    formData,
    multipartOptions,
  );
}

export function downloadBranchTemplateApi() {
  return requestClient.get(`${base}/branches/template`, {
    responseType: 'blob',
  });
}

export function bindRepositoriesToBranchesApi(data: {
  branch_ids: string[];
  mode: ComplianceBindMode;
  repository_ids: string[];
}) {
  return requestClient.post<BindResult>(
    `${base}/branches/batch-bind-repositories`,
    data,
  );
}
