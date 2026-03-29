import { useCallback, useEffect, useState } from "react";
import { History, PlayCircle, RefreshCw } from "lucide-react";
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
import {
  getAgentCheckpoints,
  getCheckpointDetail,
  resumeAgentTaskFromCheckpoint,
  type AgentCheckpoint,
  type CheckpointDetail,
} from "@/shared/api/agentTasks";

type CheckpointDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  taskId: string;
  canResume: boolean;
  onResumed: (taskId: string) => void;
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

function statusTone(status: string) {
  switch (status) {
    case "completed":
      return "border-emerald-500/40 text-emerald-400";
    case "failed":
      return "border-rose-500/40 text-rose-400";
    case "running":
      return "border-amber-500/40 text-amber-400";
    default:
      return "border-border text-muted-foreground";
  }
}

export function CheckpointDialog({
  open,
  onOpenChange,
  taskId,
  canResume,
  onResumed,
}: CheckpointDialogProps) {
  const [loading, setLoading] = useState(false);
  const [resuming, setResuming] = useState(false);
  const [checkpoints, setCheckpoints] = useState<AgentCheckpoint[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<CheckpointDetail | null>(null);

  const loadCheckpoints = useCallback(async () => {
    setLoading(true);
    try {
      const items = await getAgentCheckpoints(taskId, { limit: 50 });
      setCheckpoints(items);
      setSelectedId((current) => {
        if (current && items.some((item) => item.id === current)) {
          return current;
        }
        return items[0]?.id || null;
      });
    } catch (error) {
      console.error("Failed to load checkpoints:", error);
      toast.error(getErrorMessage(error, "加载检查点失败"));
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    if (!open) {
      return;
    }
    void loadCheckpoints();
  }, [loadCheckpoints, open]);

  useEffect(() => {
    if (!open || !selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const payload = await getCheckpointDetail(taskId, selectedId);
        if (!cancelled) {
          setDetail(payload);
        }
      } catch (error) {
        if (!cancelled) {
          console.error("Failed to load checkpoint detail:", error);
          toast.error(getErrorMessage(error, "加载检查点详情失败"));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, selectedId, taskId]);

  const handleResume = async () => {
    if (!selectedId) {
      toast.error("请先选择检查点");
      return;
    }
    try {
      setResuming(true);
      const resumedTask = await resumeAgentTaskFromCheckpoint(taskId, selectedId);
      toast.success("已从检查点恢复为新的 Agent 任务");
      onOpenChange(false);
      onResumed(resumedTask.id);
    } catch (error) {
      console.error("Failed to resume task from checkpoint:", error);
      toast.error(getErrorMessage(error, "从检查点恢复失败"));
    } finally {
      setResuming(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl">
        <DialogHeader>
          <DialogTitle>任务检查点</DialogTitle>
          <DialogDescription>
            查看 Agent 任务的运行快照，并在需要时从某个检查点恢复为新的任务执行链路。
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 xl:grid-cols-[22rem_minmax(0,1fr)] gap-6 px-6">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-xs uppercase text-muted-foreground font-bold">检查点列表</div>
              <Button variant="outline" className="cyber-btn-outline h-9" onClick={() => void loadCheckpoints()} disabled={loading}>
                <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />
                刷新
              </Button>
            </div>

            <div className="space-y-2 max-h-[30rem] overflow-y-auto pr-1">
              {loading ? (
                <div className="cyber-card p-6 text-center text-muted-foreground font-mono text-sm">加载检查点中...</div>
              ) : checkpoints.length === 0 ? (
                <div className="cyber-card p-6 text-center text-muted-foreground font-mono text-sm">当前任务还没有检查点</div>
              ) : (
                checkpoints.map((checkpoint) => (
                  <button
                    key={checkpoint.id}
                    type="button"
                    onClick={() => setSelectedId(checkpoint.id)}
                    className={`w-full text-left cyber-card p-4 transition-all ${
                      selectedId === checkpoint.id ? "border-primary shadow-[0_0_0_1px_rgba(255,107,44,0.35)]" : "hover:border-border"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="font-semibold text-foreground">{checkpoint.checkpoint_name || checkpoint.phase}</div>
                        <div className="mt-1 text-xs text-muted-foreground font-mono">
                          {checkpoint.agent_name} / {checkpoint.agent_type}
                        </div>
                        <div className="mt-2 text-xs text-muted-foreground">
                          Phase: <span className="font-mono">{checkpoint.phase}</span>
                          {" · "}
                          Iteration: <span className="font-mono">{checkpoint.iteration}</span>
                        </div>
                      </div>
                      <Badge variant="outline" className={`font-mono text-[10px] uppercase ${statusTone(checkpoint.status)}`}>
                        {checkpoint.status}
                      </Badge>
                    </div>
                    <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground font-mono">
                      <span>{checkpoint.timestamp || checkpoint.created_at || "--"}</span>
                      <span>{checkpoint.checkpoint_type}</span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          <div className="cyber-card p-6 min-h-[30rem]">
            {detail ? (
              <div className="space-y-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-lg font-bold text-foreground">{detail.checkpoint_name || detail.phase}</h3>
                      <Badge variant="outline" className={`font-mono text-[10px] uppercase ${statusTone(detail.status)}`}>
                        {detail.status}
                      </Badge>
                      <Badge variant="outline" className="font-mono text-[10px] uppercase">
                        {detail.checkpoint_type}
                      </Badge>
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground font-mono break-all">{detail.id}</div>
                  </div>
                  {canResume && (
                    <Button className="cyber-btn-primary" onClick={() => void handleResume()} disabled={resuming}>
                      {resuming ? (
                        <>
                          <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                          恢复中...
                        </>
                      ) : (
                        <>
                          <PlayCircle className="w-4 h-4 mr-2" />
                          从此检查点恢复
                        </>
                      )}
                    </Button>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="rounded border border-border bg-muted/40 p-3">
                    <div className="text-xs uppercase text-muted-foreground font-bold mb-2">运行位置</div>
                    <div className="space-y-1 text-xs font-mono text-foreground">
                      <div>阶段: {detail.phase}</div>
                      <div>序号: {detail.sequence}</div>
                      <div>迭代: {detail.iteration}</div>
                    </div>
                  </div>
                  <div className="rounded border border-border bg-muted/40 p-3">
                    <div className="text-xs uppercase text-muted-foreground font-bold mb-2">Agent 上下文</div>
                    <div className="space-y-1 text-xs font-mono text-foreground">
                      <div>名称: {detail.agent_name}</div>
                      <div>类型: {detail.agent_type}</div>
                      <div>Agent ID: {detail.agent_id}</div>
                    </div>
                  </div>
                  <div className="rounded border border-border bg-muted/40 p-3">
                    <div className="text-xs uppercase text-muted-foreground font-bold mb-2">运行统计</div>
                    <div className="space-y-1 text-xs font-mono text-foreground">
                      <div>Tokens: {detail.total_tokens}</div>
                      <div>Tool Calls: {detail.tool_calls}</div>
                      <div>Findings: {detail.findings_count}</div>
                    </div>
                  </div>
                </div>

                {Object.keys(detail.metadata || {}).length > 0 && (
                  <div className="space-y-2">
                    <div className="text-xs uppercase text-muted-foreground font-bold">检查点元数据</div>
                    <pre className="rounded border border-border bg-muted/30 p-4 text-xs font-mono text-foreground whitespace-pre-wrap break-all max-h-48 overflow-y-auto">
                      {JSON.stringify(detail.metadata, null, 2)}
                    </pre>
                  </div>
                )}

                {Object.keys(detail.state_data || {}).length > 0 && (
                  <div className="space-y-2">
                    <div className="text-xs uppercase text-muted-foreground font-bold">状态快照</div>
                    <pre className="rounded border border-border bg-muted/30 p-4 text-xs font-mono text-foreground whitespace-pre-wrap break-all max-h-72 overflow-y-auto">
                      {JSON.stringify(detail.state_data, null, 2)}
                    </pre>
                  </div>
                )}

                {Array.isArray(detail.events) && detail.events.length > 0 && (
                  <div className="space-y-2">
                    <div className="text-xs uppercase text-muted-foreground font-bold">关联事件</div>
                    <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                      {detail.events.map((event, index) => (
                        <div key={`${detail.id}-event-${index}`} className="rounded border border-border bg-muted/30 p-3 text-xs">
                          <div className="font-mono text-foreground">{String(event.message || event.event_type || "event")}</div>
                          <div className="mt-1 text-muted-foreground font-mono">
                            {String(event.timestamp || event.created_at || "")}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center gap-4 text-center text-muted-foreground">
                <History className="w-10 h-10 text-primary/60" />
                <div>
                  <div className="font-semibold text-foreground">选择一个检查点查看详情</div>
                  <div className="text-sm mt-1">如果检查点包含运行时快照，可以直接恢复为新的任务。</div>
                </div>
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" className="cyber-btn-outline" onClick={() => onOpenChange(false)}>
            关闭
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
