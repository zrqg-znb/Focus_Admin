/**
 * System Config Component
 * Cyberpunk Terminal Aesthetic
 */

import EmbeddingConfig from '@/components/agent/EmbeddingConfig';
import { KnowledgeBaseManager } from '@/components/system/KnowledgeBaseManager';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { api } from '@/shared/api/database';
import {
  clearKnownHosts,
  deleteSSHKey,
  generateSSHKey,
  getSSHKey,
  saveSSHKey,
  testSSHKey,
} from '@/shared/api/sshKeys';
import { useAuth } from '@/shared/context/AuthContext';
import { DEEPAUDIT_ACTION_CODES } from '@/shared/focus/focusPermission';
import {
  AlertCircle,
  BookOpen,
  Brain,
  CheckCircle2,
  Copy,
  Eye,
  EyeOff,
  Globe,
  Info,
  Key,
  PlayCircle,
  RotateCcw,
  Save,
  ServerCrash,
  Settings,
  Trash2,
  Wrench,
  Zap,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

// LLM Providers
const LLM_PROVIDERS = [
  {
    value: 'openai',
    label: 'OpenAI GPT',
    icon: '🟢',
    category: 'litellm',
    hint: 'gpt-5, gpt-5-mini, o3 等',
  },
  {
    value: 'claude',
    label: 'Anthropic Claude',
    icon: '🟣',
    category: 'litellm',
    hint: 'claude-sonnet-4.5, claude-opus-4 等',
  },
  {
    value: 'gemini',
    label: 'Google Gemini',
    icon: '🔵',
    category: 'litellm',
    hint: 'gemini-3-pro, gemini-3-flash 等',
  },
  {
    value: 'deepseek',
    label: 'DeepSeek',
    icon: '🔷',
    category: 'litellm',
    hint: 'deepseek-v3.1-terminus, deepseek-v3 等',
  },
  {
    value: 'qwen',
    label: '通义千问',
    icon: '🟠',
    category: 'litellm',
    hint: 'qwen3-max-instruct, qwen3-plus 等',
  },
  {
    value: 'zhipu',
    label: '智谱AI (GLM)',
    icon: '🔴',
    category: 'litellm',
    hint: 'glm-4.6, glm-4.5-flash 等',
  },
  {
    value: 'moonshot',
    label: 'Moonshot (Kimi)',
    icon: '🌙',
    category: 'litellm',
    hint: 'kimi-k2, kimi-k1.5 等',
  },
  {
    value: 'ollama',
    label: 'Ollama 本地',
    icon: '🖥️',
    category: 'litellm',
    hint: 'llama3.3-70b, qwen3-8b 等',
  },
  {
    value: 'baidu',
    label: '百度文心',
    icon: '📘',
    category: 'native',
    hint: 'ernie-4.5 (需要 API_KEY:SECRET_KEY)',
  },
  {
    value: 'minimax',
    label: 'MiniMax',
    icon: '⚡',
    category: 'native',
    hint: 'minimax-m2, minimax-m1 等',
  },
  {
    value: 'doubao',
    label: '字节豆包',
    icon: '🎯',
    category: 'native',
    hint: 'doubao-1.6-pro, doubao-1.5-pro 等',
  },
];

const VISIBLE_LLM_PROVIDERS = LLM_PROVIDERS.filter((item) =>
  ['deepseek', 'ollama', 'openai', 'qwen', 'zhipu'].includes(item.value),
);

interface SystemConfigData {
  llmProvider: string;
  llmApiKey: string;
  llmModel: string;
  llmBaseUrl: string;
  llmTimeout: number;
  llmTemperature: number;
  llmMaxTokens: number;
  // Agent超时配置
  llmFirstTokenTimeout: number;
  llmStreamTimeout: number;
  agentTimeout: number;
  subAgentTimeout: number;
  toolTimeout: number;
  codehubToken: string;
  maxAnalyzeFiles: number;
  llmConcurrency: number;
  llmGapMs: number;
  outputLanguage: string;
}

type UserConfigPayload = {
  llmConfig?: Partial<SystemConfigData> & {
    llmProvider?: string;
    provider?: string;
  };
  otherConfig?: Partial<
    Pick<
      SystemConfigData,
      | 'codehubToken'
      | 'llmConcurrency'
      | 'llmGapMs'
      | 'maxAnalyzeFiles'
      | 'outputLanguage'
    >
  >;
};

const DEFAULT_SYSTEM_CONFIG: SystemConfigData = {
  llmProvider: 'openai',
  llmApiKey: '',
  llmModel: '',
  llmBaseUrl: '',
  llmTimeout: 150_000,
  llmTemperature: 0.1,
  llmMaxTokens: 4096,
  llmFirstTokenTimeout: 90,
  llmStreamTimeout: 60,
  agentTimeout: 1800,
  subAgentTimeout: 600,
  toolTimeout: 60,
  codehubToken: '',
  maxAnalyzeFiles: 0,
  llmConcurrency: 3,
  llmGapMs: 2000,
  outputLanguage: 'zh-CN',
};

const INTERNAL_LLM_LABEL = '内网统一入口';

function toSystemConfigData(
  payload?: null | UserConfigPayload,
  fallback: SystemConfigData = DEFAULT_SYSTEM_CONFIG,
): SystemConfigData {
  const llmConfig = payload?.llmConfig ?? {};
  const otherConfig = payload?.otherConfig ?? {};

  return {
    llmProvider:
      llmConfig.llmProvider || llmConfig.provider || fallback.llmProvider,
    llmApiKey: llmConfig.llmApiKey || fallback.llmApiKey,
    llmModel: llmConfig.llmModel || fallback.llmModel,
    llmBaseUrl: llmConfig.llmBaseUrl || fallback.llmBaseUrl,
    llmTimeout: llmConfig.llmTimeout || fallback.llmTimeout,
    llmTemperature: llmConfig.llmTemperature ?? fallback.llmTemperature,
    llmMaxTokens: llmConfig.llmMaxTokens || fallback.llmMaxTokens,
    llmFirstTokenTimeout:
      llmConfig.llmFirstTokenTimeout || fallback.llmFirstTokenTimeout,
    llmStreamTimeout: llmConfig.llmStreamTimeout || fallback.llmStreamTimeout,
    agentTimeout: llmConfig.agentTimeout || fallback.agentTimeout,
    subAgentTimeout: llmConfig.subAgentTimeout || fallback.subAgentTimeout,
    toolTimeout: llmConfig.toolTimeout || fallback.toolTimeout,
    codehubToken:
      otherConfig.codehubToken ||
      (otherConfig as any).githubToken ||
      (otherConfig as any).gitlabToken ||
      (otherConfig as any).giteaToken ||
      fallback.codehubToken,
    maxAnalyzeFiles: otherConfig.maxAnalyzeFiles ?? fallback.maxAnalyzeFiles,
    llmConcurrency: otherConfig.llmConcurrency || fallback.llmConcurrency,
    llmGapMs: otherConfig.llmGapMs || fallback.llmGapMs,
    outputLanguage: otherConfig.outputLanguage || fallback.outputLanguage,
  };
}

export function SystemConfig() {
  const { hasAccess } = useAuth();
  const [config, setConfig] = useState<null | SystemConfigData>(null);
  const [loading, setLoading] = useState(true);
  const [showApiKey, setShowApiKey] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [testingLLM, setTestingLLM] = useState(false);
  const [llmTestResult, setLlmTestResult] = useState<null | {
    debug?: Record<string, unknown>;
    message: string;
    success: boolean;
  }>(null);
  const [showDebugInfo, setShowDebugInfo] = useState(true);

  // SSH Key states
  const [sshKey, setSSHKey] = useState<{
    fingerprint?: string;
    has_key: boolean;
    known_hosts?: string;
    public_key?: string;
    updated_at?: string;
  }>({ has_key: false });
  const [generatingKey, setGeneratingKey] = useState(false);
  const [deletingKey, setDeletingKey] = useState(false);
  const [clearingKnownHosts, setClearingKnownHosts] = useState(false);
  const [testingKey, setTestingKey] = useState(false);
  const [testRepoUrl, setTestRepoUrl] = useState('');
  const [sshTestResult, setSshTestResult] = useState<null | {
    message: string;
    output?: string;
    success: boolean;
  }>(null);
  const [sshKeyType, setSshKeyType] = useState<'ed25519' | 'rsa'>('ed25519');
  const [sshKeySize, setSshKeySize] = useState(4096);
  const [manualPrivateKey, setManualPrivateKey] = useState('');
  const [manualPublicKey, setManualPublicKey] = useState('');
  const [manualKnownHosts, setManualKnownHosts] = useState('');
  const [showDeleteKeyDialog, setShowDeleteKeyDialog] = useState(false);
  const canSaveSettings = hasAccess(DEEPAUDIT_ACTION_CODES.SETTINGS_SAVE);

  useEffect(() => {
    loadConfig();
    loadSSHKey();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const backendConfig =
        (await api.getUserConfig()) as null | UserConfigPayload;

      if (backendConfig) {
        const newConfig = toSystemConfigData(backendConfig);
        setConfig(newConfig);
      } else {
        console.warn('[SystemConfig] 后端返回空数据，使用默认配置');
        setConfig({ ...DEFAULT_SYSTEM_CONFIG });
      }
    } catch (error) {
      console.error('Failed to load config:', error);
      setConfig({ ...DEFAULT_SYSTEM_CONFIG });
    } finally {
      setLoading(false);
    }
  };

  // SSH Key functions
  const loadSSHKey = async () => {
    try {
      const data = await getSSHKey();
      setSSHKey(data);
    } catch (error) {
      console.error('Failed to load SSH key:', error);
    }
  };

  const handleGenerateSSHKey = async () => {
    if (!canSaveSettings) {
      toast.error('当前账号没有保存设置的权限');
      return;
    }
    try {
      setGeneratingKey(true);
      const data = await generateSSHKey({
        keyType: sshKeyType,
        keySize: sshKeyType === 'rsa' ? sshKeySize : 4096,
      });
      await loadSSHKey();
      setSshTestResult(null);
      toast.success(data.message || 'SSH 密钥生成成功');
    } catch (error: any) {
      console.error('Failed to generate SSH key:', error);
      toast.error(error.response?.data?.detail || '生成 SSH 密钥失败');
    } finally {
      setGeneratingKey(false);
    }
  };

  const handleImportSSHKey = async () => {
    if (!canSaveSettings) {
      toast.error('当前账号没有保存设置的权限');
      return;
    }
    if (!manualPrivateKey.trim()) {
      toast.error('请先粘贴 SSH 私钥');
      return;
    }
    if (!manualPublicKey.trim()) {
      toast.error('请先粘贴 SSH 公钥');
      return;
    }
    try {
      setGeneratingKey(true);
      const data = await saveSSHKey({
        private_key: manualPrivateKey.trim(),
        public_key: manualPublicKey.trim(),
        known_hosts: manualKnownHosts.trim(),
      });
      setSSHKey(data);
      setSshTestResult(null);
      toast.success('SSH 密钥已导入');
    } catch (error: any) {
      console.error('Failed to import SSH key:', error);
      toast.error(error.response?.data?.detail || '导入 SSH 密钥失败');
    } finally {
      setGeneratingKey(false);
    }
  };

  const handleDeleteSSHKey = async () => {
    if (!canSaveSettings) {
      toast.error('当前账号没有保存设置的权限');
      return;
    }
    try {
      setDeletingKey(true);
      await deleteSSHKey();
      setSSHKey({ has_key: false });
      setManualPrivateKey('');
      setManualPublicKey('');
      setManualKnownHosts('');
      setTestRepoUrl('');
      setSshTestResult(null);
      toast.success('SSH密钥已删除');
      setShowDeleteKeyDialog(false);
    } catch (error: any) {
      console.error('Failed to delete SSH key:', error);
      toast.error(error.response?.data?.detail || '删除SSH密钥失败');
    } finally {
      setDeletingKey(false);
    }
  };

  const handleTestSSHKey = async () => {
    if (!testRepoUrl.trim()) {
      toast.error('请输入用于测试的 SSH 仓库地址');
      return;
    }
    try {
      setTestingKey(true);
      const result = await testSSHKey(testRepoUrl.trim());
      setSshTestResult(result);
      if (result.success) {
        toast.success(result.message || 'SSH 连接测试成功');
      } else {
        toast.error(result.message || 'SSH 连接测试失败');
      }
      await loadSSHKey();
    } catch (error: any) {
      console.error('Failed to test SSH key:', error);
      const message = error.response?.data?.detail || '测试 SSH 连接失败';
      setSshTestResult({ success: false, message });
      toast.error(message);
    } finally {
      setTestingKey(false);
    }
  };

  const handleClearKnownHosts = async () => {
    if (!canSaveSettings) {
      toast.error('当前账号没有保存设置的权限');
      return;
    }
    try {
      setClearingKnownHosts(true);
      const result = await clearKnownHosts();
      if (result.success) {
        toast.success(result.message || 'known_hosts已清理');
        await loadSSHKey();
      } else {
        toast.error('清理known_hosts失败');
      }
    } catch (error: any) {
      console.error('Failed to clear known_hosts:', error);
      toast.error(error.response?.data?.detail || '清理known_hosts失败');
    } finally {
      setClearingKnownHosts(false);
    }
  };

  const handleCopyPublicKey = () => {
    if (sshKey.public_key) {
      navigator.clipboard.writeText(sshKey.public_key);
      toast.success('公钥已复制到剪贴板');
    }
  };

  const saveConfig = async () => {
    if (!config) return;
    if (!canSaveSettings) {
      toast.error('当前账号没有保存设置的权限');
      return;
    }
    try {
      const savedConfig = (await api.updateUserConfig({
        llmConfig: {
          llmProvider: config.llmProvider,
          llmApiKey: config.llmApiKey,
          llmModel: config.llmModel,
          llmBaseUrl: config.llmBaseUrl,
          llmTimeout: config.llmTimeout,
          llmTemperature: config.llmTemperature,
          llmMaxTokens: config.llmMaxTokens,
          // Agent超时配置
          llmFirstTokenTimeout: config.llmFirstTokenTimeout,
          llmStreamTimeout: config.llmStreamTimeout,
          agentTimeout: config.agentTimeout,
          subAgentTimeout: config.subAgentTimeout,
          toolTimeout: config.toolTimeout,
        },
        otherConfig: {
          codehubToken: config.codehubToken,
          maxAnalyzeFiles: config.maxAnalyzeFiles,
          llmConcurrency: config.llmConcurrency,
          llmGapMs: config.llmGapMs,
          outputLanguage: config.outputLanguage,
        },
      })) as null | UserConfigPayload;

      if (savedConfig) {
        setConfig(toSystemConfigData(savedConfig, config));
      }

      setHasChanges(false);
      toast.success('配置已保存！');
    } catch (error) {
      toast.error(
        `保存失败: ${error instanceof Error ? error.message : '未知错误'}`,
      );
    }
  };

  const resetConfig = async () => {
    if (!canSaveSettings) {
      toast.error('当前账号没有保存设置的权限');
      return;
    }
    // eslint-disable-next-line no-alert
    if (!window.confirm('确定要重置为默认配置吗？')) return;
    try {
      await api.deleteUserConfig();
      await loadConfig();
      setHasChanges(false);
      toast.success('已重置为默认配置');
    } catch (error) {
      toast.error(
        `重置失败: ${error instanceof Error ? error.message : '未知错误'}`,
      );
    }
  };

  const updateConfig = (
    key: keyof SystemConfigData,
    value: number | string,
  ) => {
    if (!config) return;
    setConfig((prev) => (prev ? { ...prev, [key]: value } : null));
    setHasChanges(true);
  };

  const testLLMConnection = async () => {
    if (!config) return;
    if (!config.llmBaseUrl.trim()) {
      toast.error('请先填写内网中转地址');
      return;
    }
    setTestingLLM(true);
    setLlmTestResult(null);
    try {
      const result = await api.testLLMConnection({
        provider: config.llmProvider,
        apiKey: config.llmApiKey,
        model: config.llmModel || undefined,
        baseUrl: config.llmBaseUrl || undefined,
      });
      setLlmTestResult(result);
      if (result.success) toast.success(`连接成功！模型: ${result.model}`);
      else toast.error(`连接失败: ${result.message}`);
    } catch (error) {
      const msg = error instanceof Error ? error.message : '未知错误';
      setLlmTestResult({ success: false, message: msg });
      toast.error(`测试失败: ${msg}`);
    } finally {
      setTestingLLM(false);
    }
  };

  if (loading || !config) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="space-y-4 text-center">
          <div className="loading-spinner mx-auto" />
          <p className="text-muted-foreground font-mono text-sm uppercase tracking-wider">
            加载配置中...
          </p>
        </div>
      </div>
    );
  }

  const isConfigured =
    config.llmBaseUrl.trim() !== '' ||
    config.llmApiKey.trim() !== '' ||
    config.llmModel.trim() !== '';

  return (
    <div className="space-y-6">
      {/* Status Bar */}
      <div
        className={`cyber-card p-4 ${isConfigured ? 'border-emerald-500/30' : 'border-amber-500/30'}`}
      >
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Info className="h-5 w-5 text-sky-400" />
            <span className="font-mono text-sm">
              {isConfigured ? (
                <span className="flex items-center gap-2 text-emerald-400">
                  <CheckCircle2 className="h-4 w-4" /> 内网统一入口已配置
                </span>
              ) : (
                <span className="flex items-center gap-2 text-amber-400">
                  <AlertCircle className="h-4 w-4" /> 请配置内网中转地址和模型
                </span>
              )}
            </span>
          </div>
          <div className="flex gap-2">
            {hasChanges && canSaveSettings && (
              <Button
                className="cyber-btn-primary h-8"
                onClick={saveConfig}
                size="sm"
              >
                <Save className="mr-2 h-3 w-3" /> 保存
              </Button>
            )}
            {canSaveSettings && (
              <Button
                className="cyber-btn-ghost h-8"
                onClick={resetConfig}
                size="sm"
                variant="outline"
              >
                <RotateCcw className="mr-2 h-3 w-3" /> 重置
              </Button>
            )}
          </div>
        </div>
      </div>

      <Tabs className="w-full" defaultValue="llm">
        <TabsList className="bg-muted border-border mb-6 grid h-auto w-full grid-cols-5 gap-1 rounded-lg border p-1">
          <TabsTrigger
            className="data-[state=active]:bg-primary data-[state=active]:text-foreground text-muted-foreground flex items-center gap-2 rounded py-2.5 font-mono text-xs font-bold uppercase transition-all"
            value="llm"
          >
            <Zap className="h-3 w-3" /> LLM 配置
          </TabsTrigger>
          <TabsTrigger
            className="data-[state=active]:bg-primary data-[state=active]:text-foreground text-muted-foreground flex items-center gap-2 rounded py-2.5 font-mono text-xs font-bold uppercase transition-all"
            value="embedding"
          >
            <Brain className="h-3 w-3" /> 嵌入模型
          </TabsTrigger>
          <TabsTrigger
            className="data-[state=active]:bg-primary data-[state=active]:text-foreground text-muted-foreground flex items-center gap-2 rounded py-2.5 font-mono text-xs font-bold uppercase transition-all"
            value="analysis"
          >
            <Settings className="h-3 w-3" /> 分析参数
          </TabsTrigger>
          <TabsTrigger
            className="data-[state=active]:bg-primary data-[state=active]:text-foreground text-muted-foreground flex items-center gap-2 rounded py-2.5 font-mono text-xs font-bold uppercase transition-all"
            value="git"
          >
            <Globe className="h-3 w-3" /> Git 集成
          </TabsTrigger>
          <TabsTrigger
            className="data-[state=active]:bg-primary data-[state=active]:text-foreground text-muted-foreground flex items-center gap-2 rounded py-2.5 font-mono text-xs font-bold uppercase transition-all"
            value="knowledge"
          >
            <BookOpen className="h-3 w-3" /> 知识库
          </TabsTrigger>
        </TabsList>

        {/* LLM Config */}
        <TabsContent className="space-y-6" value="llm">
          <div className="cyber-card space-y-6 p-6">
            <div className="bg-muted/50 border-border flex items-center justify-between gap-4 rounded-lg border p-4">
              <div>
                <p className="text-muted-foreground text-xs font-bold uppercase">
                  LLM 入口
                </p>
                <p className="text-foreground font-mono text-sm">
                  {config.llmProvider || INTERNAL_LLM_LABEL}
                </p>
              </div>
              <div className="text-muted-foreground text-right text-xs">
                可按需选择 `openai / qwen / deepseek /
                zhipu`；测试连接只验证当前入口，不再自动切换到 Ollama
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
              <div className="space-y-2">
                <Label className="text-muted-foreground text-xs font-bold uppercase">
                  Provider
                </Label>
                <Select
                  onValueChange={(v) => updateConfig('llmProvider', v)}
                  value={config.llmProvider}
                >
                  <SelectTrigger className="cyber-input h-10">
                    <SelectValue placeholder="选择 Provider" />
                  </SelectTrigger>
                  <SelectContent className="cyber-dialog border-border">
                    {VISIBLE_LLM_PROVIDERS.map((item) => (
                      <SelectItem
                        className="font-mono"
                        key={item.value}
                        value={item.value}
                      >
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-muted-foreground text-xs font-bold uppercase">
                  内网中转地址
                </Label>
                <Input
                  className="cyber-input h-10"
                  onChange={(e) => updateConfig('llmBaseUrl', e.target.value)}
                  placeholder="例如 https://llm-gateway.intra.example/v1"
                  value={config.llmBaseUrl}
                />
              </div>
              <div className="space-y-2">
                <Label className="text-muted-foreground text-xs font-bold uppercase">
                  API Key
                </Label>
                <div className="flex gap-2">
                  <Input
                    className="cyber-input h-10"
                    onChange={(e) => updateConfig('llmApiKey', e.target.value)}
                    placeholder="中转服务提供的 Key"
                    type={showApiKey ? 'text' : 'password'}
                    value={config.llmApiKey}
                  />
                  <Button
                    className="cyber-btn-ghost h-10 w-10"
                    onClick={() => setShowApiKey(!showApiKey)}
                    size="icon"
                    variant="outline"
                  >
                    {showApiKey ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>
              <div className="space-y-2">
                <Label className="text-muted-foreground text-xs font-bold uppercase">
                  模型名称
                </Label>
                <Input
                  className="cyber-input h-10"
                  onChange={(e) => updateConfig('llmModel', e.target.value)}
                  placeholder="例如 gpt-5, qwen3-max-instruct, deepseek-v3.1-terminus"
                  value={config.llmModel}
                />
              </div>
            </div>

            {/* Test Connection */}
            <div className="border-border flex flex-wrap items-center justify-between gap-4 border-t border-dashed pt-4">
              <div className="text-sm">
                <span className="text-foreground font-bold">测试连接</span>
                <span className="text-muted-foreground ml-2">
                  仅验证当前 Provider / Base URL / API Key
                </span>
              </div>
              <Button
                className="cyber-btn-primary h-10"
                disabled={testingLLM || !isConfigured}
                onClick={testLLMConnection}
              >
                {testingLLM ? (
                  <>
                    <div className="loading-spinner mr-2 h-4 w-4" />
                    测试中...
                  </>
                ) : (
                  <>
                    <PlayCircle className="mr-2 h-4 w-4" />
                    测试
                  </>
                )}
              </Button>
            </div>
            {llmTestResult && (
              <div
                className={`rounded-lg p-3 ${llmTestResult.success ? 'border border-emerald-500/30 bg-emerald-500/10' : 'border border-rose-500/30 bg-rose-500/10'}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm">
                    {llmTestResult.success ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-rose-400" />
                    )}
                    <span
                      className={
                        llmTestResult.success
                          ? 'text-emerald-300/80'
                          : 'text-rose-300/80'
                      }
                    >
                      {llmTestResult.message}
                    </span>
                  </div>
                  {llmTestResult.debug && (
                    <button
                      className="text-muted-foreground hover:text-foreground text-xs underline"
                      onClick={() => setShowDebugInfo(!showDebugInfo)}
                    >
                      {showDebugInfo ? '隐藏调试信息' : '显示调试信息'}
                    </button>
                  )}
                </div>
                {showDebugInfo && llmTestResult.debug && (
                  <div className="border-border/50 mt-3 border-t pt-3">
                    <div className="text-muted-foreground space-y-1 font-mono text-xs">
                      <div className="text-foreground mb-2 font-bold">
                        连接信息:
                      </div>
                      <div>
                        Provider:{' '}
                        <span className="text-foreground">
                          {String(
                            llmTestResult.debug.provider_used ||
                              llmTestResult.debug.provider_requested ||
                              'openai',
                          )}
                        </span>
                      </div>
                      <div>
                        Model:{' '}
                        <span className="text-foreground">
                          {String(
                            llmTestResult.debug.model_used ||
                              llmTestResult.debug.model_requested ||
                              'N/A',
                          )}
                        </span>
                      </div>
                      <div>
                        Base URL:{' '}
                        <span className="text-foreground">
                          {String(
                            llmTestResult.debug.base_url_used ||
                              llmTestResult.debug.base_url_requested ||
                              '(default)',
                          )}
                        </span>
                      </div>
                      <div>
                        Adapter:{' '}
                        <span className="text-foreground">
                          {String(llmTestResult.debug.adapter_type || 'N/A')}
                        </span>
                      </div>
                      <div>
                        API Key:{' '}
                        <span className="text-foreground">
                          {String(llmTestResult.debug.api_key_prefix)} (长度:{' '}
                          {String(llmTestResult.debug.api_key_length)})
                        </span>
                      </div>
                      <div>
                        耗时:{' '}
                        <span className="text-foreground">
                          {String(llmTestResult.debug.elapsed_time_ms || 'N/A')}{' '}
                          ms
                        </span>
                      </div>

                      {/* 用户保存的配置参数 */}
                      {llmTestResult.debug.saved_config && (
                        <div className="border-border/30 mt-3 border-t pt-2">
                          <div className="mb-2 font-bold text-cyan-400">
                            已保存的配置参数:
                          </div>
                          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                            <div>
                              温度:{' '}
                              <span className="text-foreground">
                                {String(
                                  (
                                    llmTestResult.debug.saved_config as Record<
                                      string,
                                      unknown
                                    >
                                  ).temperature ?? 'N/A',
                                )}
                              </span>
                            </div>
                            <div>
                              最大Tokens:{' '}
                              <span className="text-foreground">
                                {String(
                                  (
                                    llmTestResult.debug.saved_config as Record<
                                      string,
                                      unknown
                                    >
                                  ).max_tokens ?? 'N/A',
                                )}
                              </span>
                            </div>
                            <div>
                              超时:{' '}
                              <span className="text-foreground">
                                {String(
                                  (
                                    llmTestResult.debug.saved_config as Record<
                                      string,
                                      unknown
                                    >
                                  ).timeout_ms ?? 'N/A',
                                )}{' '}
                                ms
                              </span>
                            </div>
                            <div>
                              请求间隔:{' '}
                              <span className="text-foreground">
                                {String(
                                  (
                                    llmTestResult.debug.saved_config as Record<
                                      string,
                                      unknown
                                    >
                                  ).gap_ms ?? 'N/A',
                                )}{' '}
                                ms
                              </span>
                            </div>
                            <div>
                              并发数:{' '}
                              <span className="text-foreground">
                                {String(
                                  (
                                    llmTestResult.debug.saved_config as Record<
                                      string,
                                      unknown
                                    >
                                  ).concurrency ?? 'N/A',
                                )}
                              </span>
                            </div>
                            <div>
                              最大文件数:{' '}
                              <span className="text-foreground">
                                {String(
                                  (
                                    llmTestResult.debug.saved_config as Record<
                                      string,
                                      unknown
                                    >
                                  ).max_analyze_files ?? 'N/A',
                                )}
                              </span>
                            </div>
                            <div>
                              输出语言:{' '}
                              <span className="text-foreground">
                                {String(
                                  (
                                    llmTestResult.debug.saved_config as Record<
                                      string,
                                      unknown
                                    >
                                  ).output_language ?? 'N/A',
                                )}
                              </span>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* 测试时实际使用的参数 */}
                      {llmTestResult.debug.test_params && (
                        <div className="border-border/30 mt-2 border-t pt-2">
                          <div className="mb-2 font-bold text-emerald-400">
                            测试时使用的参数:
                          </div>
                          <div className="grid grid-cols-3 gap-x-4">
                            <div>
                              温度:{' '}
                              <span className="text-foreground">
                                {String(
                                  (
                                    llmTestResult.debug.test_params as Record<
                                      string,
                                      unknown
                                    >
                                  ).temperature ?? 'N/A',
                                )}
                              </span>
                            </div>
                            <div>
                              超时:{' '}
                              <span className="text-foreground">
                                {String(
                                  (
                                    llmTestResult.debug.test_params as Record<
                                      string,
                                      unknown
                                    >
                                  ).timeout ?? 'N/A',
                                )}
                                s
                              </span>
                            </div>
                            <div>
                              MaxTokens:{' '}
                              <span className="text-foreground">
                                {String(
                                  (
                                    llmTestResult.debug.test_params as Record<
                                      string,
                                      unknown
                                    >
                                  ).max_tokens ?? 'N/A',
                                )}
                              </span>
                            </div>
                          </div>
                        </div>
                      )}

                      {llmTestResult.debug.error_category && (
                        <div className="mt-2">
                          错误类型:{' '}
                          <span className="text-rose-400">
                            {String(llmTestResult.debug.error_category)}
                          </span>
                        </div>
                      )}
                      {llmTestResult.debug.error_type && (
                        <div>
                          异常类型:{' '}
                          <span className="text-rose-400">
                            {String(llmTestResult.debug.error_type)}
                          </span>
                        </div>
                      )}
                      {llmTestResult.debug.status_code && (
                        <div>
                          HTTP 状态码:{' '}
                          <span className="text-rose-400">
                            {String(llmTestResult.debug.status_code)}
                          </span>
                        </div>
                      )}
                      {llmTestResult.debug.api_response && (
                        <div className="mt-2">
                          <div className="font-bold text-amber-400">
                            API 服务器返回:
                          </div>
                          <pre className="mt-1 overflow-x-auto rounded border border-amber-500/30 bg-amber-500/10 p-2 text-xs">
                            {String(llmTestResult.debug.api_response)}
                          </pre>
                        </div>
                      )}
                      {llmTestResult.debug.error_message && (
                        <div className="mt-2">
                          <div className="text-foreground font-bold">
                            完整错误信息:
                          </div>
                          <pre className="bg-background/50 mt-1 max-h-32 overflow-x-auto overflow-y-auto rounded p-2 text-xs">
                            {String(llmTestResult.debug.error_message)}
                          </pre>
                        </div>
                      )}
                      {llmTestResult.debug.traceback && (
                        <details className="mt-2">
                          <summary className="text-muted-foreground hover:text-foreground cursor-pointer">
                            完整堆栈跟踪
                          </summary>
                          <pre className="bg-background/50 mt-1 max-h-48 overflow-x-auto overflow-y-auto whitespace-pre-wrap rounded p-2 text-xs">
                            {String(llmTestResult.debug.traceback)}
                          </pre>
                        </details>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Advanced Parameters */}
            <details className="border-border border-t border-dashed pt-4" open>
              <summary className="hover:text-primary text-muted-foreground cursor-pointer text-sm font-bold uppercase">
                高级参数
              </summary>

              {/* LLM基础参数 */}
              <div className="mb-2 mt-4">
                <span className="text-muted-foreground text-xs font-semibold uppercase">
                  LLM 基础参数
                </span>
              </div>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label className="text-muted-foreground text-xs uppercase">
                    请求超时 (毫秒)
                  </Label>
                  <Input
                    className="cyber-input h-10"
                    onChange={(e) =>
                      updateConfig('llmTimeout', Number(e.target.value))
                    }
                    type="number"
                    value={config.llmTimeout}
                  />
                  <p className="text-muted-foreground text-xs">
                    单次LLM请求的超时时间
                  </p>
                </div>
                <div className="space-y-2">
                  <Label className="text-muted-foreground text-xs uppercase">
                    温度 (0-2)
                  </Label>
                  <Input
                    className="cyber-input h-10"
                    max="2"
                    min="0"
                    onChange={(e) =>
                      updateConfig('llmTemperature', Number(e.target.value))
                    }
                    step="0.1"
                    type="number"
                    value={config.llmTemperature}
                  />
                  <p className="text-muted-foreground text-xs">
                    控制输出随机性，越低越确定
                  </p>
                </div>
                <div className="space-y-2">
                  <Label className="text-muted-foreground text-xs uppercase">
                    最大 Tokens
                  </Label>
                  <Input
                    className="cyber-input h-10"
                    onChange={(e) =>
                      updateConfig('llmMaxTokens', Number(e.target.value))
                    }
                    type="number"
                    value={config.llmMaxTokens}
                  />
                  <p className="text-muted-foreground text-xs">
                    单次请求最大输出Token数
                  </p>
                </div>
              </div>

              {/* Agent超时配置 */}
              <div className="mb-2 mt-6">
                <span className="text-muted-foreground text-xs font-semibold uppercase">
                  Agent 超时配置
                </span>
              </div>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label className="text-muted-foreground text-xs uppercase">
                    首Token超时 (秒)
                  </Label>
                  <Input
                    className="cyber-input h-10"
                    onChange={(e) =>
                      updateConfig(
                        'llmFirstTokenTimeout',
                        Number(e.target.value),
                      )
                    }
                    type="number"
                    value={config.llmFirstTokenTimeout}
                  />
                  <p className="text-muted-foreground text-xs">
                    等待LLM首个Token的超时时间
                  </p>
                </div>
                <div className="space-y-2">
                  <Label className="text-muted-foreground text-xs uppercase">
                    流式超时 (秒)
                  </Label>
                  <Input
                    className="cyber-input h-10"
                    onChange={(e) =>
                      updateConfig('llmStreamTimeout', Number(e.target.value))
                    }
                    type="number"
                    value={config.llmStreamTimeout}
                  />
                  <p className="text-muted-foreground text-xs">
                    流式输出中两个Token间的超时
                  </p>
                </div>
                <div className="space-y-2">
                  <Label className="text-muted-foreground text-xs uppercase">
                    工具超时 (秒)
                  </Label>
                  <Input
                    className="cyber-input h-10"
                    onChange={(e) =>
                      updateConfig('toolTimeout', Number(e.target.value))
                    }
                    type="number"
                    value={config.toolTimeout}
                  />
                  <p className="text-muted-foreground text-xs">
                    单个工具执行的默认超时时间
                  </p>
                </div>
                <div className="space-y-2">
                  <Label className="text-muted-foreground text-xs uppercase">
                    子Agent超时 (秒)
                  </Label>
                  <Input
                    className="cyber-input h-10"
                    onChange={(e) =>
                      updateConfig('subAgentTimeout', Number(e.target.value))
                    }
                    type="number"
                    value={config.subAgentTimeout}
                  />
                  <p className="text-muted-foreground text-xs">
                    子Agent (Recon/Analysis/Verification) 超时
                  </p>
                </div>
                <div className="space-y-2">
                  <Label className="text-muted-foreground text-xs uppercase">
                    总超时 (秒)
                  </Label>
                  <Input
                    className="cyber-input h-10"
                    onChange={(e) =>
                      updateConfig('agentTimeout', Number(e.target.value))
                    }
                    type="number"
                    value={config.agentTimeout}
                  />
                  <p className="text-muted-foreground text-xs">
                    整个Agent审计任务的最大时间
                  </p>
                </div>
              </div>
            </details>
          </div>

          {/* Usage Notes */}
          <div className="bg-muted border-border space-y-2 rounded-lg border p-4 text-xs">
            <p className="text-muted-foreground flex items-center gap-2 font-bold uppercase">
              <Info className="h-4 w-4 text-sky-400" />
              配置说明
            </p>
            <p className="text-muted-foreground">
              • <strong className="text-muted-foreground">统一入口</strong>:
              前端只保留内网中转配置，“测试连接”只验证当前填写的入口
            </p>
            <p className="text-muted-foreground">
              • <strong className="text-muted-foreground">API 中转站</strong>:
              在 Base URL 填入中转站地址即可，API Key 填中转站提供的 Key
            </p>
            <p className="text-muted-foreground">
              • <strong className="text-muted-foreground">兼容历史配置</strong>:
              旧 provider 会被加载并归一为统一入口，不会再作为可选项展示
            </p>
          </div>
        </TabsContent>

        {/* Embedding Config */}
        <TabsContent className="space-y-6" value="embedding">
          <EmbeddingConfig />
        </TabsContent>

        {/* Analysis Parameters */}
        <TabsContent className="space-y-6" value="analysis">
          <div className="cyber-card space-y-6 p-6">
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div className="space-y-2">
                <Label className="text-muted-foreground text-xs font-bold uppercase">
                  最大分析文件数
                </Label>
                <Input
                  className="cyber-input h-10"
                  onChange={(e) =>
                    updateConfig('maxAnalyzeFiles', Number(e.target.value))
                  }
                  type="number"
                  value={config.maxAnalyzeFiles}
                />
                <p className="text-muted-foreground text-xs">
                  单次任务最多处理的文件数量
                </p>
              </div>
              <div className="space-y-2">
                <Label className="text-muted-foreground text-xs font-bold uppercase">
                  LLM 并发数
                </Label>
                <Input
                  className="cyber-input h-10"
                  onChange={(e) =>
                    updateConfig('llmConcurrency', Number(e.target.value))
                  }
                  type="number"
                  value={config.llmConcurrency}
                />
                <p className="text-muted-foreground text-xs">
                  同时发送的 LLM 请求数量
                </p>
              </div>
              <div className="space-y-2">
                <Label className="text-muted-foreground text-xs font-bold uppercase">
                  请求间隔 (毫秒)
                </Label>
                <Input
                  className="cyber-input h-10"
                  onChange={(e) =>
                    updateConfig('llmGapMs', Number(e.target.value))
                  }
                  type="number"
                  value={config.llmGapMs}
                />
                <p className="text-muted-foreground text-xs">
                  每个请求之间的延迟时间
                </p>
              </div>
              <div className="space-y-2">
                <Label className="text-muted-foreground text-xs font-bold uppercase">
                  输出语言
                </Label>
                <Select
                  onValueChange={(v) => updateConfig('outputLanguage', v)}
                  value={config.outputLanguage}
                >
                  <SelectTrigger className="cyber-input h-10">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="cyber-dialog border-border">
                    <SelectItem className="font-mono" value="zh-CN">
                      🇨🇳 中文
                    </SelectItem>
                    <SelectItem className="font-mono" value="en-US">
                      🇺🇸 English
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-muted-foreground text-xs">
                  代码审查结果的输出语言
                </p>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* Git Integration */}
        <TabsContent className="space-y-6" value="git">
          <div className="cyber-card space-y-6 p-6">
            <div className="space-y-2">
              <Label className="text-muted-foreground text-xs font-bold uppercase">
                CodeHub Token (可选)
              </Label>
              <Input
                className="cyber-input h-10"
                onChange={(e) => updateConfig('codehubToken', e.target.value)}
                placeholder="输入 CodeHub / 内网 Git Token"
                type="password"
                value={config.codehubToken}
              />
              <p className="text-muted-foreground text-xs">
                用于访问 CodeHub 或其他内网 Git 私有仓库。旧的
                GitHub/GitLab/Gitea Token 会兼容读取，但新配置统一写入这个字段。
              </p>
            </div>
            <div className="bg-muted border-border rounded-lg border p-4 text-xs">
              <p className="text-muted-foreground mb-2 flex items-center gap-2 font-bold">
                <Info className="h-4 w-4 text-sky-400" />
                提示
              </p>
              <p className="text-muted-foreground">• 公开仓库无需配置 Token</p>
              <p className="text-muted-foreground">
                • 私有 CodeHub / 内网 Git 仓库建议配置统一 Token
              </p>
              <p className="text-muted-foreground">
                • 如果你们使用 SSH 拉取，也可以只配置下方 SSH 密钥
              </p>
            </div>
          </div>

          {/* SSH Key Management */}
          <div className="cyber-card space-y-4 p-6">
            <div className="mb-2 flex items-center gap-3">
              <Key className="h-5 w-5 text-emerald-400" />
              <h3 className="text-foreground text-lg font-bold uppercase tracking-wider">
                SSH 密钥管理
              </h3>
            </div>

            <div className="flex items-start gap-3 rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-4">
              <div className="mt-0.5 flex-shrink-0">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/20">
                  <Key className="h-4 w-4 text-emerald-400" />
                </div>
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-foreground mb-1 text-sm font-medium">
                  使用 SSH 密钥访问 Git 仓库
                </p>
                <p className="text-muted-foreground text-xs leading-relaxed">
                  生成 SSH 密钥对后，将公钥添加到 CodeHub 或内网 Git
                  服务，即可使用 SSH URL 访问私有仓库。私钥将被加密存储。
                </p>
              </div>
            </div>

            {sshKey.has_key ? (
              <div className="space-y-4">
                {/* Public Key Display */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label className="text-muted-foreground flex items-center gap-2 text-xs font-bold uppercase">
                      <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                      SSH 公钥
                    </Label>
                    <Button
                      className="h-8 text-xs"
                      onClick={handleCopyPublicKey}
                      size="sm"
                      variant="ghost"
                    >
                      <Copy className="mr-1 h-3 w-3" />
                      复制
                    </Button>
                  </div>
                  <Textarea
                    className="cyber-input h-24 resize-none font-mono text-xs"
                    readOnly
                    value={sshKey.public_key || ''}
                  />

                  {/* 显示指纹 */}
                  {sshKey.fingerprint && (
                    <div className="bg-muted/50 border-border rounded border p-3">
                      <Label className="text-muted-foreground mb-1 block text-xs font-bold uppercase">
                        公钥指纹 (SHA256)
                      </Label>
                      <code className="break-all font-mono text-xs text-emerald-400">
                        {sshKey.fingerprint}
                      </code>
                    </div>
                  )}

                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                    <div className="bg-muted/50 border-border rounded border p-3">
                      <Label className="text-muted-foreground mb-1 block text-xs font-bold uppercase">
                        最后更新时间
                      </Label>
                      <div className="text-foreground font-mono text-xs">
                        {sshKey.updated_at || '未知'}
                      </div>
                    </div>
                    <div className="bg-muted/50 border-border rounded border p-3">
                      <Label className="text-muted-foreground mb-1 block text-xs font-bold uppercase">
                        known_hosts
                      </Label>
                      <div className="text-foreground font-mono text-xs">
                        {sshKey.known_hosts
                          ? `已记录 ${sshKey.known_hosts.split('\n').filter(Boolean).length} 条主机指纹`
                          : '尚未缓存'}
                      </div>
                    </div>
                  </div>

                  <p className="text-muted-foreground text-xs">
                    请将此公钥添加到 CodeHub 或你们的内网 Git 服务 SSH
                    公钥列表中
                  </p>
                </div>

                <div className="border-border space-y-2 border-t pt-4">
                  <Label className="text-muted-foreground text-xs font-bold uppercase">
                    在线连通性测试
                  </Label>
                  <div className="flex flex-col gap-3 md:flex-row">
                    <Input
                      className="cyber-input"
                      onChange={(event) => setTestRepoUrl(event.target.value)}
                      placeholder="git@codehub.example.com:team/repo.git"
                      value={testRepoUrl}
                    />
                    <Button
                      className="cyber-btn-outline whitespace-nowrap"
                      disabled={testingKey}
                      onClick={handleTestSSHKey}
                      variant="outline"
                    >
                      {testingKey ? (
                        <>
                          <div className="loading-spinner mr-2 h-4 w-4" />
                          测试中...
                        </>
                      ) : (
                        <>
                          <PlayCircle className="mr-2 h-4 w-4" />
                          测试 SSH
                        </>
                      )}
                    </Button>
                  </div>
                  <p className="text-muted-foreground text-xs leading-relaxed">
                    推荐使用 `git@...` 形式的 SSH
                    仓库地址。测试成功后，后端会自动补充或更新 `known_hosts`。
                  </p>
                  {sshTestResult && (
                    <div
                      className={`rounded-lg border p-4 font-mono text-xs ${
                        sshTestResult.success
                          ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300/90'
                          : 'border-rose-500/30 bg-rose-500/10 text-rose-300/90'
                      }`}
                    >
                      <div className="mb-2 font-semibold">
                        {sshTestResult.message}
                      </div>
                      {sshTestResult.output && (
                        <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap break-all text-[11px] leading-5">
                          {sshTestResult.output}
                        </pre>
                      )}
                    </div>
                  )}
                </div>

                {/* Delete Key and Clear Known Hosts */}
                {canSaveSettings && (
                  <div className="border-border flex justify-end gap-2 border-t pt-4">
                    <Button
                      className="cyber-btn-outline h-10"
                      disabled={clearingKnownHosts}
                      onClick={handleClearKnownHosts}
                      variant="outline"
                    >
                      {clearingKnownHosts ? (
                        <>
                          <div className="loading-spinner mr-2 h-4 w-4" />
                          清理中...
                        </>
                      ) : (
                        <>
                          <ServerCrash className="mr-2 h-4 w-4" />
                          清理 known_hosts
                        </>
                      )}
                    </Button>
                    <Button
                      className="h-10 border border-rose-500/30 bg-rose-500/20 text-rose-400 hover:bg-rose-500/30"
                      onClick={() => setShowDeleteKeyDialog(true)}
                      variant="destructive"
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      删除密钥
                    </Button>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                  <div className="space-y-4 rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-4">
                    <div>
                      <div className="text-foreground text-sm font-semibold">
                        在线生成 SSH 密钥
                      </div>
                      <div className="text-muted-foreground mt-1 text-xs">
                        后端已支持直接生成密钥对，生成后会自动安全保存私钥并返回公钥。
                      </div>
                    </div>

                    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                      <div className="space-y-2">
                        <Label className="text-muted-foreground text-xs font-bold uppercase">
                          密钥类型
                        </Label>
                        <Select
                          onValueChange={(value: 'ed25519' | 'rsa') =>
                            setSshKeyType(value)
                          }
                          value={sshKeyType}
                        >
                          <SelectTrigger className="cyber-input h-10">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="cyber-dialog border-border">
                            <SelectItem className="font-mono" value="ed25519">
                              ed25519
                            </SelectItem>
                            <SelectItem className="font-mono" value="rsa">
                              rsa
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label className="text-muted-foreground text-xs font-bold uppercase">
                          RSA 位数
                        </Label>
                        <Input
                          className="cyber-input"
                          disabled={sshKeyType !== 'rsa'}
                          onChange={(event) =>
                            setSshKeySize(Number(event.target.value) || 4096)
                          }
                          type="number"
                          value={sshKeySize}
                        />
                      </div>
                    </div>

                    {canSaveSettings && (
                      <div className="flex justify-end">
                        <Button
                          className="cyber-btn-primary h-10"
                          disabled={generatingKey}
                          onClick={handleGenerateSSHKey}
                        >
                          {generatingKey ? (
                            <>
                              <div className="loading-spinner mr-2 h-4 w-4" />
                              生成中...
                            </>
                          ) : (
                            <>
                              <Wrench className="mr-2 h-4 w-4" />
                              生成 SSH 密钥
                            </>
                          )}
                        </Button>
                      </div>
                    )}
                  </div>

                  <div className="text-muted-foreground rounded-lg border border-amber-500/20 bg-amber-500/10 p-4 text-xs">
                    如果你已经有现成的 SSH
                    私钥，也可以手动导入。导入时支持同时写入
                    `known_hosts`，便于首次连仓时复用。
                  </div>
                </div>

                <div className="space-y-2">
                  <Label className="text-muted-foreground text-xs font-bold uppercase">
                    SSH 私钥
                  </Label>
                  <Textarea
                    className="cyber-input h-32 resize-y font-mono text-xs"
                    onChange={(e) => setManualPrivateKey(e.target.value)}
                    placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
                    value={manualPrivateKey}
                  />
                </div>

                <div className="space-y-2">
                  <Label className="text-muted-foreground text-xs font-bold uppercase">
                    SSH 公钥
                  </Label>
                  <Textarea
                    className="cyber-input h-24 resize-y font-mono text-xs"
                    onChange={(e) => setManualPublicKey(e.target.value)}
                    placeholder="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA..."
                    value={manualPublicKey}
                  />
                </div>

                <div className="space-y-2">
                  <Label className="text-muted-foreground text-xs font-bold uppercase">
                    known_hosts（可选）
                  </Label>
                  <Textarea
                    className="cyber-input h-24 resize-y font-mono text-xs"
                    onChange={(e) => setManualKnownHosts(e.target.value)}
                    placeholder="codehub.example.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA..."
                    value={manualKnownHosts}
                  />
                </div>

                {canSaveSettings && (
                  <div className="flex justify-end">
                    <Button
                      className="cyber-btn-primary h-10"
                      disabled={generatingKey}
                      onClick={handleImportSSHKey}
                    >
                      {generatingKey ? (
                        <>
                          <div className="loading-spinner mr-2 h-4 w-4" />
                          导入中...
                        </>
                      ) : (
                        <>
                          <Key className="mr-2 h-4 w-4" />
                          导入 SSH 密钥
                        </>
                      )}
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent className="space-y-6" value="knowledge">
          <KnowledgeBaseManager />
        </TabsContent>
      </Tabs>

      {/* Floating Save Button */}
      {hasChanges && canSaveSettings && (
        <div className="cyber-card fixed bottom-6 right-6 z-50 p-4">
          <Button className="cyber-btn-primary h-12" onClick={saveConfig}>
            <Save className="mr-2 h-4 w-4" /> 保存所有更改
          </Button>
        </div>
      )}

      {/* Delete SSH Key Confirmation Dialog */}
      <AlertDialog
        onOpenChange={setShowDeleteKeyDialog}
        open={showDeleteKeyDialog}
      >
        <AlertDialogContent className="cyber-card cyber-dialog border-rose-500/30">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-foreground flex items-center gap-2 text-lg font-bold uppercase">
              <Trash2 className="h-5 w-5 text-rose-400" />
              确认删除 SSH 密钥？
            </AlertDialogTitle>
            <AlertDialogDescription className="text-muted-foreground">
              删除后将无法使用 SSH 方式访问 Git
              仓库，需要重新生成密钥。此操作不可恢复。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              className="cyber-btn-outline"
              disabled={deletingKey}
            >
              取消
            </AlertDialogCancel>
            <AlertDialogAction
              className="border border-rose-500/30 bg-rose-500/20 text-rose-400 hover:bg-rose-500/30"
              disabled={deletingKey}
              onClick={handleDeleteSSHKey}
            >
              {deletingKey ? (
                <>
                  <div className="loading-spinner mr-2 h-4 w-4" />
                  删除中...
                </>
              ) : (
                '确认删除'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
