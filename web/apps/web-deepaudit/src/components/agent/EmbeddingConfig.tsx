/**
 * Embedding configuration panel for DeepAudit system settings.
 */

import { useEffect, useMemo, useState } from 'react';

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
import { apiClient } from '@/shared/api/serverClient';
import { useAuth } from '@/shared/context/AuthContext';
import { DEEPAUDIT_ACTION_CODES } from '@/shared/focus/focusPermission';
import {
  AlertCircle,
  Check,
  CheckCircle2,
  Globe,
  Info,
  Loader2,
  Lock,
  PlayCircle,
  RefreshCw,
  Server,
} from 'lucide-react';
import { toast } from 'sonner';

interface EmbeddingProviderMeta {
  default_model?: string | null;
  description: string;
  id: string;
  models: string[];
  name: string;
  requires_api_key: boolean;
}

interface EmbeddingProviderModels {
  default_model?: string | null;
  models: string[];
  provider: string;
  requires_api_key: boolean;
}

interface EmbeddingConfigResponse {
  api_key: string | null;
  api_key_configured?: boolean;
  base_url: string | null;
  batch_size: number | null;
  config_locked?: boolean;
  config_source?: string;
  dimensions: number | null;
  model: string;
  provider: string;
}

interface TestResult {
  dimensions?: number;
  latency_ms?: number;
  message: string;
  sample_embedding?: number[];
  success: boolean;
}

function containsOnlyAscii(value: string) {
  return /^[\x00-\x7F]*$/.test(value);
}

function getApiKeyValidationMessage() {
  return 'API Key 只能包含 ASCII 字符，请勿输入中文或其它非 ASCII 占位内容';
}

