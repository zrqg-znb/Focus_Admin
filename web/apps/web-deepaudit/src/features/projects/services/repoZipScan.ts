import { apiClient } from "@/shared/api/serverClient";

/**
 * 上传ZIP文件并启动扫描
 */
export async function scanZipFile(params: {
  projectId: string;
  zipFile: File;
  excludePatterns?: string[];
  createdBy?: string;
  filePaths?: string[];
  ruleSetId?: string;
  promptTemplateId?: string;
}): Promise<string> {
  const formData = new FormData();
  formData.append("file", params.zipFile);
  await apiClient.post(`/projects/${params.projectId}/zip`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  const res = await apiClient.post(`/scan/zip`, {
    project_id: params.projectId,
    exclude_patterns: params.excludePatterns || [],
    file_paths: params.filePaths || [],
    rule_set_id: params.ruleSetId,
    prompt_template_id: params.promptTemplateId,
    include_tests: false,
    include_docs: false,
    analysis_depth: "standard",
  });
  return res.data.id;
}

/**
 * 使用已存储的ZIP文件启动扫描（无需重新上传）
 */
export async function scanStoredZipFile(params: {
  projectId: string;
  excludePatterns?: string[];
  createdBy?: string;
  filePaths?: string[];
  ruleSetId?: string;
  promptTemplateId?: string;
}): Promise<string> {
  const res = await apiClient.post(`/scan/zip`, {
    project_id: params.projectId,
    exclude_patterns: params.excludePatterns || [],
    file_paths: params.filePaths || [],
    rule_set_id: params.ruleSetId,
    prompt_template_id: params.promptTemplateId,
    include_tests: false,
    include_docs: false,
    analysis_depth: "standard",
  });
  return res.data.id;
}

export function validateZipFile(file: File): { valid: boolean; error?: string } {
  // 检查文件类型
  if (!file.type.includes('zip') && !file.name.toLowerCase().endsWith('.zip')) {
    return { valid: false, error: '请上传ZIP格式的文件' };
  }

  // 检查文件大小 (限制为500MB)
  const maxSize = 500 * 1024 * 1024;
  if (file.size > maxSize) {
    return { valid: false, error: '文件大小不能超过500MB' };
  }

  return { valid: true };
}
