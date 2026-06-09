import { act, type ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getAgentTask } from "@/shared/api/agentTasks";
import AgentAuditPage from "./index";

const testState = vi.hoisted(() => ({
	taskId: "task-1" as string | null,
	connectStream: vi.fn(),
	disconnectStream: vi.fn(),
	navigate: vi.fn(),
	hasAccess: vi.fn(() => false),
	toastError: vi.fn(),
	taskCallCounts: {} as Record<string, number>,
	eventCallCounts: {} as Record<string, number>,
}));

vi.mock("react-router-dom", () => ({
	useNavigate: () => testState.navigate,
	useParams: () => ({ taskId: testState.taskId }),
}));

vi.mock("sonner", () => ({
	toast: {
		error: testState.toastError,
	},
}));

vi.mock("@/shared/context/AuthContext", () => ({
	useAuth: () => ({
		hasAccess: testState.hasAccess,
	}),
}));

vi.mock("@/hooks/useAgentStream", () => ({
	useAgentStream: vi.fn(() => ({
		connect: testState.connectStream,
		disconnect: testState.disconnectStream,
		isConnected: false,
	})),
	default: vi.fn(() => ({
		connect: testState.connectStream,
		disconnect: testState.disconnectStream,
		isConnected: false,
	})),
}));

vi.mock("@/shared/api/agentTasks", () => ({
	cancelAgentTask: vi.fn(async () => true),
	getAgentEvents: vi.fn(
		async (taskId: string, params: { after_sequence?: number } = {}) => {
			const callIndex = testState.eventCallCounts[taskId] ?? 0;
			testState.eventCallCounts[taskId] = callIndex + 1;

			if ((params.after_sequence ?? 0) > 0 || callIndex > 0) {
				return [];
			}

			const baseSequence = taskId === "task-1" ? 1 : 101;
			return [
				{
					id: `${taskId}-event-${baseSequence}`,
					sequence: baseSequence,
					event_type: "info",
					message: `${taskId} historical log`,
					timestamp: "2026-05-04T00:00:00.000Z",
					metadata: {
						agent_name: "Orchestrator",
					},
				},
			];
		},
	),
	getAgentFindings: vi.fn(async () => []),
	getAgentTask: vi.fn(async (taskId: string) => {
		const callIndex = testState.taskCallCounts[taskId] ?? 0;
		testState.taskCallCounts[taskId] = callIndex + 1;

		const statusSequence =
			taskId === "task-1" ? ["planning", "indexing"] : ["running"];
		const status =
			statusSequence[Math.min(callIndex, statusSequence.length - 1)];

		return {
			id: taskId,
			name: `Task ${taskId}`,
			status,
			current_phase: status,
			current_step: `${status} step`,
			last_synced_at: 1710000000,
			workspace_source: "workspace",
			total_files: 0,
			resolved_file_count: 0,
			selected_target_count: 0,
			selected_directory_count: 0,
		} as Awaited<ReturnType<typeof getAgentTask>>;
	}),
	getAgentTree: vi.fn(async (taskId: string) => ({
		task_id: taskId,
		root_agent_id: null,
		total_agents: 0,
		running_agents: 0,
		completed_agents: 0,
		failed_agents: 0,
		total_findings: 0,
		nodes: [],
	})),
}));

vi.mock("@/components/ui/badge", () => ({
	Badge: ({ children }: { children?: ReactNode }) => <span>{children}</span>,
}));

vi.mock("@/components/agent/CreateAgentTaskDialog", () => ({
	default: () => null,
}));

vi.mock("./components", () => ({
	SplashScreen: () => null,
	Header: () => null,
	LogEntry: () => null,
	AgentTreeNodeItem: () => null,
	AgentDetailPanel: () => null,
	StatsPanel: () => null,
	InventoryReportPanel: () => null,
	AgentErrorBoundary: ({ children }: { children?: ReactNode }) => (
		<>{children}</>
	),
	CheckpointDialog: () => null,
}));

vi.mock("./components/ReportExportDialog", () => ({
	default: () => null,
}));

(
	globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

if (!HTMLElement.prototype.scrollIntoView) {
	Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
		value: vi.fn(),
		writable: true,
	});
}

async function flushMicrotasks(cycles = 6) {
	for (let i = 0; i < cycles; i++) {
		await act(async () => {
			await Promise.resolve();
		});
	}
}

describe("AgentAudit SSE lifecycle", () => {
	let container: HTMLDivElement;
	let root: Root;
	const mockedGetAgentTask = vi.mocked(getAgentTask);

	const renderPage = () => {
		act(() => {
			root.render(<AgentAuditPage />);
		});
	};

	beforeEach(() => {
		container = document.createElement("div");
		document.body.appendChild(container);
		root = createRoot(container);

		testState.taskId = "task-1";
		testState.taskCallCounts = {};
		testState.eventCallCounts = {};
		testState.connectStream.mockReset();
		testState.disconnectStream.mockReset();
		testState.navigate.mockReset();
		testState.hasAccess.mockReset().mockReturnValue(false);
		testState.toastError.mockReset();
		mockedGetAgentTask.mockClear();

		vi.useFakeTimers();
	});

	afterEach(() => {
		act(() => {
			root.unmount();
		});
		container.remove();
		vi.useRealTimers();
		vi.clearAllMocks();
	});

	it("keeps the SSE connection alive when active task status refreshes", async () => {
		renderPage();
		await flushMicrotasks();

		expect(testState.connectStream).toHaveBeenCalledTimes(1);
		expect(testState.disconnectStream).not.toHaveBeenCalled();

		await act(async () => {
			await vi.advanceTimersByTimeAsync(2000);
		});
		await flushMicrotasks();

		expect(mockedGetAgentTask).toHaveBeenCalledTimes(2);
		expect(testState.connectStream).toHaveBeenCalledTimes(1);
		expect(testState.disconnectStream).not.toHaveBeenCalled();
	});

	it("disconnects the old stream and reconnects after the task id changes", async () => {
		renderPage();
		await flushMicrotasks();

		expect(testState.connectStream).toHaveBeenCalledTimes(1);
		expect(testState.disconnectStream).not.toHaveBeenCalled();

		testState.taskId = "task-2";
		renderPage();
		await flushMicrotasks();

		expect(testState.disconnectStream).toHaveBeenCalledTimes(1);
		expect(testState.connectStream).toHaveBeenCalledTimes(2);
	});
});
