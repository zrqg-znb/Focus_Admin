import { AlertTriangle, FileCode, GitBranch, ListChecks, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { InventoryReport, InventoryReportItem } from "@/shared/api/agentTasks";

function asText(value: unknown, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "string" || typeof value === "number") return String(value);
  return JSON.stringify(value, null, 2);
}

function asArray<T = unknown>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function CodeRef({ item, index }: { item: InventoryReportItem; index: number }) {
  const location = [item.file_path, item.line_start].filter(Boolean).join(":");

  return (
    <div className="rounded-md border border-border bg-card/80 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-muted-foreground">#{index}</span>
            <span className="truncate text-sm font-semibold text-foreground">
              {item.symbol || item.item_type || "代码位置"}
            </span>
          </div>
          <p className="mt-1 truncate font-mono text-xs text-muted-foreground">
            {location || "未标注位置"}
          </p>
        </div>
        <Badge className="cyber-badge-muted shrink-0 text-[11px]">
          {item.item_type || "reference"}
        </Badge>
      </div>

      {item.evidence ? (
        <pre className="mt-3 max-h-28 overflow-auto rounded border border-border bg-background/80 p-2 font-mono text-xs leading-5 text-muted-foreground">
          {item.evidence}
        </pre>
      ) : null}

      {(item.risk_note || item.suggested_followup) && (
        <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
          <div className="rounded border border-amber-500/20 bg-amber-500/5 p-2">
            <div className="mb-1 font-semibold text-amber-600 dark:text-amber-300">风险备注</div>
            <div className="leading-5 text-muted-foreground">{item.risk_note || "-"}</div>
          </div>
          <div className="rounded border border-cyan-500/20 bg-cyan-500/5 p-2">
            <div className="mb-1 font-semibold text-cyan-600 dark:text-cyan-300">建议跟进</div>
            <div className="leading-5 text-muted-foreground">{item.suggested_followup || "-"}</div>
          </div>
        </div>
      )}
    </div>
  );
}

export function InventoryReportPanel({
  itemsCount,
  report,
}: {
  itemsCount: number;
  report?: InventoryReport;
}) {
  const scenario = report?.scenario || {};
  const scope = report?.scope || {};
  const overview = report?.overview || {};
  const qa = report?.qa || {};
  const items = asArray<InventoryReportItem>(report?.items);
  const chains = asArray(report?.chains);
  const resources = asArray(report?.resources);
  const warnings = asArray(qa.warnings);
  const keywords = asArray<string>(scope.keywords);

  return (
    <div className="h-full flex-1 overflow-y-auto bg-muted/30 p-5 custom-scrollbar">
      <div className="space-y-4">
        <div className="rounded-md border border-border bg-card/80 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <ListChecks className="h-4 w-4 text-cyan-500" />
                <h2 className="text-sm font-bold uppercase tracking-wider text-foreground">
                  {asText(scenario.name || scenario.key, "梳理报告")}
                </h2>
              </div>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {asText(overview.summary, "暂无摘要。")}
              </p>
            </div>
            <Badge className="cyber-badge-info font-mono text-xs">
              {itemsCount} items
            </Badge>
          </div>

          <div className="mt-4 grid gap-3 text-xs sm:grid-cols-3">
            <div className="rounded border border-border bg-background/60 p-2">
              <div className="text-muted-foreground">覆盖情况</div>
              <div className="mt-1 text-foreground">{asText(overview.coverage)}</div>
            </div>
            <div className="rounded border border-border bg-background/60 p-2">
              <div className="text-muted-foreground">限制说明</div>
              <div className="mt-1 text-foreground">{asText(overview.limitations)}</div>
            </div>
            <div className="rounded border border-border bg-background/60 p-2">
              <div className="text-muted-foreground">QA 状态</div>
              <div className="mt-1 text-foreground">{asText(qa.status, "unchecked")}</div>
            </div>
          </div>

          {keywords.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {keywords.slice(0, 18).map((keyword) => (
                <Badge className="cyber-badge-muted text-[11px]" key={keyword}>
                  {keyword}
                </Badge>
              ))}
            </div>
          )}
        </div>

        <section className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <FileCode className="h-4 w-4 text-primary" />
            梳理条目
          </div>
          {items.length > 0 ? (
            <div className="space-y-3">
              {items.map((item, index) => (
                <CodeRef index={index + 1} item={item} key={`${item.file_path || "item"}-${index}`} />
              ))}
            </div>
          ) : (
            <div className="rounded-md border border-dashed border-border p-5 text-center text-sm text-muted-foreground">
              当前没有梳理条目。
            </div>
          )}
        </section>

        {chains.length > 0 && (
          <section className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <GitBranch className="h-4 w-4 text-violet-500" />
              调用链 / 资源访问链
            </div>
            <div className="space-y-2">
              {chains.map((chain, index) => (
                <pre className="rounded-md border border-border bg-card/80 p-3 font-mono text-xs leading-5 text-muted-foreground" key={index}>
                  {asText(chain)}
                </pre>
              ))}
            </div>
          </section>
        )}

        {resources.length > 0 && (
          <section className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              资源清单
            </div>
            <div className="space-y-2">
              {resources.map((resource, index) => (
                <pre className="rounded-md border border-border bg-card/80 p-3 font-mono text-xs leading-5 text-muted-foreground" key={index}>
                  {asText(resource)}
                </pre>
              ))}
            </div>
          </section>
        )}

        <section className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            QA 校验
          </div>
          {warnings.length > 0 ? (
            <div className="space-y-2">
              {warnings.map((warning, index) => (
                <pre className="rounded-md border border-amber-500/20 bg-amber-500/5 p-3 font-mono text-xs leading-5 text-amber-700 dark:text-amber-200" key={index}>
                  {asText(warning)}
                </pre>
              ))}
            </div>
          ) : (
            <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-3 text-sm text-emerald-700 dark:text-emerald-300">
              未发现引用一致性告警。
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default InventoryReportPanel;
