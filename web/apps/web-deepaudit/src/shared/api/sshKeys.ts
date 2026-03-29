/**
 * SSH Keys API Client
 */

import { apiClient } from './serverClient';

export interface SSHKeyResponse {
  has_key: boolean;
  public_key?: string;
  fingerprint?: string;
  known_hosts?: string;
  updated_at?: string;
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

export interface SSHKeyTestResponse {
  success: boolean;
  message: string;
  output?: string;
}

function toRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}

function normalizeSSHKeyResponse(data: unknown): SSHKeyResponse {
  const record = toRecord(data);
  return {
    has_key: Boolean(record.has_private_key),
    public_key: typeof record.public_key === 'string' ? record.public_key : undefined,
    fingerprint: typeof record.fingerprint === 'string' ? record.fingerprint : undefined,
    known_hosts: typeof record.known_hosts === 'string' ? record.known_hosts : undefined,
    updated_at: typeof record.updated_at === 'string' ? record.updated_at : undefined,
  };
}

/**
 * 生成新的SSH密钥对
 */
export const generateSSHKey = async (payload?: {
  keyType?: "rsa" | "ed25519";
  keySize?: number;
}): Promise<SSHKeyGenerateResponse> => {
  const response = await apiClient.post<SSHKeyGenerateResponse>('/ssh-keys/generate', {
    key_type: payload?.keyType || 'ed25519',
    key_size: payload?.keySize || 4096,
  });
  return {
    public_key: String(response.data?.public_key || ''),
    fingerprint: response.data?.fingerprint,
    message: String(response.data?.message || 'SSH 密钥生成成功'),
  };
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
  const response = await apiClient.post<SSHKeyTestResponse>('/ssh-keys/test', {
    repo_url: repoUrl,
  });
  return {
    success: Boolean(response.data?.success),
    message: String(response.data?.message || ''),
    output: response.data?.output,
  };
};

/**
 * 清理known_hosts文件
 */
export const clearKnownHosts = async (): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.delete('/ssh-keys/known-hosts');
  return {
    success: Boolean(response.data),
    message: 'known_hosts 已清理',
  };
};
