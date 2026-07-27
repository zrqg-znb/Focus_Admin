import { requestClient } from '#/api/request';

const base = '/api/agent-tools/providers';

/** AI 辅助工具平台中可复用的 OpenAI 兼容模型连接。 */
export interface Provider {
  id: string;
  name: string;
  base_url: string;
  model: string;
  has_api_key: boolean;
  is_active: boolean;
  description: string;
  owner_name?: string;
  sys_create_datetime?: string;
}

/** 保存模型连接时提交的字段；API Key 不会被响应返回。 */
export interface ProviderPayload {
  name: string;
  base_url: string;
  model: string;
  api_key: string;
  is_active: boolean;
  description: string;
}

/** 获取当前用户可用于各 Agent 的模型连接。 */
export const listProvidersApi = () => requestClient.get<Provider[]>(base);

/** 创建平台级模型连接。 */
export const createProviderApi = (data: ProviderPayload) =>
  requestClient.post<Provider>(base, data);

/** 更新平台级模型连接。 */
export const updateProviderApi = (id: string, data: ProviderPayload) =>
  requestClient.put<Provider>(`${base}/${id}`, data);

/** 测试 API 地址、密钥和模型名称是否有效。 */
export const testProviderApi = (id: string) =>
  requestClient.post<{ message: string; ok: boolean }>(`${base}/${id}/test`);
