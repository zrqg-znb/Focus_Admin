import { requestClient } from '#/api/request';

export interface HardwarePoint {
  id: string;
  code: string;
  boards: string[];
  remark?: string;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface PlatformConfig {
  id: string;
  name: string;
  remark?: string;
  sys_create_datetime?: string;
  sys_update_datetime?: string;
}

export interface HardwareConfigOptions {
  points: HardwarePoint[];
  viu_platforms: PlatformConfig[];
  cdc_platforms: PlatformConfig[];
  smart_screen_versions: PlatformConfig[];
}

export interface HardwarePointCreatePayload {
  code: string;
  boards: string[];
  remark?: string;
}

export interface HardwarePointUpdatePayload {
  code?: string;
  boards?: string[];
  remark?: string;
}

export interface PlatformConfigPayload {
  name: string;
  remark?: string;
}

const pointBase = '/api/project-manager/hardware/points';
const viuBase = '/api/project-manager/hardware/viu-platforms';
const cdcBase = '/api/project-manager/hardware/cdc-platforms';
const smartBase = '/api/project-manager/hardware/smart-screen-versions';

export async function listHardwareConfigOptionsApi() {
  return requestClient.get<HardwareConfigOptions>(
    '/api/project-manager/hardware/options',
  );
}

export async function listHardwarePointsApi() {
  return requestClient.get<HardwarePoint[]>(pointBase);
}

export async function createHardwarePointApi(data: HardwarePointCreatePayload) {
  return requestClient.post<HardwarePoint>(pointBase, data);
}

export async function updateHardwarePointApi(
  id: string,
  data: HardwarePointUpdatePayload,
) {
  return requestClient.put<HardwarePoint>(`${pointBase}/${id}`, data);
}

export async function deleteHardwarePointApi(id: string) {
  return requestClient.delete<HardwarePoint>(`${pointBase}/${id}`);
}

export async function listCdcPlatformsApi() {
  return requestClient.get<PlatformConfig[]>(cdcBase);
}

export async function listViuPlatformsApi() {
  return requestClient.get<PlatformConfig[]>(viuBase);
}

export async function createViuPlatformApi(data: PlatformConfigPayload) {
  return requestClient.post<PlatformConfig>(viuBase, data);
}

export async function updateViuPlatformApi(
  id: string,
  data: PlatformConfigPayload,
) {
  return requestClient.put<PlatformConfig>(`${viuBase}/${id}`, data);
}

export async function deleteViuPlatformApi(id: string) {
  return requestClient.delete<PlatformConfig>(`${viuBase}/${id}`);
}

export async function createCdcPlatformApi(data: PlatformConfigPayload) {
  return requestClient.post<PlatformConfig>(cdcBase, data);
}

export async function updateCdcPlatformApi(
  id: string,
  data: PlatformConfigPayload,
) {
  return requestClient.put<PlatformConfig>(`${cdcBase}/${id}`, data);
}

export async function deleteCdcPlatformApi(id: string) {
  return requestClient.delete<PlatformConfig>(`${cdcBase}/${id}`);
}

export async function listSmartScreenVersionsApi() {
  return requestClient.get<PlatformConfig[]>(smartBase);
}

export async function createSmartScreenVersionApi(data: PlatformConfigPayload) {
  return requestClient.post<PlatformConfig>(smartBase, data);
}

export async function updateSmartScreenVersionApi(
  id: string,
  data: PlatformConfigPayload,
) {
  return requestClient.put<PlatformConfig>(`${smartBase}/${id}`, data);
}

export async function deleteSmartScreenVersionApi(id: string) {
  return requestClient.delete<PlatformConfig>(`${smartBase}/${id}`);
}
