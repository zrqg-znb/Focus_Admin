import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BookOpen,
  Brain,
  FileUp,
  Plus,
  RefreshCw,
  Search,
  ShieldAlert,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  deleteKnowledgeDocument,
  getKnowledgeDocument,
  getKnowledgeStatus,
  listKnowledgeDocuments,
  rebuildKnowledgeIndex,
  saveKnowledgeDocument,
  searchKnowledgeDocuments,
  validateKnowledgeModules,
  type KnowledgeDocument,
  type KnowledgeStatus,
  uploadKnowledgeDocument,
} from "@/shared/api/rag";

const CATEGORY_OPTIONS = [
  { value: "all", label: "全部分类" },
  { value: "vulnerability", label: "漏洞知识" },
  { value: "framework", label: "框架安全" },
  { value: "best_practice", label: "最佳实践" },
  { value: "remediation", label: "修复建议" },
  { value: "code_pattern", label: "代码模式" },
  { value: "compliance", label: "合规要求" },
] as const;

type EditorFormState = {
  id: string;
  title: string;
  category: string;
  severity: string;
  tags: string;
  cweIds: string;
  owaspIds: string;
  content: string;
};

const EMPTY_FORM: EditorFormState = {
  id: "",
  title: "",
  category: "best_practice",
  severity: "",
  tags: "",
  cweIds: "",
  owaspIds: "",
  content: "",
};

function getErrorMessage(error: unknown, fallback: string) {
  if (typeof error === "object" && error !== null) {
    const record = error as {
      response?: {
        data?: {
          detail?: string;
        };
      };
    };
    return record.response?.data?.detail || fallback;
  }
  return fallback;
}

function splitInputList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinInputList(values: string[] | undefined) {
  return Array.isArray(values) ? values.join(", ") : "";
}

function formatCategoryLabel(category: string) {
  return CATEGORY_OPTIONS.find((item) => item.value === category)?.label || category;
}

function isCustomDocument(document: null | KnowledgeDocument) {
  return String(document?.metadata?.source || "").trim().toLowerCase() === "custom";
}

function toEditorForm(document: KnowledgeDocument): EditorFormState {
  return {
    id: document.id,
    title: document.title,
    category: document.category || "best_practice",
    severity: document.severity || "",
    tags: joinInputList(document.tags),
    cweIds: joinInputList(document.cwe_ids),
    owaspIds: joinInputList(document.owasp_ids),
    content: document.content,
  };
}

