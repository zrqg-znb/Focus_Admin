/**
 * System Config Component
 * Cyberpunk Terminal Aesthetic
 */

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import {
  Settings, Save, RotateCcw, Eye, EyeOff, CheckCircle2, AlertCircle,
  Info, Zap, Globe, PlayCircle, Brain, Key, Copy, Trash2, ServerCrash
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/shared/api/database";
import EmbeddingConfig from "@/components/agent/EmbeddingConfig";
import { clearKnownHosts, deleteSSHKey, getSSHKey, saveSSHKey } from "@/shared/api/sshKeys";
import { useAuth } from "@/shared/context/AuthContext";
import { DEEPAUDIT_ACTION_CODES } from "@/shared/focus/focusPermission";

// LLM Providers
const LLM_PROVIDERS = [
  { value: 'openai', label: 'OpenAI GPT', icon: '🟢', category: 'litellm', hint: 'gpt-5, gpt-5-mini, o3 等' },
  { value: 'claude', label: 'Anthropic Claude', icon: '🟣', category: 'litellm', hint: 'claude-sonnet-4.5, claude-opus-4 等' },
  { value: 'gemini', label: 'Google Gemini', icon: '🔵', category: 'litellm', hint: 'gemini-3-pro, gemini-3-flash 等' },
  { value: 'deepseek', label: 'DeepSeek', icon: '🔷', category: 'litellm', hint: 'deepseek-v3.1-terminus, deepseek-v3 等' },
  { value: 'qwen', label: '通义千问', icon: '🟠', category: 'litellm', hint: 'qwen3-max-instruct, qwen3-plus 等' },
  { value: 'zhipu', label: '智谱AI (GLM)', icon: '🔴', category: 'litellm', hint: 'glm-4.6, glm-4.5-flash 等' },
  { value: 'moonshot', label: 'Moonshot (Kimi)', icon: '🌙', category: 'litellm', hint: 'kimi-k2, kimi-k1.5 等' },
  { value: 'ollama', label: 'Ollama 本地', icon: '🖥️', category: 'litellm', hint: 'llama3.3-70b, qwen3-8b 等' },
  { value: 'baidu', label: '百度文心', icon: '📘', category: 'native', hint: 'ernie-4.5 (需要 API_KEY:SECRET_KEY)' },
  { value: 'minimax', label: 'MiniMax', icon: '⚡', category: 'native', hint: 'minimax-m2, minimax-m1 等' },
  { value: 'doubao', label: '字节豆包', icon: '🎯', category: 'native', hint: 'doubao-1.6-pro, doubao-1.5-pro 等' },
];

const DEFAULT_MODELS: Record<string, string> = {
  openai: 'gpt-5', claude: 'claude-sonnet-4.5', gemini: 'gemini-3-pro',
  deepseek: 'deepseek-v3.1-terminus', qwen: 'qwen3-max-instruct', zhipu: 'glm-4.6', moonshot: 'kimi-k2',
  ollama: 'llama3.3-70b', baidu: 'ernie-4.5', minimax: 'minimax-m2', doubao: 'doubao-1.6-pro',
};

const VISIBLE_LLM_PROVIDERS = LLM_PROVIDERS.filter((item) =>
  ["openai", "deepseek", "qwen", "zhipu", "ollama"].includes(item.value)
);

interface SystemConfigData {
  llmProvider: string; llmApiKey: string; llmModel: string; llmBaseUrl: string;
  llmTimeout: number; llmTemperature: number; llmMaxTokens: number;
  // Agent超时配置
  llmFirstTokenTimeout: number; llmStreamTimeout: number;
  agentTimeout: number; subAgentTimeout: number; toolTimeout: number;
  githubToken: string; gitlabToken: string; giteaToken: string;
  maxAnalyzeFiles: number; llmConcurrency: number; llmGapMs: number; outputLanguage: string;
}

type UserConfigPayload = {
  llmConfig?: Partial<SystemConfigData> & {
    provider?: string;
    llmProvider?: string;
  };
  otherConfig?: Partial<Pick<
    SystemConfigData,
    | "githubToken"
    | "gitlabToken"
    | "giteaToken"
    | "maxAnalyzeFiles"
    | "llmConcurrency"
    | "llmGapMs"
    | "outputLanguage"
  >>;
};

const DEFAULT_SYSTEM_CONFIG: SystemConfigData = {
  llmProvider: "openai",
  llmApiKey: "",
  llmModel: "",
  llmBaseUrl: "",
  llmTimeout: 150000,
  llmTemperature: 0.1,
  llmMaxTokens: 4096,
  llmFirstTokenTimeout: 90,
  llmStreamTimeout: 60,
  agentTimeout: 1800,
  subAgentTimeout: 600,
  toolTimeout: 60,
  githubToken: "",
  gitlabToken: "",
  giteaToken: "",
  maxAnalyzeFiles: 0,
  llmConcurrency: 3,
  llmGapMs: 2000,
  outputLanguage: "zh-CN",
};

const INTERNAL_LLM_LABEL = "内网统一入口";

function toSystemConfigData(
  payload?: null | UserConfigPayload,
  fallback: SystemConfigData = DEFAULT_SYSTEM_CONFIG,
): SystemConfigData {
  const llmConfig = payload?.llmConfig ?? {};
  const otherConfig = payload?.otherConfig ?? {};

  return {
    llmProvider: llmConfig.llmProvider || llmConfig.provider || fallback.llmProvider,
    llmApiKey: llmConfig.llmApiKey || fallback.llmApiKey,
    llmModel: llmConfig.llmModel || fallback.llmModel,
    llmBaseUrl: llmConfig.llmBaseUrl || fallback.llmBaseUrl,
    llmTimeout: llmConfig.llmTimeout || fallback.llmTimeout,
    llmTemperature: llmConfig.llmTemperature ?? fallback.llmTemperature,
    llmMaxTokens: llmConfig.llmMaxTokens || fallback.llmMaxTokens,
    llmFirstTokenTimeout: llmConfig.llmFirstTokenTimeout || fallback.llmFirstTokenTimeout,
    llmStreamTimeout: llmConfig.llmStreamTimeout || fallback.llmStreamTimeout,
    agentTimeout: llmConfig.agentTimeout || fallback.agentTimeout,
    subAgentTimeout: llmConfig.subAgentTimeout || fallback.subAgentTimeout,
    toolTimeout: llmConfig.toolTimeout || fallback.toolTimeout,
    githubToken: otherConfig.githubToken || fallback.githubToken,
    gitlabToken: otherConfig.gitlabToken || fallback.gitlabToken,
    giteaToken: otherConfig.giteaToken || fallback.giteaToken,
    maxAnalyzeFiles: otherConfig.maxAnalyzeFiles ?? fallback.maxAnalyzeFiles,
    llmConcurrency: otherConfig.llmConcurrency || fallback.llmConcurrency,
    llmGapMs: otherConfig.llmGapMs || fallback.llmGapMs,
    outputLanguage: otherConfig.outputLanguage || fallback.outputLanguage,
  };
}

export function SystemConfig() {
  const { hasAccess } = useAuth();
  const [config, setConfig] = useState<SystemConfigData | null>(null);
  const [loading, setLoading] = useState(true);
  const [showApiKey, setShowApiKey] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [testingLLM, setTestingLLM] = useState(false);
  const [llmTestResult, setLlmTestResult] = useState<{ success: boolean; message: string; debug?: Record<string, unknown> } | null>(null);
  const [showDebugInfo, setShowDebugInfo] = useState(true);

  // SSH Key states
  const [sshKey, setSSHKey] = useState<{ has_key: boolean; public_key?: string; fingerprint?: string }>({ has_key: false });
  const [generatingKey, setGeneratingKey] = useState(false);
  const [deletingKey, setDeletingKey] = useState(false);
  const [clearingKnownHosts, setClearingKnownHosts] = useState(false);
  const [manualPrivateKey, setManualPrivateKey] = useState("");
  const [manualPublicKey, setManualPublicKey] = useState("");
  const [manualKnownHosts, setManualKnownHosts] = useState("");
  const [showDeleteKeyDialog, setShowDeleteKeyDialog] = useState(false);
  const canSaveSettings = hasAccess(DEEPAUDIT_ACTION_CODES.SETTINGS_SAVE);

  useEffect(() => { loadConfig(); loadSSHKey(); }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      console.log('[SystemConfig] 开始加载配置...');

      const backendConfig = await api.getUserConfig() as UserConfigPayload | null;

      console.log('[SystemConfig] 后端返回的原始数据:', JSON.stringify(backendConfig, null, 2));

      if (backendConfig) {
        const newConfig = toSystemConfigData(backendConfig);

        console.log('[SystemConfig] 解析后的配置:', newConfig);
        setConfig(newConfig);

        console.log('✓ 配置已加载:', {
          provider: newConfig.llmProvider,
          hasApiKey: !!newConfig.llmApiKey,
          model: newConfig.llmModel,
        });
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

  const handleImportSSHKey = async () => {
    if (!canSaveSettings) {
      toast.error("当前账号没有保存设置的权限");
      return;
    }
    if (!manualPrivateKey.trim()) {
      toast.error("请先粘贴 SSH 私钥");
      return;
    }
    if (!manualPublicKey.trim()) {
      toast.error("请先粘贴 SSH 公钥");
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
      toast.success("SSH 密钥已导入");
    } catch (error: any) {
      console.error('Failed to import SSH key:', error);
      toast.error(error.response?.data?.detail || "导入 SSH 密钥失败");
    } finally {
      setGeneratingKey(false);
    }
  };

  const handleDeleteSSHKey = async () => {
    if (!canSaveSettings) {
      toast.error("当前账号没有保存设置的权限");
      return;
    }
    try {
      setDeletingKey(true);
      await deleteSSHKey();
      setSSHKey({ has_key: false });
      setManualPrivateKey("");
      setManualPublicKey("");
      setManualKnownHosts("");
      toast.success("SSH密钥已删除");
      setShowDeleteKeyDialog(false);
    } catch (error: any) {
      console.error('Failed to delete SSH key:', error);
      toast.error(error.response?.data?.detail || "删除SSH密钥失败");
    } finally {
      setDeletingKey(false);
    }
  };

  const handleClearKnownHosts = async () => {
    if (!canSaveSettings) {
      toast.error("当前账号没有保存设置的权限");
      return;
    }
    try {
      setClearingKnownHosts(true);
      const result = await clearKnownHosts();
      if (result.success) {
        toast.success(result.message || "known_hosts已清理");
      } else {
        toast.error("清理known_hosts失败");
      }
    } catch (error: any) {
      console.error('Failed to clear known_hosts:', error);
      toast.error(error.response?.data?.detail || "清理known_hosts失败");
    } finally {
      setClearingKnownHosts(false);
    }
  };

  const handleCopyPublicKey = () => {
    if (sshKey.public_key) {
      navigator.clipboard.writeText(sshKey.public_key);
      toast.success("公钥已复制到剪贴板");
    }
  };

  const saveConfig = async () => {
    if (!config) return;
    if (!canSaveSettings) {
      toast.error("当前账号没有保存设置的权限");
      return;
    }
    try {
      const savedConfig = await api.updateUserConfig({
        llmConfig: {
          llmProvider: config.llmProvider, llmApiKey: config.llmApiKey,
          llmModel: config.llmModel, llmBaseUrl: config.llmBaseUrl,
          llmTimeout: config.llmTimeout, llmTemperature: config.llmTemperature,
          llmMaxTokens: config.llmMaxTokens,
          // Agent超时配置
          llmFirstTokenTimeout: config.llmFirstTokenTimeout,
          llmStreamTimeout: config.llmStreamTimeout,
          agentTimeout: config.agentTimeout,
          subAgentTimeout: config.subAgentTimeout,
          toolTimeout: config.toolTimeout,
        },
        otherConfig: {
          githubToken: config.githubToken, gitlabToken: config.gitlabToken, giteaToken: config.giteaToken,
          maxAnalyzeFiles: config.maxAnalyzeFiles, llmConcurrency: config.llmConcurrency,
          llmGapMs: config.llmGapMs, outputLanguage: config.outputLanguage,
        },
      }) as UserConfigPayload | null;

      if (savedConfig) {
        setConfig(toSystemConfigData(savedConfig, config));
      }

      setHasChanges(false);
      toast.success("配置已保存！");
    } catch (error) {
      toast.error(`保存失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  };

  const resetConfig = async () => {
    if (!canSaveSettings) {
      toast.error("当前账号没有保存设置的权限");
      return;
    }
    if (!window.confirm("确定要重置为默认配置吗？")) return;
    try {
      await api.deleteUserConfig();
      await loadConfig();
      setHasChanges(false);
      toast.success("已重置为默认配置");
    } catch (error) {
      toast.error(`重置失败: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  };

  const updateConfig = (key: keyof SystemConfigData, value: string | number) => {
    if (!config) return;
    setConfig(prev => prev ? { ...prev, [key]: value } : null);
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
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-4">
          <div className="loading-spinner mx-auto" />
          <p className="text-muted-foreground font-mono text-sm uppercase tracking-wider">加载配置中...</p>
        </div>
      </div>
    );
  }

  const isConfigured = config.llmBaseUrl.trim() !== '' || config.llmApiKey.trim() !== '' || config.llmModel.trim() !== '';

  return (
    <div className="space-y-6">
      {/* Status Bar */}
      <div className={`cyber-card p-4 ${isConfigured ? 'border-emerald-500/30' : 'border-amber-500/30'}`}>
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <Info className="h-5 w-5 text-sky-400" />
            <span className="font-mono text-sm">
              {isConfigured ? (
                <span className="text-emerald-400 flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" /> 内网统一入口已配置
                </span>
              ) : (
                <span className="text-amber-400 flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" /> 请配置内网中转地址和模型
                </span>
              )}
            </span>
          </div>
          <div className="flex gap-2">
            {hasChanges && canSaveSettings && (
              <Button onClick={saveConfig} size="sm" className="cyber-btn-primary h-8">
                <Save className="w-3 h-3 mr-2" /> 保存
              </Button>
            )}
            {canSaveSettings && (
              <Button onClick={resetConfig} variant="outline" size="sm" className="cyber-btn-ghost h-8">
                <RotateCcw className="w-3 h-3 mr-2" /> 重置
              </Button>
            )}
          </div>
        </div>
      </div>

      <Tabs defaultValue="llm" className="w-full">
        <TabsList className="grid w-full grid-cols-4 bg-muted border border-border p-1 h-auto gap-1 rounded-lg mb-6">
          <TabsTrigger value="llm" className="data-[state=active]:bg-primary data-[state=active]:text-foreground font-mono font-bold uppercase py-2.5 text-muted-foreground transition-all rounded text-xs flex items-center gap-2">
            <Zap className="w-3 h-3" /> LLM 配置
          </TabsTrigger>
          <TabsTrigger value="embedding" className="data-[state=active]:bg-primary data-[state=active]:text-foreground font-mono font-bold uppercase py-2.5 text-muted-foreground transition-all rounded text-xs flex items-center gap-2">
            <Brain className="w-3 h-3" /> 嵌入模型
          </TabsTrigger>
          <TabsTrigger value="analysis" className="data-[state=active]:bg-primary data-[state=active]:text-foreground font-mono font-bold uppercase py-2.5 text-muted-foreground transition-all rounded text-xs flex items-center gap-2">
            <Settings className="w-3 h-3" /> 分析参数
          </TabsTrigger>
          <TabsTrigger value="git" className="data-[state=active]:bg-primary data-[state=active]:text-foreground font-mono font-bold uppercase py-2.5 text-muted-foreground transition-all rounded text-xs flex items-center gap-2">
            <Globe className="w-3 h-3" /> Git 集成
          </TabsTrigger>
        </TabsList>

        {/* LLM Config */}
        <TabsContent value="llm" className="space-y-6">
          <div className="cyber-card p-6 space-y-6">
            <div className="bg-muted/50 border border-border rounded-lg p-4 flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-bold text-muted-foreground uppercase">LLM 入口</p>
                <p className="text-sm text-foreground font-mono">{config.llmProvider || INTERNAL_LLM_LABEL}</p>
              </div>
              <div className="text-xs text-muted-foreground text-right">
                可按需选择 `openai / qwen / deepseek / zhipu`，后端仍会在失败时自动切换到本地兜底
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label className="text-xs font-bold text-muted-foreground uppercase">Provider</Label>
                <Select value={config.llmProvider} onValueChange={(v) => updateConfig('llmProvider', v)}>
                  <SelectTrigger className="h-10 cyber-input">
                    <SelectValue placeholder="选择 Provider" />
                  </SelectTrigger>
                  <SelectContent className="cyber-dialog border-border">
                    {VISIBLE_LLM_PROVIDERS.map((item) => (
                      <SelectItem key={item.value} value={item.value} className="font-mono">
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-bold text-muted-foreground uppercase">内网中转地址</Label>
                <Input
                  value={config.llmBaseUrl}
                  onChange={(e) => updateConfig('llmBaseUrl', e.target.value)}
                  placeholder="例如 https://llm-gateway.intra.example/v1"
                  className="h-10 cyber-input"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-bold text-muted-foreground uppercase">API Key</Label>
                <div className="flex gap-2">
                  <Input
                    type={showApiKey ? 'text' : 'password'}
                    value={config.llmApiKey}
                    onChange={(e) => updateConfig('llmApiKey', e.target.value)}
                    placeholder="中转服务提供的 Key"
                    className="h-10 cyber-input"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="h-10 w-10 cyber-btn-ghost"
                  >
                    {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                </div>
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-bold text-muted-foreground uppercase">模型名称</Label>
                <Input
                  value={config.llmModel}
                  onChange={(e) => updateConfig('llmModel', e.target.value)}
                  placeholder="例如 gpt-5, qwen3-max-instruct, deepseek-v3.1-terminus"
                  className="h-10 cyber-input"
                />
              </div>
            </div>

            {/* Test Connection */}
            <div className="pt-4 border-t border-border border-dashed flex items-center justify-between flex-wrap gap-4">
              <div className="text-sm">
                <span className="font-bold text-foreground">测试连接</span>
                <span className="text-muted-foreground ml-2">验证内网中转和本地兜底路径</span>
              </div>
              <Button
                onClick={testLLMConnection}
                disabled={testingLLM || !isConfigured}
                className="cyber-btn-primary h-10"
              >
                {testingLLM ? (
                  <>
                    <div className="loading-spinner w-4 h-4 mr-2" />
                    测试中...
                  </>
                ) : (
                  <>
                    <PlayCircle className="w-4 h-4 mr-2" />
                    测试
                  </>
                )}
              </Button>
            </div>
            {llmTestResult && (
              <div className={`p-3 rounded-lg ${llmTestResult.success ? 'bg-emerald-500/10 border border-emerald-500/30' : 'bg-rose-500/10 border border-rose-500/30'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm">
                    {llmTestResult.success ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-rose-400" />
                    )}
                    <span className={llmTestResult.success ? 'text-emerald-300/80' : 'text-rose-300/80'}>
                      {llmTestResult.message}
                    </span>
                  </div>
                  {llmTestResult.debug && (
                    <button
                      onClick={() => setShowDebugInfo(!showDebugInfo)}
                      className="text-xs text-muted-foreground hover:text-foreground underline"
                    >
                      {showDebugInfo ? '隐藏调试信息' : '显示调试信息'}
                    </button>
                  )}
                </div>
                {showDebugInfo && llmTestResult.debug && (
                  <div className="mt-3 pt-3 border-t border-border/50">
                    <div className="text-xs font-mono space-y-1 text-muted-foreground">
                      <div className="font-bold text-foreground mb-2">连接信息:</div>
                      <div>Provider: <span className="text-foreground">{String(llmTestResult.debug.provider_used || llmTestResult.debug.provider_requested || 'openai')}</span></div>
                      <div>Model: <span className="text-foreground">{String(llmTestResult.debug.model_used || llmTestResult.debug.model_requested || 'N/A')}</span></div>
                      <div>Base URL: <span className="text-foreground">{String(llmTestResult.debug.base_url_used || llmTestResult.debug.base_url_requested || '(default)')}</span></div>
                      <div>Adapter: <span className="text-foreground">{String(llmTestResult.debug.adapter_type || 'N/A')}</span></div>
                      <div>API Key: <span className="text-foreground">{String(llmTestResult.debug.api_key_prefix)} (长度: {String(llmTestResult.debug.api_key_length)})</span></div>
                      <div>耗时: <span className="text-foreground">{String(llmTestResult.debug.elapsed_time_ms || 'N/A')} ms</span></div>

                      {/* 用户保存的配置参数 */}
                      {llmTestResult.debug.saved_config && (
                        <div className="mt-3 pt-2 border-t border-border/30">
                          <div className="font-bold text-cyan-400 mb-2">已保存的配置参数:</div>
                          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                            <div>温度: <span className="text-foreground">{String((llmTestResult.debug.saved_config as Record<string, unknown>).temperature ?? 'N/A')}</span></div>
                            <div>最大Tokens: <span className="text-foreground">{String((llmTestResult.debug.saved_config as Record<string, unknown>).max_tokens ?? 'N/A')}</span></div>
                            <div>超时: <span className="text-foreground">{String((llmTestResult.debug.saved_config as Record<string, unknown>).timeout_ms ?? 'N/A')} ms</span></div>
                            <div>请求间隔: <span className="text-foreground">{String((llmTestResult.debug.saved_config as Record<string, unknown>).gap_ms ?? 'N/A')} ms</span></div>
                            <div>并发数: <span className="text-foreground">{String((llmTestResult.debug.saved_config as Record<string, unknown>).concurrency ?? 'N/A')}</span></div>
                            <div>最大文件数: <span className="text-foreground">{String((llmTestResult.debug.saved_config as Record<string, unknown>).max_analyze_files ?? 'N/A')}</span></div>
                            <div>输出语言: <span className="text-foreground">{String((llmTestResult.debug.saved_config as Record<string, unknown>).output_language ?? 'N/A')}</span></div>
                          </div>
                        </div>
                      )}

                      {/* 测试时实际使用的参数 */}
                      {llmTestResult.debug.test_params && (
                        <div className="mt-2 pt-2 border-t border-border/30">
                          <div className="font-bold text-emerald-400 mb-2">测试时使用的参数:</div>
                          <div className="grid grid-cols-3 gap-x-4">
                            <div>温度: <span className="text-foreground">{String((llmTestResult.debug.test_params as Record<string, unknown>).temperature ?? 'N/A')}</span></div>
                            <div>超时: <span className="text-foreground">{String((llmTestResult.debug.test_params as Record<string, unknown>).timeout ?? 'N/A')}s</span></div>
                            <div>MaxTokens: <span className="text-foreground">{String((llmTestResult.debug.test_params as Record<string, unknown>).max_tokens ?? 'N/A')}</span></div>
                          </div>
                        </div>
                      )}

                      {llmTestResult.debug.error_category && (
                        <div className="mt-2">错误类型: <span className="text-rose-400">{String(llmTestResult.debug.error_category)}</span></div>
                      )}
                      {llmTestResult.debug.error_type && (
                        <div>异常类型: <span className="text-rose-400">{String(llmTestResult.debug.error_type)}</span></div>
                      )}
                      {llmTestResult.debug.status_code && (
                        <div>HTTP 状态码: <span className="text-rose-400">{String(llmTestResult.debug.status_code)}</span></div>
                      )}
                      {llmTestResult.debug.api_response && (
                        <div className="mt-2">
                          <div className="font-bold text-amber-400">API 服务器返回:</div>
                          <pre className="mt-1 p-2 bg-amber-500/10 border border-amber-500/30 rounded text-xs overflow-x-auto">
                            {String(llmTestResult.debug.api_response)}
                          </pre>
                        </div>
                      )}
                      {llmTestResult.debug.error_message && (
                        <div className="mt-2">
                          <div className="font-bold text-foreground">完整错误信息:</div>
                          <pre className="mt-1 p-2 bg-background/50 rounded text-xs overflow-x-auto max-h-32 overflow-y-auto">
                            {String(llmTestResult.debug.error_message)}
                          </pre>
                        </div>
                      )}
                      {llmTestResult.debug.traceback && (
                        <details className="mt-2">
                          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">完整堆栈跟踪</summary>
                          <pre className="mt-1 p-2 bg-background/50 rounded text-xs overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap">
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
            <details open className="pt-4 border-t border-border border-dashed">
              <summary className="font-bold uppercase cursor-pointer hover:text-primary text-muted-foreground text-sm">高级参数</summary>

              {/* LLM基础参数 */}
              <div className="mt-4 mb-2">
                <span className="text-xs text-muted-foreground uppercase font-semibold">LLM 基础参数</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground uppercase">请求超时 (毫秒)</Label>
                  <Input
                    type="number"
                    value={config.llmTimeout}
                    onChange={(e) => updateConfig('llmTimeout', Number(e.target.value))}
                    className="h-10 cyber-input"
                  />
                  <p className="text-xs text-muted-foreground">单次LLM请求的超时时间</p>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground uppercase">温度 (0-2)</Label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={config.llmTemperature}
                    onChange={(e) => updateConfig('llmTemperature', Number(e.target.value))}
                    className="h-10 cyber-input"
                  />
                  <p className="text-xs text-muted-foreground">控制输出随机性，越低越确定</p>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground uppercase">最大 Tokens</Label>
                  <Input
                    type="number"
                    value={config.llmMaxTokens}
                    onChange={(e) => updateConfig('llmMaxTokens', Number(e.target.value))}
                    className="h-10 cyber-input"
                  />
                  <p className="text-xs text-muted-foreground">单次请求最大输出Token数</p>
                </div>
              </div>

              {/* Agent超时配置 */}
              <div className="mt-6 mb-2">
                <span className="text-xs text-muted-foreground uppercase font-semibold">Agent 超时配置</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground uppercase">首Token超时 (秒)</Label>
                  <Input
                    type="number"
                    value={config.llmFirstTokenTimeout}
                    onChange={(e) => updateConfig('llmFirstTokenTimeout', Number(e.target.value))}
                    className="h-10 cyber-input"
                  />
                  <p className="text-xs text-muted-foreground">等待LLM首个Token的超时时间</p>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground uppercase">流式超时 (秒)</Label>
                  <Input
                    type="number"
                    value={config.llmStreamTimeout}
                    onChange={(e) => updateConfig('llmStreamTimeout', Number(e.target.value))}
                    className="h-10 cyber-input"
                  />
                  <p className="text-xs text-muted-foreground">流式输出中两个Token间的超时</p>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground uppercase">工具超时 (秒)</Label>
                  <Input
                    type="number"
                    value={config.toolTimeout}
                    onChange={(e) => updateConfig('toolTimeout', Number(e.target.value))}
                    className="h-10 cyber-input"
                  />
                  <p className="text-xs text-muted-foreground">单个工具执行的默认超时时间</p>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground uppercase">子Agent超时 (秒)</Label>
                  <Input
                    type="number"
                    value={config.subAgentTimeout}
                    onChange={(e) => updateConfig('subAgentTimeout', Number(e.target.value))}
                    className="h-10 cyber-input"
                  />
                  <p className="text-xs text-muted-foreground">子Agent (Recon/Analysis/Verification) 超时</p>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground uppercase">总超时 (秒)</Label>
                  <Input
                    type="number"
                    value={config.agentTimeout}
                    onChange={(e) => updateConfig('agentTimeout', Number(e.target.value))}
                    className="h-10 cyber-input"
                  />
                  <p className="text-xs text-muted-foreground">整个Agent审计任务的最大时间</p>
                </div>
              </div>
            </details>
          </div>

          {/* Usage Notes */}
          <div className="bg-muted border border-border p-4 rounded-lg text-xs space-y-2">
            <p className="font-bold uppercase text-muted-foreground flex items-center gap-2">
              <Info className="w-4 h-4 text-sky-400" />
              配置说明
            </p>
            <p className="text-muted-foreground">• <strong className="text-muted-foreground">统一入口</strong>: 前端只保留内网中转配置，后端会自动对接本地兜底模型</p>
            <p className="text-muted-foreground">• <strong className="text-muted-foreground">API 中转站</strong>: 在 Base URL 填入中转站地址即可，API Key 填中转站提供的 Key</p>
            <p className="text-muted-foreground">• <strong className="text-muted-foreground">兼容历史配置</strong>: 旧 provider 会被加载并归一为统一入口，不会再作为可选项展示</p>
          </div>
        </TabsContent>

        {/* Embedding Config */}
        <TabsContent value="embedding" className="space-y-6">
          <EmbeddingConfig />
        </TabsContent>

        {/* Analysis Parameters */}
        <TabsContent value="analysis" className="space-y-6">
          <div className="cyber-card p-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label className="text-xs font-bold text-muted-foreground uppercase">最大分析文件数</Label>
                <Input
                  type="number"
                  value={config.maxAnalyzeFiles}
                  onChange={(e) => updateConfig('maxAnalyzeFiles', Number(e.target.value))}
                  className="h-10 cyber-input"
                />
                <p className="text-xs text-muted-foreground">单次任务最多处理的文件数量</p>
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-bold text-muted-foreground uppercase">LLM 并发数</Label>
                <Input
                  type="number"
                  value={config.llmConcurrency}
                  onChange={(e) => updateConfig('llmConcurrency', Number(e.target.value))}
                  className="h-10 cyber-input"
                />
                <p className="text-xs text-muted-foreground">同时发送的 LLM 请求数量</p>
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-bold text-muted-foreground uppercase">请求间隔 (毫秒)</Label>
                <Input
                  type="number"
                  value={config.llmGapMs}
                  onChange={(e) => updateConfig('llmGapMs', Number(e.target.value))}
                  className="h-10 cyber-input"
                />
                <p className="text-xs text-muted-foreground">每个请求之间的延迟时间</p>
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-bold text-muted-foreground uppercase">输出语言</Label>
                <Select value={config.outputLanguage} onValueChange={(v) => updateConfig('outputLanguage', v)}>
                  <SelectTrigger className="h-10 cyber-input">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="cyber-dialog border-border">
                    <SelectItem value="zh-CN" className="font-mono">🇨🇳 中文</SelectItem>
                    <SelectItem value="en-US" className="font-mono">🇺🇸 English</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">代码审查结果的输出语言</p>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* Git Integration */}
        <TabsContent value="git" className="space-y-6">
          <div className="cyber-card p-6 space-y-6">
            <div className="space-y-2">
              <Label className="text-xs font-bold text-muted-foreground uppercase">GitHub Token (可选)</Label>
              <Input
                type="password"
                value={config.githubToken}
                onChange={(e) => updateConfig('githubToken', e.target.value)}
                placeholder="ghp_xxxxxxxxxxxx"
                className="h-10 cyber-input"
              />
              <p className="text-xs text-muted-foreground">
                用于访问私有仓库。获取:{' '}
                <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                  github.com/settings/tokens
                </a>
              </p>
            </div>
            <div className="space-y-2">
              <Label className="text-xs font-bold text-muted-foreground uppercase">GitLab Token (可选)</Label>
              <Input
                type="password"
                value={config.gitlabToken}
                onChange={(e) => updateConfig('gitlabToken', e.target.value)}
                placeholder="glpat-xxxxxxxxxxxx"
                className="h-10 cyber-input"
              />
              <p className="text-xs text-muted-foreground">
                用于访问私有仓库。获取:{' '}
                <a href="https://gitlab.com/-/profile/personal_access_tokens" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                  gitlab.com/-/profile/personal_access_tokens
                </a>
              </p>
            </div>
            <div className="space-y-2">
              <Label className="text-xs font-bold text-muted-foreground uppercase">Gitea Token (可选)</Label>
              <Input
                type="password"
                value={config.giteaToken}
                onChange={(e) => updateConfig('giteaToken', e.target.value)}
                placeholder="sha1_xxxxxxxxxxxx"
                className="h-10 cyber-input"
              />
              <p className="text-xs text-muted-foreground">
                用于访问 Gitea 私有仓库。获取:{' '}
                <span className="text-primary">
                  [your-gitea-instance]/user/settings/applications
                </span>
              </p>
            </div>
            <div className="bg-muted border border-border p-4 rounded-lg text-xs">
              <p className="font-bold text-muted-foreground flex items-center gap-2 mb-2">
                <Info className="w-4 h-4 text-sky-400" />
                提示
              </p>
              <p className="text-muted-foreground">• 公开仓库无需配置 Token</p>
              <p className="text-muted-foreground">• 私有仓库需要配置对应平台的 Token</p>
            </div>
          </div>

          {/* SSH Key Management */}
          <div className="cyber-card p-6 space-y-4">
            <div className="flex items-center gap-3 mb-2">
              <Key className="w-5 h-5 text-emerald-400" />
              <h3 className="text-lg font-bold uppercase tracking-wider text-foreground">SSH 密钥管理</h3>
            </div>

            <div className="flex items-start gap-3 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
              <div className="flex-shrink-0 mt-0.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                  <Key className="w-4 h-4 text-emerald-400" />
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-foreground font-medium mb-1">
                  使用 SSH 密钥访问 Git 仓库
                </p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  生成 SSH 密钥对后，将公钥添加到 GitHub/GitLab，即可使用 SSH URL 访问私有仓库。私钥将被加密存储。
                </p>
              </div>
            </div>

            {!sshKey.has_key ? (
              <div className="space-y-4">
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-4 text-xs text-muted-foreground">
                  当前 Focus 后端已支持保存 SSH 凭据，但未开放在线自动生成。
                  请粘贴已有的 SSH 私钥、公钥与可选的 `known_hosts` 内容完成导入。
                </div>

                <div className="space-y-2">
                  <Label className="text-xs font-bold text-muted-foreground uppercase">SSH 私钥</Label>
                  <Textarea
                    value={manualPrivateKey}
                    onChange={(e) => setManualPrivateKey(e.target.value)}
                    placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
                    className="cyber-input font-mono text-xs h-32 resize-y"
                  />
                </div>

                <div className="space-y-2">
                  <Label className="text-xs font-bold text-muted-foreground uppercase">SSH 公钥</Label>
                  <Textarea
                    value={manualPublicKey}
                    onChange={(e) => setManualPublicKey(e.target.value)}
                    placeholder="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA..."
                    className="cyber-input font-mono text-xs h-24 resize-y"
                  />
                </div>

                <div className="space-y-2">
                  <Label className="text-xs font-bold text-muted-foreground uppercase">known_hosts（可选）</Label>
                  <Textarea
                    value={manualKnownHosts}
                    onChange={(e) => setManualKnownHosts(e.target.value)}
                    placeholder="github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA..."
                    className="cyber-input font-mono text-xs h-24 resize-y"
                  />
                </div>

                {canSaveSettings && (
                  <div className="flex justify-end">
                    <Button
                      onClick={handleImportSSHKey}
                      disabled={generatingKey}
                      className="cyber-btn-primary h-10"
                    >
                      {generatingKey ? (
                        <>
                          <div className="loading-spinner w-4 h-4 mr-2" />
                          导入中...
                        </>
                      ) : (
                        <>
                          <Key className="w-4 h-4 mr-2" />
                          导入 SSH 密钥
                        </>
                      )}
                    </Button>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                {/* Public Key Display */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label className="text-xs font-bold text-muted-foreground uppercase flex items-center gap-2">
                      <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                      SSH 公钥
                    </Label>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={handleCopyPublicKey}
                      className="h-8 text-xs"
                    >
                      <Copy className="w-3 h-3 mr-1" />
                      复制
                    </Button>
                  </div>
                  <Textarea
                    value={sshKey.public_key || ""}
                    readOnly
                    className="cyber-input font-mono text-xs h-24 resize-none"
                  />

                  {/* 显示指纹 */}
                  {sshKey.fingerprint && (
                    <div className="p-3 bg-muted/50 rounded border border-border">
                      <Label className="text-xs font-bold text-muted-foreground uppercase mb-1 block">
                        公钥指纹 (SHA256)
                      </Label>
                      <code className="text-xs text-emerald-400 font-mono break-all">
                        {sshKey.fingerprint}
                      </code>
                    </div>
                  )}

                  <p className="text-xs text-muted-foreground">
                    请将此公钥添加到 <a href="https://github.com/settings/keys" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">GitHub</a> 或 <a href="https://gitlab.com/-/profile/keys" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">GitLab</a> 账户
                  </p>
                </div>

                <div className="space-y-2 pt-4 border-t border-border">
                  <Label className="text-xs font-bold text-muted-foreground uppercase">
                    使用说明
                  </Label>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    在线 SSH 探测接口当前未开放。导入密钥后，可直接在项目创建或代码拉取流程中使用 SSH 仓库地址进行验证。
                  </p>
                </div>

                {/* Delete Key and Clear Known Hosts */}
                {canSaveSettings && (
                  <div className="flex justify-end gap-2 pt-4 border-t border-border">
                    <Button
                      variant="outline"
                      onClick={handleClearKnownHosts}
                      disabled={clearingKnownHosts}
                      className="cyber-btn-outline h-10"
                    >
                      {clearingKnownHosts ? (
                        <>
                          <div className="loading-spinner w-4 h-4 mr-2" />
                          清理中...
                        </>
                      ) : (
                        <>
                          <ServerCrash className="w-4 h-4 mr-2" />
                          清理 known_hosts
                        </>
                      )}
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={() => setShowDeleteKeyDialog(true)}
                      className="bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 border border-rose-500/30 h-10"
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      删除密钥
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* Floating Save Button */}
      {hasChanges && canSaveSettings && (
        <div className="fixed bottom-6 right-6 cyber-card p-4 z-50">
          <Button onClick={saveConfig} className="cyber-btn-primary h-12">
            <Save className="w-4 h-4 mr-2" /> 保存所有更改
          </Button>
        </div>
      )}

      {/* Delete SSH Key Confirmation Dialog */}
      <AlertDialog open={showDeleteKeyDialog} onOpenChange={setShowDeleteKeyDialog}>
        <AlertDialogContent className="cyber-card border-rose-500/30 cyber-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-lg font-bold uppercase text-foreground flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-rose-400" />
              确认删除 SSH 密钥？
            </AlertDialogTitle>
            <AlertDialogDescription className="text-muted-foreground">
              删除后将无法使用 SSH 方式访问 Git 仓库，需要重新生成密钥。此操作不可恢复。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="cyber-btn-outline" disabled={deletingKey}>
              取消
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteSSHKey}
              disabled={deletingKey}
              className="bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 border border-rose-500/30"
            >
              {deletingKey ? (
                <>
                  <div className="loading-spinner w-4 h-4 mr-2" />
                  删除中...
                </>
              ) : (
                "确认删除"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
