/**
 * SSH Keys API Client
 */

import { apiClient } from './serverClient';

export interface SSHKeyResponse {
  has_key: boolean;
  public_key?: string;
  fingerprint?: string;
}

export interface SSHKeyGenerateResponse {
  public_key: string;
  fingerprint?: string;
  message: string;
}

export interface SSHKeySavePayload {
  known_hosts?: string;
  private_key?: string;
  public_key?: string;
}

export interface SSHKeyTestRequest {
  repo_url: string;
}

export interface SSHKeyTestResponse {
  success: boolean;
  message: string;
  output?: string;
}

function normalizeSSHKeyResponse(data: any): SSHKeyResponse {
  return {
    has_key: Boolean(data?.has_private_key),
    public_key: data?.public_key,
    fingerprint: data?.fingerprint,
  };
}

/**
 * 生成新的SSH密钥对
 */
export const generateSSHKey = async (): Promise<SSHKeyGenerateResponse> => {
  throw new Error('当前 Focus 后端尚未提供 SSH 密钥自动生成功能，请手动粘贴已有密钥。');
};

/**
 * 获取当前用户的SSH公钥
 */
export const getSSHKey = async (): Promise<SSHKeyResponse> => {
  const response = await apiClient.get<SSHKeyResponse>('/ssh-keys/');
  return normalizeSSHKeyResponse(response.data);
};

/**
 * 保存 SSH 密钥
 */
export const saveSSHKey = async (payload: SSHKeySavePayload): Promise<SSHKeyResponse> => {
  const response = await apiClient.post('/ssh-keys/', payload);
  return normalizeSSHKeyResponse(response.data);
};

/**
 * 删除SSH密钥
 */
export const deleteSSHKey = async (): Promise<{ message: string }> => {
  await apiClient.delete('/ssh-keys/');
  return { message: 'SSH 密钥已删除' };
};

/**
 * 测试SSH密钥
 */
export const testSSHKey = async (repoUrl: string): Promise<SSHKeyTestResponse> => {
  return {
    success: false,
    message: '当前 Focus 后端尚未提供 SSH 在线测试接口，请直接通过项目拉取任务验证。',
  };
};

/**
 * 清理known_hosts文件
 */
export const clearKnownHosts = async (): Promise<{ success: boolean; message: string }> => {
  await saveSSHKey({ known_hosts: "" });
  return {
    success: true,
    message: 'known_hosts 已清理',
  };
};