export function KnowledgeBaseManager() {
  const [status, setStatus] = useState<KnowledgeStatus | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [keyword, setKeyword] = useState("");
  const [tag, setTag] = useState("");
  const [category, setCategory] = useState("all");
  const [semanticSearch, setSemanticSearch] = useState(false);
  const [loading, setLoading] = useState(true);
  const [rebuilding, setRebuilding] = useState(false);
  const [validating, setValidating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [editorMode, setEditorMode] = useState<"create" | "edit">("create");
  const [editorForm, setEditorForm] = useState<EditorFormState>(EMPTY_FORM);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [validationResult, setValidationResult] = useState<null | {
    valid: string[];
    invalid: string[];
  }>(null);
  const [uploadMeta, setUploadMeta] = useState<Omit<EditorFormState, "content">>({
    id: "",
    title: "",
    category: "best_practice",
    severity: "",
    tags: "",
    cweIds: "",
    owaspIds: "",
  });

  const selectedDocument = useMemo(
    () => documents.find((item) => item.id === selectedDocumentId) || null,
    [documents, selectedDocumentId],
  );

  const loadStatus = useCallback(async () => {
    const nextStatus = await getKnowledgeStatus();
    setStatus(nextStatus);
  }, []);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const payload =
        keyword.trim() && semanticSearch
          ? await searchKnowledgeDocuments({
              query: keyword.trim(),
              category: category === "all" ? undefined : category,
              top_k: 20,
            })
          : await listKnowledgeDocuments({
              category: category === "all" ? undefined : category,
              keyword: keyword.trim() || undefined,
              tag: tag.trim() || undefined,
            });

      const nextItems = payload.items || [];
      setDocuments(nextItems);
      setSelectedDocumentId((current) => {
        if (current && nextItems.some((item) => item.id === current)) {
          return current;
        }
        return nextItems[0]?.id || null;
      });
    } catch (error) {
      console.error("Failed to load knowledge documents:", error);
      toast.error(getErrorMessage(error, "加载知识库失败"));
    } finally {
      setLoading(false);
    }
  }, [category, keyword, semanticSearch, tag]);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  const openCreateDialog = () => {
    setEditorMode("create");
    setEditorForm({ ...EMPTY_FORM });
    setEditorOpen(true);
  };

  const openEditDialog = async (documentId: string) => {
    try {
      const detail = await getKnowledgeDocument(documentId);
      setEditorMode("edit");
      setEditorForm(toEditorForm(detail));
      setEditorOpen(true);
    } catch (error) {
      console.error("Failed to load knowledge detail:", error);
      toast.error(getErrorMessage(error, "加载知识详情失败"));
    }
  };

  const handleSave = async () => {
    if (!editorForm.title.trim()) {
      toast.error("请输入知识条目标题");
      return;
    }
    if (!editorForm.content.trim()) {
      toast.error("请输入知识内容");
      return;
    }

    try {
      setSaving(true);
      await saveKnowledgeDocument({
        id: editorForm.id.trim() || undefined,
        title: editorForm.title.trim(),
        content: editorForm.content.trim(),
        category: editorForm.category,
        severity: editorForm.severity.trim() || undefined,
        tags: splitInputList(editorForm.tags),
        cwe_ids: splitInputList(editorForm.cweIds),
        owasp_ids: splitInputList(editorForm.owaspIds),
      });
      toast.success(editorMode === "create" ? "知识条目已创建" : "知识条目已更新");
      setEditorOpen(false);
      await Promise.all([loadStatus(), loadDocuments()]);
    } catch (error) {
      console.error("Failed to save knowledge document:", error);
      toast.error(getErrorMessage(error, "保存知识条目失败"));
    } finally {
      setSaving(false);
    }
  };

  const handleUpload = async () => {
    if (!uploadFile) {
      toast.error("请先选择要上传的知识文件");
      return;
    }
    try {
      setUploading(true);
      await uploadKnowledgeDocument({
        file: uploadFile,
        documentId: uploadMeta.id.trim() || undefined,
        title: uploadMeta.title.trim() || undefined,
        category: uploadMeta.category || undefined,
        severity: uploadMeta.severity.trim() || undefined,
        tags: splitInputList(uploadMeta.tags),
        cweIds: splitInputList(uploadMeta.cweIds),
        owaspIds: splitInputList(uploadMeta.owaspIds),
      });
      toast.success("知识文件已上传");
      setUploadOpen(false);
      setUploadFile(null);
      setUploadMeta({
        id: "",
        title: "",
        category: "best_practice",
        severity: "",
        tags: "",
        cweIds: "",
        owaspIds: "",
      });
      await Promise.all([loadStatus(), loadDocuments()]);
    } catch (error) {
      console.error("Failed to upload knowledge document:", error);
      toast.error(getErrorMessage(error, "上传知识文件失败"));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (document: KnowledgeDocument) => {
    if (!isCustomDocument(document)) {
      toast.error("内置知识条目不支持删除");
      return;
    }
    if (!window.confirm(`确认删除知识条目“${document.title}”吗？`)) {
      return;
    }
    try {
      setDeletingId(document.id);
      await deleteKnowledgeDocument(document.id);
      toast.success("知识条目已删除");
      await Promise.all([loadStatus(), loadDocuments()]);
    } catch (error) {
      console.error("Failed to delete knowledge document:", error);
      toast.error(getErrorMessage(error, "删除知识条目失败"));
    } finally {
      setDeletingId(null);
    }
  };

  const handleRebuild = async () => {
    try {
      setRebuilding(true);
      const nextStatus = await rebuildKnowledgeIndex();
      setStatus(nextStatus);
      toast.success("知识库索引已重建");
      await loadDocuments();
    } catch (error) {
      console.error("Failed to rebuild knowledge index:", error);
      toast.error(getErrorMessage(error, "重建知识库索引失败"));
    } finally {
      setRebuilding(false);
    }
  };

  const handleValidateModules = async () => {
    const moduleIds = documents.map((item) => item.id).filter(Boolean);
    if (moduleIds.length === 0) {
      toast.error("当前没有可校验的知识模块");
      return;
    }
    try {
      setValidating(true);
      const result = await validateKnowledgeModules(moduleIds);
      setValidationResult(result);
      if (result.invalid.length > 0) {
        toast.error(`发现 ${result.invalid.length} 个无效知识模块`);
      } else {
        toast.success(`模块校验通过，共 ${result.valid.length} 项`);
      }
    } catch (error) {
      console.error("Failed to validate knowledge modules:", error);
      toast.error(getErrorMessage(error, "校验知识模块失败"));
    } finally {
      setValidating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="cyber-card p-4">
          <div className="text-xs uppercase text-muted-foreground font-bold mb-2">索引状态</div>
          <div className="flex items-center gap-2 text-sm font-mono">
            <span className={`w-2 h-2 rounded-full ${status?.enabled ? "bg-emerald-400" : "bg-amber-400"}`} />
            <span className={status?.enabled ? "text-emerald-400" : "text-amber-400"}>
              {status?.enabled ? "向量检索已启用" : "当前走关键字兜底"}
            </span>
          </div>
        </div>
        <div className="cyber-card p-4">
          <div className="text-xs uppercase text-muted-foreground font-bold mb-2">知识条目</div>
          <div className="text-2xl font-mono font-bold text-foreground">{status?.stats.total || 0}</div>
        </div>
        <div className="cyber-card p-4">
          <div className="text-xs uppercase text-muted-foreground font-bold mb-2">索引文档数</div>
          <div className="text-2xl font-mono font-bold text-foreground">{status?.document_count || 0}</div>
        </div>
        <div className="cyber-card p-4">
          <div className="text-xs uppercase text-muted-foreground font-bold mb-2">索引分块数</div>
          <div className="text-2xl font-mono font-bold text-foreground">{status?.chunk_count || 0}</div>
        </div>
      </div>

      <div className="cyber-card p-6 space-y-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 flex-1">
            <div className="space-y-2 md:col-span-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">知识搜索</Label>
              <div className="flex items-center gap-2">
                <Input
                  value={keyword}
                  onChange={(event) => setKeyword(event.target.value)}
                  placeholder="按标题、标签、内容搜索，或启用语义检索"
                  className="cyber-input"
                />
                <Button
                  variant={semanticSearch ? "default" : "outline"}
                  className={semanticSearch ? "cyber-btn-primary" : "cyber-btn-outline"}
                  onClick={() => setSemanticSearch((current) => !current)}
                >
                  <Brain className="w-4 h-4 mr-2" />
                  语义检索
                </Button>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">分类</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger className="cyber-input h-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="cyber-dialog border-border">
                  {CATEGORY_OPTIONS.map((item) => (
                    <SelectItem key={item.value} value={item.value} className="font-mono">
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">标签过滤</Label>
              <Input
                value={tag}
                onChange={(event) => setTag(event.target.value)}
                placeholder="例如 csrf"
                className="cyber-input"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void loadDocuments()} variant="outline" className="cyber-btn-outline">
              <Search className="w-4 h-4 mr-2" />
              刷新列表
            </Button>
            <Button onClick={handleRebuild} disabled={rebuilding} variant="outline" className="cyber-btn-outline">
              <RefreshCw className={`w-4 h-4 mr-2 ${rebuilding ? "animate-spin" : ""}`} />
              重建索引
            </Button>
            <Button onClick={handleValidateModules} disabled={validating || documents.length === 0} variant="outline" className="cyber-btn-outline">
              <ShieldAlert className="w-4 h-4 mr-2" />
              {validating ? "校验中..." : "校验模块"}
            </Button>
            <Button onClick={() => setUploadOpen(true)} variant="outline" className="cyber-btn-outline">
              <FileUp className="w-4 h-4 mr-2" />
              上传文件
            </Button>
            <Button onClick={openCreateDialog} className="cyber-btn-primary">
              <Plus className="w-4 h-4 mr-2" />
              新建条目
            </Button>
          </div>
        </div>

        {validationResult && (
          <div className={`rounded-lg border p-4 text-xs font-mono ${
            validationResult.invalid.length > 0
              ? "border-amber-500/30 bg-amber-500/10 text-amber-200"
              : "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
          }`}>
            <div className="font-semibold mb-2">最近一次模块校验结果</div>
            <div>有效模块: {validationResult.valid.length}</div>
            <div>无效模块: {validationResult.invalid.length}</div>
            {validationResult.invalid.length > 0 && (
              <div className="mt-2 break-all">无效列表: {validationResult.invalid.join(", ")}</div>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] gap-6">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-xs uppercase text-muted-foreground font-bold">知识条目列表</div>
              <Badge variant="outline" className="font-mono">
                {documents.length} 项
              </Badge>
            </div>
            <div className="space-y-2 max-h-[32rem] overflow-y-auto pr-1">
              {loading ? (
                <div className="cyber-card p-8 text-center text-muted-foreground font-mono text-sm">加载知识条目中...</div>
              ) : documents.length === 0 ? (
                <div className="cyber-card p-8 text-center text-muted-foreground font-mono text-sm">当前筛选条件下暂无知识条目</div>
              ) : (
                documents.map((document) => {
                  const active = selectedDocumentId === document.id;
                  const custom = isCustomDocument(document);
                  return (
                    <button
                      key={document.id}
                      type="button"
                      onClick={() => setSelectedDocumentId(document.id)}
                      className={`w-full text-left cyber-card p-4 transition-all ${
                        active ? "border-primary shadow-[0_0_0_1px_rgba(255,107,44,0.35)]" : "hover:border-border"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-semibold text-foreground">{document.title}</span>
                            <Badge variant="outline" className="font-mono text-[10px] uppercase">
                              {formatCategoryLabel(document.category)}
                            </Badge>
                            <Badge
                              variant="outline"
                              className={`font-mono text-[10px] uppercase ${
                                custom ? "border-emerald-500/40 text-emerald-400" : "border-border text-muted-foreground"
                              }`}
                            >
                              {custom ? "custom" : "builtin"}
                            </Badge>
                          </div>
                          <div className="mt-2 text-xs text-muted-foreground font-mono break-all">{document.id}</div>
                          <div className="mt-3 line-clamp-3 text-sm text-muted-foreground">{document.content}</div>
                        </div>
                        {document.score != null && (
                          <div className="text-xs font-mono text-primary whitespace-nowrap">{document.score.toFixed(3)}</div>
                        )}
                      </div>
                      {document.tags.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {document.tags.slice(0, 5).map((item) => (
                            <span
                              key={`${document.id}-${item}`}
                              className="rounded border border-border bg-muted px-2 py-1 text-[10px] font-mono text-muted-foreground"
                            >
                              {item}
                            </span>
                          ))}
                        </div>
                      )}
                    </button>
                  );
                })
              )}
            </div>
          </div>

          <div className="cyber-card p-6 space-y-4 min-h-[28rem]">
            {selectedDocument ? (
              <>
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-lg font-bold text-foreground">{selectedDocument.title}</h3>
                      <Badge variant="outline" className="font-mono text-[10px] uppercase">
                        {formatCategoryLabel(selectedDocument.category)}
                      </Badge>
                      {selectedDocument.severity && (
                        <Badge variant="outline" className="font-mono text-[10px] uppercase border-amber-500/40 text-amber-400">
                          {selectedDocument.severity}
                        </Badge>
                      )}
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground font-mono break-all">{selectedDocument.id}</div>
                  </div>

                  <div className="flex gap-2">
                    {isCustomDocument(selectedDocument) && (
                      <>
                        <Button
                          variant="outline"
                          className="cyber-btn-outline"
                          onClick={() => void openEditDialog(selectedDocument.id)}
                        >
                          编辑
                        </Button>
                        <Button
                          variant="outline"
                          className="border-rose-500/30 text-rose-400 hover:bg-rose-500/10"
                          disabled={deletingId === selectedDocument.id}
                          onClick={() => void handleDelete(selectedDocument)}
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          删除
                        </Button>
                      </>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                  <div className="rounded border border-border bg-muted/40 p-3">
                    <div className="text-xs uppercase text-muted-foreground font-bold mb-2">标签</div>
                    <div className="flex flex-wrap gap-2">
                      {selectedDocument.tags.length > 0 ? (
                        selectedDocument.tags.map((item) => (
                          <span key={item} className="rounded border border-border px-2 py-1 text-xs font-mono text-muted-foreground">
                            {item}
                          </span>
                        ))
                      ) : (
                        <span className="text-muted-foreground">无</span>
                      )}
                    </div>
                  </div>
                  <div className="rounded border border-border bg-muted/40 p-3">
                    <div className="text-xs uppercase text-muted-foreground font-bold mb-2">模块元数据</div>
                    <div className="space-y-1 text-xs font-mono text-muted-foreground">
                      <div>来源: {String(selectedDocument.metadata?.source || "builtin")}</div>
                      {selectedDocument.file_path && <div>文件: {selectedDocument.file_path}</div>}
                      {selectedDocument.metadata?.uploaded_file_name && (
                        <div>上传文件: {String(selectedDocument.metadata.uploaded_file_name)}</div>
                      )}
                    </div>
                  </div>
                  <div className="rounded border border-border bg-muted/40 p-3">
                    <div className="text-xs uppercase text-muted-foreground font-bold mb-2">CWE</div>
                    <div className="text-xs font-mono text-muted-foreground break-all">
                      {selectedDocument.cwe_ids.length > 0 ? selectedDocument.cwe_ids.join(", ") : "无"}
                    </div>
                  </div>
                  <div className="rounded border border-border bg-muted/40 p-3">
                    <div className="text-xs uppercase text-muted-foreground font-bold mb-2">OWASP</div>
                    <div className="text-xs font-mono text-muted-foreground break-all">
                      {selectedDocument.owasp_ids.length > 0 ? selectedDocument.owasp_ids.join(", ") : "无"}
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-xs uppercase text-muted-foreground font-bold">知识内容</div>
                  <div className="rounded border border-border bg-muted/30 p-4 max-h-[22rem] overflow-y-auto">
                    <pre className="whitespace-pre-wrap text-sm leading-6 font-mono text-foreground">
                      {selectedDocument.content}
                    </pre>
                  </div>
                </div>
              </>
            ) : (
              <div className="h-full flex flex-col items-center justify-center gap-4 text-center text-muted-foreground">
                <BookOpen className="w-10 h-10 text-primary/60" />
                <div>
                  <div className="font-semibold text-foreground">选择一个知识条目查看详情</div>
                  <div className="text-sm mt-1">支持内置知识、自定义条目和文件上传。</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <Dialog open={editorOpen} onOpenChange={setEditorOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>{editorMode === "create" ? "新建知识条目" : "编辑知识条目"}</DialogTitle>
            <DialogDescription>自定义知识条目保存后会立即进入模块校验和检索索引。</DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 px-6">
            <div className="space-y-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">模块 ID</Label>
              <Input
                value={editorForm.id}
                onChange={(event) => setEditorForm((current) => ({ ...current, id: event.target.value }))}
                placeholder="例如 csrf_review"
                className="cyber-input"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">标题</Label>
              <Input
                value={editorForm.title}
                onChange={(event) => setEditorForm((current) => ({ ...current, title: event.target.value }))}
                placeholder="例如 CSRF 审计清单"
                className="cyber-input"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">分类</Label>
              <Select
                value={editorForm.category}
                onValueChange={(value) => setEditorForm((current) => ({ ...current, category: value }))}
              >
                <SelectTrigger className="cyber-input h-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="cyber-dialog border-border">
                  {CATEGORY_OPTIONS.filter((item) => item.value !== "all").map((item) => (
                    <SelectItem key={item.value} value={item.value} className="font-mono">
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">严重度</Label>
              <Input
                value={editorForm.severity}
                onChange={(event) => setEditorForm((current) => ({ ...current, severity: event.target.value }))}
                placeholder="例如 medium"
                className="cyber-input"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">标签</Label>
              <Input
                value={editorForm.tags}
                onChange={(event) => setEditorForm((current) => ({ ...current, tags: event.target.value }))}
                placeholder="逗号分隔，例如 csrf, django"
                className="cyber-input"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">CWE / OWASP</Label>
              <div className="grid grid-cols-2 gap-3">
                <Input
                  value={editorForm.cweIds}
                  onChange={(event) => setEditorForm((current) => ({ ...current, cweIds: event.target.value }))}
                  placeholder="CWE-352"
                  className="cyber-input"
                />
                <Input
                  value={editorForm.owaspIds}
                  onChange={(event) => setEditorForm((current) => ({ ...current, owaspIds: event.target.value }))}
                  placeholder="A01:2021"
                  className="cyber-input"
                />
              </div>
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">知识内容</Label>
              <Textarea
                value={editorForm.content}
                onChange={(event) => setEditorForm((current) => ({ ...current, content: event.target.value }))}
                placeholder="输入安全知识内容，可直接粘贴 Markdown 或纯文本"
                className="cyber-input min-h-[18rem] font-mono text-sm"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" className="cyber-btn-outline" onClick={() => setEditorOpen(false)}>
              取消
            </Button>
            <Button className="cyber-btn-primary" onClick={() => void handleSave()} disabled={saving}>
              {saving ? "保存中..." : editorMode === "create" ? "创建条目" : "保存修改"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>上传知识文件</DialogTitle>
            <DialogDescription>支持 `.json`、`.md`、`.markdown`、`.txt`，上传后会自动重建知识索引。</DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 px-6">
            <div className="space-y-2 md:col-span-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">知识文件</Label>
              <Input
                type="file"
                accept=".json,.md,.markdown,.txt"
                onChange={(event) => setUploadFile(event.target.files?.[0] || null)}
                className="cyber-input"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">模块 ID</Label>
              <Input
                value={uploadMeta.id}
                onChange={(event) => setUploadMeta((current) => ({ ...current, id: event.target.value }))}
                placeholder="可选，不填则自动生成"
                className="cyber-input"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">标题</Label>
              <Input
                value={uploadMeta.title}
                onChange={(event) => setUploadMeta((current) => ({ ...current, title: event.target.value }))}
                placeholder="可选，优先使用文件内定义"
                className="cyber-input"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">分类</Label>
              <Select
                value={uploadMeta.category}
                onValueChange={(value) => setUploadMeta((current) => ({ ...current, category: value }))}
              >
                <SelectTrigger className="cyber-input h-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="cyber-dialog border-border">
                  {CATEGORY_OPTIONS.filter((item) => item.value !== "all").map((item) => (
                    <SelectItem key={item.value} value={item.value} className="font-mono">
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">严重度</Label>
              <Input
                value={uploadMeta.severity}
                onChange={(event) => setUploadMeta((current) => ({ ...current, severity: event.target.value }))}
                placeholder="例如 high"
                className="cyber-input"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">标签</Label>
              <Input
                value={uploadMeta.tags}
                onChange={(event) => setUploadMeta((current) => ({ ...current, tags: event.target.value }))}
                placeholder="逗号分隔"
                className="cyber-input"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">CWE</Label>
              <Input
                value={uploadMeta.cweIds}
                onChange={(event) => setUploadMeta((current) => ({ ...current, cweIds: event.target.value }))}
                placeholder="CWE-79, CWE-352"
                className="cyber-input"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase text-muted-foreground font-bold">OWASP</Label>
              <Input
                value={uploadMeta.owaspIds}
                onChange={(event) => setUploadMeta((current) => ({ ...current, owaspIds: event.target.value }))}
                placeholder="A03:2021"
                className="cyber-input"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" className="cyber-btn-outline" onClick={() => setUploadOpen(false)}>
              取消
            </Button>
            <Button className="cyber-btn-primary" onClick={() => void handleUpload()} disabled={uploading}>
              {uploading ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  上传中...
                </>
              ) : (
                <>
                  <FileUp className="w-4 h-4 mr-2" />
                  上传并入库
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="bg-muted border border-border p-4 rounded-lg text-xs space-y-2">
        <p className="font-bold uppercase text-muted-foreground flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-sky-400" />
          知识库说明
        </p>
        <p className="text-muted-foreground">• 自定义知识条目会立即进入模块校验和 Agent 知识注入链路。</p>
        <p className="text-muted-foreground">• 语义检索依赖 embedding 配置；未配置时仍可使用普通关键字筛选。</p>
        <p className="text-muted-foreground">• 删除仅支持 `custom` 来源条目，内置漏洞知识和框架知识默认只读。</p>
      </div>
    </div>
  );
}
