import { api } from '@/shared/config/database';

export async function runRepositoryAudit(params: {
  branch?: string;
  createdBy?: string;
  exclude?: string[];
  filePaths?: string[];
  group?: string;
  manifestXml?: string;
  projectId: string;
  promptTemplateId?: string;
  repositoryType?: string;
  repoUrl: string;
  ruleSetId?: string;
}) {
  // 后端会从用户配置中读取 CodeHub Token，前端不需要传递
  // The backend handles everything now.
  // We just need to create the task (which triggers the scan in our new api implementation)
  // or call a specific scan endpoint.

  // In our new api.createAuditTask implementation (src/shared/api/database.ts),
  // it actually calls /projects/{id}/scan which starts the process.

  const task = await api.createAuditTask({
    project_id: params.projectId,
    task_type: 'repository',
    repository_url: params.repoUrl,
    repository_type: params.repositoryType as any,
    branch_name: params.branch || 'main',
    manifest_xml: params.manifestXml,
    group: params.group,
    exclude_patterns: params.exclude || [],
    scan_config: {
      file_paths: params.filePaths,
      rule_set_id: params.ruleSetId,
      prompt_template_id: params.promptTemplateId,
    },
    created_by: params.createdBy || 'unknown',
  } as any);

  return task.id;
}
