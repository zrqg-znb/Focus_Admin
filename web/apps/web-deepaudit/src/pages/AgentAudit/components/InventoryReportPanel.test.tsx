import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import InventoryReportPanel from "./InventoryReportPanel";

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

describe("InventoryReportPanel", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it("renders overview, inventory items, chains, and qa warnings", () => {
    act(() => {
      root.render(
        <InventoryReportPanel
          itemsCount={1}
          report={{
            scenario: { key: "api_chain", name: "高危 API 调用链梳理" },
            scope: { keywords: ["strcpy", "malloc"] },
            overview: {
              summary: "梳理了高危 API 调用点。",
              coverage: "src/main.c",
              limitations: "未展开测试目录",
            },
            items: [
              {
                file_path: "src/main.c",
                line_start: 12,
                symbol: "copy_name",
                item_type: "api_call",
                evidence: "strcpy(dst, src);",
                risk_note: "长度边界待确认",
                suggested_followup: "人工确认 src 来源",
              },
            ],
            chains: [{ from: "handler", to: "copy_name" }],
            resources: [{ name: "dst", type: "buffer" }],
            qa: {
              status: "warnings",
              checked_items: 1,
              warnings: [{ type: "evidence_mismatch" }],
            },
          }}
        />,
      );
    });

    expect(container.textContent).toContain("高危 API 调用链梳理");
    expect(container.textContent).toContain("梳理了高危 API 调用点。");
    expect(container.textContent).toContain("copy_name");
    expect(container.textContent).toContain("strcpy(dst, src);");
    expect(container.textContent).toContain("handler");
    expect(container.textContent).toContain("evidence_mismatch");
  });
});
