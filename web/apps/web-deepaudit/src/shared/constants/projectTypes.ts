/**
 * 项目类型相关常量
 */

import type { ProjectSourceType, RepositoryType } from '@/shared/types';

// 项目来源类型选项
export const PROJECT_SOURCE_TYPES: Array<{
  description: string;
  label: string;
  value: ProjectSourceType;
}> = [
  {
    value: 'repository',
    label: '远程仓库',
    description: '从 CodeHub / 内网 Git 服务拉取代码',
  },
  {
    value: 'zip',
    label: 'ZIP上传',
    description: '上传本地ZIP压缩包进行扫描',
  },
];

// 仓库模式显示名称
export const REPOSITORY_TYPE_LABELS: Record<RepositoryType, string> = {
  single: '单仓',
  multi: '多仓',
};

// 仓库模式选项
export const REPOSITORY_TYPE_OPTIONS: Array<{
  description: string;
  label: string;
  value: RepositoryType;
}> = Object.entries(REPOSITORY_TYPE_LABELS).map(([value, label]) => ({
  value: value as RepositoryType,
  label,
  description:
    value === 'single'
      ? '直接 git clone，适合普通单仓项目'
      : '先执行 git mm init，再执行 git mm sync，适合多仓项目',
}));

// 兼容旧命名：尽量让现有 import 不需要大改
export const REPOSITORY_PLATFORM_LABELS = REPOSITORY_TYPE_LABELS;
export const REPOSITORY_PLATFORMS = REPOSITORY_TYPE_OPTIONS;

// 项目来源类型的颜色配置
export const SOURCE_TYPE_COLORS: Record<
  ProjectSourceType,
  {
    bg: string;
    border: string;
    text: string;
  }
> = {
  repository: {
    bg: 'bg-blue-100',
    text: 'text-blue-800',
    border: 'border-blue-300',
  },
  zip: {
    bg: 'bg-amber-100',
    text: 'text-amber-800',
    border: 'border-amber-300',
  },
};

// 仓库模式的颜色配置
export const PLATFORM_COLORS: Record<
  RepositoryType,
  {
    bg: string;
    text: string;
  }
> = {
  single: { bg: 'bg-foreground', text: 'text-background' },
  multi: { bg: 'bg-violet-600', text: 'text-white' },
};
