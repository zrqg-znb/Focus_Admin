import type { CreateAuditTaskForm, Project } from '@/shared/types';
import type { ZipFileMeta } from '@/shared/utils/zipStorage';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  getRepositoryTypeLabel,
  getScanMethodDescription,
  isMultiRepository,
  isRepositoryProject,
  isZipProject,
} from '@/shared/utils/projectUtils';
import { GitBranch, Info, Zap } from 'lucide-react';

import ZipFileSection from './ZipFileSection';

interface BasicConfigProps {
  project: Project;
  taskForm: CreateAuditTaskForm;
  onUpdateForm: (updates: Partial<CreateAuditTaskForm>) => void;
  // ZIP 相关
  zipLoading: boolean;
  storedZipInfo: null | ZipFileMeta;
  useStoredZip: boolean;
  zipFile: File | null;
  onSwitchToStored: () => void;
  onSwitchToUpload: () => void;
  onFileSelect: (file: File | null, input?: HTMLInputElement) => void;
}

export default function BasicConfig({
  project,
  taskForm,
  onUpdateForm,
  zipLoading,
  storedZipInfo,
  useStoredZip,
  zipFile,
  onSwitchToStored,
  onSwitchToUpload,
  onFileSelect,
}: BasicConfigProps) {
  const isRepo = isRepositoryProject(project);
  const isZip = isZipProject(project);

  return (
    <div className="mt-6 space-y-4 font-mono">
      {/* ZIP 项目文件上传 */}
      {isZip && (
        <ZipFileSection
          loading={zipLoading}
          onFileSelect={onFileSelect}
          onSwitchToStored={onSwitchToStored}
          onSwitchToUpload={onSwitchToUpload}
          storedZipInfo={storedZipInfo}
          useStoredZip={useStoredZip}
          zipFile={zipFile}
        />
      )}

      <div className="grid grid-cols-2 gap-4">
        {/* 任务类型 */}
        <div className="space-y-2">
          <Label className="font-bold uppercase" htmlFor="task_type">
            任务类型
          </Label>
          <Select
            onValueChange={(value: 'instant' | 'repository') =>
              onUpdateForm({ task_type: value })
            }
            value={taskForm.task_type}
          >
            <SelectTrigger className="retro-input h-10 rounded-none border-2 border-black shadow-none focus:ring-0">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="rounded-none border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              <SelectItem value="repository">
                <div className="flex items-center space-x-2">
                  <GitBranch className="h-4 w-4" />
                  <span className="font-mono">仓库审计</span>
                </div>
              </SelectItem>
              <SelectItem value="instant">
                <div className="flex items-center space-x-2">
                  <Zap className="h-4 w-4" />
                  <span className="font-mono">即时分析</span>
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* 分支选择 - 仅仓库类型项目显示 */}
        {taskForm.task_type === 'repository' && isRepo && (
          <div className="space-y-2">
            <Label className="font-bold uppercase" htmlFor="branch_name">
              目标分支
            </Label>
            <Input
              className="retro-input h-10"
              id="branch_name"
              onChange={(e) => onUpdateForm({ branch_name: e.target.value })}
              placeholder={project.default_branch || 'main'}
              value={taskForm.branch_name || ''}
            />
          </div>
        )}

        {taskForm.task_type === 'repository' &&
          isRepo &&
          isMultiRepository(project) && (
            <>
              <div className="space-y-2">
                <Label className="font-bold uppercase" htmlFor="manifest_xml">
                  Manifest XML
                </Label>
                <Input
                  className="retro-input h-10"
                  id="manifest_xml"
                  onChange={(e) =>
                    onUpdateForm({ manifest_xml: e.target.value })
                  }
                  placeholder={project.manifest_xml || 'default.xml'}
                  value={taskForm.manifest_xml || ''}
                />
              </div>
              <div className="space-y-2">
                <Label className="font-bold uppercase" htmlFor="group">
                  Group
                </Label>
                <Input
                  className="retro-input h-10"
                  id="group"
                  onChange={(e) => onUpdateForm({ group: e.target.value })}
                  placeholder={project.group || '可选'}
                  value={taskForm.group || ''}
                />
              </div>
            </>
          )}
      </div>

      {/* 项目信息展示 */}
      <ProjectInfoCard project={project} />
    </div>
  );
}

function ProjectInfoCard({ project }: { project: Project }) {
  const isRepo = isRepositoryProject(project);
  let languages: string[] = [];

  try {
    if (project.programming_languages) {
      languages = JSON.parse(project.programming_languages);
    }
  } catch {
    // ignore
  }

  return (
    <div className="border-2 border-black bg-blue-50 p-4 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
      <div className="flex items-start space-x-3">
        <Info className="mt-0.5 h-5 w-5 text-blue-600" />
        <div className="font-mono text-sm">
          <p className="mb-1 font-bold uppercase text-blue-900">
            选中项目：{project.name}
          </p>
          <div className="space-y-1 font-bold text-blue-800">
            <p>项目类型：{isRepo ? '远程仓库' : 'ZIP上传'}</p>
            {project.description && <p>描述：{project.description}</p>}
            {isRepo && (
              <>
                <p>
                  仓库模式：{getRepositoryTypeLabel(project.repository_type)}
                </p>
                <p>默认分支：{project.default_branch}</p>
                <p>拉取方式：{getScanMethodDescription(project)}</p>
                {isMultiRepository(project) && (
                  <>
                    <p>Manifest XML：{project.manifest_xml || '未设置'}</p>
                    <p>Group：{project.group || '未设置'}</p>
                  </>
                )}
              </>
            )}
            {languages.length > 0 && <p>编程语言：{languages.join(', ')}</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
