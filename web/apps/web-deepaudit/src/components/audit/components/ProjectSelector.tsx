import type { Project } from '@/shared/types';

import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  getRepositoryTypeBadge,
  getRepositoryTypeLabel,
  getSourceTypeBadge,
  isRepositoryProject,
} from '@/shared/utils/projectUtils';
import { FileText, Search } from 'lucide-react';

interface ProjectSelectorProps {
  projects: Project[];
  selectedId: string;
  searchTerm: string;
  loading: boolean;
  onSelect: (id: string) => void;
  onSearchChange: (term: string) => void;
}

export default function ProjectSelector({
  projects,
  selectedId,
  searchTerm,
  loading,
  onSelect,
  onSearchChange,
}: ProjectSelectorProps) {
  const filteredProjects = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.description?.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  const projectListContent = (() => {
    if (loading) {
      return <LoadingSpinner />;
    }

    if (filteredProjects.length > 0) {
      return filteredProjects.map((project) => (
        <ProjectCard
          isSelected={selectedId === project.id}
          key={project.id}
          onSelect={() => onSelect(project.id)}
          project={project}
        />
      ));
    }

    return <EmptyState hasSearch={!!searchTerm} />;
  })();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Label className="font-mono text-base font-bold uppercase">
          选择项目
        </Label>
        <Badge
          className="border-border rounded-none font-mono text-xs"
          variant="outline"
        >
          {filteredProjects.length} 个可用项目
        </Badge>
      </div>

      <div className="relative">
        <Search className="text-foreground absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform" />
        <Input
          className="retro-input h-10 pl-10"
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="搜索项目名称..."
          value={searchTerm}
        />
      </div>

      <div className="grid max-h-60 grid-cols-1 gap-3 overflow-y-auto p-1 md:grid-cols-2">
        {projectListContent}
      </div>
    </div>
  );
}

function ProjectCard({
  project,
  isSelected,
  onSelect,
}: {
  isSelected: boolean;
  onSelect: () => void;
  project: Project;
}) {
  const isRepo = isRepositoryProject(project);

  return (
    <div
      className={`relative cursor-pointer border-2 p-4 transition-all ${
        isSelected
          ? 'border-primary translate-x-[-2px] translate-y-[-2px] bg-blue-50 shadow-[4px_4px_0px_0px_rgba(37,99,235,1)]'
          : 'border-border bg-background hover:bg-background hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]'
      }`}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h4 className="font-display text-sm font-bold uppercase">
            {project.name}
          </h4>
          {project.description && (
            <p className="text-muted-foreground mt-1 line-clamp-2 font-mono text-xs">
              {project.description}
            </p>
          )}
          <div className="text-muted-foreground mt-2 flex items-center space-x-4 font-mono text-xs font-bold">
            <span
              className={`px-1.5 py-0.5 ${isRepo ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}
            >
              {getSourceTypeBadge(project.source_type)}
            </span>
            {isRepo && (
              <>
                <span className="uppercase">
                  {getRepositoryTypeBadge(project.repository_type)}
                </span>
                <span>{project.default_branch}</span>
                {project.repository_type === 'multi' && (
                  <span>{getRepositoryTypeLabel(project.repository_type)}</span>
                )}
              </>
            )}
          </div>
        </div>
        {isSelected && (
          <div className="bg-primary border-border flex h-5 w-5 items-center justify-center border-2">
            <div className="bg-background h-2 w-2" />
          </div>
        )}
      </div>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <div className="col-span-2 flex items-center justify-center py-8">
      <div className="border-primary h-8 w-8 animate-spin rounded-none border-4 border-t-transparent" />
    </div>
  );
}

function EmptyState({ hasSearch }: { hasSearch: boolean }) {
  return (
    <div className="text-muted-foreground col-span-2 py-8 text-center font-mono">
      <FileText className="mx-auto mb-2 h-8 w-8 opacity-50" />
      <p className="text-sm">
        {hasSearch ? '未找到匹配的项目' : '暂无可用项目'}
      </p>
    </div>
  );
}
