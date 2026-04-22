import type { AuditTask, CodeAnalysisResult, Project } from '@/shared/types';

import { normalizeCodeAnalysisResult } from '@/shared/api/focusAdapter';
import { apiClient } from '@/shared/api/serverClient';
import { api } from '@/shared/config/database';
import { SUPPORTED_LANGUAGES } from '@/shared/constants';

type RepositoryAnalysisParams = {
  analysisDepth?: 'basic' | 'deep' | 'standard';
  branch?: string;
  excludePatterns?: string[];
  filePaths?: string[];
  group?: string;
  includeDocs?: boolean;
  includeTests?: boolean;
  manifestXml?: string;
  maxFileSize?: number;
  projectId: string;
  promptTemplateId?: string;
  ruleSetId?: string;
};

function getErrorMessage(error: unknown, fallback: string) {
  if (typeof error === 'object' && error !== null) {
    const record = error as {
      message?: string;
      response?: {
        data?: {
          detail?: string;
        };
      };
    };
    return record.response?.data?.detail || record.message || fallback;
  }
  return fallback;
}

export const CodeAnalysisEngine = {
  getSupportedLanguages(): string[] {
    return [...SUPPORTED_LANGUAGES];
  },

  async analyzeCode(
    code: string,
    language: string,
    promptTemplateId?: string,
    fileName?: string,
  ): Promise<CodeAnalysisResult> {
    try {
      const response = await apiClient.post('/scan/instant', {
        code_content: code,
        language,
        file_name: fileName || undefined,
        prompt_template_id: promptTemplateId || undefined,
      });
      return normalizeCodeAnalysisResult(response.data) as CodeAnalysisResult;
    } catch (error) {
      console.error('Analysis failed:', error);
      throw new Error(getErrorMessage(error, 'Analysis failed'));
    }
  },

  async analyzeRepository(
    params: RepositoryAnalysisParams,
  ): Promise<AuditTask> {
    try {
      return await api.createAuditTask({
        project_id: params.projectId,
        task_type: 'repository',
        branch_name: params.branch,
        manifest_xml: params.manifestXml,
        group: params.group,
        exclude_patterns: params.excludePatterns || [],
        prompt_template_id: params.promptTemplateId,
        rule_set_id: params.ruleSetId,
        scan_config: {
          analysis_depth: params.analysisDepth || 'standard',
          file_paths: params.filePaths || [],
          include_docs: Boolean(params.includeDocs),
          include_tests: Boolean(params.includeTests),
          max_file_size: params.maxFileSize,
        },
      });
    } catch (error) {
      console.error('Repository analysis failed:', error);
      throw new Error(getErrorMessage(error, '启动仓库分析失败'));
    }
  },

  async getRepositories(): Promise<Project[]> {
    const projects = await api.getProjects();
    return projects.filter(
      (project) =>
        project.source_type === 'repository' && Boolean(project.repository_url),
    );
  },

  async getBranches(
    projectId: string,
  ): Promise<{ branches: string[]; default_branch: string; error?: string }> {
    return api.getProjectBranches(projectId);
  },
};
