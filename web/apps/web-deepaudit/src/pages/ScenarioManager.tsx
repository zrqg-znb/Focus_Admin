import { useEffect, useMemo, useState } from 'react';
import {
  Copy,
  Layers3,
  Loader2,
  Plus,
  RefreshCw,
  Shield,
  Sparkles,
  Trash2,
} from 'lucide-react';
import { toast } from 'sonner';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import {
  createScenarioProfile,
  copyScenarioProfile,
  deleteScenarioProfile,
  getScenarioProfiles,
  setDefaultScenarioProfile,
  updateScenarioProfile,
  type ScenarioObjectiveType,
  type ScenarioProfile,
} from '@/shared/api/scenarios';
import { useAuth } from '@/shared/context/AuthContext';
import { DEEPAUDIT_ACTION_CODES } from '@/shared/focus/focusPermission';
import { getPromptTemplates, type PromptTemplate } from '@/shared/api/prompts';
import { getRuleSets, type AuditRuleSet } from '@/shared/api/rules';
import { listKnowledgeDocuments, type KnowledgeDocument } from '@/shared/api/rag';

type ScenarioFormState = {
  scenario_key: string;
  name: string;
  description: string;
  objective_type: ScenarioObjectiveType;
  prompt_template_id: string;
  rule_set_id: string;
  knowledge_modules: string[];
  is_active: boolean;
};

const EMPTY_FORM: ScenarioFormState = {
  scenario_key: '',
  name: '',
  description: '',
  objective_type: 'audit',
  prompt_template_id: '',
  rule_set_id: '',
  knowledge_modules: [],
  is_active: true,
};

function getObjectiveLabel(value: ScenarioObjectiveType) {
  return value === 'inventory' ? '代码梳理' : '漏洞审计';
}

function buildFormState(scenario: ScenarioProfile | null): ScenarioFormState {
  if (!scenario) {
    return EMPTY_FORM;
  }
  return {
    scenario_key: scenario.scenario_key,
    name: scenario.name,
    description: scenario.description || '',
    objective_type: scenario.objective_type,
    prompt_template_id: scenario.prompt_template_id || '',
    rule_set_id: scenario.rule_set_id || '',
    knowledge_modules: [...scenario.knowledge_modules],
    is_active: scenario.is_active,
  };
}

function getErrorMessage(error: unknown, fallback: string) {
  if (typeof error === 'object' && error !== null) {
    const record = error as {
      response?: {
        data?: {
          detail?: string;
        };
      };
      message?: string;
    };
    return record.response?.data?.detail || record.message || fallback;
  }
  return fallback;
}

