import {
  act,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
} from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Project } from "@/shared/types";
import { api } from "@/shared/config/database";
import { createAgentTask } from "@/shared/api/agentTasks";
import { getZipFileInfo } from "@/shared/utils/zipStorage";
import CreateAgentTaskDialog from "./CreateAgentTaskDialog";

const testState = vi.hoisted(() => ({
  navigate: vi.fn(),
  hasAccess: vi.fn(() => true),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
  createAgentTask: vi.fn(),
  getProjects: vi.fn(),
  getZipFileInfo: vi.fn(),
}));

vi.mock("react-router-dom", () => ({
  useNavigate: () => testState.navigate,
}));

vi.mock("sonner", () => ({
  toast: {
    success: testState.toastSuccess,
    error: testState.toastError,
    info: vi.fn(),
  },
}));

vi.mock("@/shared/context/AuthContext", () => ({
  useAuth: () => ({
    hasAccess: testState.hasAccess,
  }),
}));

vi.mock("@/shared/config/database", () => ({
  api: {
    getProjects: testState.getProjects,
    getProjectBranches: vi.fn(),
  },
}));

vi.mock("@/shared/api/agentTasks", () => ({
  createAgentTask: testState.createAgentTask,
}));

vi.mock("@/shared/utils/zipStorage", () => ({
  getZipFileInfo: testState.getZipFileInfo,
  validateZipFile: vi.fn(() => ({ valid: true })),
}));

vi.mock("@/components/ui/dialog", () => ({
  Dialog: ({ children, open }: { children?: ReactNode; open?: boolean }) =>
    open ? <div data-testid="dialog">{children}</div> : null,
  DialogContent: ({ children, ...props }: { children?: ReactNode }) => (
    <div {...props}>{children}</div>
  ),
  DialogHeader: ({ children, ...props }: { children?: ReactNode }) => (
    <div {...props}>{children}</div>
  ),
  DialogTitle: ({ children, ...props }: { children?: ReactNode }) => (
    <div {...props}>{children}</div>
  ),
}));

vi.mock("@/components/ui/button", () => ({
  Button: ({
    children,
    ...props
  }: ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button {...props}>{children}</button>
  ),
}));

vi.mock("@/components/ui/badge", () => ({
  Badge: ({
    children,
    ...props
  }: HTMLAttributes<HTMLSpanElement>) => <span {...props}>{children}</span>,
}));

vi.mock("@/components/ui/input", () => ({
  Input: ({
    children: _children,
    ...props
  }: InputHTMLAttributes<HTMLInputElement>) => <input {...props} />,
}));

vi.mock("@/components/ui/scroll-area", () => ({
  ScrollArea: ({
    children,
    ...props
  }: HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div>,
}));

vi.mock("@/components/ui/collapsible", () => ({
  Collapsible: ({
    children,
    onOpenChange: _onOpenChange,
    ...props
  }: HTMLAttributes<HTMLDivElement> & { onOpenChange?: unknown }) => (
    <div {...props}>{children}</div>
  ),
  CollapsibleContent: ({
    children,
    ...props
  }: HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div>,
  CollapsibleTrigger: ({
    children,
    ...props
  }: ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button {...props}>{children}</button>
  ),
}));

vi.mock("@/components/ui/branch-selector", () => ({
  BranchSelector: ({
    value,
    onChange,
  }: {
    value?: string;
    onChange?: (value: string) => void;
  }) => (
    <select
      aria-label="branch-selector"
      onChange={(event) => onChange?.(event.target.value)}
      value={value}
    />
  ),
}));

vi.mock("@/components/audit/FileSelectionDialog", () => ({
  default: () => null,
}));

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

function createZipProject(): Project {
  const now = new Date().toISOString();
  return {
    id: "zip-project-1",
    name: "ZIP Scenario Project",
    description: "验证场景预设的 ZIP 项目",
    source_type: "zip",
    default_branch: "main",
    programming_languages: '["c", "cpp"]',
    owner_id: "owner-1",
    is_active: true,
    created_at: now,
    updated_at: now,
  };
}

async function flushMicrotasks(cycles = 4) {
  for (let i = 0; i < cycles; i += 1) {
    await act(async () => {
      await Promise.resolve();
    });
  }
}

describe("CreateAgentTaskDialog", () => {
  let container: HTMLDivElement;
  let root: Root;

  const renderDialog = () => {
    act(() => {
      root.render(<CreateAgentTaskDialog open onOpenChange={vi.fn()} />);
    });
  };

  const findButtonByText = (text: string) =>
    Array.from(container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes(text),
    );

  const findProjectItem = (name: string) =>
    Array.from(container.querySelectorAll("div")).find(
      (element) =>
        element.className.includes("cursor-pointer") &&
        element.textContent?.includes(name),
    );

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);

    const project = createZipProject();
    testState.navigate.mockReset();
    testState.hasAccess.mockReset().mockReturnValue(true);
    testState.toastSuccess.mockReset();
    testState.toastError.mockReset();
    testState.createAgentTask.mockReset().mockResolvedValue({ id: "agent-task-1" });
    testState.getProjects.mockReset().mockResolvedValue([project]);
    testState.getZipFileInfo.mockReset().mockResolvedValue({ has_file: true });
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
    vi.clearAllMocks();
  });

  it("submits only the selected scenario key in the audit scope payload", async () => {
    renderDialog();
    await flushMicrotasks();

    const projectItem = findProjectItem("ZIP Scenario Project");
    expect(projectItem).toBeTruthy();

    act(() => {
      projectItem?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    await flushMicrotasks();

    const scenarioButton = findButtonByText("高危 API 调用链梳理");
    expect(scenarioButton).toBeTruthy();

    act(() => {
      scenarioButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    await flushMicrotasks();

    const startButton = findButtonByText("Start Audit");
    expect(startButton).toBeTruthy();
    expect((startButton as HTMLButtonElement).disabled).toBe(false);

    expect(testState.createAgentTask).not.toHaveBeenCalled();

    await act(async () => {
      startButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      await Promise.resolve();
    });
    await flushMicrotasks();

    expect(testState.createAgentTask).toHaveBeenCalledTimes(1);
    const payload = testState.createAgentTask.mock.calls[0]?.[0] as
      | unknown
      | undefined;
    const payloadRecord = payload as Record<string, unknown> | undefined;
    expect(payload).toEqual(
      expect.objectContaining({
        project_id: "zip-project-1",
        name: "Agent审计-ZIP Scenario Project",
        verification_level: "sandbox",
      }),
    );
    expect(payloadRecord?.audit_scope).toEqual({ scenario_key: "api_chain" });
    expect(payloadRecord?.target_vulnerabilities).toBeUndefined();
    expect(payloadRecord?.prompt_template_id).toBeUndefined();
    expect(payloadRecord?.rule_set_id).toBeUndefined();
    expect(payloadRecord?.knowledge_modules).toBeUndefined();
    expect(testState.toastSuccess).toHaveBeenCalledWith("Agent 审计任务已创建");
    expect(testState.navigate).toHaveBeenCalledWith("/agent-audit/agent-task-1");
  });
});
