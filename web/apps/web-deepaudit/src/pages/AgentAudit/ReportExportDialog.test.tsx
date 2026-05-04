import {
	act,
	type ButtonHTMLAttributes,
	type ComponentProps,
	type HTMLAttributes,
	type InputHTMLAttributes,
	type ReactNode,
} from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ReportExportDialog } from "./components/ReportExportDialog";
import type { AgentFinding, AgentTask } from "@/shared/api/agentTasks";

const testState = vi.hoisted(() => ({
	apiGet: vi.fn(),
	generateHtml: vi.fn(),
	serializeOptions: vi.fn((options: unknown) => JSON.stringify(options)),
	toastSuccess: vi.fn(),
	toastError: vi.fn(),
	createObjectURL: vi.fn(() => "blob:mock-url"),
	revokeObjectURL: vi.fn(),
	anchorClick: vi.fn(),
}));

vi.mock("@/shared/api/serverClient", () => ({
	apiClient: {
		get: testState.apiGet,
	},
}));

vi.mock("./reportHtml", () => ({
	DEFAULT_REPORT_EXPORT_OPTIONS: {
		includeCodeSnippets: true,
		includeRemediation: true,
		includeMetadata: true,
		compactMode: false,
	},
	generateAgentAuditHtmlReport: testState.generateHtml,
	serializeReportExportOptions: testState.serializeOptions,
}));