export default function EmbeddingConfigPanel() {
  const { hasAccess } = useAuth();
  const [currentConfig, setCurrentConfig] = useState<EmbeddingConfigResponse | null>(null);
  const [providers, setProviders] = useState<EmbeddingProviderMeta[]>([]);
  const [providerModels, setProviderModels] = useState<EmbeddingProviderModels | null>(null);
  const [loading, setLoading] = useState(true);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);

  const [selectedProvider, setSelectedProvider] = useState('openai');
  const [selectedModel, setSelectedModel] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [customDimension, setCustomDimension] = useState<number | null>(null);
  const [batchSize, setBatchSize] = useState(100);

  const canSaveSettings = hasAccess(DEEPAUDIT_ACTION_CODES.SETTINGS_SAVE);
  const configLocked = Boolean(currentConfig?.config_locked);
  const selectedProviderMeta = useMemo(
    () =>
      providers.find((item) => item.id === selectedProvider) || null,
    [providers, selectedProvider],
  );
  const requiresApiKey = Boolean(
    providerModels?.requires_api_key ?? selectedProviderMeta?.requires_api_key,
  );
  const modelOptions = useMemo(() => {
    const models = [...(providerModels?.models || selectedProviderMeta?.models || [])];
    if (selectedModel && !models.includes(selectedModel)) {
      models.unshift(selectedModel);
    }
    return models;
  }, [providerModels, selectedProviderMeta, selectedModel]);

  useEffect(() => {
    void loadData();
  }, []);

  useEffect(() => {
    if (!selectedProvider) {
      return;
    }
    void loadProviderModels(selectedProvider);
  }, [selectedProvider]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [configRes, providersRes] = await Promise.all([
        apiClient.get('/embedding/config'),
        apiClient.get('/embedding/providers'),
      ]);
      const nextConfig = configRes.data as EmbeddingConfigResponse;
      const nextProviders = Array.isArray(providersRes.data)
        ? (providersRes.data as EmbeddingProviderMeta[])
        : [];

      setCurrentConfig(nextConfig);
      setProviders(nextProviders);
      setSelectedProvider(nextConfig.provider || nextProviders[0]?.id || 'openai');
      setSelectedModel(nextConfig.model || '');
      setApiKey(nextConfig.api_key || '');
      setBaseUrl(nextConfig.base_url || '');
      setCustomDimension(nextConfig.dimensions || null);
      setBatchSize(nextConfig.batch_size || 100);
      setTestResult(null);
    } catch {
      toast.error('加载 embedding 配置失败');
    } finally {
      setLoading(false);
    }
  };

  const loadProviderModels = async (provider: string) => {
    try {
      setModelsLoading(true);
      const response = await apiClient.get(`/embedding/models/${provider}`);
      const payload = response.data as EmbeddingProviderModels;
      setProviderModels(payload);
      if (!selectedModel && payload.default_model) {
        setSelectedModel(payload.default_model);
      }
    } catch (error) {
      setProviderModels(null);
      const message =
        error instanceof Error ? error.message : '加载模型列表失败';
      toast.error(message);
    } finally {
      setModelsLoading(false);
    }
  };

  const handleProviderChange = (provider: string) => {
    const meta = providers.find((item) => item.id === provider);
    setSelectedProvider(provider);
    setSelectedModel(meta?.default_model || '');
    if (provider === 'ollama') {
      setApiKey('');
    }
    setTestResult(null);
  };

  const validateBeforeSubmit = () => {
    if (!selectedProvider) {
      toast.error('请选择 Embedding Provider');
      return false;
    }
    if (!selectedModel) {
      toast.error('请选择模型');
      return false;
    }
    if (selectedProvider !== 'ollama' && apiKey && !containsOnlyAscii(apiKey)) {
      toast.error(getApiKeyValidationMessage());
      return false;
    }
    const hasReusableConfiguredKey =
      Boolean(currentConfig?.api_key_configured) &&
      currentConfig?.provider === selectedProvider;
    if (requiresApiKey && !apiKey.trim() && !hasReusableConfiguredKey) {
      toast.error('当前 embedding provider 需要 API Key');
      return false;
    }
    return true;
  };

  const handleSave = async () => {
    if (!canSaveSettings) {
      toast.error('当前账号没有保存设置的权限');
      return;
    }
    if (configLocked) {
      toast.error('当前 embedding 配置由生产环境统一管理，页面不允许保存覆盖');
      return;
    }
    if (!validateBeforeSubmit()) {
      return;
    }

    try {
      setSaving(true);
      await apiClient.put('/embedding/config', {
        provider: selectedProvider,
        model: selectedModel,
        api_key: selectedProvider === 'ollama' ? undefined : apiKey || undefined,
        base_url: baseUrl || undefined,
        dimensions: customDimension || undefined,
        batch_size: batchSize,
      });
      toast.success('Embedding 配置已保存');
      await loadData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    if (!validateBeforeSubmit()) {
      return;
    }

    try {
      setTesting(true);
      setTestResult(null);
      const response = await apiClient.post('/embedding/test', {
        provider: selectedProvider,
        model: selectedModel,
        api_key: selectedProvider === 'ollama' ? undefined : apiKey || undefined,
        base_url: baseUrl || undefined,
        dimensions: customDimension || undefined,
      });
      setTestResult(response.data);
      if (response.data?.success) {
        toast.success('测试成功');
      } else {
        toast.error(response.data?.message || '测试失败');
      }
    } catch (error: any) {
      const message = error.response?.data?.detail || '测试失败';
      setTestResult({
        success: false,
        message,
      });
      toast.error(message);
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[300px] items-center justify-center">
        <div className="space-y-4 text-center">
          <div className="loading-spinner mx-auto" />
          <p className="text-muted-foreground font-mono text-sm uppercase tracking-wider">
            加载配置中...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {configLocked && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4">
          <div className="mb-2 flex items-center gap-2 text-amber-300">
            <Lock className="h-4 w-4" />
            <span className="font-bold">当前 embedding 配置由生产环境统一管理</span>
          </div>
          <p className="text-sm text-muted-foreground">
            你仍然可以修改当前表单并点击“测试连接”验证局域网 Ollama 是否可达，但保存按钮会被禁用，不会覆盖生产运行配置。
          </p>
        </div>
      )}

      {currentConfig && (
        <div className="cyber-card border-primary/30 p-4">
          <div className="mb-3 flex items-center gap-2">
            <Server className="text-primary h-4 w-4" />
            <span className="font-mono font-bold text-sm uppercase text-foreground">
              当前生效配置
            </span>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
            <div className="rounded-lg border border-border bg-muted p-3">
              <p className="text-muted-foreground mb-1 text-xs uppercase">Provider</p>
              <p className="font-mono text-sm text-foreground">{currentConfig.provider}</p>
            </div>
            <div className="rounded-lg border border-border bg-muted p-3">
              <p className="text-muted-foreground mb-1 text-xs uppercase">模型</p>
              <p className="font-mono text-sm text-foreground truncate">{currentConfig.model}</p>
            </div>
            <div className="rounded-lg border border-border bg-muted p-3">
              <p className="text-muted-foreground mb-1 text-xs uppercase">Base URL</p>
              <p className="font-mono text-sm text-foreground truncate">
                {currentConfig.base_url || '(default)'}
              </p>
            </div>
            <div className="rounded-lg border border-border bg-muted p-3">
              <p className="text-muted-foreground mb-1 text-xs uppercase">向量维度</p>
              <p className="font-mono text-sm text-foreground">{currentConfig.dimensions || '-'}</p>
            </div>
            <div className="rounded-lg border border-border bg-muted p-3">
              <p className="text-muted-foreground mb-1 text-xs uppercase">API Key</p>
              <p className="font-mono text-sm text-foreground">
                {currentConfig.api_key_configured ? '已配置' : '未配置'}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="cyber-card space-y-6 p-6">
        <div className="space-y-2">
          <Label className="text-muted-foreground text-xs font-bold uppercase">
            Embedding Provider
          </Label>
          <Select onValueChange={handleProviderChange} value={selectedProvider}>
            <SelectTrigger className="cyber-input h-10">
              <SelectValue placeholder="选择 Embedding Provider" />
            </SelectTrigger>
            <SelectContent className="cyber-dialog border-border">
              {providers.map((provider) => (
                <SelectItem key={provider.id} className="font-mono" value={provider.id}>
                  {provider.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-muted-foreground text-xs">
            {selectedProviderMeta?.description || '选择要用于语义检索的 embedding provider'}
          </p>
        </div>

        <div className="space-y-2">
          <Label className="text-muted-foreground text-xs font-bold uppercase">
            模型
          </Label>
          {modelOptions.length > 0 ? (
            <Select onValueChange={setSelectedModel} value={selectedModel}>
              <SelectTrigger className="cyber-input h-10">
                <SelectValue
                  placeholder={modelsLoading ? '加载模型列表中...' : '选择模型'}
                />
              </SelectTrigger>
              <SelectContent className="cyber-dialog border-border">
                {modelOptions.map((model) => (
                  <SelectItem key={model} className="font-mono" value={model}>
                    {model}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <Input
              className="cyber-input h-10"
              onChange={(event) => setSelectedModel(event.target.value)}
              placeholder="输入模型名称"
              type="text"
              value={selectedModel}
            />
          )}
          <p className="text-muted-foreground text-xs">
            {selectedProvider === 'ollama'
              ? '推荐直接选择 bge-m3；若 Ollama 已拉取自定义模型，也可以输入自定义模型名。'
              : '优先使用系统提供的模型列表。'}
          </p>
        </div>

        {selectedProvider !== 'ollama' && (
          <div className="space-y-2">
            <Label className="text-muted-foreground text-xs font-bold uppercase">
              API Key
            </Label>
            <Input
              className="cyber-input h-10"
              onChange={(event) => setApiKey(event.target.value)}
              placeholder="输入 API Key"
              type="password"
              value={apiKey}
            />
            <p className="text-muted-foreground text-xs">
              {currentConfig?.api_key_configured && !apiKey
                ? '当前已存在可用 API Key；留空测试时会沿用已保存或系统配置。'
                : 'API Key 只能包含 ASCII 字符，请勿输入中文占位内容。'}
            </p>
          </div>
        )}

        {selectedProvider === 'ollama' && (
          <div className="rounded-lg border border-sky-500/20 bg-sky-500/10 p-3 text-sm text-muted-foreground">
            <div className="mb-1 flex items-center gap-2 text-sky-300">
              <Info className="h-4 w-4" />
              <span className="font-bold">Ollama 默认无需 API Key</span>
            </div>
            <p>
              关键在于当前 DeepAudit 后端机器必须能访问 Ollama 所在主机的 `11434` 端口。`127.0.0.1` 只代表服务器自己，不代表你的电脑。
            </p>
          </div>
        )}

        <div className="space-y-2">
          <Label className="text-muted-foreground text-xs font-bold uppercase">
            Base URL
          </Label>
          <Input
            className="cyber-input h-10"
            onChange={(event) => setBaseUrl(event.target.value)}
            placeholder={
              selectedProvider === 'ollama'
                ? '例如 http://10.0.0.8:11434'
                : '例如 https://llm-gateway.intra.example/v1'
            }
            type="url"
            value={baseUrl}
          />
          <p className="text-muted-foreground text-xs">
            {selectedProvider === 'ollama'
              ? '填写到主机和端口即可，不要手动追加 /v1 或 /api；后端会自动归一化。'
              : '如使用内网 OpenAI 兼容网关，请填写完整兼容入口地址。'}
          </p>
        </div>

        <div className="space-y-2">
          <Label className="text-muted-foreground text-xs font-bold uppercase">
            自定义向量维度 <span className="text-muted-foreground">(可选)</span>
          </Label>
          <Input
            className="cyber-input h-10 w-40"
            max={8192}
            min={64}
            onChange={(event) =>
              setCustomDimension(event.target.value ? parseInt(event.target.value, 10) : null)
            }
            placeholder="留空使用默认值"
            type="number"
            value={customDimension || ''}
          />
          <p className="text-muted-foreground text-xs">
            `bge-m3` 默认推荐使用 `1024` 维；若你的封装服务实际输出不同维度，再在这里覆盖。
          </p>
        </div>

        <div className="space-y-2">
          <Label className="text-muted-foreground text-xs font-bold uppercase">
            批处理大小
          </Label>
          <Input
            className="cyber-input h-10 w-32"
            max={500}
            min={1}
            onChange={(event) => setBatchSize(parseInt(event.target.value, 10) || 100)}
            type="number"
            value={batchSize}
          />
          <p className="text-muted-foreground text-xs">
            每批嵌入的文本数量，建议 50-100。
          </p>
        </div>

        {testResult && (
          <div
            className={`rounded-lg p-4 ${
              testResult.success
                ? 'border border-emerald-500/30 bg-emerald-500/10'
                : 'border border-rose-500/30 bg-rose-500/10'
            }`}
          >
            <div className="mb-2 flex items-center gap-2">
              {testResult.success ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
              ) : (
                <AlertCircle className="h-5 w-5 text-rose-400" />
              )}
              <span
                className={`font-bold ${
                  testResult.success ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {testResult.success ? '测试成功' : '测试失败'}
              </span>
            </div>
            <p className="text-muted-foreground text-sm">{testResult.message}</p>
            {testResult.success && (
              <div className="mt-3 space-y-1 border-t border-border pt-3 font-mono text-xs text-muted-foreground">
                <div>
                  向量维度: <span className="text-foreground">{testResult.dimensions}</span>
                </div>
                <div>
                  延迟: <span className="text-foreground">{testResult.latency_ms}ms</span>
                </div>
                {testResult.sample_embedding && (
                  <div className="truncate">
                    示例向量:{' '}
                    <span className="text-muted-foreground">
                      [{testResult.sample_embedding
                        .slice(0, 5)
                        .map((value) => value.toFixed(4))
                        .join(', ')}
                      ...]
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <div className="flex items-center gap-3 border-t border-dashed border-border pt-4">
          <Button
            className="cyber-btn-outline h-10"
            disabled={testing || !selectedModel}
            onClick={handleTest}
            variant="outline"
          >
            {testing ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <PlayCircle className="mr-2 h-4 w-4" />
            )}
            测试连接
          </Button>

          {canSaveSettings && (
            <Button
              className="cyber-btn-primary h-10"
              disabled={saving || !selectedModel || configLocked}
              onClick={handleSave}
            >
              {saving ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Check className="mr-2 h-4 w-4" />
              )}
              保存配置
            </Button>
          )}

          <Button
            className="cyber-btn-ghost ml-auto h-10"
            onClick={() => void loadData()}
            variant="ghost"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-muted p-4 text-xs space-y-3">
        <p className="text-muted-foreground flex items-center gap-2 font-bold uppercase">
          <Info className="h-4 w-4 text-sky-400" />
          配置说明
        </p>
        <ul className="text-muted-foreground space-y-1 ml-6">
          <li>• Embedding 模型用于 Agent 审计和知识库的语义检索。</li>
          <li>• Ollama 场景默认无需 API Key，重点是生产后端到目标主机的网络连通性。</li>
          <li>• 如果填写的是 Ollama 地址，请只填到主机和端口，例如 `http://10.0.0.8:11434`。</li>
          <li>• 若页面提示“统一管理”，说明运行配置来自生产环境变量，页面编辑仅用于临时测试。</li>
        </ul>
        {selectedProvider === 'ollama' && (
          <div className="rounded-md border border-sky-500/20 bg-sky-500/10 p-3">
            <div className="mb-1 flex items-center gap-2 text-sky-300">
              <Globe className="h-4 w-4" />
              <span className="font-bold">生产环境 Ollama 检查清单</span>
            </div>
            <ul className="space-y-1">
              <li>1. Ollama 所在机器需监听局域网地址，而不是只监听 `127.0.0.1`。</li>
              <li>2. 生产后端机器必须能访问目标主机的 `11434` 端口。</li>
              <li>3. `bge-m3` 需已在 Ollama 所在机器完成拉取并可正常 `api/embed`。</li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
