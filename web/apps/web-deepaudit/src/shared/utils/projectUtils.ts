/**
 * 项目工具函数
 * 用于统一处理项目类型判断和相关逻辑
 */

import type {
  Project,
  ProjectSourceType,
  RepositoryType,
} from '@/shared/types';

import {
  REPOSITORY_PLATFORMS,
  REPOSITORY_TYPE_LABELS,
} from '@/shared/constants/projectTypes';

const LEGACY_REPOSITORY_TYPES = new Set(['gitea', 'github', 'gitlab', 'other']);

/**
 * 判断项目是否为仓库类型
 */
export function isRepositoryProject(project: Project): boolean {
  return project.source_type === 'repository';
}

/**
 * 判断项目是否为ZIP上传类型
 */
export function isZipProject(project: Project): boolean {
  return project.source_type === 'zip';
}

/**
 * 获取项目来源类型的显示名称
 */
export function getSourceTypeLabel(sourceType: ProjectSourceType): string {
  const labels: Record<ProjectSourceType, string> = {
    repository: '远程仓库',
    zip: 'ZIP上传',
  };
  return labels[sourceType] || '未知';
}

/**
 * 获取项目来源类型的英文标签
 */
export function getSourceTypeBadge(sourceType: ProjectSourceType): string {
  const badges: Record<ProjectSourceType, string> = {
    repository: 'REPO',
    zip: 'ZIP',
  };
  return badges[sourceType] || 'UNKNOWN';
}

/**
 * 规范化仓库模式
 */
export function normalizeRepositoryType(value?: null | string): RepositoryType {
  const raw = String(value || 'single')
    .trim()
    .toLowerCase();
  if (raw === 'multi') {
    return 'multi';
  }
  if (raw === 'single' || LEGACY_REPOSITORY_TYPES.has(raw)) {
    return 'single';
  }
  return 'single';
}

/**
 * 判断是否为多仓
 */
export function isMultiRepository(
  project:
    | null
    | Pick<Project, 'repository_type'>
    | undefined
    | { repository_type?: null | string },
): boolean {
  return normalizeRepositoryType(project?.repository_type) === 'multi';
}

/**
 * 获取仓库模式的显示名称
 */
export function getRepositoryTypeLabel(repositoryType?: null | string): string {
  return (
    REPOSITORY_TYPE_LABELS[normalizeRepositoryType(repositoryType)] ||
    REPOSITORY_TYPE_LABELS.single
  );
}

/**
 * 获取仓库模式的英文标签
 */
export function getRepositoryTypeBadge(repositoryType?: null | string): string {
  const normalized = normalizeRepositoryType(repositoryType);
  return normalized === 'multi' ? 'MULTI' : 'SINGLE';
}

/**
 * 获取仓库模式选项
 */
export function getRepositoryTypeOptions() {
  return REPOSITORY_PLATFORMS;
}

/**
 * 获取仓库平台的显示名称（兼容旧命名）
 */
export function getRepositoryPlatformLabel(platform?: string): string {
  return getRepositoryTypeLabel(platform);
}

/**
 * 判断项目是否可以选择分支（仅仓库类型项目）
 */
export function canSelectBranch(project: Project): boolean {
  return isRepositoryProject(project) && !!project.repository_url;
}

/**
 * 判断项目是否需要上传ZIP文件进行扫描
 */
export function requiresZipUpload(project: Project): boolean {
  return isZipProject(project);
}

/**
 * 获取项目扫描方式的描述
 */
export function getScanMethodDescription(project: Project): string {
  if (isRepositoryProject(project)) {
    if (isMultiRepository(project)) {
      return '通过 git mm init + git mm sync 拉取多仓代码';
    }
    return '从 CodeHub 仓库直接 git clone';
  }
  return '上传ZIP文件进行扫描';
}

/**
 * 验证项目配置是否完整
 */
export function validateProjectConfig(project: Project): {
  errors: string[];
  valid: boolean;
} {
  const errors: string[] = [];

  if (!project.name?.trim()) {
    errors.push('项目名称不能为空');
  }

  if (isRepositoryProject(project)) {
    if (!project.repository_url?.trim()) {
      errors.push('仓库地址不能为空');
    }
    if (isMultiRepository(project)) {
      if (!project.default_branch?.trim()) {
        errors.push('多仓项目的默认分支不能为空');
      }
      if (!project.manifest_xml?.trim()) {
        errors.push('多仓项目的 manifest_xml 不能为空');
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}