vi.mock("sonner", () => ({
	toast: {
		success: testState.toastSuccess,
		error: testState.toastError,
	},
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
	Button: ({ children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) => (
		<button {...props}>{children}</button>
	),
}));

vi.mock("@/components/ui/badge", () => ({
	Badge: ({ children, ...props }: HTMLAttributes<HTMLSpanElement>) => (
		<span {...props}>{children}</span>
	),
}));

vi.mock("@/components/ui/scroll-area", () => ({
	ScrollArea: ({ children, ...props }: HTMLAttributes<HTMLDivElement>) => (
		<div {...props}>{children}</div>
	),
}));

vi.mock("@/components/ui/switch", () => ({
	Switch: ({
		checked,
		onCheckedChange,
		...props
	}: InputHTMLAttributes<HTMLInputElement> & {
		checked?: boolean;
		onCheckedChange?: unknown;
	}) => (
		<input
			{...props}
			type="checkbox"
			aria-checked={checked ? "true" : "false"}
			checked={checked}
			readOnly
		/>
	),
}));

(
	globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

function createTask(): AgentTask {
	return {
		id: "task-1",
		project_id: "project-1",
		name: "HTML 导出烟雾测试",
		description: "确认 HTML 报告仍可通过导出弹窗正常生成和下载。",
		task_type: "deepaudit",
		status: "completed",
		current_phase: "reporting",
		current_step: "完成",
		total_files: 12,
		indexed_files: 12,
		analyzed_files: 11,
		files_with_findings: 1,
		total_chunks: 30,
		findings_count: 1,
		verified_count: 1,
		false_positive_count: 0,
		total_iterations: 4,
		tool_calls_count: 8,
		tokens_used: 2048,
		critical_count: 0,
		high_count: 1,
		medium_count: 0,
		low_count: 0,
		quality_score: 92,
		security_score: 88,
		created_at: "2026-05-04T01:02:03.000Z",
		started_at: "2026-05-04T01:05:00.000Z",
		completed_at: "2026-05-04T01:10:00.000Z",
		repository_type: "single",
		repository_signature: "repo-signature",
		repository_url: "https://example.com/repo.git",
		branch_name: "main",
		manifest_xml: null,
		group: "security",
		workspace_path: "/tmp/workspace",
		cache_repo: null,
		last_synced_at: 1710000000,
		progress_percentage: 100,
		audit_scope: {},
		target_vulnerabilities: ["xss"],
		verification_level: "sandbox",
		exclude_patterns: [],
		target_files: ["src/app.ts"],
		selected_target_count: 1,
		selected_directory_count: 0,
		resolved_file_count: 11,
		workspace_source: "workspace",
		error_message: null,
	};
}

function createFindings(): AgentFinding[] {
	return [
		{
			id: "finding-1",
			task_id: "task-1",
			vulnerability_type: "xss",
			severity: "high",
			title: "Reflected XSS in preview panel",
			description: "预览面板直接渲染外部输入。",
			file_path: "src/components/Preview.tsx",
			line_start: 24,
			line_end: 28,
			code_snippet: "<div dangerouslySetInnerHTML={{ __html: input }} />",
			status: "open",
			is_verified: false,
			has_poc: false,
			poc_code: null,
			suggestion: "在渲染前对输入内容进行转义或过滤。",
			fix_code: null,
			ai_explanation: "直接渲染未经信任的 HTML 会暴露脚本执行面。",
			ai_confidence: 0.93,
			created_at: "2026-05-04T01:06:00.000Z",
		},
	];
}

async function flushMicrotasks(cycles = 6) {
	for (let i = 0; i < cycles; i += 1) {
		await act(async () => {
			await Promise.resolve();
		});
	}
}

describe("ReportExportDialog HTML export smoke test", () => {
	let container: HTMLDivElement;
	let root: Root;

	const renderDialog = (
		props: Partial<ComponentProps<typeof ReportExportDialog>> = {},
	) => {
		const task = props.task ?? createTask();
		const findings = props.findings ?? createFindings();

		act(() => {
			root.render(
				<ReportExportDialog
					open
					onOpenChange={vi.fn()}
					task={task}
					findings={findings}
					{...props}
				/>,
			);
		});
	};

	beforeEach(() => {
		container = document.createElement("div");
		document.body.appendChild(container);
		root = createRoot(container);

		testState.apiGet
			.mockReset()
			.mockImplementation(
				async (_url: string, config?: { params?: { format?: string } }) => {
					if (config?.params?.format === "json") {
						return { data: { task_id: "task-1", status: "completed" } };
					}
					return {
						data: ["# 总览", "", "## 风险", "报告正文。"].join("\n"),
					};
				},
			);
		testState.generateHtml
			.mockReset()
			.mockResolvedValue(
				"<!doctype html><html><body><h1>Light HTML Report</h1></body></html>",
			);
		testState.serializeOptions.mockClear();
		testState.toastSuccess.mockReset();
		testState.toastError.mockReset();
		testState.createObjectURL.mockReset().mockReturnValue("blob:mock-url");
		testState.revokeObjectURL.mockReset();
		testState.anchorClick.mockReset();

		vi.spyOn(URL, "createObjectURL").mockImplementation(
			testState.createObjectURL,
		);
		vi.spyOn(URL, "revokeObjectURL").mockImplementation(
			testState.revokeObjectURL,
		);
		vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(
			testState.anchorClick,
		);
	});

	afterEach(() => {
		act(() => {
			root.unmount();
		});
		container.remove();
		vi.restoreAllMocks();
		vi.clearAllMocks();
	});

	it("builds and downloads the HTML report from the export dialog", async () => {
		renderDialog();
		await flushMicrotasks();

		expect(testState.apiGet).toHaveBeenCalledWith(
			"/agent-tasks/task-1/report",
			expect.objectContaining({ params: { format: "markdown" } }),
		);

		const htmlFormatButton = Array.from(
			container.querySelectorAll("button"),
		).find((button) => button.textContent?.includes("HTML"));
		expect(htmlFormatButton).toBeTruthy();

		await act(async () => {
			htmlFormatButton?.dispatchEvent(
				new MouseEvent("click", { bubbles: true }),
			);
		});
		await flushMicrotasks();

		expect(testState.generateHtml).toHaveBeenCalledTimes(1);
		expect(testState.generateHtml).toHaveBeenCalledWith(
			expect.stringContaining("# 总览"),
			expect.objectContaining({ id: "task-1" }),
			expect.arrayContaining([
				expect.objectContaining({ title: "Reflected XSS in preview panel" }),
			]),
			expect.any(Object),
		);

		const downloadButton = Array.from(
			container.querySelectorAll("button"),
		).find((button) => button.textContent?.includes("下载 HTML")) as
			| HTMLButtonElement
			| undefined;

		expect(downloadButton).toBeTruthy();
		expect(downloadButton?.disabled).toBe(false);

		await act(async () => {
			downloadButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
		});
		await flushMicrotasks();

		expect(testState.generateHtml).toHaveBeenCalledTimes(2);
		expect(testState.anchorClick).toHaveBeenCalledTimes(1);
		expect(testState.createObjectURL).toHaveBeenCalledTimes(1);
		expect(testState.revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
		expect(testState.toastSuccess).toHaveBeenCalledWith(
			"报告已导出为 HTML 格式",
		);
	});
});