export default function ScenarioManager() {
  const { hasAccess } = useAuth();
  const canManageScenarios = hasAccess(DEEPAUDIT_ACTION_CODES.SCENARIOS_MANAGE);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [scenarios, setScenarios] = useState<ScenarioProfile[]>([]);
  const [promptTemplates, setPromptTemplates] = useState<PromptTemplate[]>([]);
  const [ruleSets, setRuleSets] = useState<AuditRuleSet[]>([]);
  const [knowledgeDocuments, setKnowledgeDocuments] = useState<KnowledgeDocument[]>([]);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editorMode, setEditorMode] = useState<'create' | 'edit'>('create');
  const [selectedScenario, setSelectedScenario] = useState<ScenarioProfile | null>(null);
  const [form, setForm] = useState<ScenarioFormState>(EMPTY_FORM);

  const loadData = async () => {
    try {
      setLoading(true);
      const [scenarioRes, promptRes, ruleRes, knowledgeRes] = await Promise.all([
        getScenarioProfiles({ page: 1, pageSize: 200 }),
        getPromptTemplates({ is_active: true }),
        getRuleSets({ is_active: true }),
        listKnowledgeDocuments(),
      ]);
      setScenarios(scenarioRes.items);
      setPromptTemplates(promptRes.items);
      setRuleSets(ruleRes.items);
      setKnowledgeDocuments(knowledgeRes.items);
    } catch (error) {
      toast.error(getErrorMessage(error, '加载场景数据失败'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const stats = useMemo(() => {
    return {
      total: scenarios.length,
      system: scenarios.filter((item) => item.is_system).length,
      custom: scenarios.filter((item) => !item.is_system).length,
      active: scenarios.filter((item) => item.is_active).length,
    };
  }, [scenarios]);

  const knowledgeLookup = useMemo(() => {
    return new Map(
      knowledgeDocuments.map((item) => [item.id, item.title || item.id]),
    );
  }, [knowledgeDocuments]);

  const openCreateDialog = () => {
    if (!canManageScenarios) {
      toast.error('当前账号没有管理场景的权限');
      return;
    }
    setEditorMode('create');
    setSelectedScenario(null);
    setForm(EMPTY_FORM);
    setEditorOpen(true);
  };

  const openEditDialog = (scenario: ScenarioProfile) => {
    if (!canManageScenarios) {
      toast.error('当前账号没有管理场景的权限');
      return;
    }
    if (scenario.is_system) {
      toast.info('系统场景建议通过复制后再编辑');
      return;
    }
    setEditorMode('edit');
    setSelectedScenario(scenario);
    setForm(buildFormState(scenario));
    setEditorOpen(true);
  };

  const handleSubmit = async () => {
    if (!canManageScenarios) {
      toast.error('当前账号没有管理场景的权限');
      return;
    }
    try {
      setSaving(true);
      const payload = {
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        objective_type: form.objective_type,
        prompt_template_id: form.prompt_template_id || null,
        rule_set_id: form.rule_set_id || null,
        knowledge_modules: form.knowledge_modules,
        is_active: form.is_active,
      };

      if (editorMode === 'create') {
        await createScenarioProfile({
          scenario_key: form.scenario_key.trim(),
          ...payload,
        });
        toast.success('场景已创建');
      } else if (selectedScenario) {
        await updateScenarioProfile(selectedScenario.id, payload);
        toast.success('场景已更新');
      }

      setEditorOpen(false);
      await loadData();
    } catch (error) {
      toast.error(getErrorMessage(error, '保存场景失败'));
    } finally {
      setSaving(false);
    }
  };

  const handleCopy = async (scenario: ScenarioProfile) => {
    if (!canManageScenarios) {
      toast.error('当前账号没有管理场景的权限');
      return;
    }
    try {
      await copyScenarioProfile(scenario.id, {});
      toast.success('场景已复制');
      await loadData();
    } catch (error) {
      toast.error(getErrorMessage(error, '复制场景失败'));
    }
  };

  const handleDelete = async (scenario: ScenarioProfile) => {
    if (!canManageScenarios) {
      toast.error('当前账号没有管理场景的权限');
      return;
    }
    if (scenario.is_system) {
      toast.error('系统场景不允许删除');
      return;
    }
    if (!window.confirm(`确认删除场景「${scenario.name}」吗？`)) {
      return;
    }
    try {
      await deleteScenarioProfile(scenario.id);
      toast.success('场景已删除');
      await loadData();
    } catch (error) {
      toast.error(getErrorMessage(error, '删除场景失败'));
    }
  };

  const handleToggleActive = async (scenario: ScenarioProfile) => {
    if (!canManageScenarios) {
      toast.error('当前账号没有管理场景的权限');
      return;
    }
    if (scenario.is_system) {
      toast.info('系统场景默认保持启用');
      return;
    }
    try {
      await updateScenarioProfile(scenario.id, {
        is_active: !scenario.is_active,
      });
      toast.success(scenario.is_active ? '场景已停用' : '场景已启用');
      await loadData();
    } catch (error) {
      toast.error(getErrorMessage(error, '更新场景状态失败'));
    }
  };

  const handleSetDefault = async (scenario: ScenarioProfile) => {
    if (!canManageScenarios) {
      toast.error('当前账号没有管理场景的权限');
      return;
    }
    try {
      await setDefaultScenarioProfile(scenario.id);
      toast.success('默认场景已更新');
      await loadData();
    } catch (error) {
      toast.error(getErrorMessage(error, '设置默认场景失败'));
    }
  };

  const toggleKnowledgeModule = (moduleId: string, checked: boolean) => {
    setForm((current) => {
      const nextModules = checked
        ? Array.from(new Set([...current.knowledge_modules, moduleId]))
        : current.knowledge_modules.filter((item) => item !== moduleId);
      return {
        ...current,
        knowledge_modules: nextModules,
      };
    });
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center cyber-bg-elevated">
        <div className="space-y-3 text-center">
          <Loader2 className="text-primary mx-auto h-6 w-6 animate-spin" />
          <p className="text-muted-foreground font-mono text-sm uppercase tracking-wider">
            加载场景中...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen space-y-6 p-6 cyber-bg-elevated">
      <div className="pointer-events-none absolute inset-0 cyber-grid-subtle" />

      <div className="relative z-10 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-foreground text-2xl font-bold">场景管理</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            用场景统一绑定 Prompt、规则集、知识模块与输出目标。
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => void loadData()} type="button" variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
          <Button disabled={!canManageScenarios} onClick={openCreateDialog} type="button">
            <Plus className="mr-2 h-4 w-4" />
            新建场景
          </Button>
        </div>
      </div>

      <div className="relative z-10 grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="cyber-card p-4">
          <p className="stat-label">场景总数</p>
          <p className="stat-value text-primary">{stats.total}</p>
        </div>
        <div className="cyber-card p-4">
          <p className="stat-label">系统预设</p>
          <p className="stat-value text-sky-400">{stats.system}</p>
        </div>
        <div className="cyber-card p-4">
          <p className="stat-label">自定义场景</p>
          <p className="stat-value text-emerald-400">{stats.custom}</p>
        </div>
        <div className="cyber-card p-4">
          <p className="stat-label">已启用</p>
          <p className="stat-value text-amber-400">{stats.active}</p>
        </div>
      </div>

      <div className="relative z-10 grid gap-4 xl:grid-cols-2">
        {scenarios.map((scenario) => (
          <div className="cyber-card space-y-4 p-5" key={scenario.id}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-foreground truncate text-lg font-semibold">
                    {scenario.name}
                  </h2>
                  <Badge className="cyber-badge-muted">{getObjectiveLabel(scenario.objective_type)}</Badge>
                  {scenario.is_system ? (
                    <Badge className="cyber-badge-info">系统</Badge>
                  ) : (
                    <Badge className="cyber-badge-success">自定义</Badge>
                  )}
                  {scenario.is_default && (
                    <Badge className="cyber-badge-warning">默认</Badge>
                  )}
                  {!scenario.is_active && (
                    <Badge className="bg-muted text-muted-foreground">已停用</Badge>
                  )}
                </div>
                <p className="text-muted-foreground mt-2 break-all font-mono text-xs">
                  {scenario.scenario_key}
                </p>
                <p className="text-muted-foreground mt-3 text-sm leading-6">
                  {scenario.description || '未填写场景描述。'}
                </p>
              </div>
              <div className="rounded-lg border border-primary/20 bg-primary/5 p-3">
                {scenario.is_system ? (
                  <Shield className="text-primary h-5 w-5" />
                ) : (
                  <Sparkles className="text-primary h-5 w-5" />
                )}
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-border bg-muted/40 p-3">
                <p className="text-muted-foreground text-xs uppercase">提示词模板</p>
                <p className="mt-2 text-sm text-foreground">
                  {scenario.prompt_template_name || '未绑定'}
                </p>
              </div>
              <div className="rounded-lg border border-border bg-muted/40 p-3">
                <p className="text-muted-foreground text-xs uppercase">规则集</p>
                <p className="mt-2 text-sm text-foreground">
                  {scenario.rule_set_name || '未绑定'}
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-muted-foreground text-xs uppercase">知识模块</p>
              <div className="flex flex-wrap gap-2">
                {scenario.knowledge_modules.length > 0 ? (
                  scenario.knowledge_modules.map((moduleId) => (
                    <Badge className="bg-muted text-foreground" key={moduleId}>
                      {knowledgeLookup.get(moduleId) || moduleId}
                    </Badge>
                  ))
                ) : (
                  <span className="text-muted-foreground text-sm">未绑定知识模块</span>
                )}
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
              <div className="flex items-center gap-2">
                <Switch
                  checked={scenario.is_active}
                  disabled={!canManageScenarios || scenario.is_system}
                  onCheckedChange={() => handleToggleActive(scenario)}
                />
                <span className="text-sm text-muted-foreground">
                  {scenario.is_active ? '已启用' : '已停用'}
                </span>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button onClick={() => handleCopy(scenario)} size="sm" type="button" variant="outline">
                  <Copy className="mr-2 h-4 w-4" />
                  复制
                </Button>
                <Button
                  disabled={!canManageScenarios || scenario.is_default}
                  onClick={() => handleSetDefault(scenario)}
                  size="sm"
                  type="button"
                  variant="outline"
                >
                  <Layers3 className="mr-2 h-4 w-4" />
                  设为默认
                </Button>
                <Button
                  disabled={!canManageScenarios || scenario.is_system}
                  onClick={() => openEditDialog(scenario)}
                  size="sm"
                  type="button"
                  variant="outline"
                >
                  编辑
                </Button>
                <Button
                  className="text-rose-600 hover:text-rose-700 dark:text-rose-400 dark:hover:text-rose-300"
                  disabled={!canManageScenarios || scenario.is_system}
                  onClick={() => handleDelete(scenario)}
                  size="sm"
                  type="button"
                  variant="outline"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  删除
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>

      <Dialog onOpenChange={setEditorOpen} open={editorOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editorMode === 'create' ? '新建场景' : '编辑场景'}</DialogTitle>
            <DialogDescription>
              场景创建后即可在所有 Agent 审计入口中复用。
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-5 px-6 pb-2">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="scenario-name">场景名称</Label>
                <Input
                  id="scenario-name"
                  onChange={(event) =>
                    setForm((current) => ({ ...current, name: event.target.value }))
                  }
                  placeholder="例如：并发资源代码梳理"
                  value={form.name}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="scenario-key">场景键</Label>
                <Input
                  disabled={editorMode === 'edit'}
                  id="scenario-key"
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      scenario_key: event.target.value.toLowerCase(),
                    }))
                  }
                  placeholder="例如：concurrency_inventory"
                  value={form.scenario_key}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="scenario-description">描述</Label>
              <Textarea
                id="scenario-description"
                onChange={(event) =>
                  setForm((current) => ({ ...current, description: event.target.value }))
                }
                placeholder="说明这个场景的适用范围、期望输出和聚焦方向"
                rows={4}
                value={form.description}
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>输出目标</Label>
                <Select
                  onValueChange={(value: ScenarioObjectiveType) =>
                    setForm((current) => ({ ...current, objective_type: value }))
                  }
                  value={form.objective_type}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="audit">漏洞审计</SelectItem>
                    <SelectItem value="inventory">代码梳理</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>是否启用</Label>
                <div className="flex h-10 items-center gap-3 rounded-md border border-border px-3">
                  <Switch
                    checked={form.is_active}
                    onCheckedChange={(checked) =>
                      setForm((current) => ({ ...current, is_active: checked }))
                    }
                  />
                  <span className="text-sm text-muted-foreground">
                    {form.is_active ? '启用中' : '已停用'}
                  </span>
                </div>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>提示词模板</Label>
                <Select
                  onValueChange={(value) =>
                    setForm((current) => ({
                      ...current,
                      prompt_template_id: value === 'none' ? '' : value,
                    }))
                  }
                  value={form.prompt_template_id || 'none'}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="不绑定模板" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">不绑定模板</SelectItem>
                    {promptTemplates.map((item) => (
                      <SelectItem key={item.id} value={item.id}>
                        {item.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>规则集</Label>
                <Select
                  onValueChange={(value) =>
                    setForm((current) => ({
                      ...current,
                      rule_set_id: value === 'none' ? '' : value,
                    }))
                  }
                  value={form.rule_set_id || 'none'}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="不绑定规则集" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">不绑定规则集</SelectItem>
                    {ruleSets.map((item) => (
                      <SelectItem key={item.id} value={item.id}>
                        {item.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-3">
              <Label>知识模块</Label>
              <div className="max-h-56 space-y-2 overflow-y-auto rounded-lg border border-border bg-muted/30 p-3">
                {knowledgeDocuments.length > 0 ? (
                  knowledgeDocuments.map((item) => {
                    const checked = form.knowledge_modules.includes(item.id);
                    return (
                      <label
                        className="flex items-start gap-3 rounded-md border border-transparent px-2 py-2 hover:border-border hover:bg-background/60"
                        key={item.id}
                      >
                        <Checkbox
                          checked={checked}
                          onCheckedChange={(nextChecked) =>
                            toggleKnowledgeModule(item.id, Boolean(nextChecked))
                          }
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-foreground">
                              {item.title || item.id}
                            </span>
                            <Badge className="cyber-badge-muted text-[11px]">
                              {item.category}
                            </Badge>
                          </div>
                          <p className="text-muted-foreground mt-1 break-all text-xs">
                            {item.id}
                          </p>
                        </div>
                      </label>
                    );
                  })
                ) : (
                  <p className="text-sm text-muted-foreground">暂无可用知识模块。</p>
                )}
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button onClick={() => setEditorOpen(false)} type="button" variant="ghost">
              取消
            </Button>
            <Button disabled={saving || !canManageScenarios} onClick={handleSubmit} type="button">
              {saving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  保存中...
                </>
              ) : editorMode === 'create' ? (
                '创建场景'
              ) : (
                '保存修改'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
