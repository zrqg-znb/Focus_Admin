/**
 * 嵌入模型配置组件
 * Cyberpunk Terminal Aesthetic
 * 独立于 LLM 配置，专门用于 Agent 审计的 RAG 系统
 */

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Brain,
  Check,
  Loader2,
  RefreshCw,
  Server,
  Info,
  CheckCircle2,
  AlertCircle,
  PlayCircle,
} from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/shared/api/serverClient";
import { useAuth } from "@/shared/context/AuthContext";
import { DEEPAUDIT_ACTION_CODES } from "@/shared/focus/focusPermission";

interface EmbeddingConfig {
  provider: string;
  model: string;
  api_key: string | null;
  base_url: string | null;
  dimensions: number;
  batch_size: number;
}

interface TestResult {
  success: boolean;
  message: string;
  dimensions?: number;
  sample_embedding?: number[];
  latency_ms?: number;
}

export default function EmbeddingConfigPanel() {
  const { hasAccess } = useAuth();
  const [currentConfig, setCurrentConfig] = useState<EmbeddingConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);

  // 表单状态
  const [selectedModel, setSelectedModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [customDimension, setCustomDimension] = useState<number | null>(null);
  const [batchSize, setBatchSize] = useState(100);
  const canSaveSettings = hasAccess(DEEPAUDIT_ACTION_CODES.SETTINGS_SAVE);

  // 加载数据
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const configRes = await apiClient.get("/embedding/config");
      setCurrentConfig(configRes.data);

      // 设置表单默认值
      if (configRes.data) {
        setSelectedModel(configRes.data.model);
        setApiKey(configRes.data.api_key || "");
        setBaseUrl(configRes.data.base_url || "");
        setCustomDimension(configRes.data.dimensions || null);
        setBatchSize(configRes.data.batch_size);
      }
    } catch (error) {
      toast.error("加载配置失败");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!canSaveSettings) {
      toast.error("当前账号没有保存设置的权限");
      return;
    }
    if (!selectedModel) {
      toast.error("请填写模型名称");
      return;
    }

    try {
      setSaving(true);
      await apiClient.put("/embedding/config", {
        provider: "openai",
        model: selectedModel,
        api_key: apiKey || undefined,
        base_url: baseUrl || undefined,
        dimensions: customDimension || undefined,
        batch_size: batchSize,
      });

      toast.success("配置已保存");
      await loadData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    if (!selectedModel) {
      toast.error("请填写模型名称");
      return;
    }

    try {
      setTesting(true);
      setTestResult(null);

      const response = await apiClient.post("/embedding/test", {
        provider: "openai",
        model: selectedModel,
        api_key: apiKey || undefined,
        base_url: baseUrl || undefined,
        dimension: customDimension || undefined,
      });

      setTestResult(response.data);

      if (response.data.success) {
        toast.success("测试成功");
      } else {
        toast.error("测试失败");
      }
    } catch (error: any) {
      setTestResult({
        success: false,
        message: error.response?.data?.detail || "测试失败",
      });
      toast.error("测试失败");
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="text-center space-y-4">
          <div className="loading-spinner mx-auto" />
          <p className="text-muted-foreground font-mono text-sm uppercase tracking-wider">加载配置中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 当前配置状态 */}
      {currentConfig && (
        <div className="cyber-card p-4 border-primary/30">
          <div className="flex items-center gap-2 mb-3">
            <Server className="w-4 h-4 text-primary" />
            <span className="font-mono font-bold text-sm uppercase text-foreground">当前配置</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-muted p-3 rounded-lg border border-border">
              <p className="text-xs text-muted-foreground uppercase mb-1">模型</p>
              <p className="font-mono text-sm text-foreground truncate">{currentConfig.model}</p>
            </div>
            <div className="bg-muted p-3 rounded-lg border border-border">
              <p className="text-xs text-muted-foreground uppercase mb-1">中转地址</p>
              <p className="font-mono text-sm text-foreground truncate">{currentConfig.base_url || "(default)"}</p>
            </div>
            <div className="bg-muted p-3 rounded-lg border border-border">
              <p className="text-xs text-muted-foreground uppercase mb-1">向量维度</p>
              <p className="font-mono text-sm text-foreground">{currentConfig.dimensions}</p>
            </div>
            <div className="bg-muted p-3 rounded-lg border border-border">
              <p className="text-xs text-muted-foreground uppercase mb-1">批处理大小</p>
              <p className="font-mono text-sm text-foreground">{currentConfig.batch_size}</p>
            </div>
          </div>
        </div>
      )}

      {/* 配置表单 */}
      <div className="cyber-card p-6 space-y-6">
        {/* 模型 */}
        <div className="space-y-2">
          <Label className="text-xs font-bold text-muted-foreground uppercase">模型</Label>
          <Input
            type="text"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            placeholder="输入模型名称"
            className="h-10 cyber-input"
          />
        </div>

        {/* API Key */}
        <div className="space-y-2">
          <div className="space-y-2">
            <Label className="text-xs font-bold text-muted-foreground uppercase">
              API Key
            </Label>
            <Input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="输入内网中转 Key"
              className="h-10 cyber-input"
            />
            <p className="text-xs text-muted-foreground">
              API Key 将安全存储，不会显示在页面上
            </p>
          </div>
        </div>

        {/* 自定义端点 */}
        <div className="space-y-2">
          <Label className="text-xs font-bold text-muted-foreground uppercase">
            自定义 API 端点 <span className="text-muted-foreground">(内网地址)</span>
          </Label>
          <Input
            type="url"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="例如 https://llm-gateway.intra.example/v1"
            className="h-10 cyber-input"
          />
          <p className="text-xs text-muted-foreground">
            用于公司内网中转或自托管代理
          </p>
        </div>

        {/* 自定义向量维度 */}
        <div className="space-y-2">
          <Label className="text-xs font-bold text-muted-foreground uppercase">
            自定义向量维度 <span className="text-muted-foreground">(可选)</span>
          </Label>
          <Input
            type="number"
            value={customDimension || ""}
            onChange={(e) => setCustomDimension(e.target.value ? parseInt(e.target.value) : null)}
            placeholder="留空使用默认值"
            min={64}
            max={8192}
            className="h-10 cyber-input w-40"
          />
          <p className="text-xs text-muted-foreground">
            适用于内网中转或本地 embedding 服务，若服务端已固定维度可留空
          </p>
        </div>

        {/* 批处理大小 */}
        <div className="space-y-2">
          <Label className="text-xs font-bold text-muted-foreground uppercase">批处理大小</Label>
          <Input
            type="number"
            value={batchSize}
            onChange={(e) => setBatchSize(parseInt(e.target.value) || 100)}
            min={1}
            max={500}
            className="h-10 cyber-input w-32"
          />
          <p className="text-xs text-muted-foreground">
            每批嵌入的文本数量，建议 50-100
          </p>
        </div>

        {/* 测试结果 */}
        {testResult && (
          <div
            className={`p-4 rounded-lg ${
              testResult.success
                ? "bg-emerald-500/10 border border-emerald-500/30"
                : "bg-rose-500/10 border border-rose-500/30"
            }`}
          >
            <div className="flex items-center gap-2 mb-2">
              {testResult.success ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              ) : (
                <AlertCircle className="w-5 h-5 text-rose-400" />
              )}
              <span
                className={`font-bold ${
                  testResult.success ? "text-emerald-400" : "text-rose-400"
                }`}
              >
                {testResult.success ? "测试成功" : "测试失败"}
              </span>
            </div>
            <p className="text-sm text-muted-foreground">{testResult.message}</p>
            {testResult.success && (
              <div className="mt-3 pt-3 border-t border-border text-xs text-muted-foreground space-y-1 font-mono">
                <div>向量维度: <span className="text-foreground">{testResult.dimensions}</span></div>
                <div>延迟: <span className="text-foreground">{testResult.latency_ms}ms</span></div>
                {testResult.sample_embedding && (
                  <div className="truncate">
                    示例向量: <span className="text-muted-foreground">[{testResult.sample_embedding.slice(0, 5).map((v) => v.toFixed(4)).join(", ")}...]</span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex items-center gap-3 pt-4 border-t border-border border-dashed">
          <Button
            onClick={handleTest}
            disabled={testing || !selectedModel}
            variant="outline"
            className="cyber-btn-outline h-10"
          >
            {testing ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <PlayCircle className="w-4 h-4 mr-2" />
            )}
            测试连接
          </Button>

          {canSaveSettings && (
            <Button
              onClick={handleSave}
              disabled={saving || !selectedModel}
              className="cyber-btn-primary h-10"
            >
              {saving ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Check className="w-4 h-4 mr-2" />
              )}
              保存配置
            </Button>
          )}

          <Button
            onClick={loadData}
            variant="ghost"
            className="cyber-btn-ghost ml-auto h-10"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* 说明 */}
      <div className="bg-muted border border-border p-4 rounded-lg text-xs space-y-3">
        <p className="font-bold uppercase text-muted-foreground flex items-center gap-2">
          <Info className="w-4 h-4 text-sky-400" />
          配置说明
        </p>
        <ul className="text-muted-foreground space-y-1 ml-6">
          <li>• 嵌入模型用于 Agent 审计的代码语义搜索 (RAG)</li>
          <li>• 页面只保留内网中转地址、API Key 和模型，不再暴露 provider 选择</li>
          <li>• 若服务端已固定向量维度，可将该项留空</li>
          <li>• 向量维度会影响存储空间和检索精度</li>
        </ul>
      </div>
    </div>
  );
}
